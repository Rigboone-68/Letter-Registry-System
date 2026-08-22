"""End-to-end tests for User management & approval (Phase 3B.4).

Real JWTs, real database-backed Users, real HTTP requests through
/api/v1/users*, against a real PostgreSQL test database — same pattern as
tests/integration/test_admin_management.py. Unlike that file, the caller
throughout is an ADMIN (department-scoped), not a SYSTEM_ADMIN (global) —
so cross-department isolation is exercised here for the first time against
a real business resource, not just the verification-only endpoints in
tests/integration/test_authorization.py.
"""

import threading
import uuid
from datetime import datetime, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.security import create_access_token
from app.models.department import Department
from app.models.enums import ActiveStatus, AuthorizationPurpose, AuthorizationStatus, UserRole, UserStatus
from app.models.letter import Letter
from app.models.user import User
from app.models.user_authorization import UserAuthorization
from app.services.auth_service import AuthService
from app.services.exceptions import SignupNotAuthorizedError
from tests.conftest import TEST_DATABASE_URL
from tests.factories import make_authorization, make_department, make_user

USERS_URL = "/api/v1/users"
AUTHORIZATIONS_URL = f"{USERS_URL}/authorizations"
SIGNUP_URL = "/api/v1/auth/signup"
LOGIN_URL = "/api/v1/auth/login"
ME_URL = "/api/v1/auth/me"
VALID_PASSWORD = "correct horse battery staple"


def _user_url(user_id) -> str:
    return f"{USERS_URL}/{user_id}"


def _authorization_url(authorization_id) -> str:
    return f"{AUTHORIZATIONS_URL}/{authorization_id}"


def _token_for(user) -> str:
    return create_access_token(subject=user.id, role=user.role.value, department_id=user.department_id)


def _auth_headers(user) -> dict:
    return {"Authorization": f"Bearer {_token_for(user)}"}


def _make_system_admin(db_session, email="sys.admin@example.gov"):
    return make_user(db_session, department=None, role=UserRole.SYSTEM_ADMIN, email=email)


def _make_department_admin(db_session, department, email="dept.admin@example.gov", status=UserStatus.ACTIVE):
    return make_user(db_session, department, role=UserRole.ADMIN, email=email, status=status)


def _make_regular_user(db_session, department, email="dept.user@example.gov", status=UserStatus.ACTIVE):
    return make_user(db_session, department, role=UserRole.USER, email=email, status=status)


def _signup_payload(email, password=VALID_PASSWORD, full_name="User Candidate"):
    return {
        "full_name": full_name,
        "email": email,
        "password": password,
        "password_confirm": password,
    }


# =========================================================================
# AUTHORIZATION — who can call which endpoint
# =========================================================================


def test_admin_can_authorize_user(client, db_session):
    department = make_department(db_session, name="Authz Dept 1")
    admin = _make_department_admin(db_session, department, email="admin.authz1@example.gov")
    response = client.post(
        AUTHORIZATIONS_URL, json={"email": "candidate1@example.gov"}, headers=_auth_headers(admin)
    )
    assert response.status_code == 201


def test_user_cannot_authorize_user(client, db_session):
    department = make_department(db_session, name="Authz Dept 2")
    user = _make_regular_user(db_session, department, email="user.authz2@example.gov")
    response = client.post(
        AUTHORIZATIONS_URL, json={"email": "candidate2@example.gov"}, headers=_auth_headers(user)
    )
    assert response.status_code == 403


def test_system_admin_cannot_authorize_user(client, db_session):
    """SYSTEM_ADMIN has no department of its own to scope this to —
    `require_admin` is strictly ADMIN, unlike admin management's
    `require_system_admin`."""
    sys_admin = _make_system_admin(db_session, email="sys.admin.authz3@example.gov")
    response = client.post(
        AUTHORIZATIONS_URL, json={"email": "candidate3@example.gov"}, headers=_auth_headers(sys_admin)
    )
    assert response.status_code == 403


def test_user_cannot_list_users(client, db_session):
    department = make_department(db_session, name="Authz Dept 4")
    user = _make_regular_user(db_session, department, email="user.authz4@example.gov")
    response = client.get(USERS_URL, headers=_auth_headers(user))
    assert response.status_code == 403


def test_user_cannot_approve_user(client, db_session):
    department = make_department(db_session, name="Authz Dept 5")
    user = _make_regular_user(db_session, department, email="user.authz5@example.gov")
    target = _make_regular_user(
        db_session, department, email="target.authz5@example.gov", status=UserStatus.PENDING_APPROVAL
    )
    response = client.post(f"{_user_url(target.id)}/approve", headers=_auth_headers(user))
    assert response.status_code == 403


