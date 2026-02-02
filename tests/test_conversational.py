
import unittest
from engine.parser.fuzzy_parser import FuzzyParser
from engine.runtime.interpreter import Interpreter

class TestConversational(unittest.TestCase):

    def test_full_conversation(self):
        text = """
        I want a number called "Score" starting at 0.
        There is a string named "Status" with value "Ready".

        When we start the engine:
            Make the "Score" 100.
            Then add 50 to it.
            Set "Status" to "Winning".
            Tell me the "Score".
            If "Score" is 150:
                Say "We won!".
        """
        
        # 1. Parse
        parser = FuzzyParser()
        ast = parser.parse(text)
        
        # Verify AST structure references "Ignition" equivalent trigger
        self.assertEqual(len(ast.globals), 2)
        self.assertEqual(len(ast.triggers), 1)
        self.assertEqual(ast.triggers[0].name, "Ignition")
        
        # 2. Run
        interp = Interpreter()
        interp.run(ast, entry_point="Ignition")
        
        # 3. Verify State
        self.assertEqual(interp.state["Score"], 150)
        self.assertEqual(interp.state["Status"], "Winning")
        
        # 4. Verify Output
        self.assertIn("150", interp.out_stream)
        self.assertIn("We won", interp.out_stream)

    def test_implicit_set(self):
        text = """
        I want a number called "Velocity" starting at 0.
        When we start:
            "Velocity" is 50.
            Add 10 to it.
        """
        parser = FuzzyParser()
        ast = parser.parse(text)
        
        interp = Interpreter()
        interp.run(ast, entry_point="Ignition")
        
        self.assertEqual(interp.state["Velocity"], 60)

if __name__ == '__main__':
    unittest.main()
