"""Pretty-print a Rust AST to a formatted source string.

This module is the *only* place where indentation, spacing, and brace
placement are decided.  Converter modules build AST nodes; the formatter
turns them into text.
"""

from __future__ import annotations

from .rust_ast import (
    # Types
    RsPrimitiveType, RsOptionType, RsVecType, RsHashMapType, RsRawType, RsType,
    # Expressions
    RsLiteral, RsIdent, RsBinOp, RsUnaryOp, RsCall, RsMethodCall,
    RsFieldAccess, RsIndex, RsClosure, RsAwait, RsMacro, RsIfExpr,
    RsRawExpr, RsExpr,
    # Statements
    RsLet, RsReturn, RsExprStmt, RsIf, RsFor, RsWhile, RsLoop,
    RsMatch, RsMatchArm, RsTryCatch, RsBreak, RsContinue,
    RsComment, RsRawStmt, RsStmt,
    # Items
    RsParam, RsFunction, RsField, RsStruct, RsEnumVariant, RsEnum,
    RsImpl, RsTypeAlias, RsConst, RsItem, RsFile,
)


_INDENT = "    "


def _indent_continuation(text: str, indent: int) -> str:
    """Re-indent all lines of a multiline expression to match context."""
    P = _INDENT * indent
    lines = text.split("\n")
    result = [lines[0]]
    for line in lines[1:]:
        if line.strip():
            result.append(P + line)
        else:
            result.append("")
    return "\n".join(result)


# -----------------------------------------------------------------------
# Public entry point
# -----------------------------------------------------------------------

def format_file(f: RsFile) -> str:
    """Format a complete Rust source file."""
    parts: list[str] = []
    if f.doc_comment:
        parts.append(f.doc_comment)

    prev_was_comment = False
    for item in f.items:
        text = format_item(item, 0)
        if text is None or not text.strip():
            continue
        is_comment = isinstance(item, RsComment)
        if not prev_was_comment:
            parts.append("")
        parts.append(text)
        prev_was_comment = is_comment

    return "\n".join(parts)


# -----------------------------------------------------------------------
# Items
# -----------------------------------------------------------------------

def format_item(item: RsItem, indent: int) -> str:
    """Format a top-level item."""
    P = _INDENT * indent

    if isinstance(item, RsFunction):
        return _format_function(item, indent)

    if isinstance(item, RsStruct):
        return _format_struct(item, indent)

    if isinstance(item, RsEnum):
        return _format_enum(item, indent)

    if isinstance(item, RsImpl):
        return _format_impl(item, indent)

    if isinstance(item, RsTypeAlias):
        return _format_type_alias(item, indent)

    if isinstance(item, RsConst):
        return _format_const(item, indent)

    if isinstance(item, RsComment):
        return f"{P}{item.text}"

    if isinstance(item, RsRawStmt):
        return item.text

    return ""


def _format_function(fn: RsFunction, indent: int) -> str:
    P = _INDENT * indent
    parts: list[str] = []
    if fn.doc_comment:
        parts.append(f"{P}{fn.doc_comment}")

    pub = "pub " if fn.is_pub else ""
    async_kw = "async " if fn.is_async else ""
    params_s = ", ".join(_format_param(p) for p in fn.params)
    ret_s = ""
    if fn.return_type:
        rt = format_type(fn.return_type)
        if rt not in ("()", ""):
            ret_s = f" -> {rt}"

    body_s = _format_body(fn.body, indent + 1)
    if not body_s.strip():
        body_s = f"{P}{_INDENT}// empty"

    parts.append(f"{P}{pub}{async_kw}fn {fn.name}({params_s}){ret_s} {{")
    parts.append(body_s)
    parts.append(f"{P}}}")
    return "\n".join(parts)


def _format_param(p: RsParam) -> str:
    ts = format_type(p.type_ann)
    if ts == "":
        # Self param or comment-only param
        return p.name
    if p.is_rest:
        return f"{p.name}: &[{ts}]"
    return f"{p.name}: {ts}"


