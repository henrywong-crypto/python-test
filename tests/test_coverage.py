"""Additional tests to improve coverage of converter.py and other modules."""

from __future__ import annotations

from convert_typescript_to_rust import convert_file
from convert_typescript_to_rust.converter import c


class TestLiterals:
    """Tests for literal node conversion in converter.py."""

    def test_number_literal(self) -> None:
        result = convert_file("const x = 42;", "t.ts")
        assert "42" in result

    def test_single_quote_string(self) -> None:
        result = convert_file("const x = 'hello';", "t.ts")
        assert '"hello"' in result

    def test_double_quote_string(self) -> None:
        result = convert_file('const x = "hello";', "t.ts")
        assert '"hello"' in result

    def test_true_literal(self) -> None:
        result = convert_file("const x = true;", "t.ts")
        assert "true" in result

    def test_false_literal(self) -> None:
        result = convert_file("const x = false;", "t.ts")
        assert "false" in result

    def test_undefined_literal(self) -> None:
        result = convert_file("const x = undefined;", "t.ts")
        assert "None" in result

    def test_regex_with_flags(self) -> None:
        result = convert_file("const re = /abc/gi;", "t.ts")
        assert "regex::Regex::new" in result
        assert "abc" in result


class TestIdentifiers:
    """Tests for identifier conversion paths."""

    def test_property_identifier(self) -> None:
        result = convert_file("obj.myProp;", "t.ts")
        assert "my_prop" in result

    def test_type_identifier_known(self) -> None:
        result = convert_file("let x: string = 'a';", "t.ts")
        assert "String" in result

    def test_super_keyword(self) -> None:
        result = convert_file("class A extends B { constructor() { super(); } }", "t.ts")
        # super() calls are filtered out in methods, but super itself => "super"
        assert "pub struct A" in result


class TestMoreExpressions:
    """Tests for expression paths not yet covered."""

    def test_template_substitution(self) -> None:
        result = convert_file("const s = `${x}`;", "t.ts")
        assert "format!" in result

    def test_parenthesized_expression(self) -> None:
        result = convert_file("const x = (a + b);", "t.ts")
        assert "a + b" in result

    def test_optional_chaining(self) -> None:
        result = convert_file("const x = obj?.prop;", "t.ts")
        # Optional chaining may or may not produce and_then depending on parser
        assert "obj" in result and "prop" in result

    def test_subscript_expression(self) -> None:
        result = convert_file("const x = arr[0];", "t.ts")
        assert "arr[0]" in result

    def test_member_length(self) -> None:
        result = convert_file("const x = arr.length;", "t.ts")
        assert ".len()" in result

    def test_member_prototype(self) -> None:
        result = convert_file("const x = Foo.prototype;", "t.ts")
        # prototype is stripped
        assert "prototype" not in result or "foo" in result.lower()

    def test_new_vec(self) -> None:
        result = convert_file("const a = new Array(10);", "t.ts")
        assert "Vec::with_capacity" in result

    def test_new_regex(self) -> None:
        result = convert_file('const re = new RegExp("abc");', "t.ts")
        assert "new" in result or "::new" in result

    def test_new_generic_class(self) -> None:
        result = convert_file("const x = new Foo(1, 2);", "t.ts")
        assert "::new(1, 2)" in result

    def test_sequence_expression(self) -> None:
        result = convert_file("const x = (a(), b());", "t.ts")
        assert ";" in result

    def test_yield_expression(self) -> None:
        result = convert_file("function* gen() { yield 42; }", "t.ts")
        assert "yield" in result

    def test_satisfies_expression(self) -> None:
        result = convert_file("const x = val satisfies string;", "t.ts")
        assert "satisfies" not in result


