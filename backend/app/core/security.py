"""Centralized security primitives: password hashing and JWT handling.

This is the single place password hashing and token logic live, per the
Phase 1 placeholder this module replaces — no other layer should import
`argon2`/`jwt` directly or reimplement any of this.

Password hashing: Argon2id via `argon2-cffi`'s `PasswordHasher`, used
directly rather than through `passlib` (whose argon2 backend integration has
a history of version-pinning friction with `argon2-cffi` itself — using the
library directly avoids that indirection). `argon2-cffi`'s default profile
is Argon2id, the variant requested for this project. Verification always
goes through the library (`PasswordHasher.verify`), never a manual
string/hash comparison.

JWT: PyJWT, not python-jose (informally sketched as a placeholder in
`requirements.txt` before this phase) — python-jose has had an
algorithm-confusion vulnerability (CVE-2024-33663) and slower maintenance;
PyJWT is actively maintained. Only HS256 (symmetric, `SECRET_KEY`-based) is
used, and `algorithms=` is always passed explicitly on decode — the token's
own header is never trusted to select the algorithm, which is what prevents
algorithm-confusion attacks in the first place.
"""

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHash, VerifyMismatchError

from app.core.config import settings

# --- Password hashing ----------------------------------------------------

_password_hasher = PasswordHasher()

# V1 password policy (brief §6): documented here, enforced from exactly one
# place (`validate_password_policy`) called by both the signup schema
# (app/schemas/auth.py) and the bootstrap CLI (app/services/bootstrap_service.py)
# — the only two places a plaintext password is ever accepted.
MIN_PASSWORD_LENGTH = 8
# Caps hashing cost (Argon2's work scales with input size) and guards
# against pathological oversized submissions; not a "complexity" rule.
MAX_PASSWORD_LENGTH = 128


def hash_password(password: str) -> str:
    """Hash a plaintext password. The result is safe to store; the input
    never is."""
    return _password_hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    """Verify a plaintext password against a stored hash via the hashing
    library itself — never a manual string comparison."""
    try:
        return _password_hasher.verify(password_hash, password)
    except (VerifyMismatchError, InvalidHash):
        return False


def validate_password_policy(password: str) -> None:
    """Raise ValueError with a human-readable reason if `password` doesn't
    meet the V1 policy. Deliberately minimal — see module docstring."""
    if not password:
        raise ValueError("Password must not be empty.")
    if len(password) < MIN_PASSWORD_LENGTH:
        raise ValueError(f"Password must be at least {MIN_PASSWORD_LENGTH} characters.")
    if len(password) > MAX_PASSWORD_LENGTH:
        raise ValueError(f"Password must be at most {MAX_PASSWORD_LENGTH} characters.")


# --- JWT -------------------------------------------------------------------


class InvalidTokenError(Exception):
    """Raised for any token that is missing, malformed, expired, or has an
    invalid signature. Deliberately does not distinguish which — callers
    (see app/api/deps.py) should treat this as "not authenticated"."""


def _require_secret_key() -> str:
    # Mirrors the lazy-check pattern already established in
    # app/database/session.py:get_engine() for DATABASE_URL — fail loudly,
    # only when a token operation is actually attempted, not at import time.
    if not settings.SECRET_KEY:
        raise RuntimeError(
            "SECRET_KEY is not configured. Copy backend/.env.example to "
            "backend/.env and set a generated secret before using "
            "authentication."
        )
    return settings.SECRET_KEY


def create_access_token(
    *,
    subject: uuid.UUID,
    role: str,
    department_id: Optional[uuid.UUID],
) -> str:
    """Create a signed JWT access token.

    Payload intentionally holds only what a future authorization check
    needs (`sub`, `role`, `department_id`) plus standard timing claims —
    never the password hash or any other sensitive data.
    """
    secret_key = _require_secret_key()
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {
        "sub": str(subject),
        "role": role,
        "department_id": str(department_id) if department_id is not None else None,
        "iat": int(now.timestamp()),
        "exp": int(expires_at.timestamp()),
    }
    return jwt.encode(payload, secret_key, algorithm=settings.ALGORITHM)


def decode_access_token(token: str) -> Dict[str, Any]:
    """Decode and verify a JWT access token, raising `InvalidTokenError` for
    any failure (bad signature, expired, malformed). The algorithm allow-list
    is always passed explicitly — the token's own header never selects it."""
    secret_key = _require_secret_key()
    try:
        return jwt.decode(token, secret_key, algorithms=[settings.ALGORITHM])
    except jwt.PyJWTError as exc:
        raise InvalidTokenError(str(exc)) from exc
