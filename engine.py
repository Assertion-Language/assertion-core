import re
import sys
import os
import time
import hmac
import hashlib
from pathlib import Path
from typing import List, Dict, Any

# ============================================================
# 1. LICENSE AUTHORITY (HMAC Protected)
# ============================================================
class LicenseAuthority:
    SECRET = b"MOBIUS_ARCHITECT_ULTRAKEY_2025"

    @staticmethod
    def verify_key(raw: str):
        try:
            tier, ts, hwid, sig = raw.split("|")
            message = f"{tier}:{ts}:{hwid}".encode()
            expected = hmac.new(LicenseAuthority.SECRET, message, hashlib.sha256).hexdigest()
            if sig != expected: return None
            return {"tier": tier, "hwid": hwid}
        except:
            return None

def get_hwid():
    try:
        if os.name == 'nt':
            import subprocess
            data = subprocess.check_output('wmic csproduct get uuid').decode().split('\n')[1].strip()
        else:
            data = f"{os.name}-{os.getlogin()}"
    except:
        data = "GENERIC_ID"
    return hashlib.sha256(data.encode()).hexdigest()[:16]

# ============================================================
# 2. INDUSTRIAL PARSER (Tokenization)
# ============================================================
class Tokenizer:
    def tokenize(self, text: str):
        lines = text.split("\n")
        tokens = []
        for ln in lines:
            if not ln.strip(): continue
            indent = len(ln) - len(ln.lstrip())
            tokens.append({"indent": indent, "raw": ln.strip()})
        return tokens

class Parser:
    def parse(self, tokens):
        ast = {}
        current_trigger = None
        buf = []
        for t in tokens:
            raw = t["raw"]
            if raw.startswith("WHEN "):
                if current_trigger: ast[current_trigger] = buf
                buf = []
                current_trigger = raw.replace("WHEN ", "").replace(":", "").strip()
                continue
            buf.append(t)
        if current_trigger: ast[current_trigger] = buf
        return ast

# ============================================================
# 3. VIRTUAL FILE SYSTEM (Sandboxed)
# ============================================================
class VFS:
    ROOT = Path(".vfs")
    @staticmethod
    def init(): VFS.ROOT.mkdir(exist_ok=True)
    @staticmethod
    def write(name, content): (VFS.ROOT / name).write_text(str(content), encoding='utf-8')
    @staticmethod
    def read(name): 
        p = VFS.ROOT / name
        return p.read_text(encoding='utf-8') if p.exists() else None

