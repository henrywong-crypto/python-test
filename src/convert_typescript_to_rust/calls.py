"""Call expression handlers for TypeScript-to-Rust conversion.

Handles ``Math.*``, ``console.*``, ``JSON.*``, ``Object.*``, ``Array.isArray``,
``Date.now``, ``axios.*``, common method renames, and top-level function calls.

All public functions return Rust AST nodes (``RsExpr``).
"""

from __future__ import annotations

from tree_sitter import Node

from .rust_ast import RsExpr, RsRawExpr

# Avoid circular import -- converter imports us, we import converter lazily.

_METHOD_MAP: dict[str, str] = {
    "push": "push",
    "pop": "pop",
    "includes": "contains",
    "toLowerCase": "to_lowercase()",
    "toUpperCase": "to_uppercase()",
    "startsWith": "starts_with",
    "endsWith": "ends_with",
    "trim": "trim()",
    "trimStart": "trim_start()",
    "trimEnd": "trim_end()",
    "replace": "replace",
    "replaceAll": "replace",
    "split": "split",
    "join": "join",
    "map": "iter().map",
    "filter": "iter().filter",
    "find": "iter().find",
    "some": "iter().any",
    "every": "iter().all",
    "forEach": "iter().for_each",
    "flatMap": "iter().flat_map",
    "flat": "into_iter().flatten().collect::<Vec<_>>()",
    "sort": "sort()",
    "reverse": "reverse()",
    "keys": "keys()",
    "values": "values()",
    "slice": "get",
    "splice": "drain",
    "catch": "ok()",
    "then": "and_then",
}


def _math_call(method: str, args: str) -> str:
    """Convert ``Math.<method>(args)`` to Rust.

    Args:
        method: The Math method name (e.g. ``"floor"``).
        args: The already-converted argument string.

    Returns:
        The Rust expression string.
    """
    if method == "floor":
        return f"({args} as f64).floor()"
    if method == "ceil":
        return f"({args} as f64).ceil()"
    if method == "round":
        return f"({args} as f64).round()"
    if method == "abs":
        return f"({args} as f64).abs()"
    if method == "sqrt":
        return f"({args} as f64).sqrt()"
    if method == "log":
        return f"({args} as f64).ln()"
    if method == "log2":
        return f"({args} as f64).log2()"
    if method == "log10":
        return f"({args} as f64).log10()"
    if method == "trunc":
        return f"({args} as f64).trunc()"
    if method == "sign":
        return f"({args} as f64).signum()"
    if method == "pow":
        parts = args.split(",", 1)
        if len(parts) == 2:
            return f"({parts[0].strip()} as f64).powf({parts[1].strip()} as f64)"
    if method == "max":
        parts = args.split(",", 1)
        if len(parts) == 2:
            return f"({parts[0].strip()} as f64).max({parts[1].strip()} as f64)"
        return "f64::MAX"
    if method == "min":
        parts = args.split(",", 1)
        if len(parts) == 2:
            return f"({parts[0].strip()} as f64).min({parts[1].strip()} as f64)"
        return "f64::MIN"
    if method == "random":
        return "rand::random::<f64>()"
    if method == "PI":
        return "std::f64::consts::PI"
    return f"f64::{method}({args})"


def _console_call(method: str, args: str) -> str:
    """Convert ``console.<method>(args)`` to tracing macros.

    Args:
        method: The console method name (e.g. ``"error"``).
        args: The already-converted argument string.

    Returns:
        The Rust ``tracing::*!`` macro call.
    """
    if method == "error":
        return f'tracing::error!("{{}}", {args})'
    if method == "warn":
        return f'tracing::warn!("{{}}", {args})'
    if method == "debug":
        return f'tracing::debug!("{{}}", {args})'
    return f'tracing::info!("{{}}", {args})'


