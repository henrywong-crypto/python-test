"""Tests for expression handlers: binary ops, ternary, template strings, arrow functions, objects, arrays."""

from __future__ import annotations

from convert_typescript_to_rust import convert_file


class TestBinaryOps:
    """Tests for binary expression conversion."""

    def test_strict_equals(self) -> None:
        result = convert_file("const r = a === b;", "t.ts")
        assert "==" in result
        assert "===" not in result

    def test_strict_not_equals(self) -> None:
        result = convert_file("const r = a !== b;", "t.ts")
        assert "!=" in result
        assert "!==" not in result

    def test_instanceof(self) -> None:
        result = convert_file("const r = x instanceof Foo;", "t.ts")
        assert "downcast_ref" in result

    def test_in_operator(self) -> None:
        result = convert_file('const r = "key" in obj;', "t.ts")
        assert "contains_key" in result

    def test_arithmetic(self) -> None:
        result = convert_file("const r = a + b;", "t.ts")
        assert "a + b" in result


class TestTernary:
    """Tests for ternary expression conversion."""

    def test_basic_ternary(self) -> None:
        result = convert_file("const x = a ? b : c;", "t.ts")
        assert "if a { b } else { c }" in result


class TestTemplateStrings:
    """Tests for template string conversion."""

    def test_basic_template(self) -> None:
        result = convert_file("const s = `hello ${name}`;", "t.ts")
        assert "format!" in result
        assert "hello {}" in result

    def test_no_substitution(self) -> None:
        result = convert_file("const s = `plain`;", "t.ts")
        assert '"plain".to_string()' in result

    def test_multiple_substitutions(self) -> None:
        result = convert_file("const s = `${a} and ${b}`;", "t.ts")
        assert "format!" in result
        assert "{} and {}" in result


class TestArrowFunctions:
    """Tests for arrow function conversion."""

    def test_simple_arrow(self) -> None:
        result = convert_file("const f = (x: number) => x * 2;", "t.ts")
        assert "|x|" in result

    def test_arrow_with_block(self) -> None:
        result = convert_file("const f = (x: number) => { return x; };", "t.ts")
        assert "|x| {" in result

    def test_no_params(self) -> None:
        result = convert_file("const f = () => 42;", "t.ts")
        assert "|| 42" in result


class TestObjects:
    """Tests for object literal conversion."""

    def test_basic_object(self) -> None:
        result = convert_file('const obj = { key: "value" };', "t.ts")
        assert "serde_json::json!" in result

    def test_shorthand(self) -> None:
        result = convert_file("const obj = { name };", "t.ts")
        assert '"name": name' in result


class TestArrays:
    """Tests for array literal conversion."""

    def test_basic_array(self) -> None:
        result = convert_file("const arr = [1, 2, 3];", "t.ts")
        assert "vec![1, 2, 3]" in result

    def test_empty_array(self) -> None:
        result = convert_file("const arr = [];", "t.ts")
        assert "vec![]" in result


class TestUnary:
    """Tests for unary expressions."""

    def test_typeof(self) -> None:
        result = convert_file('const t = typeof x === "string";', "t.ts")
        assert "is_string" in result

    def test_void(self) -> None:
        result = convert_file("void 0;", "t.ts")
        assert "let _ =" in result

    def test_delete(self) -> None:
        result = convert_file("delete obj.prop;", "t.ts")
        assert ".take()" in result


class TestUpdate:
    """Tests for update expressions."""

    def test_prefix_increment(self) -> None:
        result = convert_file("++x;", "t.ts")
        assert "+= 1" in result

    def test_postfix_decrement(self) -> None:
        result = convert_file("x--;", "t.ts")
        assert "-= 1" in result


class TestAssignment:
    """Tests for assignment expressions."""

    def test_basic_assignment(self) -> None:
        result = convert_file("x = 5;", "t.ts")
        assert "x = 5;" in result

    def test_augmented(self) -> None:
        result = convert_file("x += 1;", "t.ts")
        assert "x += 1;" in result


class TestMiscExpressions:
    """Tests for miscellaneous expressions."""

    def test_await(self) -> None:
        result = convert_file("const r = await fetch();", "t.ts")
        assert ".await" in result

    def test_spread(self) -> None:
        result = convert_file("const arr = [...other];", "t.ts")
        assert "..other" in result

    def test_new_map(self) -> None:
        result = convert_file("const m = new Map<string, number>();", "t.ts")
        assert "HashMap::new()" in result

    def test_new_set(self) -> None:
        result = convert_file("const s = new Set<string>();", "t.ts")
        assert "HashSet::new()" in result

    def test_non_null_assertion(self) -> None:
        result = convert_file("const x = obj!;", "t.ts")
        assert ".unwrap()" in result

    def test_as_expression(self) -> None:
        result = convert_file("const x = val as string;", "t.ts")
        # as-expression is dropped, only the value remains
        assert "as string" not in result

    def test_regex(self) -> None:
        result = convert_file("const re = /abc/g;", "t.ts")
        assert "regex::Regex::new" in result

    def test_null_literal(self) -> None:
        result = convert_file("const x = null;", "t.ts")
        assert "None" in result

    def test_this(self) -> None:
        result = convert_file("const x = this.foo;", "t.ts")
        assert "self.foo" in result
