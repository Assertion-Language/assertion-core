"""
Bytecode + Virtual Machine
==========================
This module implements:
- A compact bytecode instruction format
- A stack-based VM
- SSA → Bytecode lowering
- Real control flow (jmp, jmp_if)
- File operations, printing, arithmetic
- Variable storage model

This is the runtime layer for executing IR programs.
"""

from dataclasses import dataclass
from typing import List, Dict, Any
from engine.ir.ssa import Function, Instr, BasicBlock


# ============================================================
# BYTECODE FORMAT
# ============================================================

@dataclass
class BCInstr:
    op: str
    args: List[Any]


# ============================================================
# BYTECODE PROGRAM
# ============================================================

@dataclass
class BytecodeProgram:
    consts: List[Any]
    code: List[BCInstr]
    labels: Dict[str, int]


# ============================================================
# LOWER SSA → BYTECODE
# ============================================================

class BytecodeCompiler:

    def __init__(self):
        self.consts = []
        self.labels = {}
        self.code = []
        self.var_slots: Dict[str, int] = {}
        self.reg_slots: Dict[str, int] = {}
        self.next_slot = 0

    # ----- CONSTANT POOL -----
    def emit_const(self, value):
        self.consts.append(value)
        idx = len(self.consts) - 1
        self.code.append(BCInstr("LOAD_CONST", [idx]))

    # ----- REGISTER STORAGE -----
    def slot_for(self, name: str):
        if name not in self.reg_slots:
            self.reg_slots[name] = self.next_slot
            self.next_slot += 1
        return self.reg_slots[name]

    # ----- BASIC OPS -----
    def emit(self, op, *args):
        self.code.append(BCInstr(op, list(args)))

    # ============================================================
    # LOWER FUNCTION
    # ============================================================

    def compile_function(self, func: Function) -> BytecodeProgram:
        # Map blocks to labels
        for blk in func.blocks:
            self.labels[blk.name] = len(self.code)
            self.code.append(BCInstr("LABEL", [blk.name]))

            for inst in blk.instrs:
                self.lower_instr(inst)

            if blk.terminator:
                self.lower_instr(blk.terminator)

        return BytecodeProgram(self.consts, self.code, self.labels)

    # ============================================================
    # LOWER SINGLE INSTRUCTION
    # ============================================================

    def lower_instr(self, inst: Instr):
        op = inst.op

        # -----------------------
        # CONSTANTS
        # -----------------------
        if op == "const":
            self.emit_const(inst.result.value)
            dst = self.slot_for(inst.result.name)
            self.emit("STORE", dst)
            return

        # -----------------------
        # BINARY OPS
        # -----------------------
        if op in ("add", "sub", "mul", "eq", "gt"):
            a = self.slot_for(inst.args[0].name)
            b = self.slot_for(inst.args[1].name)
            self.emit("LOAD", a)
            self.emit("LOAD", b)

            map_op = {
                "add": "ADD",
                "sub": "SUB",
                "mul": "MUL",
                "eq":  "EQ",
                "gt":  "GT"
            }

            self.emit(map_op[op])
            dst = self.slot_for(inst.result.name)
            self.emit("STORE", dst)
            return

        # -----------------------
        # LOAD / STORE
        # -----------------------
        if op == "load":
            name = inst.args[0].name
            slot = self.slot_for(name)
            self.emit("LOAD", slot)
            dst = self.slot_for(inst.result.name)
            self.emit("STORE", dst)
            return

        if op == "store":
            name = inst.args[0].name
            src = inst.args[1].name
            slot_src = self.slot_for(src)
            slot_dst = self.slot_for(name)
            self.emit("LOAD", slot_src)
            self.emit("STORE", slot_dst)
            return

        # -----------------------
        # PRINT
        # -----------------------
        if op == "print":
            val = self.slot_for(inst.args[0].name)
            self.emit("LOAD", val)
            self.emit("PRINT")
            return

        # -----------------------
        # FILE OPS
        # -----------------------
        if op == "file.create":
            s = self.slot_for(inst.args[0].name)
            self.emit("LOAD", s)
            self.emit("FILE_CREATE")
            return

        if op == "file.write":
            s = self.slot_for(inst.args[0].name)
            c = self.slot_for(inst.args[1].name)
            self.emit("LOAD", s)
            self.emit("LOAD", c)
            self.emit("FILE_WRITE")
            return

        # -----------------------
        # BRANCHES
        # -----------------------
        if op == "br":
            label = inst.args[0].name
            self.emit("JMP", label)
            return

        if op == "cbr":
            cond = self.slot_for(inst.args[0].name)
            then_label = inst.args[1].name
            else_label = inst.args[2].name

            self.emit("LOAD", cond)
            self.emit("JMP_IF", then_label)
            self.emit("JMP", else_label)
            return


# ============================================================
# VM — EXECUTOR
# ============================================================

class VM:

    def __init__(self, program: BytecodeProgram):
        self.program = program
        self.stack = []
        self.pc = 0
        self.vars = {}
        self.running = True

    # ----------------------------------------------------------
    # Stack helpers
    # ----------------------------------------------------------

    def push(self, v):
        self.stack.append(v)

    def pop(self):
        return self.stack.pop()

    # ----------------------------------------------------------
    # Run Loop
    # ----------------------------------------------------------

    def run(self):
        code = self.program.code
        labels = self.program.labels

        while self.pc < len(code) and self.running:
            instr = code[self.pc]
            op = instr.op
            args = instr.args
            self.pc += 1

            if op == "LABEL":
                continue

            if op == "LOAD_CONST":
                idx = args[0]
                self.push(self.program.consts[idx])
                continue

            if op == "LOAD":
                slot = args[0]
                self.push(self.vars.get(slot, 0))
                continue

            if op == "STORE":
                slot = args[0]
                self.vars[slot] = self.pop()
                continue

            if op == "ADD":
                b = self.pop(); a = self.pop()
                self.push(a + b)
                continue

            if op == "SUB":
                b = self.pop(); a = self.pop()
                self.push(a - b)
                continue

            if op == "MUL":
                b = self.pop(); a = self.pop()
                self.push(a * b)
                continue

            if op == "EQ":
                b = self.pop(); a = self.pop()
                self.push(1 if a == b else 0)
                continue

            if op == "GT":
                b = self.pop(); a = self.pop()
                self.push(1 if a > b else 0)
                continue

            if op == "PRINT":
                print(self.pop())
                continue

            if op == "FILE_CREATE":
                name = self.pop()
                with open(name, "w") as f:
                    f.write("")
                continue

            if op == "FILE_WRITE":
                content = self.pop()
                fname = self.pop()
                with open(fname, "a") as f:
                    f.write(str(content) + "\n")
                continue

            if op == "JMP":
                label = args[0]
                self.pc = labels[label]
                continue

            if op == "JMP_IF":
                label = args[0]
                cond = self.pop()
                if cond:
                    self.pc = labels[label]
                continue

            # Stop if unknown opcode
            raise RuntimeError(f"Unknown opcode: {op}")
