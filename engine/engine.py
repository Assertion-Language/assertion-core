"""
Assertion Engine — Bootstrap Orchestrator
Maximum Power • Compact • Modular • Compiler-Grade
"""

from pathlib import Path
from engine.lexer.tokenizer import tokenize
from engine.parser.parser import Parser
from engine.parser.semantic import SemanticAnalyzer
from engine.parser.fuzzy_parser import FuzzyParser
from engine.runtime.interpreter import Interpreter
from engine.crypto.manifest_crypto import verify_manifest_signature

class Engine:
    """

    The orchestration layer.
    This does NOT contain parsing/IR/runtime logic.
    It delegates to the modular subsystems.
    """

    def __init__(self):
        self.ast = None
        self.ir = None
        self.bytecode = None

    def load_manifest(self, path: str):
        text = Path(path).read_text(encoding='utf-8')

        if not verify_manifest_signature(text):
            raise ValueError("Manifest signature invalid or missing")

        # Conversational / Fuzzy Parser
        # We now use the FuzzyParser which handles sentence splitting and NLP
        print(f"[Engine] Loading conversational manifest: {path}")
        parser = FuzzyParser()
        self.ast = parser.parse(text)
        
        # Legacy Strict Mode
        # tokens = tokenize(text)
        # parser = Parser()
        # self.ast = parser.parse(tokens)

        # SemanticAnalyzer().analyze(self.ast)

    def compile(self):
        """
        Later phases will replace this with:
        - AST → SSA IR
        - Optimizations → optimized IR
        - IR → Bytecode or WASM
        """
        pass

    def run(self):
        """
        Execute the AST using the Interpreter.
        """
        if not self.ast:
            print("No AST loaded. Call load_manifest() first.")
            return

        interp = Interpreter()
        interp.run(self.ast)


def main():
    import sys
    if len(sys.argv) < 2:
        print("Usage: python -m engine <manifest_file>")
        return

    eng = Engine()
    eng.load_manifest(sys.argv[1])
    eng.compile()
    eng.run()


if __name__ == "__main__":
    main()
