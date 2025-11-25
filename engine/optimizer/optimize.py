"""
Optimizer Entry Point
=====================
Combine all optimization passes into one pipeline.
"""

from engine.optimizer.passes import PassManager
from engine.optimizer.gvn import gvn
from engine.optimizer.licm import licm
from engine.optimizer.dce import dce
from engine.ir.ssa import Function


def optimize(func: Function):
    pm = PassManager()
    pm.add_pass(gvn)
    pm.add_pass(licm)
    pm.add_pass(dce)
    pm.run(func)
    return func
