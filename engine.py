#engine.py

import re
import sys
import os
import traceback


class DSLRuntimeError(Exception):
    """Custom error for DSL execution."""
    pass


class AssertionEngine:
    """
    A full-featured, hardened DSL interpreter for the Assertion Language.
    Includes strict parsing, safe regex handling, robust I/O, multi-trigger chaining,
    and deterministic execution.
    """

    # ----------------------------
    # INITIALIZATION
    # ----------------------------
    def __init__(self, debug=False):
        self.state = {}
        self.constraints = []
        self.triggers = {}
        self.debug_mode = debug
        self.MAX_LOOP_SAFETY = 500
        self.MAX_RECURSION_DEPTH = 50
        self.call_depth = 0

    # ----------------------------
    # UTILITIES
    # ----------------------------
    def log(self, msg):
        if self.debug_mode:
            print(f"[DEBUG] {msg}")

    # ----------------------------
    # PARSER
    # ----------------------------
    def load_manifest(self, file_path):
        print(f"[*] Loading Manifest: {file_path}")

        if not os.path.exists(file_path):
            raise DSLRuntimeError(f"Manifest '{file_path}' does not exist.")

        content = open(file_path).read()

        # -------- VARIABLES --------
        pattern_var = re.compile(
            r'THERE IS A ([^"]+?) called "([^"]+)"(?: with value ([^\.\n]+))?[\.\n]'
        )

        for type_, name, val in pattern_var.findall(content):
            type_ = type_.strip()
            val = val.strip().replace('"', '') if val else None

            if val is None:
                # Type-based defaulting
                if any(t in type_.lower() for t in ("number", "integer", "float")):
                    parsed = 0
                else:
                    parsed = ""
            else:
                # Strong numeric parsing
                num = re.sub(r"\s+", "", val)
                if num.replace(".", "", 1).lstrip("-").isdigit():
                    parsed = float(num) if "." in num else int(num)
                else:
                    parsed = val

            self.state[name] = {"type": type_, "value": parsed}

        # -------- CONSTRAINTS --------
        block = re.search(r"CONSTRAINT:(.*?)(?=WHEN|THERE|$)", content, re.DOTALL)
        if block:
            lines = block.group(1).strip().split("\n")
            for ln in lines:
                ln = ln.strip().replace("- ", "")
                if ln:
                    self.constraints.append(ln)

        # -------- TRIGGERS --------
        split = re.split(r"\bWHEN\b", content)[1:]

        for section in split:
            lines = section.split("\n")
            trigger_name = lines[0].replace(":", "").strip().replace('"', "")
            actions = [l for l in lines[1:] if l.strip()]
            self.triggers[trigger_name] = actions

    # ----------------------------
    # STATE HELPERS
    # ----------------------------
    def get_value(self, raw):
        raw = raw.strip().replace('"', '')
        if raw in self.state:
            return self.state[raw]["value"]
        try:
            return int(raw) if raw.isdigit() else float(raw)
        except:
            return raw

    def set_value(self, key, value):
        if key not in self.state:
            raise DSLRuntimeError(f"Variable '{key}' does not exist.")
        self.state[key]["value"] = value

    # ----------------------------
    # CONSTRAINT CHECKING
    # ----------------------------
    def check_constraints(self):
        for rule in self.constraints:
            if "cannot be greater than" in rule:
                var, limit = rule.split(" cannot be greater than ")
                var = var.replace('"', '').strip()
                limit = float(limit.strip())
                val = self.state[var]["value"]
                if val > limit:
                    print(f"\n[!] CONSTRAINT VIOLATION: {var} ({val}) > {limit}")
                    return False
        return True

    # ----------------------------
    # BLOCK EXECUTION
    # ----------------------------
    def execute_block(self, lines, indent=0):
        i = 0
        L = len(lines)

        while i < L:
            line = lines[i]
            stripped = line.strip()
            current_indent = len(line) - len(line.lstrip())

            # Skip unrelated blocks
            if current_indent < indent:
                i += 1
                continue

            self.log(f"Line: {stripped}")

            # ========== CREATE FILE ==========
            if stripped.startswith("CREATE FILE"):
                fname = stripped.replace("CREATE FILE", "").strip().strip('"')
                open(fname, "w").close()
                print(f"    [DISK] Created: {fname}")
                i += 1
                continue

            # ========== WRITE / APPEND ==========
            if "TO FILE" in stripped and (stripped.startswith("WRITE") or stripped.startswith("APPEND")):
                mode = "a" if stripped.startswith("APPEND") else "w"
                left, fname = stripped.split(" TO FILE ")
                fname = fname.strip().strip('"')
                content_raw = left.replace("WRITE", "").replace("APPEND", "").strip()
                content = str(self.get_value(content_raw))
                with open(fname, mode) as f:
                    if mode == "a":
                        f.write(content + "\n")
                    else:
                        f.write(content)
                print(f"    [DISK] Wrote to: {fname}")
                i += 1
                continue

            # ========== READ FILE ==========
            if stripped.startswith("READ FILE"):
                m = re.search(r'READ FILE "([^"]+)" INTO "([^"]+)"', stripped)
                if not m:
                    raise DSLRuntimeError(f"Malformed READ FILE syntax: {stripped}")
                fname, target = m.groups()
                if not os.path.exists(fname):
                    print(f"    [!] File not found: {fname}")
                else:
                    self.state[target]["value"] = open(fname).read().strip()
                    print(f"    [DISK] Read from: {fname}")
                i += 1
                continue

            # ========== ASK ==========
            if stripped.startswith("ASK"):
                m = re.search(r'ASK "([^"]+)" and STORE in "([^"]+)"', stripped)
                if not m:
                    raise DSLRuntimeError(f"Malformed ASK syntax: {stripped}")
                q, target = m.groups()
                ans = input(f"    [INPUT] {q} ")
                self.set_value(target, ans)
                i += 1
                continue

            # ========== OUTPUT ==========
            if stripped.startswith("OUTPUT"):
                target = stripped.replace("OUTPUT", "").strip()
                print(f"    > {self.get_value(target)}")
                i += 1
                continue

            # ========== SET ==========
            if stripped.startswith("SET"):
                # Math form
                m = re.search(r'SET\s+"([^"]+)"\s+to\s+"([^"]+)"\s+(PLUS|MINUS|TIMES)\s+"([^"]+)"', stripped)
                if m:
                    target, a, op, b = m.groups()
                    A, B = self.get_value(a), self.get_value(b)
                    if op == "PLUS": result = A + B
                    elif op == "MINUS": result = A - B
                    else: result = A * B
                    self.set_value(target, result)
                    if not self.check_constraints():
                        return False
                    i += 1
                    continue

                # Simple form
                m = re.search(r'SET\s+"([^"]+)"\s+to\s+(.+)', stripped)
                if m:
                    target, value = m.groups()
                    self.set_value(target, self.get_value(value))
                    if not self.check_constraints():
                        return False
                    i += 1
                    continue

                raise DSLRuntimeError(f"Malformed SET syntax: {stripped}")

            # ========== IF ==========
            if stripped.startswith("IF"):
                m = re.search(r'IF\s+"([^"]+)"\s+IS\s+(NOT\s+)?\s*"([^"]+)"\s*:', stripped)
                if not m:
                    raise DSLRuntimeError(f"Malformed IF syntax: {stripped}")
                var, neg, cmp_val = m.groups()
                real = str(self.get_value(var))
                cmp_val = str(self.get_value(cmp_val))
                condition = (real == cmp_val)
                if neg:
                    condition = not condition

                # Collect nested lines
                block = []
                j = i + 1
                while j < L:
                    next_indent = len(lines[j]) - len(lines[j].lstrip())
                    if next_indent > current_indent:
                        block.append(lines[j])
                    else:
                        break
                    j += 1

                if condition:
                    self.log("IF branch TRUE")
                    if not self.execute_block(block, indent=current_indent + 1):
                        return False
                else:
                    self.log("IF branch FALSE")

                i = j
                continue

            # ========== REPEAT ==========
            if stripped.startswith("REPEAT"):
                m = re.search(r"REPEAT\s+(\d+)\s+TIMES", stripped)
                if not m:
                    raise DSLRuntimeError(f"Malformed REPEAT syntax: {stripped}")
                count = int(m.group(1))

                if count > self.MAX_LOOP_SAFETY:
                    print(f"[!] Loop safety triggered ({count}), skipping loop.")
                    count = 0

                # Collect nested block
                block = []
                j = i + 1
                while j < L:
                    next_indent = len(lines[j]) - len(lines[j].lstrip())
                    if next_indent > current_indent:
                        block.append(lines[j])
                    else:
                        break
                    j += 1

                for _ in range(count):
                    if not self.execute_block(block, indent=current_indent + 1):
                        break

                i = j
                continue

            raise DSLRuntimeError(f"Unknown instruction: {stripped}")

        return True

    # ----------------------------
    # TRIGGER EXECUTION
    # ----------------------------
    def run(self, trigger):
        if trigger.startswith("WHEN_CALL"):
            trigger = trigger.replace("WHEN_CALL", "").strip().strip('"')

        if trigger not in self.triggers:
            raise DSLRuntimeError(f"Trigger '{trigger}' not found.")

        print(f"\n[*] Trigger: {trigger}")

        if self.call_depth > self.MAX_RECURSION_DEPTH:
            raise DSLRuntimeError("Max trigger recursion depth exceeded.")

        self.call_depth += 1
        try:
            ok = self.execute_block(self.triggers[trigger])
            if not ok:
                print("Execution halted due to constraint violation.")
        finally:
            self.call_depth -= 1


# ---------------------------------------
# CLI ENTRY
# ---------------------------------------
if __name__ == "__main__":
    engine = AssertionEngine(debug=False)
    if len(sys.argv) > 1:
        engine.load_manifest(sys.argv[1])
        engine.run("Ignition")