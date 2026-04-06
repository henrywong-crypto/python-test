"""Tests for call expression handlers: Math.*, console.*, JSON.*, etc."""

from __future__ import annotations

from convert_typescript_to_rust.calls import _math_call, _console_call, _METHOD_MAP
from convert_typescript_to_rust import convert_file


class TestMathCall:
    """Tests for _math_call."""

    def test_floor(self) -> None:
        assert _math_call("floor", "x") == "(x as f64).floor()"

    def test_ceil(self) -> None:
        assert _math_call("ceil", "x") == "(x as f64).ceil()"

    def test_round(self) -> None:
        assert _math_call("round", "x") == "(x as f64).round()"

    def test_abs(self) -> None:
        assert _math_call("abs", "x") == "(x as f64).abs()"

    def test_sqrt(self) -> None:
        assert _math_call("sqrt", "x") == "(x as f64).sqrt()"

    def test_log(self) -> None:
        assert _math_call("log", "x") == "(x as f64).ln()"

    def test_log2(self) -> None:
        assert _math_call("log2", "x") == "(x as f64).log2()"

    def test_pow(self) -> None:
        result = _math_call("pow", "x, 2")
        assert "powf" in result

    def test_max_two_args(self) -> None:
        result = _math_call("max", "a, b")
        assert ".max(" in result

    def test_max_no_args(self) -> None:
        assert _math_call("max", "") == "f64::MAX"

    def test_min_two_args(self) -> None:
        result = _math_call("min", "a, b")
        assert ".min(" in result

    def test_min_no_args(self) -> None:
        assert _math_call("min", "") == "f64::MIN"

    def test_random(self) -> None:
        assert _math_call("random", "") == "rand::random::<f64>()"

    def test_pi(self) -> None:
        assert _math_call("PI", "") == "std::f64::consts::PI"

    def test_sign(self) -> None:
        assert _math_call("sign", "x") == "(x as f64).signum()"

    def test_trunc(self) -> None:
        assert _math_call("trunc", "x") == "(x as f64).trunc()"

    def test_unknown_method(self) -> None:
        result = _math_call("unknown", "x")
        assert result == "f64::unknown(x)"


class TestConsoleCall:
    """Tests for _console_call."""

    def test_log(self) -> None:
        result = _console_call("log", "msg")
        assert "tracing::info!" in result

    def test_error(self) -> None:
        result = _console_call("error", "msg")
        assert "tracing::error!" in result

    def test_warn(self) -> None:
        result = _console_call("warn", "msg")
        assert "tracing::warn!" in result

    def test_debug(self) -> None:
        result = _console_call("debug", "msg")
        assert "tracing::debug!" in result


class TestMethodMap:
    """Tests for _METHOD_MAP completeness."""

    def test_push(self) -> None:
        assert _METHOD_MAP["push"] == "push"

    def test_includes(self) -> None:
        assert _METHOD_MAP["includes"] == "contains"

    def test_map(self) -> None:
        assert _METHOD_MAP["map"] == "iter().map"

    def test_filter(self) -> None:
        assert _METHOD_MAP["filter"] == "iter().filter"


class TestCallIntegration:
    """Integration tests for call expressions via convert_file."""

    def test_math_sqrt(self) -> None:
        result = convert_file("Math.sqrt(4);", "test.ts")
        assert ".sqrt()" in result

    def test_console_log(self) -> None:
        result = convert_file('console.log("hello");', "test.ts")
        assert "tracing::info!" in result

    def test_json_stringify(self) -> None:
        result = convert_file("JSON.stringify(obj);", "test.ts")
        assert "serde_json::to_string" in result

    def test_json_parse(self) -> None:
        result = convert_file('JSON.parse(str);', "test.ts")
        assert "serde_json::from_str" in result

    def test_array_is_array(self) -> None:
        result = convert_file("Array.isArray(x);", "test.ts")
        assert ".is_array()" in result

    def test_date_now(self) -> None:
        result = convert_file("Date.now();", "test.ts")
        assert "SystemTime" in result

    def test_axios_get(self) -> None:
        result = convert_file('axios.get("/api");', "test.ts")
        assert "reqwest::Client::new().get" in result

    def test_object_keys(self) -> None:
        result = convert_file("Object.keys(obj);", "test.ts")
        assert ".keys()" in result

    def test_parse_int(self) -> None:
        result = convert_file('parseInt("42");', "test.ts")
        assert "parse::<i64>" in result

    def test_parse_float(self) -> None:
        result = convert_file('parseFloat("3.14");', "test.ts")
        assert "parse::<f64>" in result

    def test_set_timeout(self) -> None:
        result = convert_file("setTimeout(fn, 100);", "test.ts")
        assert "tokio::time::sleep" in result
