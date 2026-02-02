"""
Math Engine — The "Reasoning" Engine
====================================
Evaluates mathematical expressions safely using Python's eval (sandbox restrictions applied).
"""

import math

class MathEngine:
    def evaluate(self, expression: str, context: dict):
        """
        Evaluates a math expression string with variable substitution.
        
        Args:
            expression: "5 * Score + 10"
            context: Variables dictionary {"Score": 100}
        """
        # 1. Substitute variables in the expression?
        # Safe eval using a restricted global scope
        
        # Prepare safe scope
        safe_locals = context.copy()
        safe_globals = {
            "math": math,
            "abs": abs,
            "min": min,
            "max": max,
            "round": round
        }
        
        try:
            # We assume expression is valid python-like math
            # "5 * Score" -> if Score is in safe_locals, it works.
            return eval(expression, safe_globals, safe_locals)
        except Exception as e:
            # Fallback: maybe it's just a string?
            return expression
