"""Benchmark tool for measuring conversion quality.

Compares the TypeScript AST structure against the generated Rust output to
measure conversion fidelity across constructs, comments, and exports.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Any

from tree_sitter import Parser, Node

from . import convert_file, TS_LANGUAGE, TSX_LANGUAGE
from .converter import c


def count_ast_nodes(node: Node, *, named_only: bool = True) -> int:
    """Count all AST nodes recursively.

    Args:
        node: The root tree-sitter node.
        named_only: If ``True``, count only named nodes.

    Returns:
        The total node count.
    """
    count = 1 if (not named_only or node.is_named) else 0
    for ch in node.children:
        count += count_ast_nodes(ch, named_only=named_only)
    return count


def collect_node_types(
    node: Node, depth: int = 0, max_depth: int = 50
) -> list[tuple[str, int]]:
    """Collect ``(type, depth)`` pairs from the AST.

    Args:
        node: The tree-sitter node.
        depth: Current depth.
        max_depth: Maximum recursion depth.

    Returns:
        A list of ``(node_type, depth)`` tuples.
    """
    results: list[tuple[str, int]] = []
    if node.is_named and node.type not in ("program",):
        results.append((node.type, depth))
    if depth < max_depth:
        for ch in node.children:
            results.extend(collect_node_types(ch, depth + 1, max_depth))
    return results


def benchmark_file(ts_path: str) -> dict[str, Any]:
    """Benchmark conversion of a single TypeScript file.

    Args:
        ts_path: Path to the TypeScript file.

    Returns:
        A dictionary with benchmark metrics.
    """
    tp = Path(ts_path)
    ts_content = tp.read_text(errors="replace")
    lang = TSX_LANGUAGE if ts_path.endswith(".tsx") else TS_LANGUAGE
    parser = Parser(lang)
    ts_tree = parser.parse(ts_content.encode())

    rs_content = convert_file(ts_content, ts_path)

    ts_nodes = collect_node_types(ts_tree.root_node)
    ts_total = len(ts_nodes)

    def _count_comments(node: Node) -> int:
        n = 1 if node.type == "comment" else 0
        for ch in node.children:
            n += _count_comments(ch)
        return n

    ts_comments = _count_comments(ts_tree.root_node)

    rs_comment_matches = 0

    def _check_comments(node: Node) -> None:
        nonlocal rs_comment_matches
        if node.type == "comment":
            if node.text.decode().strip() in rs_content:
                rs_comment_matches += 1
        for ch in node.children:
            _check_comments(ch)

    _check_comments(ts_tree.root_node)

    construct_map: dict[str, str] = {
        "function_declaration": "functions",
        "generator_function_declaration": "functions",
        "arrow_function": "functions",
        "class_declaration": "classes",
        "abstract_class_declaration": "classes",
        "interface_declaration": "interfaces",
        "type_alias_declaration": "type_aliases",
        "enum_declaration": "enums",
        "lexical_declaration": "variables",
        "variable_declaration": "variables",
        "if_statement": "if_statements",
        "for_statement": "for_loops",
        "for_in_statement": "for_loops",
        "while_statement": "while_loops",
        "do_statement": "while_loops",
        "switch_statement": "switch_statements",
        "try_statement": "try_catch",
        "return_statement": "return_statements",
    }

    ts_constructs: dict[str, int] = {
        "functions": 0, "classes": 0, "interfaces": 0,
        "type_aliases": 0, "enums": 0, "variables": 0,
        "if_statements": 0, "for_loops": 0, "while_loops": 0,
        "switch_statements": 0, "try_catch": 0, "return_statements": 0,
    }
    for node_type, _ in ts_nodes:
        if node_type in construct_map:
            ts_constructs[construct_map[node_type]] += 1

    rs_constructs: dict[str, int] = {
        "functions": len(re.findall(r"\bfn\s+\w+", rs_content))
        + len(re.findall(r"\|[^|]*\|\s*\{", rs_content)),
        "classes": len(re.findall(r"\bstruct\s+\w+", rs_content)),
        "interfaces": len(re.findall(r"\bstruct\s+\w+", rs_content)),
        "type_aliases": len(re.findall(r"\btype\s+\w+\s*=", rs_content))
        + len(re.findall(r"\bstruct\s+\w+", rs_content)),
        "enums": len(re.findall(r"\benum\s+\w+", rs_content)),
        "variables": len(re.findall(r"\blet\s+", rs_content)),
        "if_statements": len(re.findall(r"\bif\s+", rs_content)),
        "for_loops": len(re.findall(r"\bfor\s+\w+\s+in\b", rs_content)),
        "while_loops": len(re.findall(r"\bwhile\s+", rs_content)),
        "switch_statements": len(re.findall(r"\bmatch\s+", rs_content)),
        "try_catch": len(re.findall(r"Result.*Error", rs_content)),
        "return_statements": len(re.findall(r"\breturn\b", rs_content)),
    }

    exported_count = 0
    exported_empty = 0
    for node in ts_tree.root_node.children:
        if node.type == "export_statement":
            exported_count += 1
            result = c(node, 0)
            if not result or not result.strip():
                exported_empty += 1

    return {
        "file": ts_path,
        "ts_ast_nodes": ts_total,
        "ts_comments": ts_comments,
        "rs_comments_matched": rs_comment_matches,
        "comment_pct": (
            rs_comment_matches / ts_comments * 100 if ts_comments > 0 else 100.0
        ),
        "ts_constructs": ts_constructs,
        "rs_constructs": rs_constructs,
        "exports_total": exported_count,
        "exports_empty": exported_empty,
        "export_pct": (
            (exported_count - exported_empty) / exported_count * 100
            if exported_count > 0
            else 100.0
        ),
    }


def run_benchmark(
    ts_root: str = "src", max_files: int = 0
) -> dict[str, Any]:
    """Run benchmark across all TypeScript files in a directory.

    Args:
        ts_root: Root directory to scan.
        max_files: Maximum number of files to benchmark (0 = unlimited).

    Returns:
        Aggregated totals dictionary.
    """
    ts_files = sorted(str(p) for p in Path(ts_root).rglob("*.ts"))
    ts_files += sorted(str(p) for p in Path(ts_root).rglob("*.tsx"))
    if max_files > 0:
        ts_files = ts_files[:max_files]

    totals: dict[str, Any] = {
        "files": 0,
        "ts_comments": 0,
        "rs_comments_matched": 0,
        "exports_total": 0,
        "exports_empty": 0,
        "ts_constructs": {},
        "rs_constructs": {},
    }

    for ts_file in ts_files:
        if Path(ts_file).stem == "index":
            continue
        try:
            result = benchmark_file(ts_file)
            totals["files"] += 1
            totals["ts_comments"] += result["ts_comments"]
            totals["rs_comments_matched"] += result["rs_comments_matched"]
            totals["exports_total"] += result["exports_total"]
            totals["exports_empty"] += result["exports_empty"]
            for k in result["ts_constructs"]:
                totals["ts_constructs"][k] = (
                    totals["ts_constructs"].get(k, 0) + result["ts_constructs"][k]
                )
                totals["rs_constructs"][k] = (
                    totals["rs_constructs"].get(k, 0) + result["rs_constructs"][k]
                )
        except Exception:
            pass

    return totals


def print_benchmark(totals: dict[str, Any]) -> None:
    """Print formatted benchmark results to stdout.

    Args:
        totals: The aggregated totals from ``run_benchmark``.
    """
    print("=" * 65)
    print("  convert-typescript-to-rust CONVERSION BENCHMARK (AST-level)")
    print("=" * 65)
    print()
    print(f"Files benchmarked: {totals['files']}")
    print()

    tc = totals["ts_comments"]
    rc = totals["rs_comments_matched"]
    if tc > 0:
        print(f"COMMENTS: {rc}/{tc} ({rc / tc * 100:.1f}%)")
    else:
        print("COMMENTS: 0/0 (100.0%)")
    print()

    et = totals["exports_total"]
    ee = totals["exports_empty"]
    if et > 0:
        print(f"EXPORTS: {et - ee}/{et} converted ({(et - ee) / et * 100:.1f}%)")
    else:
        print("EXPORTS: 0/0 (100.0%)")
    print()

    print(f"{'Construct':<20} {'TS':>8} {'RS':>8} {'Ratio':>8}")
    print("-" * 48)
    for k in sorted(totals["ts_constructs"].keys()):
        t = totals["ts_constructs"][k]
        r = totals["rs_constructs"].get(k, 0)
        ratio = r / t * 100 if t > 0 else 100.0
        marker = "+" if ratio >= 85 else "~" if ratio >= 50 else "-"
        print(f"  {k:<18} {t:>7,} {r:>7,} {ratio:>6.1f}% {marker}")
    print()

    total_ts = sum(totals["ts_constructs"].values())
    total_rs = sum(totals["rs_constructs"].values())
    construct_ratio = total_rs / total_ts * 100 if total_ts > 0 else 100
    comment_ratio = rc / tc * 100 if tc > 0 else 100
    export_ratio = (et - ee) / et * 100 if et > 0 else 100

    score = construct_ratio * 0.5 + comment_ratio * 0.3 + export_ratio * 0.2
    print(f"OVERALL SCORE: {score:.1f}/100")
    print(f"  Code constructs: {construct_ratio:.1f}%  (weight 50%)")
    print(f"  Comments:        {comment_ratio:.1f}%  (weight 30%)")
    print(f"  Exports:         {export_ratio:.1f}%  (weight 20%)")


if __name__ == "__main__":
    max_f = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    t = run_benchmark("src", max_f)
    print_benchmark(t)
