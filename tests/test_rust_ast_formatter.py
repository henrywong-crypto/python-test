"""Tests for rust_ast.py and formatter.py -- the new Rust AST IR and formatter."""

from __future__ import annotations

from convert_typescript_to_rust.rust_ast import (
    RsFile, RsFunction, RsStruct, RsEnum, RsImpl, RsTypeAlias, RsConst,
    RsField, RsEnumVariant, RsParam, RsComment, RsRawStmt,
    RsLet, RsReturn, RsExprStmt, RsIf, RsFor, RsWhile, RsLoop,
    RsMatch, RsMatchArm, RsTryCatch, RsBreak, RsContinue,
    RsLiteral, RsIdent, RsBinOp, RsUnaryOp, RsCall, RsMethodCall,
    RsFieldAccess, RsIndex, RsClosure, RsAwait, RsMacro, RsIfExpr, RsRawExpr,
    RsPrimitiveType, RsOptionType, RsVecType, RsHashMapType, RsRawType,
)
from convert_typescript_to_rust.formatter import (
    format_file, format_item, format_stmt, format_expr, format_type,
)


class TestRsAstDataclasses:
    """Test that AST dataclasses can be instantiated."""

    def test_rs_file(self) -> None:
        f = RsFile(doc_comment="//! test", items=[])
        assert f.doc_comment == "//! test"
        assert f.items == []

    def test_rs_function(self) -> None:
        fn = RsFunction(name="greet", is_pub=True, is_async=False)
        assert fn.name == "greet"
        assert fn.params == []
        assert fn.body == []

    def test_rs_struct(self) -> None:
        s = RsStruct(name="Foo", fields=[
            RsField(name="bar", type_ann=RsPrimitiveType(name="String")),
        ])
        assert s.name == "Foo"
        assert len(s.fields) == 1

    def test_rs_enum(self) -> None:
        e = RsEnum(name="Color", variants=[
            RsEnumVariant(name="Red"),
            RsEnumVariant(name="Blue"),
        ])
        assert e.name == "Color"
        assert len(e.variants) == 2

    def test_rs_impl(self) -> None:
        impl = RsImpl(type_name="Foo", methods=[
            RsFunction(name="new", is_pub=True),
        ])
        assert impl.type_name == "Foo"

    def test_rs_type_alias(self) -> None:
        ta = RsTypeAlias(name="ID", type_ann=RsPrimitiveType(name="String"))
        assert ta.name == "ID"

    def test_rs_const(self) -> None:
        c = RsConst(name="MAX", type_ann=RsPrimitiveType(name="usize"),
                     value=RsLiteral(value="100"))
        assert c.name == "MAX"

    def test_rs_let(self) -> None:
        l = RsLet(name="x", mutable=True, value=RsLiteral(value="42"))
        assert l.name == "x"
        assert l.mutable is True

    def test_rs_expressions(self) -> None:
        assert RsLiteral(value="42").value == "42"
        assert RsIdent(name="x").name == "x"
        assert RsBinOp(left=RsIdent(name="a"), op="+", right=RsIdent(name="b")).op == "+"
        assert RsUnaryOp(op="!", operand=RsIdent(name="x")).op == "!"
        assert RsCall(func=RsIdent(name="f"), args=[]).func.name == "f"
        assert RsMethodCall(obj=RsIdent(name="x"), method="len").method == "len"
        assert RsFieldAccess(obj=RsIdent(name="s"), field="name").field == "name"
        assert RsIndex(obj=RsIdent(name="arr"), index=RsLiteral(value="0")).index.value == "0"
        assert RsAwait(expr=RsIdent(name="f")).expr.name == "f"
        assert RsMacro(name="vec!", args="1, 2").name == "vec!"
        assert RsRawExpr(text="foo()").text == "foo()"

    def test_rs_statements(self) -> None:
        assert RsReturn(value=RsLiteral(value="42")).value.value == "42"
        assert RsBreak().__class__.__name__ == "RsBreak"
        assert RsContinue().__class__.__name__ == "RsContinue"
        assert RsComment(text="// hi").text == "// hi"
        assert RsRawStmt(text="x;").text == "x;"

    def test_type_nodes(self) -> None:
        assert RsPrimitiveType(name="f64").name == "f64"
        assert RsOptionType(inner=RsPrimitiveType(name="String")).inner.name == "String"
        assert RsVecType(inner=RsPrimitiveType(name="u8")).inner.name == "u8"
        assert RsHashMapType(
            key=RsPrimitiveType(name="String"),
            value=RsPrimitiveType(name="f64"),
        ).key.name == "String"
        assert RsRawType(text="serde_json::Value").text == "serde_json::Value"


