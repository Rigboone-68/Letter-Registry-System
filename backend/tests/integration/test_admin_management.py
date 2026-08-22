"""End-to-end tests for Admin management (brief §27).

Real JWTs, real database-backed Users, real HTTP requests through
/api/v1/admins*, against a real PostgreSQL test database — same pattern as
tests/integration/test_department_management.py and test_authorization.py.
"""

import threading
import uuid
from datetime import datetime, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.security import create_access_token
from app.models.department import Department
from app.models.enums import ActiveStatus, AuthorizationPurpose, UserRole, UserStatus
from app.models.letter import Letter
from app.models.user import User
from app.models.user_authorization import UserAuthorization
from app.services.auth_service import AuthService
from app.services.exceptions import SignupNotAuthorizedError
from tests.conftest import TEST_DATABASE_URL
from tests.factories import make_authorization, make_department, make_user

ADMINS_URL = "/api/v1/admins"
AUTHORIZATIONS_URL = f"{ADMINS_URL}/authorizations"
SIGNUP_URL = "/api/v1/auth/signup"
VALID_PASSWORD = "correct horse battery staple"


def _admin_url(user_id) -> str:
    return f"{ADMINS_URL}/{user_id}"


def _token_for(user) -> str:
    return create_access_token(subject=user.id, role=user.role.value, department_id=user.department_id)


def _auth_headers(user) -> dict:
    return {"Authorization": f"Bearer {_token_for(user)}"}


def _make_system_admin(db_session, email="sys.admin@example.gov"):
    return make_user(db_session, department=None, role=UserRole.SYSTEM_ADMIN, email=email)


def _make_department_admin(db_session, department, email="dept.admin@example.gov", status=UserStatus.ACTIVE):
    return make_user(db_session, department, role=UserRole.ADMIN, email=email, status=status)


def _make_regular_user(db_session, department, email="dept.user@example.gov"):
    return make_user(db_session, department, role=UserRole.USER, email=email)


def _signup_payload(email, password=VALID_PASSWORD, full_name="Admin Candidate"):
    return {
        "full_name": full_name,
        "email": email,
        "password": password,
        "password_confirm": password,
    }


# =========================================================================
# AUTHORIZATION — who can call which endpoint (brief §27, items 1-8)
# =========================================================================


def test_system_admin_can_authorize_admin(client, db_session):
    department = make_department(db_session, name="Authz Dept 1")
    sys_admin = _make_system_admin(db_session)
    response = client.post(
        AUTHORIZATIONS_URL,
        json={"email": "candidate1@example.gov", "department_id": str(department.id)},
        headers=_auth_headers(sys_admin),
    )
    assert response.status_code == 201


def test_admin_cannot_authorize_admin(client, db_session):
    department = make_department(db_session, name="Authz Dept 2")
    admin = _make_department_admin(db_session, department, email="admin.authz2@example.gov")
    response = client.post(
        AUTHORIZATIONS_URL,
        json={"email": "candidate2@example.gov", "department_id": str(department.id)},
        headers=_auth_headers(admin),
    )
    assert response.status_code == 403


def test_user_cannot_authorize_admin(client, db_session):
    department = make_department(db_session, name="Authz Dept 3")
    user = _make_regular_user(db_session, department, email="user.authz3@example.gov")
    response = client.post(
        AUTHORIZATIONS_URL,
        json={"email": "candidate3@example.gov", "department_id": str(department.id)},
        headers=_auth_headers(user),
    )
    assert response.status_code == 403


def test_admin_cannot_approve_admin(client, db_session):
    department = make_department(db_session, name="Authz Dept 4")
    admin = _make_department_admin(db_session, department, email="admin.authz4@example.gov")
    target = _make_department_admin(
        db_session, department, email="target.authz4@example.gov", status=UserStatus.PENDING_APPROVAL
    )
    response = client.post(f"{_admin_url(target.id)}/approve", headers=_auth_headers(admin))
    assert response.status_code == 403


