"""End-to-end tests for Classification management (Phase 4B).

Mirrors tests/integration/test_category_management.py, plus
`restricts_access` — the data-model half of the classified-access
authorization boundary (docs/architecture/letter-registry.md §8). Its
actual enforcement is tested against real Letters in
tests/integration/test_letter_registry.py, not here — this file covers
management CRUD/authorization (item Z) only.
"""

from app.core.security import create_access_token
from app.models.enums import UserRole
from tests.factories import make_department, make_user

CLASSIFICATIONS_URL = "/api/v1/classifications"


def _classification_url(classification_id) -> str:
    return f"{CLASSIFICATIONS_URL}/{classification_id}"


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
# AUTHORIZATION (item Z)
# =========================================================================


def test_system_admin_can_create_classification(client, db_session):
    sys_admin = _make_system_admin(db_session, email="sys.admin.cls1@example.gov")
    response = client.post(
        CLASSIFICATIONS_URL, json={"name": "Cls Test 1"}, headers=_auth_headers(sys_admin)
    )
    assert response.status_code == 201


def test_admin_cannot_create_classification(client, db_session):
    department = make_department(db_session, name="Cls Auth Dept 2")
    admin = _make_department_admin(db_session, department, email="admin.cls2@example.gov")
    response = client.post(
        CLASSIFICATIONS_URL, json={"name": "Cls Test 2"}, headers=_auth_headers(admin)
    )
    assert response.status_code == 403


def test_user_cannot_create_classification(client, db_session):
    department = make_department(db_session, name="Cls Auth Dept 3")
    user = _make_regular_user(db_session, department, email="user.cls3@example.gov")
    response = client.post(
        CLASSIFICATIONS_URL, json={"name": "Cls Test 3"}, headers=_auth_headers(user)
    )
    assert response.status_code == 403


def test_admin_cannot_update_classification(client, db_session):
    sys_admin = _make_system_admin(db_session, email="sys.admin.cls4@example.gov")
    department = make_department(db_session, name="Cls Auth Dept 4")
    admin = _make_department_admin(db_session, department, email="admin.cls4@example.gov")
    create_resp = client.post(
        CLASSIFICATIONS_URL, json={"name": "Cls Test 4"}, headers=_auth_headers(sys_admin)
    )
    classification_id = create_resp.json()["id"]

    response = client.patch(
        _classification_url(classification_id),
        json={"description": "hijacked"},
        headers=_auth_headers(admin),
    )
    assert response.status_code == 403


# =========================================================================
# CRUD ESSENTIALS + restricts_access
# =========================================================================


def test_classification_defaults_restricts_access_false(client, db_session):
    sys_admin = _make_system_admin(db_session, email="sys.admin.cls5@example.gov")
    response = client.post(
        CLASSIFICATIONS_URL, json={"name": "Cls Test 5"}, headers=_auth_headers(sys_admin)
    )
    assert response.status_code == 201
    assert response.json()["restricts_access"] is False


def test_classification_can_be_created_with_restricts_access_true(client, db_session):
    sys_admin = _make_system_admin(db_session, email="sys.admin.cls6@example.gov")
    response = client.post(
        CLASSIFICATIONS_URL,
        json={"name": "Cls Test 6", "restricts_access": True},
        headers=_auth_headers(sys_admin),
    )
    assert response.status_code == 201
    assert response.json()["restricts_access"] is True


def test_restricts_access_can_be_toggled_via_update(client, db_session):
    sys_admin = _make_system_admin(db_session, email="sys.admin.cls7@example.gov")
    create_resp = client.post(
        CLASSIFICATIONS_URL, json={"name": "Cls Test 7"}, headers=_auth_headers(sys_admin)
    )
    classification_id = create_resp.json()["id"]
    assert create_resp.json()["restricts_access"] is False

    update_resp = client.patch(
        _classification_url(classification_id),
        json={"restricts_access": True},
        headers=_auth_headers(sys_admin),
    )
    assert update_resp.status_code == 200
    assert update_resp.json()["restricts_access"] is True


def test_duplicate_classification_name_rejected(client, db_session):
    sys_admin = _make_system_admin(db_session, email="sys.admin.cls8@example.gov")
    client.post(CLASSIFICATIONS_URL, json={"name": "Cls Test 8"}, headers=_auth_headers(sys_admin))
    response = client.post(
        CLASSIFICATIONS_URL, json={"name": "Cls Test 8"}, headers=_auth_headers(sys_admin)
    )
    assert response.status_code == 409


def test_classification_activate_deactivate_idempotent(client, db_session):
    sys_admin = _make_system_admin(db_session, email="sys.admin.cls9@example.gov")
    create_resp = client.post(
        CLASSIFICATIONS_URL, json={"name": "Cls Test 9"}, headers=_auth_headers(sys_admin)
    )
    classification_id = create_resp.json()["id"]

    deactivate_resp = client.post(
        f"{_classification_url(classification_id)}/deactivate", headers=_auth_headers(sys_admin)
    )
    assert deactivate_resp.status_code == 200
    assert deactivate_resp.json()["status"] == "INACTIVE"

    activate_resp = client.post(
        f"{_classification_url(classification_id)}/activate", headers=_auth_headers(sys_admin)
    )
    assert activate_resp.status_code == 200
    assert activate_resp.json()["status"] == "ACTIVE"
