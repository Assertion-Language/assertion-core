"""
Manifest Cryptographic Verification
Compact • Secure • Cross-Platform

This module verifies a manifest’s authenticity using:
- HMAC-SHA256 signatures
- A compact, embeddable, offline secret
- No OS-specific dependencies
"""

import hmac
import hashlib
from typing import Optional


# ============================================================
# 1. SECRET KEY (replace with your own for production)
# ============================================================
SECRET = b"ASSERTION_ENGINE_CRYPTO_2025"


# ============================================================
# 2. Extract signature from manifest text
# ============================================================
def extract_signature(text: str) -> Optional[str]:
    """
    Manifest format requirement:

    #SIGNATURE:<hex>
    ---
    <manifest content>

    The signature is NOT part of the content, only a header.

    This function returns the hex signature string or None.
    """
    lines = text.splitlines()
    for line in lines:
        if line.startswith("#SIGNATURE:"):
            return line.split(":", 1)[1].strip()
    return None


# ============================================================
# 3. Compute the expected signature
# ============================================================
def compute_signature(content: str) -> str:
    """
    Compute HMAC-SHA256 of the manifest content.
    Content excludes signature line.
    """
    return hmac.new(SECRET, content.encode("utf-8"), hashlib.sha256).hexdigest()


# ============================================================
# 4. Public verification function
# ============================================================
def verify_manifest_signature(text: str) -> bool:
    """
    - Reads manifest text
    - Extracts the signature
    - Strips the signature header from content
    - Computes HMAC
    - Compares securely

    Returns True if signature matches, else False.
    """

    sig = extract_signature(text)
    if not sig:
        return False

    # Remove signature line from content
    clean_lines = [
        line for line in text.splitlines()
        if not line.startswith("#SIGNATURE:")
    ]
    clean_text = "\n".join(clean_lines)

    expected = compute_signature(clean_text)

    # Constant-time compare
    return hmac.compare_digest(sig, expected)
