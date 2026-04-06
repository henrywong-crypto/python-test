"""Statement handlers: variable declarations, if, for, while, switch, try/catch.

Each public function converts a tree-sitter statement node into its Rust
equivalent.
"""

from __future__ import annotations

from tree_sitter import Node

from .types import convert_type
from .helpers import _snake, _strip_parens, _trailing_comments


def _block_body(node: Node | None, ind: int) -> str:
    """Convert all children of a ``statement_block`` to Rust lines.

    Skips ``{`` and ``}`` tokens and concatenates the converted child nodes.

    Args:
        node: The tree-sitter ``statement_block`` node, or ``None``.
        ind: Current indentation level for children.

    Returns:
        The Rust block body as a multi-line string.
    """
    if node is None:
        return ""
    from .converter import c

    lines: list[str] = []
    for ch in node.children:
        if ch.type in ("{", "}"):
            continue
        line = c(ch, ind)
        if line is not None and line != "":
            lines.append(line)
    return "\n".join(lines)


def _var_decl(node: Node, ind: int) -> str:
    """Convert a ``lexical_declaration`` or ``variable_declaration`` to Rust ``let`` bindings.

    Args:
        node: The tree-sitter declaration node.
        ind: Current indentation level.

    Returns:
        The Rust variable declaration(s).
    """
    kind = "let"
    for ch in node.children:
        if ch.type == "const":
            kind = "let"
        elif ch.type in ("let", "var"):
            kind = "let mut"
    results: list[str] = []
    for ch in node.children:
        if ch.type == "variable_declarator":
            results.append(_var_declarator_line(ch, ind, kind))
        elif ch.type == "comment":
            results.append(f"{'    ' * ind}{ch.text.decode()}")
    tc = _trailing_comments(node)
    if tc and results:
        results[-1] = f"{results[-1]} {tc}"
    return "\n".join(results)


def _var_declarator_line(node: Node, ind: int, kind: str = "let") -> str:
    """Convert a single ``variable_declarator`` to a Rust ``let`` binding.

    Handles plain variables, object destructuring, and array destructuring.

    Args:
        node: The tree-sitter ``variable_declarator`` node.
        ind: Current indentation level.
        kind: ``"let"`` or ``"let mut"``.

    Returns:
        The Rust let-binding line(s).
    """
    from .converter import c

    P = "    " * ind
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
        val_s = c(value, ind) if value else "Default::default()"
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
            lines = [f"{P}let _destructured = {val_s};"]
            for f in fields:
                lines.append(
                    f'{P}let {f} = _destructured.get("{f}").cloned().unwrap_or_default();'
                )
            return "\n".join(lines)
        elif pattern.type == "array_pattern":
            fields_arr: list[str] = []
            for ch in pattern.children:
                if ch.type == "identifier":
                    fields_arr.append(_snake(ch.text.decode()))
            lines = [f"{P}let _arr = {val_s};"]
            for i, f in enumerate(fields_arr):
                lines.append(f"{P}let {f} = _arr.get({i}).cloned().unwrap_or_default();")
            return "\n".join(lines)

    name = _snake(name_node.text.decode()) if name_node else "_"
    ts = f": {convert_type(type_ann)}" if type_ann else ""
    if value:
        return f"{P}{kind} {name}{ts} = {c(value, ind)};"
    return f"{P}{kind} {name}{ts} = Default::default();"


def _if_stmt(node: Node, ind: int) -> str:
    """Convert an ``if_statement`` to Rust ``if ... { } else { }``.

    Args:
        node: The tree-sitter ``if_statement`` node.
        ind: Current indentation level.

    Returns:
        The Rust if statement string.
    """
    from .converter import c

    P = "    " * ind
    cond = node.child_by_field_name("condition")
    cons = node.child_by_field_name("consequence")
    alt = node.child_by_field_name("alternative")
    cond_s = _strip_parens(c(cond, ind)) if cond else "true"
    result = f"{P}if {cond_s} {{\n{_block_body(cons, ind + 1)}\n{P}}}"
    if alt:
        result += c(alt, ind)
    return result