def test_system_admin_cannot_approve_user(client, db_session):
    department = make_department(db_session, name="Authz Dept 6")
    sys_admin = _make_system_admin(db_session, email="sys.admin.authz6@example.gov")
    target = _make_regular_user(
        db_session, department, email="target.authz6@example.gov", status=UserStatus.PENDING_APPROVAL
    )
    response = client.post(f"{_user_url(target.id)}/approve", headers=_auth_headers(sys_admin))
    assert response.status_code == 403


def test_only_admin_can_deactivate_or_reactivate(client, db_session):
    department = make_department(db_session, name="Authz Dept 7")
    admin = _make_department_admin(db_session, department, email="admin.authz7@example.gov")
    target = _make_regular_user(db_session, department, email="target.authz7@example.gov")

    deactivate_resp = client.post(f"{_user_url(target.id)}/deactivate", headers=_auth_headers(admin))
    assert deactivate_resp.status_code == 200
    reactivate_resp = client.post(f"{_user_url(target.id)}/reactivate", headers=_auth_headers(admin))
    assert reactivate_resp.status_code == 200


# =========================================================================
# AUTHORIZATION WORKFLOW — creating and consuming a UserAuthorization
# =========================================================================


def test_valid_user_authorization_succeeds(client, db_session):
    department = make_department(db_session, name="Workflow Dept 1")
    admin = _make_department_admin(db_session, department, email="admin.wf1@example.gov")
    response = client.post(
        AUTHORIZATIONS_URL, json={"email": "wf.candidate1@example.gov"}, headers=_auth_headers(admin)
    )
    assert response.status_code == 201
    body = response.json()
    assert body["email"] == "wf.candidate1@example.gov"
    assert body["department_id"] == str(department.id)


def test_client_supplied_department_on_authorization_rejected(client, db_session):
    department = make_department(db_session, name="Workflow Dept 2")
    admin = _make_department_admin(db_session, department, email="admin.wf2@example.gov")
    response = client.post(
        AUTHORIZATIONS_URL,
        json={"email": "wf.candidate2@example.gov", "department_id": str(department.id)},
        headers=_auth_headers(admin),
    )
    assert response.status_code == 422  # extra="forbid" — no department_id field exists


def test_authorization_derives_department_from_admin_not_client(client, db_session):
    admins_dept = make_department(db_session, name="Workflow Dept 3 (admin's)")
    admin = _make_department_admin(db_session, admins_dept, email="admin.wf3@example.gov")
    response = client.post(
        AUTHORIZATIONS_URL, json={"email": "wf.candidate3@example.gov"}, headers=_auth_headers(admin)
    )
    assert response.json()["department_id"] == str(admins_dept.id)


def test_admin_with_inactive_department_cannot_authorize(client, db_session):
    department = make_department(db_session, name="Workflow Dept 4", status=ActiveStatus.INACTIVE)
    admin = _make_department_admin(db_session, department, email="admin.wf4@example.gov")
    response = client.post(
        AUTHORIZATIONS_URL, json={"email": "wf.candidate4@example.gov"}, headers=_auth_headers(admin)
    )
    assert response.status_code == 403


def test_duplicate_unresolved_user_authorization_rejected(client, db_session):
    department = make_department(db_session, name="Workflow Dept 5")
    admin = _make_department_admin(db_session, department, email="admin.wf5@example.gov")
    payload = {"email": "wf.candidate5@example.gov"}

    first = client.post(AUTHORIZATIONS_URL, json=payload, headers=_auth_headers(admin))
    assert first.status_code == 201
    second = client.post(AUTHORIZATIONS_URL, json=payload, headers=_auth_headers(admin))
    assert second.status_code == 409


def test_existing_active_user_email_rejected(client, db_session):
    department = make_department(db_session, name="Workflow Dept 6")
    admin = _make_department_admin(db_session, department, email="admin.wf6@example.gov")
    _make_regular_user(db_session, department, email="already.active.user@example.gov")

    response = client.post(
        AUTHORIZATIONS_URL, json={"email": "already.active.user@example.gov"}, headers=_auth_headers(admin)
    )
    assert response.status_code == 409


def test_user_signup_consumes_correct_authorization(client, db_session):
    department = make_department(db_session, name="Workflow Dept 7")
    admin = _make_department_admin(db_session, department, email="admin.wf7@example.gov")
    make_authorization(
        db_session, department, admin, email="signup.wf7@example.gov", purpose=AuthorizationPurpose.USER
    )

    client.post(SIGNUP_URL, json=_signup_payload("signup.wf7@example.gov"))

    db_session.expire_all()
    authorization = (
        db_session.query(UserAuthorization).filter(UserAuthorization.email == "signup.wf7@example.gov").one()
    )
    assert authorization.status.value == "USED"


