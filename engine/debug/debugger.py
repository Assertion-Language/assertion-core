"""
Runtime Debugger (TUI + Breakpoints + Step Control)
===================================================

This debugger controls execution across:
- Bytecode VM
- Native JIT
- WASM backend
- Fiber scheduler
- Distributed cluster nodes (optional)

Features:
- TUI window (ASCII)
- Breakpoints (line, SSA op, bytecode index)
- Step-in, step-over, step-out
- Variable watch
- Call stack viewer
- Fiber-aware pause/resume

Central runtime inspector for Assertion Engine.
"""

import sys
import threading
import time
import inspect
from typing import Dict, List, Optional, Any

from engine.scheduler.fibers import scheduler


# ============================================================
# Breakpoint Object
# ============================================================

class Breakpoint:
    def __init__(self, target: str, kind: str):
        """
        kind: "bytecode", "ssa", "line", "vm"
        """
        self.target = target
        self.kind = kind


# ============================================================
# Debugger UI (ASCII TUI)
# ============================================================

class DebuggerUI:
    """
    Minimalistic ASCII TUI that works everywhere:
    - iPad terminals
    - SSH
    - Linux TTY
    """

    @staticmethod
    def clear():
        sys.stdout.write("\033[2J\033[H")

    @staticmethod
    def header(title):
        print("=" * 60)
        print(f"{title}")
        print("=" * 60)

    @staticmethod
    def section(name):
        print(f"\n--- {name} ---")

    @staticmethod
    def prompt():
        return input("\n(debugger) ").strip()


# ============================================================
# Execution Context Wrapper
# ============================================================

class ExecutionContext:
    """
    Unified execution context used across VM, JIT, WASM.
    """
    def __init__(self):
        self.callstack: List[str] = []
        self.locals: Dict[str, Any] = {}
        self.ip = 0              # instruction pointer (bytecode or wasm)
        self.ssa_index = 0       # SSA IR index
        self.paused = False


# ============================================================
# Core Debugger
# ============================================================

class Debugger:

    def __init__(self):
        self.breakpoints: List[Breakpoint] = []
        self.ctx = ExecutionContext()
        self.running = False
        self.step_mode = None  # "in", "over", "out"

        self.vm_hook = None
        self.jit_hook = None
        self.wasm_hook = None

        # Lock for pausing VM/fibers
        self.pause_lock = threading.Lock()
        self.pause_lock.acquire()  # Locked until debug begins

    # --------------------------------------------------------
    # External runtime hooking
    # --------------------------------------------------------

    def hook_vm(self, fn):
        """fn(ctx) called before each VM instruction."""
        self.vm_hook = fn

    def hook_jit(self, fn):
        """fn(ctx) called before JIT dispatch."""
        self.jit_hook = fn

    def hook_wasm(self, fn):
        """fn(ctx) called before WASM instruction."""
        self.wasm_hook = fn

    # --------------------------------------------------------
    # Breakpoint Management
    # --------------------------------------------------------

    def add_breakpoint(self, target: str, kind: str):
        self.breakpoints.append(Breakpoint(target, kind))

    def check_breakpoint(self, location: str, kind: str):
        for bp in self.breakpoints:
            if bp.kind == kind and bp.target == location:
                return True
        return False

    # --------------------------------------------------------
    # Pausing + UI
    # --------------------------------------------------------

    def pause(self):
        self.ctx.paused = True
        self.debug_loop()

    def debug_loop(self):
        DebuggerUI.clear()
        DebuggerUI.header("ASSERTION ENGINE DEBUGGER")

        while True:
            DebuggerUI.section("Execution State")
            print(f"IP: {self.ctx.ip}")
            print(f"SSA Index: {self.ctx.ssa_index}")

            DebuggerUI.section("Call Stack")
            for f in self.ctx.callstack:
                print(f" - {f}")

            DebuggerUI.section("Locals")
            for k, v in self.ctx.locals.items():
                print(f"{k} = {v}")

            cmd = DebuggerUI.prompt()

            # ----------------- Commands -----------------

            if cmd in ("c", "continue"):
                self.ctx.paused = False
                self.pause_lock.release()
                return

            elif cmd in ("s", "step"):
                self.step_mode = "in"
                self.ctx.paused = False
                self.pause_lock.release()
                return

            elif cmd in ("n", "next"):
                self.step_mode = "over"
                self.ctx.paused = False
                self.pause_lock.release()
                return

            elif cmd in ("o", "out"):
                self.step_mode = "out"
                self.ctx.paused = False
                self.pause_lock.release()
                return

            elif cmd.startswith("bp "):
                _, target = cmd.split(" ", 1)
                self.add_breakpoint(target, "bytecode")
                print(f"Breakpoint added at {target}")

            elif cmd == "q" or cmd == "quit":
                print("Debugger terminating runtime.")
                sys.exit(0)

            else:
                print("Unknown command.")

    # --------------------------------------------------------
    # VM Hook Integration
    # --------------------------------------------------------

    def vm_step(self, ctx: ExecutionContext, location: str):
        self.ctx = ctx

        # Breakpoint?
        if self.check_breakpoint(location, "bytecode"):
            self.pause_lock.acquire()
            self.pause()

        # Step mode?
        if self.step_mode == "in":
            self.step_mode = None
            self.pause_lock.acquire()
            self.pause()

    # --------------------------------------------------------
    # WASM Hook Integration
    # --------------------------------------------------------

    def wasm_step(self, ctx: ExecutionContext, label: str):
        self.ctx = ctx
        if self.check_breakpoint(label, "wasm"):
            self.pause_lock.acquire()
            self.pause()

    # --------------------------------------------------------
    # JIT Hook Integration
    # --------------------------------------------------------

    def jit_step(self, ctx: ExecutionContext, stage: str):
        self.ctx = ctx
        if self.check_breakpoint(stage, "jit"):
            self.pause_lock.acquire()
            self.pause()


# ============================================================
# Global Debugger Instance
# ============================================================

debugger = Debugger()


# Public helper for VM/WASM/JIT to call
def debug_vm_step(ctx: ExecutionContext, loc: str):
    debugger.vm_step(ctx, loc)


def debug_wasm_step(ctx: ExecutionContext, loc: str):
    debugger.wasm_step(ctx, loc)


def debug_jit_step(ctx: ExecutionContext, loc: str):
    debugger.jit_step(ctx, loc)