class TestFormatterTypes:
    """Test formatter type rendering."""

    def test_primitive(self) -> None:
        assert format_type(RsPrimitiveType(name="f64")) == "f64"

    def test_option(self) -> None:
        assert format_type(RsOptionType(inner=RsPrimitiveType(name="String"))) == "Option<String>"

    def test_vec(self) -> None:
        assert format_type(RsVecType(inner=RsPrimitiveType(name="u8"))) == "Vec<u8>"

    def test_hashmap(self) -> None:
        result = format_type(RsHashMapType(
            key=RsPrimitiveType(name="String"),
            value=RsPrimitiveType(name="f64"),
        ))
        assert result == "std::collections::HashMap<String, f64>"

    def test_raw_type(self) -> None:
        assert format_type(RsRawType(text="Box<dyn Fn()>")) == "Box<dyn Fn()>"


class TestFormatterExpressions:
    """Test formatter expression rendering."""

    def test_literal(self) -> None:
        assert format_expr(RsLiteral(value="42")) == "42"

    def test_ident(self) -> None:
        assert format_expr(RsIdent(name="foo")) == "foo"

    def test_binop(self) -> None:
        expr = RsBinOp(left=RsIdent(name="a"), op="+", right=RsIdent(name="b"))
        assert format_expr(expr) == "a + b"

    def test_unary(self) -> None:
        expr = RsUnaryOp(op="!", operand=RsIdent(name="x"))
        assert format_expr(expr) == "!x"

    def test_call(self) -> None:
        expr = RsCall(func=RsIdent(name="f"), args=[RsLiteral(value="1")])
        assert format_expr(expr) == "f(1)"

    def test_method_call(self) -> None:
        expr = RsMethodCall(obj=RsIdent(name="v"), method="push", args=[RsLiteral(value="1")])
        assert format_expr(expr) == "v.push(1)"

    def test_field_access(self) -> None:
        expr = RsFieldAccess(obj=RsIdent(name="s"), field="name")
        assert format_expr(expr) == "s.name"

    def test_index(self) -> None:
        expr = RsIndex(obj=RsIdent(name="arr"), index=RsLiteral(value="0"))
        assert format_expr(expr) == "arr[0]"

    def test_closure_expr_body(self) -> None:
        expr = RsClosure(params=["x"], body=RsIdent(name="x"))
        assert format_expr(expr) == "|x| x"

    def test_closure_no_body(self) -> None:
        expr = RsClosure(params=["x"], body=None)
        assert format_expr(expr) == "|x| {}"

    def test_closure_block_body(self) -> None:
        expr = RsClosure(params=["x"], body=[RsReturn(value=RsIdent(name="x"))])
        result = format_expr(expr)
        assert "|x| {" in result
        assert "return x;" in result

    def test_await(self) -> None:
        expr = RsAwait(expr=RsIdent(name="f"))
        assert format_expr(expr) == "f.await"

    def test_macro(self) -> None:
        expr = RsMacro(name="vec!", args="1, 2, 3")
        assert format_expr(expr) == "vec!(1, 2, 3)"

    def test_if_expr(self) -> None:
        expr = RsIfExpr(
            condition=RsIdent(name="cond"),
            then_expr=RsLiteral(value="1"),
            else_expr=RsLiteral(value="2"),
        )
        assert format_expr(expr) == "if cond { 1 } else { 2 }"

    def test_raw_expr(self) -> None:
        assert format_expr(RsRawExpr(text="foo()")) == "foo()"