def test_user_cannot_approve_admin(client, db_session):
    department = make_department(db_session, name="Authz Dept 5")
    user = _make_regular_user(db_session, department, email="user.authz5@example.gov")
    target = _make_department_admin(
        db_session, department, email="target.authz5@example.gov", status=UserStatus.PENDING_APPROVAL
    )
    response = client.post(f"{_admin_url(target.id)}/approve", headers=_auth_headers(user))
    assert response.status_code == 403


def test_only_system_admin_can_approve(client, db_session):
    department = make_department(db_session, name="Authz Dept 6")
    sys_admin = _make_system_admin(db_session, email="sys.admin.authz6@example.gov")
    target = _make_department_admin(
        db_session, department, email="target.authz6@example.gov", status=UserStatus.PENDING_APPROVAL
    )
    response = client.post(f"{_admin_url(target.id)}/approve", headers=_auth_headers(sys_admin))
    assert response.status_code == 200


def test_only_system_admin_can_deactivate_or_reactivate(client, db_session):
    department = make_department(db_session, name="Authz Dept 7")
    sys_admin = _make_system_admin(db_session, email="sys.admin.authz7@example.gov")
    target = _make_department_admin(db_session, department, email="target.authz7@example.gov")

    deactivate_resp = client.post(f"{_admin_url(target.id)}/deactivate", headers=_auth_headers(sys_admin))
    assert deactivate_resp.status_code == 200
    reactivate_resp = client.post(f"{_admin_url(target.id)}/reactivate", headers=_auth_headers(sys_admin))
    assert reactivate_resp.status_code == 200


def test_only_system_admin_can_change_admin_department(client, db_session):
    department_a = make_department(db_session, name="Authz Dept 8A")
    department_b = make_department(db_session, name="Authz Dept 8B")
    sys_admin = _make_system_admin(db_session, email="sys.admin.authz8@example.gov")
    target = _make_department_admin(db_session, department_a, email="target.authz8@example.gov")

    response = client.patch(
        f"{_admin_url(target.id)}/department",
        json={"department_id": str(department_b.id)},
        headers=_auth_headers(sys_admin),
    )
    assert response.status_code == 200


# =========================================================================
# AUTHORIZATION WORKFLOW (items 9-20)
# =========================================================================


def test_valid_admin_authorization_succeeds(client, db_session):
    department = make_department(db_session, name="Workflow Dept 1")
    sys_admin = _make_system_admin(db_session, email="sys.admin.wf1@example.gov")
    response = client.post(
        AUTHORIZATIONS_URL,
        json={"email": "wf.candidate1@example.gov", "department_id": str(department.id)},
        headers=_auth_headers(sys_admin),
    )
    assert response.status_code == 201
    body = response.json()
    assert body["email"] == "wf.candidate1@example.gov"
    assert body["department_id"] == str(department.id)


def test_invalid_department_rejected(client, db_session):
    sys_admin = _make_system_admin(db_session, email="sys.admin.wf2@example.gov")
    response = client.post(
        AUTHORIZATIONS_URL,
        json={"email": "wf.candidate2@example.gov", "department_id": str(uuid.uuid4())},
        headers=_auth_headers(sys_admin),
    )
    assert response.status_code == 404


def test_client_cannot_inject_purpose_on_admin_authorization(client, db_session):
    """Hardening-pass regression (Phase 3B.4 review, answers "can a
    malicious client alter authorization purpose?" for the Admin side —
    see docs/architecture/user-management.md §13): `AdminAuthorizationCreate`
    has no `purpose` field and sets `extra="forbid"`; purpose is always
    hardcoded server-side to `ADMIN` in
    app/services/admin_service.py:authorize_admin."""
    department = make_department(db_session, name="Workflow Dept 2B")
    sys_admin = _make_system_admin(db_session, email="sys.admin.wf2b@example.gov")
    response = client.post(
        AUTHORIZATIONS_URL,
        json={
            "email": "wf2b.candidate@example.gov",
            "department_id": str(department.id),
            "purpose": "USER",
        },
        headers=_auth_headers(sys_admin),
    )
    assert response.status_code == 422  # extra="forbid" — no purpose field exists


