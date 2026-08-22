"""End-to-end authorization tests: real JWTs, real database-backed Users,
real HTTP requests through the protected dev/test endpoints in
app/api/v1/endpoints/dev_authz_test.py (brief §10, §11).

tests/unit/test_authorization.py already covers the same rules as pure
function calls, quickly and exhaustively. This file exists because the
brief explicitly requires proof "using real database-backed Users" through
the actual dependency chain (JWT → get_current_user → role/department
check) rather than only unit-level mocks — a passing unit test proves the
logic is right in isolation, not that it's correctly wired into the API.
"""

from app.core.security import create_access_token
from app.models.enums import UserRole, UserStatus
from tests.factories import make_department, make_user

SYSTEM_ADMIN_URL = "/api/v1/auth/test/system-admin"
ADMIN_URL = "/api/v1/auth/test/admin"
ADMIN_OR_SYSTEM_ADMIN_URL = "/api/v1/auth/test/admin-or-system-admin"
USER_OR_ADMIN_URL = "/api/v1/auth/test/user-or-admin"


def _department_url(department_id) -> str:
    return f"/api/v1/auth/test/department/{department_id}"


def _token_for(user) -> str:
    return create_access_token(subject=user.id, role=user.role.value, department_id=user.department_id)


def _auth_headers(user) -> dict:
    return {"Authorization": f"Bearer {_token_for(user)}"}


def _make_system_admin(db_session, email="sys.admin@example.gov"):
    return make_user(db_session, department=None, role=UserRole.SYSTEM_ADMIN, email=email)


# =========================================================================
# ROLE TESTS (brief §10)
# =========================================================================


def test_system_admin_satisfies_require_system_admin(client, db_session):
    admin = _make_system_admin(db_session)
    response = client.get(SYSTEM_ADMIN_URL, headers=_auth_headers(admin))
    assert response.status_code == 200


def test_admin_does_not_satisfy_require_system_admin(client, db_session):
    department = make_department(db_session, name="Role Test Dept A")
    admin = make_user(db_session, department, role=UserRole.ADMIN, email="admin.a@example.gov")
    response = client.get(SYSTEM_ADMIN_URL, headers=_auth_headers(admin))
    assert response.status_code == 403


def test_user_does_not_satisfy_require_system_admin(client, db_session):
    department = make_department(db_session, name="Role Test Dept B")
    user = make_user(db_session, department, role=UserRole.USER, email="user.b@example.gov")
    response = client.get(SYSTEM_ADMIN_URL, headers=_auth_headers(user))
    assert response.status_code == 403


def test_system_admin_satisfies_admin_or_system_admin(client, db_session):
    admin = _make_system_admin(db_session, email="sys.admin2@example.gov")
    response = client.get(ADMIN_OR_SYSTEM_ADMIN_URL, headers=_auth_headers(admin))
    assert response.status_code == 200


def test_admin_satisfies_admin_or_system_admin(client, db_session):
    department = make_department(db_session, name="Role Test Dept C")
    admin = make_user(db_session, department, role=UserRole.ADMIN, email="admin.c@example.gov")
    response = client.get(ADMIN_OR_SYSTEM_ADMIN_URL, headers=_auth_headers(admin))
    assert response.status_code == 200


def test_user_does_not_satisfy_admin_or_system_admin(client, db_session):
    department = make_department(db_session, name="Role Test Dept D")
    user = make_user(db_session, department, role=UserRole.USER, email="user.d@example.gov")
    response = client.get(ADMIN_OR_SYSTEM_ADMIN_URL, headers=_auth_headers(user))
    assert response.status_code == 403


def test_user_satisfies_user_or_admin(client, db_session):
    department = make_department(db_session, name="Role Test Dept E")
    user = make_user(db_session, department, role=UserRole.USER, email="user.e@example.gov")
    response = client.get(USER_OR_ADMIN_URL, headers=_auth_headers(user))
    assert response.status_code == 200


def test_system_admin_does_not_satisfy_user_or_admin(client, db_session):
    admin = _make_system_admin(db_session, email="sys.admin3@example.gov")
    response = client.get(USER_OR_ADMIN_URL, headers=_auth_headers(admin))
    assert response.status_code == 403


