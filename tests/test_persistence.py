
import unittest
import os
import json
from engine.parser.fuzzy_parser import FuzzyParser
from engine.runtime.interpreter import Interpreter

class TestPersistence(unittest.TestCase):
    def test_save_and_load(self):
        filename = "test_memory.json"
        if os.path.exists(filename): os.remove(filename)
        
        # 1. Save State
        text_save = f"""
        I want a number called "Score" starting at 500.
        When we start:
            Save state to "{filename}".
        """
        parser = FuzzyParser()
        ast = parser.parse(text_save)
        interp = Interpreter()
        interp.run(ast, entry_point="Ignition")
        
        self.assertTrue(os.path.exists(filename))
        with open(filename, 'r') as f:
            data = json.load(f)
            self.assertEqual(data["Score"], 500)
            
        # 2. Load State (New Interpreter)
        text_load = f"""
        When we start:
            Load state from "{filename}".
            Tell me the "Score".
        """
        parser2 = FuzzyParser()
        ast2 = parser2.parse(text_load)
        interp2 = Interpreter()
        interp2.run(ast2, entry_point="Ignition")
        
        self.assertEqual(interp2.state["Score"], 500)
        
        # Cleanup
        if os.path.exists(filename): os.remove(filename)

if __name__ == '__main__':
    unittest.main()
