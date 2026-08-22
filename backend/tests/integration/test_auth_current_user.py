"""Tests for GET /api/v1/auth/me and the get_current_user dependency
(brief §15-16, §24 "Current User"/"Security")."""

import base64
import uuid
from datetime import datetime, timedelta, timezone

import jwt

from app.core.config import settings
from app.core.security import create_access_token, hash_password
from app.models.enums import UserStatus
from tests.factories import make_department, make_user

ME_URL = "/api/v1/auth/me"
PASSWORD = "correct horse battery staple"


def _auth_header(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _tamper_signature(token: str) -> str:
    """Flip one real signature byte and re-encode — deterministic, unlike
    flipping the last base64 *character* of the signature string (see
    test_me_with_tampered_token_is_rejected's docstring for why that
    approach was flaky, not a production bug)."""
    header, payload, signature = token.split(".")
    padded = signature + "=" * (-len(signature) % 4)
    raw = bytearray(base64.urlsafe_b64decode(padded))
    raw[0] ^= 0xFF
    tampered_signature = base64.urlsafe_b64encode(bytes(raw)).rstrip(b"=").decode()
    return f"{header}.{payload}.{tampered_signature}"


def test_me_returns_correct_user_for_valid_token(client, db_session):
    department = make_department(db_session, name="Me Endpoint Department")
    user = make_user(
        db_session,
        department,
        email="me.user@example.gov",
        status=UserStatus.ACTIVE,
        password_hash=hash_password(PASSWORD),
    )
    token = create_access_token(subject=user.id, role=user.role.value, department_id=user.department_id)

    response = client.get(ME_URL, headers=_auth_header(token))

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == str(user.id)
    assert body["email"] == "me.user@example.gov"
    assert body["role"] == "USER"
    assert body["department_id"] == str(department.id)
    assert body["status"] == "ACTIVE"


def test_me_never_returns_password_hash(client, db_session):
    department = make_department(db_session, name="No Hash Leak Department")
    user = make_user(
        db_session,
        department,
        email="nohash.user@example.gov",
        password_hash=hash_password(PASSWORD),
    )
    token = create_access_token(subject=user.id, role=user.role.value, department_id=user.department_id)

    response = client.get(ME_URL, headers=_auth_header(token))

    assert "password_hash" not in response.json()
    assert "password" not in response.json()


def test_me_without_authorization_header_is_rejected(client, db_session):
    response = client.get(ME_URL)
    assert response.status_code in (401, 403)  # FastAPI's HTTPBearer default is 403 when missing


def test_me_with_malformed_bearer_token_is_rejected(client, db_session):
    response = client.get(ME_URL, headers={"Authorization": "Bearer not-a-real-jwt"})
    assert response.status_code == 401


def test_me_with_non_bearer_scheme_is_rejected(client, db_session):
    department = make_department(db_session, name="Wrong Scheme Department")
    user = make_user(db_session, department, email="scheme.user@example.gov")
    token = create_access_token(subject=user.id, role=user.role.value, department_id=user.department_id)

    response = client.get(ME_URL, headers={"Authorization": f"Basic {token}"})
    assert response.status_code in (401, 403)


def test_me_with_tampered_token_is_rejected(client, db_session):
    """Root cause of the flaky version of this test (found during a Phase
    3B.4 hardening pass, ~6% failure rate reproduced empirically): the
    original technique flipped the *last base64 character* of the
    signature to a fixed value ('A', or 'B' if already 'A'). A 32-byte
    HMAC-SHA256 signature's final base64 character encodes only 4 real
    bits plus 2 discarded padding bits (32 % 3 == 2, an incomplete final
    byte group) — and 'A' (000000) vs. 'B' (000001) differ only in the
    last of those 6 bits, which is exactly one of the 2 discarded ones.
    So whenever the signature's real last-4-bits already happened to be
    0000 (1/16 of random signatures — i.e. the last char was already
    'A'), the "tamper to B" fallback silently produced a *byte-identical*
    signature, and the server correctly (and securely) accepted it. This
    was a test-construction bug, not a JWT/signature-verification
    weakness — `app/core/security.py:decode_access_token` never changed
    and its real-bit-flip variant (`_tamper_signature`, this module) is
    rejected 401 in 5,000/5,000 empirical trials. See
    `docs/PROJECT_STATUS.md`, "Known Limitations" for the record of this
    fix."""
    department = make_department(db_session, name="Tampered Token Department")
    user = make_user(db_session, department, email="tampered.user@example.gov")
    token = create_access_token(subject=user.id, role=user.role.value, department_id=user.department_id)

    tampered_token = _tamper_signature(token)

    response = client.get(ME_URL, headers=_auth_header(tampered_token))
    assert response.status_code == 401


def test_me_with_expired_token_is_rejected(client, db_session):
    department = make_department(db_session, name="Expired Token Department")
    user = make_user(db_session, department, email="expired.token.user@example.gov")

    now = datetime.now(timezone.utc)
    expired_payload = {
        "sub": str(user.id),
        "role": user.role.value,
        "department_id": str(department.id),
        "iat": int((now - timedelta(hours=2)).timestamp()),
        "exp": int((now - timedelta(hours=1)).timestamp()),
    }
    expired_token = jwt.encode(expired_payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

    response = client.get(ME_URL, headers=_auth_header(expired_token))
    assert response.status_code == 401


def test_me_with_token_for_nonexistent_user_is_rejected(client, db_session):
    token = create_access_token(subject=uuid.uuid4(), role="USER", department_id=None)
    response = client.get(ME_URL, headers=_auth_header(token))
    assert response.status_code == 401


def test_me_rejected_after_user_is_deactivated(client, db_session):
    """A token issued while the user was ACTIVE must stop working the
    moment the account is deactivated — the dependency re-checks status
    against the database on every request rather than trusting the token's
    claims (brief §15, step 6)."""
    department = make_department(db_session, name="Deactivation Department")
    user = make_user(
        db_session, department, email="deactivate.me@example.gov", status=UserStatus.ACTIVE
    )
    token = create_access_token(subject=user.id, role=user.role.value, department_id=user.department_id)

    first_response = client.get(ME_URL, headers=_auth_header(token))
    assert first_response.status_code == 200

    user.status = UserStatus.DEACTIVATED
    db_session.flush()

    second_response = client.get(ME_URL, headers=_auth_header(token))
    assert second_response.status_code == 401


def test_me_rejected_for_pending_approval_user(client, db_session):
    department = make_department(db_session, name="Pending Token Department")
    user = make_user(
        db_session,
        department,
        email="pending.token.user@example.gov",
        status=UserStatus.PENDING_APPROVAL,
    )
    token = create_access_token(subject=user.id, role=user.role.value, department_id=user.department_id)

    response = client.get(ME_URL, headers=_auth_header(token))
    assert response.status_code == 401
