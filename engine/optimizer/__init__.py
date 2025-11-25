"""
Optimization Pass Registry
==========================
Central place to register and organize optimization passes.
"""

from typing import List, Callable
from engine.ir.ssa import Function


class PassManager:
    def __init__(self):
        self.passes: List[Callable[[Function], None]] = []

    def add_pass(self, fn: Callable[[Function], None]):
        self.passes.append(fn)

    def run(self, func: Function):
        for p in self.passes:
            p(func)
