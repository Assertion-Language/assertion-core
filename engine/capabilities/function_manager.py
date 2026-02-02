"""
Function Manager — The "Teaching" Engine
========================================
Allows the user to define reusable skills using "TO [TASK]:" syntax.
"""

from typing import Dict, List, Optional
from engine.parser.ast_nodes import Trigger, Stmt

class FunctionManager:
    def __init__(self):
        # Maps "lower case task name" -> Trigger (block of code)
        self.skills: Dict[str, Trigger] = {}

    def teach(self, name: str, block: List[Stmt]):
        """
        Teaches the engine a new skill.
        Example: "To greet someone"
        """
        key = name.lower().strip()
        # Create a Trigger-like structure to hold the block
        # We reuse Trigger for convenience, though it's technically a Function
        skill = Trigger(name=name, line=0, block=block)
        self.skills[key] = skill
        print(f"[Brain] Learned new skill: '{name}'")

    def recall(self, name: str) -> Optional[Trigger]:
        """
        Retrieves a skill by name.
        """
        return self.skills.get(name.lower().strip())
