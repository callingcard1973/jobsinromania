#!/usr/bin/env python3
import pytest
import os
from datetime import timedelta

os.environ["SECRET_KEY"] = "test_secret_key_32_chars_minimum_length"
os.environ["ALGORITHM"] = "HS256"
os.environ["ACCESS_TOKEN_EXPIRE_MINUTES"] = "30"

from app.core.security import verify_password, get_password_hash, create_access_token, decode_access_token
from app.core.config import get_settings


def test_password_hashing():
    plain = "test_password_123"
    hashed = get_password_hash(plain)
    assert hashed != plain
    assert verify_password(plain, hashed)
    assert not verify_password("wrong_password", hashed)


def test_password_hash_different():
    plain = "same_password"
    hash1 = get_password_hash(plain)
    hash2 = get_password_hash(plain)
    assert hash1 != hash2


def test_create_access_token():
    data = {"sub": "1"}
    token = create_access_token(data)
    assert token is not None
    assert isinstance(token, str)


def test_create_token_with_expiry():
    data = {"sub": "2"}
    expires = timedelta(minutes=60)
    token = create_access_token(data, expires_delta=expires)
    assert token is not None


def test_decode_valid_token():
    data = {"sub": "123"}
    token = create_access_token(data)
    payload = decode_access_token(token)
    assert payload is not None
    assert payload.get("sub") == "123"


def test_decode_expired_token():
    data = {"sub": "456"}
    expires = timedelta(seconds=-1)
    token = create_access_token(data, expires_delta=expires)
    payload = decode_access_token(token)
    assert payload is None


def test_decode_invalid_token():
    invalid_token = "invalid.token.here"
    payload = decode_access_token(invalid_token)
    assert payload is None


def test_settings_secret_key_validation():
    from app.core.config import Settings

    with pytest.raises(ValueError, match="secret_key must be set"):
        Settings(secret_key="")

    with pytest.raises(ValueError, match="secret_key must be set"):
        Settings(secret_key="your-secret-key-change-in-production")

    with pytest.raises(ValueError, match="at least 32 characters"):
        Settings(secret_key="short_key")


def test_settings_algorithm_validation():
    from app.core.config import Settings

    with pytest.raises(ValueError, match="algorithm must be"):
        Settings(secret_key="x" * 32, algorithm="RS512")


def test_settings_expiry_validation():
    from app.core.config import Settings

    with pytest.raises(ValueError, match="access_token_expire_minutes must be > 0"):
        Settings(secret_key="x" * 32, access_token_expire_minutes=0)

    with pytest.raises(ValueError, match="access_token_expire_minutes must be > 0"):
        Settings(secret_key="x" * 32, access_token_expire_minutes=-1)
