"""Core AST walker for TypeScript-to-Rust conversion.

The ``convert_node(node)`` function is the main dispatch point. It examines
each tree-sitter node's type and delegates to the appropriate handler in the
``types``, ``calls``, ``declarations``, ``statements``, and ``expressions``
modules.

All handlers return Rust AST nodes (from ``rust_ast``). NO strings are built
here -- the formatter is the only place that produces strings.
"""

from __future__ import annotations

import re
from tree_sitter import Node

from .rust_ast import (
    RsExpr, RsRawExpr, RsLiteral, RsIdent, RsBinOp, RsUnaryOp,
    RsFieldAccess, RsIndex, RsMethodCall, RsCall, RsAwait, RsMacro,
    RsIfExpr, RsClosure,
    RsStmt, RsRawStmt, RsLet, RsReturn, RsExprStmt, RsIf, RsFor,
    RsWhile, RsLoop, RsMatch, RsMatchArm, RsTryCatch, RsBreak,
    RsContinue, RsComment,
    RsItem,
)
from .types import convert_type, convert_type_node, _TYPE_MAP
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
    _var_declarator,
    _if_stmt,
    _for_c,
    _for_in,
    _switch,
    _try,
    _block_body_stmts,
)
from .expressions import _template, _arrow, _object, _args




# Type alias for anything the converter can return
RsNode = RsExpr | RsStmt | RsItem | list[RsStmt] | list[RsItem] | None