def test_inactive_department_rejected(client, db_session):
    department = make_department(db_session, name="Workflow Dept 3", status=ActiveStatus.INACTIVE)
    sys_admin = _make_system_admin(db_session, email="sys.admin.wf3@example.gov")
    response = client.post(
        AUTHORIZATIONS_URL,
        json={"email": "wf.candidate3@example.gov", "department_id": str(department.id)},
        headers=_auth_headers(sys_admin),
    )
    assert response.status_code == 409


def test_duplicate_unresolved_authorization_rejected(client, db_session):
    department = make_department(db_session, name="Workflow Dept 4")
    sys_admin = _make_system_admin(db_session, email="sys.admin.wf4@example.gov")
    payload = {"email": "wf.candidate4@example.gov", "department_id": str(department.id)}

    first = client.post(AUTHORIZATIONS_URL, json=payload, headers=_auth_headers(sys_admin))
    assert first.status_code == 201
    second = client.post(AUTHORIZATIONS_URL, json=payload, headers=_auth_headers(sys_admin))
    assert second.status_code == 409


def test_existing_active_admin_email_rejected(client, db_session):
    department = make_department(db_session, name="Workflow Dept 5")
    sys_admin = _make_system_admin(db_session, email="sys.admin.wf5@example.gov")
    _make_department_admin(db_session, department, email="already.active.admin@example.gov")

    response = client.post(
        AUTHORIZATIONS_URL,
        json={"email": "already.active.admin@example.gov", "department_id": str(department.id)},
        headers=_auth_headers(sys_admin),
    )
    assert response.status_code == 409


def test_admin_signup_consumes_correct_authorization(client, db_session):
    department = make_department(db_session, name="Workflow Dept 6")
    sys_admin = _make_system_admin(db_session, email="sys.admin.wf6@example.gov")
    make_authorization(
        db_session, department, sys_admin, email="signup.wf6@example.gov",
        purpose=AuthorizationPurpose.ADMIN,
    )

    client.post(SIGNUP_URL, json=_signup_payload("signup.wf6@example.gov"))

    db_session.expire_all()
    authorization = (
        db_session.query(UserAuthorization)
        .filter(UserAuthorization.email == "signup.wf6@example.gov")
        .one()
    )
    assert authorization.status.value == "USED"


def test_admin_signup_creates_admin_role(client, db_session):
    department = make_department(db_session, name="Workflow Dept 7")
    sys_admin = _make_system_admin(db_session, email="sys.admin.wf7@example.gov")
    make_authorization(
        db_session, department, sys_admin, email="signup.wf7@example.gov",
        purpose=AuthorizationPurpose.ADMIN,
    )

    response = client.post(SIGNUP_URL, json=_signup_payload("signup.wf7@example.gov"))

    assert response.status_code == 201
    body = response.json()
    assert body["role"] == "ADMIN"
    assert body["status"] == "PENDING_APPROVAL"


def test_admin_signup_uses_department_from_authorization(client, db_session):
    department = make_department(db_session, name="Workflow Dept 8")
    sys_admin = _make_system_admin(db_session, email="sys.admin.wf8@example.gov")
    make_authorization(
        db_session, department, sys_admin, email="signup.wf8@example.gov",
        purpose=AuthorizationPurpose.ADMIN,
    )

    response = client.post(SIGNUP_URL, json=_signup_payload("signup.wf8@example.gov"))

    assert response.json()["department_id"] == str(department.id)


def test_admin_signup_client_supplied_role_rejected(client, db_session):
    department = make_department(db_session, name="Workflow Dept 9")
    sys_admin = _make_system_admin(db_session, email="sys.admin.wf9@example.gov")
    make_authorization(
        db_session, department, sys_admin, email="signup.wf9@example.gov",
        purpose=AuthorizationPurpose.ADMIN,
    )

    payload = _signup_payload("signup.wf9@example.gov")
    payload["role"] = "SYSTEM_ADMIN"

    response = client.post(SIGNUP_URL, json=payload)
    assert response.status_code == 422  # extra="forbid"


