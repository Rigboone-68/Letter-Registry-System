"""End-to-end tests for Designation management (Phase 5H).

Mirrors tests/integration/test_category_management.py's shape closely
— same SYSTEM_ADMIN-only write pattern, reused for a third reference
entity — with two departures specific to Designation's own approved
design (docs/architecture/source-designation.md): the list endpoint is
readable by every authenticated role, not SYSTEM_ADMIN only (§11), and
duplicate detection is case-insensitive (§7).
"""

from app.core.security import create_access_token
from app.models.enums import ActiveStatus, UserRole
from tests.factories import make_department, make_designation, make_user

DESIGNATIONS_URL = "/api/v1/designations"


def _designation_url(designation_id) -> str:
    return f"{DESIGNATIONS_URL}/{designation_id}"


def _token_for(user) -> str:
    return create_access_token(subject=user.id, role=user.role.value, department_id=user.department_id)


def _auth_headers(user) -> dict:
    return {"Authorization": f"Bearer {_token_for(user)}"}


def _make_system_admin(db_session, email="sys.admin@example.gov"):
    return make_user(db_session, department=None, role=UserRole.SYSTEM_ADMIN, email=email)


def _make_department_admin(db_session, department, email="dept.admin@example.gov"):
    return make_user(db_session, department, role=UserRole.ADMIN, email=email)


def _make_regular_user(db_session, department, email="dept.user@example.gov"):
    return make_user(db_session, department, role=UserRole.USER, email=email)


# =========================================================================
# WRITE AUTHORIZATION — SYSTEM_ADMIN only
# =========================================================================


def test_system_admin_can_create_designation(client, db_session):
    sys_admin = _make_system_admin(db_session, email="sys.admin.des1@example.gov")
    response = client.post(
        DESIGNATIONS_URL, json={"name": "Section Officer"}, headers=_auth_headers(sys_admin)
    )
    assert response.status_code == 201
    assert response.json()["status"] == "ACTIVE"


def test_admin_cannot_create_designation(client, db_session):
    department = make_department(db_session, name="Designation Auth Dept 2")
    admin = _make_department_admin(db_session, department, email="admin.des2@example.gov")
    response = client.post(
        DESIGNATIONS_URL, json={"name": "Deputy Director"}, headers=_auth_headers(admin)
    )
    assert response.status_code == 403


def test_user_cannot_create_designation(client, db_session):
    department = make_department(db_session, name="Designation Auth Dept 3")
    user = _make_regular_user(db_session, department, email="user.des3@example.gov")
    response = client.post(
        DESIGNATIONS_URL, json={"name": "Assistant"}, headers=_auth_headers(user)
    )
    assert response.status_code == 403


def test_admin_cannot_activate_or_deactivate_designation(client, db_session):
    sys_admin = _make_system_admin(db_session, email="sys.admin.des4@example.gov")
    department = make_department(db_session, name="Designation Auth Dept 4")
    admin = _make_department_admin(db_session, department, email="admin.des4@example.gov")
    designation = make_designation(db_session, name="Des Test 4")

    deactivate_resp = client.post(
        f"{_designation_url(designation.id)}/deactivate", headers=_auth_headers(admin)
    )
    assert deactivate_resp.status_code == 403

    activate_resp = client.post(
        f"{_designation_url(designation.id)}/activate", headers=_auth_headers(admin)
    )
    assert activate_resp.status_code == 403


def test_user_cannot_activate_or_deactivate_designation(client, db_session):
    sys_admin = _make_system_admin(db_session, email="sys.admin.des5@example.gov")
    department = make_department(db_session, name="Designation Auth Dept 5")
    user = _make_regular_user(db_session, department, email="user.des5@example.gov")
    designation = make_designation(db_session, name="Des Test 5")

    deactivate_resp = client.post(
        f"{_designation_url(designation.id)}/deactivate", headers=_auth_headers(user)
    )
    assert deactivate_resp.status_code == 403

    activate_resp = client.post(
        f"{_designation_url(designation.id)}/activate", headers=_auth_headers(user)
    )
    assert activate_resp.status_code == 403


# =========================================================================
# READ ACCESS — every authenticated role (Phase 5H's own departure from
# Category/Classification's SYSTEM_ADMIN-only list endpoint)
# =========================================================================


def test_system_admin_can_list_designations(client, db_session):
    sys_admin = _make_system_admin(db_session, email="sys.admin.des6@example.gov")
    designation = make_designation(db_session, name="Des Test 6")
    response = client.get(DESIGNATIONS_URL, headers=_auth_headers(sys_admin))
    assert response.status_code == 200
    assert any(item["id"] == str(designation.id) for item in response.json()["items"])


def test_admin_can_list_designations(client, db_session):
    department = make_department(db_session, name="Designation Auth Dept 7")
    admin = _make_department_admin(db_session, department, email="admin.des7@example.gov")
    designation = make_designation(db_session, name="Des Test 7")
    response = client.get(DESIGNATIONS_URL, headers=_auth_headers(admin))
    assert response.status_code == 200
    assert any(item["id"] == str(designation.id) for item in response.json()["items"])


