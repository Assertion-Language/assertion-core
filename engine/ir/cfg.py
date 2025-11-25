"""
Control Flow Graph (CFG)
========================
Compact, essential infrastructure for:
- SSA validation
- Dominance calculation
- Optimizer passes (GVN, LICM, DCE)
- WASM structured control lowering
- JIT backend lowering

A Function consists of BasicBlocks. This module provides:
- Predecessor/successor resolution
- Reverse postorder
- Block reachability
- Dead block elimination
"""

from typing import List, Set
from engine.ir.ssa import Function, BasicBlock


# ============================================================
# Reverse Postorder (RPO)
# ============================================================

def reverse_postorder(func: Function) -> List[BasicBlock]:
    """
    Compute reverse postorder from entry block.
    This is important for dominance and SSA validations.
    """
    visited = set()
    order = []

    def dfs(blk):
        if blk in visited:
            return
        visited.add(blk)
        for succ in blk.succs:
            dfs(succ)
        order.append(blk)

    if func.blocks:
        dfs(func.blocks[0])  # entry block

    return list(reversed(order))


# ============================================================
# Reachability Analysis
# ============================================================

def reachable_blocks(func: Function) -> Set[BasicBlock]:
    """Return set of blocks reachable from entry."""
    if not func.blocks:
        return set()

    entry = func.blocks[0]
    seen = set()
    stack = [entry]

    while stack:
        blk = stack.pop()
        if blk in seen:
            continue
        seen.add(blk)
        for s in blk.succs:
            stack.append(s)

    return seen


# ============================================================
# Dead Block Elimination
# ============================================================

def remove_dead_blocks(func: Function):
    """
    Remove blocks not reachable from entry. Compact but effective.
    """
    alive = reachable_blocks(func)
    func.blocks = [b for b in func.blocks if b in alive]


# ============================================================
# Utility: Print Graph Relationships
# ============================================================

def dump_cfg(func: Function):
    print("==== CFG DUMP ====")
    for blk in func.blocks:
        print(f"{blk.name}:")
        if blk.succs:
            print("  succs: ", [b.name for b in blk.succs])
        if blk.preds:
            print("  preds: ", [b.name for b in blk.preds])
