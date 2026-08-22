"""Unit tests for the authorization primitives — app/services/authorization.py
and the role-check dependencies in app/api/deps.py.

Pure attribute checks on `User` objects, so these don't need a database:
the `User(...)` instances below are never added to a session or persisted.
`tests/integration/test_authorization.py` covers the same rules again
end-to-end, over real HTTP, with real database-backed Users and JWTs — see
that file's docstring for why both layers of testing exist.
"""

import uuid

import pytest
from fastapi import HTTPException

from app.api.deps import (
    require_admin,
    require_admin_or_system_admin,
    require_system_admin,
    require_user_or_admin,
)
from app.models.enums import UserRole
from app.models.user import User
from app.services.authorization import assert_department_access
from app.services.exceptions import DepartmentAccessDeniedError


def _make_user(role, department_id=None):
    return User(role=role, department_id=department_id)


# --- assert_department_access ---------------------------------------------


def test_system_admin_can_access_any_department():
    admin = _make_user(UserRole.SYSTEM_ADMIN, department_id=None)
    assert_department_access(admin, uuid.uuid4())  # must not raise


def test_system_admin_can_access_a_none_department_target():
    """SYSTEM_ADMIN's bypass is checked before any department_id
    comparison — must not crash on `None == None` or otherwise mishandle
    a caller with no department_id of their own (brief §8)."""
    admin = _make_user(UserRole.SYSTEM_ADMIN, department_id=None)
    assert_department_access(admin, None)  # must not raise


def test_admin_can_access_own_department():
    department_id = uuid.uuid4()
    admin = _make_user(UserRole.ADMIN, department_id=department_id)
    assert_department_access(admin, department_id)  # must not raise


def test_admin_cannot_access_other_department():
    admin = _make_user(UserRole.ADMIN, department_id=uuid.uuid4())
    with pytest.raises(DepartmentAccessDeniedError):
        assert_department_access(admin, uuid.uuid4())


def test_user_can_access_own_department():
    department_id = uuid.uuid4()
    user = _make_user(UserRole.USER, department_id=department_id)
    assert_department_access(user, department_id)  # must not raise


def test_user_cannot_access_other_department():
    user = _make_user(UserRole.USER, department_id=uuid.uuid4())
    with pytest.raises(DepartmentAccessDeniedError):
        assert_department_access(user, uuid.uuid4())


def test_admin_cannot_access_when_target_department_is_none():
    admin = _make_user(UserRole.ADMIN, department_id=uuid.uuid4())
    with pytest.raises(DepartmentAccessDeniedError):
        assert_department_access(admin, None)


# --- role dependencies, called directly (bypassing FastAPI's DI) ----------


def test_require_system_admin_accepts_system_admin():
    admin = _make_user(UserRole.SYSTEM_ADMIN)
    assert require_system_admin(current_user=admin) is admin


def test_require_system_admin_rejects_admin():
    admin = _make_user(UserRole.ADMIN, department_id=uuid.uuid4())
    with pytest.raises(HTTPException) as exc_info:
        require_system_admin(current_user=admin)
    assert exc_info.value.status_code == 403


def test_require_system_admin_rejects_user():
    user = _make_user(UserRole.USER, department_id=uuid.uuid4())
    with pytest.raises(HTTPException) as exc_info:
        require_system_admin(current_user=user)
    assert exc_info.value.status_code == 403


def test_require_admin_or_system_admin_accepts_system_admin():
    admin = _make_user(UserRole.SYSTEM_ADMIN)
    assert require_admin_or_system_admin(current_user=admin) is admin


def test_require_admin_or_system_admin_accepts_admin():
    admin = _make_user(UserRole.ADMIN, department_id=uuid.uuid4())
    assert require_admin_or_system_admin(current_user=admin) is admin


def test_require_admin_or_system_admin_rejects_user():
    user = _make_user(UserRole.USER, department_id=uuid.uuid4())
    with pytest.raises(HTTPException) as exc_info:
        require_admin_or_system_admin(current_user=user)
    assert exc_info.value.status_code == 403


def test_require_admin_rejects_system_admin():
    """require_admin is strict-ADMIN-only by design (brief §3's suggested
    structure lists it separately from require_admin_or_system_admin)."""
    admin = _make_user(UserRole.SYSTEM_ADMIN)
    with pytest.raises(HTTPException) as exc_info:
        require_admin(current_user=admin)
    assert exc_info.value.status_code == 403


def test_require_user_or_admin_accepts_user_and_admin_rejects_system_admin():
    user = _make_user(UserRole.USER, department_id=uuid.uuid4())
    admin = _make_user(UserRole.ADMIN, department_id=uuid.uuid4())
    system_admin = _make_user(UserRole.SYSTEM_ADMIN)

    assert require_user_or_admin(current_user=user) is user
    assert require_user_or_admin(current_user=admin) is admin
    with pytest.raises(HTTPException) as exc_info:
        require_user_or_admin(current_user=system_admin)
    assert exc_info.value.status_code == 403


def test_forbidden_response_does_not_name_a_role_or_department():
    """Error behavior (brief §12): the 403 detail must be generic — no
    role name, no department id, nothing an attacker could use to map out
    what would have been required."""
    user = _make_user(UserRole.USER, department_id=uuid.uuid4())
    with pytest.raises(HTTPException) as exc_info:
        require_system_admin(current_user=user)
    detail = str(exc_info.value.detail)
    assert "SYSTEM_ADMIN" not in detail
    assert "ADMIN" not in detail
