"""End-to-end tests for department management (brief §22).

Real JWTs, real database-backed Users, real HTTP requests through
/api/v1/departments/*, against a real PostgreSQL test database — same
pattern as tests/integration/test_authorization.py.
"""

import uuid

from app.core.security import create_access_token
from app.models.enums import ActiveStatus, UserRole, UserStatus
from tests.factories import make_department, make_user

DEPARTMENTS_URL = "/api/v1/departments"
DEPARTMENT_TEST_URL = "/api/v1/auth/test/department"


def _department_url(department_id) -> str:
    return f"{DEPARTMENTS_URL}/{department_id}"


def _token_for(user) -> str:
    return create_access_token(subject=user.id, role=user.role.value, department_id=user.department_id)


def _auth_headers(user) -> dict:
    return {"Authorization": f"Bearer {_token_for(user)}"}


def _make_system_admin(db_session, email="sys.admin@example.gov"):
    return make_user(db_session, department=None, role=UserRole.SYSTEM_ADMIN, email=email)


def _make_admin(db_session, department, email="dept.admin@example.gov"):
    return make_user(db_session, department, role=UserRole.ADMIN, email=email)


def _make_regular_user(db_session, department, email="dept.user@example.gov"):
    return make_user(db_session, department, role=UserRole.USER, email=email)


# =========================================================================
# AUTHORIZATION (brief §22, items 1-9)
# =========================================================================


def test_system_admin_can_create_department(client, db_session):
    admin = _make_system_admin(db_session)
    response = client.post(DEPARTMENTS_URL, json={"name": "Dept Auth 1"}, headers=_auth_headers(admin))
    assert response.status_code == 201


def test_admin_cannot_create_department(client, db_session):
    department = make_department(db_session, name="Dept Auth 2")
    admin = _make_admin(db_session, department, email="admin.auth2@example.gov")
    response = client.post(DEPARTMENTS_URL, json={"name": "New Dept"}, headers=_auth_headers(admin))
    assert response.status_code == 403


def test_user_cannot_create_department(client, db_session):
    department = make_department(db_session, name="Dept Auth 3")
    user = _make_regular_user(db_session, department, email="user.auth3@example.gov")
    response = client.post(DEPARTMENTS_URL, json={"name": "New Dept"}, headers=_auth_headers(user))
    assert response.status_code == 403


def test_admin_cannot_list_departments(client, db_session):
    department = make_department(db_session, name="Dept Auth 4")
    admin = _make_admin(db_session, department, email="admin.auth4@example.gov")
    response = client.get(DEPARTMENTS_URL, headers=_auth_headers(admin))
    assert response.status_code == 403


def test_user_cannot_list_departments(client, db_session):
    department = make_department(db_session, name="Dept Auth 5")
    user = _make_regular_user(db_session, department, email="user.auth5@example.gov")
    response = client.get(DEPARTMENTS_URL, headers=_auth_headers(user))
    assert response.status_code == 403


def test_admin_cannot_update_department(client, db_session):
    department = make_department(db_session, name="Dept Auth 6")
    admin = _make_admin(db_session, department, email="admin.auth6@example.gov")
    response = client.patch(
        _department_url(department.id), json={"name": "Renamed"}, headers=_auth_headers(admin)
    )
    assert response.status_code == 403


def test_user_cannot_update_department(client, db_session):
    department = make_department(db_session, name="Dept Auth 7")
    user = _make_regular_user(db_session, department, email="user.auth7@example.gov")
    response = client.patch(
        _department_url(department.id), json={"name": "Renamed"}, headers=_auth_headers(user)
    )
    assert response.status_code == 403


def test_admin_cannot_activate_or_deactivate_department(client, db_session):
    department = make_department(db_session, name="Dept Auth 8")
    admin = _make_admin(db_session, department, email="admin.auth8@example.gov")
    assert client.post(f"{_department_url(department.id)}/activate", headers=_auth_headers(admin)).status_code == 403
    assert client.post(f"{_department_url(department.id)}/deactivate", headers=_auth_headers(admin)).status_code == 403


def test_user_cannot_activate_or_deactivate_department(client, db_session):
    department = make_department(db_session, name="Dept Auth 9")
    user = _make_regular_user(db_session, department, email="user.auth9@example.gov")
    assert client.post(f"{_department_url(department.id)}/activate", headers=_auth_headers(user)).status_code == 403
    assert client.post(f"{_department_url(department.id)}/deactivate", headers=_auth_headers(user)).status_code == 403


# =========================================================================
# CREATION (items 10-14)
# =========================================================================