def test_admin_signup_client_supplied_department_rejected(client, db_session):
    department = make_department(db_session, name="Workflow Dept 10A")
    other_department = make_department(db_session, name="Workflow Dept 10B")
    sys_admin = _make_system_admin(db_session, email="sys.admin.wf10@example.gov")
    make_authorization(
        db_session, department, sys_admin, email="signup.wf10@example.gov",
        purpose=AuthorizationPurpose.ADMIN,
    )

    payload = _signup_payload("signup.wf10@example.gov")
    payload["department_id"] = str(other_department.id)

    response = client.post(SIGNUP_URL, json=payload)
    assert response.status_code == 422  # extra="forbid"


def test_user_authorization_cannot_create_admin(client, db_session):
    department = make_department(db_session, name="Workflow Dept 11")
    sys_admin = _make_system_admin(db_session, email="sys.admin.wf11@example.gov")
    make_authorization(
        db_session, department, sys_admin, email="user.purpose.wf11@example.gov",
        purpose=AuthorizationPurpose.USER,
    )

    response = client.post(SIGNUP_URL, json=_signup_payload("user.purpose.wf11@example.gov"))

    assert response.status_code == 201
    assert response.json()["role"] == "USER"


def test_admin_authorization_cannot_create_user(client, db_session):
    """The other direction of the same guarantee: an ADMIN-purpose
    authorization always produces role=ADMIN, never USER."""
    department = make_department(db_session, name="Workflow Dept 12")
    sys_admin = _make_system_admin(db_session, email="sys.admin.wf12@example.gov")
    make_authorization(
        db_session, department, sys_admin, email="admin.purpose.wf12@example.gov",
        purpose=AuthorizationPurpose.ADMIN,
    )

    response = client.post(SIGNUP_URL, json=_signup_payload("admin.purpose.wf12@example.gov"))

    assert response.status_code == 201
    assert response.json()["role"] == "ADMIN"
    assert response.json()["role"] != "USER"


# =========================================================================
# APPROVAL (items 21-25)
# =========================================================================


def test_pending_admin_can_be_approved(client, db_session):
    department = make_department(db_session, name="Approval Dept 1")
    sys_admin = _make_system_admin(db_session, email="sys.admin.appr1@example.gov")
    target = _make_department_admin(
        db_session, department, email="target.appr1@example.gov", status=UserStatus.PENDING_APPROVAL
    )

    response = client.post(f"{_admin_url(target.id)}/approve", headers=_auth_headers(sys_admin))

    assert response.status_code == 200
    assert response.json()["status"] == "ACTIVE"


def test_already_active_admin_cannot_be_approved_again(client, db_session):
    department = make_department(db_session, name="Approval Dept 2")
    sys_admin = _make_system_admin(db_session, email="sys.admin.appr2@example.gov")
    target = _make_department_admin(db_session, department, email="target.appr2@example.gov", status=UserStatus.ACTIVE)

    response = client.post(f"{_admin_url(target.id)}/approve", headers=_auth_headers(sys_admin))
    assert response.status_code == 409


def test_wrong_role_target_rejected_for_approval(client, db_session):
    department = make_department(db_session, name="Approval Dept 3")
    sys_admin = _make_system_admin(db_session, email="sys.admin.appr3@example.gov")
    regular_user = _make_regular_user(db_session, department, email="regular.appr3@example.gov")

    response = client.post(f"{_admin_url(regular_user.id)}/approve", headers=_auth_headers(sys_admin))
    assert response.status_code == 404


def test_missing_approval_target_returns_404(client, db_session):
    sys_admin = _make_system_admin(db_session, email="sys.admin.appr4@example.gov")
    response = client.post(f"{_admin_url(uuid.uuid4())}/approve", headers=_auth_headers(sys_admin))
    assert response.status_code == 404


