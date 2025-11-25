"""
SSA IR — Static Single Assignment Core
======================================
Compact, enterprise-grade intermediate representation.

This IR is designed for:
- CFG (control flow graph)
- Dominance + dominance frontier
- Optimizer passes: CSE, GVN, LICM, DCE
- Lowering to bytecode & WASM
- JIT backends (x86, ARM64)

This file provides:
- SSAValue: register-like value
- Instruction: IR ops
- BasicBlock: sequence of instructions
- Function: CFG of blocks
- IRBuilder: utility for constructing SSA

"""

from dataclasses import dataclass, field
from typing import List, Optional, Any


# ============================================================
# Core SSA Value
# ============================================================

@dataclass
class SSAValue:
    name: str            # "%1", "%2", ...
    typ: str             # "i32", "f64", "str"
    value: Any = None    # Literal or computed


# ============================================================
# Instruction Model
# ============================================================

@dataclass
class Instr:
    op: str                      # "add", "sub", "mul", "load", "store", "const", etc.
    args: List[SSAValue]         # operands
    result: Optional[SSAValue]   # result register
    block: "BasicBlock" = None
    meta: dict = field(default_factory=dict)

    def __repr__(self):
        if self.result:
            return f"{self.result.name} = {self.op}({', '.join(a.name for a in self.args)})"
        return f"{self.op}({', '.join(a.name for a in self.args)})"


# ============================================================
# Basic Block
# ============================================================

@dataclass
class BasicBlock:
    name: str
    instrs: List[Instr] = field(default_factory=list)
    terminator: Optional[Instr] = None
    preds: List["BasicBlock"] = field(default_factory=list)
    succs: List["BasicBlock"] = field(default_factory=list)

    def add(self, instr: Instr):
        instr.block = self
        self.instrs.append(instr)
        return instr

    def set_terminator(self, instr: Instr):
        self.terminator = instr
        instr.block = self

    def __repr__(self):
        out = [f"{self.name}:"]
        for i in self.instrs:
            out.append(f"  {i}")
        if self.terminator:
            out.append(f"  {self.terminator}")
        return "\n".join(out)


# ============================================================
# Function: CFG of BasicBlocks
# ============================================================

@dataclass
class Function:
    name: str
    blocks: List[BasicBlock] = field(default_factory=list)

    def new_block(self, name: str) -> BasicBlock:
        blk = BasicBlock(name)
        self.blocks.append(blk)
        return blk

    def __repr__(self):
        return "\n\n".join(repr(b) for b in self.blocks)


# ============================================================
# SSA IR Builder
# ============================================================

class IRBuilder:
    def __init__(self, func: Function):
        self.func = func
        self.block = func.new_block("entry")
        self.counter = 0

    # Generate new SSA name
    def new_reg(self, typ="i32", value=None):
        self.counter += 1
        name = f"%{self.counter}"
        return SSAValue(name=name, typ=typ, value=value)

    # ----------------------------------------------------------
    # Core instruction helpers
    # ----------------------------------------------------------

    def emit_const(self, value):
        typ = "i32"
        if isinstance(value, float):
            typ = "f64"
        if isinstance(value, str):
            typ = "str"
        reg = self.new_reg(typ, value)
        instr = Instr("const", [], reg)
        self.block.add(instr)
        return reg

    def emit_binary(self, op, a: SSAValue, b: SSAValue):
        reg = self.new_reg(a.typ)
        instr = Instr(op, [a, b], reg)
        self.block.add(instr)
        return reg

    def emit_load(self, name):
        reg = self.new_reg("i32")  # dynamic later
        instr = Instr("load", [SSAValue(name, "var")], reg)
        self.block.add(instr)
        return reg

    def emit_store(self, name, val: SSAValue):
        instr = Instr("store", [SSAValue(name, "var"), val], None)
        self.block.add(instr)
        return instr

    # ----------------------------------------------------------
    # Control flow
    # ----------------------------------------------------------

    def branch(self, target: BasicBlock):
        instr = Instr("br", [SSAValue(target.name, "label")], None)
        self.block.set_terminator(instr)
        self.block.succs.append(target)
        target.preds.append(self.block)

    def cbranch(self, cond: SSAValue, then_blk: BasicBlock, else_blk: BasicBlock):
        instr = Instr("cbr", [cond, SSAValue(then_blk.name, "label"), SSAValue(else_blk.name, "label")], None)
        self.block.set_terminator(instr)
        self.block.succs.extend([then_blk, else_blk])
        then_blk.preds.append(self.block)
        else_blk.preds.append(self.block)

    # ----------------------------------------------------------
    # Block switching
    # ----------------------------------------------------------

    def position_at_end(self, blk: BasicBlock):
        self.block = blk


# ============================================================
# Utility
# ============================================================

def dump_ir(func: Function):
    print("==== SSA IR DUMP ====")
    print(func)
