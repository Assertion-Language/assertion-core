
import unittest
from engine.parser.fuzzy_parser import FuzzyParser
from engine.runtime.interpreter import Interpreter

class TestREPLLogic(unittest.TestCase):
    def test_interactive_flow(self):
        # This mirrors the logic in repl.py
        parser = FuzzyParser()
        interp = Interpreter()
        
        # 1. User types a declaration
        cmd1 = "I want a number called 'Score' starting at 10."
        ast1 = parser.parse(cmd1)
        for decl in ast1.globals:
            interp.state[decl.name] = decl.value
            
        self.assertEqual(interp.state["Score"], 10)
        
        # 2. User types a command (top-level)
        cmd2 = "Add 5 to 'Score'."
        ast2 = parser.parse(cmd2)
        # Should be in "Interactive" trigger
        interactive = next((t for t in ast2.triggers if t.name == "Interactive"), None)
        self.assertIsNotNone(interactive)
        
        interp.execute_block(interactive.block)
        self.assertEqual(interp.state["Score"], 15)
        
        # 3. User checks value
        cmd3 = "Tell me the 'Score'."
        ast3 = parser.parse(cmd3)
        interactive = next((t for t in ast3.triggers if t.name == "Interactive"), None)
        interp.execute_block(interactive.block)
        # Check output stream (Interpreter captures it)
        self.assertIn("15", interp.out_stream)

if __name__ == '__main__':
    unittest.main()
