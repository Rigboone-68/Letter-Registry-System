"""Tests for bootstrapping the first System Admin (brief §8).

Calls app/services/bootstrap_service.py directly rather than going through
app/cli.py — the CLI module only gathers input (input()/getpass()) and
prints output; there is no HTTP endpoint for this operation at all (see
that module's docstring), so there is nothing for a `client` fixture to hit.
"""

import pytest

from app.core.security import verify_password
from app.models.enums import UserRole, UserStatus
from app.services.bootstrap_service import create_system_admin
from app.services.exceptions import InvalidPasswordError, SystemAdminAlreadyExistsError


def test_create_first_system_admin(db_session):
    admin = create_system_admin(
        db_session,
        full_name="Initial Admin",
        email="root.admin@example.gov",
        password="correct horse battery",
        password_confirm="correct horse battery",
    )
    assert admin.id is not None
    assert admin.email == "root.admin@example.gov"


def test_system_admin_has_no_department(db_session):
    admin = create_system_admin(
        db_session,
        full_name="Initial Admin",
        email="root.admin2@example.gov",
        password="correct horse battery",
        password_confirm="correct horse battery",
    )
    assert admin.department_id is None


def test_system_admin_is_active(db_session):
    admin = create_system_admin(
        db_session,
        full_name="Initial Admin",
        email="root.admin3@example.gov",
        password="correct horse battery",
        password_confirm="correct horse battery",
    )
    assert admin.status == UserStatus.ACTIVE


def test_system_admin_password_is_hashed(db_session):
    admin = create_system_admin(
        db_session,
        full_name="Initial Admin",
        email="root.admin4@example.gov",
        password="correct horse battery",
        password_confirm="correct horse battery",
    )
    assert admin.password_hash != "correct horse battery"
    assert admin.password_hash.startswith("$argon2id$")
    assert verify_password("correct horse battery", admin.password_hash)


def test_bootstrap_creates_system_admin_role_only(db_session):
    """The account bootstrap produces is SYSTEM_ADMIN, never ADMIN or USER —
    bootstrap has no path that could create either of those roles."""
    admin = create_system_admin(
        db_session,
        full_name="Initial Admin",
        email="root.admin5@example.gov",
        password="correct horse battery",
        password_confirm="correct horse battery",
    )
    assert admin.role == UserRole.SYSTEM_ADMIN
    assert admin.role not in (UserRole.ADMIN, UserRole.USER)


def test_duplicate_bootstrap_is_rejected(db_session):
    create_system_admin(
        db_session,
        full_name="First Admin",
        email="first.admin@example.gov",
        password="correct horse battery",
        password_confirm="correct horse battery",
    )
    with pytest.raises(SystemAdminAlreadyExistsError):
        create_system_admin(
            db_session,
            full_name="Second Admin",
            email="second.admin@example.gov",
            password="another good password",
            password_confirm="another good password",
        )


def test_bootstrap_rejects_password_below_policy(db_session):
    with pytest.raises(InvalidPasswordError):
        create_system_admin(
            db_session,
            full_name="Weak Password Admin",
            email="weak.admin@example.gov",
            password="short",
            password_confirm="short",
        )


def test_bootstrap_rejects_mismatched_password_confirmation(db_session):
    with pytest.raises(InvalidPasswordError):
        create_system_admin(
            db_session,
            full_name="Mismatch Admin",
            email="mismatch.admin@example.gov",
            password="correct horse battery",
            password_confirm="different horse battery",
        )


