"""Password hashing and JWT helpers.

Passwords use scrypt (memory-hard, built into Python, no extra dependency).
Tokens are short-lived HS256 JWTs that carry only the user id.
"""
import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

import jwt

from app.config import settings

# scrypt cost settings: ~16 MB of memory per hash, which makes brute-forcing expensive.
_N, _R, _P = 2**14, 8, 1
_ALGORITHM = "HS256"


class TokenError(Exception):
    """The token is missing, expired, forged or otherwise unusable."""


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode("utf-8"), salt=salt, n=_N, r=_R, p=_P, dklen=32)
    return f"scrypt${_N}${_R}${_P}${salt.hex()}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        scheme, n, r, p, salt_hex, digest_hex = stored.split("$")
        if scheme != "scrypt":
            return False
        expected = bytes.fromhex(digest_hex)
        actual = hashlib.scrypt(
            password.encode("utf-8"),
            salt=bytes.fromhex(salt_hex),
            n=int(n),
            r=int(r),
            p=int(p),
            dklen=len(expected),
        )
    except (ValueError, TypeError):
        return False
    return hmac.compare_digest(actual, expected)


def create_access_token(user_id: int, expires_delta: Optional[timedelta] = None) -> str:
    now = datetime.now(timezone.utc)
    lifetime = expires_delta if expires_delta is not None else timedelta(minutes=settings.access_token_minutes)
    payload = {"sub": str(user_id), "iat": now, "exp": now + lifetime}
    return jwt.encode(payload, settings.secret_key, algorithm=_ALGORITHM)


def decode_access_token(token: str) -> int:
    try:
        payload = jwt.decode(
            token,
            settings.secret_key,
            algorithms=[_ALGORITHM],  # never trust the algorithm named inside the token
            options={"require": ["exp", "sub"]},
        )
        return int(payload["sub"])
    except (jwt.PyJWTError, ValueError, TypeError, KeyError):
        raise TokenError("invalid token") from None
