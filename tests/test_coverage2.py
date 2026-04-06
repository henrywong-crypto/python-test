"""Targeted tests to reach 95% coverage on remaining uncovered lines."""

from __future__ import annotations

from convert_typescript_to_rust import convert_file
from convert_typescript_to_rust.converter import c
from convert_typescript_to_rust.types import convert_type


class TestConverterNone:
    """Test c(None) returns empty string."""

    def test_none_node(self) -> None:
        assert c(None) == ""


class TestStringFragment:
    """Test string_fragment and escape_sequence nodes."""

    def test_escape_in_template(self) -> None:
        result = convert_file(r"const s = `hello\nworld`;", "t.ts")
        assert "hello" in result


class TestConverterFallback:
    """Tests for uncommon/fallback node types in converter."""

    def test_string_single_to_double(self) -> None:
        result = convert_file("const x = 'it\\'s';", "t.ts")
        assert '"' in result

    def test_binary_with_trailing_comment(self) -> None:
        result = convert_file("const x = a + b; // sum", "t.ts")
        assert "a + b" in result

    def test_unary_not_on_call(self) -> None:
        result = convert_file("if (!isValid()) { }", "t.ts")
        assert "!" in result or "is_none" in result

    def test_update_postfix(self) -> None:
        result = convert_file("function f() { let x = 0; return x++; }", "t.ts")
        assert "_v" in result or "+= 1" in result

    def test_assignment_expression(self) -> None:
        result = convert_file("x = y;", "t.ts")
        assert "x = y;" in result

    def test_await_expression(self) -> None:
        result = convert_file("async function f() { const x = await something(); }", "t.ts")
        assert ".await" in result

    def test_pair_in_object(self) -> None:
        result = convert_file('const o = { "key": 42 };', "t.ts")
        assert '"key": 42' in result

    def test_type_assertion(self) -> None:
        result = convert_file("const x = <string>val;", "t.tsx")
        # type assertion should be dropped
        assert "val" in result

    def test_empty_argument_node(self) -> None:
        result = convert_file("func();", "t.ts")
        assert "func()" in result

    def test_import_statement(self) -> None:
        result = convert_file("import { x } from 'y'; const z = 1;", "t.ts")
        assert "import" not in result
        assert "let z = 1;" in result


class TestTypeConversions:
    """Additional tests for convert_type covering uncovered branches."""

    def test_generic_with_args_unknown(self) -> None:
        # Custom generic: MyType<A>
        result = convert_file("let x: MyType<string>;", "t.ts")
        assert "MyType<String>" in result

    def test_generic_no_args(self) -> None:
        # Generic with no type arguments resolves to the type name
        result = convert_file("let x: SomeType;", "t.ts")
        assert "SomeType" in result or "some_type" in result

    def test_union_single_non_null(self) -> None:
        # Union of just one type (no null)
        result = convert_file("let x: string | string;", "t.ts")
        assert "serde_json::Value" in result or "String" in result

    def test_parenthesized_type(self) -> None:
        result = convert_file("let x: (string);", "t.ts")
        assert "String" in result

    def test_object_type(self) -> None:
        result = convert_file("let x: { a: string };", "t.ts")
        assert "serde_json::Value" in result

    def test_conditional_type(self) -> None:
        result = convert_file("type X = T extends string ? string : number;", "t.ts")
        assert "serde_json::Value" in result or "String" in result

    def test_function_type(self) -> None:
        result = convert_file("let x: () => void;", "t.ts")
        assert "Fn" in result or "dyn" in result

    def test_readonly(self) -> None:
        result = convert_file("let x: Readonly<User>;", "t.ts")
        assert "User" in result

    def test_set_generic(self) -> None:
        result = convert_file("let x: Set<number>;", "t.ts")
        assert "HashSet<f64>" in result

    def test_empty_tuple(self) -> None:
        result = convert_file("let x: [];", "t.ts")
        assert "()" in result or "vec!" in result


class TestDeclarationsCoverage:
    """Additional tests for declarations coverage."""

    def test_comment_in_params(self) -> None:
        result = convert_file("function f(/* a */ x: number) { }", "t.ts")
        assert "/* a */" in result or "x: f64" in result

    def test_rest_parameter(self) -> None:
        result = convert_file("function f(...args: number[]) { }", "t.ts")
        assert "&[" in result

    def test_optional_param_with_default(self) -> None:
        result = convert_file("function f(x: string = 'hi') { }", "t.ts")
        assert "x: &str" in result

    def test_optional_param_no_default(self) -> None:
        result = convert_file("function f(x?: number) { }", "t.ts")
        assert "Option<f64>" in result

    def test_class_with_comments(self) -> None:
        result = convert_file("class A { // A comment\nx: number; }", "t.ts")
        assert "// A comment" in result

    def test_interface_with_method_signature(self) -> None:
        result = convert_file("interface I { greet(name: string): void; }", "t.ts")
        # method signatures in interfaces are treated as property signatures or ignored
        assert "pub struct I" in result

    def test_type_alias_with_comment(self) -> None:
        result = convert_file("// type doc\ntype X = string;", "t.ts")
        assert "// type doc" in result

    def test_enum_member_single(self) -> None:
        result = convert_file("enum E { One }", "t.ts")
        assert "One," in result

    def test_export_const_no_value(self) -> None:
        result = convert_file("export const X: string;", "t.ts")
        # No value assigned -- should still produce something
        assert "X" in result or "pub const" in result


