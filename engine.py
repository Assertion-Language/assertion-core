import re
import sys
import time
import os

class AssertionEngine:
    def _init_(self):
        self.state = {}
        self.constraints = []
        self.triggers = {}
        self.MAX_LOOP_SAFETY = 100

    def load_manifest(self, file_path):
        print(f"[*] READING MANIFEST: {file_path}...")
        try:
            with open(file_path, 'r') as f:
                content = f.read()
        except FileNotFoundError:
            print(f"ERROR: Could not find {file_path}")
            return

        # 1. PARSE VARIABLES
        context_matches = re.findall(r"THERE IS A (.?) called \"(.?)\"(?: with value (.*?))?[\.\n]", content)
        for type_, name, value in context_matches:
            val = value.strip().replace('"', '')
            if val.replace('.', '', 1).isdigit():
                val = float(val) if '.' in val else int(val)
            self.state[name] = {"type": type_.strip(), "value": val}

        # 2. PARSE CONSTRAINTS
        constraint_section = re.search(r"CONSTRAINT:(.*?)(?:WHEN|THERE|$)", content, re.DOTALL)
        if constraint_section:
            rules = constraint_section.group(1).strip().split('\n')
            for rule in rules:
                if rule.strip().replace("- ", ""):
                    self.constraints.append(rule.strip().replace("- ", ""))

        # 3. PARSE TRIGGERS
        raw_blocks = re.split(r"WHEN ", content)[1:]
        for block in raw_blocks:
            lines = block.split('\n')
            trigger_name = lines[0].replace(":", "").strip().replace('"', '')
            action_lines = [line for line in lines[1:] if line.strip()]
            self.triggers[trigger_name] = action_lines

    def check_constraints(self):
        for rule in self.constraints:
            if "cannot be greater than" in rule:
                parts = rule.split(" cannot be greater than ")
                var_name = parts[0].replace('"', '').strip()
                limit = float(parts[1].strip())
                current_val = self.state.get(var_name, {}).get("value", 0)
                if current_val > limit:
                    print(f"\n[!] CONSTRAINT VIOLATION: {var_name} ({current_val}) > {limit}")
                    return False
        return True

    def get_value(self, var_or_val):
        clean = var_or_val.replace('"', '').strip()
        if clean in self.state:
            return self.state[clean]['value']
        try:
            if "." in clean: return float(clean)
            return int(clean)
        except:
            return clean

    def execute_block(self, lines, indent_level=0):
        i = 0
        while i < len(lines):
            line = lines[i]
            stripped = line.strip().replace("- ", "")
            current_indent = len(line) - len(line.lstrip())
            
            if current_indent < indent_level: 
                i += 1
                continue

            # --- FILE I/O BLOCK ---
            if stripped.startswith("CREATE FILE"):
                filename = stripped.replace("CREATE FILE", "").strip().replace('"', '')
                with open(filename, 'w') as f: f.write("")
                print(f"    [DISK] Created file: {filename}")

            elif "TO FILE" in stripped:
                # WRITE "Text" TO FILE "file.txt"
                # APPEND "Text" TO FILE "file.txt"
                mode = 'a' if stripped.startswith("APPEND") else 'w'
                parts = stripped.split(" TO FILE ")
                content_raw = parts[0].replace("WRITE", "").replace("APPEND", "").strip()
                filename = parts[1].strip().replace('"', '')
                
                content = str(self.get_value(content_raw))
                with open(filename, mode) as f:
                    if mode == 'a': f.write(content + "\n")
                    else: f.write(content)
                print(f"    [DISK] Wrote to {filename}")

            elif stripped.startswith("READ FILE"):
                # READ FILE "file.txt" INTO "Var"
                match = re.search(r"READ FILE \"(.?)\" INTO \"(.?)\"", stripped)
                if match:
                    filename, var_target = match.groups()
                    if os.path.exists(filename):
                        with open(filename, 'r') as f:
                            self.state[var_target]["value"] = f.read().strip()
                        print(f"    [DISK] Read from {filename}")
                    else:
                        print(f"    [!] ERROR: File {filename} not found.")

            # --- EXISTING LOGIC ---
            elif stripped.startswith("ASK"):
                match = re.search(r"ASK \"(.?)\" and STORE in \"(.?)\"", stripped)
                if match:
                    question, var_target = match.groups()
                    user_input = input(f"    [INPUT] {question} ")
                    self.state[var_target]["value"] = user_input

            elif stripped.startswith("OUTPUT"):
                target = stripped.replace("OUTPUT", "").strip()
                print(f"    > {self.get_value(target)}")

            elif stripped.startswith("SET"):
                match = re.search(r"SET \"(.?)\" to \"(.?)\" (PLUS|MINUS|TIMES) (.*?)$", stripped)
                if match:
                    target, v1, op, v2 = match.groups()
                    val1 = self.get_value(v1)
                    val2 = self.get_value(v2)
                    if op == "PLUS": result = val1 + val2
                    elif op == "MINUS": result = val1 - val2
                    elif op == "TIMES": result = val1 * val2
                    self.state[target]["value"] = result
                    if not self.check_constraints(): return False

            elif stripped.startswith("IF"):
                match = re.search(r"IF \"(.?)\" IS (NOT )?\"(.?)\":", stripped)
                if match:
                    var_name, is_not, check_val = match.groups()
                    real_val = str(self.get_value(var_name))
                    target_val = str(self.get_value(check_val))
                    condition_met = (real_val == target_val)
                    if is_not: condition_met = not condition_met

                    if condition_met:
                        sub_block = []
                        j = i + 1
                        while j < len(lines):
                            if len(lines[j]) - len(lines[j].lstrip()) > current_indent:
                                sub_block.append(lines[j])
                                j += 1
                            else: break
                        self.execute_block(sub_block, indent_level + 2)
                        i = j - 1

            elif stripped.startswith("REPEAT"):
                count = int(re.search(r"REPEAT (\d+) TIMES", stripped).group(1))
                if count > self.MAX_LOOP_SAFETY: return
                sub_block = []
                j = i + 1
                while j < len(lines):
                    if len(lines[j]) - len(lines[j].lstrip()) > current_indent:
                        sub_block.append(lines[j])
                        j += 1
                    else: break
                for _ in range(count):
                    self.execute_block(sub_block, indent_level + 2)
                i = j - 1

            i += 1
        return True

    def run(self, trigger):
        print(f"\n[*] TRIGGER: {trigger}")
        if trigger in self.triggers:
            self.execute_block(self.triggers[trigger])
        else:
            print("Trigger not found.")

if _name_ == "_main_":
    engine = AssertionEngine()
    # To test file I/O, create a file named 'io_test.asrt'
    if len(sys.argv) > 1:
        engine.load_manifest(sys.argv[1])
        engine.run("Start")
    else:
        print("Usage: python engine.py [filename.asrt]")