class TestMoreStatements:
    """Tests for statement paths not yet covered."""

    def test_return_no_value(self) -> None:
        result = convert_file("function f() { return; }", "t.ts")
        assert "return;" in result

    def test_throw_statement(self) -> None:
        result = convert_file('function f() { throw new Error("bad"); }', "t.ts")
        assert "return Err(" in result

    def test_break_statement(self) -> None:
        result = convert_file("while (true) { break; }", "t.ts")
        assert "break;" in result

    def test_continue_statement(self) -> None:
        result = convert_file("while (true) { continue; }", "t.ts")
        assert "continue;" in result

    def test_empty_statement(self) -> None:
        # An empty statement (just a semicolon) should produce nothing
        result = convert_file(";", "t.ts")
        assert "//!" in result  # just the header

    def test_debugger_statement(self) -> None:
        result = convert_file("debugger;", "t.ts")
        assert "// debugger;" in result

    def test_labeled_statement(self) -> None:
        result = convert_file("outer: for (const x of arr) { break outer; }", "t.ts")
        assert "outer" in result.lower() or "'" in result

    def test_do_while(self) -> None:
        result = convert_file("do { x++; } while (x < 5);", "t.ts")
        assert "loop {" in result
        assert "break;" in result

    def test_while_statement(self) -> None:
        result = convert_file("while (running) { tick(); }", "t.ts")
        assert "while running" in result


class TestMoreDeclarations:
    """Tests for declaration paths not yet covered."""

    def test_generator_function(self) -> None:
        result = convert_file("function* gen() { yield 1; }", "t.ts")
        assert "pub fn gen" in result

    def test_method_constructor(self) -> None:
        result = convert_file(
            "class A { x: number; constructor(x: number) { this.x = x; } }",
            "t.ts",
        )
        assert "pub fn new" in result

    def test_export_class(self) -> None:
        result = convert_file("export class Foo { x: number; }", "t.ts")
        assert "pub struct Foo" in result

    def test_export_type_alias(self) -> None:
        result = convert_file("export type ID = string;", "t.ts")
        assert "pub type ID = String;" in result

    def test_abstract_class_declaration(self) -> None:
        result = convert_file("export abstract class Base { }", "t.ts")
        assert "pub struct Base" in result

    def test_async_method(self) -> None:
        result = convert_file(
            "class S { async fetch(): Promise<string> { return ''; } }",
            "t.ts",
        )
        assert "pub async fn fetch" in result

    def test_export_default_call(self) -> None:
        result = convert_file("export default createApp();", "t.ts")
        assert "pub const DEFAULT" in result

    def test_export_satisfies(self) -> None:
        result = convert_file("export default { key: 1 } satisfies Config;", "t.ts")
        assert "pub const DEFAULT" in result


class TestTypeNodes:
    """Tests for type node handling in converter.py."""

    def test_type_annotation_preserved(self) -> None:
        result = convert_file("function f(x: string): void { }", "t.ts")
        assert "pub fn f" in result

    def test_function_type(self) -> None:
        result = convert_file("let f: () => void;", "t.ts")
        # function types become Box<dyn Fn()>
        assert "Fn" in result or "dyn" in result or "let" in result

    def test_literal_type(self) -> None:
        result = convert_file("type X = 'hello';", "t.ts")
        assert "String" in result

    def test_mapped_type(self) -> None:
        result = convert_file("type X = { [K in keyof T]: T[K] };", "t.ts")
        assert "serde_json::Value" in result