# =========================================================================
# DEPARTMENT TESTS (brief §10)
# =========================================================================


def test_system_admin_can_access_department_a(client, db_session):
    department_a = make_department(db_session, name="Department A")
    admin = _make_system_admin(db_session, email="sys.admin4@example.gov")
    response = client.get(_department_url(department_a.id), headers=_auth_headers(admin))
    assert response.status_code == 200


def test_system_admin_can_access_department_b(client, db_session):
    department_b = make_department(db_session, name="Department B")
    admin = _make_system_admin(db_session, email="sys.admin5@example.gov")
    response = client.get(_department_url(department_b.id), headers=_auth_headers(admin))
    assert response.status_code == 200


def test_admin_in_department_a_can_access_department_a(client, db_session):
    department_a = make_department(db_session, name="Department A2")
    admin = make_user(db_session, department_a, role=UserRole.ADMIN, email="admin.a2@example.gov")
    response = client.get(_department_url(department_a.id), headers=_auth_headers(admin))
    assert response.status_code == 200


def test_admin_in_department_a_cannot_access_department_b(client, db_session):
    department_a = make_department(db_session, name="Department A3")
    department_b = make_department(db_session, name="Department B3")
    admin = make_user(db_session, department_a, role=UserRole.ADMIN, email="admin.a3@example.gov")
    response = client.get(_department_url(department_b.id), headers=_auth_headers(admin))
    assert response.status_code == 403


def test_user_in_department_a_can_access_department_a(client, db_session):
    department_a = make_department(db_session, name="Department A4")
    user = make_user(db_session, department_a, role=UserRole.USER, email="user.a4@example.gov")
    response = client.get(_department_url(department_a.id), headers=_auth_headers(user))
    assert response.status_code == 200


def test_user_in_department_a_cannot_access_department_b(client, db_session):
    department_a = make_department(db_session, name="Department A5")
    department_b = make_department(db_session, name="Department B5")
    user = make_user(db_session, department_a, role=UserRole.USER, email="user.a5@example.gov")
    response = client.get(_department_url(department_b.id), headers=_auth_headers(user))
    assert response.status_code == 403


# =========================================================================
# DEACTIVATION TESTS (brief §10)
# =========================================================================


def test_deactivated_admin_cannot_pass_authorization(client, db_session):
    department = make_department(db_session, name="Deactivation Dept Admin")
    admin = make_user(
        db_session, department, role=UserRole.ADMIN, email="deactivated.admin@example.gov",
        status=UserStatus.DEACTIVATED,
    )
    response = client.get(ADMIN_URL, headers=_auth_headers(admin))
    assert response.status_code == 401


def test_deactivated_user_cannot_pass_authorization(client, db_session):
    department = make_department(db_session, name="Deactivation Dept User")
    user = make_user(
        db_session, department, role=UserRole.USER, email="deactivated.user@example.gov",
        status=UserStatus.DEACTIVATED,
    )
    response = client.get(USER_OR_ADMIN_URL, headers=_auth_headers(user))
    assert response.status_code == 401


def test_deactivated_system_admin_cannot_pass_authorization(client, db_session):
    admin = make_user(
        db_session, department=None, role=UserRole.SYSTEM_ADMIN,
        email="deactivated.sysadmin@example.gov", status=UserStatus.DEACTIVATED,
    )
    response = client.get(SYSTEM_ADMIN_URL, headers=_auth_headers(admin))
    assert response.status_code == 401


def test_pending_approval_user_cannot_pass_authorization(client, db_session):
    department = make_department(db_session, name="Pending Dept")
    user = make_user(
        db_session, department, role=UserRole.USER, email="pending.user@example.gov",
        status=UserStatus.PENDING_APPROVAL,
    )
    response = client.get(USER_OR_ADMIN_URL, headers=_auth_headers(user))
    assert response.status_code == 401


# =========================================================================
# NEGATIVE SECURITY TESTS (brief §11)
# =========================================================================


