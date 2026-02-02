
import os
import shutil
import compileall
import sys

def build_dist():
    print("[BUILD] Creating distribution 'dist'...")
    if os.path.exists("dist"):
        shutil.rmtree("dist")
    
    # Copy current directory to dist (excluding .git, venv, etc)
    # Simple copy: engine and main.py
    os.makedirs("dist")
    
    # Copy Engine
    shutil.copytree("engine", "dist/engine")
    
    # Compile
    print("[BUILD] Compiling to Bytecode (.pyc)...")
    compileall.compile_dir("dist/engine", force=True, legacy=True) # legacy=True for .pyc in place (not __pycache__)
    
    # Delete Source
    print("[BUILD] Removing Source Code (.py)...")
    for root, dirs, files in os.walk("dist"):
        for file in files:
            if file.endswith(".py"):
                os.remove(os.path.join(root, file))
                print(f"    Removed {file}")
    

    # Encrypt
    print("[BUILD] Encrypting (THE VAULT)...")
    from engine.security.encryptor import VaultBuilder
    VaultBuilder().build("dist/engine")
    
    # Copy Bootloader
    shutil.copy("boot.py", "dist/boot.py")
    
    print("[BUILD] Vault Locked.")
    print("        Run with: python3 dist/boot.py")

if __name__ == "__main__":
    build_dist()