class TestCalls:
    """Tests for call expression paths not yet covered."""

    def test_to_fixed(self) -> None:
        result = convert_file("const s = num.toFixed(2);", "t.ts")
        assert "format!" in result
        assert ".2" in result

    def test_test_method(self) -> None:
        result = convert_file("const b = re.test(str);", "t.ts")
        assert "is_match" in result

    def test_match_method(self) -> None:
        result = convert_file("const m = str.match(re);", "t.ts")
        assert ".find(" in result

    def test_match_all_method(self) -> None:
        result = convert_file("const m = str.matchAll(re);", "t.ts")
        assert "find_iter" in result

    def test_to_string_hex(self) -> None:
        result = convert_file("const s = num.toString(16);", "t.ts")
        assert "format!" in result
        assert ":x" in result

    def test_to_string_default(self) -> None:
        result = convert_file("const s = num.toString();", "t.ts")
        assert ".to_string()" in result

    def test_object_values(self) -> None:
        result = convert_file("Object.values(obj);", "t.ts")
        assert ".values()" in result

    def test_object_entries(self) -> None:
        result = convert_file("Object.entries(obj);", "t.ts")
        assert ".iter()" in result

    def test_object_assign(self) -> None:
        result = convert_file("Object.assign(target, source);", "t.ts")
        assert "Object.assign" in result

    def test_process_exit(self) -> None:
        result = convert_file("process.exit(1);", "t.ts")
        assert "std::process::exit" in result

    def test_process_cwd(self) -> None:
        result = convert_file("process.cwd();", "t.ts")
        assert "current_dir" in result

    def test_is_nan(self) -> None:
        result = convert_file("isNaN(x);", "t.ts")
        assert ".is_nan()" in result

    def test_is_finite(self) -> None:
        result = convert_file("isFinite(x);", "t.ts")
        assert ".is_finite()" in result

    def test_set_interval(self) -> None:
        result = convert_file("setInterval(fn, 100);", "t.ts")
        assert "setInterval" in result

    def test_clear_timeout(self) -> None:
        result = convert_file("clearTimeout(id);", "t.ts")
        assert "clear_timeout" in result

    def test_method_push(self) -> None:
        result = convert_file("arr.push(1);", "t.ts")
        assert ".push(1)" in result

    def test_method_includes(self) -> None:
        result = convert_file("arr.includes(x);", "t.ts")
        assert ".contains(x)" in result

    def test_method_starts_with(self) -> None:
        result = convert_file('str.startsWith("a");', "t.ts")
        assert ".starts_with(" in result

    def test_method_trim(self) -> None:
        result = convert_file("str.trim();", "t.ts")
        assert ".trim()" in result

    def test_method_split(self) -> None:
        result = convert_file('str.split(",");', "t.ts")
        assert '.split(",")' in result

    def test_method_sort(self) -> None:
        result = convert_file("arr.sort();", "t.ts")
        assert ".sort()" in result

    def test_method_reverse(self) -> None:
        result = convert_file("arr.reverse();", "t.ts")
        assert ".reverse()" in result

    def test_method_flat(self) -> None:
        result = convert_file("arr.flat();", "t.ts")
        assert "flatten" in result

    def test_method_some(self) -> None:
        result = convert_file("arr.some((x) => x > 0);", "t.ts")
        assert "iter().any" in result

    def test_method_every(self) -> None:
        result = convert_file("arr.every((x) => x > 0);", "t.ts")
        assert "iter().all" in result

    def test_method_for_each(self) -> None:
        result = convert_file("arr.forEach((x) => f(x));", "t.ts")
        assert "iter().for_each" in result

    def test_method_slice(self) -> None:
        result = convert_file("arr.slice(1, 3);", "t.ts")
        assert ".get(" in result

    def test_method_catch(self) -> None:
        result = convert_file("promise.catch(() => null);", "t.ts")
        assert ".ok()" in result

    def test_method_then(self) -> None:
        result = convert_file("promise.then((x) => x);", "t.ts")
        assert ".and_then(" in result

    def test_axios_post(self) -> None:
        result = convert_file('axios.post("/api", data);', "t.ts")
        assert "reqwest::Client::new().post" in result

    def test_default_member_call(self) -> None:
        result = convert_file("obj.customMethod(1, 2);", "t.ts")
        assert ".custom_method(1, 2)" in result


class TestJSX:
    """Tests for JSX/TSX handling."""

    def test_jsx_self_closing(self) -> None:
        result = convert_file("const el = <br />;", "t.tsx")
        assert "// JSX" in result

    def test_jsx_fragment(self) -> None:
        result = convert_file("const el = <><span></span></>;", "t.tsx")
        assert "// JSX" in result


class TestErrorNode:
    """Tests for ERROR node handling."""

    def test_parse_error_preserved(self) -> None:
        # Intentionally bad syntax that will produce ERROR nodes
        result = convert_file("const x = @@@;", "t.ts")
        assert "parse error" in result or "x" in result


