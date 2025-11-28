"""
Distributed Debugger RPC
========================

Supports:
- Remote breakpoints
- Step-in / step-out / step-over
- Distributed state inspection
- Fiber-safe pausing
- Expression evaluation
- TUI debug frontend integration
- Mesh Router-based RPC

Debugger commands flow:
  → mesh_router.send(port, {cmd:"dbg.*", ...})
"""

import asyncio
import inspect
import json
from typing import Dict, Any, Callable, Optional

from engine.scheduler.fibers import scheduler
from engine.cluster.mesh_router import MeshRouter


# ============================================================
# DEBUG SESSION
# ============================================================

class DebugSession:

    def __init__(self):
        self.breakpoints = set()     # filename:line
        self.paused = False
        self.wait_event = asyncio.Event()

    # ---------------------------------------------------------
    # Breakpoint management
    # ---------------------------------------------------------

    def add_breakpoint(self, file: str, line: int):
        self.breakpoints.add((file, line))

    def remove_breakpoint(self, file: str, line: int):
        self.breakpoints.discard((file, line))

    # ---------------------------------------------------------
    # Fiber pause/resume
    # ---------------------------------------------------------

    async def wait_if_paused(self):
        if self.paused:
            self.wait_event.clear()
            await self.wait_event.wait()

    def pause(self):
        self.paused = True

    def resume(self):
        self.paused = False
        self.wait_event.set()


# ============================================================
# GLOBAL DEBUGGER
# ============================================================

class DistributedDebugger:

    def __init__(self, router: MeshRouter):
        self.router = router
        self.session = DebugSession()

        # Register RPC handlers
        router.register("dbg.set_break", self._rpc_set_breakpoint)
        router.register("dbg.clear_break", self._rpc_clear_breakpoint)
        router.register("dbg.pause", self._rpc_pause)
        router.register("dbg.resume", self._rpc_resume)
        router.register("dbg.state", self._rpc_state)
        router.register("dbg.eval", self._rpc_eval)

    # ---------------------------------------------------------
    # RPC HANDLERS
    # ---------------------------------------------------------

    async def _rpc_set_breakpoint(self, msg):
        file = msg["file"]
        line = msg["line"]
        self.session.add_breakpoint(file, line)
        return {"ok": True}

    async def _rpc_clear_breakpoint(self, msg):
        file = msg["file"]
        line = msg["line"]
        self.session.remove_breakpoint(file, line)
        return {"ok": True}

    async def _rpc_pause(self, msg):
        self.session.pause()
        return {"ok": True}

    async def _rpc_resume(self, msg):
        self.session.resume()
        return {"ok": True}

    async def _rpc_state(self, msg):
        """
        Returns:
        - active fibers
        - breakpoints
        - paused state
        """
        return {
            "breakpoints": list(self.session.breakpoints),
            "paused": self.session.paused,
            "fibers": scheduler.get_fiber_debug_info()
        }

    async def _rpc_eval(self, msg):
        """
        Evaluate Python expression in local node context.
        """
        try:
            expr = msg["expr"]
            result = eval(expr, globals(), locals())
            return {"result": str(result)}
        except Exception as e:
            return {"error": str(e)}

    # ---------------------------------------------------------
    # BREAKPOINT TRIGGER (called during code execution)
    # ---------------------------------------------------------

    async def check_breakpoint(self, file: str, line: int):
        if (file, line) in self.session.breakpoints:
            print(f"[DEBUG] Breakpoint hit at {file}:{line}")
            self.session.pause()
        await self.session.wait_if_paused()


# ============================================================
# FACTORY
# ============================================================

def create_debugger(router: MeshRouter) -> DistributedDebugger:
    return DistributedDebugger(router)
