"""Declaration handlers: functions, classes, interfaces, enums, exports, type aliases.

Each public function takes a tree-sitter ``Node`` and returns a Rust AST
node (``RsItem``) or a formatted string for backward compatibility.
"""

from __future__ import annotations

import re
from tree_sitter import Node

from .rust_ast import (
    RsItem, RsFunction, RsStruct, RsEnum, RsImpl, RsTypeAlias, RsConst,
    RsField, RsEnumVariant, RsParam, RsComment, RsRawStmt,
    RsStmt, RsRawExpr, RsExpr, RsType, RsRawType,
)
from .types import convert_type, convert_type_node, _TYPE_MAP
from .helpers import _snake, _screaming, _safe_field


def _params_list(node: Node | None) -> list[RsParam]:
    """Convert a ``formal_parameters`` node to a list of RsParam AST nodes."""
    if node is None:
        return []
    params: list[RsParam] = []
    for ch in node.children:
        if ch.type == "comment":
            # Comments in params are tricky -- we store as a param with comment name
            params.append(RsParam(
                name=f"/* {ch.text.decode().lstrip('/ ')} */",
                type_ann=RsRawType(text=""),
            ))
        elif ch.type == "required_parameter":
            name = None
            type_ann = None
            is_rest = False
            for c2 in ch.children:
                if c2.type == "identifier":
                    name = c2
                if c2.type == "type_annotation":
                    type_ann = c2
                if c2.type == "rest_pattern":
                    is_rest = True
                    for c3 in c2.children:
                        if c3.type == "identifier":
                            name = c3
            n = _snake(name.text.decode()) if name else "_"
            t = convert_type(type_ann) if type_ann else "serde_json::Value"
            if is_rest:
                params.append(RsParam(name=n, type_ann=RsRawType(text=t), is_rest=True))
            else:
                if t == "String":
                    t = "&str"
                params.append(RsParam(name=n, type_ann=RsRawType(text=t)))
        elif ch.type == "optional_parameter":
            name = None
            type_ann = None
            has_default = False
            for c2 in ch.children:
                if c2.type == "identifier":
                    name = c2
                if c2.type == "type_annotation":
                    type_ann = c2
                if not c2.is_named and c2.text.decode() == "=":
                    has_default = True
            n = _snake(name.text.decode()) if name else "_"
            t = convert_type(type_ann) if type_ann else "serde_json::Value"
            if has_default:
                if t == "String":
                    t = "&str"
                params.append(RsParam(name=n, type_ann=RsRawType(text=t)))
            else:
                params.append(RsParam(name=n, type_ann=RsRawType(text=f"Option<{t}>")))
    return params


def _params(node: Node | None) -> str:
    """Convert a ``formal_parameters`` node to a Rust parameter list string.

    Backward-compatible wrapper returning a string.
    """
    param_list = _params_list(node)
    parts: list[str] = []
    for p in param_list:
        from .formatter import format_type
        ts = format_type(p.type_ann)
        if ts == "":
            # Comment-only param
            parts.append(p.name)
        elif p.is_rest:
            parts.append(f"{p.name}: &[{ts}]")
        else:
            parts.append(f"{p.name}: {ts}")
    return ", ".join(parts)


def _function(node: Node, ind: int = 0) -> str:
    """Convert a function or generator declaration to a Rust ``pub fn``.

    Returns the formatted string (for backward compatibility with converter.py).
    """
    fn_node = _function_node(node)
    from .formatter import format_item
    return format_item(fn_node, ind)


def _function_node(node: Node) -> RsFunction:
    """Convert a function or generator declaration to an RsFunction AST node."""
    from .statements import _block_body_stmts

    name = node.child_by_field_name("name")
    params_node = None
    ret = None
    body = None
    is_async = False
    for ch in node.children:
        if ch.type == "async":
            is_async = True
        if ch.type == "formal_parameters":
            params_node = ch
        if ch.type == "type_annotation":
            ret = ch
        if ch.type == "statement_block":
            body = ch
    fn_name = _snake(name.text.decode()) if name else "unknown"
    params = _params_list(params_node)
    ret_type = None
    if ret:
        rt = convert_type(ret)
        if rt not in ("()", ""):
            ret_type = RsRawType(text=rt)
    body_stmts = _block_body_stmts(body) if body else [RsRawStmt(text="    // empty")]

    return RsFunction(
        name=fn_name,
        is_pub=True,
        is_async=is_async,
        params=params,
        return_type=ret_type,
        body=body_stmts,
    )


def _type_alias(node: Node) -> str:
    """Convert a ``type_alias_declaration`` to a Rust type alias or struct."""
    name = None
    type_val = None
    found_eq = False
    comments: list[str] = []
    for ch in node.children:
        if ch.type == "type_identifier":
            name = ch
        if ch.type == "comment":
            comments.append(ch.text.decode())
        if ch.text.decode() == "=":
            found_eq = True
        elif found_eq and ch.is_named and ch.type != "comment":
            type_val = ch
            break
    n = name.text.decode() if name else "Unknown"
    if type_val and type_val.type == "object_type":
        result = _object_type_to_struct(n, type_val)
        if comments:
            return "\n".join(comments) + "\n" + result
        return result
    t = convert_type(type_val) if type_val else "serde_json::Value"
    result = f"pub type {n} = {t};"
    if comments:
        return "\n".join(comments) + "\n" + result
    return result