def test_user_signup_creates_pending_user_in_admins_department(client, db_session):
    department = make_department(db_session, name="Workflow Dept 8")
    admin = _make_department_admin(db_session, department, email="admin.wf8@example.gov")
    make_authorization(
        db_session, department, admin, email="signup.wf8@example.gov", purpose=AuthorizationPurpose.USER
    )

    response = client.post(SIGNUP_URL, json=_signup_payload("signup.wf8@example.gov"))

    assert response.status_code == 201
    body = response.json()
    assert body["role"] == "USER"
    assert body["status"] == "PENDING_APPROVAL"
    assert body["department_id"] == str(department.id)


def test_revoked_authorization_cannot_be_used_to_sign_up(client, db_session):
    department = make_department(db_session, name="Workflow Dept 9")
    admin = _make_department_admin(db_session, department, email="admin.wf9@example.gov")
    create_resp = client.post(
        AUTHORIZATIONS_URL, json={"email": "signup.wf9@example.gov"}, headers=_auth_headers(admin)
    )
    authorization_id = create_resp.json()["id"]

    revoke_resp = client.delete(_authorization_url(authorization_id), headers=_auth_headers(admin))
    assert revoke_resp.status_code == 200
    assert revoke_resp.json()["status"] == "REVOKED"

    signup_resp = client.post(SIGNUP_URL, json=_signup_payload("signup.wf9@example.gov"))
    assert signup_resp.status_code == 403  # SignupNotAuthorizedError — see app/api/v1/endpoints/auth.py


def test_client_cannot_inject_purpose_on_user_authorization(client, db_session):
    """Hardening-pass regression (answers "can a malicious client alter
    authorization purpose?" — see docs/architecture/user-management.md
    §13): `UserAuthorizationCreate` has no `purpose` field and sets
    `extra="forbid"`; `purpose` is always hardcoded server-side to `USER`
    in app/services/user_service.py:authorize_user."""
    department = make_department(db_session, name="Workflow Dept 10")
    admin = _make_department_admin(db_session, department, email="admin.wf10@example.gov")
    response = client.post(
        AUTHORIZATIONS_URL,
        json={"email": "wf10.candidate@example.gov", "purpose": "ADMIN"},
        headers=_auth_headers(admin),
    )
    assert response.status_code == 422  # extra="forbid" — no purpose field exists


def test_revoke_endpoint_cannot_touch_admin_purpose_authorization(client, db_session):
    """Hardening-pass regression (answers "can the USER-purpose revocation
    endpoint accidentally revoke an ADMIN-purpose authorization?" — see
    docs/architecture/user-management.md §13): even an ADMIN-purpose
    authorization created by this exact Admin, in this exact department,
    is invisible to DELETE /api/v1/users/authorizations/{id} — the service
    layer explicitly filters `purpose == USER` before anything else."""
    department = make_department(db_session, name="Workflow Dept 11")
    admin = _make_department_admin(db_session, department, email="admin.wf11@example.gov")
    admin_purpose_authorization = make_authorization(
        db_session, department, admin,
        email="wf11.admin.candidate@example.gov", purpose=AuthorizationPurpose.ADMIN,
    )

    response = client.delete(
        _authorization_url(admin_purpose_authorization.id), headers=_auth_headers(admin)
    )
    assert response.status_code == 404

    db_session.expire_all()
    reloaded = db_session.get(UserAuthorization, admin_purpose_authorization.id)
    assert reloaded.status == AuthorizationStatus.ACTIVE  # untouched


# =========================================================================
# LISTING
# =========================================================================


def test_admin_lists_only_own_department_users(client, db_session):
    dept_a = make_department(db_session, name="List Dept A1")
    dept_b = make_department(db_session, name="List Dept B1")
    admin_a = _make_department_admin(db_session, dept_a, email="admin.list1a@example.gov")
    _make_regular_user(db_session, dept_a, email="list1.a.user@example.gov")
    _make_regular_user(db_session, dept_b, email="list1.b.user@example.gov")

    response = client.get(USERS_URL, headers=_auth_headers(admin_a))

    assert response.status_code == 200
    emails = {item["email"] for item in response.json()["items"]}
    assert "list1.a.user@example.gov" in emails
    assert "list1.b.user@example.gov" not in emails


