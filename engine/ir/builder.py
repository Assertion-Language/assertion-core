"""
IR Builder — AST → SSA Lowering
================================
This module lowers the high-level AST into SSA IR:

Supported constructs:
- SET (with arithmetic)
- OUTPUT
- IF
- REPEAT
- CREATE FILE
- WRITE FILE

Produces:
- SSAValue
- Instruction sequences
- Basic blocks + control flow

This is the bridge between parsing and optimization.
"""

from typing import Dict, Any
from engine.parser.ast_nodes import (
    Program, Trigger, SetStmt, OutputStmt, RepeatStmt,
    IfStmt, CreateFileStmt, WriteFileStmt,
    Literal, Identifier
)

from engine.ir.ssa import (
    Function, BasicBlock, SSAValue, Instr, IRBuilder
)


class IRGenerator:
    """
    Converts full AST → SSA IR.
    One Function per Trigger.
    """

    def __init__(self):
        self.functions = {}  # name → Function
        self.vars: Dict[str, SSAValue] = {}
        self.builder: IRBuilder = None

    # ============================================================
    # Entry: Whole Program
    # ============================================================

    def lower(self, prog: Program) -> Dict[str, Function]:
        """
        Converts each trigger into a separate SSA Function.
        """
        for trig in prog.triggers:
            func = Function(trig.name)
            self.builder = IRBuilder(func)
            self.vars = {}
            self.lower_block(trig.block)
            self.functions[trig.name] = func

        return self.functions

    # ============================================================
    # Lowering Helpers
    # ============================================================

    def lower_block(self, stmts):
        for st in stmts:
            self.lower_stmt(st)

    def lower_stmt(self, stmt):
        if isinstance(stmt, SetStmt):
            self.lower_set(stmt)

        elif isinstance(stmt, OutputStmt):
            self.lower_output(stmt)

        elif isinstance(stmt, IfStmt):
            self.lower_if(stmt)

        elif isinstance(stmt, RepeatStmt):
            self.lower_repeat(stmt)

        elif isinstance(stmt, CreateFileStmt):
            self.lower_create_file(stmt)

        elif isinstance(stmt, WriteFileStmt):
            self.lower_write_file(stmt)

    # ============================================================
    # Lower SET
    # ============================================================

    def lower_set(self, st: SetStmt):
        left = self.lower_value(st.left)

        if st.op and st.right:
            right = self.lower_value(st.right)
            if st.op == "PLUS":
                res = self.builder.emit_binary("add", left, right)
            elif st.op == "MINUS":
                res = self.builder.emit_binary("sub", left, right)
            elif st.op == "TIMES":
                res = self.builder.emit_binary("mul", left, right)
        else:
            res = left

        # store to variable
        self.vars[st.target] = res
        self.builder.emit_store(st.target, res)

    # ============================================================
    # Lower OUTPUT
    # ============================================================

    def lower_output(self, st: OutputStmt):
        val = self.lower_value(st.value)
        self.builder.block.add(Instr("print", [val], None))

    # ============================================================
    # Lower IF
    # ============================================================

    def lower_if(self, st: IfStmt):
        cond_val = self.lower_identifier_or_literal(st.var)
        expected = self.lower_value(st.expected)

        cmp_reg = self.builder.emit_binary("eq", cond_val, expected)

        func = self.builder.func
        then_blk = func.new_block("if.then")
        cont_blk = func.new_block("if.cont")

        self.builder.cbranch(cmp_reg, then_blk, cont_blk)

        # Then block
        self.builder.position_at_end(then_blk)
        for s in st.body:
            self.lower_stmt(s)
        self.builder.branch(cont_blk)

        # Continue block
        self.builder.position_at_end(cont_blk)

    # ============================================================
    # Lower REPEAT
    # ============================================================

    def lower_repeat(self, st: RepeatStmt):
        count = self.lower_value(st.count)

        func = self.builder.func
        header = func.new_block("loop.header")
        body = func.new_block("loop.body")
        after = func.new_block("loop.after")

        # jump to header
        self.builder.branch(header)

        # Loop header
        self.builder.position_at_end(header)
        iter_reg = self.builder.new_reg("i32")
        # store initial value
        self.builder.emit_store(iter_reg.name, count)
        zero = self.builder.emit_const(0)
        cmp = self.builder.emit_binary("gt", iter_reg, zero)
        self.builder.cbranch(cmp, body, after)

        # Loop body
        self.builder.position_at_end(body)
        for s in st.body:
            self.lower_stmt(s)
        # decrement
        one = self.builder.emit_const(1)
        dec = self.builder.emit_binary("sub", iter_reg, one)
        self.builder.emit_store(iter_reg.name, dec)
        self.builder.branch(header)

        # After loop
        self.builder.position_at_end(after)

    # ============================================================
    # Lower CREATE FILE
    # ============================================================

    def lower_create_file(self, st: CreateFileStmt):
        name_reg = self.builder.emit_const(st.filename)
        self.builder.block.add(Instr("file.create", [name_reg], None))

    # ============================================================
    # Lower WRITE FILE
    # ============================================================

    def lower_write_file(self, st: WriteFileStmt):
        fname = self.builder.emit_const(st.filename)
        content = self.lower_value(st.content)
        self.builder.block.add(Instr("file.write", [fname, content], None))

    # ============================================================
    # Values (literal or identifier)
    # ============================================================

    def lower_value(self, v):
        if isinstance(v, Literal):
            return self.builder.emit_const(v.value)
        if isinstance(v, Identifier):
            return self.lower_identifier_or_literal(v.name)
        raise ValueError("Unknown AST value type")

    def lower_identifier_or_literal(self, name_or_obj):
        if isinstance(name_or_obj, Identifier):
            name = name_or_obj.name
        else:
            name = name_or_obj

        if name not in self.vars:
            # undef var → assume numeric
            reg = self.builder.new_reg("i32")
            self.vars[name] = reg
            self.builder.emit_store(name, reg)

        return self.vars[name]
