"""Tests for comment preservation: top-level, inline, trailing, in objects, arrays, enums, interfaces, JSX."""

from __future__ import annotations

from convert_typescript_to_rust import convert_file


class TestTopLevelComments:
    """Tests for top-level comment preservation."""

    def test_single_line_comment(self) -> None:
        result = convert_file("// This is a comment\nconst x = 1;", "t.ts")
        assert "// This is a comment" in result

    def test_multiline_comment(self) -> None:
        result = convert_file("/* multi\nline */\nconst x = 1;", "t.ts")
        assert "/* multi\nline */" in result


class TestTrailingComments:
    """Tests for trailing comment preservation."""

    def test_trailing_on_statement(self) -> None:
        result = convert_file("const x = 1; // trailing", "t.ts")
        assert "// trailing" in result


class TestCommentInEnum:
    """Tests for comments inside enums."""

    def test_enum_comment(self) -> None:
        result = convert_file("enum E { A, /* note */ B }", "t.ts")
        assert "/* note */" in result


class TestCommentInInterface:
    """Tests for comments inside interfaces."""

    def test_interface_comment(self) -> None:
        result = convert_file("interface I { /* field comment */ name: string; }", "t.ts")
        assert "/* field comment */" in result


class TestCommentInArray:
    """Tests for comments inside arrays."""

    def test_array_comment(self) -> None:
        result = convert_file("const arr = [1, /* mid */ 2];", "t.ts")
        assert "/* mid */" in result


class TestCommentInObject:
    """Tests for comments inside object literals."""

    def test_object_comment(self) -> None:
        result = convert_file('const obj = { /* c */ key: "val" };', "t.ts")
        assert "/* c */" in result


class TestJSXComments:
    """Tests for comments inside JSX."""

    def test_jsx_preserves_comment(self) -> None:
        result = convert_file(
            "const el = <div>{/* JSX comment */}</div>;",
            "t.tsx",
        )
        assert "/* JSX comment */" in result

    def test_jsx_to_comment(self) -> None:
        result = convert_file("const el = <div></div>;", "t.tsx")
        assert "// JSX" in result