def convert_node(node: Node | None) -> RsNode:
    """Convert ANY tree-sitter node to a Rust AST node.

    This is the main recursive dispatch function. It pattern-matches on the
    node type and either handles the conversion inline (for simple cases) or
    delegates to a specialised handler function.

    Args:
        node: The tree-sitter ``Node`` to convert, or ``None``.

    Returns:
        A Rust AST node, a list of nodes, or None.
    """
    if node is None:
        return None
    t = node.type
    tx = node.text.decode()

    # --- Literals ---
    if t == "number":
        return RsLiteral(tx)
    if t == "string":
        if tx.startswith("'") and tx.endswith("'"):
            inner = tx[1:-1].replace('"', '\\"').replace("\\'", "'")
            return RsLiteral(f'"{inner}"')
        return RsLiteral(tx)
    if t in ("string_fragment", "escape_sequence"):
        return RsRawExpr(tx)
    if t in ("true", "false"):
        return RsLiteral(tx)
    if t in ("null", "undefined"):
        return RsLiteral("None")
    if t == "this":
        return RsLiteral("self")
    if t == "super":
        return RsRawExpr("super")
    if t == "regex":
        m = re.match(r"^/(.+)/([gimsuy]*)$", tx, re.DOTALL)
        if m:
            return RsRawExpr(f'regex::Regex::new(r#"{m.group(1)}"#).unwrap()')
        return RsRawExpr(f'regex::Regex::new(r#"{tx}"#).unwrap()')

    # --- Identifiers ---
    if t == "identifier":
        return RsIdent(_ident(tx))
    if t == "property_identifier":
        return RsIdent(_snake(tx))
    if t == "shorthand_property_identifier":
        return RsIdent(_snake(tx))
    if t == "shorthand_property_identifier_pattern":
        return RsIdent(_snake(tx))
    if t == "type_identifier":
        return RsRawExpr(_TYPE_MAP.get(tx, tx))

    # --- Template strings ---
    if t == "template_string":
        return _template(node)
    if t == "template_substitution":
        for ch in node.children:
            if ch.is_named:
                return convert_node(ch)
        return None

    # --- Binary ---
    if t == "binary_expression":
        parts = list(node.children)
        tc = _trailing_comments(node)
        if len(parts) >= 3:
            op_text = parts[1].text.decode()
            left = convert_expr(parts[0])
            right = convert_expr(parts[2])
            if op_text == "===":
                op_text = "=="
            elif op_text == "!==":
                op_text = "!="
            elif op_text == "instanceof":
                result_expr = RsRawExpr(f"{_fmt_expr(left)}.downcast_ref::<{_fmt_expr(right)}>().is_some()")
                if tc:
                    return RsRawExpr(f"{_fmt_expr(result_expr)} {tc}")
                return result_expr
            elif op_text == "in":
                result_expr = RsRawExpr(f"{_fmt_expr(right)}.contains_key({_fmt_expr(left)})")
                if tc:
                    return RsRawExpr(f"{_fmt_expr(result_expr)} {tc}")
                return result_expr
            result_expr = RsBinOp(left, op_text, right)
            if tc:
                return RsRawExpr(f"{_fmt_expr(result_expr)} {tc}")
            return result_expr

    # --- Unary ---
    if t == "unary_expression":
        parts = list(node.children)
        op = parts[0].text.decode()
        operand = convert_expr(parts[1]) if len(parts) > 1 else RsRawExpr("")
        if op == "typeof":
            return RsRawExpr(f"_typeof_({_fmt_expr(operand)})")
        if op == "void":
            return RsRawExpr(f"{{ let _ = {_fmt_expr(operand)}; }}")
        if op == "delete":
            return RsRawExpr(f"{_fmt_expr(operand)}.take()")
        if op == "!" and parts[1].type == "identifier":
            return RsRawExpr(f"{_fmt_expr(operand)}.is_none()")
        return RsUnaryOp(op, operand)

    # --- Update ---
    if t == "update_expression":
        parts = list(node.children)
        if parts[0].text.decode() in ("++", "--"):
            op = "+= 1" if parts[0].text.decode() == "++" else "-= 1"
            return RsRawExpr(f"{{ {_fmt_expr(convert_expr(parts[1]))} {op} }}")
        op = "+= 1" if parts[1].text.decode() == "++" else "-= 1"
        v = _fmt_expr(convert_expr(parts[0]))
        return RsRawExpr(f"{{ let _v = {v}; {v} {op}; _v }}")

    # --- Assignment ---
    if t in ("assignment_expression", "augmented_assignment_expression"):
        parts = list(node.children)
        if len(parts) >= 3:
            left = convert_expr(parts[0])
            right = convert_expr(parts[2])
            return RsRawExpr(f"{_fmt_expr(left)} {parts[1].text.decode()} {_fmt_expr(right)}")

    # --- Ternary ---
    if t == "ternary_expression":
        parts = [ch for ch in node.children if ch.is_named]
        if len(parts) >= 3:
            cond = convert_expr(parts[0])
            then = convert_expr(parts[1])
            els = convert_expr(parts[2])
            return RsIfExpr(cond, then, els)

    # --- Parens ---
    if t == "parenthesized_expression":
        named = [ch for ch in node.children if ch.is_named]
        if named:
            inner = convert_expr(named[0])
            return RsRawExpr(f"({_fmt_expr(inner)})")
        return RsRawExpr(f"({tx[1:-1]})")

    # --- Member access ---
    if t == "member_expression":
        obj = node.child_by_field_name("object") or node.children[0]
        prop = node.child_by_field_name("property") or node.children[-1]
        optional = any(ch.type == "?." for ch in node.children)
        tc = _trailing_comments(node)
        obj_expr = convert_expr(obj)
        prop_s = _snake(prop.text.decode()) if prop else ""
        if prop_s == "length":
            result_expr = RsMethodCall(obj_expr, "len", [])
        elif prop_s == "prototype":
            result_expr = obj_expr
        elif optional:
            result_expr = RsRawExpr(f"{_fmt_expr(obj_expr)}.as_ref().and_then(|v| v.{prop_s})")
        else:
            result_expr = RsFieldAccess(obj_expr, prop_s)
        if tc:
            return RsRawExpr(f"{_fmt_expr(result_expr)} {tc}")
        return result_expr

    # --- Subscript ---
    if t == "subscript_expression":
        obj_node = node.children[0]
        idx = None
        for ch in node.children:
            if ch.type not in ("[", "]") and ch != obj_node and ch.is_named:
                idx = ch
                break
        return RsIndex(convert_expr(obj_node), convert_expr(idx))

    # --- Call ---
    if t == "call_expression":
        return _call(node)

    if t == "arguments":
        return RsRawExpr(_args(node))

    # --- New ---
    if t == "new_expression":
        named = [ch for ch in node.children if ch.is_named]
        cls_expr = convert_expr(named[0]) if named else RsIdent("Unknown")
        cls_s = _fmt_expr(cls_expr)
        args_node = None
        for ch in node.children:
            if ch.type == "arguments":
                args_node = ch
        args_s = _args(args_node)
        if cls_s in ("std::collections::HashMap", "HashMap"):
            return RsRawExpr("std::collections::HashMap::new()")
        if cls_s in ("std::collections::HashSet", "HashSet"):
            return RsRawExpr("std::collections::HashSet::new()")
        if cls_s == "Vec":
            if args_s:
                return RsRawExpr(f"Vec::with_capacity({args_s})")
            return RsRawExpr("Vec::new()")
        if cls_s in ("regex::Regex", "Regex"):
            return RsRawExpr(f"regex::Regex::new({args_s}).unwrap()")
        return RsRawExpr(f"{cls_s}::new({args_s})")

    # --- Await ---
    if t == "await_expression":
        named = [ch for ch in node.children if ch.is_named]
        if named:
            return RsAwait(convert_expr(named[0]))
        return RsRawExpr(".await")

    # --- Arrow ---
    if t == "arrow_function":
        return _arrow(node)

    # --- Object ---
    if t == "object":
        return _object(node)

    # --- Array ---
    if t == "array":
        elems: list[RsExpr] = []
        comments: list[str] = []
        for ch in node.children:
            if ch.type == "comment":
                comments.append(ch.text.decode())
            elif ch.is_named:
                elems.append(convert_expr(ch))
        inner = ", ".join(_fmt_expr(e) for e in elems)
        if comments:
            comment_str = "\n".join(comments)
            return RsRawExpr(f"{comment_str}\nvec![{inner}]")
        return RsRawExpr(f"vec![{inner}]")

    # --- Pair ---
    if t == "pair":
        named = [ch for ch in node.children if ch.is_named]
        if len(named) >= 2:
            key = named[0].text.decode().strip("'\"")
            return RsRawExpr(f'"{key}": {_fmt_expr(convert_expr(named[1]))}')
        return RsRawExpr(tx)

    # --- Spread ---
    if t == "spread_element":
        named = [ch for ch in node.children if ch.is_named]
        if named:
            return RsRawExpr(f"/* ...{_fmt_expr(convert_expr(named[0]))} */")
        return RsRawExpr("/* spread */")

    # --- Type casts (drop) ---
    if t in ("as_expression", "satisfies_expression", "type_assertion"):
        named = [ch for ch in node.children if ch.is_named]
        return convert_node(named[0]) if named else None

    # --- Non-null assertion ---
    if t in ("non_null_assertion_expression", "non_null_expression"):
        named = [ch for ch in node.children if ch.is_named]
        if named:
            return RsRawExpr(f"{_fmt_expr(convert_expr(named[0]))}.unwrap()")
        return RsRawExpr(".unwrap()")

    # --- Sequence ---
    if t == "sequence_expression":
        named = [ch for ch in node.children if ch.is_named]
        return RsRawExpr("; ".join(_fmt_expr(convert_expr(x)) for x in named))

    # --- Yield ---
    if t == "yield_expression":
        named = [ch for ch in node.children if ch.is_named]
        if named:
            return RsRawExpr(f"yield {_fmt_expr(convert_expr(named[0]))}")
        return RsRawExpr("yield")

    # =============== STATEMENTS ===============

    if t == "expression_statement":
        named = [ch for ch in node.children if ch.is_named]
        tc = _trailing_comments(node)
        if named:
            expr = convert_expr(named[0])
            if tc:
                return RsExprStmt(RsRawExpr(f"{_fmt_expr(expr)} {tc}"))
            return RsExprStmt(expr)
        return None

    if t in ("lexical_declaration", "variable_declaration"):
        return _var_decl(node)

    if t == "variable_declarator":
        return _var_declarator(node, "let")

    if t == "return_statement":
        named = [ch for ch in node.children if ch.is_named]
        tc = _trailing_comments(node)
        if named:
            val = convert_expr(named[0])
            if tc:
                return RsReturn(RsRawExpr(f"{_fmt_expr(val)} {tc}"))
            return RsReturn(val)
        if tc:
            return RsRawStmt(f"return; {tc}")
        return RsReturn()

    if t == "if_statement":
        return _if_stmt(node)

    if t == "else_clause":
        named = [ch for ch in node.children if ch.is_named]
        if named and named[0].type == "if_statement":
            # Returns an RsIf node for else-if chaining
            return _if_stmt(named[0])
        if named:
            return _block_body_stmts(named[0])
        return []

    if t == "for_statement":
        return _for_c(node)
    if t == "for_in_statement":
        return _for_in(node)

    if t == "while_statement":
        cond = node.child_by_field_name("condition")
        body = node.child_by_field_name("body")
        cond_s = _strip_parens(_fmt_expr(convert_expr(cond))) if cond else "true"
        return RsWhile(
            condition=RsRawExpr(cond_s),
            body=_block_body_stmts(body),
        )

    if t == "do_statement":
        named = [ch for ch in node.children if ch.is_named]
        body_node = named[0] if named else None
        cond_node = named[1] if len(named) > 1 else None
        body_stmts = _block_body_stmts(body_node)
        cond_s = _strip_parens(_fmt_expr(convert_expr(cond_node))) if cond_node else "true"
        body_stmts.append(RsIf(
            condition=RsRawExpr(f"!({cond_s})"),
            then_body=[RsBreak()],
        ))
        return RsLoop(body=body_stmts)

    if t == "switch_statement":
        return _switch(node)
    if t == "try_statement":
        return _try(node)

    if t == "throw_statement":
        named = [ch for ch in node.children if ch.is_named]
        val = _fmt_expr(convert_expr(named[0])) if named else '"error"'
        return RsExprStmt(RsRawExpr(f"return Err({val}.into())"))

    if t == "break_statement":
        tc = _trailing_comments(node)
        if tc:
            return RsRawStmt(f"break; {tc}")
        return RsBreak()
    if t == "continue_statement":
        tc = _trailing_comments(node)
        if tc:
            return RsRawStmt(f"continue; {tc}")
        return RsContinue()
    if t == "empty_statement":
        return None
    if t == "statement_block":
        stmts = _block_body_stmts(node)
        return stmts if stmts else None
    if t == "labeled_statement":
        named = [ch for ch in node.children if ch.is_named]
        if len(named) >= 2:
            label = _fmt_expr(convert_expr(named[0]))
            body = convert_node(named[1])
            # For labeled statements, wrap as raw
            return RsRawStmt(f"'{label}: {_fmt_node(body)}")
        return None
    if t == "debugger_statement":
        return RsComment("// debugger;")

    # --- Comments ---
    if t == "comment":
        return RsComment(tx)

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
            return RsRawExpr(f"{result} {tc}")
        return RsRawExpr(result)

    # --- Import (skip) ---
    if t in (
        "import_statement", "import_clause", "import_specifier",
        "named_imports", "namespace_import",
    ):
        return None

    # --- Export ---
    if t == "export_statement":
        return _export(node)

    # --- Declarations ---
    if t in ("function_declaration", "generator_function_declaration"):
        return _function(node)
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
        items: list[RsStmt] = []
        if tag:
            items.append(RsComment(f"// JSX: <{tag}>"))
        else:
            items.append(RsComment("// JSX element"))
        for cm in jsx_comments:
            items.append(RsComment(cm))
        if len(items) == 1:
            return items[0]
        return items

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
            stmts = [RsComment(cm) for cm in error_comments]
            return stmts if len(stmts) > 1 else stmts[0]
        return RsComment(f"// [parse error]: {tx[:80]}")

    # --- Unnamed tokens ---
    if not node.is_named:
        return None

    # --- Fallback ---
    return RsRawExpr(tx)


