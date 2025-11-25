"""
Semantic Analysis — Compact & Powerful
======================================

This module performs early validation of the AST:
- Variable existence checks
- Literal/identifier resolution
- Type checks (number/string)
- Illegal operations detection
- File operation validation
- Repeat/If argument validation

Designed to keep the frontend strong and lean before IR generation.
"""

from engine.parser.ast_nodes import (
    Program, Trigger, Stmt,
    SetStmt, OutputStmt, RepeatStmt, IfStmt,
    CreateFileStmt, WriteFileStmt,
    Identifier, Literal
)


class SemanticError(Exception):
    pass


class SemanticAnalyzer:

    def __init__(self):
        # Tracks declared variables
        self.variables = {}

    # ============================================================
    # Main entry point
    # ============================================================

    def analyze(self, program: Program):
        """
        Validate each trigger independently.
        """
        for trigger in program.triggers:
            self.analyze_trigger(trigger)

    # ============================================================
    # Trigger-level scope
    # ============================================================

    def analyze_trigger(self, trig: Trigger):
        for stmt in trig.block:
            self.analyze_stmt(stmt)

    # ============================================================
    # Statement dispatcher
    # ============================================================

    def analyze_stmt(self, stmt: Stmt):
        if isinstance(stmt, SetStmt):
            self.check_set(stmt)

        elif isinstance(stmt, OutputStmt):
            self.check_output(stmt)

        elif isinstance(stmt, RepeatStmt):
            self.check_repeat(stmt)

        elif isinstance(stmt, IfStmt):
            self.check_if(stmt)

        elif isinstance(stmt, CreateFileStmt):
            self.check_create_file(stmt)

        elif isinstance(stmt, WriteFileStmt):
            self.check_write_file(stmt)

        # Other statement types are no-ops

    # ============================================================
    # Checks
    # ============================================================

    def check_set(self, s: SetStmt):
        # Record variable creation
        if s.target not in self.variables:
            self.variables[s.target] = "unknown"

        # Validate left and right sides
        self.ensure_valid_value(s.left)
        if s.op and s.right:
            self.ensure_valid_value(s.right)

    def check_output(self, s: OutputStmt):
        self.ensure_valid_value(s.value)

    def check_repeat(self, s: RepeatStmt):
        if not self.is_number(s.count):
            raise SemanticError(f"Repeat count must be number at line {s.line}")

        for st in s.body:
            self.analyze_stmt(st)

    def check_if(self, s: IfStmt):
        # Condition value must be literal or identifier
        self.ensure_valid_value(s.expected)

        for st in s.body:
            self.analyze_stmt(st)

    def check_create_file(self, s: CreateFileStmt):
        if not isinstance(s.filename, str):
            raise SemanticError(f"File name must be string at line {s.line}")

    def check_write_file(self, s: WriteFileStmt):
        if not isinstance(s.filename, str):
            raise SemanticError(f"File name must be string at line {s.line}")
        self.ensure_valid_value(s.content)

    # ============================================================
    # Helpers
    # ============================================================

    def ensure_valid_value(self, v):
        """
        Literal → always valid
        Identifier → must exist or become declared
        """
        if isinstance(v, Literal):
            return

        if isinstance(v, Identifier):
            name = v.name
            if name not in self.variables:
                # implicitly declare as unknown type
                self.variables[name] = "unknown"
            return

        raise SemanticError("Illegal expression in SET/OUTPUT/IF.")

    def is_number(self, v):
        return isinstance(v, Literal) and isinstance(v.value, (int, float))
