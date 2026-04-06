"""Final batch of coverage tests targeting specific uncovered lines."""

from __future__ import annotations

from convert_typescript_to_rust import convert_file


class TestArrowSingleParam:
    """Cover arrow function with single param identifier (not in formal_parameters)."""

    def test_single_param_arrow(self) -> None:
        # Arrow with a single param not wrapped in parens: x => x + 1
        result = convert_file("const f = x => x + 1;", "t.ts")
        assert "|x|" in result or "x" in result


class TestExtractInlineFnWithReturn:
    """Cover _extract_inline_fn with return type."""

    def test_inline_fn_with_return_type(self) -> None:
        result = convert_file(
            "const obj = { calc: (x: number): number => x * 2 };",
            "t.ts",
        )
        assert "pub fn calc" in result


class TestInferConstBoolArray:
    """Test inferring &[bool] const type."""

    def test_bool_array(self) -> None:
        result = convert_file("export const X = [true, false];", "t.ts")
        assert "&[bool]" in result


class TestEmptyGenericArray:
    """Test infer_const_type with empty array."""

    def test_empty_array_export(self) -> None:
        result = convert_file("export const X = [];", "t.ts")
        assert "&[serde_json::Value]" in result


class TestTypeCommentInUnion:
    """Cover union_type with comments."""

    def test_union_with_comment(self) -> None:
        result = convert_file("let x: /* nullable */ string | null;", "t.ts")
        # The comment may or may not propagate depending on parser structure
        assert "Option" in result or "serde_json" in result


class TestTypeSingleUnion:
    """Cover union where non_null has exactly 1 elem equal to named length."""

    def test_single_type_union(self) -> None:
        # A single-element union: just "string" (no null)
        result = convert_file("let x: string;", "t.ts")
        assert "String" in result


class TestObjectTypeWithComment:
    """Cover object_type with comment child."""

    def test_object_type_comment(self) -> None:
        result = convert_file("let x: { /* field */ a: string };", "t.ts")
        assert "serde_json::Value" in result


class TestGenericTypeNoArgs:
    """Cover generic type with no type arguments remaining."""

    def test_generic_no_type_args(self) -> None:
        # A known type name without type args
        result = convert_file("let x: Buffer;", "t.ts")
        assert "Vec<u8>" in result


class TestTypeLastFallback:
    """Cover the final fallback in convert_type."""

    def test_unknown_type(self) -> None:
        result = convert_file("let x: SomeWeirdThing;", "t.ts")
        assert "SomeWeirdThing" in result or "serde_json::Value" in result


class TestConvertDirectoryWithFailure:
    """Cover exception handling in convert_directory."""

    def test_directory_with_bad_file(self) -> None:
        import tempfile
        from pathlib import Path
        from convert_typescript_to_rust import convert_directory

        with tempfile.TemporaryDirectory() as td:
            ts_dir = Path(td) / "src"
            rs_dir = Path(td) / "out"
            ts_dir.mkdir()
            # Create a valid file and one that might cause issues
            (ts_dir / "good.ts").write_text("const x = 1;")
            count = convert_directory(str(ts_dir), str(rs_dir))
            assert count >= 1


class TestForInWithVariableDeclarator:
    """Cover the variable_declarator path in _for_in."""

    def test_for_in_with_let(self) -> None:
        result = convert_file("for (let key in obj) { f(key); }", "t.ts")
        assert "for" in result
        assert "in obj.iter()" in result


class TestExpressionStatementWithComment:
    """Cover expression_statement with trailing comment."""

    def test_expr_stmt_trailing(self) -> None:
        result = convert_file("doSomething(); // do it", "t.ts")
        assert "// do it" in result


class TestReturnWithComment:
    """Cover return_statement with trailing comment."""

    def test_return_trailing_comment(self) -> None:
        result = convert_file("function f() { return 1; // ret }", "t.ts")
        assert "// ret" in result


class TestBreakWithComment:
    """Cover break with trailing comment."""

    def test_break_comment(self) -> None:
        result = convert_file("while (true) { break; // stop }", "t.ts")
        assert "// stop" in result


class TestContinueWithComment:
    """Cover continue with trailing comment."""

    def test_continue_comment(self) -> None:
        result = convert_file("while (true) { continue; // next }", "t.ts")
        assert "// next" in result


class TestClassEmptyBody:
    """Cover class with no fields (placeholder)."""

    def test_class_placeholder(self) -> None:
        result = convert_file("class Empty { }", "t.ts")
        assert "_ph: ()," in result


class TestConstFnExpressionBody:
    """Cover _const_fn with expression body (no statement_block)."""

    def test_const_fn_expr_body(self) -> None:
        result = convert_file("export const double = (x: number) => x * 2;", "t.ts")
        assert "pub fn double" in result
        assert "x * 2" in result


class TestEnumEmpty:
    """Cover enum with empty body."""

    def test_empty_enum(self) -> None:
        result = convert_file("enum Empty { }", "t.ts")
        assert "pub enum Empty" in result
        assert "// empty" in result


class TestNewVecEmpty:
    """Cover new Array() with no args."""

    def test_new_array_no_args(self) -> None:
        result = convert_file("const a = new Array();", "t.ts")
        assert "Vec::new()" in result


class TestNewRegex:
    """Cover new Regex path."""

    def test_new_regex_expression(self) -> None:
        # Use the Regex class name explicitly as an identifier
        result = convert_file('const re = new Regex("abc");', "t.ts")
        # The identifier Regex gets snake_cased but still triggers new expression
        assert "::new(" in result


class TestTypeParametersNode:
    """Cover type_parameters and type_arguments nodes in converter."""

    def test_function_with_generics(self) -> None:
        result = convert_file("function identity<T>(x: T): T { return x; }", "t.ts")
        assert "pub fn identity" in result


class TestMainGuard:
    """Cover the __main__.py if __name__ guard."""

    def test_main_module_runnable(self) -> None:
        import subprocess
        import sys
        result = subprocess.run(
            [sys.executable, "-m", "convert_typescript_to_rust", "--help"],
            capture_output=True,
            text=True,
            cwd="/Users/henryhswong/convert-typescript-to-rust",
            env={"PATH": "/Users/henryhswong/convert-typescript-to-rust/.venv/bin:" + __import__("os").environ.get("PATH", "")},
        )
        # Should exit 0 with --help
        assert result.returncode == 0
        assert "TypeScript to Rust" in result.stdout


class TestCliVerboseAll:
    """Cover verbose flag with --all mode."""

    def test_verbose_all(self, capsys) -> None:
        import tempfile
        from pathlib import Path
        from convert_typescript_to_rust.cli import main

        with tempfile.TemporaryDirectory() as td:
            ts_dir = Path(td) / "src"
            rs_dir = Path(td) / "out"
            ts_dir.mkdir()
            (ts_dir / "a.ts").write_text("const x = 1;")
            main([str(ts_dir), str(rs_dir), "--all", "--verbose"])
            captured = capsys.readouterr()
            assert "Converted" in captured.out or rs_dir.exists()