def test_admin_user_list_status_filter(client, db_session):
    department = make_department(db_session, name="List Dept 2")
    admin = _make_department_admin(db_session, department, email="admin.list2@example.gov")
    _make_regular_user(db_session, department, email="list2.pending@example.gov", status=UserStatus.PENDING_APPROVAL)
    _make_regular_user(db_session, department, email="list2.active@example.gov", status=UserStatus.ACTIVE)

    response = client.get(f"{USERS_URL}?status=PENDING_APPROVAL", headers=_auth_headers(admin))

    emails = {item["email"] for item in response.json()["items"]}
    assert emails == {"list2.pending@example.gov"}


def test_admin_lists_authorizations_created_by_another_admin_in_same_department(client, db_session):
    """Department-wide visibility, not creator-scoped — see
    app/repositories/user_authorization_repository.py:list_by_department."""
    department = make_department(db_session, name="List Dept 3")
    admin_a = _make_department_admin(db_session, department, email="admin.list3a@example.gov")
    admin_b = _make_department_admin(db_session, department, email="admin.list3b@example.gov")
    make_authorization(
        db_session, department, admin_b, email="list3.candidate@example.gov", purpose=AuthorizationPurpose.USER
    )

    response = client.get(AUTHORIZATIONS_URL, headers=_auth_headers(admin_a))

    emails = {item["email"] for item in response.json()["items"]}
    assert "list3.candidate@example.gov" in emails


def test_empty_department_returns_empty_user_list(client, db_session):
    department = make_department(db_session, name="List Dept 4")
    admin = _make_department_admin(db_session, department, email="admin.list4@example.gov")

    response = client.get(USERS_URL, headers=_auth_headers(admin))
    assert response.json() == {"items": [], "total": 0}


# =========================================================================
# DETAILS
# =========================================================================


def test_admin_can_get_user_in_own_department(client, db_session):
    department = make_department(db_session, name="Details Dept 1")
    admin = _make_department_admin(db_session, department, email="admin.details1@example.gov")
    target = _make_regular_user(db_session, department, email="target.details1@example.gov")

    response = client.get(_user_url(target.id), headers=_auth_headers(admin))
    assert response.status_code == 200
    assert response.json()["email"] == "target.details1@example.gov"


def test_missing_user_returns_404(client, db_session):
    department = make_department(db_session, name="Details Dept 2")
    admin = _make_department_admin(db_session, department, email="admin.details2@example.gov")
    response = client.get(_user_url(uuid.uuid4()), headers=_auth_headers(admin))
    assert response.status_code == 404


def test_wrong_role_target_rejected_for_details(client, db_session):
    department = make_department(db_session, name="Details Dept 3")
    admin = _make_department_admin(db_session, department, email="admin.details3@example.gov")
    other_admin = _make_department_admin(db_session, department, email="other.details3@example.gov")

    response = client.get(_user_url(other_admin.id), headers=_auth_headers(admin))
    assert response.status_code == 404


# =========================================================================
# APPROVAL
# =========================================================================


def test_pending_user_can_be_approved(client, db_session):
    department = make_department(db_session, name="Approval Dept 1")
    admin = _make_department_admin(db_session, department, email="admin.appr1@example.gov")
    target = _make_regular_user(
        db_session, department, email="target.appr1@example.gov", status=UserStatus.PENDING_APPROVAL
    )

    response = client.post(f"{_user_url(target.id)}/approve", headers=_auth_headers(admin))

    assert response.status_code == 200
    assert response.json()["status"] == "ACTIVE"


def test_already_active_user_cannot_be_approved_again(client, db_session):
    department = make_department(db_session, name="Approval Dept 2")
    admin = _make_department_admin(db_session, department, email="admin.appr2@example.gov")
    target = _make_regular_user(db_session, department, email="target.appr2@example.gov", status=UserStatus.ACTIVE)

    response = client.post(f"{_user_url(target.id)}/approve", headers=_auth_headers(admin))
    assert response.status_code == 409


def test_missing_approval_target_returns_404(client, db_session):
    department = make_department(db_session, name="Approval Dept 3")
    admin = _make_department_admin(db_session, department, email="admin.appr3@example.gov")
    response = client.post(f"{_user_url(uuid.uuid4())}/approve", headers=_auth_headers(admin))
    assert response.status_code == 404


def test_admin_with_inactive_department_cannot_approve(client, db_session):
    department = make_department(db_session, name="Approval Dept 4", status=ActiveStatus.INACTIVE)
    admin = _make_department_admin(db_session, department, email="admin.appr4@example.gov")
    target = _make_regular_user(
        db_session, department, email="target.appr4@example.gov", status=UserStatus.PENDING_APPROVAL
    )

    response = client.post(f"{_user_url(target.id)}/approve", headers=_auth_headers(admin))
    assert response.status_code == 403


