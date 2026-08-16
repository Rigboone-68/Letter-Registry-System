"""Tests for POST /api/v1/auth/signup (brief §10-13).

Uses the `client` fixture (a TestClient sharing this test's `db_session` —
see tests/conftest.py) so an HTTP call and a direct ORM assertion afterward
see the same in-progress, later-rolled-back transaction.
"""

import threading
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models.department import Department
from app.models.enums import AuthorizationStatus, UserRole, UserStatus
from app.models.user import User
from app.models.user_authorization import UserAuthorization
from app.services.auth_service import AuthService
from app.services.exceptions import SignupNotAuthorizedError
from tests.conftest import TEST_DATABASE_URL
from tests.factories import make_authorization, make_department, make_user

VALID_PASSWORD = "correct horse battery staple"

SIGNUP_URL = "/api/v1/auth/signup"


def _signup_payload(email, password=VALID_PASSWORD, full_name="New Hire"):
    return {
        "full_name": full_name,
        "email": email,
        "password": password,
        "password_confirm": password,
    }


def _make_admin_authorizer(db_session, department):
    return make_user(
        db_session, department, role=UserRole.ADMIN, email="authorizer.admin@example.gov"
    )


# --- Happy path --------------------------------------------------------


def test_signup_with_valid_authorization_succeeds(client, db_session):
    department = make_department(db_session, name="Signup Success Department")
    admin = _make_admin_authorizer(db_session, department)
    make_authorization(db_session, department, admin, email="authorized.hire@example.gov")

    response = client.post(SIGNUP_URL, json=_signup_payload("authorized.hire@example.gov"))

    assert response.status_code == 201
    body = response.json()
    assert body["email"] == "authorized.hire@example.gov"
    assert body["status"] == "PENDING_APPROVAL"
    assert body["role"] == "USER"
    assert body["department_id"] == str(department.id)
    assert "password_hash" not in body
    assert "password" not in body


def test_signup_creates_user_as_pending_approval(client, db_session):
    department = make_department(db_session, name="Pending Status Department")
    admin = _make_admin_authorizer(db_session, department)
    make_authorization(db_session, department, admin, email="pending.hire@example.gov")

    client.post(SIGNUP_URL, json=_signup_payload("pending.hire@example.gov"))

    created = db_session.query(User).filter(User.email == "pending.hire@example.gov").one()
    assert created.status == UserStatus.PENDING_APPROVAL


def test_signup_grants_user_role_regardless_of_input(client, db_session):
    department = make_department(db_session, name="Role Injection Department")
    admin = _make_admin_authorizer(db_session, department)
    make_authorization(db_session, department, admin, email="role.hire@example.gov")

    payload = _signup_payload("role.hire@example.gov")
    payload["role"] = "SYSTEM_ADMIN"  # not a field on SignupRequest — must be rejected/ignored

    response = client.post(SIGNUP_URL, json=payload)

    assert response.status_code == 422  # extra="forbid" rejects the whole request
    assert (
        db_session.query(User).filter(User.email == "role.hire@example.gov").one_or_none() is None
    )


def test_signup_grants_authorization_department_regardless_of_input(client, db_session):
    real_department = make_department(db_session, name="Real Department")
    other_department = make_department(db_session, name="Other Department")
    admin = _make_admin_authorizer(db_session, real_department)
    make_authorization(db_session, real_department, admin, email="dept.hire@example.gov")

    payload = _signup_payload("dept.hire@example.gov")
    payload["department_id"] = str(other_department.id)  # not a field on SignupRequest

    response = client.post(SIGNUP_URL, json=payload)

    assert response.status_code == 422
    assert (
        db_session.query(User).filter(User.email == "dept.hire@example.gov").one_or_none() is None
    )


def test_signup_cannot_set_status(client, db_session):
    department = make_department(db_session, name="Status Injection Department")
    admin = _make_admin_authorizer(db_session, department)
    make_authorization(db_session, department, admin, email="status.hire@example.gov")

    payload = _signup_payload("status.hire@example.gov")
    payload["status"] = "ACTIVE"  # not a field on SignupRequest

    response = client.post(SIGNUP_URL, json=payload)

    assert response.status_code == 422
    assert (
        db_session.query(User).filter(User.email == "status.hire@example.gov").one_or_none()
        is None
    )


def test_signup_marks_authorization_as_used(client, db_session):
    department = make_department(db_session, name="Consumption Department")
    admin = _make_admin_authorizer(db_session, department)
    authorization = make_authorization(
        db_session, department, admin, email="consumed.hire@example.gov"
    )

    client.post(SIGNUP_URL, json=_signup_payload("consumed.hire@example.gov"))

    db_session.refresh(authorization)
    assert authorization.status == AuthorizationStatus.USED


# --- Rejections ------------------------------------------------------------


def test_signup_with_unauthorized_email_is_rejected(client, db_session):
    response = client.post(SIGNUP_URL, json=_signup_payload("never.authorized@example.gov"))
    assert response.status_code == 403
    assert (
        db_session.query(User)
        .filter(User.email == "never.authorized@example.gov")
        .one_or_none()
        is None
    )


