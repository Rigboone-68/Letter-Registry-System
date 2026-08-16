"""Tests for GET /api/v1/auth/me and the get_current_user dependency
(brief §15-16, §24 "Current User"/"Security")."""

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
    department = make_department(db_session, name="Tampered Token Department")
    user = make_user(db_session, department, email="tampered.user@example.gov")
    token = create_access_token(subject=user.id, role=user.role.value, department_id=user.department_id)

    header, payload, signature = token.split(".")
    tampered_signature = signature[:-1] + ("A" if signature[-1] != "A" else "B")
    tampered_token = f"{header}.{payload}.{tampered_signature}"

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
