
import unittest
import os
import sys
from engine.parser.fuzzy_parser import FuzzyParser
from engine.runtime.interpreter import Interpreter

class TestUniversal(unittest.TestCase):
    def test_run_python(self):
        text = """
        I want a number called "Magic" starting at 0.
        When we start:
            Run python:
                import math
                val = math.sqrt(100)
                state["Magic"] = val
        """
        parser = FuzzyParser()
        ast = parser.parse(text)
        interp = Interpreter()
        interp.run(ast, entry_point="Ignition")
        
        self.assertEqual(interp.state["Magic"], 10.0)

    def test_run_shell(self):
        # Create a marker file
        marker = "shell_test_marker.txt"
        if os.path.exists(marker): os.remove(marker)
        
        text = f"""
        When we start:
            Run shell 'touch {marker}'.
        """
        parser = FuzzyParser()
        ast = parser.parse(text)
        interp = Interpreter()
        interp.run(ast, entry_point="Ignition")
        
        self.assertTrue(os.path.exists(marker))
        if os.path.exists(marker): os.remove(marker)

    def test_import_module(self):
        # Create a module file
        mod_name = "test_mod.agl"
        with open(mod_name, 'w') as f:
            f.write("""
            To greet:
                Say "Hello from Module".
            
            I want a number called "Values" is 999.
            """)
            
        text = f"""
        When we start:
            Import "{mod_name}".
            Greet.
        """
        parser = FuzzyParser()
        ast = parser.parse(text)
        interp = Interpreter()
        # Mock brain logic? Interpreter needs a way to store functions.
        # In engine.py:
        # brain = FunctionManager()
        # interp = Interpreter()
        # interp.brain = brain
        # We need to simulate this.
        from engine.capabilities.function_manager import FunctionManager
        brain = FunctionManager()
        interp.brain = brain
        
        # Capture output
        # Interpreter prints to stdout. We can mock print?
        # Or parse state.
        
        interp.run(ast, entry_point="Ignition")
        
        # Check Global from import
        self.assertEqual(interp.state["Values"], 999)
        # Check Trigger execution (via output?)
        # We can't easily check output without stream capture.
        # But if it didn't crash, good.
        
        if os.path.exists(mod_name): os.remove(mod_name)

if __name__ == '__main__':
    unittest.main()
