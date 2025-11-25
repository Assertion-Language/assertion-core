"""
Assertion Engine — Bootstrap Orchestrator
Maximum Power • Compact • Modular • Compiler-Grade
"""

from pathlib import Path
from engine.lexer.tokenizer import tokenize
from engine.parser.parser import Parser
from engine.parser.semantic import SemanticAnalyzer
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

        tokens = tokenize(text)
        parser = Parser()
        self.ast = parser.parse(tokens)

        SemanticAnalyzer().analyze(self.ast)

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
        Later phases:
        - Bytecode execution
        - JIT execution
        - Fiber scheduler
        - Distributed mode
        """
        pass


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