class TestFormatterStatements:
    """Test formatter statement rendering."""

    def test_let(self) -> None:
        result = format_stmt(RsLet(name="x", value=RsLiteral(value="42")), 0)
        assert result == "let x = 42;"

    def test_let_mut(self) -> None:
        result = format_stmt(RsLet(name="x", mutable=True, value=RsLiteral(value="0")), 0)
        assert result == "let mut x = 0;"

    def test_let_typed(self) -> None:
        result = format_stmt(
            RsLet(name="x", type_ann=RsPrimitiveType(name="f64"), value=RsLiteral(value="42")),
            0,
        )
        assert result == "let x: f64 = 42;"

    def test_let_no_value(self) -> None:
        result = format_stmt(RsLet(name="x"), 0)
        assert result == "let x = Default::default();"

    def test_return_value(self) -> None:
        result = format_stmt(RsReturn(value=RsLiteral(value="42")), 0)
        assert result == "return 42;"

    def test_return_empty(self) -> None:
        result = format_stmt(RsReturn(), 0)
        assert result == "return;"

    def test_expr_stmt(self) -> None:
        result = format_stmt(RsExprStmt(expr=RsRawExpr(text="f()")), 0)
        assert result == "f();"

    def test_break(self) -> None:
        assert format_stmt(RsBreak(), 0) == "break;"

    def test_continue(self) -> None:
        assert format_stmt(RsContinue(), 0) == "continue;"

    def test_comment(self) -> None:
        assert format_stmt(RsComment(text="// hello"), 0) == "// hello"

    def test_raw_stmt(self) -> None:
        assert format_stmt(RsRawStmt(text="raw_code;"), 0) == "raw_code;"

    def test_if_stmt(self) -> None:
        stmt = RsIf(
            condition=RsRawExpr(text="x > 0"),
            then_body=[RsExprStmt(expr=RsRawExpr(text="do_it()"))],
        )
        result = format_stmt(stmt, 0)
        assert "if x > 0 {" in result
        assert "do_it();" in result

    def test_if_else(self) -> None:
        stmt = RsIf(
            condition=RsRawExpr(text="x"),
            then_body=[RsExprStmt(expr=RsRawExpr(text="a()"))],
            else_body=[RsExprStmt(expr=RsRawExpr(text="b()"))],
        )
        result = format_stmt(stmt, 0)
        assert "else {" in result

    def test_if_else_if(self) -> None:
        stmt = RsIf(
            condition=RsRawExpr(text="a"),
            then_body=[],
            else_body=[RsIf(
                condition=RsRawExpr(text="b"),
                then_body=[],
            )],
        )
        result = format_stmt(stmt, 0)
        assert "else if b {" in result

    def test_for_loop(self) -> None:
        stmt = RsFor(
            var_name="item",
            iter_expr=RsRawExpr(text="items.iter()"),
            body=[RsExprStmt(expr=RsRawExpr(text="process(item)"))],
        )
        result = format_stmt(stmt, 0)
        assert "for item in items.iter()" in result

    def test_while_loop(self) -> None:
        stmt = RsWhile(
            condition=RsRawExpr(text="x > 0"),
            body=[RsExprStmt(expr=RsRawExpr(text="x -= 1"))],
        )
        result = format_stmt(stmt, 0)
        assert "while x > 0 {" in result

    def test_loop(self) -> None:
        stmt = RsLoop(body=[RsBreak()])
        result = format_stmt(stmt, 0)
        assert "loop {" in result
        assert "break;" in result

    def test_match(self) -> None:
        stmt = RsMatch(
            expr=RsRawExpr(text="x"),
            arms=[
                RsMatchArm(pattern=RsLiteral(value="1"), body=[RsExprStmt(expr=RsRawExpr(text="a()"))]),
                RsMatchArm(pattern=RsIdent(name="_"), body=[RsExprStmt(expr=RsRawExpr(text="b()"))]),
            ],
        )
        result = format_stmt(stmt, 0)
        assert "match x {" in result
        assert "1 =>" in result
        assert "_ =>" in result

    def test_try_catch(self) -> None:
        stmt = RsTryCatch(
            try_body=[RsExprStmt(expr=RsRawExpr(text="risky()"))],
            catch_var="e",
            catch_body=[RsExprStmt(expr=RsRawExpr(text="handle(e)"))],
        )
        result = format_stmt(stmt, 0)
        assert "Result<(), Box<dyn std::error::Error>>" in result
        assert "Err(e)" in result

    def test_try_no_catch(self) -> None:
        stmt = RsTryCatch(
            try_body=[RsExprStmt(expr=RsRawExpr(text="f()"))],
        )
        result = format_stmt(stmt, 0)
        assert "// try" in result

    def test_try_finally(self) -> None:
        stmt = RsTryCatch(
            try_body=[RsExprStmt(expr=RsRawExpr(text="f()"))],
            catch_var="e",
            catch_body=[RsExprStmt(expr=RsRawExpr(text="handle(e)"))],
            finally_body=[RsExprStmt(expr=RsRawExpr(text="cleanup()"))],
        )
        result = format_stmt(stmt, 0)
        assert "// finally" in result
        assert "cleanup();" in result