def test_user_can_list_designations(client, db_session):
    department = make_department(db_session, name="Designation Auth Dept 8")
    user = _make_regular_user(db_session, department, email="user.des8@example.gov")
    designation = make_designation(db_session, name="Des Test 8")
    response = client.get(DESIGNATIONS_URL, headers=_auth_headers(user))
    assert response.status_code == 200
    assert any(item["id"] == str(designation.id) for item in response.json()["items"])


def test_user_can_filter_active_designations_only(client, db_session):
    department = make_department(db_session, name="Designation Auth Dept 8b")
    user = _make_regular_user(db_session, department, email="user.des8b@example.gov")
    make_designation(db_session, name="Des Active 8b", status=ActiveStatus.ACTIVE)
    make_designation(db_session, name="Des Inactive 8b", status=ActiveStatus.INACTIVE)
    response = client.get(f"{DESIGNATIONS_URL}?status=ACTIVE", headers=_auth_headers(user))
    assert response.status_code == 200
    assert all(item["status"] == "ACTIVE" for item in response.json()["items"])


def test_get_single_designation_is_system_admin_only(client, db_session):
    department = make_department(db_session, name="Designation Auth Dept 8c")
    user = _make_regular_user(db_session, department, email="user.des8c@example.gov")
    designation = make_designation(db_session, name="Des Test 8c")
    response = client.get(_designation_url(designation.id), headers=_auth_headers(user))
    assert response.status_code == 403


# =========================================================================
# CRUD ESSENTIALS
# =========================================================================


def test_create_list_get_update_designation(client, db_session):
    sys_admin = _make_system_admin(db_session, email="sys.admin.des9@example.gov")

    create_resp = client.post(
        DESIGNATIONS_URL, json={"name": "Des Test 9"}, headers=_auth_headers(sys_admin)
    )
    assert create_resp.status_code == 201
    designation_id = create_resp.json()["id"]

    list_resp = client.get(DESIGNATIONS_URL, headers=_auth_headers(sys_admin))
    assert list_resp.status_code == 200
    assert any(item["id"] == designation_id for item in list_resp.json()["items"])

    get_resp = client.get(_designation_url(designation_id), headers=_auth_headers(sys_admin))
    assert get_resp.status_code == 200
    assert get_resp.json()["name"] == "Des Test 9"

    update_resp = client.patch(
        _designation_url(designation_id),
        json={"name": "Des Test 9 Renamed"},
        headers=_auth_headers(sys_admin),
    )
    assert update_resp.status_code == 200
    assert update_resp.json()["name"] == "Des Test 9 Renamed"


def test_duplicate_designation_name_rejected(client, db_session):
    sys_admin = _make_system_admin(db_session, email="sys.admin.des10@example.gov")
    client.post(DESIGNATIONS_URL, json={"name": "Des Test 10"}, headers=_auth_headers(sys_admin))
    response = client.post(
        DESIGNATIONS_URL, json={"name": "Des Test 10"}, headers=_auth_headers(sys_admin)
    )
    assert response.status_code == 409


def test_case_insensitive_duplicate_designation_rejected(client, db_session):
    """'Secretary'/'secretary'/' SECRETARY ' must not become separate
    designations — docs/architecture/source-designation.md §7."""
    sys_admin = _make_system_admin(db_session, email="sys.admin.des11@example.gov")
    client.post(DESIGNATIONS_URL, json={"name": "Secretary"}, headers=_auth_headers(sys_admin))
    response = client.post(
        DESIGNATIONS_URL, json={"name": " SECRETARY "}, headers=_auth_headers(sys_admin)
    )
    assert response.status_code == 409


def test_designation_activate_deactivate_idempotent(client, db_session):
    sys_admin = _make_system_admin(db_session, email="sys.admin.des12@example.gov")
    create_resp = client.post(
        DESIGNATIONS_URL, json={"name": "Des Test 12"}, headers=_auth_headers(sys_admin)
    )
    designation_id = create_resp.json()["id"]

    deactivate_resp = client.post(
        f"{_designation_url(designation_id)}/deactivate", headers=_auth_headers(sys_admin)
    )
    assert deactivate_resp.status_code == 200
    assert deactivate_resp.json()["status"] == "INACTIVE"

    deactivate_again = client.post(
        f"{_designation_url(designation_id)}/deactivate", headers=_auth_headers(sys_admin)
    )
    assert deactivate_again.status_code == 200

    activate_resp = client.post(
        f"{_designation_url(designation_id)}/activate", headers=_auth_headers(sys_admin)
    )
    assert activate_resp.status_code == 200
    assert activate_resp.json()["status"] == "ACTIVE"


def test_client_cannot_inject_status_on_designation_create(client, db_session):
    sys_admin = _make_system_admin(db_session, email="sys.admin.des13@example.gov")
    response = client.post(
        DESIGNATIONS_URL,
        json={"name": "Des Test 13", "status": "INACTIVE"},
        headers=_auth_headers(sys_admin),
    )
    assert response.status_code == 422  # extra="forbid"


def test_no_physical_delete_endpoint_exists(client, db_session):
    """No DELETE route is registered for this resource at all —
    designations are never physically deleted (docs/architecture/
    source-designation.md §7)."""
    sys_admin = _make_system_admin(db_session, email="sys.admin.des14@example.gov")
    designation = make_designation(db_session, name="Des Test 14")
    response = client.delete(_designation_url(designation.id), headers=_auth_headers(sys_admin))
    assert response.status_code == 405  # Method Not Allowed — no such route