def _format_struct(s: RsStruct, indent: int) -> str:
    P = _INDENT * indent
    parts: list[str] = []
    if s.doc_comment:
        parts.append(f"{P}{s.doc_comment}")

    if s.is_empty:
        parts.append(f"{P}pub struct {s.name};")
        return "\n".join(parts)

    if not s.fields:
        parts.append(f"{P}pub struct {s.name};")
        return "\n".join(parts)

    if s.derives:
        derives = ", ".join(s.derives)
        parts.append(f"{P}#[derive({derives})]")
    parts.append(f"{P}pub struct {s.name} {{")
    for fld in s.fields:
        # Comment-only fields (from interface/type alias comments)
        if fld.name.startswith("_comment_") and fld.doc_comment:
            parts.append(f"{P}{_INDENT}{fld.doc_comment}")
            continue
        if fld.doc_comment:
            parts.append(f"{P}{_INDENT}{fld.doc_comment}")
        ts = format_type(fld.type_ann)
        pub = "pub " if fld.is_pub else ""
        parts.append(f"{P}{_INDENT}{pub}{fld.name}: {ts},")
    parts.append(f"{P}}}")
    return "\n".join(parts)


def _format_enum(e: RsEnum, indent: int) -> str:
    P = _INDENT * indent
    parts: list[str] = []
    if e.doc_comment:
        parts.append(f"{P}{e.doc_comment}")

    derives = ", ".join(e.derives)
    parts.append(f"{P}#[derive({derives})]")
    parts.append(f"{P}pub enum {e.name} {{")
    if e.variants:
        for v in e.variants:
            if v.doc_comment and v.name == v.doc_comment.strip():
                # Comment-only variant (from enum body comments)
                parts.append(f"{P}{_INDENT}{v.doc_comment}")
                continue
            if v.doc_comment:
                parts.append(f"{P}{_INDENT}{v.doc_comment}")
            parts.append(f"{P}{_INDENT}{v.name},")
    else:
        parts.append(f"{P}{_INDENT}// empty")
    parts.append(f"{P}}}")
    return "\n".join(parts)


def _format_impl(impl: RsImpl, indent: int) -> str:
    P = _INDENT * indent
    parts: list[str] = []
    parts.append(f"{P}impl {impl.type_name} {{")
    for i, method in enumerate(impl.methods):
        if i > 0:
            parts.append("")
        parts.append(_format_function(method, indent + 1))
    parts.append(f"{P}}}")
    return "\n".join(parts)


def _format_type_alias(ta: RsTypeAlias, indent: int) -> str:
    P = _INDENT * indent
    parts: list[str] = []
    if ta.doc_comment:
        parts.append(f"{P}{ta.doc_comment}")
    ts = format_type(ta.type_ann)
    parts.append(f"{P}pub type {ta.name} = {ts};")
    return "\n".join(parts)


def _format_const(c: RsConst, indent: int) -> str:
    P = _INDENT * indent
    parts: list[str] = []
    if c.doc_comment:
        parts.append(f"{P}{c.doc_comment}")
    ts = format_type(c.type_ann)
    vs = format_expr(c.value)
    pub = "pub " if c.is_pub else ""
    parts.append(f"{P}{pub}const {c.name}: {ts} = {vs};")
    return "\n".join(parts)


# -----------------------------------------------------------------------
# Statements
# -----------------------------------------------------------------------

