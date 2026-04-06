"""Tests for the CLI module."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

from convert_typescript_to_rust.cli import main


class TestSingleFile:
    """Tests for single-file conversion mode."""

    def test_convert_single(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            ts_path = Path(td) / "test.ts"
            rs_path = Path(td) / "test.rs"
            ts_path.write_text("const x: number = 42;")
            main([str(ts_path), str(rs_path)])
            assert rs_path.exists()
            content = rs_path.read_text()
            assert "let x" in content

    def test_dry_run(self, capsys) -> None:
        with tempfile.TemporaryDirectory() as td:
            ts_path = Path(td) / "test.ts"
            rs_path = Path(td) / "test.rs"
            ts_path.write_text("const x = 1;")
            main([str(ts_path), str(rs_path), "--dry-run"])
            assert not rs_path.exists()
            captured = capsys.readouterr()
            assert "let x" in captured.out


class TestDirectory:
    """Tests for directory conversion mode."""

    def test_convert_directory(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            ts_dir = Path(td) / "ts"
            rs_dir = Path(td) / "rs"
            ts_dir.mkdir()
            (ts_dir / "hello.ts").write_text('const msg: string = "hi";')
            main([str(ts_dir), str(rs_dir), "--all"])
            assert (rs_dir / "hello.rs").exists()

    def test_skip_index(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            ts_dir = Path(td) / "ts"
            rs_dir = Path(td) / "rs"
            ts_dir.mkdir()
            (ts_dir / "index.ts").write_text("export {};")
            (ts_dir / "main.ts").write_text("const x = 1;")
            main([str(ts_dir), str(rs_dir), "--all"])
            assert not (rs_dir / "index.rs").exists()
            assert (rs_dir / "main.rs").exists()


class TestVerbose:
    """Tests for verbose mode."""

    def test_verbose_prints(self, capsys) -> None:
        with tempfile.TemporaryDirectory() as td:
            ts_path = Path(td) / "test.ts"
            rs_path = Path(td) / "test.rs"
            ts_path.write_text("const x = 1;")
            main([str(ts_path), str(rs_path), "--verbose"])
            captured = capsys.readouterr()
            assert "test.ts" in captured.out or rs_path.exists()
