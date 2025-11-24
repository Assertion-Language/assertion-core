import re
import sys
import time

class AssertionEngine:
    def _init_(self):
        self.state = {}
        self.constraints = []
        self.triggers = {}

    def load_manifest(self, file_path):
        """Reads the .asrt file and parses the intent."""
        print(f"[*] READING MANIFEST: {file_path}...")
        with open(file_path, 'r') as f:
            content = f.read()
        
        # Parse CONTEXT (Variables)
        context_matches = re.findall(r"THERE IS A (.?) called \"(.?)\"(?: with value \"(.*?)\")?", content)
        for type_, name, value in context_matches:
            self.state[name] = {"type": type_.strip(), "value": value if value else None}
            print(f"    + CREATED: {name} ({type_.strip()})")

        # Parse CONSTRAINTS (The Laws)
        constraint_section = re.search(r"CONSTRAINT:(.*?)(?:WHEN|THERE|$)", content, re.DOTALL)
        if constraint_section:
            rules = constraint_section.group(1).strip().split('\n')
            for rule in rules:
                clean_rule = rule.strip().replace("- ", "")
                if clean_rule:
                    self.constraints.append(clean_rule)
                    print(f"    + LAW ENACTED: {clean_rule}")

        # Parse TRIGGERS (The Logic)
        # This is a simplified parser for the prototype
        when_blocks = re.split(r"WHEN ", content)[1:]
        for block in when_blocks:
            lines = block.strip().split('\n')
            trigger_name = lines[0].replace(":", "").strip()
            actions = [line.strip().replace("- ", "") for line in lines[1:] if line.strip().startswith("-")]
            self.triggers[trigger_name] = actions
            print(f"    + LOGIC DEFINED: When '{trigger_name}' happens -> {len(actions)} actions ready.")

    def check_constraints(self):
        """The Pre-Cognitive Engine: Checks if reality allows the action."""
        print("\n[*] RUNNING PRE-COGNITIVE SIMULATION...")
        time.sleep(0.5) # Artificial processing time
        
        for rule in self.constraints:
            # Simple keyword matching for this prototype
            if "locked" in rule and self.state.get("The Button", {}).get("value") == "LOCKED":
                print(f"    ! VIOLATION DETECTED: {rule}")
                return False
            # Add more complex logic checks here
            
        print("    > SIMULATION PASSED. REALITY IS STABLE.")
        return True

    def execute(self, trigger_event):
        """Executes the intent if constraints pass."""
        print(f"\n[*] TRIGGERING EVENT: {trigger_event}")
        
        if trigger_event not in self.triggers:
            print(f"    ! UNKNOWN EVENT: {trigger_event}")
            return

        if not self.check_constraints():
            print("    ! EXECUTION HALTED BY CONSTRAINT.")
            return

        # Execute Actions
        actions = self.triggers[trigger_event]
        for action in actions:
            print(f"    > EXECUTING: {action}")
            # Here we map text to actual Python functions
            if "OUTPUT" in action:
                msg = action.split("OUTPUT")[1].strip().replace('"', '')
                print(f"      [DISPLAY]: {msg}")
            elif "GENERATE Light" in action:
                 print("      [SYSTEM]: Rendering Lighting Effects...")
                 self.state["The Void"] = {"type": "Space", "value": "ILLUMINATED"}

        print("[*] EVENT COMPLETE.\n")

if _name_ == "_main_":
    # Initialize the Engine
    engine = AssertionEngine()
    
    # Load the Genesis File (Assuming it exists in the same folder)
    try:
        engine.load_manifest("genesis.asrt")
        
        # Simulate the User Action
        engine.execute("The Architect speaks")
        
    except FileNotFoundError:
        print("ERROR: genesis.asrt not found. Please create the file first."