def test_signup_with_expired_authorization_is_rejected(client, db_session):
    department = make_department(db_session, name="Expired Auth Department")
    admin = _make_admin_authorizer(db_session, department)
    make_authorization(
        db_session,
        department,
        admin,
        email="expired.hire@example.gov",
        expires_at=datetime.now(timezone.utc) - timedelta(days=1),
    )

    response = client.post(SIGNUP_URL, json=_signup_payload("expired.hire@example.gov"))
    assert response.status_code == 403


def test_signup_with_revoked_authorization_is_rejected(client, db_session):
    department = make_department(db_session, name="Revoked Auth Department")
    admin = _make_admin_authorizer(db_session, department)
    make_authorization(
        db_session,
        department,
        admin,
        email="revoked.hire@example.gov",
        status=AuthorizationStatus.REVOKED,
    )

    response = client.post(SIGNUP_URL, json=_signup_payload("revoked.hire@example.gov"))
    assert response.status_code == 403


def test_signup_with_already_used_authorization_is_rejected(client, db_session):
    department = make_department(db_session, name="Used Auth Department")
    admin = _make_admin_authorizer(db_session, department)
    make_authorization(
        db_session,
        department,
        admin,
        email="used.hire@example.gov",
        status=AuthorizationStatus.USED,
    )

    response = client.post(SIGNUP_URL, json=_signup_payload("used.hire@example.gov"))
    assert response.status_code == 403


def test_signup_with_non_expiring_authorization_succeeds(client, db_session):
    """expires_at IS NULL means "never expires" — the absence of a value
    must not be mistaken for "already expired"."""
    department = make_department(db_session, name="No Expiry Department")
    admin = _make_admin_authorizer(db_session, department)
    make_authorization(
        db_session, department, admin, email="no.expiry.hire@example.gov", expires_at=None
    )

    response = client.post(SIGNUP_URL, json=_signup_payload("no.expiry.hire@example.gov"))
    assert response.status_code == 201


def test_signup_with_duplicate_email_is_rejected(client, db_session):
    department = make_department(db_session, name="Duplicate Email Department")
    make_user(db_session, department, email="already.exists@example.gov")
    admin = _make_admin_authorizer(db_session, department)
    make_authorization(db_session, department, admin, email="already.exists@example.gov")

    response = client.post(SIGNUP_URL, json=_signup_payload("already.exists@example.gov"))
    assert response.status_code == 409


def test_signup_with_password_below_policy_is_rejected(client, db_session):
    department = make_department(db_session, name="Weak Password Department")
    admin = _make_admin_authorizer(db_session, department)
    make_authorization(db_session, department, admin, email="weak.password@example.gov")

    response = client.post(
        SIGNUP_URL, json=_signup_payload("weak.password@example.gov", password="short")
    )
    assert response.status_code == 422


def test_signup_with_mismatched_password_confirmation_is_rejected(client, db_session):
    department = make_department(db_session, name="Mismatch Department")
    admin = _make_admin_authorizer(db_session, department)
    make_authorization(db_session, department, admin, email="mismatch.hire@example.gov")

    payload = _signup_payload("mismatch.hire@example.gov")
    payload["password_confirm"] = "a different password entirely"

    response = client.post(SIGNUP_URL, json=payload)
    assert response.status_code == 422


# --- Race condition (brief §13) ---------------------------------------------


def test_concurrent_signup_attempts_consume_authorization_exactly_once():
    """Two threads racing to sign up with the SAME authorization must not
    both succeed. Uses two independent engines/sessions (not the shared
    `db_session` fixture) because genuine concurrency requires two real,
    separate connections/transactions — the fixture's single rolled-back
    transaction can't model that. Creates and cleans up its own data
    directly against lrs_test."""
    engine = create_engine(TEST_DATABASE_URL, future=True)
    SessionLocal = sessionmaker(bind=engine, future=True, expire_on_commit=False)

    setup_session = SessionLocal()
    department = make_department(setup_session, name=f"Race Department {uuid.uuid4()}")
    admin = _make_admin_authorizer(setup_session, department)
    email = f"race.hire.{uuid.uuid4()}@example.gov"
    make_authorization(setup_session, department, admin, email=email)
    setup_session.commit()
    department_id, admin_id = department.id, admin.id
    setup_session.close()

    results = []
    barrier = threading.Barrier(2)

    def attempt_signup():
        session = SessionLocal()
        try:
            barrier.wait(timeout=5)  # maximize the chance both threads race together
            service = AuthService(session)
            try:
                service.signup(full_name="Racer", email=email, password=VALID_PASSWORD)
                results.append("success")
            except SignupNotAuthorizedError:
                results.append("rejected")
        finally:
            session.close()

    threads = [threading.Thread(target=attempt_signup) for _ in range(2)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=10)

    # Clean up first (this test writes real, committed rows to lrs_test),
    # then assert — so a failed assertion never leaves stray data behind.
    cleanup_session = SessionLocal()
    try:
        user_count = cleanup_session.query(User).filter(User.email == email).count()
        cleanup_session.query(User).filter(User.email == email).delete()
        cleanup_session.query(UserAuthorization).filter(
            UserAuthorization.email == email
        ).delete()
        cleanup_session.query(User).filter(User.id == admin_id).delete()
        cleanup_session.query(Department).filter(Department.id == department_id).delete()
        cleanup_session.commit()
    finally:
        cleanup_session.close()
        engine.dispose()

    assert sorted(results) == ["rejected", "success"]
    assert user_count == 1, "exactly one User must have been created"
