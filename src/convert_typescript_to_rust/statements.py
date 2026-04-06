"""Statement handlers: variable declarations, if, for, while, switch, try/catch.

Each public function converts a tree-sitter statement node into a Rust AST
node. NO string building or indentation -- only AST node construction.
"""

from __future__ import annotations

from tree_sitter import Node

from .rust_ast import (
    RsStmt, RsRawStmt, RsLet, RsReturn, RsExprStmt, RsIf, RsFor,
    RsWhile, RsLoop, RsMatch, RsMatchArm, RsTryCatch, RsBreak,
    RsContinue, RsComment, RsExpr, RsRawExpr,
    RsFunction, RsStruct, RsEnum, RsImpl, RsTypeAlias, RsConst,
)
from .types import convert_type, convert_type_node
from .helpers import _snake, _strip_parens, _trailing_comments


def _block_body_stmts(node: Node | None) -> list[RsStmt]:
    """Convert children of a ``statement_block`` to a list of RsStmt nodes."""
    if node is None:
        return []
    from .converter import convert_node, _fmt_node

    _ITEM_TYPES = (RsFunction, RsStruct, RsEnum, RsImpl, RsTypeAlias, RsConst)

    def _wrap_item(item):
        """Wrap a top-level RsItem as an RsRawStmt for use inside a block."""
        from .formatter import format_item
        text = format_item(item, 0)
        if text and text.strip():
            return RsRawStmt(text=text)
        return None

    stmts: list[RsStmt] = []
    for ch in node.children:
        if ch.type in ("{", "}"):
            continue
        result = convert_node(ch)
        if result is None:
            continue
        if isinstance(result, list):
            for r in result:
                if isinstance(r, _ITEM_TYPES):
                    wrapped = _wrap_item(r)
                    if wrapped:
                        stmts.append(wrapped)
                elif isinstance(r, RsStmt):
                    stmts.append(r)
                elif r is not None:
                    text = _fmt_node(r)
                    if text:
                        stmts.append(RsRawStmt(text=text))
        elif isinstance(result, _ITEM_TYPES):
            wrapped = _wrap_item(result)
            if wrapped:
                stmts.append(wrapped)
        elif isinstance(result, RsStmt):
            stmts.append(result)
        elif isinstance(result, RsExpr):
            stmts.append(RsExprStmt(result))
        else:
            text = _fmt_node(result)
            if text:
                stmts.append(RsRawStmt(text=text))
    return stmts


def _block_body(node: Node | None, ind: int) -> str:
    """Convert all children of a ``statement_block`` to Rust lines (string).

    Backward-compatible wrapper that returns a formatted string.
    """
    from .converter import _fmt_node
    from .formatter import format_stmt
    stmts = _block_body_stmts(node)
    lines = []
    for s in stmts:
        text = format_stmt(s, ind)
        if text:
            lines.append(text)
    return "\n".join(lines)


def _var_decl(node: Node) -> RsStmt | list[RsStmt]:
    """Convert a ``lexical_declaration`` or ``variable_declaration`` to Rust ``let`` bindings."""
    kind = "let"
    for ch in node.children:
        if ch.type == "const":
            kind = "let"
        elif ch.type in ("let", "var"):
            kind = "let mut"
    results: list[RsStmt] = []
    for ch in node.children:
        if ch.type == "variable_declarator":
            r = _var_declarator(ch, kind)
            if isinstance(r, list):
                results.extend(r)
            elif r is not None:
                results.append(r)
        elif ch.type == "comment":
            results.append(RsComment(ch.text.decode()))
    tc = _trailing_comments(node)
    if tc and results:
        # Append trailing comment to the last statement
        last = results[-1]
        if isinstance(last, RsRawStmt):
            results[-1] = RsRawStmt(f"{last.text} {tc}")
        else:
            from .converter import _fmt_node
            from .formatter import format_stmt
            text = format_stmt(last, 0)
            results[-1] = RsRawStmt(f"{text} {tc}")
    if len(results) == 1:
        return results[0]
    return results