# =========================================================================
# DEACTIVATION
# =========================================================================


def test_active_user_can_be_deactivated(client, db_session):
    department = make_department(db_session, name="Deactivation Dept 1")
    admin = _make_department_admin(db_session, department, email="admin.deact1@example.gov")
    target = _make_regular_user(db_session, department, email="target.deact1@example.gov")

    response = client.post(f"{_user_url(target.id)}/deactivate", headers=_auth_headers(admin))
    assert response.status_code == 200
    assert response.json()["status"] == "DEACTIVATED"


def test_deactivated_user_cannot_access_protected_resources(client, db_session):
    department = make_department(db_session, name="Deactivation Dept 2")
    user = _make_regular_user(db_session, department, email="target.deact2@example.gov")
    token = _token_for(user)

    first = client.get(ME_URL, headers={"Authorization": f"Bearer {token}"})
    assert first.status_code == 200

    user.status = UserStatus.DEACTIVATED
    db_session.flush()

    second = client.get(ME_URL, headers={"Authorization": f"Bearer {token}"})
    assert second.status_code == 401


def test_deactivation_allowed_even_with_inactive_admin_department(client, db_session):
    """Deliberate design decision (see app/services/user_service.py module
    docstring): lock-down actions must remain possible even when the
    department itself has been deactivated, unlike approve/reactivate."""
    department = make_department(db_session, name="Deactivation Dept 3", status=ActiveStatus.INACTIVE)
    admin = _make_department_admin(db_session, department, email="admin.deact3@example.gov")
    target = _make_regular_user(db_session, department, email="target.deact3@example.gov")

    response = client.post(f"{_user_url(target.id)}/deactivate", headers=_auth_headers(admin))
    assert response.status_code == 200
    assert response.json()["status"] == "DEACTIVATED"


# =========================================================================
# REACTIVATION
# =========================================================================


def test_deactivated_user_can_be_reactivated(client, db_session):
    department = make_department(db_session, name="Reactivation Dept 1")
    admin = _make_department_admin(db_session, department, email="admin.react1@example.gov")
    target = _make_regular_user(
        db_session, department, email="target.react1@example.gov", status=UserStatus.DEACTIVATED
    )

    response = client.post(f"{_user_url(target.id)}/reactivate", headers=_auth_headers(admin))
    assert response.status_code == 200
    assert response.json()["status"] == "ACTIVE"


def test_reactivation_requires_active_admin_department(client, db_session):
    department = make_department(db_session, name="Reactivation Dept 2", status=ActiveStatus.INACTIVE)
    admin = _make_department_admin(db_session, department, email="admin.react2@example.gov")
    target = _make_regular_user(
        db_session, department, email="target.react2@example.gov", status=UserStatus.DEACTIVATED
    )

    response = client.post(f"{_user_url(target.id)}/reactivate", headers=_auth_headers(admin))
    assert response.status_code == 403


def test_reactivating_already_active_user_is_idempotent(client, db_session):
    department = make_department(db_session, name="Reactivation Dept 3")
    admin = _make_department_admin(db_session, department, email="admin.react3@example.gov")
    target = _make_regular_user(db_session, department, email="target.react3@example.gov", status=UserStatus.ACTIVE)

    response = client.post(f"{_user_url(target.id)}/reactivate", headers=_auth_headers(admin))
    assert response.status_code == 200
    assert response.json()["status"] == "ACTIVE"


def test_reactivated_user_regains_access(client, db_session):
    department = make_department(db_session, name="Reactivation Dept 4")
    admin = _make_department_admin(db_session, department, email="admin.react4@example.gov")
    target = _make_regular_user(
        db_session, department, email="target.react4@example.gov", status=UserStatus.DEACTIVATED
    )
    token = _token_for(target)

    blocked = client.get(ME_URL, headers={"Authorization": f"Bearer {token}"})
    assert blocked.status_code == 401

    client.post(f"{_user_url(target.id)}/reactivate", headers=_auth_headers(admin))

    restored = client.get(ME_URL, headers={"Authorization": f"Bearer {token}"})
    assert restored.status_code == 200


# =========================================================================
# REVOCATION
# =========================================================================


def test_admin_can_revoke_own_authorization(client, db_session):
    department = make_department(db_session, name="Revoke Dept 1")
    admin = _make_department_admin(db_session, department, email="admin.revoke1@example.gov")
    authorization = make_authorization(
        db_session, department, admin, email="revoke1.candidate@example.gov", purpose=AuthorizationPurpose.USER
    )

    response = client.delete(_authorization_url(authorization.id), headers=_auth_headers(admin))
    assert response.status_code == 200
    assert response.json()["status"] == "REVOKED"


