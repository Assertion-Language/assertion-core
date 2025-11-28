"""
Bytecode Disassembler + Execution Trace
=======================================

Provides:
- Human-readable bytecode dump
- Instruction indexing
- Pretty formatting
- Execution tracing hooks for VM
- Integrates with debugger (engine/debug/debugger.py)
- ASCII-friendly output for iPad and terminals
"""

from typing import List, Dict, Any
from engine.vm.bytecode_vm import BCInstr, BytecodeProgram
from engine.debug.debugger import debug_vm_step, ExecutionContext


# ============================================================
# Pretty Names for Bytecode Ops
# ============================================================

OP_NAMES = {
    "LOAD_CONST": "LOAD_CONST",
    "LOAD":       "LOAD",
    "STORE":      "STORE",
    "ADD":        "ADD",
    "SUB":        "SUB",
    "MUL":        "MUL",
    "EQ":         "EQ",
    "GT":         "GT",
    "PRINT":      "PRINT",
    "FILE_CREATE": "FILE_CREATE",
    "FILE_WRITE":  "FILE_WRITE",
    "JMP":         "JMP",
    "JMP_IF":      "JMP_IF",
    "LABEL":       "LABEL",
}


# ============================================================
# DISASSEMBLER ENGINE
# ============================================================

class Disassembler:

    @staticmethod
    def format_instr(idx: int, instr: BCInstr) -> str:
        """
        Format a single bytecode instruction with index.
        """
        op = instr.op
        args = ", ".join(str(a) for a in instr.args)
        return f"{idx:04d}: {op:<12} {args}"

    @staticmethod
    def disassemble(program: BytecodeProgram) -> str:
        """
        Full bytecode dump in human-readable form.
        """
        output = []
        output.append("==== BYTECODE DUMP ====\n")

        for i, instr in enumerate(program.code):
            output.append(Disassembler.format_instr(i, instr))

        output.append("\n==== CONSTANT POOL ====")
        for i, c in enumerate(program.consts):
            output.append(f"  {i}: {c}")

        output.append("\n==== LABELS ====")
        for name, addr in program.labels.items():
            output.append(f"  {name}: {addr}")

        return "\n".join(output)


# ============================================================
# EXECUTION TRACER
# ============================================================

class ExecutionTracer:

    def __init__(self, program: BytecodeProgram):
        self.program = program
        self.ctx = ExecutionContext()
        self.enabled = False

    def enable(self):
        self.enabled = True

    def disable(self):
        self.enabled = False

    # Called by VM before executing an instruction
    def trace_step(self, ip: int, stack: List[Any], vars: Dict[int, Any]):
        if not self.enabled:
            return

        instr = self.program.code[ip]
        opname = instr.op
        args = instr.args

        print(f"[TRACE] IP={ip:04d}  {opname} {args}   stack={stack}   vars={vars}")

        # Provide debugger-style IR location
        self.ctx.ip = ip
        debug_vm_step(self.ctx, f"ip:{ip}")

    # Dump full code with tracing markers
    def print_disassembly(self):
        print(Disassembler.disassemble(self.program))


# ============================================================
# Public API
# ============================================================

def disassemble(program: BytecodeProgram) -> str:
    return Disassembler.disassemble(program)


def create_tracer(program: BytecodeProgram) -> ExecutionTracer:
    return ExecutionTracer(program)
