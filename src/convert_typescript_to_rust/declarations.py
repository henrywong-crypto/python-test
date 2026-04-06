"""Declaration handlers: functions, classes, interfaces, enums, exports, type aliases.

Each public function takes a tree-sitter ``Node`` and returns a Rust AST
node (``RsItem``) or list of items. NO string building -- only AST construction.
"""

from __future__ import annotations

import re
from tree_sitter import Node

from .rust_ast import (
    RsItem, RsFunction, RsStruct, RsEnum, RsImpl, RsTypeAlias, RsConst,
    RsField, RsEnumVariant, RsParam, RsComment, RsRawStmt,
    RsStmt, RsRawExpr, RsExpr, RsType, RsRawType, RsLiteral,
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
            parts.append(p.name)
        elif p.is_rest:
            parts.append(f"{p.name}: &[{ts}]")
        else:
            parts.append(f"{p.name}: {ts}")
    return ", ".join(parts)


def _function(node: Node) -> RsFunction:
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
    body_stmts = _block_body_stmts(body) if body else [RsRawStmt(text="// empty")]

    return RsFunction(
        name=fn_name,
        is_pub=True,
        is_async=is_async,
        params=params,
        return_type=ret_type,
        body=body_stmts,
    )


def _type_alias(node: Node) -> RsItem | list[RsItem]:
    """Convert a ``type_alias_declaration`` to a Rust type alias or struct."""
    name = None
    type_val = None
    found_eq = False
    comments: list[RsComment] = []
    for ch in node.children:
        if ch.type == "type_identifier":
            name = ch
        if ch.type == "comment":
            comments.append(RsComment(ch.text.decode()))
        if ch.text.decode() == "=":
            found_eq = True
        elif found_eq and ch.is_named and ch.type != "comment":
            type_val = ch
            break
    n = name.text.decode() if name else "Unknown"
    if type_val and type_val.type == "object_type":
        struct = _object_type_to_struct(n, type_val)
        if comments:
            return comments + [struct]
        return struct
    t = convert_type(type_val) if type_val else "serde_json::Value"
    ta = RsTypeAlias(name=n, type_ann=RsRawType(text=t))
    if comments:
        return comments + [ta]
    return ta


def _object_type_to_struct(name: str, node: Node) -> RsStruct | RsTypeAlias:
    """Convert a TypeScript object type to a Rust struct with serde derives."""
    fields: list[RsField] = []
    for ch in node.children:
        if ch.type == "comment":
            fields.append(RsField(
                name=f"_comment_{len(fields)}",
                type_ann=RsRawType(text=""),
                doc_comment=ch.text.decode(),
                is_pub=False,
            ))
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
                fields.append(RsField(name=fn, type_ann=RsRawType(text=ft)))
    # Filter out comment-only fields for the emptiness check
    real_fields = [f for f in fields if not f.name.startswith("_comment_")]
    if real_fields:
        return RsStruct(name=name, fields=fields)
    return RsTypeAlias(name=name, type_ann=RsRawType(text="serde_json::Value"))


def _interface(node: Node) -> RsStruct:
    """Convert an ``interface_declaration`` to a Rust struct."""
    name = None
    body = None
    for ch in node.children:
        if ch.type == "type_identifier":
            name = ch
        if ch.type in ("object_type", "interface_body"):
            body = ch
    n = name.text.decode() if name else "Unknown"
    fields: list[RsField] = []
    if body:
        for ch in body.children:
            if ch.type == "comment":
                fields.append(RsField(
                    name=f"_comment_{len(fields)}",
                    type_ann=RsRawType(text=""),
                    doc_comment=ch.text.decode(),
                    is_pub=False,
                ))
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
                    fields.append(RsField(name=fn, type_ann=RsRawType(text=ft)))
    real_fields = [f for f in fields if not f.name.startswith("_comment_")]
    if real_fields:
        return RsStruct(name=n, fields=fields)
    return RsStruct(name=n, is_empty=True)


def _class(node: Node) -> list[RsItem]:
    """Convert a class (or abstract class) declaration to a Rust struct + impl."""
    name = None
    body = None
    for ch in node.children:
        if ch.type == "type_identifier":
            name = ch
        if ch.type == "class_body":
            body = ch
    n = name.text.decode() if name else "Unknown"
    fields: list[RsField] = []
    methods: list[RsFunction] = []
    class_comments: list[RsField] = []
    if body:
        for ch in body.children:
            if ch.type == "comment":
                class_comments.append(RsField(
                    name=f"_comment_{len(class_comments)}",
                    type_ann=RsRawType(text=""),
                    doc_comment=ch.text.decode(),
                    is_pub=False,
                ))
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
                    fields.append(RsField(name=fn, type_ann=RsRawType(text=ft)))
            elif ch.type == "method_definition":
                methods.append(_method(ch))

    all_fields = class_comments + fields
    if not fields:
        all_fields.append(RsField(name="_ph", type_ann=RsRawType(text="()")))

    struct = RsStruct(
        name=n,
        fields=all_fields,
        derives=[],  # no derives for class structs
    )
    items: list[RsItem] = [struct]
    if methods:
        items.append(RsImpl(type_name=n, methods=methods))
    return items


def _method(node: Node) -> RsFunction:
    """Convert a ``method_definition`` to an RsFunction for an impl block."""
    from .statements import _block_body_stmts
    from .converter import _fmt_node

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
    params = _params_list(params_node)
    # Add &self as first param
    self_param = RsParam(name="&self", type_ann=RsRawType(text=""))
    all_params = [self_param] + params
    ret_type = None
    if ret:
        rt = convert_type(ret)
        if rt not in ("()", ""):
            ret_type = RsRawType(text=rt)
    body_stmts = _block_body_stmts(body) if body else [RsRawStmt(text="// empty")]
    # Filter out super() calls and self.name = ... assignments
    filtered_stmts: list[RsStmt] = []
    for s in body_stmts:
        text = _fmt_node(s)
        if re.match(r"\s*super\(", text) or re.match(r"\s*self\.name\s*=", text):
            continue
        filtered_stmts.append(s)

    return RsFunction(
        name=mn,
        is_pub=True,
        is_async=is_async,
        params=all_params,
        return_type=ret_type,
        body=filtered_stmts,
    )


def _enum(node: Node) -> RsEnum:
    """Convert an ``enum_declaration`` to a Rust enum."""
    name = None
    body = None
    for ch in node.children:
        if ch.type == "identifier":
            name = ch
        if ch.type == "enum_body":
            body = ch
    n = name.text.decode() if name else "Unknown"
    variants: list[RsEnumVariant] = []
    if body:
        for ch in body.children:
            if ch.type == "comment":
                variants.append(RsEnumVariant(
                    name=ch.text.decode().strip(),
                    doc_comment=ch.text.decode(),
                ))
            elif ch.type == "enum_member":
                for c2 in ch.children:
                    if c2.type in ("property_identifier", "identifier"):
                        variants.append(RsEnumVariant(name=c2.text.decode()))
                        break
            elif ch.type in ("property_identifier", "identifier"):
                variants.append(RsEnumVariant(name=ch.text.decode()))
    return RsEnum(name=n, variants=variants)


def _export(node: Node) -> RsItem | list[RsItem]:
    """Convert an ``export_statement`` to Rust item(s)."""
    from .converter import convert_node, convert_expr, _fmt_expr, _fmt_node

    items: list[RsItem] = []
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
            result = convert_node(ch)
            if isinstance(result, list):
                items.extend(r for r in result if isinstance(r, RsItem))
            elif isinstance(result, RsItem):
                items.append(result)
            elif result is not None:
                items.append(RsRawStmt(_fmt_node(result)))
        elif ch.type == "lexical_declaration":
            ec = _export_const(ch)
            if isinstance(ec, list):
                items.extend(ec)
            elif ec is not None:
                items.append(ec)
        elif ch.type == "object" and has_default:
            items.append(RsRawStmt(f"pub const DEFAULT: serde_json::Value = {_fmt_expr(convert_expr(ch))};"))
        elif ch.type == "satisfies_expression" and has_default:
            named = [c2 for c2 in ch.children if c2.is_named]
            if named:
                items.append(RsRawStmt(f"pub const DEFAULT: serde_json::Value = {_fmt_expr(convert_expr(named[0]))};"))
        elif ch.type == "identifier" and has_default:
            items.append(RsRawStmt(f"pub use {_snake(ch.text.decode())} as default;"))
        elif ch.type == "call_expression" and has_default:
            items.append(RsRawStmt(f"pub const DEFAULT: serde_json::Value = {_fmt_expr(convert_expr(ch))};"))
    if len(items) == 1:
        return items[0]
    return items if items else RsRawStmt("")


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


def _export_const(node: Node) -> RsItem | list[RsItem] | None:
    """Convert an exported ``const`` declaration."""
    from .converter import convert_expr, _fmt_expr

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
                return _const_fn(name, value)
            val_s = _fmt_expr(convert_expr(value)) if value else '""'
            const_name = _screaming(name)
            rs_type = convert_type(type_ann) if type_ann else _infer_const_type(value)
            return RsConst(
                name=const_name,
                type_ann=RsRawType(text=rs_type),
                value=RsRawExpr(val_s),
            )
    return None


def _const_fn(name: str, node: Node) -> RsFunction:
    """Convert a ``const name = (params) => { ... }`` to ``pub fn name(...)``."""
    from .statements import _block_body_stmts
    from .converter import convert_expr, _fmt_expr, _fmt_node

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
    params = _params_list(params_node)
    ret_type = None
    if ret:
        rt = convert_type(ret)
        if rt not in ("()", ""):
            ret_type = RsRawType(text=rt)
    if body:
        body_stmts = _block_body_stmts(body)
    else:
        expr = None
        found_arrow = False
        for ch in node.children:
            if ch.type == "=>":
                found_arrow = True
            elif found_arrow and ch.is_named:
                expr = ch
                break
        if expr:
            body_stmts = [RsRawStmt(_fmt_expr(convert_expr(expr)))]
        else:
            body_stmts = [RsRawStmt("// empty")]
    return RsFunction(
        name=fn_name,
        is_pub=True,
        is_async=is_async,
        params=params,
        return_type=ret_type,
        body=body_stmts,
    )