def format_stmt(stmt: RsStmt, indent: int) -> str:
    """Format a statement at the given indentation level."""
    P = _INDENT * indent

    if isinstance(stmt, RsLet):
        mut = "mut " if stmt.mutable else ""
        ts = f": {format_type(stmt.type_ann)}" if stmt.type_ann else ""
        if stmt.value is not None:
            vs = format_expr(stmt.value)
            if "\n" in vs:
                vs = _indent_continuation(vs, indent)
            return f"{P}let {mut}{stmt.name}{ts} = {vs};"
        return f"{P}let {mut}{stmt.name}{ts} = Default::default();"

    if isinstance(stmt, RsReturn):
        if stmt.value is not None:
            vs = format_expr(stmt.value)
            if "\n" in vs:
                vs = _indent_continuation(vs, indent)
            return f"{P}return {vs};"
        return f"{P}return;"

    if isinstance(stmt, RsExprStmt):
        vs = format_expr(stmt.expr)
        if "\n" in vs:
            vs = _indent_continuation(vs, indent)
        return f"{P}{vs};"

    if isinstance(stmt, RsIf):
        return _format_if(stmt, indent)

    if isinstance(stmt, RsFor):
        iter_s = format_expr(stmt.iter_expr)
        body_s = _format_body(stmt.body, indent + 1)
        return f"{P}for {stmt.var_name} in {iter_s} {{\n{body_s}\n{P}}}"

    if isinstance(stmt, RsWhile):
        cond_s = format_expr(stmt.condition)
        body_s = _format_body(stmt.body, indent + 1)
        return f"{P}while {cond_s} {{\n{body_s}\n{P}}}"

    if isinstance(stmt, RsLoop):
        body_s = _format_body(stmt.body, indent + 1)
        return f"{P}loop {{\n{body_s}\n{P}}}"

    if isinstance(stmt, RsMatch):
        return _format_match(stmt, indent)

    if isinstance(stmt, RsTryCatch):
        return _format_try_catch(stmt, indent)

    if isinstance(stmt, RsBreak):
        return f"{P}break;"

    if isinstance(stmt, RsContinue):
        return f"{P}continue;"

    if isinstance(stmt, RsComment):
        return f"{P}{stmt.text}"

    if isinstance(stmt, RsRawStmt):
        # Re-indent multiline raw statements to match context
        if "\n" in stmt.text and indent > 0:
            lines = stmt.text.split("\n")
            result_lines = []
            for line in lines:
                if line.strip():
                    result_lines.append(P + line)
                else:
                    result_lines.append("")
            return "\n".join(result_lines)
        return stmt.text

    return ""


def _format_if(stmt: RsIf, indent: int) -> str:
    P = _INDENT * indent
    cond_s = format_expr(stmt.condition)
    then_s = _format_body(stmt.then_body, indent + 1)
    result = f"{P}if {cond_s} {{\n{then_s}\n{P}}}"

    if stmt.else_body is not None:
        # Check if the else body is a single RsIf (else-if chain)
        if (len(stmt.else_body) == 1 and isinstance(stmt.else_body[0], RsIf)):
            inner_if = _format_if(stmt.else_body[0], indent)
            # Strip the leading indentation from the inner if
            inner_if_stripped = inner_if.lstrip()
            result += f" else {inner_if_stripped}"
        else:
            else_s = _format_body(stmt.else_body, indent + 1)
            result += f" else {{\n{else_s}\n{P}}}"

    return result


def _format_match(stmt: RsMatch, indent: int) -> str:
    P = _INDENT * indent
    A = _INDENT * (indent + 1)
    expr_s = format_expr(stmt.expr)
    parts = [f"{P}match {expr_s} {{"]
    for arm in stmt.arms:
        if isinstance(arm.pattern, RsComment):
            parts.append(f"{A}{arm.pattern.text}")
        else:
            pat_s = format_expr(arm.pattern)
            body_s = _format_body(arm.body, indent + 2)
            if not body_s.strip():
                body_s = f"{_INDENT * (indent + 2)}()"
            parts.append(f"{A}{pat_s} => {{")
            parts.append(body_s)
            parts.append(f"{A}}}")
    parts.append(f"{P}}}")
    return "\n".join(parts)


