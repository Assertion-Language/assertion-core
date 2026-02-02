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

@dataclass
class Stmt(ASTNode):
    """Marker for all statements."""
    pass

@dataclass
class Literal(ASTNode):
    value: Any

@dataclass
class Identifier(ASTNode):
    name: str

@dataclass
class BasicType(ASTNode):
    """Type reference (e.g., 'number', 'string')."""
    name: str

# ============================================================
# Core Statements
# ============================================================

@dataclass
class SetStmt(Stmt):
    """Represents 'Set/Make X to Y', 'Add X to Y', 'X is Y'."""
    target: str
    op: Optional[str] # PLUS, MINUS, TIMES, DIVIDE or None (Assignment)
    left: Any # Literal or Identifier
    right: Optional[Any] # Literal or Identifier (None if pure assignment)

@dataclass
class OutputStmt(Stmt):
    """Represents 'Say/Print X'."""
    value: Any 

@dataclass
class RepeatStmt(Stmt):
    """Represents 'Repeat X times: ...'."""
    count:Any 
    body: List[Stmt] = field(default_factory=list)

@dataclass
class IfStmt(Stmt):
    """Represents 'If X is Y: ...'."""
    var: str # Variable to check
    expected: Any # Expected value
    body: List[Stmt] = field(default_factory=list)
    else_body: List[Stmt] = field(default_factory=list)

@dataclass
class WhileStmt(Stmt):
    """Represents 'While X is Y: ...'."""
    condition_var: str
    condition_val: Any
    body: List[Stmt] = field(default_factory=list)

@dataclass
class CallStmt(Stmt):
    """Represents 'Run/Do [Skill]'."""
    func_name: str

@dataclass
class CreateFileStmt(Stmt):
    filename: str

@dataclass
class WriteFileStmt(Stmt):
    filename: str
    content: Any

@dataclass
class SaveStmt(Stmt):
    filename: str

@dataclass
class LoadStmt(Stmt):
    filename: str


@dataclass
class PythonStmt(Stmt):
    code: str

@dataclass
class ShellStmt(Stmt):
    command: str

@dataclass
class ImportStmt(Stmt):
    module_name: str


@dataclass
class WhenStmt(Stmt):
    # Kind: "VAR", "FILE", "REQUEST"
    kind: str
    target: str # Var name or Filename
    val: Any # Expected value (for VAR)
    body: List[Stmt] = field(default_factory=list)

@dataclass
class StartServerStmt(Stmt):
    port: int


# ============================================================
# Literals
# ============================================================

@dataclass
class VarDecl(Stmt):
    """
    Global variable declaration.
    'I want a number called "X" starting at 0.'
    """
    name: str
    type: str # "Number", "String"
    value: Any


# ============================================================
# Structure
# ============================================================

@dataclass
class Trigger(ASTNode):
    """
    A named block of code that runs on an event.
    Standard: 'When we start' -> Name: 'Ignition'
    Custom: 'To greet' -> Name: 'greet'
    """
    name: str
    block: List[Stmt] = field(default_factory=list)

@dataclass
class Program(ASTNode):
    """Root of the AST."""
    globals: List[VarDecl] = field(default_factory=list)
    triggers: List[Trigger] = field(default_factory=list)