# ============================================================
# 4. THE ENGINE (Balanced Logic)
# ============================================================
class AssertionEngine:
    def __init__(self, debug=False):
        self.state = {}
        self.constraints = []
        self.triggers = {}
        
        # --- THE BALANCED MODEL ---
        # Free: 500 Loops, No Debug Logs. (Good for learning)
        # Pro:  1,000,000 Loops, Full Debug Logs. (Good for business)
        self.tier = "FREE"
        self.limits = {"loop": 500, "recursion": 50, "debug": False}
        
        self._load_license()

    def _load_license(self):
        if os.path.exists("license.key"):
            try:
                key = open("license.key").read().strip()
                data = LicenseAuthority.verify_key(key)
                if data and data["hwid"] == get_hwid():
                    self.tier = data["tier"]
                    # UNLOCK GOD MODE
                    if self.tier in ["PRO", "MAX"]:
                        self.limits = {"loop": 1000000, "recursion": 2000, "debug": True}
            except:
                pass

    def log(self, msg):
        # PAYWALL: Only PRO users see the internal logic trace
        if self.limits["debug"]:
            print(f"    [DEBUG] {msg}")

    def load_manifest(self, path):
        if not os.path.exists(path): return
        txt = Path(path).read_text(encoding='utf-8')
        
        # 1. VARS
        for ln in txt.split("\n"):
            if "THERE IS A" in ln: 
                m = re.search(r'THERE IS A (.*?) called "(.*?)"(?: with value (.*?))?[.\n]?', ln)
                if m:
                    t, n, v = m.groups()
                    v = v.strip().replace('"', '') if v else "0"
                    if v.replace('.','',1).isdigit(): v = float(v) if '.' in v else int(v)
                    self.state[n] = {"type": t.strip(), "value": v}
            
        # 2. CONSTRAINTS
        block = re.search(r"CONSTRAINT:(.*?)(?=WHEN|THERE|$)", txt, re.DOTALL)
        if block:
            for ln in block.group(1).split("\n"):
                if ln.strip(): self.constraints.append(ln.strip().replace("- ", ""))

        # 3. TRIGGERS
        tokens = Tokenizer().tokenize(txt)
        self.triggers = Parser().parse(tokens)

    def get(self, n):
        n = str(n).strip().replace('"', '')
        return self.state[n]["value"] if n in self.state else (float(n) if n.replace('.','',1).isdigit() else n)

    def set(self, n, v):
        self.state[n]["value"] = v
        if not self.check_constraints():
            print("[!] CRITICAL: REALITY CONSTRAINT BROKEN")
            sys.exit(1)

    def check_constraints(self):
        for r in self.constraints:
            if "cannot be greater than" in r:
                v, l = r.split(" cannot be greater than ")
                if self.get(v.strip().strip('"')) > float(l): return False
        return True

    def execute_block(self, tokens, indent=0):
        i = 0
        while i < len(tokens):
            t = tokens[i]
            raw, curr = t["raw"], t["indent"]
            if curr < indent: 
                i += 1
                continue
            
            self.log(f"Exec: {raw}") 

            if raw.startswith("OUTPUT"):
                print(f"    > {self.get(raw.replace('OUTPUT','').strip())}")
                i += 1

            elif raw.startswith("SET"):
                m = re.search(r'SET "(.*?)" to "(.*?)" (PLUS|MINUS) "(.*?)"', raw)
                if m:
                    tgt, a, op, b = m.groups()
                    v1 = self.get(a); v2 = self.get(b)
                    res = v1 + v2 if op == "PLUS" else v1 - v2
                    self.set(tgt, res)
                else:
                    m2 = re.search(r'SET "(.*?)" to "(.*?)"', raw)
                    if m2: self.set(m2.group(1), self.get(m2.group(2)))
                i += 1
            
            elif raw.startswith("REPEAT"):
                m = re.search(r"REPEAT (\d+) TIMES", raw)
                count = int(m.group(1)) if m else 0
                
                # THE SOFT CAP (Fame vs Money)
                if count > self.limits["loop"]:
                    print(f"    [!] FREE TIER LIMIT: Capped at {self.limits['loop']} loops.")
                    count = self.limits["loop"]

                sub = []
                j = i + 1
                while j < len(tokens):
                    if tokens[j]["indent"] > curr: sub.append(tokens[j]); j += 1
                    else: break
                
                for _ in range(count): self.execute_block(sub, indent + 2)
                i = j
            
            elif raw.startswith("IF"):
                m = re.search(r'IF "(.*?)" IS "(.*?)"', raw)
                cond = False
                if m: cond = str(self.get(m.group(1))) == str(self.get(m.group(2)))
                
                sub = []
                j = i + 1
                while j < len(tokens):
                    if tokens[j]["indent"] > curr: sub.append(tokens[j]); j += 1
                    else: break
                if cond: self.execute_block(sub, indent + 2)
                i = j
            
            elif raw.startswith("CREATE") or "TO FILE" in raw:
                if "WRITE" in raw: 
                    parts = raw.split(" TO FILE ")
                    VFS.write(parts[1].strip().replace('"',''), self.get(parts[0].replace("WRITE","").strip()))
                    self.log("Disk Write Success")
                i += 1
            else: i += 1

    def run(self, trig):
        if trig in self.triggers: self.execute_block(self.triggers[trig])

if __name__ == "__main__":
    VFS.init()
    engine = AssertionEngine()
    if len(sys.argv) > 1:
        engine.load_manifest(sys.argv[1])
        engine.run("Ignition")
    else:
        print("Usage: python engine.py <file.asrt>")
