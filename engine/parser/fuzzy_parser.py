
"""
Fuzzy Parser — The Conversational Engine
========================================
Parses natural language sentences into AST nodes using heuristic patterns.
Now with BLOCK support (Indentation).
"""

import re
from typing import List, Optional, Tuple
from engine.parser.ast_nodes import (
    Program, Trigger, Stmt,
    SetStmt, OutputStmt, RepeatStmt, IfStmt, WhileStmt,
    SetStmt, OutputStmt, RepeatStmt, IfStmt, WhileStmt,
    SetStmt, OutputStmt, RepeatStmt, IfStmt, WhileStmt,
    CreateFileStmt, WriteFileStmt, CallStmt, SaveStmt, LoadStmt,
    PythonStmt, ShellStmt, ImportStmt, WhenStmt, StartServerStmt,
    VarDecl, Literal, Identifier
)

class FuzzyParser:
    def __init__(self):
        self.code = ""
        self.last_var_mentioned = None 
        # Stack of (indent_level, block_list)
        self.block_stack = [] 

    def _clean_str(self, s: str) -> str:
        # Removes trailing punctuation: . ! ?
        if not s: return ""
        return s.rstrip(".!?")


    def parse(self, text: str) -> Program:
        self.code = text
        prog = Program(line=1)
        
        # Split into lines
        lines = text.split('\n')
        
        # Setup stacks
        # Triggers are top-level constructs.
        # But we also want to support top-level statements (REPL style).
        # Should we assume everything lives in a "Main" trigger?
        # Or parse triggers separately?
        
        # Current logic:
        # A line can accept a new Trigger OR be a statement inside a Trigger.
        # Top-level statements go into "Interactive" trigger if no other trigger active?
        
        current_trigger: Optional[Trigger] = None
        
        # We process line by line
        for i, line_raw in enumerate(lines):
            line_stripped = line_raw.lstrip()
            if not line_stripped or line_stripped.startswith("#"):
                continue
            
            indent = len(line_raw) - len(line_stripped)
            sentence = line_stripped.strip()
            
            # 1. Detect Trigger Definition (Must be top level? indent 0 preferred)
            # "When we start:"
            if re.search(r'\b(when|if)\b.*\b(start|ignition|begin)\b', sentence, re.IGNORECASE):
                current_trigger = Trigger(name="Ignition", line=i+1, block=[])
                prog.triggers.append(current_trigger)
                # Reset stack to [ (indent+1?, block) ]?
                # Actually, standard python indentation rules:
                # The next line determines the indent.
                # We set the "current block" to this trigger's block.
                # We need to track that we are IN a trigger.
                self.block_stack = [(indent, current_trigger.block)]
                continue

            # "To greet:"
            func_match = re.match(r'^\s*To\s+(.+):', sentence, re.IGNORECASE)
            if func_match:
                func_name = func_match.group(1).strip()
                current_trigger = Trigger(name=func_name, line=i+1, block=[])
                prog.triggers.append(current_trigger)
                self.block_stack = [(indent, current_trigger.block)]
                continue

            # Check for Global Decl (Always valid if matches syntax)
            decl = self.parse_global_decl(sentence, i+1)
            if decl:
                prog.globals.append(decl)
                current_trigger = None # Globals end a trigger block? 
                # Or just exist validly. If we are in a trigger, this breaks it?
                # Assuming indentation handled by stack.
                # If indentation is 0, we can assume trigger ended?
                # Let's just append global.
                # Re: "Values is 999" -> handled as SetStmt in body if we don't catch it here.
                continue

            # If we are NOT in a trigger, and handle top-level statement?
            if not current_trigger:

                # REPL Mode / Top Level
                # Create default Interactive trigger
                # See if one exists
                current_trigger = next((t for t in prog.triggers if t.name == "Interactive"), None)
                if not current_trigger:
                     current_trigger = Trigger(name="Interactive", line=0, block=[])
                     prog.triggers.append(current_trigger)
                # Initialize stack
                self.block_stack = [(indent, current_trigger.block)]
            
            # --------------------------------------------------------
            # Handle Blocks (Indentation)
            # --------------------------------------------------------
            # Determine where this line belongs in the stack
            # Stack: [(0, root_block), (4, if_block), (8, while_block)]
            # If current indent is 4, we match index 1. Pop index 2.
            
            # Find the closest matching indent in stack
            # Rules:
            # 1. New indent > Top indent: Only allowed if previous line opened a block?
            #    We can be loose. If it's deeper, it's a new block? 
            #    But we don't know WHERE to attach it unless the previous stmt has a body.
            #    Actually, we should have pushed the new body onto the stack when parsing the Opener.
            
            # Let's check if we popped back
            while len(self.block_stack) > 1 and indent <= self.block_stack[-1][0]:
                 # If indent < top, POP.
                 # If indent == top, we are in same block. 
                 # But if we are == top, we don't pop, we just append.
                 if indent < self.block_stack[-1][0]:
                     self.block_stack.pop()
                 else:
                     break
            
            # Now self.block_stack[-1] is the target block
            current_block_req_indent, current_block = self.block_stack[-1]
            
            # --------------------------------------------------------
            # Parse Statement
            # --------------------------------------------------------
            
            # Check for BLOCK OPENERS (If, While, Else)
            
            # IF
            if_match = re.match(r'^If\s+(.+?):', sentence, re.IGNORECASE)
            if if_match:
                cond_str = if_match.group(1)
                # Parse condition... (simplified for now: Var is Val)
                # "Score" is 100
                # Fuzzy parse the condition as a "Set" statement to extract left/right?
                # Or custom parser?
                
                # Logic: create IfStmt, append to current_block, PUSH body to stack
                # We need to find target Block
                
                cond_stmt = self.parse_sentence(cond_str, i+1) # Should look like a SET or implicit comparison
                
                # If parsed as SetStmt, use it as condition logic
                # IfStmt(var, expected)
                var = "Unknown"
                val = 0
                if isinstance(cond_stmt, SetStmt):
                     var = cond_stmt.target
                     # If it was "Score is 100", op is None, left is literal
                     val = cond_stmt.left
                
                if_node = IfStmt(line=i+1, var=var, expected=val, body=[], else_body=[])
                current_block.append(if_node)
                
                # Expect next line to be indented
                # We push (indent + ?, if_node.body)
                # We set a placeholder indent that will be fixed by next line? 
                # Or assumes strict indentation (e.g. +4)
                # Let's say we expect "indent > current". We'll update the stack head's indent on next line?
                # Standard approach: Push with (indent + 1) requirement?
                # Or use -1 as "Next line defines indent"
                self.block_stack.append((indent + 1, if_node.body))
                continue
            
            # WHILE
            while_match = re.match(r'^While\s+(.+?):', sentence, re.IGNORECASE)
            if while_match:
                cond_str = while_match.group(1)
                cond_stmt = self.parse_sentence(cond_str, i+1)
                var = "Unknown"
                val = 0
                if isinstance(cond_stmt, SetStmt):
                     var = cond_stmt.target
                     val = cond_stmt.left
                
                while_node = WhileStmt(line=i+1, condition_var=var, condition_val=val, body=[])
                current_block.append(while_node)
                self.block_stack.append((indent + 1, while_node.body))
                continue
                
                self.block_stack.append((indent + 1, while_node.body))
                continue
            
            # PYTHON BLOCK
            # "Run python:" or "Python:"
            python_match = re.match(r'^(?:Run\s+)?Python:', sentence, re.IGNORECASE)
            if python_match:
                py_node = PythonStmt(line=i+1, code="")
                current_block.append(py_node)
                # SPECIAL: Python blocks are RAW text.
                # We assume current_block[-1] IS the python node.
                # But our stack usually stores LISTS.
                # Logic: We push the Node itself to stack?
                # And the loop check handles it.
                self.block_stack.append((indent + 1, py_node))
                continue

                self.block_stack.append((indent + 1, py_node))
                continue

            # WHEN TRIGGER
            # When "Timer" is 5:
            # When file "x" changes:
            when_match = re.match(r'^When\s+(.+?):', sentence, re.IGNORECASE)
            if when_match:
                clause = when_match.group(1).strip()
                # Parse clause
                kind = "VAR"
                target = ""
                val = 0
                
                # Check for FILE CHANGES
                file_match = re.search(r'file\s+["\']?(.+?)["\']?\s+changes', clause, re.IGNORECASE)
                if file_match:
                    kind = "FILE"
                    target = file_match.group(1)
                
                # Check for REQUEST COMES
                elif "request comes" in clause.lower():
                    kind = "REQUEST"
                    target = "server"
                
                # Default: VAR COMPARE
                else:
                    # Parse as stmt to extract?
                    # "Timer is 5"
                    stmt = self.parse_sentence(clause, i+1)
                    if isinstance(stmt, SetStmt):
                        target = stmt.target
                        val = stmt.left
                
                when_node = WhenStmt(line=i+1, kind=kind, target=target, val=val, body=[])
                current_block.append(when_node)
                self.block_stack.append((indent + 1, when_node.body))
                continue

            # ELSE / OTHERWISE
            if re.match(r'^(Else|Otherwise):', sentence, re.IGNORECASE):
                # Attach to PREVIOUS statement in current block
                if current_block and isinstance(current_block[-1], IfStmt):
                    if_node = current_block[-1]
                    self.block_stack.append((indent + 1, if_node.else_body))
                    continue
                else:
                    pass

            # NORMAL STATEMENT (or RAW LINE)
            if isinstance(current_block, PythonStmt):
                 # RAW MODE
                 # Just append line to code
                 # Reconstruct newline
                 current_block.code += line_stripped + "\n"
            else:
                 stmt = self.parse_sentence(sentence, i+1)
                 if stmt:
                    current_block.append(stmt)

        return prog

    def parse_global_decl(self, sentence: str, line: int) -> Optional[VarDecl]:
        name_match = re.search(r'\b(called|named)\s+["\']?([\w\s]+)["\']?', sentence, re.IGNORECASE)
        if not name_match: return None
        name = name_match.group(2).strip()
        self.last_var_mentioned = name
        type_str = "Number" if "number" in sentence.lower() else "String"
        val = 0
        val_match = re.search(r'(starting at|with value|is)\s+(-?\d+(\.\d+)?)', sentence, re.IGNORECASE)
        if val_match:
            val = float(val_match.group(2)) if '.' in val_match.group(2) else int(val_match.group(2))
        else:
            str_match = re.search(r'(starting at|with value|is)\s+["\'](.*?)["\']', sentence, re.IGNORECASE)
            if str_match: val = str_match.group(2)
        return VarDecl(line=line, name=name, type=type_str, value=val)

    def parse_sentence(self, sentence: str, line: int) -> Optional[Stmt]:
        # Reuse existing Logic (simplified copy/paste from previous step, assuming imports correct)
        
        # 1. SET / UPDATE
        set_verb = re.search(r'\b(make|set|let|change|update)\b\s+(?:the\s+)?["\']?([\w\s]+)["\']?\s+(?:to\s+|be\s+)?(.+)', sentence, re.IGNORECASE)
        if set_verb:
            target = set_verb.group(2).strip()
            if target.lower() == "it": target = self.last_var_mentioned
            val_str = set_verb.group(3).strip()
            if target and target.lower() != "it": self.last_var_mentioned = target
            return self._create_set(line, target, val_str)

        # 2. STATE (Passive Set) - "Score is 10"
        if re.match(r'^\s*(when|if|while)\b', sentence, re.IGNORECASE): return None # Guard
        
        is_verb = re.search(r'^["\']?([\w\s]+)["\']?\s+(?:is|equals|should be|is now)\s+(.+)', sentence, re.IGNORECASE)
        if is_verb:
            target = is_verb.group(1).strip()
            val_str = is_verb.group(2).strip()
            if target.lower() == "it": target = self.last_var_mentioned
            elif target: self.last_var_mentioned = target
            return self._create_set(line, target, val_str)

        # 3. MATH
        math_verb = re.search(r'\b(add|subtract|multiply|divide)\b\s+(.+)\s+(?:to|from|by)\s+["\']?([\w\s]+|it)["\']?', sentence, re.IGNORECASE)
        if math_verb:
            op_map = {"add": "PLUS", "subtract": "MINUS", "multiply": "TIMES", "divide": "DIVIDE"}
            op = op_map.get(math_verb.group(1).lower())
            val_str = math_verb.group(2).strip()
            target_raw = math_verb.group(3).strip()
            target = target_raw
            if target.lower() == "it": target = self.last_var_mentioned
            else: self.last_var_mentioned = target
            return SetStmt(line=line, target=target, op=op, left=Identifier(line, target), right=self._parse_val(line, val_str))

        # 4. OUTPUT
        out_verb = re.search(r'\b(say|shout|whisper|print|output|display|tell me|show)(?: about)?\s+(.+)', sentence, re.IGNORECASE)
        if out_verb:
            content = out_verb.group(2).strip()
            # Clean punctuation FIRST
            content = self._clean_str(content)
            
            if content.lower().startswith("the "): content = content[4:]
            content = content.replace("'", "").replace('"', "")
            if content.lower() == "it": content = self.last_var_mentioned
            return OutputStmt(line=line, value=Literal(line, content))



        # 5. PERSISTENCE
        save_match = re.search(r'\bsave\s+state\s+to\s+["\']?([\w\./]+)["\']?', sentence, re.IGNORECASE)
        if save_match:
            return SaveStmt(line=line, filename=save_match.group(1))
            
        load_match = re.search(r'\bload\s+state\s+from\s+["\']?([\w\./]+)["\']?', sentence, re.IGNORECASE)
        if load_match:
            return LoadStmt(line=line, filename=load_match.group(1))

        # 6. FFI (Shell / Import)
        # "Run shell 'ls'"
        shell_match = re.search(r'\brun\s+shell\s+["\']?(.+?)["\']?[\.!?]?$', sentence, re.IGNORECASE)
        if shell_match:
             return ShellStmt(line=line, command=shell_match.group(1))
             
        import_match = re.search(r'\bimport\s+["\']?([\w\./]+)["\']?[\.!?]?$', sentence, re.IGNORECASE)
        if import_match:
             return ImportStmt(line=line, module_name=import_match.group(1))

        if import_match:
             return ImportStmt(line=line, module_name=import_match.group(1))

        # 7. NETWORKING
        start_server = re.search(r'start\s+server\s+on\s+port\s+(\d+)', sentence, re.IGNORECASE)
        if start_server:
            return StartServerStmt(line=line, port=int(start_server.group(1)))

        # 8. CALL
        call_match = re.search(r'^\s*([^\s].+)', sentence) # Relaxed to catch anything not matched
        if call_match:
             # Clean input
             raw = self._clean_str(call_match.group(1).strip())
             return CallStmt(line=line, func_name=raw)
        return None

    def _create_set(self, line, target, val_str):
        val = self._parse_val(line, val_str)
        return SetStmt(line=line, target=target, op=None, left=val, right=None)

    def _parse_val(self, line, val_str):
        # 1. Cleaning
        val_str = self._clean_str(val_str.strip())
        
        # 2. Check for List: "A, B, C"
        if ',' in val_str and not '(' in val_str: # Avoid confusing with function args if any
            # It's a list?
            items = [s.strip() for s in val_str.split(',')]
            # Parse each item
            parsed_items = []
            for item in items:
                # Recursively parse val? Or just strip quotes?
                # Simple list of strings/numbers
                item = item.replace("'", "").replace('"', "")
                try: 
                    if '.' in item: parsed_items.append(float(item))
                    else: parsed_items.append(int(item))
                except: parsed_items.append(item)
            return Literal(line, parsed_items)

        # 3. Math
        if any(c in val_str for c in "+-*/()"): return Literal(line, val_str) # Math
        
        # 4. Number
        try:
            if '.' in val_str: return Literal(line, float(val_str))
            return Literal(line, int(val_str))
        except ValueError:
            pass
        
        # 5. String
        val_str = val_str.replace("'", "").replace('"', "")
        return Literal(line, val_str)