def _format_try_catch(stmt: RsTryCatch, indent: int) -> str:
    P = _INDENT * indent
    parts: list[str] = []

    if stmt.catch_body:
        try_s = _format_body(stmt.try_body, indent + 1)
        catch_s = _format_body(stmt.catch_body, indent + 2)
        parts.append(f"{P}match (|| -> Result<(), Box<dyn std::error::Error>> {{")
        parts.append(try_s)
        parts.append(f"{P}{_INDENT}Ok(())")
        parts.append(f"{P}}})() {{")
        parts.append(f"{P}{_INDENT}Ok(()) => {{}}")
        parts.append(f"{P}{_INDENT}Err({stmt.catch_var}) => {{")
        parts.append(catch_s)
        parts.append(f"{P}{_INDENT}}}")
        parts.append(f"{P}}}")
    else:
        parts.append(f"{P}// try")
        parts.append(_format_body(stmt.try_body, indent + 1))

    if stmt.finally_body:
        parts.append(f"{P}// finally")
        parts.append(_format_body(stmt.finally_body, indent))

    return "\n".join(parts)


def _format_body(stmts: list[RsStmt], indent: int) -> str:
    """Format a list of statements as a block body."""
    lines: list[str] = []
    for s in stmts:
        line = format_stmt(s, indent)
        if line is not None and line != "":
            lines.append(line)
    return "\n".join(lines)


# -----------------------------------------------------------------------
# Expressions
# -----------------------------------------------------------------------

def format_expr(expr: RsExpr) -> str:
    """Format an expression (no indentation -- expressions are inline)."""
    if isinstance(expr, RsLiteral):
        return expr.value

    if isinstance(expr, RsIdent):
        return expr.name

    if isinstance(expr, RsBinOp):
        return f"{format_expr(expr.left)} {expr.op} {format_expr(expr.right)}"

    if isinstance(expr, RsUnaryOp):
        return f"{expr.op}{format_expr(expr.operand)}"

    if isinstance(expr, RsCall):
        func_s = format_expr(expr.func)
        args_s = ", ".join(format_expr(a) for a in expr.args)
        return f"{func_s}({args_s})"

    if isinstance(expr, RsMethodCall):
        obj_s = format_expr(expr.obj)
        args_s = ", ".join(format_expr(a) for a in expr.args)
        return f"{obj_s}.{expr.method}({args_s})"

    if isinstance(expr, RsFieldAccess):
        return f"{format_expr(expr.obj)}.{expr.field}"

    if isinstance(expr, RsIndex):
        return f"{format_expr(expr.obj)}[{format_expr(expr.index)}]"

    if isinstance(expr, RsClosure):
        params_s = ", ".join(expr.params)
        if expr.body is None:
            return f"|{params_s}| {{}}"
        if isinstance(expr.body, list):
            # Block body -- format inline for short bodies
            body_lines = []
            for s in expr.body:
                body_lines.append(format_stmt(s, 0))
            body_s = "\n".join(l for l in body_lines if l)
            return f"|{params_s}| {{\n{body_s}\n}}"
        # Expression body
        return f"|{params_s}| {format_expr(expr.body)}"

    if isinstance(expr, RsAwait):
        return f"{format_expr(expr.expr)}.await"

    if isinstance(expr, RsMacro):
        return f"{expr.name}({expr.args})"

    if isinstance(expr, RsIfExpr):
        cond = format_expr(expr.condition)
        then = format_expr(expr.then_expr)
        els = format_expr(expr.else_expr)
        return f"if {cond} {{ {then} }} else {{ {els} }}"

    if isinstance(expr, RsRawExpr):
        return expr.text

    return str(expr)


# -----------------------------------------------------------------------
# Types
# -----------------------------------------------------------------------

def format_type(ty: RsType) -> str:
    """Format a type."""
    if isinstance(ty, RsPrimitiveType):
        return ty.name

    if isinstance(ty, RsOptionType):
        return f"Option<{format_type(ty.inner)}>"

    if isinstance(ty, RsVecType):
        return f"Vec<{format_type(ty.inner)}>"

    if isinstance(ty, RsHashMapType):
        return f"std::collections::HashMap<{format_type(ty.key)}, {format_type(ty.value)}>"

    if isinstance(ty, RsRawType):
        return ty.text

    return str(ty)
