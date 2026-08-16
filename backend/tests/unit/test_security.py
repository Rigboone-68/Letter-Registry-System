"""Unit tests for password hashing, password policy, and JWT handling.

No database is needed for any of these — pure functions in
app/core/security.py.
"""

import time
import uuid

import jwt
import pytest

from app.core.security import (
    InvalidTokenError,
    create_access_token,
    decode_access_token,
    hash_password,
    validate_password_policy,
    verify_password,
)


# --- Password hashing --------------------------------------------------


def test_hash_password_produces_argon2id_hash():
    hashed = hash_password("correct horse battery staple")
    assert hashed.startswith("$argon2id$")


def test_hash_password_never_stores_plaintext():
    plaintext = "correct horse battery staple"
    hashed = hash_password(plaintext)
    assert plaintext not in hashed


def test_verify_password_accepts_correct_password():
    hashed = hash_password("correct horse battery staple")
    assert verify_password("correct horse battery staple", hashed) is True


def test_verify_password_rejects_incorrect_password():
    hashed = hash_password("correct horse battery staple")
    assert verify_password("wrong password", hashed) is False


def test_verify_password_rejects_garbage_hash_without_raising():
    assert verify_password("anything", "not-a-real-hash") is False


def test_hash_password_is_salted_and_nondeterministic():
    """Two hashes of the same password must differ (random salt per call) —
    otherwise identical passwords would produce identical stored hashes,
    which leaks information (e.g. two users sharing a password)."""
    first = hash_password("correct horse battery staple")
    second = hash_password("correct horse battery staple")
    assert first != second
    assert verify_password("correct horse battery staple", first)
    assert verify_password("correct horse battery staple", second)


# --- Password policy -----------------------------------------------------


def test_password_policy_rejects_empty_password():
    with pytest.raises(ValueError):
        validate_password_policy("")


def test_password_policy_rejects_too_short_password():
    with pytest.raises(ValueError):
        validate_password_policy("short1")


def test_password_policy_accepts_minimum_length_password():
    validate_password_policy("12345678")  # exactly 8 chars — must not raise


def test_password_policy_rejects_excessively_long_password():
    with pytest.raises(ValueError):
        validate_password_policy("a" * 129)


def test_password_policy_accepts_maximum_length_password():
    validate_password_policy("a" * 128)  # must not raise


# --- JWT -------------------------------------------------------------------


def test_create_access_token_round_trips_claims():
    user_id = uuid.uuid4()
    department_id = uuid.uuid4()
    token = create_access_token(subject=user_id, role="ADMIN", department_id=department_id)

    payload = decode_access_token(token)
    assert payload["sub"] == str(user_id)
    assert payload["role"] == "ADMIN"
    assert payload["department_id"] == str(department_id)
    assert "iat" in payload
    assert "exp" in payload


def test_create_access_token_allows_null_department_for_system_admin():
    token = create_access_token(subject=uuid.uuid4(), role="SYSTEM_ADMIN", department_id=None)
    payload = decode_access_token(token)
    assert payload["department_id"] is None


def test_token_payload_never_contains_password_fields():
    token = create_access_token(subject=uuid.uuid4(), role="USER", department_id=uuid.uuid4())
    payload = decode_access_token(token)
    assert "password" not in payload
    assert "password_hash" not in payload


def test_decode_access_token_rejects_malformed_token():
    with pytest.raises(InvalidTokenError):
        decode_access_token("not.a.jwt")


def test_decode_access_token_rejects_tampered_signature():
    token = create_access_token(subject=uuid.uuid4(), role="USER", department_id=None)
    # Flip the last character of the signature segment.
    header, payload, signature = token.split(".")
    tampered_signature = signature[:-1] + ("A" if signature[-1] != "A" else "B")
    tampered_token = f"{header}.{payload}.{tampered_signature}"

    with pytest.raises(InvalidTokenError):
        decode_access_token(tampered_token)


def test_decode_access_token_rejects_expired_token():
    from app.core.config import settings

    now = int(time.time())
    expired_payload = {
        "sub": str(uuid.uuid4()),
        "role": "USER",
        "department_id": None,
        "iat": now - 7200,
        "exp": now - 3600,  # expired one hour ago
    }
    expired_token = jwt.encode(expired_payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

    with pytest.raises(InvalidTokenError):
        decode_access_token(expired_token)


def test_decode_access_token_rejects_alg_none_token():
    """Guards against the classic JWT "alg: none" attack: a token whose
    header claims no signature is required must still be rejected, because
    decode_access_token always passes an explicit algorithms= allow-list
    rather than trusting the token's own header."""
    import base64
    import json

    header = base64.urlsafe_b64encode(json.dumps({"alg": "none", "typ": "JWT"}).encode()).rstrip(b"=")
    payload = base64.urlsafe_b64encode(
        json.dumps({"sub": str(uuid.uuid4()), "role": "SYSTEM_ADMIN", "department_id": None}).encode()
    ).rstrip(b"=")
    none_alg_token = (header + b"." + payload + b".").decode()

    with pytest.raises(InvalidTokenError):
        decode_access_token(none_alg_token)
