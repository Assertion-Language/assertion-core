"""
LICM — Loop Invariant Code Motion
=================================
Highly compact LICM:
Moves loop-invariant expressions out of the loop header.
"""

from engine.ir.ssa import Function, BasicBlock
from engine.ir.cfg import reachable_blocks


def licm(func: Function):
    # Placeholder: Compact LICM based on block identity.
    # True LICM requires loop detection via dominators.

    if len(func.blocks) < 3:
        return

    header = func.blocks[1]
    body = func.blocks[2]

    movable = []
    for inst in body.instrs:
        if inst.op in ("add", "sub", "mul", "const") and all(
            a.typ in ("i32", "f64") for a in inst.args
        ):
            movable.append(inst)

    for inst in movable:
        body.instrs.remove(inst)
        header.instrs.append(inst)
