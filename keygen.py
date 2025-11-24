import hmac
import hashlib
import time
import os

SECRET = b"MOBIUS_ARCHITECT_ULTRAKEY_2025"

def generate(tier, hwid):
    ts = int(time.time())
    msg = f"{tier}:{ts}:{hwid}".encode()
    sig = hmac.new(SECRET, msg, hashlib.sha256).hexdigest()
    return f"{tier}|{ts}|{hwid}|{sig}"

print("--- ASSERTION KEYGEN ---")
hwid = input("HWID (From 'python engine.py --hwid'): ")
# Note: Add --hwid logic to engine if needed, or use the Studio to find it later.
# For now, just type 'GENERIC_ID' to test.
if not hwid: hwid = "GENERIC_ID" 

key = generate("PRO", hwid)
print(f"\nKEY: {key}")
