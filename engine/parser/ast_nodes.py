"""
AST Nodes — Compact, Powerful, SSA-Friendly
===========================================
This file defines the abstract syntax tree (AST) skeleton for the Assertion
DSL. AST nodes are minimal, immutable-style structures that the parser and
later compiler phases (SSA, IR, optimizer, VM, WASM) depend on.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Any


# ============================================================
# Base Node
# ============================================================

@dataclass
class ASTNode:
    """Base class for all AST nodes."""
    line: int


# ============================================================
# Core Nodes
# ============================================================

@dataclass
class Program(ASTNode):
    triggers: List["Trigger"] = field(default_factory=list)


@dataclass
class Trigger(ASTNode):
    name: str
    block: List["Stmt"] = field(default_factory=list)


@dataclass
class Stmt(ASTNode):
    """Base class for statements."""


# ============================================================
# Statement Types
# ============================================================

@dataclass
class SetStmt(Stmt):
    target: str
    op: Optional[str]     # PLUS, MINUS, TIMES, or None
    left: Any             # identifier or literal
    right: Any            # identifier or literal (optional if op=None)


@dataclass
class OutputStmt(Stmt):
    value: Any


@dataclass
class IfStmt(Stmt):
    var: str
    expected: Any
    body: List[Stmt] = field(default_factory=list)


@dataclass
class RepeatStmt(Stmt):
    count: Any
    body: List[Stmt] = field(default_factory=list)


@dataclass
class CreateFileStmt(Stmt):
    filename: str


@dataclass
class WriteFileStmt(Stmt):
    filename: str
    content: Any


# ============================================================
# Literals
# ============================================================

@dataclass
class Literal(ASTNode):
    value: Any


@dataclass
class Identifier(ASTNode):
    name: str