def _object_type_to_struct(name: str, node: Node) -> str:
    """Convert a TypeScript object type to a Rust struct with serde derives."""
    fields: list[str] = []
    for ch in node.children:
        if ch.type == "comment":
            fields.append(f"    {ch.text.decode()}")
        elif ch.type == "property_signature":
            pname = None
            ptype = None
            optional = False
            for c2 in ch.children:
                if c2.type == "property_identifier":
                    pname = c2
                if c2.type == "type_annotation":
                    ptype = c2
                if c2.type == "?":
                    optional = True
            if pname:
                fn = _safe_field(_snake(pname.text.decode()))
                ft = convert_type(ptype) if ptype else "serde_json::Value"
                if optional:
                    ft = f"Option<{ft}>"
                fields.append(f"    pub {fn}: {ft},")
    if fields:
        return (
            f"#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]\n"
            f"pub struct {name} {{\n" + "\n".join(fields) + "\n}"
        )
    return f"pub type {name} = serde_json::Value;"


def _interface(node: Node) -> str:
    """Convert an ``interface_declaration`` to a Rust struct."""
    name = None
    body = None
    for ch in node.children:
        if ch.type == "type_identifier":
            name = ch
        if ch.type in ("object_type", "interface_body"):
            body = ch
    n = name.text.decode() if name else "Unknown"
    fields: list[str] = []
    if body:
        for ch in body.children:
            if ch.type == "comment":
                fields.append(f"    {ch.text.decode()}")
            elif ch.type == "property_signature":
                pname = None
                ptype = None
                optional = False
                for c2 in ch.children:
                    if c2.type == "property_identifier":
                        pname = c2
                    if c2.type == "type_annotation":
                        ptype = c2
                    if c2.type == "?":
                        optional = True
                if pname:
                    fn = _safe_field(_snake(pname.text.decode()))
                    ft = convert_type(ptype) if ptype else "serde_json::Value"
                    if optional:
                        ft = f"Option<{ft}>"
                    fields.append(f"    pub {fn}: {ft},")
    if fields:
        return (
            f"#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]\n"
            f"pub struct {n} {{\n" + "\n".join(fields) + "\n}"
        )
    return f"pub struct {n};"


def _class(node: Node) -> str:
    """Convert a class (or abstract class) declaration to a Rust struct + impl."""
    name = None
    body = None
    for ch in node.children:
        if ch.type == "type_identifier":
            name = ch
        if ch.type == "class_body":
            body = ch
    n = name.text.decode() if name else "Unknown"
    fields: list[str] = []
    methods: list[str] = []
    class_comments: list[str] = []
    if body:
        for ch in body.children:
            if ch.type == "comment":
                class_comments.append(f"    {ch.text.decode()}")
            elif ch.type == "public_field_definition":
                pname = None
                ptype = None
                for c2 in ch.children:
                    if c2.type == "property_identifier":
                        pname = c2
                    if c2.type == "type_annotation":
                        ptype = c2
                if pname:
                    fn = _safe_field(_snake(pname.text.decode()))
                    ft = convert_type(ptype) if ptype else "serde_json::Value"
                    fields.append(f"    pub {fn}: {ft},")
            elif ch.type == "method_definition":
                methods.append(_method(ch))
    fs = "\n".join(fields) if fields else "    _ph: (),"
    if class_comments:
        fs = "\n".join(class_comments) + "\n" + fs
    result = f"pub struct {n} {{\n{fs}\n}}"
    if methods:
        result += f"\n\nimpl {n} {{\n" + "\n\n".join(methods) + "\n}"
    return result


def _method(node: Node) -> str:
    """Convert a ``method_definition`` to a Rust method inside an impl block."""
    from .statements import _block_body

    name = None
    params_node = None
    body = None
    ret = None
    is_async = False
    for ch in node.children:
        if ch.type == "property_identifier":
            name = ch
        if ch.type == "formal_parameters":
            params_node = ch
        if ch.type == "statement_block":
            body = ch
        if ch.type == "type_annotation":
            ret = ch
        if ch.type == "async":
            is_async = True
    mn = _snake(name.text.decode()) if name else "unknown"
    if mn == "constructor":
        mn = "new"
    ps = _params(params_node) if params_node else ""
    if ps:
        ps = f"&self, {ps}"
    else:
        ps = "&self"
    ret_s = ""
    if ret:
        rt = convert_type(ret)
        if rt not in ("()", ""):
            ret_s = f" -> {rt}"
    async_kw = "async " if is_async else ""
    body_s = _block_body(body, 2) if body else "        // empty"
    body_lines = body_s.split("\n")
    body_lines = [
        line for line in body_lines
        if not re.match(r"\s*super\(", line) and not re.match(r"\s*self\.name\s*=", line)
    ]
    body_s = "\n".join(body_lines)
    return f"    pub {async_kw}fn {mn}({ps}){ret_s} {{\n{body_s}\n    }}"


