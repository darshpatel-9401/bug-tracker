from datetime import timedelta

import jwt
import pytest

from app.config import settings
from app.security import (
    TokenError,
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)


def test_hash_is_not_the_plain_password():
    hashed = hash_password("Password123")
    assert "Password123" not in hashed
    assert hashed.startswith("scrypt$")


def test_same_password_gets_different_hashes_because_of_salt():
    assert hash_password("Password123") != hash_password("Password123")


def test_correct_password_verifies():
    assert verify_password("Password123", hash_password("Password123")) is True


def test_wrong_password_fails():
    assert verify_password("password123", hash_password("Password123")) is False


@pytest.mark.parametrize("garbage", ["", "plaintext", "scrypt$1$2", "scrypt$a$b$c$d$e", "md5$1$2$3$4$5"])
def test_malformed_stored_hash_is_rejected_not_crashing(garbage):
    assert verify_password("Password123", garbage) is False


def test_token_round_trip():
    token = create_access_token(42)
    assert decode_access_token(token) == 42


def test_expired_token_is_rejected():
    token = create_access_token(42, expires_delta=timedelta(minutes=-1))
    with pytest.raises(TokenError):
        decode_access_token(token)


def test_tampered_token_is_rejected():
    token = create_access_token(42)
    head, body, sig = token.split(".")
    broken = ".".join([head, body, sig[:-2] + ("AA" if not sig.endswith("AA") else "BB")])
    with pytest.raises(TokenError):
        decode_access_token(broken)


def test_token_signed_with_another_key_is_rejected():
    forged = jwt.encode({"sub": "1", "exp": 9999999999}, "some-other-secret-key-that-is-long-enough", algorithm="HS256")
    with pytest.raises(TokenError):
        decode_access_token(forged)


def test_token_without_subject_is_rejected():
    no_sub = jwt.encode({"exp": 9999999999}, settings.secret_key, algorithm="HS256")
    with pytest.raises(TokenError):
        decode_access_token(no_sub)


def test_token_with_non_numeric_subject_is_rejected():
    odd = jwt.encode({"sub": "admin", "exp": 9999999999}, settings.secret_key, algorithm="HS256")
    with pytest.raises(TokenError):
        decode_access_token(odd)


def test_unsigned_none_algorithm_token_is_rejected():
    unsigned = jwt.encode({"sub": "1", "exp": 9999999999}, key=None, algorithm="none")
    with pytest.raises(TokenError):
        decode_access_token(unsigned)


def test_random_junk_is_rejected():
    with pytest.raises(TokenError):
        decode_access_token("not-a-jwt")
