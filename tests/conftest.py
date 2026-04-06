"""Shared test fixtures for the convert-typescript-to-rust test suite."""

from __future__ import annotations

import pytest
from tree_sitter import Language, Parser, Node
import tree_sitter_typescript as ts_lang

TS_LANGUAGE = Language(ts_lang.language_typescript())
TSX_LANGUAGE = Language(ts_lang.language_tsx())


@pytest.fixture()
def parse():
    """Return a helper that parses TypeScript source and returns the root node."""

    def _parse(source: str, *, tsx: bool = False) -> Node:
        lang = TSX_LANGUAGE if tsx else TS_LANGUAGE
        parser = Parser(lang)
        tree = parser.parse(source.encode("utf-8"))
        return tree.root_node

    return _parse


@pytest.fixture()
def first_named(parse):
    """Return a helper that parses source and returns the first named child."""

    def _first(source: str, *, tsx: bool = False) -> Node:
        root = parse(source, tsx=tsx)
        for ch in root.children:
            if ch.is_named:
                return ch
        raise ValueError("No named child found")

    return _first