class TestFormatterItems:
    """Test formatter item rendering."""

    def test_function(self) -> None:
        fn = RsFunction(
            name="greet",
            params=[RsParam(name="name", type_ann=RsRawType(text="&str"))],
            return_type=RsRawType(text="String"),
            body=[RsRawStmt(text="    return name;")],
        )
        result = format_item(fn, 0)
        assert "pub fn greet(name: &str) -> String {" in result
        assert "return name;" in result

    def test_async_function(self) -> None:
        fn = RsFunction(name="fetch", is_async=True, body=[RsRawStmt(text="    // empty")])
        result = format_item(fn, 0)
        assert "pub async fn fetch()" in result

    def test_struct(self) -> None:
        s = RsStruct(name="User", fields=[
            RsField(name="name", type_ann=RsPrimitiveType(name="String")),
            RsField(name="age", type_ann=RsPrimitiveType(name="f64")),
        ])
        result = format_item(s, 0)
        assert "pub struct User {" in result
        assert "pub name: String," in result
        assert "pub age: f64," in result
        assert "#[derive(" in result

    def test_empty_struct(self) -> None:
        s = RsStruct(name="Empty", is_empty=True)
        result = format_item(s, 0)
        assert result == "pub struct Empty;"

    def test_struct_no_fields(self) -> None:
        s = RsStruct(name="Empty")
        result = format_item(s, 0)
        assert result == "pub struct Empty;"

    def test_enum(self) -> None:
        e = RsEnum(name="Color", variants=[
            RsEnumVariant(name="Red"),
            RsEnumVariant(name="Green"),
        ])
        result = format_item(e, 0)
        assert "pub enum Color {" in result
        assert "Red," in result
        assert "Green," in result

    def test_empty_enum(self) -> None:
        e = RsEnum(name="Empty")
        result = format_item(e, 0)
        assert "// empty" in result

    def test_impl(self) -> None:
        impl = RsImpl(type_name="Foo", methods=[
            RsFunction(name="new", params=[RsParam(name="&self", type_ann=RsRawType(text=""))],
                        body=[RsRawStmt(text="        // empty")]),
        ])
        result = format_item(impl, 0)
        assert "impl Foo {" in result

    def test_type_alias(self) -> None:
        ta = RsTypeAlias(name="ID", type_ann=RsPrimitiveType(name="String"))
        result = format_item(ta, 0)
        assert "pub type ID = String;" in result

    def test_const(self) -> None:
        c = RsConst(name="MAX", type_ann=RsPrimitiveType(name="usize"),
                     value=RsLiteral(value="100"))
        result = format_item(c, 0)
        assert "pub const MAX: usize = 100;" in result

    def test_comment_item(self) -> None:
        result = format_item(RsComment(text="// top-level comment"), 0)
        assert result == "// top-level comment"

    def test_raw_stmt_item(self) -> None:
        result = format_item(RsRawStmt(text="use std::io;"), 0)
        assert result == "use std::io;"

    def test_function_with_doc_comment(self) -> None:
        fn = RsFunction(
            name="f",
            doc_comment="/// Does something",
            body=[RsRawStmt(text="    // empty")],
        )
        result = format_item(fn, 0)
        assert "/// Does something" in result
        assert "pub fn f()" in result

    def test_struct_with_doc_comment(self) -> None:
        s = RsStruct(
            name="Foo",
            doc_comment="/// A Foo",
            fields=[RsField(name="x", type_ann=RsPrimitiveType(name="f64"))],
        )
        result = format_item(s, 0)
        assert "/// A Foo" in result

    def test_function_empty_body(self) -> None:
        fn = RsFunction(name="f")
        result = format_item(fn, 0)
        assert "// empty" in result

    def test_param_rest(self) -> None:
        fn = RsFunction(name="f", params=[
            RsParam(name="args", type_ann=RsRawType(text="String"), is_rest=True),
        ])
        result = format_item(fn, 0)
        assert "args: &[String]" in result


