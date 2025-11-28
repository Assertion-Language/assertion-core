"""
assertionctl — Unified CLI for Assertion Engine
===============================================

Capabilities:
- Run manifests
- Compile to SSA, IR, Bytecode, WASM, JIT
- Visualize IR (DOT + ASCII)
- Debug mode with breakpoints
- Execution tracing
- Distributed cluster (RAFT) runtime mode
- Fiber scheduling control
- Bytecode disassembler
- JIT output inspection
- Engine diagnostics

This is the main entry-point tool for developers.
"""

import argparse
import sys
from pathlib import Path

# Core engine
from engine.frontend.parser import parse_manifest
from engine.ir.ssa_lowering import lower_to_ssa
from engine.vm.bytecode_lowering import lower_to_bytecode
from engine.runtime.orchestrator import orchestrator
from engine.vm.disassembler import disassemble
from engine.visual.ir_visualizer import IRVisualizer
from engine.debug.debugger import debugger

# Fiber scheduler
from engine.scheduler.fibers import scheduler


# ============================================================
# COMMAND IMPLEMENTATIONS
# ============================================================

def cmd_run(args):
    text = Path(args.file).read_text()
    ast = parse_manifest(text)
    func = lower_to_ssa(ast)
    bc = lower_to_bytecode(func)

    if args.debug:
        orchestrator.enable_debugger()
    if args.trace:
        orchestrator.enable_tracing()

    # distributed mode?
    if args.cluster:
        port = args.port
        peers = [int(p) for p in args.peers.split(",")] if args.peers else []
        orchestrator.enable_cluster(port, peers)

    # select backend
    if args.backend:
        if args.backend == "vm":
            orchestrator.use_vm()
        elif args.backend == "jit":
            orchestrator.use_jit()
        elif args.backend == "wasm":
            orchestrator.use_wasm()
        elif args.backend == "auto":
            orchestrator.use_auto()

    orchestrator.run(func, bc)


def cmd_ir(args):
    text = Path(args.file).read_text()
    ast = parse_manifest(text)
    func = lower_to_ssa(ast)

    if args.ascii:
        IRVisualizer.print_ascii(func)
    else:
        out = args.out or (Path(args.file).stem + ".dot")
        IRVisualizer.to_dot(func, out)
        print(f"[OK] IR graph → {out}")


def cmd_bytecode(args):
    text = Path(args.file).read_text()
    ast = parse_manifest(text)
    func = lower_to_ssa(ast)
    bc = lower_to_bytecode(func)

    print(disassemble(bc))


def cmd_debug(args):
    text = Path(args.file).read_text()
    ast = parse_manifest(text)
    func = lower_to_ssa(ast)
    bc = lower_to_bytecode(func)

    orchestrator.enable_debugger()
    orchestrator.run(func, bc)


def cmd_trace(args):
    text = Path(args.file).read_text()
    ast = parse_manifest(text)
    func = lower_to_ssa(ast)
    bc = lower_to_bytecode(func)

    orchestrator.enable_tracing()
    orchestrator.run(func, bc)


def cmd_cluster(args):
    """
    Start a RAFT/Gossip cluster node only.
    """
    print(f"[CLUSTER] Starting node at port {args.port}")
    orchestrator.enable_cluster(args.port, [int(p) for p in args.peers.split(",")] if args.peers else [])
    orchestrator.cluster.blocking_start()


def cmd_fibers(args):
    """
    Show fiber scheduler status.
    """
    from engine.scheduler.fibers import scheduler
    print("=== Fiber Scheduler Status ===")
    print(f"Running: {scheduler.running}")
    print(f"Queued fibers: {len(scheduler.runq.q)}")
    print(f"Sleeping fibers: {len(scheduler.sleepers)}")


def cmd_version(_):
    print("Assertion Engine — Next-Gen Runtime")
    print("Version: 3.0 (VM + JIT + WASM + Cluster + Fibers)")


def cmd_diag(_):
    print("=== Engine Diagnostics ===")
    print(f"Python version: {sys.version}")
    print(f"Platform: {sys.platform}")
    print("Fiber Scheduler:", "running" if scheduler.running else "stopped")
    print("Debugger enabled:", orchestrator.debug_enabled)
    print("Tracing enabled:", orchestrator.trace_enabled)
    print("Cluster enabled:", orchestrator.cluster_enabled)


# ============================================================
# CLI SETUP
# ============================================================

def make_parser():
    p = argparse.ArgumentParser(prog="assertionctl", description="Assertion Engine Compiler / Runtime Tool")

    sub = p.add_subparsers(dest="cmd")

    # run
    r = sub.add_parser("run", help="Run manifest")
    r.add_argument("file")
    r.add_argument("--backend", choices=["vm", "jit", "wasm", "auto"])
    r.add_argument("--debug", action="store_true")
    r.add_argument("--trace", action="store_true")
    r.add_argument("--cluster", action="store_true")
    r.add_argument("--port", type=int, default=9000)
    r.add_argument("--peers", type=str)
    r.set_defaults(func=cmd_run)

    # ir
    ir = sub.add_parser("ir", help="Show IR / CFG graph")
    ir.add_argument("file")
    ir.add_argument("--ascii", action="store_true")
    ir.add_argument("--out")
    ir.set_defaults(func=cmd_ir)

    # bytecode dump
    bc = sub.add_parser("bytecode", help="Disassemble bytecode")
    bc.add_argument("file")
    bc.set_defaults(func=cmd_bytecode)

    # debug
    d = sub.add_parser("debug", help="Debug execution")
    d.add_argument("file")
    d.set_defaults(func=cmd_debug)

    # trace
    t = sub.add_parser("trace", help="Trace every instruction")
    t.add_argument("file")
    t.set_defaults(func=cmd_trace)

    # cluster node
    cl = sub.add_parser("cluster", help="Start standalone cluster node")
    cl.add_argument("--port", type=int, required=True)
    cl.add_argument("--peers", type=str)
    cl.set_defaults(func=cmd_cluster)

    # fibers inspect
    f = sub.add_parser("fibers", help="Inspect fiber scheduler")
    f.set_defaults(func=cmd_fibers)

    # version
    v = sub.add_parser("version", help="Show version")
    v.set_defaults(func=cmd_version)

    # diagnostics
    dg = sub.add_parser("diag", help="System/engine diagnostics")
    dg.set_defaults(func=cmd_diag)

    return p


# ============================================================
# ENTRY POINT
# ============================================================

def main():
    parser = make_parser()
    args = parser.parse_args()

    if not hasattr(args, "func"):
        parser.print_help()
        return

    args.func(args)


if __name__ == "__main__":
    main()
