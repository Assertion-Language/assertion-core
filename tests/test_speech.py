
import unittest
import textwrap
from engine.lexer.tokenizer import tokenize
from engine.parser.parser import Parser
from engine.runtime.interpreter import Interpreter

class TestSpeechSyntax(unittest.TestCase):

    def test_synonyms_and_noise(self):
        code = textwrap.dedent("""
            WHEN Ignition:
                PLEASE MAKE "Score" 100
                LET "Bonus" 50
                SAY "Score"
                PLEASE SHOUT "Bonus"
        """)
        
        tokens = tokenize(code)
        print("\nTOKENS:", tokens)
        
        parser = Parser()
        ast = parser.parse(tokens)
        print("\nAST:", ast)
        
        interp = Interpreter()
        if ast.triggers:
            print("\nBLOCK:", ast.triggers[0].block)
            interp.execute_block(ast.triggers[0].block)
        
        print("\nSTATE:", interp.state)
        print("OUT:", interp.out_stream)

        self.assertEqual(interp.state.get("Score"), 100)
        self.assertEqual(interp.state.get("Bonus"), 50)
        self.assertEqual(interp.out_stream, ["100", "50"])

    def test_flexible_grammar_no_to(self):
        code = textwrap.dedent("""
            WHEN Ignition:
                SET "x" 10
        """)
        tokens = tokenize(code)
        parser = Parser()
        ast = parser.parse(tokens)
        
        interp = Interpreter()
        interp.execute_block(ast.triggers[0].block)
        
        self.assertEqual(interp.state.get("x"), 10)

    def test_context_variables(self):
        code = textwrap.dedent("""
            THERE IS A Number CALLED "GlobalVal" WITH VALUE 99
            
            WHEN Ignition:
                OUTPUT "GlobalVal"
        """)
        tokens = tokenize(code)
        # Debug printing
        print("Context Tokens:", tokens)
        
        parser = Parser()
        ast = parser.parse(tokens)
        
        interp = Interpreter()
        interp.run(ast)
        
        self.assertEqual(interp.state["GlobalVal"], 99)
        self.assertEqual(interp.out_stream, ["99"])

if __name__ == '__main__':
    unittest.main()