def _var_declarator(node: Node, kind: str = "let") -> RsStmt | list[RsStmt] | None:
    """Convert a single ``variable_declarator`` to Rust AST node(s)."""
    from .converter import convert_expr, _fmt_expr

    name_node = None
    value = None
    type_ann = None
    pattern = None
    found_eq = False
    for ch in node.children:
        if ch.type == "identifier":
            name_node = ch
        if ch.type == "object_pattern":
            pattern = ch
        if ch.type == "array_pattern":
            pattern = ch
        if ch.type == "type_annotation":
            type_ann = ch
        if not ch.is_named and ch.text.decode() == "=":
            found_eq = True
        elif (
            found_eq and ch.is_named
            and ch != name_node and ch.type != "type_annotation" and ch != pattern
        ):
            value = ch
            break

    if pattern is not None:
        val_expr = convert_expr(value) if value else RsRawExpr("Default::default()")
        val_s = _fmt_expr(val_expr)
        if pattern.type == "object_pattern":
            fields: list[str] = []
            for ch in pattern.children:
                if ch.type == "shorthand_property_identifier_pattern":
                    fields.append(_snake(ch.text.decode()))
                elif ch.type == "pair_pattern":
                    local = None
                    for c2 in ch.children:
                        if c2.type == "identifier":
                            local = c2
                    if local:
                        fields.append(_snake(local.text.decode()))
            stmts: list[RsStmt] = [RsLet("_destructured", mutable=False, value=RsRawExpr(val_s))]
            for f in fields:
                stmts.append(RsLet(f, mutable=False, value=RsRawExpr(
                    f'_destructured.get("{f}").cloned().unwrap_or_default()'
                )))
            return stmts
        elif pattern.type == "array_pattern":
            fields_arr: list[str] = []
            for ch in pattern.children:
                if ch.type == "identifier":
                    fields_arr.append(_snake(ch.text.decode()))
            stmts_arr: list[RsStmt] = [RsLet("_arr", mutable=False, value=RsRawExpr(val_s))]
            for i, f in enumerate(fields_arr):
                stmts_arr.append(RsLet(f, mutable=False, value=RsRawExpr(
                    f"_arr.get({i}).cloned().unwrap_or_default()"
                )))
            return stmts_arr

    name = _snake(name_node.text.decode()) if name_node else "_"
    mutable = "mut" in kind
    from .rust_ast import RsRawType
    ts = RsRawType(text=convert_type(type_ann)) if type_ann else None
    if value:
        val_expr = convert_expr(value)
        return RsLet(name, mutable=mutable, type_ann=ts, value=val_expr)
    return RsLet(name, mutable=mutable, type_ann=ts, value=None)


# Keep the old name as an alias for backward compat in tests
_var_declarator_line = None  # removed -- use _var_declarator


def _if_stmt(node: Node) -> RsIf:
    """Convert an ``if_statement`` to an RsIf AST node."""
    from .converter import convert_expr, convert_node, _fmt_expr

    cond = node.child_by_field_name("condition")
    cons = node.child_by_field_name("consequence")
    alt = node.child_by_field_name("alternative")
    cond_s = _strip_parens(_fmt_expr(convert_expr(cond))) if cond else "true"
    then_body = _block_body_stmts(cons)
    else_body = None
    if alt:
        alt_result = convert_node(alt)
        if isinstance(alt_result, RsIf):
            else_body = [alt_result]
        elif isinstance(alt_result, list):
            else_body = alt_result
        elif alt_result is not None:
            else_body = [alt_result] if isinstance(alt_result, RsStmt) else None
    return RsIf(
        condition=RsRawExpr(cond_s),
        then_body=then_body,
        else_body=else_body,
    )


def _for_c(node: Node) -> RsLoop:
    """Convert a C-style ``for`` statement to a Rust ``loop``."""
    body_node = None
    for ch in node.children:
        if ch.type == "statement_block":
            body_node = ch
    body_stmts = _block_body_stmts(body_node)
    body_stmts.append(RsRawStmt("break; // C-style for"))
    return RsLoop(body=body_stmts)


def _for_in(node: Node) -> RsFor:
    """Convert a ``for-in`` or ``for-of`` statement to Rust ``for ... in ... {}``."""
    from .converter import convert_expr, _fmt_expr

    left = node.child_by_field_name("left")
    right = node.child_by_field_name("right")
    body_node = node.child_by_field_name("body")
    var_name = "_item"
    if left:
        if left.type == "identifier":
            var_name = _snake(left.text.decode())
        else:
            for ch in left.children:
                if ch.type == "identifier":
                    var_name = _snake(ch.text.decode())
                    break
                if ch.type == "variable_declarator":
                    for c2 in ch.children:
                        if c2.type == "identifier":
                            var_name = _snake(c2.text.decode())
                            break
    iter_s = _fmt_expr(convert_expr(right)) if right else "iter"
    return RsFor(
        var_name=var_name,
        iter_expr=RsRawExpr(f"{iter_s}.iter()"),
        body=_block_body_stmts(body_node),
    )


