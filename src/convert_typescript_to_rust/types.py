"""Type mapping and conversion for TypeScript types to Rust types.

Contains the canonical type map, Rust keyword set, and the ``convert_type``
function that turns any tree-sitter type node into a Rust type string.
"""

from __future__ import annotations

from tree_sitter import Node


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
    """Collect comment texts from inside type nodes.

    Args:
        n: A tree-sitter ``Node``.

    Returns:
        A list of comment text strings found recursively.
    """
    coms: list[str] = []
    for ch in n.children:
        if ch.type == "comment":
            coms.append(ch.text.decode())
        elif ch.is_named:
            coms.extend(_type_comments(ch))
    return coms


def convert_type(node: Node | None) -> str:
    """Convert a tree-sitter type node to its Rust type string.

    Handles predefined types, generics (``Promise``, ``Array``, ``Map``,
    ``Set``, ``Record``, ``Partial``, ``Readonly``), unions, intersections,
    tuples, function types, and more.

    Args:
        node: The tree-sitter type node, or ``None``.

    Returns:
        The Rust type string.
    """
    if node is None:
        return "serde_json::Value"
    t = node.type
    tx = node.text.decode()

    if t == "predefined_type":
        return _TYPE_MAP.get(tx, tx)
    if t == "type_identifier":
        return _TYPE_MAP.get(tx, tx)
    if t == "array_type":
        named = [ch for ch in node.children if ch.is_named]
        return f"Vec<{convert_type(named[0])}>" if named else "Vec<serde_json::Value>"
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
            return convert_type(args[0]) if args else "()"
        if name == "Array":
            return f"Vec<{convert_type(args[0])}>" if args else "Vec<serde_json::Value>"
        if name == "Map":
            k = convert_type(args[0]) if args else "String"
            v = convert_type(args[1]) if len(args) > 1 else "serde_json::Value"
            return f"std::collections::HashMap<{k}, {v}>"
        if name == "Set":
            return (
                f"std::collections::HashSet<{convert_type(args[0])}>"
                if args
                else "std::collections::HashSet<String>"
            )
        if name == "Record":
            k = convert_type(args[0]) if args else "String"
            v = convert_type(args[1]) if len(args) > 1 else "serde_json::Value"
            return f"std::collections::HashMap<{k}, {v}>"
        if name in ("Partial", "Readonly"):
            return convert_type(args[0]) if args else "serde_json::Value"
        if args:
            a = ", ".join(convert_type(x) for x in args)
            return f"{_TYPE_MAP.get(name, name)}<{a}>"
        return _TYPE_MAP.get(name, name)
    if t == "union_type":
        named = [ch for ch in node.children if ch.is_named and ch.type != "comment"]
        coms = _type_comments(node)
        nulls = {"null", "undefined"}
        non_null = [ch for ch in named if ch.text.decode() not in nulls]
        if len(non_null) < len(named) and len(non_null) == 1:
            result = f"Option<{convert_type(non_null[0])}>"
        elif len(non_null) == 1:
            result = convert_type(non_null[0])
        else:
            result = "serde_json::Value"
        if coms:
            return "\n".join(coms) + "\n" + result
        return result
    if t == "intersection_type":
        return "serde_json::Value"
    if t == "parenthesized_type":
        named = [ch for ch in node.children if ch.is_named]
        return convert_type(named[0]) if named else "serde_json::Value"
    if t in ("literal_type", "template_literal_type"):
        return "String"
    if t == "tuple_type":
        named = [ch for ch in node.children if ch.is_named]
        parts = ", ".join(convert_type(m) for m in named)
        return f"({parts})" if named else "()"
    if t in ("object_type", "mapped_type", "index_signature", "conditional_type"):
        coms = _type_comments(node)
        result = "serde_json::Value"
        if coms:
            return "\n".join(coms) + "\n" + result
        return result
    if t == "function_type":
        return "Box<dyn Fn() -> serde_json::Value>"
    if t == "type_annotation":
        named = [ch for ch in node.children if ch.is_named]
        return convert_type(named[0]) if named else "serde_json::Value"
    return _TYPE_MAP.get(tx, "serde_json::Value")
