"""convert_typescript_to_rust -- TypeScript to Rust AST transpiler.

Public API for converting TypeScript source code to Rust using tree-sitter
for parsing, an AST-walking approach that builds a Rust AST intermediate
representation, and a formatter that renders the AST to source code.

Architecture:
    TS source -> tree-sitter parse -> converter (builds Rust AST nodes)
              -> formatter (renders to string) -> postprocess -> output
"""

from __future__ import annotations

from pathlib import Path

from .converter import c as _c, _fmt
from .postprocess import postprocess as _postprocess
from .rust_ast import RsFile, RsComment, RsRawStmt

__version__: str = "0.1.0"

# Re-export tree-sitter language objects for consumers and tests
from tree_sitter import Language, Parser
import tree_sitter_typescript as _ts_lang

TS_LANGUAGE: Language = Language(_ts_lang.language_typescript())
TSX_LANGUAGE: Language = Language(_ts_lang.language_tsx())


def convert_file(content: str, file_path: str = "<string>") -> str:
    """Convert a TypeScript source string to Rust source code.

    The conversion pipeline:
    1. Parse TypeScript with tree-sitter
    2. Walk the AST and build Rust AST nodes via converter modules
    3. Assemble an ``RsFile`` intermediate representation
    4. Format the ``RsFile`` to a string via the formatter
    5. Apply post-processing regex fixups

    Args:
        content: The TypeScript source text.
        file_path: Optional file path used for the header comment and to
            choose the correct tree-sitter language (TSX vs TS).

    Returns:
        The generated Rust source code as a string.
    """
    lang = TSX_LANGUAGE if file_path.endswith(".tsx") else TS_LANGUAGE
    parser = Parser(lang)
    tree = parser.parse(content.encode("utf-8"))
    parts: list[str] = [f"//! Converted from {file_path}\n"]
    prev_was_comment = False
    nodes = list(tree.root_node.children)

    # Pre-scan: mark comments that are immediately above import statements
    skip_indices: set[int] = set()
    for i, node in enumerate(nodes):
        if node.type == "import_statement":
            j = i - 1
            while j >= 0 and nodes[j].type == "comment":
                comment_end_line = nodes[j].end_point[0]
                next_start_line = nodes[j + 1].start_point[0]
                if next_start_line - comment_end_line <= 1:
                    skip_indices.add(j)
                    j -= 1
                else:
                    break

    for i, node in enumerate(nodes):
        if i in skip_indices:
            continue
        code = _c(node, 0)
        if code and code.strip():
            is_comment = code.strip().startswith("//") or code.strip().startswith("/*")
            if not prev_was_comment:
                parts.append("")
            parts.append(code)
            prev_was_comment = is_comment
    raw = "\n".join(parts)
    raw = _postprocess(raw)
    return raw


def convert_directory(ts_dir: str, rs_dir: str) -> int:
    """Convert all TypeScript files in *ts_dir*, writing Rust files to *rs_dir*.

    The directory structure is mirrored.  ``index.ts`` files are skipped.

    Args:
        ts_dir: Root directory containing TypeScript files.
        rs_dir: Root directory for Rust output files.

    Returns:
        The number of files successfully converted.
    """
    from .helpers import _snake

    ts_root = Path(ts_dir)
    rs_root = Path(rs_dir)
    converted = 0

    all_files: list[Path] = []
    all_files.extend(sorted(ts_root.rglob("*.ts")))
    all_files.extend(sorted(ts_root.rglob("*.tsx")))

    for ts_file in all_files:
        if ts_file.suffix not in (".ts", ".tsx"):
            continue
        if ts_file.stem == "index":
            continue
        try:
            rel = ts_file.relative_to(ts_root)
            parts = list(rel.parts)
            stem = parts[-1].replace(".tsx", "").replace(".ts", "")
            rs_stem = _snake(stem)
            rs_dirs = [_snake(d) for d in parts[:-1]]
            rs_path = rs_root
            for d in rs_dirs:
                rs_path = rs_path / d
            rs_path = rs_path / f"{rs_stem}.rs"

            content = ts_file.read_text(encoding="utf-8", errors="replace")
            rust_code = convert_file(content, str(ts_file))
            rs_path.parent.mkdir(parents=True, exist_ok=True)
            rs_path.write_text(rust_code)
            converted += 1
        except Exception:
            pass

    return converted


__all__ = ["convert_file", "convert_directory", "__version__"]
