
import hashlib
import hmac
import os
import sys

class LicenseManager:
    def __init__(self, secret_key: str = "super_secret_master_key_v1"):
        self.secret_key = secret_key.encode()

    def get_machine_id(self) -> str:
        """
        Generates a unique ID for the machine.
        Uses /etc/machine-id on Linux, fallbacks to simple MAC.
        """
        try:
            if os.path.exists("/etc/machine-id"):
                with open("/etc/machine-id", "r") as f:
                    return f.read().strip()
        except Exception:
            pass
        
        # Fallback
        import uuid
        return str(uuid.getnode())

    def generate_license(self, machine_id: str) -> str:
        """
        Generates a valid license key for a given machine ID.
        (Used by the vendor - US - to enable a client)
        """
        # HMAC-SHA256(Secret, MachineID)
        return hmac.new(self.secret_key, machine_id.encode(), hashlib.sha256).hexdigest()

    def validate_license(self):
        """
        Checks if the current environment has a valid license.
        Refuses to run if invalid.
        """
        mid = self.get_machine_id()
        expected = self.generate_license(mid)
        
        # Look for license.key file
        if not os.path.exists("license.key"):
            print("==================================================")
            print(" [ERROR] NO LICENSE FOUND")
            print(" This software is protected.")
            print(f" Your Machine ID: {mid}")
            print(" Please purchase a license to continue.")
            print("==================================================")
            sys.exit(1)
            
        with open("license.key", "r") as f:
            key = f.read().strip()
            
        if not hmac.compare_digest(key, expected):
            print("==================================================")
            print(" [ERROR] INVALID LICENSE")
            print(" This software is pirated or corrupted.")
            print(" Execution Refused.")
            print("==================================================")
            sys.exit(1)
            
        print("[SYSTEM] License Verified. Starting Engine...")
