"""Expression handlers: template strings, arrows, objects, inline functions.

Converts tree-sitter expression nodes to Rust AST nodes.
NO string building -- only AST node construction.
"""

from __future__ import annotations

from tree_sitter import Node

from .rust_ast import (
    RsExpr, RsRawExpr, RsStmt, RsRawStmt,
    RsFunction, RsParam, RsItem, RsClosure,
)
from .types import convert_type, convert_type_node
from .helpers import _snake
from .declarations import _params_list


def _args(node: Node | None) -> str:
    """Convert an ``arguments`` node to a comma-separated Rust argument string.

    Returns a plain string because arguments are used inline in many places.
    """
    if node is None:
        return ""
    from .converter import convert_expr, _fmt_expr

    parts: list[str] = []
    for ch in node.children:
        if ch.is_named:
            parts.append(_fmt_expr(convert_expr(ch)))
    return ", ".join(parts)


def _template(node: Node) -> RsExpr:
    """Convert a template string to Rust ``format!()`` or a plain string."""
    from .converter import convert_expr, _fmt_expr

    parts: list[str] = []
    fmt_args: list[str] = []
    for ch in node.children:
        if ch.type in ("string_fragment", "escape_sequence"):
            parts.append(ch.text.decode().replace("{", "{{").replace("}", "}}"))
        elif ch.type == "template_substitution":
            named = [c2 for c2 in ch.children if c2.is_named]
            if named:
                parts.append("{}")
                fmt_args.append(_fmt_expr(convert_expr(named[0])))
    if not fmt_args:
        return RsRawExpr(text=f'"{"".join(parts)}".to_string()')
    return RsRawExpr(text=f'format!("{"".join(parts)}", {", ".join(fmt_args)})')


def _arrow(node: Node) -> RsExpr:
    """Convert an arrow function to a Rust closure."""
    from .converter import convert_expr, _fmt_expr
    from .statements import _block_body_stmts

    params_node = None
    body = None
    single_param = None
    for ch in node.children:
        if ch.type == "formal_parameters":
            params_node = ch
        if ch.type == "statement_block":
            body = ch
        if ch.type == "identifier" and params_node is None and ch != node.children[0]:
            single_param = ch
    if single_param:
        ps = _snake(single_param.text.decode())
    elif params_node:
        ps_list: list[str] = []
        for ch in params_node.children:
            if ch.type in ("required_parameter", "optional_parameter"):
                for c2 in ch.children:
                    if c2.type == "identifier":
                        ps_list.append(_snake(c2.text.decode()))
            elif ch.type == "identifier":
                ps_list.append(_snake(ch.text.decode()))
        ps = ", ".join(ps_list)
    else:
        ps = ""

    if body:
        stmts = _block_body_stmts(body)
        from .converter import _fmt_node
        body_s = "\n".join(_fmt_node(s) for s in stmts if _fmt_node(s))
        return RsRawExpr(text=f"|{ps}| {{\n{body_s}\n}}")
    expr = None
    found = False
    for ch in node.children:
        if ch.type == "=>":
            found = True
        elif found and ch.is_named:
            expr = ch
            break
    if expr:
        return RsRawExpr(text=f"|{ps}| {_fmt_expr(convert_expr(expr))}")
    return RsRawExpr(text=f"|{ps}| {{}}")


def _object(node: Node) -> RsExpr:
    """Convert an object literal to Rust ``serde_json::json!({...})``.

    Inline function values are extracted as separate ``pub fn`` definitions.
    """
    from .converter import convert_expr, convert_node, _fmt_expr, _fmt_node
    from .statements import _block_body_stmts

    pairs: list[str] = []
    extra_fns: list[str] = []
    comments: list[str] = []
    for ch in node.children:
        if ch.type == "comment":
            comments.append(ch.text.decode())
        elif ch.type == "pair":
            named = [c2 for c2 in ch.children if c2.is_named]
            if len(named) >= 2:
                key = named[0].text.decode().strip("'\"")
                val_node = named[1]
                if val_node.type in ("arrow_function", "function"):
                    fn_name = _snake(key)
                    fn_code = _extract_inline_fn(fn_name, val_node)
                    extra_fns.append(fn_code)
                    pairs.append(f'"{key}": {fn_name}')
                else:
                    pairs.append(_fmt_expr(convert_expr(ch)))
            else:
                pairs.append(_fmt_expr(convert_expr(ch)))
        elif ch.type == "shorthand_property_identifier":
            name = ch.text.decode()
            pairs.append(f'"{name}": {_snake(name)}')
        elif ch.type == "spread_element":
            pairs.append(_fmt_expr(convert_expr(ch)))
        elif ch.type == "method_definition":
            name_node = None
            body_node = None
            params_node = None
            is_async = False
            for c2 in ch.children:
                if c2.type == "property_identifier":
                    name_node = c2
                if c2.type == "statement_block":
                    body_node = c2
                if c2.type == "formal_parameters":
                    params_node = c2
                if c2.type == "async":
                    is_async = True
            if name_node:
                fn_name = _snake(name_node.text.decode())
                ps = _params_str(params_node) if params_node else ""
                async_kw = "async " if is_async else ""
                stmts = _block_body_stmts(body_node) if body_node else []
                body_s = "\n".join(_fmt_node(s) for s in stmts if _fmt_node(s))
                extra_fns.append(
                    f"pub {async_kw}fn {fn_name}({ps}) {{\n{body_s}\n}}"
                )
                pairs.append(f'"{name_node.text.decode()}": {fn_name}')
    obj_str = "serde_json::json!({" + ", ".join(pairs) + "})"
    result_parts: list[str] = []
    if comments:
        result_parts.extend(comments)
    if extra_fns:
        result_parts.extend(extra_fns)
    result_parts.append(obj_str)
    return RsRawExpr(text="\n\n".join(result_parts))


def _extract_inline_fn(name: str, node: Node) -> str:
    """Extract an inline arrow/function expression as a named Rust function."""
    from .converter import convert_expr, _fmt_expr, _fmt_node
    from .statements import _block_body_stmts

    is_async = any(ch.type == "async" for ch in node.children)
    params_node = None
    body = None
    ret = None
    for ch in node.children:
        if ch.type == "formal_parameters":
            params_node = ch
        if ch.type == "statement_block":
            body = ch
        if ch.type == "type_annotation":
            ret = ch
    ps = _params_str(params_node) if params_node else ""
    ret_s = ""
    if ret:
        rt = convert_type(ret)
        if rt not in ("()", ""):
            ret_s = f" -> {rt}"
    async_kw = "async " if is_async else ""
    if body:
        stmts = _block_body_stmts(body)
        body_s = "\n".join(_fmt_node(s) for s in stmts if _fmt_node(s))
    else:
        expr = None
        found = False
        for ch in node.children:
            if ch.type == "=>":
                found = True
            elif found and ch.is_named:
                expr = ch
                break
        body_s = f"    {_fmt_expr(convert_expr(expr))}" if expr else "    // empty"
    return f"pub {async_kw}fn {name}({ps}){ret_s} {{\n{body_s}\n}}"


def _params_str(node: Node | None) -> str:
    """Convert a ``formal_parameters`` node to a comma-separated Rust param string."""
    from .declarations import _params
    return _params(node)