def test_revoking_already_used_authorization_rejected(client, db_session):
    department = make_department(db_session, name="Revoke Dept 2")
    admin = _make_department_admin(db_session, department, email="admin.revoke2@example.gov")
    authorization = make_authorization(
        db_session, department, admin, email="revoke2.candidate@example.gov",
        purpose=AuthorizationPurpose.USER, status=AuthorizationStatus.USED,
    )

    response = client.delete(_authorization_url(authorization.id), headers=_auth_headers(admin))
    assert response.status_code == 409


def test_revoking_already_revoked_authorization_is_idempotent(client, db_session):
    department = make_department(db_session, name="Revoke Dept 3")
    admin = _make_department_admin(db_session, department, email="admin.revoke3@example.gov")
    authorization = make_authorization(
        db_session, department, admin, email="revoke3.candidate@example.gov", purpose=AuthorizationPurpose.USER
    )

    first = client.delete(_authorization_url(authorization.id), headers=_auth_headers(admin))
    assert first.status_code == 200
    second = client.delete(_authorization_url(authorization.id), headers=_auth_headers(admin))
    assert second.status_code == 200
    assert second.json()["status"] == "REVOKED"


def test_admin_cannot_revoke_another_admins_authorization(client, db_session):
    department = make_department(db_session, name="Revoke Dept 4")
    admin_a = _make_department_admin(db_session, department, email="admin.revoke4a@example.gov")
    admin_b = _make_department_admin(db_session, department, email="admin.revoke4b@example.gov")
    authorization = make_authorization(
        db_session, department, admin_b, email="revoke4.candidate@example.gov", purpose=AuthorizationPurpose.USER
    )

    response = client.delete(_authorization_url(authorization.id), headers=_auth_headers(admin_a))
    assert response.status_code == 404


def test_admin_cannot_revoke_authorization_from_another_department(client, db_session):
    dept_a = make_department(db_session, name="Revoke Dept A5")
    dept_b = make_department(db_session, name="Revoke Dept B5")
    admin_a = _make_department_admin(db_session, dept_a, email="admin.revoke5a@example.gov")
    admin_b = _make_department_admin(db_session, dept_b, email="admin.revoke5b@example.gov")
    authorization = make_authorization(
        db_session, dept_b, admin_b, email="revoke5.candidate@example.gov", purpose=AuthorizationPurpose.USER
    )

    response = client.delete(_authorization_url(authorization.id), headers=_auth_headers(admin_a))
    assert response.status_code == 404


def test_revoking_authorization_does_not_affect_existing_account(client, db_session):
    department = make_department(db_session, name="Revoke Dept 6")
    admin = _make_department_admin(db_session, department, email="admin.revoke6@example.gov")
    authorization = make_authorization(
        db_session, department, admin, email="revoke6.candidate@example.gov", purpose=AuthorizationPurpose.USER
    )
    client.post(SIGNUP_URL, json=_signup_payload("revoke6.candidate@example.gov"))

    db_session.expire_all()
    used_authorization = db_session.get(UserAuthorization, authorization.id)
    assert used_authorization.status.value == "USED"

    revoke_resp = client.delete(_authorization_url(authorization.id), headers=_auth_headers(admin))
    assert revoke_resp.status_code == 409  # already USED — the account it produced is untouched

    db_session.expire_all()
    account = db_session.query(User).filter(User.email == "revoke6.candidate@example.gov").one()
    assert account.status == UserStatus.PENDING_APPROVAL


def test_revoking_nonexistent_authorization_returns_404(client, db_session):
    department = make_department(db_session, name="Revoke Dept 7")
    admin = _make_department_admin(db_session, department, email="admin.revoke7@example.gov")
    response = client.delete(_authorization_url(uuid.uuid4()), headers=_auth_headers(admin))
    assert response.status_code == 404


# =========================================================================
# CROSS-DEPARTMENT SECURITY
# =========================================================================


def test_admin_cannot_get_user_in_another_department(client, db_session):
    dept_a = make_department(db_session, name="Cross Dept A1")
    dept_b = make_department(db_session, name="Cross Dept B1")
    admin_a = _make_department_admin(db_session, dept_a, email="admin.cross1a@example.gov")
    target = _make_regular_user(db_session, dept_b, email="target.cross1@example.gov")

    response = client.get(_user_url(target.id), headers=_auth_headers(admin_a))
    assert response.status_code == 404  # not 403 — existence in another department is hidden


