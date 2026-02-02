
import hashlib
import hmac
import os
import sys
from enum import Enum

class Tier(Enum):
    FREE = "Free"
    PRO = "Pro"

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
        Generates a valid PRO license key for a given machine ID.
        """
        # HMAC-SHA256(Secret, MachineID)
        return hmac.new(self.secret_key, machine_id.encode(), hashlib.sha256).hexdigest()

    def validate_license(self) -> Tier:
        """
        Checks for license.key. 
        Returns Tier.PRO if valid.
        Returns Tier.FREE if missing/invalid.
        """
        mid = self.get_machine_id()
        expected = self.generate_license(mid)
        
        # Look for license.key file
        if not os.path.exists("license.key"):
            print("==================================================")
            print(f" [INFO] Running in FREE Mode (Machine ID: {mid})")
            print(" Upgrade to PRO to unlock Networking, Shell, and more.")
            print("==================================================")
            return Tier.FREE
            
        with open("license.key", "r") as f:
            key = f.read().strip()
            
        if not hmac.compare_digest(key, expected):
            print("==================================================")
            print(" [WARN] Invalid License Key. Reverting to FREE Mode.")
            print("==================================================")
            return Tier.FREE
            
        print("==================================================")
        print(" [SYSTEM] PRO LICENSE VERIFIED.")
        print(" Unlocked: Networking, Shell, FFI, Persistence.")
        print("==================================================")
        return Tier.PRO
