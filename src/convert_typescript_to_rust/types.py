"""Type mapping and conversion for TypeScript types to Rust types.

Contains the canonical type map, Rust keyword set, and the ``convert_type``
function that turns any tree-sitter type node into a Rust type string.
"""

from __future__ import annotations

from tree_sitter import Node

from .rust_ast import (
    RsType, RsPrimitiveType, RsOptionType, RsVecType, RsHashMapType, RsRawType,
)


_TYPE_MAP: dict[str, str] = {
    "string": "String",
    "number": "f64",
    "boolean": "bool",
    "void": "()",
    "undefined": "()",
    "null": "()",
    "never": "!",
    "any": "serde_json::Value",
    "unknown": "serde_json::Value",
    "object": "serde_json::Value",
    "bigint": "i64",
    "symbol": "String",
    "Function": "Box<dyn Fn()>",
    "Date": "String",
    "RegExp": "String",
    "Error": "Box<dyn std::error::Error>",
    "Buffer": "Vec<u8>",
    "Uint8Array": "Vec<u8>",
    "ArrayBuffer": "Vec<u8>",
}

_RUST_KEYWORDS: frozenset[str] = frozenset({
    "type", "self", "Self", "super", "crate", "mod", "fn", "struct",
    "enum", "trait", "impl", "pub", "use", "let", "mut", "const",
    "static", "ref", "move", "return", "if", "else", "match",
    "for", "while", "loop", "break", "continue", "as", "in",
    "where", "async", "await", "dyn", "abstract", "become",
    "box", "do", "final", "macro", "override", "priv", "try",
    "typeof", "unsized", "virtual", "yield",
})


def _type_comments(n: Node) -> list[str]:
    """Collect comment texts from inside type nodes."""
    coms: list[str] = []
    for ch in n.children:
        if ch.type == "comment":
            coms.append(ch.text.decode())
        elif ch.is_named:
            coms.extend(_type_comments(ch))
    return coms


def convert_type_node(node: Node | None) -> RsType:
    """Convert a tree-sitter type node to an RsType AST node."""
    if node is None:
        return RsRawType(text="serde_json::Value")
    t = node.type
    tx = node.text.decode()

    if t == "predefined_type":
        return RsRawType(text=_TYPE_MAP.get(tx, tx))
    if t == "type_identifier":
        return RsRawType(text=_TYPE_MAP.get(tx, tx))
    if t == "array_type":
        named = [ch for ch in node.children if ch.is_named]
        inner = convert_type_node(named[0]) if named else RsRawType(text="serde_json::Value")
        return RsRawType(text=f"Vec<{_format_type_inline(inner)}>")
    if t == "generic_type":
        name_node = None
        args_node = None
        for ch in node.children:
            if ch.type == "type_identifier":
                name_node = ch
            if ch.type == "type_arguments":
                args_node = ch
        name = name_node.text.decode() if name_node else "Unknown"
        args = [ch for ch in (args_node.children if args_node else []) if ch.is_named]
        if name == "Promise":
            return convert_type_node(args[0]) if args else RsRawType(text="()")
        if name == "Array":
            inner = _format_type_inline(convert_type_node(args[0])) if args else "serde_json::Value"
            return RsRawType(text=f"Vec<{inner}>")
        if name == "Map":
            k = _format_type_inline(convert_type_node(args[0])) if args else "String"
            v = _format_type_inline(convert_type_node(args[1])) if len(args) > 1 else "serde_json::Value"
            return RsRawType(text=f"std::collections::HashMap<{k}, {v}>")
        if name == "Set":
            inner = _format_type_inline(convert_type_node(args[0])) if args else "String"
            return RsRawType(text=f"std::collections::HashSet<{inner}>")
        if name == "Record":
            k = _format_type_inline(convert_type_node(args[0])) if args else "String"
            v = _format_type_inline(convert_type_node(args[1])) if len(args) > 1 else "serde_json::Value"
            return RsRawType(text=f"std::collections::HashMap<{k}, {v}>")
        if name in ("Partial", "Readonly"):
            return convert_type_node(args[0]) if args else RsRawType(text="serde_json::Value")
        if args:
            a = ", ".join(_format_type_inline(convert_type_node(x)) for x in args)
            return RsRawType(text=f"{_TYPE_MAP.get(name, name)}<{a}>")
        return RsRawType(text=_TYPE_MAP.get(name, name))
    if t == "union_type":
        named = [ch for ch in node.children if ch.is_named and ch.type != "comment"]
        coms = _type_comments(node)
        nulls = {"null", "undefined"}
        non_null = [ch for ch in named if ch.text.decode() not in nulls]
        if len(non_null) < len(named) and len(non_null) == 1:
            result = f"Option<{_format_type_inline(convert_type_node(non_null[0]))}>"
        elif len(non_null) == 1:
            result = _format_type_inline(convert_type_node(non_null[0]))
        else:
            result = "serde_json::Value"
        if coms:
            return RsRawType(text="\n".join(coms) + "\n" + result)
        return RsRawType(text=result)
    if t == "intersection_type":
        return RsRawType(text="serde_json::Value")
    if t == "parenthesized_type":
        named = [ch for ch in node.children if ch.is_named]
        return convert_type_node(named[0]) if named else RsRawType(text="serde_json::Value")
    if t in ("literal_type", "template_literal_type"):
        return RsRawType(text="String")
    if t == "tuple_type":
        named = [ch for ch in node.children if ch.is_named]
        parts = ", ".join(_format_type_inline(convert_type_node(m)) for m in named)
        return RsRawType(text=f"({parts})" if named else "()")
    if t in ("object_type", "mapped_type", "index_signature", "conditional_type"):
        coms = _type_comments(node)
        result = "serde_json::Value"
        if coms:
            return RsRawType(text="\n".join(coms) + "\n" + result)
        return RsRawType(text=result)
    if t == "function_type":
        return RsRawType(text="Box<dyn Fn() -> serde_json::Value>")
    if t == "type_annotation":
        named = [ch for ch in node.children if ch.is_named]
        return convert_type_node(named[0]) if named else RsRawType(text="serde_json::Value")
    return RsRawType(text=_TYPE_MAP.get(tx, "serde_json::Value"))


def _format_type_inline(ty: RsType) -> str:
    """Quick inline formatting of a type node to a string."""
    from .formatter import format_type
    return format_type(ty)


def convert_type(node: Node | None) -> str:
    """Convert a tree-sitter type node to its Rust type string.

    This is the backward-compatible wrapper that returns a string.
    """
    ty = convert_type_node(node)
    return _format_type_inline(ty)
