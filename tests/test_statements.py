"""Tests for statement handlers: if, for, while, switch/match, try/catch, var decl, destructuring."""

from __future__ import annotations

from convert_typescript_to_rust import convert_file


class TestIfStatements:
    """Tests for if/else conversion."""

    def test_basic_if(self) -> None:
        result = convert_file("if (x > 0) { doIt(); }", "t.ts")
        assert "if x > 0 {" in result

    def test_if_else(self) -> None:
        result = convert_file("if (x) { a(); } else { b(); }", "t.ts")
        assert "if" in result
        assert "else {" in result

    def test_if_else_if(self) -> None:
        result = convert_file("if (a) { x(); } else if (b) { y(); } else { z(); }", "t.ts")
        assert "else if" in result


class TestForLoops:
    """Tests for for loop conversion."""

    def test_for_of(self) -> None:
        result = convert_file("for (const item of items) { process(item); }", "t.ts")
        assert "for" in result
        assert "in items.iter()" in result

    def test_c_style_for(self) -> None:
        result = convert_file("for (let i = 0; i < 10; i++) { f(); }", "t.ts")
        assert "loop {" in result

    def test_for_in(self) -> None:
        result = convert_file("for (const key in obj) { f(key); }", "t.ts")
        assert "for" in result
        assert "in obj.iter()" in result


class TestWhileLoops:
    """Tests for while/do-while conversion."""

    def test_while(self) -> None:
        result = convert_file("while (x > 0) { x--; }", "t.ts")
        assert "while x > 0 {" in result

    def test_do_while(self) -> None:
        result = convert_file("do { x++; } while (x < 10);", "t.ts")
        assert "loop {" in result
        assert "break;" in result


class TestSwitch:
    """Tests for switch/match conversion."""

    def test_basic_switch(self) -> None:
        result = convert_file(
            'switch (x) { case 1: a(); break; case 2: b(); break; default: c(); }',
            "t.ts",
        )
        assert "match x {" in result
        assert "1 =>" in result
        assert "2 =>" in result
        assert "_ =>" in result


class TestTryCatch:
    """Tests for try/catch/finally conversion."""

    def test_basic_try_catch(self) -> None:
        result = convert_file("try { riskyOp(); } catch (e) { handleError(e); }", "t.ts")
        assert "Result<(), Box<dyn std::error::Error>>" in result
        assert "Err(e)" in result

    def test_try_finally(self) -> None:
        result = convert_file("try { f(); } catch (e) { g(); } finally { cleanup(); }", "t.ts")
        assert "// finally" in result


class TestVarDecl:
    """Tests for variable declaration conversion."""

    def test_const(self) -> None:
        result = convert_file("const x = 42;", "t.ts")
        assert "let x = 42;" in result

    def test_let(self) -> None:
        result = convert_file("let x = 42;", "t.ts")
        assert "let mut x = 42;" in result

    def test_var(self) -> None:
        result = convert_file("var x = 42;", "t.ts")
        assert "let mut x = 42;" in result

    def test_typed_const(self) -> None:
        result = convert_file("const x: number = 42;", "t.ts")
        assert "let x: f64 = 42;" in result

    def test_no_value(self) -> None:
        result = convert_file("let x: string;", "t.ts")
        assert "let mut x: String = Default::default();" in result


class TestDestructuring:
    """Tests for destructuring patterns."""

    def test_object_destructuring(self) -> None:
        result = convert_file("const { name, age } = user;", "t.ts")
        assert "_destructured" in result
        assert "name" in result
        assert "age" in result

    def test_array_destructuring(self) -> None:
        result = convert_file("const [a, b] = arr;", "t.ts")
        assert "_arr" in result
        assert ".get(0)" in result
        assert ".get(1)" in result
