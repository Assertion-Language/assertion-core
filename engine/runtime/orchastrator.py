"""
Runtime Orchestrator
====================

This module unifies:

- Bytecode VM
- Native JIT backend
- WASM backend
- Fiber scheduler
- Distributed cluster runtime (RAFT + Gossip)
- Debugger (breakpoints/steps)
- IR visualizer and execution tracer

The orchestrator is the “brain” of the Assertion Engine:
It selects how, where, and when to run code.
"""

import threading
import asyncio
import time
from typing import Optional, Callable

# Core backends
from engine.vm.bytecode_vm import BytecodeProgram, VM
from engine.vm.disassembler import create_tracer
from engine.jit.native_jit import jit_compile
from engine.wasm.wasm_backend import compile_to_wasm

# Runtime orchestration
from engine.scheduler.fibers import scheduler
from engine.cluster.distributed import DistributedEngine

# Debugging
from engine.debug.debugger import debugger, ExecutionContext

# Visualization
from engine.visual.ir_visualizer import IRVisualizer


# ============================================================
# Orchestrator Modes
# ============================================================

EXEC_VM   = "vm"
EXEC_JIT  = "jit"
EXEC_WASM = "wasm"
EXEC_AUTO = "auto"   # smart mode
EXEC_DIST = "cluster"


# ============================================================
# ORCHESTRATOR
# ============================================================

class RuntimeOrchestrator:

    def __init__(self):
        self.backend = EXEC_AUTO
        self.cluster: Optional[DistributedEngine] = None
        self.cluster_enabled = False
        self.debug_enabled = False
        self.trace_enabled = False

        # VM/JIT/WASM objects
        self.vm: Optional[VM] = None
        self.jit_func = None
        self.wasm_bytes = None

        # Execution tracer (bytecode)
        self.tracer = None

    # ---------------------------------------------------------
    # Configure Backend
    # ---------------------------------------------------------

    def use_vm(self):
        self.backend = EXEC_VM

    def use_jit(self):
        self.backend = EXEC_JIT

    def use_wasm(self):
        self.backend = EXEC_WASM

    def use_auto(self):
        self.backend = EXEC_AUTO

    def enable_cluster(self, port: int, peers: list[int]):
        self.cluster = DistributedEngine(port, peers)
        self.cluster_enabled = True

    def enable_debugger(self):
        self.debug_enabled = True

    def enable_tracing(self):
        self.trace_enabled = True

    # ---------------------------------------------------------
    # Visualization
    # ---------------------------------------------------------

    def visualize_ir(self, func, ascii=False, out_path=None):
        if ascii:
            IRVisualizer.print_ascii(func)
        else:
            if not out_path:
                out_path = f"{func.name}.dot"
            IRVisualizer.to_dot(func, out_path)
            print(f"[VISUAL] IR graph saved to: {out_path}")

    # ---------------------------------------------------------
    # Pre-Execution Preparation
    # ---------------------------------------------------------

    def prepare(self, func, bc: BytecodeProgram):
        """
        Prepare VM/JIT/WASM artifacts.
        """
        # Bytecode & tracer
        self.tracer = create_tracer(bc)

        # VM
        self.vm = VM(bc)

        # JIT native
        try:
            self.jit_func = jit_compile(func)
        except Exception as e:
            print("[JIT] Failed:", e)
            self.jit_func = None

        # WASM
        try:
            self.wasm_bytes = compile_to_wasm(func)
        except Exception as e:
            print("[WASM] Failed:", e)
            self.wasm_bytes = None

    # ---------------------------------------------------------
    # Backend Selection Logic
    # ---------------------------------------------------------

    def select_backend(self):
        """
        AUTO mode prioritizes:
            1. JIT (if fully supported)
            2. WASM
            3. VM
        """
        if self.backend != EXEC_AUTO:
            return self.backend

        if self.jit_func:
            return EXEC_JIT
        if self.wasm_bytes:
            return EXEC_WASM
        return EXEC_VM

    # ---------------------------------------------------------
    # Execution Entry
    # ---------------------------------------------------------

    def run(self, func, bc: BytecodeProgram):
        """Run function using the selected execution model."""
        self.prepare(func, bc)

        # Start cluster if needed
        if self.cluster_enabled:
            asyncio.run(self.cluster.start())

        mode = self.select_backend()

        print(f"[ORCH] Using backend: {mode.upper()}")

        if mode == EXEC_VM:
            self.execute_vm()
        elif mode == EXEC_JIT:
            self.execute_jit()
        elif mode == EXEC_WASM:
            self.execute_wasm()
        else:
            raise ValueError("Unknown backend")

    # ---------------------------------------------------------
    # VM Execution with Fiber and Debugger
    # ---------------------------------------------------------

    def execute_vm(self):

        def fiber_vm():
            if self.trace_enabled:
                self.tracer.enable()
            else:
                self.tracer.disable()

            program = self.vm.program

            # VM run loop with debugger hooks
            while self.vm.pc < len(program.code):
                instr = program.code[self.vm.pc]

                # Trace hook
                if self.trace_enabled:
                    self.tracer.trace_step(
                        self.vm.pc,
                        self.vm.stack,
                        self.vm.vars
                    )

                # Debugger step hook
                if self.debug_enabled:
                    ctx = ExecutionContext()
                    ctx.ip = self.vm.pc
                    ctx.locals = dict(self.vm.vars)

                    debugger.vm_step(ctx, f"ip:{self.vm.pc}")

                # Execute instruction
                self.vm.step()

            print("[VM] Execution finished.")

        scheduler.spawn(fiber_vm, priority=128)
        scheduler.start()

    # ---------------------------------------------------------
    # Native JIT Execution (single-shot)
    # ---------------------------------------------------------

    def execute_jit(self):
        if not self.jit_func:
            print("[JIT] Not available, falling back to VM.")
            return self.execute_vm()

        # Debug step
        if self.debug_enabled:
            ctx = ExecutionContext()
            ctx.ip = 0
            debugger.jit_step(ctx, "entry")

        result = self.jit_func()
        print("[JIT] Execution Result:", result)

    # ---------------------------------------------------------
    # WASM Execution
    # ---------------------------------------------------------

    def execute_wasm(self):
        if not self.wasm_bytes:
            print("[WASM] Not available, falling back to VM.")
            return self.execute_vm()

        # WASM engine required — external call
        print("[WASM] Produced WASM module (bytes):", len(self.wasm_bytes))
        print("[WASM] For actual execution, load with: wasmtime / wasmer / browser.")

        # Debug stub call
        if self.debug_enabled:
            ctx = ExecutionContext()
            ctx.ip = 0
            debugger.wasm_step(ctx, "entry")

        print("[WASM] Execution finished (external execution required).")


# ============================================================
# Global Orchestrator Instance
# ============================================================

orchestrator = RuntimeOrchestrator()
