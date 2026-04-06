"""Command-line interface for convert-typescript-to-rust.

Provides ``convert-typescript-to-rust`` entry point with single-file mode,
directory mode (``--all``), ``--dry-run``, and ``--verbose`` flags.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import convert_file, convert_directory


def _convert_single(ts_path: str, rs_path: str, *, verbose: bool = False) -> None:
    """Convert a single TypeScript file and write the result.

    Args:
        ts_path: Path to the input TypeScript file.
        rs_path: Path for the output Rust file.
        verbose: If True, print extra information.
    """
    content = Path(ts_path).read_text(encoding="utf-8", errors="replace")
    rust_code = convert_file(content, ts_path)
    Path(rs_path).parent.mkdir(parents=True, exist_ok=True)
    Path(rs_path).write_text(rust_code)
    if verbose:
        print(f"  {ts_path} -> {rs_path}")


def main(argv: list[str] | None = None) -> None:
    """Entry point for the CLI.

    Args:
        argv: Optional argument list (defaults to ``sys.argv[1:]``).
    """
    parser = argparse.ArgumentParser(
        prog="convert-typescript-to-rust",
        description="TypeScript to Rust AST transpiler",
    )
    parser.add_argument("ts_path", help="TypeScript file or directory")
    parser.add_argument("rs_path", help="Rust output file or directory")
    parser.add_argument(
        "--all",
        action="store_true",
        help="Convert all .ts/.tsx files in directory",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print Rust output to stdout instead of writing files",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print extra progress information",
    )

    args = parser.parse_args(argv)

    if args.all:
        count = convert_directory(args.ts_path, args.rs_path)
        if args.verbose:
            print(f"Converted {count} files")
    else:
        if args.dry_run:
            content = Path(args.ts_path).read_text(encoding="utf-8", errors="replace")
            print(convert_file(content, args.ts_path))
        else:
            _convert_single(args.ts_path, args.rs_path, verbose=args.verbose)
