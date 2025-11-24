import sys
import os
import time
from engine import AssertionEngine

class Studio:
    def __init__(self):
        self.filename = "genesis.asrt"
        self.engine = AssertionEngine()

    def clear(self): os.system('cls' if os.name == 'nt' else 'clear')

    def menu(self):
        while True:
            self.clear()
            print("==========================================")
            print("   ASSERTION STUDIO [UNIVERSAL]")
            print(f"   TIER: {self.engine.tier}")
            print("==========================================")
            print("   [1] RUN CODE")
            print("   [2] WRITE CODE")
            print("   [3] ACTIVATE LICENSE")
            print("   [0] EXIT")
            
            c = input("\n   SELECT >> ").strip()
            
            if c == "1":
                print("\n   [*] EXECUTING...\n")
                self.engine = AssertionEngine() # Reload to catch new keys
                self.engine.load_manifest(self.filename)
                self.engine.run("Ignition")
                input("\n   [DONE]")
            
            elif c == "2":
                print(f"\n   [*] WRITING TO {self.filename} (Type SAVE to finish):")
                lines = []
                while True:
                    l = input("   > ")
                    if l.strip() == "SAVE": break
                    lines.append(l)
                with open(self.filename, "w") as f: f.write("\n".join(lines))
            
            elif c == "3":
                k = input("\n   PASTE KEY: ").strip()
                with open("license.key", "w") as f: f.write(k)
                print("   [+] KEY SAVED.")
                time.sleep(1)
            
            elif c == "0": sys.exit()

if __name__ == "__main__":
    Studio().menu()
