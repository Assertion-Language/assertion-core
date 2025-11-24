import re
import sys
import time

class AssertionEngine:
    def _init_(self):
        self.state = {}
        self.constraints = []
        self.triggers = {}

    def load_manifest(self, file_path):
        print(f"[*] READING MANIFEST: {file_path}...")
        with open(file_path, 'r') as f:
            content = f.read()
        
        # 1. PARSE VARIABLES (Now detects Numbers)
        # Regex looks for: THERE IS A [Type] called "[Name]" with value [Value]
        context_matches = re.findall(r"THERE IS A (.?) called \"(.?)\"(?: with value (.*?))?[\.\n]", content)
        for type_, name, value in context_matches:
            clean_value = value.strip()
            # Auto-convert numbers
            try:
                if "." in clean_value:
                    final_value = float(clean_value)
                else:
                    final_value = int(clean_value)
            except:
                final_value = clean_value.replace('"', '') # It's a string
            
            self.state[name] = {"type": type_.strip(), "value": final_value}
            print(f"    + CREATED: {name} = {final_value}")

        # 2. PARSE CONSTRAINTS
        constraint_section = re.search(r"CONSTRAINT:(.*?)(?:WHEN|THERE|$)", content, re.DOTALL)
        if constraint_section:
            rules = constraint_section.group(1).strip().split('\n')
            for rule in rules:
                clean_rule = rule.strip().replace("- ", "")
                if clean_rule:
                    self.constraints.append(clean_rule)

        # 3. PARSE TRIGGERS
        when_blocks = re.split(r"WHEN ", content)[1:]
        for block in when_blocks:
            lines = block.strip().split('\n')
            trigger_name = lines[0].replace(":", "").strip()
            actions = [line.strip().replace("- ", "") for line in lines[1:] if line.strip().startswith("-")]
            self.triggers[trigger_name] = actions

    def check_constraints(self):
        """The Pre-Cognitive Engine: Math Safety."""
        for rule in self.constraints:
            # Example Logic: "Cost" cannot be greater than "Revenue"
            if "cannot be greater than" in rule:
                parts = rule.split(" cannot be greater than ")
                var1 = parts[0].replace('"', '').strip()
                var2 = parts[1].replace('"', '').strip()
                
                val1 = self.state.get(var1, {}).get("value", 0)
                val2 = self.state.get(var2, {}).get("value", 0)
                
                if val1 > val2:
                    print(f"    ! VIOLATION: {var1} ({val1}) > {var2} ({val2})")
                    return False
        return True

    def perform_math(self, action):
        """Parses natural language math into Python math."""
        # Pattern: SET "Target" to "A" OP "B"
        match = re.search(r"SET \"(.?)\" to \"(.?)\" (PLUS|MINUS|TIMES|DIVIDED BY) \"(.*?)\"", action)
        if match:
            target, var_a, op, var_b = match.groups()
            val_a = self.state.get(var_a, {}).get("value", 0)
            val_b = self.state.get(var_b, {}).get("value", 0)
            
            result = 0
            if op == "PLUS": result = val_a + val_b
            if op == "MINUS": result = val_a - val_b
            if op == "TIMES": result = val_a * val_b
            if op == "DIVIDED BY": 
                if val_b == 0:
                    print("    ! FATAL ERROR: Division by Zero detected.")
                    return
                result = val_a / val_b
            
            self.state[target]["value"] = result
            print(f"      [CALCULATION]: {var_a} {op} {var_b} -> {result}")
            return True
        return False

    def execute(self, trigger_event):
        print(f"\n[*] TRIGGERING EVENT: {trigger_event}")
        if not self.check_constraints():
            print("    ! EXECUTION BLOCKED BY CONSTRAINT.")
            return

        actions = self.triggers.get(trigger_event, [])
        for action in actions:
            # Check if it's Math
            if "SET" in action:
                self.perform_math(action)
            # Check if it's Output
            elif "OUTPUT" in action:
                target = action.replace("OUTPUT", "").strip().replace('"', '')
                # Is it a variable or string?
                if target in self.state:
                    print(f"      [DISPLAY]: {self.state[target]['value']}")
                else:
                    print(f"      [DISPLAY]: {target}")

if _name_ == "_main_":
    engine = AssertionEngine()
    # Change this to "calculation.asrt" to test the math
    try:
        engine.load_manifest("calculation.asrt")
        engine.execute("Audit")
    except FileNotFoundError:
        print("ERROR: Manifest file not found.")
