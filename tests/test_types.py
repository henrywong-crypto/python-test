"""Tests for type conversion: primitives, arrays, generics, unions, intersections, tuples."""

from __future__ import annotations

from convert_typescript_to_rust.types import convert_type, _TYPE_MAP


class TestPrimitives:
    """Tests for predefined_type and type_identifier mapping."""

    def test_string(self, first_named) -> None:
        node = first_named("let x: string;")
        # Find the type_annotation -> predefined_type
        for ch in node.children:
            for ch2 in ch.children:
                if ch2.type == "type_annotation":
                    assert convert_type(ch2) == "String"
                    return
        raise AssertionError("type_annotation not found")

    def test_number(self, first_named) -> None:
        node = first_named("let x: number;")
        for ch in node.children:
            for ch2 in ch.children:
                if ch2.type == "type_annotation":
                    assert convert_type(ch2) == "f64"
                    return

    def test_boolean(self, first_named) -> None:
        node = first_named("let x: boolean;")
        for ch in node.children:
            for ch2 in ch.children:
                if ch2.type == "type_annotation":
                    assert convert_type(ch2) == "bool"
                    return

    def test_void(self, first_named) -> None:
        node = first_named("let x: void;")
        for ch in node.children:
            for ch2 in ch.children:
                if ch2.type == "type_annotation":
                    assert convert_type(ch2) == "()"
                    return

    def test_any(self, first_named) -> None:
        node = first_named("let x: any;")
        for ch in node.children:
            for ch2 in ch.children:
                if ch2.type == "type_annotation":
                    assert convert_type(ch2) == "serde_json::Value"
                    return


class TestTypeMap:
    """Tests for the _TYPE_MAP dictionary."""

    def test_contains_common_types(self) -> None:
        assert "string" in _TYPE_MAP
        assert "number" in _TYPE_MAP
        assert "boolean" in _TYPE_MAP

    def test_buffer_types(self) -> None:
        assert _TYPE_MAP["Buffer"] == "Vec<u8>"
        assert _TYPE_MAP["Uint8Array"] == "Vec<u8>"


class TestNone:
    """Tests for convert_type(None)."""

    def test_none_returns_default(self) -> None:
        assert convert_type(None) == "serde_json::Value"


class TestArrayTypes:
    """Tests for array type conversion."""

    def test_string_array(self, first_named) -> None:
        node = first_named("let x: string[];")
        for ch in node.children:
            for ch2 in ch.children:
                if ch2.type == "type_annotation":
                    result = convert_type(ch2)
                    assert "Vec<String>" in result
                    return


class TestGenericTypes:
    """Tests for generic type conversion."""

    def test_promise(self, first_named) -> None:
        node = first_named("let x: Promise<string>;")
        for ch in node.children:
            for ch2 in ch.children:
                if ch2.type == "type_annotation":
                    result = convert_type(ch2)
                    assert result == "String"
                    return

    def test_map(self, first_named) -> None:
        node = first_named("let x: Map<string, number>;")
        for ch in node.children:
            for ch2 in ch.children:
                if ch2.type == "type_annotation":
                    result = convert_type(ch2)
                    assert "HashMap" in result
                    return

    def test_set(self, first_named) -> None:
        node = first_named("let x: Set<string>;")
        for ch in node.children:
            for ch2 in ch.children:
                if ch2.type == "type_annotation":
                    result = convert_type(ch2)
                    assert "HashSet" in result
                    return

    def test_record(self, first_named) -> None:
        node = first_named("let x: Record<string, number>;")
        for ch in node.children:
            for ch2 in ch.children:
                if ch2.type == "type_annotation":
                    result = convert_type(ch2)
                    assert "HashMap" in result
                    return

    def test_partial(self, first_named) -> None:
        node = first_named("let x: Partial<User>;")
        for ch in node.children:
            for ch2 in ch.children:
                if ch2.type == "type_annotation":
                    result = convert_type(ch2)
                    assert result == "User"
                    return

    def test_array_generic(self, first_named) -> None:
        node = first_named("let x: Array<number>;")
        for ch in node.children:
            for ch2 in ch.children:
                if ch2.type == "type_annotation":
                    result = convert_type(ch2)
                    assert "Vec<f64>" in result
                    return


class TestUnionTypes:
    """Tests for union type conversion."""

    def test_nullable(self, first_named) -> None:
        node = first_named("let x: string | null;")
        for ch in node.children:
            for ch2 in ch.children:
                if ch2.type == "type_annotation":
                    result = convert_type(ch2)
                    assert "Option<String>" in result
                    return

    def test_multi_union(self, first_named) -> None:
        node = first_named("let x: string | number | boolean;")
        for ch in node.children:
            for ch2 in ch.children:
                if ch2.type == "type_annotation":
                    result = convert_type(ch2)
                    assert result == "serde_json::Value"
                    return


class TestIntersectionTypes:
    """Tests for intersection type conversion."""

    def test_intersection(self, first_named) -> None:
        node = first_named("let x: A & B;")
        for ch in node.children:
            for ch2 in ch.children:
                if ch2.type == "type_annotation":
                    result = convert_type(ch2)
                    assert result == "serde_json::Value"
                    return


class TestTupleTypes:
    """Tests for tuple type conversion."""

    def test_tuple(self, first_named) -> None:
        node = first_named("let x: [string, number];")
        for ch in node.children:
            for ch2 in ch.children:
                if ch2.type == "type_annotation":
                    result = convert_type(ch2)
                    assert "String" in result
                    assert "f64" in result
                    return
