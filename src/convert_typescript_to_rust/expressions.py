"""Expression handlers: template strings, arrows, objects, inline functions.

Converts tree-sitter expression nodes to their Rust equivalents.
"""

from __future__ import annotations

from tree_sitter import Node

from .types import convert_type
from .helpers import _snake
from .declarations import _params


def _args(node: Node | None, ind: int) -> str:
    """Convert an ``arguments`` node to a comma-separated Rust argument string.

    Args:
        node: The tree-sitter ``arguments`` node, or ``None``.
        ind: Current indentation level.

    Returns:
        A comma-separated string of converted arguments.
    """
    if node is None:
        return ""
    from .converter import c

    parts: list[str] = []
    for ch in node.children:
        if ch.is_named:
            parts.append(c(ch, ind))
    return ", ".join(parts)


def _template(node: Node, ind: int) -> str:
    """Convert a template string to Rust ``format!()`` or a plain string.

    Args:
        node: The tree-sitter ``template_string`` node.
        ind: Current indentation level.

    Returns:
        The Rust ``format!(...)`` or ``"...".to_string()`` expression.
    """
    from .converter import c

    parts: list[str] = []
    fmt_args: list[str] = []
    for ch in node.children:
        if ch.type in ("string_fragment", "escape_sequence"):
            parts.append(ch.text.decode().replace("{", "{{").replace("}", "}}"))
        elif ch.type == "template_substitution":
            named = [c2 for c2 in ch.children if c2.is_named]
            if named:
                parts.append("{}")
                fmt_args.append(c(named[0], ind))
    if not fmt_args:
        return f'"{"".join(parts)}".to_string()'
    return f'format!("{"".join(parts)}", {", ".join(fmt_args)})'


def _arrow(node: Node, ind: int) -> str:
    """Convert an arrow function to a Rust closure.

    Args:
        node: The tree-sitter ``arrow_function`` node.
        ind: Current indentation level.

    Returns:
        The Rust closure expression string.
    """
    from .converter import c
    from .statements import _block_body

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
        return f"|{ps}| {{\n{_block_body(body, ind + 1)}\n{'    ' * ind}}}"
    expr = None
    found = False
    for ch in node.children:
        if ch.type == "=>":
            found = True
        elif found and ch.is_named:
            expr = ch
            break
    if expr:
        return f"|{ps}| {c(expr, ind)}"
    return f"|{ps}| {{}}"


def _object(node: Node, ind: int) -> str:
    """Convert an object literal to Rust ``serde_json::json!({...})``.

    Inline function values are extracted as separate ``pub fn`` definitions.

    Args:
        node: The tree-sitter ``object`` node.
        ind: Current indentation level.

    Returns:
        The Rust object expression, possibly preceded by extracted functions.
    """
    from .converter import c
    from .statements import _block_body

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
                    fn_code = _extract_inline_fn(fn_name, val_node, ind)
                    extra_fns.append(fn_code)
                    pairs.append(f'"{key}": {fn_name}')
                else:
                    pairs.append(c(ch, ind))
            else:
                pairs.append(c(ch, ind))
        elif ch.type == "shorthand_property_identifier":
            name = ch.text.decode()
            pairs.append(f'"{name}": {_snake(name)}')
        elif ch.type == "spread_element":
            pairs.append(c(ch, ind))
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
                ps = _params(params_node) if params_node else ""
                async_kw = "async " if is_async else ""
                body_s = _block_body(body_node, ind + 1) if body_node else ""
                extra_fns.append(
                    f"{'    ' * ind}pub {async_kw}fn {fn_name}({ps}) {{\n{body_s}\n{'    ' * ind}}}"
                )
                pairs.append(f'"{name_node.text.decode()}": {fn_name}')
    obj_str = "serde_json::json!({" + ", ".join(pairs) + "})"
    result_parts: list[str] = []
    if comments:
        result_parts.extend(comments)
    if extra_fns:
        result_parts.extend(extra_fns)
    result_parts.append(obj_str)
    return "\n\n".join(result_parts)


def _extract_inline_fn(name: str, node: Node, ind: int) -> str:
    """Extract an inline arrow/function expression as a named Rust function.

    Args:
        name: The desired function name (snake_case).
        node: The tree-sitter arrow_function or function node.
        ind: Current indentation level.

    Returns:
        The Rust function definition string.
    """
    from .converter import c
    from .statements import _block_body

    P = "    " * ind
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
    ps = _params(params_node) if params_node else ""
    ret_s = ""
    if ret:
        rt = convert_type(ret)
        if rt not in ("()", ""):
            ret_s = f" -> {rt}"
    async_kw = "async " if is_async else ""
    if body:
        body_s = _block_body(body, ind + 1)
    else:
        expr = None
        found = False
        for ch in node.children:
            if ch.type == "=>":
                found = True
            elif found and ch.is_named:
                expr = ch
                break
        body_s = f"{P}    {c(expr, ind + 1)}" if expr else f"{P}    // empty"
    return f"{P}pub {async_kw}fn {name}({ps}){ret_s} {{\n{body_s}\n{P}}}"