def convert_expr(node: Node | None) -> RsExpr:
    """Convert a tree-sitter node to an RsExpr.

    If the conversion yields a non-expression, wrap it in RsRawExpr.
    """
    if node is None:
        return RsRawExpr("")
    result = convert_node(node)
    if result is None:
        return RsRawExpr("")
    if isinstance(result, RsExpr):
        return result
    # Wrap statement-like results as a RsRawExpr
    return RsRawExpr(_fmt_node(result))


def convert_stmt(node: Node | None) -> RsStmt | list[RsStmt] | None:
    """Convert a tree-sitter node to an RsStmt or list of RsStmt."""
    if node is None:
        return None
    result = convert_node(node)
    if result is None:
        return None
    if isinstance(result, list):
        return result
    if isinstance(result, RsStmt):
        return result
    if isinstance(result, RsExpr):
        return RsExprStmt(result)
    if isinstance(result, RsItem):
        return RsRawStmt(_fmt_node(result))
    return RsRawStmt(_fmt_node(result))


def convert_item(node: Node | None) -> RsItem | list[RsItem] | None:
    """Convert a tree-sitter node to an RsItem or list of RsItem."""
    if node is None:
        return None
    result = convert_node(node)
    if result is None:
        return None
    if isinstance(result, RsItem):
        return result
    if isinstance(result, list):
        # Check if list of items
        items: list[RsItem] = []
        for r in result:
            if isinstance(r, RsItem):
                items.append(r)
            else:
                items.append(RsRawStmt(_fmt_node(r)))
        return items
    if isinstance(result, RsExpr):
        return RsRawStmt(_fmt_expr(result))
    if isinstance(result, RsStmt):
        return RsRawStmt(_fmt_node(result))
    return RsRawStmt(str(result))


