
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
    
    print("[BUILD] Obfuscation Complete.")
    print("        Distribution available in 'dist/'.")
    print("        Run with: python3 dist/engine/cli/repl.pyc (Wait, need entry point wrapper?)")

if __name__ == "__main__":
    build_dist()