def test_admin_with_inactive_department_cannot_be_approved(client, db_session):
    department = make_department(db_session, name="Approval Dept 5", status=ActiveStatus.INACTIVE)
    sys_admin = _make_system_admin(db_session, email="sys.admin.appr5@example.gov")
    target = _make_department_admin(
        db_session, department, email="target.appr5@example.gov", status=UserStatus.PENDING_APPROVAL
    )

    response = client.post(f"{_admin_url(target.id)}/approve", headers=_auth_headers(sys_admin))
    assert response.status_code == 409


# =========================================================================
# LIFECYCLE (items 26-30)
# =========================================================================


def test_active_admin_can_be_deactivated(client, db_session):
    department = make_department(db_session, name="Lifecycle Dept 1")
    sys_admin = _make_system_admin(db_session, email="sys.admin.lc1@example.gov")
    target = _make_department_admin(db_session, department, email="target.lc1@example.gov")

    response = client.post(f"{_admin_url(target.id)}/deactivate", headers=_auth_headers(sys_admin))
    assert response.status_code == 200
    assert response.json()["status"] == "DEACTIVATED"


def test_deactivated_admin_cannot_access_protected_resources(client, db_session):
    department = make_department(db_session, name="Lifecycle Dept 2")
    admin = _make_department_admin(db_session, department, email="target.lc2@example.gov")
    token = _token_for(admin)

    first = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert first.status_code == 200

    admin.status = UserStatus.DEACTIVATED
    db_session.flush()

    second = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert second.status_code == 401


def test_deactivated_admin_can_be_reactivated(client, db_session):
    department = make_department(db_session, name="Lifecycle Dept 3")
    sys_admin = _make_system_admin(db_session, email="sys.admin.lc3@example.gov")
    target = _make_department_admin(
        db_session, department, email="target.lc3@example.gov", status=UserStatus.DEACTIVATED
    )

    response = client.post(f"{_admin_url(target.id)}/reactivate", headers=_auth_headers(sys_admin))
    assert response.status_code == 200
    assert response.json()["status"] == "ACTIVE"


def test_reactivation_requires_active_department(client, db_session):
    department = make_department(db_session, name="Lifecycle Dept 4", status=ActiveStatus.INACTIVE)
    sys_admin = _make_system_admin(db_session, email="sys.admin.lc4@example.gov")
    target = _make_department_admin(
        db_session, department, email="target.lc4@example.gov", status=UserStatus.DEACTIVATED
    )

    response = client.post(f"{_admin_url(target.id)}/reactivate", headers=_auth_headers(sys_admin))
    assert response.status_code == 409


def test_historical_records_remain_intact_after_deactivation(client, db_session):
    department = make_department(db_session, name="Lifecycle Dept 5")
    sys_admin = _make_system_admin(db_session, email="sys.admin.lc5@example.gov")
    admin = _make_department_admin(db_session, department, email="target.lc5@example.gov")
    letter_row = Letter(
        department_id=department.id,
        received_from="Sender",
        received_at=datetime.now(timezone.utc),
        recorded_by=admin.id,
    )
    db_session.add(letter_row)
    db_session.flush()
    letter_id = letter_row.id

    client.post(f"{_admin_url(admin.id)}/deactivate", headers=_auth_headers(sys_admin))

    db_session.expire_all()
    reloaded_letter = db_session.get(Letter, letter_id)
    reloaded_admin = db_session.get(User, admin.id)
    assert reloaded_letter is not None
    assert reloaded_letter.recorded_by == admin.id
    assert reloaded_admin is not None
    assert reloaded_admin.status == UserStatus.DEACTIVATED


# =========================================================================
# MULTIPLE ADMINS (items 31-33)
# =========================================================================


def test_department_can_have_multiple_admins(client, db_session):
    department = make_department(db_session, name="Multi Admin Dept 1")
    _make_department_admin(db_session, department, email="multi1.a@example.gov")
    _make_department_admin(db_session, department, email="multi1.b@example.gov")
    _make_department_admin(db_session, department, email="multi1.c@example.gov")

    db_session.expire_all()
    count = (
        db_session.query(User)
        .filter(User.department_id == department.id, User.role == UserRole.ADMIN)
        .count()
    )
    assert count == 3


