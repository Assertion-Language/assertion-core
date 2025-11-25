"""
Dominance Analysis
==================
Compact, production-strength dominator computation:
- Immediate dominators via iterative algorithm
- Dominance tree
- Dominance frontier
- Essential for SSA, LICM, GVN, block restructuring

This module assumes:
- Function.blocks[0] is entry
- CFG successors/preds populated
"""

from typing import Dict, Set, List
from engine.ir.ssa import Function, BasicBlock
from engine.ir.cfg import reverse_postorder


# ============================================================
# Compute Immediate Dominators (idom)
# ============================================================

def compute_idoms(func: Function) -> Dict[BasicBlock, BasicBlock]:
    """
    Lengauer-Tarjan algorithm is compact but long;
    here we use a simple iterative algorithm suitable
    for medium-sized programs. Compact + stable.
    """

    blocks = reverse_postorder(func)
    if not blocks:
        return {}

    entry = blocks[0]

    # All blocks initially dominate by all; entry only by itself
    idom = {b: None for b in blocks}
    idom[entry] = entry

    changed = True
    while changed:
        changed = False
        for b in blocks[1:]:
            preds = [p for p in b.preds if idom[p] is not None]
            if not preds:
                continue

            # Start with first processed predecessor
            new_idom = preds[0]
            for p in preds[1:]:
                new_idom = intersect(idom, p, new_idom)

            if idom[b] != new_idom:
                idom[b] = new_idom
                changed = True

    return idom


def intersect(idom, b1, b2):
    """
    Intersect dominance paths.
    """
    f1 = b1
    f2 = b2
    while f1 != f2:
        # move the one with deeper rpo index
        f1 = idom[f1]
        f2 = idom[f2]
    return f1


# ============================================================
# Dominance Frontier
# ============================================================

def compute_dominance_frontier(func: Function, idom: Dict[BasicBlock, BasicBlock]):
    """
    Computes the dominance frontier (DF):
    DF[b] = { y | b does not strictly dominate y
              AND b dominates a predecessor of y }
    """
    df = {b: set() for b in func.blocks}

    for b in func.blocks:
        if len(b.preds) >= 2:
            for p in b.preds:
                runner = p
                while runner != idom[b] and runner is not None:
                    df[runner].add(b)
                    runner = idom[runner]

    return df


# ============================================================
# Dump utilities
# ============================================================

def dump_idoms(idom):
    print("==== IMMEDIATE DOMINATORS ====")
    for b, d in idom.items():
        print(f"{b.name} <- {d.name if d else 'None'}")


def dump_df(df):
    print("==== DOMINANCE FRONTIER ====")
    for b, s in df.items():
        if s:
            print(f"{b.name}: {[x.name for x in s]}")
