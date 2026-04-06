"""Tests for declaration handlers: functions, classes, interfaces, enums, exports, type aliases."""

from __future__ import annotations

from convert_typescript_to_rust import convert_file


class TestFunctions:
    """Tests for function declarations."""

    def test_basic_function(self) -> None:
        result = convert_file("function greet(name: string): string { return name; }", "t.ts")
        assert "pub fn greet" in result
        assert "-> String" in result
        assert "return name;" in result

    def test_async_function(self) -> None:
        result = convert_file("async function fetch(): Promise<string> { return ''; }", "t.ts")
        assert "pub async fn fetch" in result

    def test_function_no_return(self) -> None:
        result = convert_file("function doIt() { }", "t.ts")
        assert "pub fn do_it()" in result

    def test_function_with_params(self) -> None:
        result = convert_file("function add(a: number, b: number): number { return a + b; }", "t.ts")
        assert "a: f64" in result
        assert "b: f64" in result


class TestClasses:
    """Tests for class declarations."""

    def test_basic_class(self) -> None:
        result = convert_file("class Foo { bar: string; }", "t.ts")
        assert "pub struct Foo" in result
        assert "pub bar: String" in result

    def test_class_with_method(self) -> None:
        result = convert_file(
            "class Foo { greet() { console.log('hi'); } }",
            "t.ts",
        )
        assert "impl Foo" in result
        assert "pub fn greet" in result

    def test_abstract_class(self) -> None:
        result = convert_file("abstract class Base { }", "t.ts")
        assert "pub struct Base" in result


class TestInterfaces:
    """Tests for interface declarations."""

    def test_basic_interface(self) -> None:
        result = convert_file("interface User { name: string; age: number; }", "t.ts")
        assert "pub struct User" in result
        assert "pub name: String" in result
        assert "pub age: f64" in result

    def test_optional_field(self) -> None:
        result = convert_file("interface Cfg { debug?: boolean; }", "t.ts")
        assert "Option<bool>" in result

    def test_empty_interface(self) -> None:
        result = convert_file("interface Empty { }", "t.ts")
        assert "pub struct Empty;" in result

    def test_serde_derive(self) -> None:
        result = convert_file("interface User { name: string; }", "t.ts")
        assert "serde::Serialize" in result
        assert "serde::Deserialize" in result


class TestEnums:
    """Tests for enum declarations."""

    def test_basic_enum(self) -> None:
        result = convert_file("enum Color { Red, Green, Blue }", "t.ts")
        assert "pub enum Color" in result
        assert "Red," in result
        assert "Green," in result
        assert "Blue," in result

    def test_enum_derive(self) -> None:
        result = convert_file("enum Status { Active }", "t.ts")
        assert "#[derive(Debug, Clone, PartialEq)]" in result


class TestExports:
    """Tests for export statements."""

    def test_export_function(self) -> None:
        result = convert_file("export function greet() { }", "t.ts")
        assert "pub fn greet" in result

    def test_export_const(self) -> None:
        result = convert_file("export const MAX = 10;", "t.ts")
        assert "pub const MAX" in result

    def test_export_const_function(self) -> None:
        result = convert_file("export const fn1 = () => { };", "t.ts")
        assert "pub fn fn1" in result

    def test_export_interface(self) -> None:
        result = convert_file("export interface Foo { x: number; }", "t.ts")
        assert "pub struct Foo" in result

    def test_export_enum(self) -> None:
        result = convert_file("export enum Dir { Up, Down }", "t.ts")
        assert "pub enum Dir" in result

    def test_export_default_object(self) -> None:
        result = convert_file('export default { key: "val" };', "t.ts")
        assert "pub const DEFAULT" in result

    def test_export_default_ident(self) -> None:
        result = convert_file("const x = 1; export default x;", "t.ts")
        assert "pub use" in result


class TestTypeAliases:
    """Tests for type alias declarations."""

    def test_simple_alias(self) -> None:
        result = convert_file("type ID = string;", "t.ts")
        assert "pub type ID = String;" in result

    def test_object_type_alias(self) -> None:
        result = convert_file("type Cfg = { host: string; port: number; };", "t.ts")
        assert "pub struct Cfg" in result
        assert "pub host: String" in result
        assert "pub port: f64" in result
