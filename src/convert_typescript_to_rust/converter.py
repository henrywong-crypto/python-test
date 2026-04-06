"""Core AST walker for TypeScript-to-Rust conversion.

The ``c(node, ind)`` function is the main dispatch point. It examines each
tree-sitter node's type and delegates to the appropriate handler in the
``types``, ``calls``, ``declarations``, ``statements``, and ``expressions``
modules.
"""

from __future__ import annotations

import re
from tree_sitter import Node

from .types import convert_type, _TYPE_MAP
from .helpers import (
    _snake,
    _ident,
    _strip_parens,
    _trailing_comments,
)
from .calls import _call
from .declarations import (
    _function,
    _class,
    _interface,
    _enum,
    _export,
    _type_alias,
)
from .statements import (
    _var_decl,
    _var_declarator_line,
    _if_stmt,
    _for_c,
    _for_in,
    _switch,
    _try,
    _block_body,
)
from .expressions import _template, _arrow, _object, _args


def c(node: Node | None, ind: int = 0) -> str:
    """Convert ANY tree-sitter node to Rust code.

    This is the main recursive dispatch function. It pattern-matches on the
    node type and either handles the conversion inline (for simple cases) or
    delegates to a specialised handler function.

    Args:
        node: The tree-sitter ``Node`` to convert, or ``None``.
        ind: Current indentation level (0-based, each level = 4 spaces).

    Returns:
        The Rust source code fragment for this node.
    """
    if node is None:
        return ""
    t = node.type
    tx = node.text.decode()
    P = "    " * ind

    # --- Literals ---
    if t == "number":
        return tx
    if t == "string":
        if tx.startswith("'") and tx.endswith("'"):
            inner = tx[1:-1].replace('"', '\\"').replace("\\'", "'")
            return f'"{inner}"'
        return tx
    if t in ("string_fragment", "escape_sequence"):
        return tx
    if t in ("true", "false"):
        return tx
    if t in ("null", "undefined"):
        return "None"
    if t == "this":
        return "self"
    if t == "super":
        return "super"
    if t == "regex":
        m = re.match(r"^/(.+)/([gimsuy]*)$", tx, re.DOTALL)
        if m:
            return f'regex::Regex::new(r#"{m.group(1)}"#).unwrap()'
        return f'regex::Regex::new(r#"{tx}"#).unwrap()'

    # --- Identifiers ---
    if t == "identifier":
        return _ident(tx)
    if t == "property_identifier":
        return _snake(tx)
    if t == "shorthand_property_identifier":
        return _snake(tx)
    if t == "shorthand_property_identifier_pattern":
        return _snake(tx)
    if t == "type_identifier":
        return _TYPE_MAP.get(tx, tx)

    # --- Template strings ---
    if t == "template_string":
        return _template(node, ind)
    if t == "template_substitution":
        for ch in node.children:
            if ch.is_named:
                return c(ch, ind)
        return ""

    # --- Binary ---
    if t == "binary_expression":
        parts = list(node.children)
        tc = _trailing_comments(node)
        if len(parts) >= 3:
            op_text = parts[1].text.decode()
            if op_text == "===":
                op_text = "=="
            elif op_text == "!==":
                op_text = "!="
            elif op_text == "instanceof":
                result = f"{c(parts[0], ind)}.downcast_ref::<{c(parts[2], ind)}>().is_some()"
                return f"{result} {tc}" if tc else result
            elif op_text == "in":
                result = f"{c(parts[2], ind)}.contains_key({c(parts[0], ind)})"
                return f"{result} {tc}" if tc else result
            result = f"{c(parts[0], ind)} {op_text} {c(parts[2], ind)}"
            return f"{result} {tc}" if tc else result

    # --- Unary ---
    if t == "unary_expression":
        parts = list(node.children)
        op = parts[0].text.decode()
        operand = c(parts[1], ind) if len(parts) > 1 else ""
        if op == "typeof":
            return f"_typeof_({operand})"
        if op == "void":
            return f"{{ let _ = {operand}; }}"
        if op == "delete":
            return f"{operand}.take()"
        if op == "!" and parts[1].type == "identifier":
            return f"{operand}.is_none()"
        return f"{op}{operand}"

    # --- Update ---
    if t == "update_expression":
        parts = list(node.children)
        if parts[0].text.decode() in ("++", "--"):
            op = "+= 1" if parts[0].text.decode() == "++" else "-= 1"
            return f"{{ {c(parts[1], ind)} {op} }}"
        op = "+= 1" if parts[1].text.decode() == "++" else "-= 1"
        return f"{{ let _v = {c(parts[0], ind)}; {c(parts[0], ind)} {op}; _v }}"

    # --- Assignment ---
    if t in ("assignment_expression", "augmented_assignment_expression"):
        parts = list(node.children)
        if len(parts) >= 3:
            return f"{c(parts[0], ind)} {parts[1].text.decode()} {c(parts[2], ind)}"

    # --- Ternary ---
    if t == "ternary_expression":
        parts = [ch for ch in node.children if ch.is_named]
        if len(parts) >= 3:
            return f"if {c(parts[0], ind)} {{ {c(parts[1], ind)} }} else {{ {c(parts[2], ind)} }}"

    # --- Parens ---
    if t == "parenthesized_expression":
        named = [ch for ch in node.children if ch.is_named]
        if named:
            return f"({c(named[0], ind)})"
        return f"({tx[1:-1]})"

    # --- Member access ---
    if t == "member_expression":
        obj = node.child_by_field_name("object") or node.children[0]
        prop = node.child_by_field_name("property") or node.children[-1]
        optional = any(ch.type == "?." for ch in node.children)
        tc = _trailing_comments(node)
        obj_s = c(obj, ind)
        prop_s = _snake(prop.text.decode()) if prop else ""
        if prop_s == "length":
            result = f"{obj_s}.len()"
        elif prop_s == "prototype":
            result = obj_s
        elif optional:
            result = f"{obj_s}.as_ref().and_then(|v| v.{prop_s})"
        else:
            result = f"{obj_s}.{prop_s}"
        return f"{result} {tc}" if tc else result

    # --- Subscript ---
    if t == "subscript_expression":
        obj = node.children[0]
        idx = None
        for ch in node.children:
            if ch.type not in ("[", "]") and ch != obj and ch.is_named:
                idx = ch
                break
        return f"{c(obj, ind)}[{c(idx, ind)}]"

    # --- Call ---
    if t == "call_expression":
        return _call(node, ind)

    if t == "arguments":
        return _args(node, ind)

    # --- New ---
    if t == "new_expression":
        named = [ch for ch in node.children if ch.is_named]
        cls_s = c(named[0], ind) if named else "Unknown"
        args_node = None
        for ch in node.children:
            if ch.type == "arguments":
                args_node = ch
        args_s = _args(args_node, ind)
        if cls_s in ("std::collections::HashMap", "HashMap"):
            return "std::collections::HashMap::new()"
        if cls_s in ("std::collections::HashSet", "HashSet"):
            return "std::collections::HashSet::new()"
        if cls_s == "Vec":
            if args_s:
                return f"Vec::with_capacity({args_s})"
            return "Vec::new()"
        if cls_s in ("regex::Regex", "Regex"):
            return f"regex::Regex::new({args_s}).unwrap()"
        return f"{cls_s}::new({args_s})"

    # --- Await ---
    if t == "await_expression":
        named = [ch for ch in node.children if ch.is_named]
        if named:
            return f"{c(named[0], ind)}.await"
        return ".await"

    # --- Arrow ---
    if t == "arrow_function":
        return _arrow(node, ind)

    # --- Object ---
    if t == "object":
        return _object(node, ind)

    # --- Array ---
    if t == "array":
        elems: list[str] = []
        comments: list[str] = []
        for ch in node.children:
            if ch.type == "comment":
                comments.append(ch.text.decode())
            elif ch.is_named:
                elems.append(c(ch, ind))
        inner = ", ".join(elems)
        if comments:
            comment_str = "\n".join(f"{P}{cm}" for cm in comments)
            return f"{comment_str}\nvec![{inner}]"
        return f"vec![{inner}]"

    # --- Pair ---
    if t == "pair":
        named = [ch for ch in node.children if ch.is_named]
        if len(named) >= 2:
            key = named[0].text.decode().strip("'\"")
            return f'"{key}": {c(named[1], ind)}'
        return tx

    # --- Spread ---
    if t == "spread_element":
        named = [ch for ch in node.children if ch.is_named]
        if named:
            return f"/* ...{c(named[0], ind)} */"
        return "/* spread */"

    # --- Type casts (drop) ---
    if t in ("as_expression", "satisfies_expression", "type_assertion"):
        named = [ch for ch in node.children if ch.is_named]
        return c(named[0], ind) if named else ""

    # --- Non-null assertion ---
    if t in ("non_null_assertion_expression", "non_null_expression"):
        named = [ch for ch in node.children if ch.is_named]
        return f"{c(named[0], ind)}.unwrap()" if named else ".unwrap()"

    # --- Sequence ---
    if t == "sequence_expression":
        named = [ch for ch in node.children if ch.is_named]
        return "; ".join(c(x, ind) for x in named)

    # --- Yield ---
    if t == "yield_expression":
        named = [ch for ch in node.children if ch.is_named]
        return f"yield {c(named[0], ind)}" if named else "yield"

    # =============== STATEMENTS ===============

    if t == "expression_statement":
        named = [ch for ch in node.children if ch.is_named]
        tc = _trailing_comments(node)
        expr = f"{P}{c(named[0], ind)};" if named else ""
        if tc:
            return f"{expr} {tc}"
        return expr

    if t in ("lexical_declaration", "variable_declaration"):
        return _var_decl(node, ind)

    if t == "variable_declarator":
        return _var_declarator_line(node, ind, "let")

    if t == "return_statement":
        named = [ch for ch in node.children if ch.is_named]
        tc = _trailing_comments(node)
        if named:
            stmt = f"{P}return {c(named[0], ind)};"
        else:
            stmt = f"{P}return;"
        return f"{stmt} {tc}" if tc else stmt

    if t == "if_statement":
        return _if_stmt(node, ind)

    if t == "else_clause":
        named = [ch for ch in node.children if ch.is_named]
        if named and named[0].type == "if_statement":
            return f" else {_if_stmt(named[0], ind).lstrip()}"
        if named:
            return f" else {{\n{_block_body(named[0], ind + 1)}\n{P}}}"
        return ""

    if t == "for_statement":
        return _for_c(node, ind)
    if t == "for_in_statement":
        return _for_in(node, ind)

    if t == "while_statement":
        cond = node.child_by_field_name("condition")
        body = node.child_by_field_name("body")
        return f"{P}while {_strip_parens(c(cond, ind))} {{\n{_block_body(body, ind + 1)}\n{P}}}"

    if t == "do_statement":
        named = [ch for ch in node.children if ch.is_named]
        body = named[0] if named else None
        cond_node = named[1] if len(named) > 1 else None
        return (
            f"{P}loop {{\n{_block_body(body, ind + 1)}\n"
            f"{P}    if !({_strip_parens(c(cond_node, ind))}) {{ break; }}\n{P}}}"
        )

    if t == "switch_statement":
        return _switch(node, ind)
    if t == "try_statement":
        return _try(node, ind)

    if t == "throw_statement":
        named = [ch for ch in node.children if ch.is_named]
        val = c(named[0], ind) if named else '"error"'
        return f"{P}return Err({val}.into());"

    if t == "break_statement":
        tc = _trailing_comments(node)
        return f"{P}break; {tc}" if tc else f"{P}break;"
    if t == "continue_statement":
        tc = _trailing_comments(node)
        return f"{P}continue; {tc}" if tc else f"{P}continue;"
    if t == "empty_statement":
        return ""
    if t == "statement_block":
        return _block_body(node, ind)
    if t == "labeled_statement":
        named = [ch for ch in node.children if ch.is_named]
        if len(named) >= 2:
            return f"{P}'{c(named[0], ind)}: {c(named[1], ind)}"
        return ""
    if t == "debugger_statement":
        return f"{P}// debugger;"

    # --- Comments ---
    if t == "comment":
        return f"{P}{tx}"

    # --- Type nodes ---
    if t in (
        "type_annotation", "type_parameters", "type_arguments",
        "constraint", "default_type", "mapped_type", "index_signature",
        "intersection_type", "union_type", "conditional_type",
        "predefined_type", "literal_type", "tuple_type",
        "object_type", "function_type", "array_type", "generic_type",
        "parenthesized_type", "template_literal_type",
        "infer_type", "typeof", "keyof",
    ):
        tc = _trailing_comments(node)
        result = convert_type(node)
        if tc:
            return f"{result} {tc}"
        return result

    # --- Import (skip) ---
    if t in (
        "import_statement", "import_clause", "import_specifier",
        "named_imports", "namespace_import",
    ):
        return ""

    # --- Export ---
    if t == "export_statement":
        return _export(node, ind)

    # --- Declarations ---
    if t in ("function_declaration", "generator_function_declaration"):
        return _function(node, ind)
    if t == "type_alias_declaration":
        return _type_alias(node)
    if t == "interface_declaration":
        return _interface(node)
    if t in ("class_declaration", "abstract_class_declaration"):
        return _class(node)
    if t == "enum_declaration":
        return _enum(node)

    # --- JSX/TSX ---
    if t in (
        "jsx_element", "jsx_self_closing_element", "jsx_fragment",
        "jsx_opening_element", "jsx_closing_element", "jsx_expression",
        "jsx_attribute", "jsx_text",
    ):
        jsx_comments: list[str] = []

        def _jsx_comments(n: Node) -> None:
            if n.type == "comment":
                jsx_comments.append(n.text.decode())
            for ch in n.children:
                _jsx_comments(ch)

        _jsx_comments(node)
        tag = ""
        for ch in node.children:
            if ch.type in ("jsx_opening_element", "jsx_self_closing_element"):
                for c2 in ch.children:
                    if c2.type in ("identifier", "member_expression"):
                        tag = c2.text.decode()
                        break
        lines = [f"{P}// JSX: <{tag}>"] if tag else [f"{P}// JSX element"]
        for cm in jsx_comments:
            lines.append(f"{P}{cm}")
        return "\n".join(lines)

    # --- ERROR nodes ---
    if t == "ERROR":
        error_comments: list[str] = []

        def _extract_error_comments(n: Node) -> None:
            if n.type == "comment":
                error_comments.append(n.text.decode())
            for ch in n.children:
                _extract_error_comments(ch)

        _extract_error_comments(node)
        if error_comments:
            return "\n".join(f"{P}{cm}" for cm in error_comments)
        return f"{P}// [parse error]: {tx[:80]}"

    # --- Unnamed tokens ---
    if not node.is_named:
        return ""

    # --- Fallback ---
    return f"{P}{tx}"