class TestFormatterFile:
    """Test format_file."""

    def test_basic_file(self) -> None:
        f = RsFile(
            doc_comment="//! test file",
            items=[
                RsFunction(name="main", body=[RsRawStmt(text="    // empty")]),
            ],
        )
        result = format_file(f)
        assert "//! test file" in result
        assert "pub fn main()" in result

    def test_file_with_multiple_items(self) -> None:
        f = RsFile(items=[
            RsStruct(name="Foo", fields=[
                RsField(name="x", type_ann=RsPrimitiveType(name="f64")),
            ]),
            RsFunction(name="create_foo", body=[RsRawStmt(text="    // empty")]),
        ])
        result = format_file(f)
        assert "pub struct Foo" in result
        assert "pub fn create_foo" in result

    def test_file_blank_lines_between_items(self) -> None:
        f = RsFile(items=[
            RsFunction(name="a", body=[RsRawStmt(text="    // empty")]),
            RsFunction(name="b", body=[RsRawStmt(text="    // empty")]),
        ])
        result = format_file(f)
        # There should be a blank line between items
        assert "\n\n" in result


class TestFormatterIndentation:
    """Test that indentation is handled by the formatter."""

    def test_indented_function(self) -> None:
        fn = RsFunction(name="f", body=[RsRawStmt(text="        // nested")])
        result = format_item(fn, 1)
        assert "    pub fn f()" in result

    def test_indented_struct(self) -> None:
        s = RsStruct(name="S", fields=[
            RsField(name="x", type_ann=RsPrimitiveType(name="f64")),
        ])
        result = format_item(s, 1)
        assert "    pub struct S {" in result
        assert "        pub x: f64," in result

    def test_indented_let(self) -> None:
        result = format_stmt(RsLet(name="x", value=RsLiteral(value="1")), 2)
        assert result == "        let x = 1;"

    def test_match_arm_comment(self) -> None:
        stmt = RsMatch(
            expr=RsRawExpr(text="x"),
            arms=[
                RsMatchArm(pattern=RsComment(text="// arm comment"), body=[]),
            ],
        )
        result = format_stmt(stmt, 0)
        assert "// arm comment" in result
