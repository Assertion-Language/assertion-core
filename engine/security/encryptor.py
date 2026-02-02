
import os
import marshal
import py_compile

# Simple XOR Key (Obfuscation)
KEY = b"ANTIGRAVITY_SECRET_KEY_2025"

def xor_data(data: bytes) -> bytes:
    key_len = len(KEY)
    return bytes(b ^ KEY[i % key_len] for i, b in enumerate(data))

def encrypt_file(file_path: str):
    # 1. Compile to Bytecode
    try:
        cfile = py_compile.compile(file_path, doraise=True)
    except Exception as e:
        print(f"Failed to compile {file_path}: {e}")
        return

    # 2. Read Bytecode
    with open(cfile, "rb") as f:
        # Skip header (16 bytes for python 3.7+)
        # Actually, marshal loads the *code object* which is after the header.
        # But importlib.sourceless_loader expects header?
        # My custom loader will use marshal.load directly on the code object.
        # So I need to strip the header?
        # Standard .pyc has 16 bytes header.
        f.seek(16)
        code_data = f.read()

    # 3. Encrypt
    encrypted_data = xor_data(code_data)

    # 4. Save as .agl.bin
    target = file_path.replace(".py", ".agl.bin")
    with open(target, "wb") as f:
        f.write(encrypted_data)
    
    print(f"    [ENCRYPT] {file_path} -> {target}")

    # 5. Cleanup
    os.remove(file_path) # Source
    os.remove(cfile)     # Pyc

def encrypt_directory(root_dir: str):
    print(f"[THE VAULT] Encrypting directory: {root_dir}")
    for root, dirs, files in os.walk(root_dir):
        for file in files:
            if file.endswith(".py") and file != "boot.py":
                # boot.py must remain plain text to load the rest?
                # Or we compile boot.py to .pyc but don't encrypt it?
                # For this demo, we encrypt everything except the loader itself.
                # Assuming loader logic is in boot.py or separate.
                pass
                
    # Actually, we need to be careful.
    # I'll encrypt everything manually.
    pass

class VaultBuilder:
    def build(self, target_dir):
        for root, dirs, files in os.walk(target_dir):
            for file in files:
                if file.endswith(".py"):
                    full_path = os.path.join(root, file)
                    encrypt_file(full_path)
