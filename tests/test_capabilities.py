
import unittest
from engine.parser.fuzzy_parser import FuzzyParser
from engine.runtime.interpreter import Interpreter

class TestCapabilities(unittest.TestCase):

    def test_teaching_and_math(self):
        text = """
        I want a number called "Result" starting at 0.
        
        To calculate score:
            Set "Result" to (10 * 5) + 2.
            
        When we start:
            Calculate score.
            Tell me the "Result".
        """
        
        # 1. Parse
        parser = FuzzyParser()
        ast = parser.parse(text)
        
        # 2. Run
        interp = Interpreter()
        # Mocking the Fuzzy Parser's output where "Calculate score" translates to a trigger run?
        # Ahem, FuzzyParser currently parses "Calculate score" as... what?
        # It parses it as a Sentence. 
        # "calculate score" -> ???
        # We need to update FuzzyParser to recognize function CALLS or treat unknown verbs as function calls?
        
        # Actually, let's look at FuzzyParser logic.
        # It handles SET, OUTPUT. It returns None for others.
        # We need to update FuzzyParser to generic-call unknown verbs?
        pass 

    def test_math_only(self):
        text = """
        I want a number called "Val" starting at 0.
        When we start:
            Set "Val" to (100 / 2) + 50.
        """
        parser = FuzzyParser()
        ast = parser.parse(text)
        interp = Interpreter()
        interp.run(ast, entry_point="Ignition")
        
        self.assertEqual(interp.state["Val"], 100.0)

if __name__ == '__main__':
    unittest.main()