def _for_c(node: Node, ind: int) -> str:
    """Convert a C-style ``for`` statement to a Rust ``loop``.

    Args:
        node: The tree-sitter ``for_statement`` node.
        ind: Current indentation level.

    Returns:
        The Rust loop string.
    """
    P = "    " * ind
    body = None
    for ch in node.children:
        if ch.type == "statement_block":
            body = ch
    return f"{P}loop {{\n{_block_body(body, ind + 1)}\n{P}    break; // C-style for\n{P}}}"


def _for_in(node: Node, ind: int) -> str:
    """Convert a ``for-in`` or ``for-of`` statement to Rust ``for ... in ... {}``.

    Args:
        node: The tree-sitter ``for_in_statement`` node.
        ind: Current indentation level.

    Returns:
        The Rust for-in loop string.
    """
    from .converter import c

    P = "    " * ind
    left = node.child_by_field_name("left")
    right = node.child_by_field_name("right")
    body = node.child_by_field_name("body")
    var_name = "_item"
    if left:
        for ch in left.children:
            if ch.type == "identifier":
                var_name = _snake(ch.text.decode())
                break
            if ch.type == "variable_declarator":
                for c2 in ch.children:
                    if c2.type == "identifier":
                        var_name = _snake(c2.text.decode())
                        break
    iter_s = c(right, ind) if right else "iter"
    return f"{P}for {var_name} in {iter_s}.iter() {{\n{_block_body(body, ind + 1)}\n{P}}}"


def _switch(node: Node, ind: int) -> str:
    """Convert a ``switch`` statement to Rust ``match``.

    Args:
        node: The tree-sitter ``switch_statement`` node.
        ind: Current indentation level.

    Returns:
        The Rust match expression string.
    """
    from .converter import c

    P = "    " * ind
    val = None
    body = None
    for ch in node.children:
        if ch.type == "parenthesized_expression":
            val = ch
        if ch.type == "switch_body":
            body = ch
    val_s = _strip_parens(c(val, ind)) if val else "value"
    arms: list[str] = []
    if body:
        for ch in body.children:
            if ch.type == "comment":
                arms.append(f"{'    ' * (ind + 1)}{ch.text.decode()}")
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
                cv = c(case_val, ind) if case_val else "_"
                bl = [c(s, ind + 2) for s in stmts if "break;" not in c(s, ind + 2)]
                bl_s = "\n".join(bl) if bl else f"{'    ' * (ind + 2)}()"
                arms.append(f"{'    ' * (ind + 1)}{cv} => {{\n{bl_s}\n{'    ' * (ind + 1)}}}")
            elif ch.type == "switch_default":
                stmts_d = [c2 for c2 in ch.children if c2.is_named]
                bl = [c(s, ind + 2) for s in stmts_d if "break;" not in c(s, ind + 2)]
                bl_s = "\n".join(bl) if bl else f"{'    ' * (ind + 2)}()"
                arms.append(f"{'    ' * (ind + 1)}_ => {{\n{bl_s}\n{'    ' * (ind + 1)}}}")
    return f"{P}match {val_s} {{\n" + "\n".join(arms) + f"\n{P}}}"


def _try(node: Node, ind: int) -> str:
    """Convert a ``try/catch/finally`` statement to Rust.

    Uses a closure returning ``Result`` to simulate try/catch.

    Args:
        node: The tree-sitter ``try_statement`` node.
        ind: Current indentation level.

    Returns:
        The Rust try/catch equivalent.
    """
    P = "    " * ind
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
    try_s = _block_body(try_block, ind + 1) if try_block else ""
    result = ""
    if catch_clause:
        param = None
        catch_body = None
        for ch in catch_clause.children:
            if ch.type == "identifier":
                param = ch
            if ch.type == "statement_block":
                catch_body = ch
        pn = _snake(param.text.decode()) if param else "e"
        catch_s = _block_body(catch_body, ind + 2) if catch_body else ""
        result = (
            f"{P}match (|| -> Result<(), Box<dyn std::error::Error>> {{\n"
            f"{try_s}\n{P}    Ok(())\n{P}}})() {{\n"
            f"{P}    Ok(()) => {{}}\n"
            f"{P}    Err({pn}) => {{\n{catch_s}\n{P}    }}\n{P}}}"
        )
    else:
        result = f"{P}// try\n{try_s}"
    if finally_clause:
        fb = None
        for ch in finally_clause.children:
            if ch.type == "statement_block":
                fb = ch
        if fb:
            result += f"\n{P}// finally\n{_block_body(fb, ind)}"
    return result
