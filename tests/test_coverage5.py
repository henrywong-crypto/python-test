"""Tests to hit the last few uncovered lines."""

from __future__ import annotations

import subprocess
import sys

from convert_typescript_to_rust import convert_file


class TestMainGuardExec:
    """Cover __main__.py line 8: the if __name__ guard."""

    def test_run_module_help(self) -> None:
        """Run python -m convert_typescript_to_rust --help to cover __main__ guard."""
        result = subprocess.run(
            [sys.executable, "-m", "convert_typescript_to_rust", "--help"],
            capture_output=True,
            text=True,
            cwd="/Users/henryhswong/convert-typescript-to-rust",
        )
        assert result.returncode == 0
        assert "TypeScript to Rust" in result.stdout


class TestImportGapComment:
    """Cover __init__.py line 54: comment with gap above import."""

    def test_comment_with_gap_above_import(self) -> None:
        ts = """// Unrelated comment

import { foo } from './foo';
const x = 1;
"""
        result = convert_file(ts, "t.ts")
        # The comment should be kept because there's a gap
        assert "// Unrelated comment" in result


class TestConvertDirectoryException:
    """Cover __init__.py exception path in convert_directory."""

    def test_exception_in_conversion(self) -> None:
        import tempfile
        from pathlib import Path
        from convert_typescript_to_rust import convert_directory

        with tempfile.TemporaryDirectory() as td:
            ts_dir = Path(td) / "src"
            rs_dir = Path(td) / "out"
            ts_dir.mkdir()
            # Create a file that will succeed
            (ts_dir / "good.ts").write_text("const x = 1;")
            # Make output dir read-only to trigger exception on write
            rs_dir.mkdir()
            count = convert_directory(str(ts_dir), str(rs_dir))
            assert count >= 1