def _enum(node: Node) -> str:
    """Convert an ``enum_declaration`` to a Rust enum."""
    name = None
    body = None
    for ch in node.children:
        if ch.type == "identifier":
            name = ch
        if ch.type == "enum_body":
            body = ch
    n = name.text.decode() if name else "Unknown"
    variants: list[str] = []
    if body:
        for ch in body.children:
            if ch.type == "comment":
                variants.append(f"    {ch.text.decode()}")
            elif ch.type == "enum_member":
                for c2 in ch.children:
                    if c2.type in ("property_identifier", "identifier"):
                        variants.append(f"    {c2.text.decode()},")
                        break
            elif ch.type in ("property_identifier", "identifier"):
                variants.append(f"    {ch.text.decode()},")
    vs = "\n".join(variants) if variants else "    // empty"
    return f"#[derive(Debug, Clone, PartialEq)]\npub enum {n} {{\n{vs}\n}}"


def _export(node: Node, ind: int) -> str:
    """Convert an ``export_statement`` to Rust."""
    from .converter import c, _fmt

    parts: list[str] = []
    has_default = any(
        ch.type == "default" or ch.text.decode() == "default"
        for ch in node.children
    )
    for ch in node.children:
        if ch.type in (
            "function_declaration", "generator_function_declaration",
            "type_alias_declaration",
            "interface_declaration", "class_declaration",
            "abstract_class_declaration", "enum_declaration",
        ):
            parts.append(_fmt(c(ch, ind)))
        elif ch.type == "lexical_declaration":
            parts.append(_export_const(ch, ind))
        elif ch.type == "object" and has_default:
            parts.append(f"pub const DEFAULT: serde_json::Value = {_fmt(c(ch))};")
        elif ch.type == "satisfies_expression" and has_default:
            named = [c2 for c2 in ch.children if c2.is_named]
            if named:
                parts.append(f"pub const DEFAULT: serde_json::Value = {_fmt(c(named[0]))};")
        elif ch.type == "identifier" and has_default:
            parts.append(f"pub use {_snake(ch.text.decode())} as default;")
        elif ch.type == "call_expression" and has_default:
            parts.append(f"pub const DEFAULT: serde_json::Value = {_fmt(c(ch))};")
    return "\n".join(parts)


def _infer_const_type(value_node: Node | None) -> str:
    """Infer a Rust type from a constant's value node."""
    if value_node is None:
        return "&str"
    t = value_node.type
    if t == "number":
        text = value_node.text.decode()
        if "." in text:
            return "f64"
        return "usize"
    if t == "string":
        return "&str"
    if t == "template_string":
        return "String"
    if t in ("true", "false"):
        return "bool"
    if t in ("null", "undefined"):
        return "Option<()>"
    if t == "array":
        elems = [ch for ch in value_node.children if ch.is_named]
        if elems:
            ft = elems[0].type
            if ft == "string":
                return "&[&str]"
            if ft == "number":
                return "&[f64]"
            if ft in ("true", "false"):
                return "&[bool]"
        return "&[serde_json::Value]"
    if t == "object":
        return "serde_json::Value"
    return "&str"


def _export_const(node: Node, ind: int) -> str:
    """Convert an exported ``const`` declaration."""
    from .converter import c, _fmt

    P = "    " * ind
    for ch in node.children:
        if ch.type == "variable_declarator":
            name_node = None
            value = None
            type_ann = None
            found_eq = False
            for c2 in ch.children:
                if c2.type == "identifier":
                    name_node = c2
                if c2.type == "type_annotation":
                    type_ann = c2
                if not c2.is_named and c2.text.decode() == "=":
                    found_eq = True
                elif (
                    found_eq and c2.is_named
                    and c2 != name_node and c2.type != "type_annotation"
                ):
                    value = c2
                    break
            name = name_node.text.decode() if name_node else "UNKNOWN"
            if value and value.type in ("arrow_function", "function"):
                return _const_fn(name, value, ind)
            val_s = _fmt(c(value)) if value else '""'
            const_name = _screaming(name)
            rs_type = convert_type(type_ann) if type_ann else _infer_const_type(value)
            return f"{P}pub const {const_name}: {rs_type} = {val_s};"
    return ""


def _const_fn(name: str, node: Node, ind: int) -> str:
    """Convert a ``const name = (params) => { ... }`` to ``pub fn name(...)``."""
    from .converter import c, _fmt
    from .statements import _block_body, _block_body_stmts

    P = "    " * ind
    fn_name = _snake(name)
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
        found_arrow = False
        for ch in node.children:
            if ch.type == "=>":
                found_arrow = True
            elif found_arrow and ch.is_named:
                expr = ch
                break
        body_s = f"{P}    {_fmt(c(expr))}" if expr else f"{P}    // empty"
    return f"{P}pub {async_kw}fn {fn_name}({ps}){ret_s} {{\n{body_s}\n{P}}}"
