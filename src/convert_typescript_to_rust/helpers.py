"""Helper utilities for name conversion and text processing.

Small pure-function helpers used across the converter modules.
"""

from __future__ import annotations

import re

from .types import _RUST_KEYWORDS, _TYPE_MAP


def _snake(name: str) -> str:
    """Convert a camelCase or PascalCase name to snake_case.

    Args:
        name: The identifier to convert.

    Returns:
        The snake_case version of *name*.
    """
    name = name.replace("-", "_")
    s = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1_\2", name)
    s = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", s)
    return s.lower()


def _screaming(name: str) -> str:
    """Convert a name to SCREAMING_SNAKE_CASE.

    Args:
        name: The identifier to convert.

    Returns:
        The SCREAMING_SNAKE_CASE version of *name*.
    """
    return _snake(name).upper()


def _safe_field(name: str) -> str:
    """Escape Rust keywords used as field names with ``r#`` prefix.

    Args:
        name: The field name to check.

    Returns:
        The escaped field name if it is a Rust keyword, otherwise unchanged.
    """
    if name in _RUST_KEYWORDS:
        return f"r#{name}"
    return name


def _ident(name: str) -> str:
    """Convert a TypeScript identifier to its Rust equivalent.

    Well-known identifiers (``console``, ``Math``, ``JSON``, etc.) are mapped
    to their Rust counterparts; everything else is snake_cased.

    Args:
        name: The TypeScript identifier text.

    Returns:
        The Rust identifier string.
    """
    if name == "console":
        return "tracing"
    if name == "JSON":
        return "serde_json"
    if name == "Math":
        return "f64"
    if name == "Object":
        return "serde_json::Value"
    if name == "Array":
        return "Vec"
    if name == "Map":
        return "std::collections::HashMap"
    if name == "Set":
        return "std::collections::HashSet"
    if name == "parseInt":
        return "i64::from_str_radix"
    if name == "parseFloat":
        return "f64::from_str"
    if name == "process":
        return "std::process"
    if name == "Date":
        return "Date"
    if name == "Symbol":
        return "symbol"
    return _snake(name)


def _strip_parens(s: str) -> str:
    """Remove a single layer of surrounding parentheses if present.

    Args:
        s: The string to unwrap.

    Returns:
        The string without the outermost matching parentheses.
    """
    s = s.strip()
    if s.startswith("(") and s.endswith(")"):
        return s[1:-1]
    return s


def _trailing_comments(node: object) -> str:
    """Extract comment children from a tree-sitter *node*.

    Args:
        node: A tree-sitter ``Node``.

    Returns:
        A space-joined string of comment texts, or ``""`` if none.
    """
    comments: list[str] = []
    for ch in node.children:  # type: ignore[attr-defined]
        if ch.type == "comment":
            comments.append(ch.text.decode())
    return " ".join(comments) if comments else ""


def _rust_num(text: str) -> str:
    """Emit a numeric literal that works in an f64 context.

    Args:
        text: The raw numeric text from the TypeScript source.

    Returns:
        The Rust-friendly numeric literal string.
    """
    if "." in text or "e" in text.lower():
        return text
    return text + ".0"
