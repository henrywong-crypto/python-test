"""Tests for the benchmark module."""

from __future__ import annotations

import tempfile
from pathlib import Path

from convert_typescript_to_rust.benchmark import (
    benchmark_file,
    run_benchmark,
    print_benchmark,
    count_ast_nodes,
    collect_node_types,
)


class TestBenchmarkFile:
    """Tests for benchmark_file."""

    def test_basic_file(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "test.ts"
            p.write_text("export function greet(): string { return 'hi'; }")
            result = benchmark_file(str(p))
            assert result["ts_ast_nodes"] > 0
            assert result["exports_total"] >= 1
            assert "ts_constructs" in result
            assert "rs_constructs" in result

    def test_empty_file(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "empty.ts"
            p.write_text("")
            result = benchmark_file(str(p))
            assert result["ts_ast_nodes"] == 0

    def test_comment_matching(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "commented.ts"
            p.write_text("// important\nconst x = 1;")
            result = benchmark_file(str(p))
            assert result["ts_comments"] >= 1
            assert result["rs_comments_matched"] >= 1


class TestRunBenchmark:
    """Tests for run_benchmark."""

    def test_runs_without_error(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "test.ts"
            p.write_text("const x = 1;")
            totals = run_benchmark(td)
            assert totals["files"] >= 1

    def test_skips_index(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            (Path(td) / "index.ts").write_text("export {};")
            (Path(td) / "main.ts").write_text("const x = 1;")
            totals = run_benchmark(td)
            assert totals["files"] == 1

    def test_max_files(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            for i in range(5):
                (Path(td) / f"f{i}.ts").write_text(f"const x{i} = {i};")
            totals = run_benchmark(td, max_files=2)
            assert totals["files"] <= 2


class TestPrintBenchmark:
    """Tests for print_benchmark."""

    def test_prints_without_error(self, capsys) -> None:
        totals = {
            "files": 1,
            "ts_comments": 5,
            "rs_comments_matched": 4,
            "exports_total": 3,
            "exports_empty": 0,
            "ts_constructs": {"functions": 2, "variables": 1},
            "rs_constructs": {"functions": 2, "variables": 1},
        }
        print_benchmark(totals)
        captured = capsys.readouterr()
        assert "OVERALL SCORE" in captured.out
        assert "functions" in captured.out

    def test_handles_zero_comments(self, capsys) -> None:
        totals = {
            "files": 0,
            "ts_comments": 0,
            "rs_comments_matched": 0,
            "exports_total": 0,
            "exports_empty": 0,
            "ts_constructs": {},
            "rs_constructs": {},
        }
        print_benchmark(totals)
        captured = capsys.readouterr()
        assert "COMMENTS" in captured.out


class TestHelperFunctions:
    """Tests for count_ast_nodes and collect_node_types."""

    def test_count_ast_nodes(self, parse) -> None:
        root = parse("const x = 1;")
        count = count_ast_nodes(root)
        assert count > 0

    def test_collect_node_types(self, parse) -> None:
        root = parse("const x = 1;")
        types = collect_node_types(root)
        assert len(types) > 0
        node_type_names = [t for t, _ in types]
        assert "lexical_declaration" in node_type_names
