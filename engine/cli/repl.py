"""
Interactive REPL — Chat with the Machine
========================================
A read-eval-print loop that maintains state and allows conversational interaction.
"""

import sys
from engine.parser.fuzzy_parser import FuzzyParser
from engine.runtime.interpreter import Interpreter

def start_repl():
    print("Assertion Language 1.0 (Conversational)")
    print("Type your thoughts. Say 'exit' or 'bye' to quit.")
    print("-----------------------------------------------")

    parser = FuzzyParser()
    interp = Interpreter()
    
    # Pre-teach some basic concepts if needed?
    # interp.brain.teach(...)

    while True:
        try:
            user_input = input(">> ").strip()
            if not user_input:
                continue
            
            if user_input.lower() in ["exit", "bye", "quit"]:
                print("Goodbye.")
                break

            # 1. Parse
            # We wrap the single line in a clean context?
            # FuzzyParser expects full text.
            # State is persistent in Interpreter, but Parser resets per call?
            # Actually FuzzyParser is stateless except for "last_var_mentioned".
            # We should keep the parser instance alive to track context (like "it").
            
            ast = parser.parse(user_input)
            
            # 2. Execute
            # Update state with any new globals
            for decl in ast.globals:
                interp.state[decl.name] = decl.value
                print(f"    [Memo] Remembered {decl.name}")

            # Register any new skills (Triggers named "To ...")
            # Logic in Interpreter.run normally does this, but we are running incrementally.
            # We should explicitly teach skills.
            for trig in ast.triggers:
                if trig.name != "Interactive":
                     interp.brain.teach(trig.name, trig.block)
            
            # Run "Interactive" trigger if present (Top-level commands)
            interactive = next((t for t in ast.triggers if t.name == "Interactive"), None)
            if interactive:
                interp.execute_block(interactive.block)
 

        except KeyboardInterrupt:
            print("\nExiting...")
            break
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    start_repl()