def test_admin_cannot_approve_user_in_another_department(client, db_session):
    dept_a = make_department(db_session, name="Cross Dept A2")
    dept_b = make_department(db_session, name="Cross Dept B2")
    admin_a = _make_department_admin(db_session, dept_a, email="admin.cross2a@example.gov")
    target = _make_regular_user(
        db_session, dept_b, email="target.cross2@example.gov", status=UserStatus.PENDING_APPROVAL
    )

    response = client.post(f"{_user_url(target.id)}/approve", headers=_auth_headers(admin_a))
    assert response.status_code == 404


def test_admin_cannot_deactivate_user_in_another_department(client, db_session):
    dept_a = make_department(db_session, name="Cross Dept A3")
    dept_b = make_department(db_session, name="Cross Dept B3")
    admin_a = _make_department_admin(db_session, dept_a, email="admin.cross3a@example.gov")
    target = _make_regular_user(db_session, dept_b, email="target.cross3@example.gov")

    response = client.post(f"{_user_url(target.id)}/deactivate", headers=_auth_headers(admin_a))
    assert response.status_code == 404


def test_admin_cannot_reactivate_user_in_another_department(client, db_session):
    dept_a = make_department(db_session, name="Cross Dept A4")
    dept_b = make_department(db_session, name="Cross Dept B4")
    admin_a = _make_department_admin(db_session, dept_a, email="admin.cross4a@example.gov")
    target = _make_regular_user(
        db_session, dept_b, email="target.cross4@example.gov", status=UserStatus.DEACTIVATED
    )

    response = client.post(f"{_user_url(target.id)}/reactivate", headers=_auth_headers(admin_a))
    assert response.status_code == 404


def test_admin_department_a_operations_do_not_leak_into_department_b_listing(client, db_session):
    dept_a = make_department(db_session, name="Cross Dept A5")
    dept_b = make_department(db_session, name="Cross Dept B5")
    admin_b = _make_department_admin(db_session, dept_b, email="admin.cross5b@example.gov")
    _make_regular_user(db_session, dept_a, email="target.cross5a@example.gov")
    _make_regular_user(db_session, dept_b, email="target.cross5b@example.gov")

    response = client.get(USERS_URL, headers=_auth_headers(admin_b))
    emails = {item["email"] for item in response.json()["items"]}
    assert emails == {"target.cross5b@example.gov"}


# =========================================================================
# SELF-PROTECTION & WRONG-TARGET (structural — no dedicated check exists)
# =========================================================================


def test_admin_cannot_approve_self(client, db_session):
    """`find_user_by_id` filters role==USER; an Admin's own id is role
    ADMIN, so this 404s by construction — see
    app/services/user_service.py module docstring."""
    department = make_department(db_session, name="Self Protect Dept 1")
    admin = _make_department_admin(db_session, department, email="self1.admin@example.gov")
    response = client.post(f"{_user_url(admin.id)}/approve", headers=_auth_headers(admin))
    assert response.status_code == 404


def test_admin_cannot_deactivate_self(client, db_session):
    department = make_department(db_session, name="Self Protect Dept 2")
    admin = _make_department_admin(db_session, department, email="self2.admin@example.gov")
    response = client.post(f"{_user_url(admin.id)}/deactivate", headers=_auth_headers(admin))
    assert response.status_code == 404


def test_admin_cannot_reactivate_self(client, db_session):
    department = make_department(db_session, name="Self Protect Dept 3")
    admin = _make_department_admin(db_session, department, email="self3.admin@example.gov")
    response = client.post(f"{_user_url(admin.id)}/reactivate", headers=_auth_headers(admin))
    assert response.status_code == 404


def test_system_admin_cannot_be_targeted_via_users_endpoints(client, db_session):
    department = make_department(db_session, name="Self Protect Dept 4")
    admin = _make_department_admin(db_session, department, email="self4.admin@example.gov")
    sys_admin = _make_system_admin(db_session, email="self4.sysadmin@example.gov")

    for suffix in ("/approve", "/deactivate", "/reactivate"):
        response = client.post(f"{_user_url(sys_admin.id)}{suffix}", headers=_auth_headers(admin))
        assert response.status_code == 404, suffix


# =========================================================================
# LIFECYCLE / HISTORICAL DATA
# =========================================================================


