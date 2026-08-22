"""Shared test data factories for the Phase 3A authentication tests.

Plain functions, not fixtures — call with the test's `db_session`. Kept
separate from tests/integration/test_models.py's own local factories
(added in Phase 2) to avoid touching that already-reviewed file for this
phase; the two are similar by design, not accidentally duplicated.
"""

from app.models.department import Department
from app.models.enums import ActiveStatus, AuthorizationStatus, UserRole, UserStatus
from app.models.user import User
from app.models.user_authorization import UserAuthorization


def make_department(db_session, name="Ministry of Testing", code=None, status=ActiveStatus.ACTIVE):
    department = Department(name=name, code=code, status=status)
    db_session.add(department)
    db_session.flush()
    return department


def make_user(
    db_session,
    department,
    role=UserRole.USER,
    email="user@example.gov",
    full_name="Test User",
    status=UserStatus.ACTIVE,
    password_hash="not-a-real-hash",
):
    user = User(
        full_name=full_name,
        email=email,
        password_hash=password_hash,
        role=role,
        department_id=department.id if department else None,
        status=status,
    )
    db_session.add(user)
    db_session.flush()
    return user


def make_authorization(
    db_session,
    department,
    authorized_by,
    email="new.hire@example.gov",
    status=AuthorizationStatus.ACTIVE,
    expires_at=None,
):
    authorization = UserAuthorization(
        email=email,
        department_id=department.id,
        authorized_by=authorized_by.id,
        status=status,
        expires_at=expires_at,
    )
    db_session.add(authorization)
    db_session.flush()
    return authorization