def test_valid_department_creation_succeeds(client, db_session):
    admin = _make_system_admin(db_session, email="sys.admin.create1@example.gov")
    response = client.post(
        DEPARTMENTS_URL, json={"name": "Ministry of Creation", "code": "MOC"}, headers=_auth_headers(admin)
    )
    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "Ministry of Creation"
    assert body["code"] == "MOC"
    assert body["status"] == "ACTIVE"


def test_blank_name_rejected(client, db_session):
    admin = _make_system_admin(db_session, email="sys.admin.create2@example.gov")
    response = client.post(DEPARTMENTS_URL, json={"name": "   "}, headers=_auth_headers(admin))
    assert response.status_code == 422


def test_duplicate_name_rejected(client, db_session):
    admin = _make_system_admin(db_session, email="sys.admin.create3@example.gov")
    client.post(DEPARTMENTS_URL, json={"name": "Duplicate Dept Name"}, headers=_auth_headers(admin))
    response = client.post(DEPARTMENTS_URL, json={"name": "Duplicate Dept Name"}, headers=_auth_headers(admin))
    assert response.status_code == 409


def test_duplicate_code_rejected(client, db_session):
    admin = _make_system_admin(db_session, email="sys.admin.create4@example.gov")
    client.post(
        DEPARTMENTS_URL, json={"name": "Dept Code Owner", "code": "DUPCODE"}, headers=_auth_headers(admin)
    )
    response = client.post(
        DEPARTMENTS_URL, json={"name": "Different Name", "code": "DUPCODE"}, headers=_auth_headers(admin)
    )
    assert response.status_code == 409


def test_server_controlled_fields_cannot_be_injected(client, db_session):
    admin = _make_system_admin(db_session, email="sys.admin.create5@example.gov")
    fake_id = str(uuid.uuid4())
    response = client.post(
        DEPARTMENTS_URL,
        json={
            "name": "Injection Attempt Dept",
            "id": fake_id,
            "status": "INACTIVE",
            "created_at": "2000-01-01T00:00:00Z",
            "updated_at": "2000-01-01T00:00:00Z",
        },
        headers=_auth_headers(admin),
    )
    assert response.status_code == 422  # extra="forbid" rejects the whole request


# =========================================================================
# RETRIEVAL (items 15-18)
# =========================================================================


def test_existing_department_can_be_retrieved(client, db_session):
    department = make_department(db_session, name="Retrievable Dept")
    admin = _make_system_admin(db_session, email="sys.admin.retrieve1@example.gov")
    response = client.get(_department_url(department.id), headers=_auth_headers(admin))
    assert response.status_code == 200
    assert response.json()["id"] == str(department.id)


def test_missing_department_returns_404(client, db_session):
    admin = _make_system_admin(db_session, email="sys.admin.retrieve2@example.gov")
    response = client.get(_department_url(uuid.uuid4()), headers=_auth_headers(admin))
    assert response.status_code == 404


def test_system_admin_can_list_active_and_inactive_departments(client, db_session):
    make_department(db_session, name="Listable Active Dept", status=ActiveStatus.ACTIVE)
    make_department(db_session, name="Listable Inactive Dept", status=ActiveStatus.INACTIVE)
    admin = _make_system_admin(db_session, email="sys.admin.retrieve3@example.gov")

    response = client.get(DEPARTMENTS_URL, headers=_auth_headers(admin))
    assert response.status_code == 200
    names = {item["name"] for item in response.json()["items"]}
    assert "Listable Active Dept" in names
    assert "Listable Inactive Dept" in names


def test_status_filtering_works(client, db_session):
    make_department(db_session, name="Filter Active Dept", status=ActiveStatus.ACTIVE)
    make_department(db_session, name="Filter Inactive Dept", status=ActiveStatus.INACTIVE)
    admin = _make_system_admin(db_session, email="sys.admin.retrieve4@example.gov")

    active_response = client.get(f"{DEPARTMENTS_URL}?status=ACTIVE", headers=_auth_headers(admin))
    inactive_response = client.get(f"{DEPARTMENTS_URL}?status=INACTIVE", headers=_auth_headers(admin))

    active_names = {item["name"] for item in active_response.json()["items"]}
    inactive_names = {item["name"] for item in inactive_response.json()["items"]}
    assert "Filter Active Dept" in active_names
    assert "Filter Active Dept" not in inactive_names
    assert "Filter Inactive Dept" in inactive_names
    assert "Filter Inactive Dept" not in active_names


# =========================================================================
# UPDATE (items 19-23)
# =========================================================================


def test_name_can_be_updated(client, db_session):
    department = make_department(db_session, name="Original Name Dept")
    admin = _make_system_admin(db_session, email="sys.admin.update1@example.gov")
    response = client.patch(
        _department_url(department.id), json={"name": "Updated Name Dept"}, headers=_auth_headers(admin)
    )
    assert response.status_code == 200
    assert response.json()["name"] == "Updated Name Dept"