def test_deactivating_one_admin_does_not_affect_another(client, db_session):
    department = make_department(db_session, name="Multi Admin Dept 2")
    sys_admin = _make_system_admin(db_session, email="sys.admin.multi2@example.gov")
    admin_a = _make_department_admin(db_session, department, email="multi2.a@example.gov")
    admin_b = _make_department_admin(db_session, department, email="multi2.b@example.gov")

    client.post(f"{_admin_url(admin_a.id)}/deactivate", headers=_auth_headers(sys_admin))

    db_session.expire_all()
    assert db_session.get(User, admin_a.id).status == UserStatus.DEACTIVATED
    assert db_session.get(User, admin_b.id).status == UserStatus.ACTIVE


def test_admin_list_returns_multiple_admins(client, db_session):
    department = make_department(db_session, name="Multi Admin Dept 3")
    sys_admin = _make_system_admin(db_session, email="sys.admin.multi3@example.gov")
    _make_department_admin(db_session, department, email="multi3.a@example.gov")
    _make_department_admin(db_session, department, email="multi3.b@example.gov")

    response = client.get(f"{ADMINS_URL}?department_id={department.id}", headers=_auth_headers(sys_admin))

    assert response.status_code == 200
    emails = {item["email"] for item in response.json()["items"]}
    assert {"multi3.a@example.gov", "multi3.b@example.gov"} <= emails


# =========================================================================
# DEPARTMENT TRANSFER (items 34-39)
# =========================================================================


def test_system_admin_can_move_admin_between_departments(client, db_session):
    department_a = make_department(db_session, name="Transfer Dept A1")
    department_b = make_department(db_session, name="Transfer Dept B1")
    sys_admin = _make_system_admin(db_session, email="sys.admin.transfer1@example.gov")
    admin = _make_department_admin(db_session, department_a, email="transfer1.admin@example.gov")

    response = client.patch(
        f"{_admin_url(admin.id)}/department",
        json={"department_id": str(department_b.id)},
        headers=_auth_headers(sys_admin),
    )
    assert response.status_code == 200
    assert response.json()["department_id"] == str(department_b.id)


def test_transfer_destination_must_be_active(client, db_session):
    department_a = make_department(db_session, name="Transfer Dept A2")
    department_b = make_department(db_session, name="Transfer Dept B2", status=ActiveStatus.INACTIVE)
    sys_admin = _make_system_admin(db_session, email="sys.admin.transfer2@example.gov")
    admin = _make_department_admin(db_session, department_a, email="transfer2.admin@example.gov")

    response = client.patch(
        f"{_admin_url(admin.id)}/department",
        json={"department_id": str(department_b.id)},
        headers=_auth_headers(sys_admin),
    )
    assert response.status_code == 409


def test_transfer_does_not_rewrite_historical_records(client, db_session):
    department_a = make_department(db_session, name="Transfer Dept A3")
    department_b = make_department(db_session, name="Transfer Dept B3")
    sys_admin = _make_system_admin(db_session, email="sys.admin.transfer3@example.gov")
    admin = _make_department_admin(db_session, department_a, email="transfer3.admin@example.gov")

    letter = Letter(
        department_id=department_a.id,
        received_from="Sender",
        received_at=datetime.now(timezone.utc),
        recorded_by=admin.id,
    )
    db_session.add(letter)
    db_session.flush()
    letter_id = letter.id

    client.patch(
        f"{_admin_url(admin.id)}/department",
        json={"department_id": str(department_b.id)},
        headers=_auth_headers(sys_admin),
    )

    db_session.expire_all()
    reloaded_letter = db_session.get(Letter, letter_id)
    assert reloaded_letter.department_id == department_a.id  # unchanged


def test_admins_current_department_becomes_destination(client, db_session):
    department_a = make_department(db_session, name="Transfer Dept A4")
    department_b = make_department(db_session, name="Transfer Dept B4")
    sys_admin = _make_system_admin(db_session, email="sys.admin.transfer4@example.gov")
    admin = _make_department_admin(db_session, department_a, email="transfer4.admin@example.gov")

    client.patch(
        f"{_admin_url(admin.id)}/department",
        json={"department_id": str(department_b.id)},
        headers=_auth_headers(sys_admin),
    )

    db_session.expire_all()
    assert db_session.get(User, admin.id).department_id == department_b.id


