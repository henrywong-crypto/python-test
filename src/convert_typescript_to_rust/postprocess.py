"""Post-processing for patterns that require cross-node context.

Applies regex-based fixups that cannot be handled at the single-node AST
level, such as ``typeof`` checks and ``process.env`` access.
"""

from __future__ import annotations

import re


_TYPEOF_MAP: dict[str, str] = {
    "string": "is_string",
    "number": "is_number",
    "boolean": "is_boolean",
    "object": "is_object",
    "undefined": "is_null",
    "function": "is_object",
}


def postprocess(code: str) -> str:
    """Fix patterns that require cross-node context not available in the AST walker.

    Currently handles:

    * ``_typeof_(x) == "string"`` -> ``x.is_string()``
    * ``_typeof_(x) != "string"`` -> ``!x.is_string()``
    * remaining ``_typeof_(x)`` -> ``/* typeof x */``
    * ``std::process.env.X`` -> ``std::env::var("X").unwrap_or_default()``

    Args:
        code: The raw Rust source produced by the AST walker.

    Returns:
        The post-processed Rust source.
    """
    for ts_type, rs_method in _TYPEOF_MAP.items():
        code = code.replace(
            '_typeof_({}) == "' + ts_type + '"', '{}.%s()' % rs_method
        )
    for ts_type, rs_method in _TYPEOF_MAP.items():
        code = re.sub(
            rf'_typeof_\((\w+)\) == "{ts_type}"',
            rf"\1.{rs_method}()",
            code,
        )
        code = re.sub(
            rf'_typeof_\((\w+)\) != "{ts_type}"',
            rf"!\1.{rs_method}()",
            code,
        )
    code = re.sub(r"_typeof_\((\w+)\)", r"/* typeof \1 */", code)
    code = re.sub(
        r'std::process\.env\.(\w+)',
        r'std::env::var("\1").unwrap_or_default()',
        code,
    )
    return code