class TestExpressionsCoverage:
    """Additional tests for expressions.py coverage."""

    def test_arrow_body_expression(self) -> None:
        result = convert_file("const f = () => 42;", "t.ts")
        assert "|| 42" in result

    def test_object_with_spread_element(self) -> None:
        result = convert_file("const x = { ...other };", "t.ts")
        assert "..other" in result

    def test_object_shorthand(self) -> None:
        result = convert_file("const obj = { name };", "t.ts")
        assert '"name": name' in result

    def test_arrow_multiple_params(self) -> None:
        result = convert_file("const f = (a: number, b: number) => a + b;", "t.ts")
        assert "|a, b|" in result

    def test_extract_inline_fn_expression_body(self) -> None:
        result = convert_file("const obj = { calc: (x: number) => x * 2 };", "t.ts")
        assert "|x| x * 2" in result

    def test_object_method_async(self) -> None:
        result = convert_file("const obj = { async load() { return 1; } };", "t.ts")
        assert "pub async fn load" in result


class TestStatementsCoverage:
    """Additional tests for statements.py coverage."""

    def test_destructuring_pair_pattern(self) -> None:
        result = convert_file("const { name: localName } = obj;", "t.ts")
        assert "local_name" in result

    def test_var_decl_comment(self) -> None:
        result = convert_file("let /* x comment */ x = 1;", "t.ts")
        assert "x" in result

    def test_switch_default_only(self) -> None:
        result = convert_file("switch (x) { default: doSomething(); }", "t.ts")
        assert "_ =>" in result

    def test_try_no_catch_only_finally(self) -> None:
        result = convert_file("try { f(); } finally { cleanup(); }", "t.ts")
        assert "cleanup" in result


class TestConverterEdgeCases:
    """Edge cases in the converter."""

    def test_delete_expression(self) -> None:
        result = convert_file("delete obj.prop;", "t.ts")
        assert ".take()" in result

    def test_void_expression(self) -> None:
        result = convert_file("void 0;", "t.ts")
        assert "let _ =" in result

    def test_type_identifier_known(self) -> None:
        # Directly accessing type_identifier path for a known type
        result = convert_file("interface I { x: Date; }", "t.ts")
        assert "String" in result

    def test_member_access_with_comment(self) -> None:
        result = convert_file("obj.prop; // access", "t.ts")
        assert "// access" in result or "obj.prop" in result

    def test_jsx_opening_tag(self) -> None:
        result = convert_file("const el = <Comp />;", "t.tsx")
        assert "// JSX" in result

    def test_error_node_with_comment(self) -> None:
        result = convert_file("@@@ /* error comment */ @@@;", "t.ts")
        assert "error" in result.lower() or "comment" in result

    def test_non_null_expression(self) -> None:
        result = convert_file("const x = y!.z;", "t.ts")
        assert ".unwrap()" in result


class TestBenchmarkEdgeCases:
    """Edge cases in benchmark module."""

    def test_benchmark_tsx_file(self) -> None:
        import tempfile
        from pathlib import Path
        from convert_typescript_to_rust.benchmark import benchmark_file

        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "test.tsx"
            p.write_text("const el = <div></div>;")
            result = benchmark_file(str(p))
            assert result["ts_ast_nodes"] > 0


class TestMainModule:
    """Test __main__ module can be invoked."""

    def test_main_import(self) -> None:
        from convert_typescript_to_rust import __main__
        assert hasattr(__main__, "main")


class TestInitConverts:
    """Test __init__ module convert_directory with tsx and subdirs."""

    def test_convert_directory_empty(self) -> None:
        import tempfile
        from pathlib import Path
        from convert_typescript_to_rust import convert_directory

        with tempfile.TemporaryDirectory() as td:
            ts_dir = Path(td) / "src"
            rs_dir = Path(td) / "out"
            ts_dir.mkdir()
            count = convert_directory(str(ts_dir), str(rs_dir))
            assert count == 0


class TestParamsEdge:
    """Parameter edge cases."""

    def test_no_params(self) -> None:
        result = convert_file("function f() { }", "t.ts")
        assert "pub fn f()" in result

    def test_class_method_no_params(self) -> None:
        result = convert_file("class A { doIt() { } }", "t.ts")
        assert "pub fn do_it(&self)" in result