def test_admin_cannot_perform_department_a_operations_after_transfer(client, db_session):
    department_a = make_department(db_session, name="Transfer Dept A5")
    department_b = make_department(db_session, name="Transfer Dept B5")
    sys_admin = _make_system_admin(db_session, email="sys.admin.transfer5@example.gov")
    admin = _make_department_admin(db_session, department_a, email="transfer5.admin@example.gov")

    client.patch(
        f"{_admin_url(admin.id)}/department",
        json={"department_id": str(department_b.id)},
        headers=_auth_headers(sys_admin),
    )

    # A fresh token reflects the admin's department at time of issuance —
    # regardless, department-scoped authorization re-derives the current
    # department from the database, never the token's claim.
    new_token = _token_for(db_session.get(User, admin.id))
    response = client.get(
        f"/api/v1/auth/test/department/{department_a.id}",
        headers={"Authorization": f"Bearer {new_token}"},
    )
    assert response.status_code == 403


def test_admin_can_perform_department_b_operations_after_transfer(client, db_session):
    department_a = make_department(db_session, name="Transfer Dept A6")
    department_b = make_department(db_session, name="Transfer Dept B6")
    sys_admin = _make_system_admin(db_session, email="sys.admin.transfer6@example.gov")
    admin = _make_department_admin(db_session, department_a, email="transfer6.admin@example.gov")

    client.patch(
        f"{_admin_url(admin.id)}/department",
        json={"department_id": str(department_b.id)},
        headers=_auth_headers(sys_admin),
    )

    db_session.expire_all()
    new_token = _token_for(db_session.get(User, admin.id))
    response = client.get(
        f"/api/v1/auth/test/department/{department_b.id}",
        headers={"Authorization": f"Bearer {new_token}"},
    )
    assert response.status_code == 200


# =========================================================================
# SELF-PROTECTION (items 40-44)
# =========================================================================


def test_admin_cannot_change_own_department(client, db_session):
    department_a = make_department(db_session, name="Self Protect Dept A1")
    department_b = make_department(db_session, name="Self Protect Dept B1")
    admin = _make_department_admin(db_session, department_a, email="self1.admin@example.gov")

    response = client.patch(
        f"{_admin_url(admin.id)}/department",
        json={"department_id": str(department_b.id)},
        headers=_auth_headers(admin),
    )
    assert response.status_code == 403


def test_admin_cannot_change_own_role(client, db_session):
    """No endpoint accepts a role field at all; this proves an Admin
    self-targeting the department-transfer endpoint (the only admin-owned
    field this phase lets a caller change) still can't smuggle a role
    change through it."""
    department = make_department(db_session, name="Self Protect Dept 2")
    admin = _make_department_admin(db_session, department, email="self2.admin@example.gov")

    response = client.patch(
        f"{_admin_url(admin.id)}/department",
        json={"department_id": str(department.id), "role": "SYSTEM_ADMIN"},
        headers=_auth_headers(admin),
    )
    assert response.status_code in (403, 422)  # 403 (not System Admin) fires first either way


def test_admin_cannot_approve_self(client, db_session):
    """The role gate (`require_system_admin`) always evaluates before any
    service-layer logic, so it fires here regardless of the caller's own
    approval state — which is also why this uses an ACTIVE admin: a
    PENDING_APPROVAL admin can't authenticate at all (401, per Phase 3A's
    get_current_user), which would make this test prove the wrong thing.
    See test_deactivated_admin_cannot_access_protected_resources for that
    guarantee instead."""
    department = make_department(db_session, name="Self Protect Dept 3")
    admin = _make_department_admin(db_session, department, email="self3.admin@example.gov")
    response = client.post(f"{_admin_url(admin.id)}/approve", headers=_auth_headers(admin))
    assert response.status_code == 403


