"""Tests for POST /api/v1/auth/login (brief §14)."""

import jwt

from app.core.config import settings
from app.core.security import hash_password
from app.models.enums import UserRole, UserStatus
from tests.factories import make_department, make_user

LOGIN_URL = "/api/v1/auth/login"
PASSWORD = "correct horse battery staple"


def _make_login_ready_user(db_session, department, email, status=UserStatus.ACTIVE, role=UserRole.USER):
    return make_user(
        db_session,
        department,
        role=role,
        email=email,
        status=status,
        password_hash=hash_password(PASSWORD),
    )


def test_active_user_can_login(client, db_session):
    department = make_department(db_session, name="Login Success Department")
    _make_login_ready_user(db_session, department, "active.user@example.gov")

    response = client.post(LOGIN_URL, json={"email": "active.user@example.gov", "password": PASSWORD})

    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["user"]["email"] == "active.user@example.gov"
    assert body["user"]["status"] == "ACTIVE"
    assert "password_hash" not in body["user"]
    assert "password" not in body["user"]


def test_login_with_incorrect_password_is_rejected(client, db_session):
    department = make_department(db_session, name="Wrong Password Department")
    _make_login_ready_user(db_session, department, "wrong.pw@example.gov")

    response = client.post(LOGIN_URL, json={"email": "wrong.pw@example.gov", "password": "not the right password"})
    assert response.status_code == 401


def test_login_with_unknown_email_is_rejected(client, db_session):
    response = client.post(LOGIN_URL, json={"email": "never.registered@example.gov", "password": PASSWORD})
    assert response.status_code == 401


def test_login_unknown_email_and_wrong_password_return_identical_response(client, db_session):
    """No account-enumeration signal: both failure modes must be
    byte-identical from the client's point of view."""
    department = make_department(db_session, name="Enumeration Guard Department")
    _make_login_ready_user(db_session, department, "real.user@example.gov")

    unknown_response = client.post(
        LOGIN_URL, json={"email": "does.not.exist@example.gov", "password": PASSWORD}
    )
    wrong_password_response = client.post(
        LOGIN_URL, json={"email": "real.user@example.gov", "password": "incorrect"}
    )

    assert unknown_response.status_code == wrong_password_response.status_code == 401
    assert unknown_response.json() == wrong_password_response.json()


def test_pending_approval_user_is_rejected(client, db_session):
    department = make_department(db_session, name="Pending Login Department")
    _make_login_ready_user(
        db_session, department, "pending.user@example.gov", status=UserStatus.PENDING_APPROVAL
    )

    response = client.post(LOGIN_URL, json={"email": "pending.user@example.gov", "password": PASSWORD})
    assert response.status_code == 403
    assert "approval" in response.json()["detail"].lower()


def test_deactivated_user_is_rejected(client, db_session):
    department = make_department(db_session, name="Deactivated Login Department")
    _make_login_ready_user(
        db_session, department, "deactivated.user@example.gov", status=UserStatus.DEACTIVATED
    )

    response = client.post(
        LOGIN_URL, json={"email": "deactivated.user@example.gov", "password": PASSWORD}
    )
    assert response.status_code == 403
    assert "deactivated" in response.json()["detail"].lower()


def test_pending_and_deactivated_responses_are_distinguishable(client, db_session):
    department = make_department(db_session, name="Distinct Status Department")
    _make_login_ready_user(
        db_session, department, "pending.two@example.gov", status=UserStatus.PENDING_APPROVAL
    )
    _make_login_ready_user(
        db_session, department, "deactivated.two@example.gov", status=UserStatus.DEACTIVATED
    )

    pending_response = client.post(
        LOGIN_URL, json={"email": "pending.two@example.gov", "password": PASSWORD}
    )
    deactivated_response = client.post(
        LOGIN_URL, json={"email": "deactivated.two@example.gov", "password": PASSWORD}
    )

    assert pending_response.json()["detail"] != deactivated_response.json()["detail"]


def test_active_user_login_returns_jwt(client, db_session):
    department = make_department(db_session, name="JWT Issuance Department")
    _make_login_ready_user(db_session, department, "jwt.user@example.gov")

    response = client.post(LOGIN_URL, json={"email": "jwt.user@example.gov", "password": PASSWORD})

    body = response.json()
    assert "access_token" in body
    assert isinstance(body["access_token"], str) and len(body["access_token"]) > 0


def test_login_token_contains_correct_subject_and_claims(client, db_session):
    department = make_department(db_session, name="Claims Department")
    user = _make_login_ready_user(
        db_session, department, "claims.user@example.gov", role=UserRole.ADMIN
    )

    response = client.post(LOGIN_URL, json={"email": "claims.user@example.gov", "password": PASSWORD})
    token = response.json()["access_token"]

    payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    assert payload["sub"] == str(user.id)
    assert payload["role"] == "ADMIN"
    assert payload["department_id"] == str(department.id)
    assert "password" not in payload
    assert "password_hash" not in payload


def test_login_token_expiration_is_enforced(client, db_session):
    """The token carries a real, near-future `exp` derived from
    ACCESS_TOKEN_EXPIRE_MINUTES — full expiry-rejection behavior is
    exercised end-to-end by
    tests/unit/test_security.py::test_decode_access_token_rejects_expired_token
    and tests/integration/test_auth_current_user.py; this test only checks
    the claim shape the login endpoint actually issues."""
    department = make_department(db_session, name="Expiry Claim Department")
    _make_login_ready_user(db_session, department, "expiry.user@example.gov")

    response = client.post(LOGIN_URL, json={"email": "expiry.user@example.gov", "password": PASSWORD})
    payload = jwt.decode(
        response.json()["access_token"], settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
    )

    assert payload["exp"] - payload["iat"] == settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60


def test_login_rejects_invalid_email_format(client):
    response = client.post(LOGIN_URL, json={"email": "not-an-email", "password": PASSWORD})
    assert response.status_code == 422
