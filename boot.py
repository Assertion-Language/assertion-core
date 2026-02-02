
"""
THE VAULT - SECURE BOOTLOADER
This file is the ONLY entry point. All other code is encrypted.
"""
import sys
import os

# 1. Install the secure loader
# We need to import the loader. 
# But the loader itself might be encrypted?
# Chicken and egg. 
# We include the loader logic INLINE or leave loader.py as plaintext.
# For "Uncrackable", inline is better, or obfuscate loader.py.
# We will import loader.py (assuming it's plaintext for now) or inline it.
# To keep this clean, I will assume loader.py is available or I write it here.
# I'll write the loader logic here to reduce file count and dependency.

import importlib.abc
import importlib.util
import marshal

KEY = b"ANTIGRAVITY_SECRET_KEY_2025"

def xor_data(data: bytes) -> bytes:
    key_len = len(KEY)
    return bytes(b ^ KEY[i % key_len] for i, b in enumerate(data))

class VaultLoader(importlib.abc.MetaPathFinder, importlib.abc.Loader):
    def find_spec(self, fullname, path, target=None):
        if path is None: path = [os.getcwd()]
        parts = fullname.split(".")
        
        # 1. Package?
        # Check path/part/__init__.agl.bin
        for p in path:
            # reconstruct path
            pkg_path = os.path.join(p, *parts, "__init__.agl.bin")
            if os.path.exists(pkg_path):
                 return importlib.util.spec_from_loader(fullname, self, is_package=True)
            
            # 2. Module? 
            # path/part.agl.bin? Or path/part/part.agl.bin?
            # Standard: path/module.agl.bin
            # If engine.runtime.interpreter:
            # p/engine/runtime/interpreter.agl.bin
            
            mod_path = os.path.join(p, *parts) + ".agl.bin"
            if os.path.exists(mod_path):
                return importlib.util.spec_from_loader(fullname, self, is_package=False)
                
        return None

    def create_module(self, spec): return None
    
    def exec_module(self, module):
        fullname = module.__name__
        parts = fullname.split(".")
        
        # Re-resolve (Hack for MVP)
        filename = None
        is_pkg = False
        
        # Check CWD/Relative
        path_base = os.path.join(*parts)
        if os.path.exists(path_base + "/__init__.agl.bin"):
            filename = path_base + "/__init__.agl.bin"
            is_pkg = True
        elif os.path.exists(path_base + ".agl.bin"):
            filename = path_base + ".agl.bin"
            
        if not filename:
             raise ImportError(f"SecureLoad fail: {fullname}")
             
        with open(filename, "rb") as f:
            data = xor_data(f.read())
        
        try:
            code = marshal.loads(data)
        except:
            raise ImportError(f"Corrupted Vault: {fullname}")
            
        if is_pkg: module.__path__ = [os.path.dirname(filename)]
        exec(code, module.__dict__)

# Install Hook
sys.meta_path.insert(0, VaultLoader())

# ============================================================
# BOOT
# ============================================================
print("[THE VAULT] Secure Boot Initialized.")

if __name__ == "__main__":
    try:
        # Load the Engine
        # from engine.runtime.interpreter import Interpreter
        # This triggers the hook!
        
        # We need a license check first? 
        # Engine does it internally.
        
        # Import the REPL or Test?
        # Let's import the Interpreter and run a simple test or drop to REPL.
        # User didn't ask for REPL, just "encrypt source".
        # I'll run the "interpreter" module if main.
        
        from engine.runtime.interpreter import Interpreter
        print("[THE VAULT] Engine Loaded from Encrypted Memory.")
        
        interpreter = Interpreter()
        # Interpreter init checks license.
        
        print("Ready. (Running minimal test)")
        # Minimal test
        # We need classes from ast_nodes?
        # They are encrypted too.
        from engine.parser.fuzzy_parser import FuzzyParser
        
        code = 'Say "Hello form The Vault".'
        parser = FuzzyParser()
        prog = parser.parse(code)
        import asyncio
        asyncio.run(interpreter.run(prog))
        
    except Exception as e:
        print(f"[BOOT ERROR] {e}")