# ---------------------------------------------------------------------------
# Formatting helpers (internal -- used only to assemble raw expression text)
# ---------------------------------------------------------------------------

def _fmt_expr(expr: RsExpr | None) -> str:
    """Format an expression to a string using the formatter."""
    if expr is None:
        return ""
    from .formatter import format_expr
    return format_expr(expr)


def _fmt_node(node) -> str:
    """Format any AST node to a string using the formatter."""
    if node is None:
        return ""
    if isinstance(node, str):
        return node
    if isinstance(node, list):
        from .formatter import format_stmt, format_item
        parts = []
        for n in node:
            parts.append(_fmt_node(n))
        return "\n".join(p for p in parts if p)
    from .formatter import format_expr, format_stmt, format_item
    if isinstance(node, RsExpr):
        return format_expr(node)
    if isinstance(node, RsStmt):
        return format_stmt(node, 0)
    if isinstance(node, RsItem):
        return format_item(node, 0)
    return str(node)


# ---------------------------------------------------------------------------
# Backward compatibility aliases
# ---------------------------------------------------------------------------

def c(node: Node | None, ind: int = 0) -> str:
    """Backward-compatible wrapper: convert node and format to string.

    The ``ind`` parameter is accepted but ignored -- indentation is now
    handled exclusively by the formatter.
    """
    result = convert_node(node)
    if result is None:
        return ""
    return _fmt_node(result)


def _fmt(node_or_str, ind: int = 0) -> str:
    """Backward-compatible bridge for formatting any value to a string."""
    if node_or_str is None:
        return ""
    if isinstance(node_or_str, str):
        return node_or_str
    return _fmt_node(node_or_str)
