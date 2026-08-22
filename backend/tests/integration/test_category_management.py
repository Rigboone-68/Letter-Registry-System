"""End-to-end tests for Category management (Phase 4B).

Mirrors tests/integration/test_department_management.py's shape closely
— same SYSTEM_ADMIN-only CRUD pattern, reused verbatim for a second
reference entity. Does not re-test every department-management scenario;
covers authorization (item Y) and the essentials (create/list/get/update/
activate/deactivate/duplicate) needed to prove Category management works
as the Letter registry's prerequisite (docs/architecture/letter-registry.md
§7).
"""

from app.core.security import create_access_token
from app.models.enums import UserRole
from tests.factories import make_department, make_user

CATEGORIES_URL = "/api/v1/categories"


def _category_url(category_id) -> str:
    return f"{CATEGORIES_URL}/{category_id}"


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
# AUTHORIZATION (item Y)
# =========================================================================


def test_system_admin_can_create_category(client, db_session):
    sys_admin = _make_system_admin(db_session, email="sys.admin.cat1@example.gov")
    response = client.post(CATEGORIES_URL, json={"name": "Cat Test 1"}, headers=_auth_headers(sys_admin))
    assert response.status_code == 201


def test_admin_cannot_create_category(client, db_session):
    department = make_department(db_session, name="Cat Auth Dept 2")
    admin = _make_department_admin(db_session, department, email="admin.cat2@example.gov")
    response = client.post(CATEGORIES_URL, json={"name": "Cat Test 2"}, headers=_auth_headers(admin))
    assert response.status_code == 403


def test_user_cannot_create_category(client, db_session):
    department = make_department(db_session, name="Cat Auth Dept 3")
    user = _make_regular_user(db_session, department, email="user.cat3@example.gov")
    response = client.post(CATEGORIES_URL, json={"name": "Cat Test 3"}, headers=_auth_headers(user))
    assert response.status_code == 403


def test_admin_cannot_deactivate_category(client, db_session):
    sys_admin = _make_system_admin(db_session, email="sys.admin.cat4@example.gov")
    department = make_department(db_session, name="Cat Auth Dept 4")
    admin = _make_department_admin(db_session, department, email="admin.cat4@example.gov")
    create_resp = client.post(CATEGORIES_URL, json={"name": "Cat Test 4"}, headers=_auth_headers(sys_admin))
    category_id = create_resp.json()["id"]

    response = client.post(f"{_category_url(category_id)}/deactivate", headers=_auth_headers(admin))
    assert response.status_code == 403


# =========================================================================
# CRUD ESSENTIALS
# =========================================================================


def test_create_list_get_update_category(client, db_session):
    sys_admin = _make_system_admin(db_session, email="sys.admin.cat5@example.gov")

    create_resp = client.post(
        CATEGORIES_URL,
        json={"name": "Cat Test 5", "description": "A test category"},
        headers=_auth_headers(sys_admin),
    )
    assert create_resp.status_code == 201
    category_id = create_resp.json()["id"]
    assert create_resp.json()["status"] == "ACTIVE"

    list_resp = client.get(CATEGORIES_URL, headers=_auth_headers(sys_admin))
    assert list_resp.status_code == 200
    assert any(item["id"] == category_id for item in list_resp.json()["items"])

    get_resp = client.get(_category_url(category_id), headers=_auth_headers(sys_admin))
    assert get_resp.status_code == 200
    assert get_resp.json()["name"] == "Cat Test 5"

    update_resp = client.patch(
        _category_url(category_id), json={"description": "Updated"}, headers=_auth_headers(sys_admin)
    )
    assert update_resp.status_code == 200
    assert update_resp.json()["description"] == "Updated"


def test_duplicate_category_name_rejected(client, db_session):
    sys_admin = _make_system_admin(db_session, email="sys.admin.cat6@example.gov")
    client.post(CATEGORIES_URL, json={"name": "Cat Test 6"}, headers=_auth_headers(sys_admin))
    response = client.post(CATEGORIES_URL, json={"name": "Cat Test 6"}, headers=_auth_headers(sys_admin))
    assert response.status_code == 409


def test_category_activate_deactivate_idempotent(client, db_session):
    sys_admin = _make_system_admin(db_session, email="sys.admin.cat7@example.gov")
    create_resp = client.post(CATEGORIES_URL, json={"name": "Cat Test 7"}, headers=_auth_headers(sys_admin))
    category_id = create_resp.json()["id"]

    deactivate_resp = client.post(f"{_category_url(category_id)}/deactivate", headers=_auth_headers(sys_admin))
    assert deactivate_resp.status_code == 200
    assert deactivate_resp.json()["status"] == "INACTIVE"

    deactivate_again = client.post(f"{_category_url(category_id)}/deactivate", headers=_auth_headers(sys_admin))
    assert deactivate_again.status_code == 200

    activate_resp = client.post(f"{_category_url(category_id)}/activate", headers=_auth_headers(sys_admin))
    assert activate_resp.status_code == 200
    assert activate_resp.json()["status"] == "ACTIVE"


def test_client_cannot_inject_status_on_category_create(client, db_session):
    sys_admin = _make_system_admin(db_session, email="sys.admin.cat8@example.gov")
    response = client.post(
        CATEGORIES_URL,
        json={"name": "Cat Test 8", "status": "INACTIVE"},
        headers=_auth_headers(sys_admin),
    )
    assert response.status_code == 422  # extra="forbid"


# The three seeded categories (migration 48ec742d9e8f: General Letter,
# Notification, Office Order) are NOT re-verified here — `lrs_test`
# (this suite's database) is built via `Base.metadata.create_all()`
# (tests/conftest.py), which creates schema from the current models only
# and never runs Alembic's data migrations. The seed was verified
# directly against `lrs_dev` via a real `alembic upgrade head` — see the
# Phase 4B final report and docs/architecture/letter-registry.md §4.
