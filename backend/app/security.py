import hashlib
import secrets
from typing import Optional

def make_salt() -> str:
    """Return a hex salt string."""
    return secrets.token_hex(8)

def hash_password(pw: str, salt: Optional[str] = None) -> str:
    """
    Return stored password format: salt$hexhash
    Uses salt + password bytes hashed with sha256.
    """
    if salt is None:
        salt = make_salt()
    h = hashlib.sha256((salt + pw).encode("utf-8")).hexdigest()
    return f"{salt}${h}"

def verify_password(plain: str, stored: str) -> bool:
    """
    Verify a plaintext password against stored salt$hexhash.
    Returns True if matches.
    """
    try:
        salt, hexhash = stored.split("$", 1)
    except ValueError:
        return False
    check = hashlib.sha256((salt + plain).encode("utf-8")).hexdigest()
    return secrets.compare_digest(check, hexhash)