def test_admin_cannot_deactivate_self(client, db_session):
    department = make_department(db_session, name="Self Protect Dept 4")
    admin = _make_department_admin(db_session, department, email="self4.admin@example.gov")
    response = client.post(f"{_admin_url(admin.id)}/deactivate", headers=_auth_headers(admin))
    assert response.status_code == 403


def test_admin_cannot_reactivate_self(client, db_session):
    """Same reasoning as test_admin_cannot_approve_self: uses an ACTIVE
    admin so the request is authenticated at all, proving the role gate —
    not account status — is what blocks this."""
    department = make_department(db_session, name="Self Protect Dept 5")
    admin = _make_department_admin(db_session, department, email="self5.admin@example.gov")
    response = client.post(f"{_admin_url(admin.id)}/reactivate", headers=_auth_headers(admin))
    assert response.status_code == 403


# =========================================================================
# SYSTEM ADMIN PROTECTION (items 45-46)
# =========================================================================


def test_system_admin_cannot_be_targeted_as_admin(client, db_session):
    sys_admin = _make_system_admin(db_session, email="sys.admin.protect1@example.gov")
    other_sys_admin = _make_system_admin(db_session, email="sys.admin.protect1.target@example.gov")

    for suffix in ("/approve", "/deactivate", "/reactivate"):
        response = client.post(f"{_admin_url(other_sys_admin.id)}{suffix}", headers=_auth_headers(sys_admin))
        assert response.status_code == 404, suffix

    get_response = client.get(_admin_url(other_sys_admin.id), headers=_auth_headers(sys_admin))
    assert get_response.status_code == 404


def test_system_admin_remains_unaffected_by_department_operations(client, db_session):
    department = make_department(db_session, name="SysAdmin Protect Dept")
    sys_admin = _make_system_admin(db_session, email="sys.admin.protect2@example.gov")

    # A SYSTEM_ADMIN passed as a department-transfer target is rejected —
    # SYSTEM_ADMIN accounts have no department_id to change (brief §12,
    # §15) and are simply not addressable through /admins/*.
    response = client.patch(
        _admin_url(sys_admin.id) + "/department",
        json={"department_id": str(department.id)},
        headers=_auth_headers(sys_admin),
    )
    assert response.status_code == 404


# =========================================================================
# RACE SAFETY (item 47)
# =========================================================================


def test_concurrent_admin_signup_attempts_consume_authorization_exactly_once():
    """Same guarantee Phase 3A proved for USER signups, re-verified for the
    ADMIN-purpose path specifically — two threads racing to sign up with
    the same ADMIN authorization must not both succeed."""
    engine = create_engine(TEST_DATABASE_URL, future=True)
    SessionLocal = sessionmaker(bind=engine, future=True, expire_on_commit=False)

    setup_session = SessionLocal()
    department = make_department(setup_session, name=f"Race Admin Dept {uuid.uuid4()}")
    sys_admin = _make_system_admin(setup_session, email=f"sys.admin.race.{uuid.uuid4()}@example.gov")
    email = f"race.admin.{uuid.uuid4()}@example.gov"
    make_authorization(
        setup_session, department, sys_admin, email=email, purpose=AuthorizationPurpose.ADMIN
    )
    setup_session.commit()
    department_id, sys_admin_id = department.id, sys_admin.id
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
        admin_role_count = (
            cleanup_session.query(User)
            .filter(User.email == email, User.role == UserRole.ADMIN)
            .count()
        )
        cleanup_session.query(User).filter(User.email == email).delete()
        cleanup_session.query(UserAuthorization).filter(UserAuthorization.email == email).delete()
        cleanup_session.query(User).filter(User.id == sys_admin_id).delete()
        cleanup_session.query(Department).filter(Department.id == department_id).delete()
        cleanup_session.commit()
    finally:
        cleanup_session.close()
        engine.dispose()

    assert sorted(results) == ["rejected", "success"]
    assert user_count == 1, "exactly one User must have been created"
    assert admin_role_count == 1, "the one User created must be role=ADMIN"
