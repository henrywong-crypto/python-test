"""Rust AST intermediate representation.

Defines all Rust AST nodes as Python dataclasses. The converter modules
build these nodes from the TypeScript tree-sitter AST, and the formatter
module renders them to formatted Rust source code.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Union, Optional


# ---------------------------------------------------------------------------
# Types
# ---------------------------------------------------------------------------

@dataclass
class RsPrimitiveType:
    """A primitive or named type like ``String``, ``f64``, ``bool``."""
    name: str  # "String", "f64", "bool", "()", "!"


@dataclass
class RsOptionType:
    """``Option<T>``."""
    inner: "RsType"


@dataclass
class RsVecType:
    """``Vec<T>``."""
    inner: "RsType"


@dataclass
class RsHashMapType:
    """``std::collections::HashMap<K, V>``."""
    key: "RsType"
    value: "RsType"


@dataclass
class RsRawType:
    """A raw type string that is passed through verbatim."""
    text: str


RsType = Union[RsPrimitiveType, RsOptionType, RsVecType, RsHashMapType, RsRawType]


# ---------------------------------------------------------------------------
# Expressions
# ---------------------------------------------------------------------------

@dataclass
class RsLiteral:
    """A literal value (number, string, bool, None, etc.)."""
    value: str


@dataclass
class RsIdent:
    """An identifier."""
    name: str


@dataclass
class RsBinOp:
    """A binary operation."""
    left: "RsExpr"
    op: str
    right: "RsExpr"


@dataclass
class RsUnaryOp:
    """A unary operation (prefix)."""
    op: str
    operand: "RsExpr"


@dataclass
class RsCall:
    """A function call."""
    func: "RsExpr"
    args: list["RsExpr"] = field(default_factory=list)


@dataclass
class RsMethodCall:
    """A method call on an object."""
    obj: "RsExpr"
    method: str
    args: list["RsExpr"] = field(default_factory=list)


@dataclass
class RsFieldAccess:
    """Field access ``obj.field``."""
    obj: "RsExpr"
    field: str


@dataclass
class RsIndex:
    """Index access ``obj[index]``."""
    obj: "RsExpr"
    index: "RsExpr"


@dataclass
class RsClosure:
    """A closure ``|params| body``."""
    params: list[str] = field(default_factory=list)
    body: Union[list["RsStmt"], "RsExpr", None] = None


@dataclass
class RsAwait:
    """An ``.await`` expression."""
    expr: "RsExpr"


@dataclass
class RsMacro:
    """A macro call like ``format!(...)``, ``vec![...]``."""
    name: str
    args: str  # raw args string


@dataclass
class RsIfExpr:
    """An inline if-else expression."""
    condition: "RsExpr"
    then_expr: "RsExpr"
    else_expr: "RsExpr"


@dataclass
class RsRawExpr:
    """A raw expression string passed through verbatim."""
    text: str


RsExpr = Union[
    RsLiteral, RsIdent, RsBinOp, RsUnaryOp, RsCall, RsMethodCall,
    RsFieldAccess, RsIndex, RsClosure, RsAwait, RsMacro, RsIfExpr, RsRawExpr,
]


# ---------------------------------------------------------------------------
# Statements
# ---------------------------------------------------------------------------

@dataclass
class RsLet:
    """A ``let`` binding."""
    name: str
    mutable: bool = False
    type_ann: Optional[RsType] = None
    value: Optional[RsExpr] = None


@dataclass
class RsReturn:
    """A ``return`` statement."""
    value: Optional[RsExpr] = None


@dataclass
class RsExprStmt:
    """An expression used as a statement (with trailing ``;``)."""
    expr: RsExpr


@dataclass
class RsIf:
    """An ``if`` / ``else if`` / ``else`` statement."""
    condition: RsExpr
    then_body: list["RsStmt"] = field(default_factory=list)
    else_body: Optional[list["RsStmt"]] = None


@dataclass
class RsFor:
    """A ``for var in iter`` loop."""
    var_name: str
    iter_expr: RsExpr
    body: list["RsStmt"] = field(default_factory=list)


@dataclass
class RsWhile:
    """A ``while`` loop."""
    condition: RsExpr
    body: list["RsStmt"] = field(default_factory=list)


@dataclass
class RsLoop:
    """An unconditional ``loop``."""
    body: list["RsStmt"] = field(default_factory=list)


@dataclass
class RsMatch:
    """A ``match`` expression/statement."""
    expr: RsExpr
    arms: list["RsMatchArm"] = field(default_factory=list)


@dataclass
class RsMatchArm:
    """A single arm in a ``match``."""
    pattern: RsExpr
    body: list["RsStmt"] = field(default_factory=list)


@dataclass
class RsTryCatch:
    """A try/catch simulation using closure + Result."""
    try_body: list["RsStmt"] = field(default_factory=list)
    catch_var: str = "e"
    catch_body: list["RsStmt"] = field(default_factory=list)
    finally_body: Optional[list["RsStmt"]] = None


@dataclass
class RsBreak:
    """A ``break`` statement."""
    pass


@dataclass
class RsContinue:
    """A ``continue`` statement."""
    pass


@dataclass
class RsComment:
    """A comment (single-line or multi-line)."""
    text: str


@dataclass
class RsRawStmt:
    """A raw statement string passed through verbatim."""
    text: str


RsStmt = Union[
    RsLet, RsReturn, RsExprStmt, RsIf, RsFor, RsWhile, RsLoop,
    RsMatch, RsTryCatch, RsBreak, RsContinue, RsComment, RsRawStmt,
]


# ---------------------------------------------------------------------------
# Items (top-level)
# ---------------------------------------------------------------------------

@dataclass
class RsParam:
    """A function parameter."""
    name: str
    type_ann: RsType
    is_rest: bool = False


@dataclass
class RsFunction:
    """A function definition."""
    name: str
    is_pub: bool = True
    is_async: bool = False
    params: list[RsParam] = field(default_factory=list)
    return_type: Optional[RsType] = None
    body: list[RsStmt] = field(default_factory=list)
    doc_comment: Optional[str] = None


@dataclass
class RsField:
    """A struct field."""
    name: str
    type_ann: RsType
    is_pub: bool = True
    doc_comment: Optional[str] = None


@dataclass
class RsStruct:
    """A struct definition."""
    name: str
    fields: list[RsField] = field(default_factory=list)
    derives: list[str] = field(default_factory=lambda: [
        "Debug", "Clone", "serde::Serialize", "serde::Deserialize",
    ])
    doc_comment: Optional[str] = None
    is_empty: bool = False  # True for "pub struct Foo;"


@dataclass
class RsEnumVariant:
    """An enum variant."""
    name: str
    doc_comment: Optional[str] = None


@dataclass
class RsEnum:
    """An enum definition."""
    name: str
    variants: list[RsEnumVariant] = field(default_factory=list)
    derives: list[str] = field(default_factory=lambda: [
        "Debug", "Clone", "PartialEq",
    ])
    doc_comment: Optional[str] = None


@dataclass
class RsImpl:
    """An ``impl`` block."""
    type_name: str
    methods: list[RsFunction] = field(default_factory=list)


@dataclass
class RsTypeAlias:
    """A type alias ``pub type Name = Type;``."""
    name: str
    type_ann: RsType
    doc_comment: Optional[str] = None


@dataclass
class RsConst:
    """A constant ``pub const NAME: Type = value;``."""
    name: str
    type_ann: RsType
    value: RsExpr
    is_pub: bool = True
    doc_comment: Optional[str] = None


RsItem = Union[
    RsFunction, RsStruct, RsEnum, RsImpl, RsTypeAlias, RsConst,
    RsComment, RsRawStmt,
]


@dataclass
class RsFile:
    """A complete Rust source file."""
    doc_comment: Optional[str] = None
    items: list[RsItem] = field(default_factory=list)