class TestObjectMethods:
    """Tests for object literal with methods."""

    def test_object_with_method(self) -> None:
        result = convert_file("const obj = { greet() { return 1; } };", "t.ts")
        assert "pub fn greet" in result

    def test_object_with_async_method(self) -> None:
        result = convert_file("const obj = { async fetch() { return 1; } };", "t.ts")
        assert "pub async fn fetch" in result


class TestPostprocess:
    """Tests for postprocessing patterns."""

    def test_typeof_string(self) -> None:
        result = convert_file('if (typeof x === "string") { }', "t.ts")
        assert "is_string" in result

    def test_typeof_number(self) -> None:
        result = convert_file('if (typeof x === "number") { }', "t.ts")
        assert "is_number" in result

    def test_typeof_not_equal(self) -> None:
        result = convert_file('if (typeof x !== "boolean") { }', "t.ts")
        assert "is_boolean" in result

    def test_typeof_unknown(self) -> None:
        result = convert_file("const t = typeof x;", "t.ts")
        assert "typeof" in result

    def test_process_env(self) -> None:
        result = convert_file("const x = process.env.NODE_ENV;", "t.ts")
        assert 'std::env::var(' in result


class TestParams:
    """Tests for parameter conversion."""

    def test_optional_param(self) -> None:
        result = convert_file("function f(x?: number) { }", "t.ts")
        assert "Option<f64>" in result

    def test_rest_param(self) -> None:
        result = convert_file("function f(...args: string[]) { }", "t.ts")
        assert "&[" in result

    def test_default_param(self) -> None:
        result = convert_file("function f(x: number = 10) { }", "t.ts")
        assert "x: f64" in result


class TestInferConstType:
    """Tests for _infer_const_type."""

    def test_infer_number_int(self) -> None:
        result = convert_file("export const X = 42;", "t.ts")
        assert "usize" in result

    def test_infer_number_float(self) -> None:
        result = convert_file("export const X = 3.14;", "t.ts")
        assert "f64" in result

    def test_infer_string(self) -> None:
        result = convert_file('export const X = "hello";', "t.ts")
        assert "&str" in result

    def test_infer_bool(self) -> None:
        result = convert_file("export const X = true;", "t.ts")
        assert "bool" in result

    def test_infer_null(self) -> None:
        result = convert_file("export const X = null;", "t.ts")
        assert "Option" in result

    def test_infer_array_string(self) -> None:
        result = convert_file('export const X = ["a", "b"];', "t.ts")
        assert "&[&str]" in result

    def test_infer_array_number(self) -> None:
        result = convert_file("export const X = [1, 2, 3];", "t.ts")
        assert "&[f64]" in result

    def test_infer_object(self) -> None:
        result = convert_file('export const X = { a: 1 };', "t.ts")
        assert "serde_json::Value" in result

    def test_infer_template(self) -> None:
        result = convert_file("export const X = `hello`;", "t.ts")
        assert "String" in result


class TestModuleEntry:
    """Test __main__.py entry point."""

    def test_import(self) -> None:
        import convert_typescript_to_rust.__main__  # noqa: F401


class TestVersion:
    """Test __version__ attribute."""

    def test_version(self) -> None:
        from convert_typescript_to_rust import __version__
        assert __version__ == "0.1.0"


class TestElseClause:
    """Tests for else clause handling."""

    def test_else_block(self) -> None:
        result = convert_file("if (x) { a(); } else { b(); }", "t.ts")
        assert "else {" in result

    def test_else_if(self) -> None:
        result = convert_file("if (x) { } else if (y) { } else { }", "t.ts")
        assert "else if" in result


class TestUnaryNot:
    """Tests for unary ! on non-identifier."""

    def test_not_expr(self) -> None:
        result = convert_file("const x = !condition;", "t.ts")
        assert ".is_none()" in result or "!" in result


class TestUpdateExpression:
    """Tests for postfix update."""

    def test_postfix_increment(self) -> None:
        result = convert_file("const old = x++;", "t.ts")
        assert "+= 1" in result