def test_full_user_lifecycle(client, db_session):
    """authorize -> signup -> pending login rejected -> approve -> login ->
    access -> deactivate -> access rejected -> reactivate -> access
    restored — the same end-to-end shape as the brief's live verification
    steps, run here as an automated regression."""
    department = make_department(db_session, name="Full Lifecycle Dept")
    admin = _make_department_admin(db_session, department, email="admin.lifecycle@example.gov")
    email = "lifecycle.candidate@example.gov"

    authorize_resp = client.post(AUTHORIZATIONS_URL, json={"email": email}, headers=_auth_headers(admin))
    assert authorize_resp.status_code == 201

    signup_resp = client.post(SIGNUP_URL, json=_signup_payload(email))
    assert signup_resp.status_code == 201
    user_id = signup_resp.json()["id"]

    pending_login = client.post(LOGIN_URL, json={"email": email, "password": VALID_PASSWORD})
    assert pending_login.status_code == 403

    approve_resp = client.post(f"{_user_url(user_id)}/approve", headers=_auth_headers(admin))
    assert approve_resp.status_code == 200

    login_resp = client.post(LOGIN_URL, json={"email": email, "password": VALID_PASSWORD})
    assert login_resp.status_code == 200
    token = login_resp.json()["access_token"]

    access_resp = client.get(ME_URL, headers={"Authorization": f"Bearer {token}"})
    assert access_resp.status_code == 200

    deactivate_resp = client.post(f"{_user_url(user_id)}/deactivate", headers=_auth_headers(admin))
    assert deactivate_resp.status_code == 200

    blocked_resp = client.get(ME_URL, headers={"Authorization": f"Bearer {token}"})
    assert blocked_resp.status_code == 401

    reactivate_resp = client.post(f"{_user_url(user_id)}/reactivate", headers=_auth_headers(admin))
    assert reactivate_resp.status_code == 200

    restored_resp = client.get(ME_URL, headers={"Authorization": f"Bearer {token}"})
    assert restored_resp.status_code == 200


def test_historical_records_remain_intact_after_user_deactivation(client, db_session):
    department = make_department(db_session, name="Historical Dept 1")
    admin = _make_department_admin(db_session, department, email="admin.historical1@example.gov")
    user = _make_regular_user(db_session, department, email="target.historical1@example.gov")
    letter_row = Letter(
        department_id=department.id,
        received_from="Sender",
        received_at=datetime.now(timezone.utc),
        recorded_by=user.id,
    )
    db_session.add(letter_row)
    db_session.flush()
    letter_id = letter_row.id

    client.post(f"{_user_url(user.id)}/deactivate", headers=_auth_headers(admin))

    db_session.expire_all()
    reloaded_letter = db_session.get(Letter, letter_id)
    reloaded_user = db_session.get(User, user.id)
    assert reloaded_letter is not None
    assert reloaded_letter.recorded_by == user.id
    assert reloaded_user.status == UserStatus.DEACTIVATED


# =========================================================================
# RACE SAFETY
# =========================================================================


def test_concurrent_user_signup_attempts_consume_authorization_exactly_once():
    """Same guarantee proven for signups generally (Phase 3A) and for the
    ADMIN-purpose path specifically (Phase 3B.3), re-verified here for an
    Admin-issued USER-purpose authorization."""
    engine = create_engine(TEST_DATABASE_URL, future=True)
    SessionLocal = sessionmaker(bind=engine, future=True, expire_on_commit=False)

    setup_session = SessionLocal()
    department = make_department(setup_session, name=f"Race User Dept {uuid.uuid4()}")
    admin = _make_department_admin(setup_session, department, email=f"admin.race.{uuid.uuid4()}@example.gov")
    email = f"race.user.{uuid.uuid4()}@example.gov"
    make_authorization(setup_session, department, admin, email=email, purpose=AuthorizationPurpose.USER)
    setup_session.commit()
    department_id, admin_id = department.id, admin.id
    setup_session.close()

    results = []
    barrier = threading.Barrier(2)

    def attempt_signup():
        session = SessionLocal()
        try:
            barrier.wait(timeout=5)
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

    cleanup_session = SessionLocal()
    try:
        user_count = cleanup_session.query(User).filter(User.email == email).count()
        user_role_count = (
            cleanup_session.query(User).filter(User.email == email, User.role == UserRole.USER).count()
        )
        cleanup_session.query(User).filter(User.email == email).delete()
        cleanup_session.query(UserAuthorization).filter(UserAuthorization.email == email).delete()
        cleanup_session.query(User).filter(User.id == admin_id).delete()
        cleanup_session.query(Department).filter(Department.id == department_id).delete()
        cleanup_session.commit()
    finally:
        cleanup_session.close()
        engine.dispose()

    assert sorted(results) == ["rejected", "success"]
    assert user_count == 1, "exactly one User must have been created"
    assert user_role_count == 1, "the one User created must be role=USER"