def _call(node: Node) -> RsExpr:
    """Convert a ``call_expression`` node to a Rust AST expression.

    Dispatches to ``_math_call``, ``_console_call``, or method-map lookups as
    appropriate. Falls back to a direct function call.

    Returns:
        An ``RsExpr`` node.
    """
    from .converter import convert_expr, _fmt_expr
    from .helpers import _snake
    from .expressions import _args

    func = node.child_by_field_name("function") or node.children[0]
    args_node = None
    for ch in node.children:
        if ch.type == "arguments":
            args_node = ch
            break

    if func.type == "member_expression":
        obj_node = func.child_by_field_name("object") or func.children[0]
        prop_node = func.child_by_field_name("property") or func.children[-1]
        obj_expr = convert_expr(obj_node)
        obj_s = _fmt_expr(obj_expr)
        prop = prop_node.text.decode() if prop_node else ""
        args_s = _args(args_node)

        # Math.*
        if obj_s == "f64" or obj_node.text.decode() == "Math":
            return RsRawExpr(text=_math_call(prop, args_s))

        # console.*
        if obj_s == "tracing" or obj_node.text.decode() == "console":
            return RsRawExpr(text=_console_call(prop, args_s))

        # JSON.*
        if obj_s == "serde_json" or obj_node.text.decode() == "JSON":
            if prop == "stringify":
                return RsRawExpr(text=f"serde_json::to_string(&{args_s}).unwrap_or_default()")
            if prop == "parse":
                return RsRawExpr(text=f"serde_json::from_str({args_s}).unwrap_or_default()")

        # Array.isArray
        if obj_node.text.decode() == "Array" and prop == "isArray":
            return RsRawExpr(text=f"{args_s}.is_array()")

        # Object.*
        if obj_node.text.decode() == "Object":
            if prop == "keys":
                return RsRawExpr(text=f"{args_s}.keys().cloned().collect::<Vec<_>>()")
            if prop == "values":
                return RsRawExpr(text=f"{args_s}.values().cloned().collect::<Vec<_>>()")
            if prop == "entries":
                return RsRawExpr(text=f"{args_s}.iter().collect::<Vec<_>>()")
            if prop == "assign":
                return RsRawExpr(text=f"/* Object.assign({args_s}) */")

        # axios.*
        if obj_node.text.decode() == "axios":
            method = prop.lower()
            if method in ("get", "post", "put", "delete", "patch"):
                return RsRawExpr(text=f"reqwest::Client::new().{method}({args_s}).send().await")

        # Date.now()
        if obj_node.text.decode() == "Date" and prop == "now":
            return RsRawExpr(text="std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().as_millis() as f64")

        # process.*
        if obj_node.text.decode() == "process":
            if prop == "exit":
                return RsRawExpr(text=f"std::process::exit({args_s} as i32)")
            if prop == "cwd":
                return RsRawExpr(text="std::env::current_dir().unwrap().to_string_lossy().to_string()")

        # .toFixed(n)
        if prop == "toFixed":
            n = args_s.strip() if args_s else "0"
            return RsRawExpr(text=f'format!("{{:.{n}}}", {obj_s})')

        # .test(x)
        if prop == "test":
            return RsRawExpr(text=f"{obj_s}.is_match({args_s})")

        # .match(x)
        if prop == "match":
            return RsRawExpr(text=f"{obj_s}.find({args_s})")
        if prop == "matchAll":
            return RsRawExpr(text=f"{obj_s}.find_iter({args_s})")

        # .toString(radix)
        if prop == "toString":
            if args_s.strip() in ('"hex"', "'hex'", "16"):
                return RsRawExpr(text=f'format!("{{:x}}", {obj_s})')
            return RsRawExpr(text=f"{obj_s}.to_string()")

        # indexOf special case
        if prop == "indexOf":
            return RsRawExpr(text=f"{obj_s}.find({args_s})")

        # shift special case (no args, always remove first element)
        if prop == "shift":
            return RsRawExpr(text=f"{obj_s}.remove(0)")

        # Common method renames
        if prop in _METHOD_MAP:
            rs_method = _METHOD_MAP[prop]
            if rs_method == "__special__":
                pass  # handled above
            elif rs_method.endswith("()"):
                return RsRawExpr(text=f"{obj_s}.{rs_method}")
            else:
                return RsRawExpr(text=f"{obj_s}.{rs_method}({args_s})")

        # Default member call
        prop_s = _snake(prop)
        return RsRawExpr(text=f"{obj_s}.{prop_s}({args_s})")

    # Top-level function calls
    func_expr = convert_expr(func)
    func_s = _fmt_expr(func_expr)
    args_s = _args(args_node)

    if func_s == "i64::from_str_radix":
        return RsRawExpr(text=f"{args_s}.parse::<i64>().unwrap_or(0)")
    if func_s == "f64::from_str":
        return RsRawExpr(text=f"{args_s}.parse::<f64>().unwrap_or(0.0)")
    if func_s == "is_na_n":
        return RsRawExpr(text=f"{args_s}.is_nan()")
    if func_s == "is_finite":
        return RsRawExpr(text=f"{args_s}.is_finite()")
    if func_s == "set_timeout":
        return RsRawExpr(text=f"tokio::time::sleep(std::time::Duration::from_millis({args_s} as u64)).await")
    if func_s == "set_interval":
        return RsRawExpr(text=f"/* setInterval({args_s}) */")
    if func_s in ("clear_timeout", "clear_interval"):
        return RsRawExpr(text=f"/* {func_s}({args_s}) */")

    return RsRawExpr(text=f"{func_s}({args_s})")
