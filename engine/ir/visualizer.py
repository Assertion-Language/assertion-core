"""
IR Visualizer — SSA + CFG + Dominance
=====================================

Compact but powerful visualization layer:
- Pretty-print SSA IR
- Pretty-print CFG structure
- Graphviz DOT output (if desired)
- Dominance tree visualization
"""

from engine.ir.ssa import Function, BasicBlock, Instr, SSAValue
from engine.ir.cfg import reachable_blocks
from engine.ir.dominance import compute_idoms
from typing import Dict


# ============================================================
# Pretty-print IR
# ============================================================

def print_ir(func: Function):
    print("===== SSA FUNCTION DUMP =====")
    for blk in func.blocks:
        print(f"\n[{blk.name}]")
        for inst in blk.instrs:
            print("  ", inst)
        if blk.terminator:
            print("  ", blk.terminator)


# ============================================================
# Pretty-print CFG
# ============================================================

def print_cfg(func: Function):
    print("\n===== CONTROL FLOW GRAPH =====")
    for blk in func.blocks:
        succs = [s.name for s in blk.succs]
        preds = [p.name for p in blk.preds]
        print(f"{blk.name}:")
        print(f"  preds: {preds}")
        print(f"  succs: {succs}")


# ============================================================
# Dominance Tree Visualization
# ============================================================

def print_dominators(func: Function):
    idom = compute_idoms(func)
    print("\n===== DOMINANCE (idom) =====")
    for blk, dom in idom.items():
        root = dom.name if dom else "None"
        print(f"{blk.name} <- {root}")


# ============================================================
# Graphviz DOT Export
# ============================================================

def to_dot(func: Function) -> str:
    """
    Generate DOT graph representation for visualization.
    Compatible with Graphviz, Viz.js, or online DOT viewers.
    """

    out = ["digraph cfg {", '  node [shape=box, fontname="Courier"];']

    for blk in func.blocks:
        # Label block with its instructions
        label = f"{blk.name}\\n"
        for i in blk.instrs:
            label += f"  {i}\\n"
        if blk.terminator:
            label += f"  {blk.terminator}\\n"

        out.append(f'  "{blk.name}" [label="{label}"];')

        # Succ edges
        for s in blk.succs:
            out.append(f'  "{blk.name}" -> "{s.name}";')

    out.append("}")
    return "\n".join(out)


def save_dot(func: Function, path: str):
    """
    Save DOT graph to file.
    """
    dot = to_dot(func)
    with open(path, "w") as f:
        f.write(dot)
    print(f"[Visualizer] DOT saved to {path}")
