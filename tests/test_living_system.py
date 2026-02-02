
import unittest
import asyncio
import os
from engine.parser.fuzzy_parser import FuzzyParser
from engine.runtime.interpreter import Interpreter

class TestLivingSystem(unittest.TestCase):
    def test_when_trigger(self):
        # Async test runner helper
        async def run_test():
            text = """
            I want a number called "Timer" starting at 0.
            When "Timer" is 5:
                Say "Boom".
                Set "Timer" to 10.
            
            When we start:
                Set "Timer" to 5.
            """
            parser = FuzzyParser()
            ast = parser.parse(text)
            interp = Interpreter()
            
            # We run for a short time to allow tick event
            # run() is async now.
            # But run() has an infinite loop if listeners exist.
            # We need to run it as a task and cancel it?
            # Or reliance on "tick" implies we can just call tick() manually for testing?
            # interpreter.listeners should be populated.
            
            # Manual execution for test stability
            # 1. Parse & Init
            for trig in ast.triggers:
                if trig.name != "Ignition" and trig.name != "Interactive": 
                     interp.brain.teach(trig.name, trig.block)
            for decl in ast.globals:
                interp.state[decl.name] = decl.value
                
            # Execute Interactive (Registers Listeners)
            interactive = next((t for t in ast.triggers if t.name == "Interactive"), None)
            if interactive:
                await interp.execute_block(interactive.block)

            # Execute Ignition
            trigger = next((t for t in ast.triggers if t.name == "Ignition"), None)
            
            # 2. Register Listeners (from WHERE? Parser doesn't extract WhenStmt to top level?)
            # Wait, WhenStmt is valid inside "Ignition" or top level.
            # If in Ignition: executed once, registers listener.
            # Logic: When "Timer" is 5: -> This is a STATEMENT that executes "Register Listener".
            # So running Ignition registers it? 
            # Check parser: WhenStmt appended to current block.
            # So yes, it's a statement.
            
            # 3. Run Ignition
            await interp.execute_block(trigger.block)
            
            # Verify listener registered
            self.assertEqual(len(interp.listeners), 1)
            
            # 4. State is 5. Tick should trigger logic.
            await interp.tick()
            
            # Logic: Say Boom, Set Timer to 10.
            self.assertEqual(interp.state["Timer"], 10)
            self.assertIn("Boom", interp.out_stream)
            
        asyncio.run(run_test())

    def test_async_loop(self):
        # Verify While loop yields
        async def run_test():
            text = """
            I want a number called "Count" starting at 0.
            When we start:
                While "Count" is 0:
                    Set "Count" to 1.
            """
            parser = FuzzyParser()
            ast = parser.parse(text)
            interp = Interpreter()
            await interp.run(ast, entry_point="Ignition")
            self.assertEqual(interp.state["Count"], 1)

        asyncio.run(run_test())

if __name__ == '__main__':
    unittest.main()
