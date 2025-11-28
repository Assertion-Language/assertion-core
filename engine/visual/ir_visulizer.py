"""
IR Visualizer — SSA Graph + CFG Renderer + ASCII Fallback
=========================================================

Generates:
- GraphViz DOT files
- SSA IR node graphs
- Control flow graph (CFG)
- Dominator graph (if provided)
- ASCII mode for iPad / minimal terminals

Fully compatible with:
- SSA IR (engine/ir/ssa.py)
- Optimizer
- WASM backend
- JIT backend
"""

from typing import List
from engine.ir.ssa import Function, BasicBlock, Instr
import textwrap


# ============================================================
# DOT Helpers
# ============================================================

def dot_escape(s: str) -> str:
    return s.replace('"', '\\"')


def dot_header():
    return "digraph IR {\n  rankdir=TB;\n  node [shape=box, fontname=Courier];\n"


def dot_footer():
    return "}\n"


# ============================================================
# SSA Node Label Builders
# ============================================================

def format_instr(inst: Instr) -> str:
    """Compact label for IR nodes."""
    if inst.result:
        return f"{inst.result.name} = {inst.op}({', '.join(a.name for a in inst.args)})"
    else:
        return f"{inst.op}({', '.join(a.name for a in inst.args)})"


def block_label(blk: BasicBlock) -> str:
    out = [f"{blk.name}:"]
    for inst in blk.instrs:
        out.append("  " + format_instr(inst))
    if blk.terminator:
        out.append("  TERM: " + format_instr(blk.terminator))
    return "\\l".join(out) + "\\l"


# ============================================================
# CFG Graph Builder
# ============================================================

def build_cfg_edges(func: Function):
    edges = []
    for blk in func.blocks:
        if blk.terminator:
            inst = blk.terminator
            if inst.op == "br":
                edges.append((blk.name, inst.args[0].name))
            elif inst.op == "cbr":
                edges.append((blk.name, inst.args[1].name))  # then
                edges.append((blk.name, inst.args[2].name))  # else
    return edges


# ============================================================
# DOT Generator for Full SSA IR
# ============================================================

def generate_dot(func: Function) -> str:
    out = dot_header()

    # Nodes
    for blk in func.blocks:
        label = block_label(blk)
        out += f'  "{blk.name}" [label="{dot_escape(label)}"];\n'

    # Edges
    for src, dst in build_cfg_edges(func):
        out += f'  "{src}" -> "{dst}";\n'

    out += dot_footer()
    return out


# ============================================================
# ASCII Visualizer (iPad + no Graphviz mode)
# ============================================================

def ascii_graph(func: Function) -> str:
    """
    Generates a pretty ASCII representation of IR:
    - Blocks
    - Instructions
    - CFG arrows
    """

    lines = []
    lines.append("=" * 60)
    lines.append(f" IR ASCII VISUALIZATION — Function: {func.name}")
    lines.append("=" * 60)

    for blk in func.blocks:
        lines.append(f"\n[{blk.name}]")
        lines.append("-" * 60)

        for inst in blk.instrs:
            lines.append("  " + format_instr(inst))

        if blk.terminator:
            lines.append("  TERM: " + format_instr(blk.terminator))

        # outgoing edges
        out_edges = []
        for src, dst in build_cfg_edges(func):
            if src == blk.name:
                out_edges.append(dst)

        if out_edges:
            lines.append(f"   --> {', '.join(out_edges)}")

    return "\n".join(lines)


# ============================================================
# Public Visualizer API
# ============================================================

class IRVisualizer:

    @staticmethod
    def to_dot(func: Function, path: str):
        """Write SSA/CFG graph to .dot file."""
        with open(path, "w") as f:
            f.write(generate_dot(func))

    @staticmethod
    def to_ascii(func: Function) -> str:
        """Return ASCII diagram."""
        return ascii_graph(func)

    @staticmethod
    def print_ascii(func: Function):
        print(ascii_graph(func))
