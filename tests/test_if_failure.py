
import unittest
from engine.parser.fuzzy_parser import FuzzyParser
from engine.runtime.interpreter import Interpreter

class TestIfFailure(unittest.TestCase):
    def test_false_condition(self):
        text = """
        I want a number called "Score" starting at 0.
        When we start:
            If "Score" is 100:
                Say "This should not run".
            Say "Finished".
        """
        
        parser = FuzzyParser()
        ast = parser.parse(text)
        
        interp = Interpreter()
        interp.run(ast, entry_point="Ignition")
        
        # If the bug exists, "This should not run" will be in output
        self.assertNotIn("This should not run", interp.out_stream)
        self.assertIn("Finished", interp.out_stream)

if __name__ == '__main__':
    unittest.main()
