import re
import sys
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
            type_ = type_.strip()
            if value:
                val_str = value.strip().replace('"', '')
                # Robust Number Detection
                num_str = re.sub(r'\s+', '', val_str)
                if num_str.lstrip('-').replace('.', '').isdigit() and num_str.count('-') <= 1 and num_str.count('.') <= 1:
                    val = float(num_str) if '.' in num_str else int(num_str)
                else:
                    val = val_str
            else:
                if any(t in type_.lower() for t in ["number", "integer", "float"]):
                    val = 0
                else:
                    val = ""
            self.state[name] = {"type": type_, "value": val}

        # 2. PARSE CONSTRAINTS
        constraint_section = re.search(r"CONSTRAINT:(.*?)(?:WHEN|THERE|$)", content, re.DOTALL)
        if constraint_section:
            rules = constraint_section.group(1).strip().split('\n')
            for rule in rules:
                cleaned = rule.strip().replace("- ", "")
                if cleaned:
                    self.constraints.append(cleaned)

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
                i += 1 

            elif "TO FILE" in stripped:
                mode = 'a' if stripped.startswith("APPEND") else 'w'
                parts = stripped.split(" TO FILE ")
                content_raw = parts[0].replace("WRITE", "").replace("APPEND", "").strip()
                filename = parts[1].strip().replace('"', '')
                
                content = str(self.get_value(content_raw))
                with open(filename, mode) as f:
                    if mode == 'a': f.write(content + "\n")
                    else: f.write(content)
                print(f"    [DISK] Wrote to {filename}")
                i += 1 

            elif stripped.startswith("READ FILE"):
                match = re.search(r"READ FILE \"(.?)\" INTO \"(.?)\"", stripped)
                if match:
                    filename, var_target = match.groups()
                    if os.path.exists(filename):
                        with open(filename, 'r') as f:
                            self.state[var_target]["value"] = f.read().strip()
                        print(f"    [DISK] Read from {filename}")
                    else:
                        print(f"    [!] ERROR: File {filename} not found.")
                i += 1 

            # --- EXISTING LOGIC ---
            elif stripped.startswith("ASK"):
                match = re.search(r"ASK \"(.?)\" and STORE in \"(.?)\"", stripped)
                if match:
                    question, var_target = match.groups()
                    user_input = input(f"    [INPUT] {question} ")
                    self.state[var_target]["value"] = user_input
                i += 1 

            elif stripped.startswith("OUTPUT"):
                target = stripped.replace("OUTPUT", "").strip()
                print(f"    > {self.get_value(target)}")
                i += 1 

            elif stripped.startswith("SET"):
                arith_match = re.search(r"SET\s+\"(.?)\"\s+to\s+\"(.?)\"\s+(PLUS|MINUS|TIMES)\s+(.*)", stripped)
                if arith_match:
                    target, v1, op, v2 = arith_match.groups()
                    val1 = self.get_value(v1)
                    val2 = self.get_value(v2)
                    if op == "PLUS": result = val1 + val2
                    elif op == "MINUS": result = val1 - val2
                    elif op == "TIMES": result = val1 * val2
                    self.state[target]["value"] = result
                    if not self.check_constraints(): return False
                else:
                    simple_match = re.search(r'SET\s+\"(.?)\"\s+to\s+(.)', stripped)
                    if simple_match:
                        target, v = simple_match.groups()
                        self.state[target]["value"] = self.get_value(v)
                        if not self.check_constraints(): return False
                i += 1 

            elif stripped.startswith("IF"):
                match = re.search(r'IF\s+"(.?)"\s+IS\s+(NOT\s+)?\s+"([^"])"\s*:', stripped)
                condition_met = False
                if match:
                    var_name, is_not, check_val = match.groups()
                    real_val = str(self.get_value(var_name))
                    target_val = str(self.get_value(check_val))
                    condition_met = (real_val == target_val)
                    if is_not: condition_met = not condition_met

                sub_block = []
                j = i + 1
                while j < len(lines):
                    if j >= len(lines): break
                    sub_line_indent = len(lines[j]) - len(lines[j].lstrip())
                    if sub_line_indent > current_indent:
                        sub_block.append(lines[j])
                        j += 1
                    else: break
                
                if condition_met:
                    self.execute_block(sub_block, indent_level=current_indent + 1)
                i = j 

            elif stripped.startswith("REPEAT"):
                match = re.search(r'REPEAT\s+(\d+)\s+TIMES', stripped)
                count = 0
                if match:
                    count = int(match.group(1))
                    if count > self.MAX_LOOP_SAFETY: 
                        print(f"    [!] LOOP SAFETY: Skipping repeat of {count} times.")
                        count = 0
                
                sub_block = []
                j = i + 1
                while j < len(lines):
                    if j >= len(lines): break
                    sub_line_indent = len(lines[j]) - len(lines[j].lstrip())
                    if sub_line_indent > current_indent:
                        sub_block.append(lines[j])
                        j += 1
                    else: break
                
                for _ in range(count):
                    if not self.execute_block(sub_block, indent_level=current_indent + 1) is False:
                         pass
                i = j 

            else:
                i += 1
        return True

    def run(self, trigger):
        print(f"\n[*] TRIGGER: {trigger}")
        if trigger in self.triggers:
            success = self.execute_block(self.triggers[trigger])
            if not success:
                print("Execution halted due to constraint violation.")
        else:
            print("Trigger not found.")

if _name_ == "_main_":
    engine = AssertionEngine()
    if len(sys.argv) > 1:
        engine.load_manifest(sys.argv[1])
        engine.run("Ignition") 
    else:
        print("Usage: python engine.py [filename.asrt]")
