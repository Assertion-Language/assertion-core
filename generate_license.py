
from engine.security.license import LicenseManager

lm = LicenseManager()
mid = lm.get_machine_id()
print(f"Machine ID: {mid}")
key = lm.generate_license(mid)
print(f"License Key: {key}")

with open("license.key", "w") as f:
    f.write(key)
print("Saved to license.key")