def test_user_cannot_gain_access_by_supplying_another_departments_uuid(client, db_session):
    """The classic attack: a legitimate USER manually edits the department
    UUID in the request to point at a department they don't belong to."""
    own_department = make_department(db_session, name="Attacker Own Dept 1")
    other_department = make_department(db_session, name="Victim Dept 1")
    user = make_user(db_session, own_department, role=UserRole.USER, email="attacker1@example.gov")

    response = client.get(_department_url(other_department.id), headers=_auth_headers(user))
    assert response.status_code == 403


def test_admin_cannot_gain_access_by_supplying_another_departments_uuid(client, db_session):
    own_department = make_department(db_session, name="Attacker Own Dept 2")
    other_department = make_department(db_session, name="Victim Dept 2")
    admin = make_user(db_session, own_department, role=UserRole.ADMIN, email="attacker2@example.gov")

    response = client.get(_department_url(other_department.id), headers=_auth_headers(admin))
    assert response.status_code == 403


def test_user_cannot_gain_access_via_fabricated_nonexistent_department_uuid(client, db_session):
    """Proves the check is a strict equality against the caller's own
    department, not merely "does this department exist" — a made-up UUID
    that matches no row must be rejected identically to a real, foreign
    one."""
    import uuid as uuid_module

    own_department = make_department(db_session, name="Attacker Own Dept 3")
    user = make_user(db_session, own_department, role=UserRole.USER, email="attacker3@example.gov")

    response = client.get(_department_url(uuid_module.uuid4()), headers=_auth_headers(user))
    assert response.status_code == 403


def test_user_cannot_access_admin_only_operation(client, db_session):
    department = make_department(db_session, name="Escalation Dept 1")
    user = make_user(db_session, department, role=UserRole.USER, email="escalate1@example.gov")
    response = client.get(ADMIN_URL, headers=_auth_headers(user))
    assert response.status_code == 403


def test_admin_cannot_access_system_admin_only_operation(client, db_session):
    department = make_department(db_session, name="Escalation Dept 2")
    admin = make_user(db_session, department, role=UserRole.ADMIN, email="escalate2@example.gov")
    response = client.get(SYSTEM_ADMIN_URL, headers=_auth_headers(admin))
    assert response.status_code == 403


def test_unauthenticated_request_rejected_from_every_protected_endpoint(client, db_session):
    department = make_department(db_session, name="Unauth Dept")
    for url in (
        SYSTEM_ADMIN_URL,
        ADMIN_URL,
        ADMIN_OR_SYSTEM_ADMIN_URL,
        USER_OR_ADMIN_URL,
        _department_url(department.id),
    ):
        response = client.get(url)
        assert response.status_code in (401, 403), url


def test_deactivated_user_with_valid_jwt_rejected_from_department_endpoint(client, db_session):
    """A JWT issued while ACTIVE, then presented after the account is
    deactivated, must be rejected here too — not only at /auth/me (already
    covered in Phase 3A) — proving every dependency built on
    get_current_user inherits the same re-check."""
    department = make_department(db_session, name="Deactivate Then Access Dept")
    user = make_user(db_session, department, role=UserRole.USER, email="deactivate.then.access@example.gov")
    token = _token_for(user)

    first = client.get(_department_url(department.id), headers={"Authorization": f"Bearer {token}"})
    assert first.status_code == 200

    user.status = UserStatus.DEACTIVATED
    db_session.flush()

    second = client.get(_department_url(department.id), headers={"Authorization": f"Bearer {token}"})
    assert second.status_code == 401


def test_department_access_denial_response_is_generic(client, db_session):
    """Error behavior (brief §5, §12): a 403 for department access must not
    name the department, confirm it exists, or reveal the caller's own
    department — just a fixed, generic message."""
    own_department = make_department(db_session, name="Generic Error Own Dept")
    other_department = make_department(db_session, name="Generic Error Victim Dept")
    user = make_user(db_session, own_department, role=UserRole.USER, email="generic.error@example.gov")

    response = client.get(_department_url(other_department.id), headers=_auth_headers(user))

    assert response.status_code == 403
    detail = response.json()["detail"]
    assert str(other_department.id) not in detail
    assert "Generic Error Victim Dept" not in detail
    assert str(own_department.id) not in detail