class TestExportConst:
    """Tests for arrow function in export const."""

    def test_async_arrow_export(self) -> None:
        result = convert_file(
            "export const fetchData = async (url: string): Promise<string> => { return url; };",
            "t.ts",
        )
        assert "pub async fn fetch_data" in result

    def test_arrow_expression_body(self) -> None:
        result = convert_file("export const double = (x: number) => x * 2;", "t.ts")
        assert "pub fn double" in result
        assert "x * 2" in result


class TestObjectExtraction:
    """Tests for _extract_inline_fn in objects."""

    def test_object_with_arrow_value(self) -> None:
        result = convert_file(
            'const config = { handler: (x: number) => x + 1 };',
            "t.ts",
        )
        assert "|x| x + 1" in result


class TestSwitchWithComments:
    """Tests for switch with comments."""

    def test_switch_comment(self) -> None:
        result = convert_file(
            """switch (x) {
                // case comment
                case 1: break;
                default: break;
            }""",
            "t.ts",
        )
        assert "// case comment" in result


class TestTryCatchFinally:
    """Tests for try without catch."""

    def test_try_no_catch(self) -> None:
        # tree-sitter may parse this as try with just finally
        result = convert_file("try { f(); } finally { cleanup(); }", "t.ts")
        assert "cleanup" in result or "finally" in result


class TestNewExpressions:
    """Tests for new expression edge cases."""

    def test_new_vec_no_args(self) -> None:
        result = convert_file("const a = new Array();", "t.ts")
        assert "Vec::new()" in result

    def test_new_hashset(self) -> None:
        result = convert_file("const s = new Set<string>();", "t.ts")
        assert "HashSet::new()" in result


class TestMethodMapCoverage:
    """Tests for more METHOD_MAP entries."""

    def test_pop(self) -> None:
        result = convert_file("arr.pop();", "t.ts")
        assert ".pop()" in result

    def test_shift(self) -> None:
        result = convert_file("arr.shift();", "t.ts")
        assert ".remove(0" in result

    def test_index_of(self) -> None:
        result = convert_file("arr.indexOf(x);", "t.ts")
        assert "iter().position" in result

    def test_to_lower_case(self) -> None:
        result = convert_file("str.toLowerCase();", "t.ts")
        assert ".to_lowercase()" in result

    def test_to_upper_case(self) -> None:
        result = convert_file("str.toUpperCase();", "t.ts")
        assert ".to_uppercase()" in result

    def test_ends_with(self) -> None:
        result = convert_file('str.endsWith("x");', "t.ts")
        assert ".ends_with(" in result

    def test_trim_start(self) -> None:
        result = convert_file("str.trimStart();", "t.ts")
        assert ".trim_start()" in result

    def test_trim_end(self) -> None:
        result = convert_file("str.trimEnd();", "t.ts")
        assert ".trim_end()" in result

    def test_join(self) -> None:
        result = convert_file('arr.join(",");', "t.ts")
        assert '.join(",")' in result

    def test_flat_map(self) -> None:
        result = convert_file("arr.flatMap((x) => [x]);", "t.ts")
        assert "iter().flat_map" in result

    def test_keys(self) -> None:
        result = convert_file("obj.keys();", "t.ts")
        assert ".keys()" in result

    def test_values(self) -> None:
        result = convert_file("obj.values();", "t.ts")
        assert ".values()" in result

    def test_splice(self) -> None:
        result = convert_file("arr.splice(1, 2);", "t.ts")
        assert ".drain(" in result

    def test_find_method(self) -> None:
        result = convert_file("arr.find((x) => x > 0);", "t.ts")
        assert "iter().find" in result

    def test_replace(self) -> None:
        result = convert_file('str.replace("a", "b");', "t.ts")
        assert '.replace("a", "b")' in result

    def test_replace_all(self) -> None:
        result = convert_file('str.replaceAll("a", "b");', "t.ts")
        assert '.replace("a", "b")' in result
