"""Integration tests: full file conversion with complex inputs."""

from __future__ import annotations

from convert_typescript_to_rust import convert_file, convert_directory

import tempfile
from pathlib import Path


class TestComplexFile:
    """Tests for complex multi-feature file conversion."""

    def test_multiple_exports(self) -> None:
        ts = """
export interface Config {
    host: string;
    port: number;
}

export const DEFAULT_PORT: number = 3000;

export function createConfig(host: string): Config {
    return { host, port: DEFAULT_PORT };
}
"""
        result = convert_file(ts, "config.ts")
        assert "pub struct Config" in result
        assert "pub const DEFAULT_PORT" in result
        assert "pub fn create_config" in result

    def test_async_await_class(self) -> None:
        ts = """
class ApiService {
    baseUrl: string;

    async fetchData(url: string): Promise<string> {
        const response = await fetch(url);
        return response.text();
    }
}
"""
        result = convert_file(ts, "api.ts")
        assert "pub struct ApiService" in result
        assert "impl ApiService" in result
        assert "pub async fn fetch_data" in result
        assert ".await" in result

    def test_try_catch_with_logging(self) -> None:
        ts = """
function safeParse(input: string): string {
    try {
        const result = JSON.parse(input);
        return JSON.stringify(result);
    } catch (e) {
        console.error(e);
        return "{}";
    }
}
"""
        result = convert_file(ts, "parse.ts")
        assert "pub fn safe_parse" in result
        assert "serde_json::from_str" in result
        assert "serde_json::to_string" in result
        assert "tracing::error!" in result
        assert "Result" in result

    def test_enum_with_switch(self) -> None:
        ts = """
enum Status { Active, Inactive, Pending }

function describe(s: Status): string {
    switch (s) {
        case Status.Active:
            return "active";
        default:
            return "other";
    }
}
"""
        result = convert_file(ts, "status.ts")
        assert "pub enum Status" in result
        assert "match s {" in result

    def test_interface_with_optional_fields(self) -> None:
        ts = """
interface User {
    // The user's name
    name: string;
    age: number;
    email?: string;
    role?: string;
}
"""
        result = convert_file(ts, "user.ts")
        assert "pub struct User" in result
        assert "// The user's name" in result
        assert "Option<String>" in result

    def test_arrow_functions_and_map(self) -> None:
        ts = """
const items = [1, 2, 3];
const doubled = items.map((x) => x * 2);
const filtered = items.filter((x) => x > 1);
const found = items.find((x) => x === 2);
"""
        result = convert_file(ts, "arr.ts")
        assert "vec![1, 2, 3]" in result
        assert "iter().map" in result
        assert "iter().filter" in result
        assert "iter().find" in result

    def test_template_strings(self) -> None:
        ts = """
const name = "world";
const msg = `Hello, ${name}! Today is ${day}.`;
"""
        result = convert_file(ts, "tpl.ts")
        assert "format!" in result
        assert "Hello, {}! Today is {}." in result

    def test_destructuring_and_spread(self) -> None:
        ts = """
const { name, age } = user;
const [first, second] = items;
const merged = { ...defaults, ...overrides };
"""
        result = convert_file(ts, "destr.ts")
        assert "_destructured" in result
        assert "_arr" in result
        assert ".." in result


class TestConvertDirectory:
    """Tests for convert_directory."""

    def test_converts_directory(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            ts_dir = Path(td) / "ts_src"
            rs_dir = Path(td) / "rs_out"
            ts_dir.mkdir()
            (ts_dir / "hello.ts").write_text("export function hello() { }")
            (ts_dir / "world.ts").write_text("export const WORLD = 'earth';")
            count = convert_directory(str(ts_dir), str(rs_dir))
            assert count == 2
            assert (rs_dir / "hello.rs").exists()
            assert (rs_dir / "world.rs").exists()

    def test_skips_index_files(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            ts_dir = Path(td) / "src"
            rs_dir = Path(td) / "out"
            ts_dir.mkdir()
            (ts_dir / "index.ts").write_text("export {};")
            (ts_dir / "main.ts").write_text("const x = 1;")
            count = convert_directory(str(ts_dir), str(rs_dir))
            assert count == 1
            assert not (rs_dir / "index.rs").exists()

    def test_nested_directories(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            ts_dir = Path(td) / "src"
            rs_dir = Path(td) / "out"
            sub = ts_dir / "utils"
            sub.mkdir(parents=True)
            (sub / "helper.ts").write_text("export function help() { }")
            count = convert_directory(str(ts_dir), str(rs_dir))
            assert count == 1
            assert (rs_dir / "utils" / "helper.rs").exists()

    def test_tsx_files(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            ts_dir = Path(td) / "src"
            rs_dir = Path(td) / "out"
            ts_dir.mkdir()
            (ts_dir / "comp.tsx").write_text("const el = <div></div>;")
            count = convert_directory(str(ts_dir), str(rs_dir))
            assert count == 1


class TestFileHeader:
    """Tests for the file header comment."""

    def test_header_present(self) -> None:
        result = convert_file("const x = 1;", "myfile.ts")
        assert "//! Converted from myfile.ts" in result

    def test_tsx_header(self) -> None:
        result = convert_file("const x = 1;", "comp.tsx")
        assert "//! Converted from comp.tsx" in result


class TestImportSkipping:
    """Tests for import statement handling."""

    def test_imports_skipped(self) -> None:
        ts = """
import { foo } from './foo';
import * as bar from 'bar';
const x = 1;
"""
        result = convert_file(ts, "t.ts")
        assert "import" not in result
        assert "let x = 1;" in result

    def test_import_comment_skipped(self) -> None:
        ts = """// For the foo module
import { foo } from './foo';
const x = 1;
"""
        result = convert_file(ts, "t.ts")
        # Comment directly above import should be skipped
        assert "For the foo module" not in result