def test_code_can_be_updated(client, db_session):
    department = make_department(db_session, name="Code Update Dept", code="OLD")
    admin = _make_system_admin(db_session, email="sys.admin.update2@example.gov")
    response = client.patch(
        _department_url(department.id), json={"code": "NEW"}, headers=_auth_headers(admin)
    )
    assert response.status_code == 200
    assert response.json()["code"] == "NEW"


def test_empty_update_rejected(client, db_session):
    department = make_department(db_session, name="Empty Update Dept")
    admin = _make_system_admin(db_session, email="sys.admin.update3@example.gov")
    response = client.patch(_department_url(department.id), json={}, headers=_auth_headers(admin))
    assert response.status_code == 422


def test_duplicate_name_update_rejected(client, db_session):
    make_department(db_session, name="Existing Name Dept")
    target = make_department(db_session, name="Target Dept For Rename")
    admin = _make_system_admin(db_session, email="sys.admin.update4@example.gov")

    response = client.patch(
        _department_url(target.id), json={"name": "Existing Name Dept"}, headers=_auth_headers(admin)
    )
    assert response.status_code == 409


def test_duplicate_code_update_rejected(client, db_session):
    make_department(db_session, name="Existing Code Owner Dept", code="TAKEN")
    target = make_department(db_session, name="Target Dept For Code Change")
    admin = _make_system_admin(db_session, email="sys.admin.update5@example.gov")

    response = client.patch(
        _department_url(target.id), json={"code": "TAKEN"}, headers=_auth_headers(admin)
    )
    assert response.status_code == 409


# =========================================================================
# STATUS (items 24-30)
# =========================================================================


def test_active_department_can_be_deactivated(client, db_session):
    department = make_department(db_session, name="Deactivate Me Dept", status=ActiveStatus.ACTIVE)
    admin = _make_system_admin(db_session, email="sys.admin.status1@example.gov")
    response = client.post(f"{_department_url(department.id)}/deactivate", headers=_auth_headers(admin))
    assert response.status_code == 200
    assert response.json()["status"] == "INACTIVE"


def test_inactive_department_can_be_activated(client, db_session):
    department = make_department(db_session, name="Activate Me Dept", status=ActiveStatus.INACTIVE)
    admin = _make_system_admin(db_session, email="sys.admin.status2@example.gov")
    response = client.post(f"{_department_url(department.id)}/activate", headers=_auth_headers(admin))
    assert response.status_code == 200
    assert response.json()["status"] == "ACTIVE"


def test_deactivation_does_not_delete_users(client, db_session):
    department = make_department(db_session, name="Preserve Users Dept")
    user = _make_regular_user(db_session, department, email="preserved.user@example.gov")
    admin = _make_system_admin(db_session, email="sys.admin.status3@example.gov")

    client.post(f"{_department_url(department.id)}/deactivate", headers=_auth_headers(admin))

    db_session.expire_all()
    still_there = db_session.get(type(user), user.id)
    assert still_there is not None
    assert still_there.department_id == department.id


def test_deactivation_does_not_delete_letters(client, db_session):
    from datetime import datetime, timezone

    from app.models.letter import Letter

    department = make_department(db_session, name="Preserve Letters Dept")
    recorder = _make_regular_user(db_session, department, email="letter.recorder@example.gov")
    letter = Letter(
        reference_number=f"REF-{uuid.uuid4()}",
        recipient_department_id=department.id,
        source_name="Sender",
        sender_name="Sender Name",
        sender_designation="Sender Designation",
        sender_department="Sender Department",
        received_at=datetime.now(timezone.utc),
        recorded_by=recorder.id,
    )
    db_session.add(letter)
    db_session.flush()
    letter_id = letter.id
    admin = _make_system_admin(db_session, email="sys.admin.status4@example.gov")

    client.post(f"{_department_url(department.id)}/deactivate", headers=_auth_headers(admin))

    db_session.expire_all()
    assert db_session.get(Letter, letter_id) is not None


def test_deactivation_does_not_delete_historical_records(client, db_session):
    """Broader check: the Department row itself survives (never physically
    deleted), and its own audit columns (created_at) are untouched."""
    department = make_department(db_session, name="Historical Preservation Dept")
    original_created_at = department.created_at
    admin = _make_system_admin(db_session, email="sys.admin.status5@example.gov")

    client.post(f"{_department_url(department.id)}/deactivate", headers=_auth_headers(admin))

    db_session.expire_all()
    reloaded = db_session.get(type(department), department.id)
    assert reloaded is not None
    assert reloaded.created_at == original_created_at


