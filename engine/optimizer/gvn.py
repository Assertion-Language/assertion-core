"""
GVN — Global Value Numbering
============================
Compact implementation:
Eliminates redundant computations such as:
    a = x + y
    b = x + y   → replaced with a
"""

from engine.ir.ssa import Instruction, Function


def gvn(func: Function):
    table = {}  # tuple(op, args) → SSAValue

    for blk in func.blocks:
        new_instrs = []
        for inst in blk.instrs:
            if inst.result is None:
                new_instrs.append(inst)
                continue

            key = (inst.op, tuple(v.name for v in inst.args))

            if key in table:
                # Replace with known value
                inst.result.value = table[key].value
                inst.result.name = table[key].name
            else:
                table[key] = inst.result
                new_instrs.append(inst)

        blk.instrs = new_instrs
