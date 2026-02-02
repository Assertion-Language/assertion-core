
import unittest
from engine.parser.fuzzy_parser import FuzzyParser
from engine.runtime.interpreter import Interpreter

class TestAdvancedLogic(unittest.TestCase):
    def test_else_logic(self):
        text = """
        I want a number called "Score" starting at 50.
        
        When we start:
            If "Score" is 100:
                Say "High Score".
            Otherwise:
                Say "Low Score".
                Set "Score" to 0.
        """
        parser = FuzzyParser()
        ast = parser.parse(text)
        interp = Interpreter()
        interp.run(ast, entry_point="Ignition")
        
        self.assertIn("Low Score", interp.out_stream)
        self.assertEqual(interp.state["Score"], 0)

    def test_while_loop(self):
        text = """
        I want a number called "Count" starting at 0.
        
        When we start:
            While "Count" is 0:
                Say "Looping".
                Set "Count" to 1.
            Say "Done".
        """
        parser = FuzzyParser()
        ast = parser.parse(text)
        interp = Interpreter()
        interp.run(ast, entry_point="Ignition")
        
        self.assertIn("Looping", interp.out_stream)
        self.assertIn("Done", interp.out_stream)
        self.assertEqual(interp.state["Count"], 1)

    def test_nested_logic(self):
        text = """
        I want a number called "Flag" starting at 1.
        When we start:
            If "Flag" is 1:
                Say "Outer".
                If "Flag" is 1:
                    Say "Inner".
        """
        parser = FuzzyParser()
        ast = parser.parse(text)
        interp = Interpreter()
        interp.run(ast, entry_point="Ignition")
        
        self.assertIn("Outer", interp.out_stream)
        self.assertIn("Inner", interp.out_stream)

if __name__ == '__main__':
    unittest.main()
