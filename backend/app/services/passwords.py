"""Password hashing with stdlib scrypt — zero external dependencies.

Format: "scrypt$<n>$<r>$<p>$<salt_hex>$<hash_hex>". Parameters are embedded in
the stored string so they can be raised later without breaking old hashes.
Plaintext passwords are never stored or logged anywhere.
"""

import hashlib
import hmac
import os

# OWASP-reasonable interactive-login parameters (~16.8 MB memory cost).
_N, _R, _P = 16384, 8, 1
_SALT_BYTES = 16
_DKLEN = 32
# scrypt with n=16384,r=8 needs ~16.8MB; OpenSSL's default maxmem (32MB in
# theory, lower on some builds) can reject it — always pass maxmem explicitly.
_MAXMEM = 64 * 1024 * 1024


def hash_password(password: str) -> str:
    salt = os.urandom(_SALT_BYTES)
    derived = hashlib.scrypt(
        password.encode("utf-8"), salt=salt, n=_N, r=_R, p=_P,
        maxmem=_MAXMEM, dklen=_DKLEN,
    )
    return f"scrypt${_N}${_R}${_P}${salt.hex()}${derived.hex()}"


def verify_password(password: str, stored: str) -> bool:
    """Constant-time comparison against a stored hash; False on any malformation."""
    try:
        algo, n_s, r_s, p_s, salt_hex, hash_hex = stored.split("$")
        if algo != "scrypt":
            return False
        n, r, p = int(n_s), int(r_s), int(p_s)
        expected = bytes.fromhex(hash_hex)
        derived = hashlib.scrypt(
            password.encode("utf-8"), salt=bytes.fromhex(salt_hex),
            n=n, r=r, p=p, maxmem=_MAXMEM, dklen=len(expected),
        )
        return hmac.compare_digest(derived, expected)
    except (ValueError, TypeError):
        return False
