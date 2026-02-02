
import unittest
from engine.parser.fuzzy_parser import FuzzyParser
from engine.runtime.interpreter import Interpreter

class TestLists(unittest.TestCase):
    def test_list_creation_and_append(self):
        text = """
        I want a number called "Score" starting at 0.
        
        When we start:
            My list is "Apple", "Banana".
            Add "Cherry" to "My list".
            Add "Score" to "My list".
        """
        parser = FuzzyParser()
        ast = parser.parse(text)
        interp = Interpreter()
        interp.run(ast, entry_point="Ignition")
        
        lst = interp.state["My list"]
        self.assertIsInstance(lst, list)
        self.assertEqual(len(lst), 4)
        self.assertEqual(lst[0], "Apple")
        self.assertEqual(lst[2], "Cherry")
        self.assertEqual(lst[3], 0) # Variable resolution? 
        # "Score" in quotes -> String "Score" or Value 0?
        # Interpreter evaluate: if Literal string matches var, use var logic?
        # Let's see. 
        # Logic in Interpreter.evaluate:
        # if isinstance(node, Literal) and isinstance(node.value, str) and node.value in self.state: return state[value]
        # So "Score" -> 0.
        
    def test_list_math(self):
        # Testing if list creation survives math check
        text = """
        Values is 10, 20.
        """
        parser = FuzzyParser()
        ast = parser.parse(text)
        interp = Interpreter()
        interp.run(ast, entry_point="Interactive") 
        # Top level -> Interactive
        
        self.assertEqual(interp.state["Values"], [10, 20])

if __name__ == '__main__':
    unittest.main()
