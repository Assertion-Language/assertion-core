"""
DCE — Dead Code Elimination
===========================
Removes instructions whose results are never used.
"""

from engine.ir.ssa import Function


def dce(func: Function):
    used = set()

    # Find used registers
    for blk in func.blocks:
        for inst in blk.instrs:
            for arg in inst.args:
                used.add(arg.name)

    # Remove unused
    for blk in func.blocks:
        blk.instrs = [
            inst for inst in blk.instrs
            if inst.result is None or inst.result.name in used
        ]