def _switch(node: Node) -> RsMatch:
    """Convert a ``switch`` statement to Rust ``match``."""
    from .converter import convert_expr, _fmt_expr

    val = None
    body = None
    for ch in node.children:
        if ch.type == "parenthesized_expression":
            val = ch
        if ch.type == "switch_body":
            body = ch
    val_s = _strip_parens(_fmt_expr(convert_expr(val))) if val else "value"
    arms: list[RsMatchArm] = []
    if body:
        for ch in body.children:
            if ch.type == "comment":
                arms.append(RsMatchArm(
                    pattern=RsComment(ch.text.decode()),
                    body=[],
                ))
            elif ch.type == "switch_case":
                case_val = None
                stmts: list[Node] = []
                for c2 in ch.children:
                    if c2.type in ("case", ":"):
                        continue
                    if case_val is None and c2.is_named:
                        case_val = c2
                    elif c2.is_named:
                        stmts.append(c2)
                cv_expr = convert_expr(case_val) if case_val else RsRawExpr("_")
                # Convert body stmts, filtering out break
                from .converter import convert_node, _fmt_node
                body_stmts: list[RsStmt] = []
                for s in stmts:
                    r = convert_node(s)
                    if r is None:
                        continue
                    text = _fmt_node(r)
                    if "break;" in text:
                        continue
                    if isinstance(r, list):
                        for item in r:
                            if isinstance(item, RsStmt):
                                body_stmts.append(item)
                            elif item is not None:
                                body_stmts.append(RsRawStmt(text=_fmt_node(item)))
                    elif isinstance(r, RsStmt):
                        body_stmts.append(r)
                    else:
                        body_stmts.append(RsRawStmt(text=text))
                arms.append(RsMatchArm(pattern=cv_expr, body=body_stmts))
            elif ch.type == "switch_default":
                stmts_d = [c2 for c2 in ch.children if c2.is_named]
                from .converter import convert_node, _fmt_node
                body_stmts_d: list[RsStmt] = []
                for s in stmts_d:
                    r = convert_node(s)
                    if r is None:
                        continue
                    text = _fmt_node(r)
                    if "break;" in text:
                        continue
                    if isinstance(r, list):
                        for item in r:
                            if isinstance(item, RsStmt):
                                body_stmts_d.append(item)
                            elif item is not None:
                                body_stmts_d.append(RsRawStmt(text=_fmt_node(item)))
                    elif isinstance(r, RsStmt):
                        body_stmts_d.append(r)
                    else:
                        body_stmts_d.append(RsRawStmt(text=text))
                arms.append(RsMatchArm(pattern=RsRawExpr("_"), body=body_stmts_d))
    return RsMatch(expr=RsRawExpr(val_s), arms=arms)


def _try(node: Node) -> RsTryCatch:
    """Convert a ``try/catch/finally`` statement to Rust AST."""
    try_block = None
    catch_clause = None
    finally_clause = None
    for ch in node.children:
        if ch.type == "statement_block":
            try_block = ch
        if ch.type == "catch_clause":
            catch_clause = ch
        if ch.type == "finally_clause":
            finally_clause = ch
    try_body = _block_body_stmts(try_block) if try_block else []
    catch_var = "e"
    catch_body: list[RsStmt] = []
    if catch_clause:
        param = None
        catch_block = None
        for ch in catch_clause.children:
            if ch.type == "identifier":
                param = ch
            if ch.type == "statement_block":
                catch_block = ch
        catch_var = _snake(param.text.decode()) if param else "e"
        catch_body = _block_body_stmts(catch_block) if catch_block else []
    finally_body: list[RsStmt] | None = None
    if finally_clause:
        fb = None
        for ch in finally_clause.children:
            if ch.type == "statement_block":
                fb = ch
        if fb:
            finally_body = _block_body_stmts(fb)
    return RsTryCatch(
        try_body=try_body,
        catch_var=catch_var,
        catch_body=catch_body,
        finally_body=finally_body,
    )
