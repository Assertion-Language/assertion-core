"""
Debugger TUI (Terminal UI)
==========================

This is an ncurses-like TUI interface for the distributed debugger.

Modules integrated:
- debug_rpc (File 22)
- mesh_router (File 21)
- event_bus (File 19)
- workflow_state
- execution_graph
- fiber scheduler

This TUI works even in minimal terminals, including on iPadOS shells.
"""

import asyncio
import curses
import json
import time

from typing import Dict, Any, List

from engine.cluster.mesh_router import MeshRouter


# ============================================================
# THE TUI APPLICATION
# ============================================================

class DebuggerTUI:

    def __init__(self, router: MeshRouter, target_port: int):
        self.router = router
        self.target_port = target_port

        self.screen = None
        self.height = 0
        self.width = 0

        self.last_state = None
        self.last_events: List[str] = []

        # Async update task
        asyncio.create_task(self._update_loop())

    # ---------------------------------------------------------
    # MAIN WRAPPER
    # ---------------------------------------------------------

    def start(self):
        curses.wrapper(self._run_curses)

    # ---------------------------------------------------------
    # CURSES INIT
    # ---------------------------------------------------------

    def _run_curses(self, scr):
        self.screen = scr
        curses.curs_set(0)
        scr.nodelay(True)
        scr.clear()

        while True:
            try:
                self.height, self.width = scr.getmaxyx()
                self._draw(scr)
                ch = scr.getch()

                if ch == ord("q"):
                    break
                elif ch == ord("p"):
                    asyncio.run(self._cmd_pause())
                elif ch == ord("r"):
                    asyncio.run(self._cmd_resume())

                time.sleep(0.05)

            except KeyboardInterrupt:
                break

    # ---------------------------------------------------------
    # UI SECTIONS
    # ---------------------------------------------------------

    def _draw(self, scr):
        scr.clear()

        # Header
        scr.addstr(0, 0, f"DISTRIBUTED DEBUGGER — Node {self.target_port}".ljust(self.width), curses.A_REVERSE)

        # Section layout
        bp_height = self.height // 4
        fiber_height = self.height // 4
        event_height = self.height - (bp_height + fiber_height + 2)

        # Breakpoints Panel
        self._draw_breakpoints(scr, 1, 0, bp_height)

        # Fiber Panel
        self._draw_fibers(scr, 1 + bp_height, 0, fiber_height)

        # Event Panel
        self._draw_events(scr, 1 + bp_height + fiber_height, 0, event_height)

        scr.refresh()

    def _draw_breakpoints(self, scr, y, x, h):
        scr.addstr(y, x, "[BREAKPOINTS]", curses.A_BOLD)

        if not self.last_state:
            return

        for i, bp in enumerate(self.last_state.get("breakpoints", [])):
            if i >= h - 2:
                break
            scr.addstr(y + 1 + i, x, f"{bp[0]}:{bp[1]}")

    def _draw_fibers(self, scr, y, x, h):
        scr.addstr(y, x, "[FIBERS]", curses.A_BOLD)

        if not self.last_state:
            return

        fibers = self.last_state.get("fibers", [])

        for i, f in enumerate(fibers):
            if i >= h - 2:
                break
            scr.addstr(y + 1 + i, x, f"#{f['id']}  {f['status']}")

    def _draw_events(self, scr, y, x, h):
        scr.addstr(y, x, "[EVENT STREAM]", curses.A_BOLD)

        for i, line in enumerate(self.last_events[-(h - 2):]):
            scr.addstr(y + 1 + i, x, line[: self.width - 1])

    # ---------------------------------------------------------
    # FETCH REMOTE DEBUG STATE
    # ---------------------------------------------------------

    async def _update_loop(self):
        """
        Polls target node for debug state & recent events
        """
        await asyncio.sleep(1)

        while True:
            state = await self.router.send(self.target_port, {"cmd": "dbg.state"})
            if state and "paused" in state:
                self.last_state = state

            # random events from cluster
            es = await self.router.send(self.target_port, {"cmd": "get_event_sample"})
            if es and "events" in es:
                for e in es["events"]:
                    msg = f"[{e.get('timestamp', 0):.3f}] {e.get('channel')} → {e.get('payload')}"
                    self.last_events.append(msg)

            await asyncio.sleep(0.5)

    # ---------------------------------------------------------
    # COMMANDS
    # ---------------------------------------------------------

    async def _cmd_pause(self):
        await self.router.send(self.target_port, {"cmd": "dbg.pause"})

    async def _cmd_resume(self):
        await self.router.send(self.target_port, {"cmd": "dbg.resume"})


# ============================================================
# FACTORY
# ============================================================

def create_debugger_tui(router: MeshRouter, target_port: int) -> DebuggerTUI:
    return DebuggerTUI(router, target_port)
