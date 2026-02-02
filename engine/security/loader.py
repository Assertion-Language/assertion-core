
import sys
import importlib.abc
import importlib.util
import os
import marshal

# Key must match Encryptor
KEY = b"ANTIGRAVITY_SECRET_KEY_2025"

def xor_data(data: bytes) -> bytes:
    key_len = len(KEY)
    return bytes(b ^ KEY[i % key_len] for i, b in enumerate(data))

class VaultLoader(importlib.abc.MetaPathFinder, importlib.abc.Loader):
    def find_spec(self, fullname, path, target=None):
        # We only handle our encrypted format
        if path is None:
             path = [os.getcwd()]
        
        # Convert dotted name to path
        # engine.engine -> engine/engine.agl.bin
        parts = fullname.split(".")
        
        # Check in all paths
        for p in path:
            # Check for package (__init__.agl.bin)
            pkg_target = os.path.join(p, *parts, "__init__.agl.bin")
            if os.path.exists(pkg_target):
                return importlib.util.spec_from_loader(fullname, self, is_package=True)
            
            # Check for module (.agl.bin)
            mod_target = os.path.join(p, *parts) + ".agl.bin"
            # It might be separate path join if parts has multiple
            # os.path.join(p, "engine", "engine.agl.bin")
            # If fullname is "engine.engine", parts=["engine", "engine"]
            # Target: root/engine/engine.agl.bin
            
            mod_target = os.path.join(p, *parts[:-1], parts[-1] + ".agl.bin")
            if os.path.exists(mod_target):
                 return importlib.util.spec_from_loader(fullname, self, is_package=False)
                 
        return None

    def create_module(self, spec):
        return None # Default creation

    def exec_module(self, module):
        fullname = module.__name__
        parts = fullname.split(".")
        
        # Locate file again (naive)
        # In real impl, store path in spec.
        # Let's check typical paths
        filename = None
        is_pkg = False
        
        # Try local first
        local_path = os.path.join(*parts) + ".agl.bin"
        local_pkg = os.path.join(*parts, "__init__.agl.bin")
        
        if os.path.exists(local_pkg):
            filename = local_pkg
            is_pkg = True
        elif os.path.exists(local_path):
             filename = local_path
        else:
             # Try searching sys.path?
             # For this demo, assumption is CWD.
             pass
             
        if not filename:
            raise ImportError(f"VaultLoader could not find {fullname}")

        # Decrypt
        with open(filename, "rb") as f:
            enc_data = f.read()
        
        raw_bytes = xor_data(enc_data)
        
        try:
            code = marshal.loads(raw_bytes)
        except Exception as e:
            raise ImportError(f"VaultLoader failed to load {fullname} (Decryption Error?): {e}")
            
        # Execute
        if is_pkg:
            module.__path__ = [os.path.dirname(filename)]
            
        exec(code, module.__dict__)

# Install Hook
sys.meta_path.insert(0, VaultLoader())