def test_admin_in_inactive_department_cannot_perform_departmental_operations(client, db_session):
    department = make_department(db_session, name="Inactive For Admin Dept", status=ActiveStatus.INACTIVE)
    admin = _make_admin(db_session, department, email="admin.inactive1@example.gov")

    response = client.get(f"{DEPARTMENT_TEST_URL}/{department.id}", headers=_auth_headers(admin))
    assert response.status_code == 403


def test_user_in_inactive_department_cannot_perform_departmental_operations(client, db_session):
    department = make_department(db_session, name="Inactive For User Dept", status=ActiveStatus.INACTIVE)
    user = _make_regular_user(db_session, department, email="user.inactive1@example.gov")

    response = client.get(f"{DEPARTMENT_TEST_URL}/{department.id}", headers=_auth_headers(user))
    assert response.status_code == 403


def test_system_admin_can_still_access_inactive_department(client, db_session):
    department = make_department(db_session, name="Inactive For SysAdmin Dept", status=ActiveStatus.INACTIVE)
    admin = _make_system_admin(db_session, email="sys.admin.status6@example.gov")

    # Management endpoint:
    get_response = client.get(_department_url(department.id), headers=_auth_headers(admin))
    assert get_response.status_code == 200

    # Departmental-resource-style endpoint (dev/test authorization endpoint):
    dept_access_response = client.get(f"{DEPARTMENT_TEST_URL}/{department.id}", headers=_auth_headers(admin))
    assert dept_access_response.status_code == 200


# =========================================================================
# SECURITY (items 31-35)
# =========================================================================


def test_client_cannot_change_department_id(client, db_session):
    department = make_department(db_session, name="ID Injection Dept")
    other_department = make_department(db_session, name="Other Dept For ID Injection")
    admin = _make_system_admin(db_session, email="sys.admin.security1@example.gov")

    response = client.patch(
        _department_url(department.id),
        json={"name": "Renamed", "id": str(other_department.id)},
        headers=_auth_headers(admin),
    )
    assert response.status_code == 422  # extra="forbid"


def test_admin_and_user_cannot_escalate_to_system_admin_endpoint(client, db_session):
    department = make_department(db_session, name="Escalation Dept")
    admin = _make_admin(db_session, department, email="admin.security2@example.gov")
    user = _make_regular_user(db_session, department, email="user.security2@example.gov")

    for caller in (admin, user):
        response = client.post(
            DEPARTMENTS_URL, json={"name": "Should Not Be Created"}, headers=_auth_headers(caller)
        )
        assert response.status_code == 403


def test_unauthenticated_access_rejected(client, db_session):
    department = make_department(db_session, name="Unauth Dept")
    assert client.get(DEPARTMENTS_URL).status_code in (401, 403)
    assert client.post(DEPARTMENTS_URL, json={"name": "x"}).status_code in (401, 403)
    assert client.get(_department_url(department.id)).status_code in (401, 403)
    assert client.patch(_department_url(department.id), json={"name": "x"}).status_code in (401, 403)
    assert client.post(f"{_department_url(department.id)}/activate").status_code in (401, 403)
    assert client.post(f"{_department_url(department.id)}/deactivate").status_code in (401, 403)


def test_deactivated_user_remains_unable_to_access_departmental_resources(client, db_session):
    department = make_department(db_session, name="Deactivated User Dept")
    user = _make_regular_user(db_session, department, email="deactivated.dept.user@example.gov")
    token = _token_for(user)

    first = client.get(f"{DEPARTMENT_TEST_URL}/{department.id}", headers={"Authorization": f"Bearer {token}"})
    assert first.status_code == 200

    user.status = UserStatus.DEACTIVATED
    db_session.flush()

    second = client.get(f"{DEPARTMENT_TEST_URL}/{department.id}", headers={"Authorization": f"Bearer {token}"})
    assert second.status_code == 401


def test_reactivating_department_restores_operational_access(client, db_session):
    department = make_department(db_session, name="Reactivation Dept", status=ActiveStatus.ACTIVE)
    user = _make_regular_user(db_session, department, email="reactivation.user@example.gov")
    admin = _make_system_admin(db_session, email="sys.admin.security5@example.gov")
    user_headers = _auth_headers(user)

    baseline = client.get(f"{DEPARTMENT_TEST_URL}/{department.id}", headers=user_headers)
    assert baseline.status_code == 200

    client.post(f"{_department_url(department.id)}/deactivate", headers=_auth_headers(admin))
    while_inactive = client.get(f"{DEPARTMENT_TEST_URL}/{department.id}", headers=user_headers)
    assert while_inactive.status_code == 403

    client.post(f"{_department_url(department.id)}/activate", headers=_auth_headers(admin))
    after_reactivation = client.get(f"{DEPARTMENT_TEST_URL}/{department.id}", headers=user_headers)
    assert after_reactivation.status_code == 200
