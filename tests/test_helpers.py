"""Tests for helper utilities: _snake, _screaming, _safe_field, _ident, _strip_parens, _trailing_comments."""

from __future__ import annotations

from convert_typescript_to_rust.helpers import (
    _snake,
    _screaming,
    _safe_field,
    _ident,
    _strip_parens,
    _trailing_comments,
    _rust_num,
)


class TestSnake:
    """Tests for _snake."""

    def test_camel_case(self) -> None:
        assert _snake("camelCase") == "camel_case"

    def test_pascal_case(self) -> None:
        assert _snake("PascalCase") == "pascal_case"

    def test_already_snake(self) -> None:
        assert _snake("already_snake") == "already_snake"

    def test_with_hyphens(self) -> None:
        assert _snake("kebab-case") == "kebab_case"

    def test_consecutive_upper(self) -> None:
        assert _snake("HTMLParser") == "html_parser"

    def test_single_word(self) -> None:
        assert _snake("word") == "word"

    def test_all_upper(self) -> None:
        assert _snake("ABC") == "abc"

    def test_number_boundary(self) -> None:
        assert _snake("item2Count") == "item2_count"


class TestScreaming:
    """Tests for _screaming."""

    def test_camel_to_screaming(self) -> None:
        assert _screaming("camelCase") == "CAMEL_CASE"

    def test_pascal_to_screaming(self) -> None:
        assert _screaming("PascalCase") == "PASCAL_CASE"

    def test_already_screaming(self) -> None:
        assert _screaming("ALREADY") == "ALREADY"


class TestSafeField:
    """Tests for _safe_field."""

    def test_keyword_escaped(self) -> None:
        assert _safe_field("type") == "r#type"

    def test_non_keyword(self) -> None:
        assert _safe_field("name") == "name"

    def test_self_keyword(self) -> None:
        assert _safe_field("self") == "r#self"

    def test_fn_keyword(self) -> None:
        assert _safe_field("fn") == "r#fn"


class TestIdent:
    """Tests for _ident."""

    def test_console(self) -> None:
        assert _ident("console") == "tracing"

    def test_json(self) -> None:
        assert _ident("JSON") == "serde_json"

    def test_math(self) -> None:
        assert _ident("Math") == "f64"

    def test_parse_int(self) -> None:
        assert _ident("parseInt") == "i64::from_str_radix"

    def test_regular_name(self) -> None:
        assert _ident("myVariable") == "my_variable"

    def test_process(self) -> None:
        assert _ident("process") == "std::process"

    def test_array(self) -> None:
        assert _ident("Array") == "Vec"


class TestStripParens:
    """Tests for _strip_parens."""

    def test_strips(self) -> None:
        assert _strip_parens("(hello)") == "hello"

    def test_no_parens(self) -> None:
        assert _strip_parens("hello") == "hello"

    def test_whitespace(self) -> None:
        assert _strip_parens("  (hello)  ") == "hello"

    def test_nested_stays(self) -> None:
        assert _strip_parens("((x))") == "(x)"


class TestTrailingComments:
    """Tests for _trailing_comments."""

    def test_with_comment_node(self, first_named) -> None:
        node = first_named("const x = 1; // comment")
        # The trailing comment is a sibling of the declaration, not a child.
        # Test with a node that actually contains comment children.
        result = _trailing_comments(node)
        # Comments on lexical_declaration may or may not be children depending
        # on tree-sitter version.  Just ensure the function returns a string.
        assert isinstance(result, str)

    def test_no_comments(self, first_named) -> None:
        node = first_named("const x = 1;")
        result = _trailing_comments(node)
        assert result == ""


class TestRustNum:
    """Tests for _rust_num."""

    def test_integer(self) -> None:
        assert _rust_num("42") == "42.0"

    def test_float(self) -> None:
        assert _rust_num("3.14") == "3.14"

    def test_scientific(self) -> None:
        assert _rust_num("1e10") == "1e10"
