"""Audit-generation tests (Phase 4E implementation).

Real JWTs, real database-backed Letters/Users/Departments/Admins/
Categories/Classifications, real HTTP requests through the existing
endpoints, against a real PostgreSQL test database — same pattern as
every integration test file since Phase 3A. Verifies `AuditLog` rows are
actually created with the correct actor/target/values, not just that the
underlying business operation still succeeds (already covered by the
pre-existing suite, which stays green — see docs/architecture/
audit-notifications.md's implementation record for the regression
confirmation).
"""

import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy import select

from app.core.config import settings
from app.core.security import create_access_token
from app.models.audit_log import AuditLog
from app.models.enums import UserRole, UserStatus
from app.models.letter import Letter
from app.services.audit_service import AuditService
from tests.factories import (
    make_authorization,
    make_category,
    make_classification,
    make_department,
    make_letter,
    make_user,
)

LETTERS_URL = "/api/v1/letters"
DEPARTMENTS_URL = "/api/v1/departments"
ADMINS_URL = "/api/v1/admins"
USERS_URL = "/api/v1/users"
CATEGORIES_URL = "/api/v1/categories"
CLASSIFICATIONS_URL = "/api/v1/classifications"


@pytest.fixture()
def storage_root(tmp_path, monkeypatch):
    """Requested explicitly only by the document-upload test below —
    redirects STORAGE_PATH to an isolated temp directory, the same
    pattern test_document_management.py uses (there, autouse; here,
    opt-in, since only one test in this file touches storage)."""
    monkeypatch.setattr(settings, "STORAGE_PATH", str(tmp_path))
    return tmp_path


def _token_for(user) -> str:
    return create_access_token(subject=user.id, role=user.role.value, department_id=user.department_id)


def _auth_headers(user) -> dict:
    return {"Authorization": f"Bearer {_token_for(user)}"}


def _make_system_admin(db_session, email=None):
    return make_user(
        db_session, department=None, role=UserRole.SYSTEM_ADMIN, email=email or f"sys.{uuid.uuid4()}@example.gov"
    )


def _make_admin(db_session, department, email=None):
    return make_user(
        db_session, department, role=UserRole.ADMIN, email=email or f"admin.{uuid.uuid4()}@example.gov"
    )


def _make_regular_user(db_session, department, email=None):
    return make_user(
        db_session, department, role=UserRole.USER, email=email or f"user.{uuid.uuid4()}@example.gov"
    )


def _letter_payload(**overrides):
    payload = {
        "reference_number": f"REF-{uuid.uuid4()}",
        "subject": "Confidential quarterly briefing",
        "source_name": "Test Source Organization",
        "sender_name": "Test Sender",
        "sender_designation": "Test Designation",
        "sender_department": "Test Sender Department",
        "received_at": datetime.now(timezone.utc).isoformat(),
    }
    payload.update(overrides)
    return payload


def _latest_audit(db_session, entity_type, entity_id=None, action=None):
    stmt = select(AuditLog).where(AuditLog.entity_type == entity_type)
    if entity_id is not None:
        stmt = stmt.where(AuditLog.entity_id == entity_id)
    if action is not None:
        stmt = stmt.where(AuditLog.action == action)
    stmt = stmt.order_by(AuditLog.created_at.desc())
    return db_session.execute(stmt).scalars().first()


def _all_audit_for_entity(db_session, entity_type, entity_id):
    stmt = (
        select(AuditLog)
        .where(AuditLog.entity_type == entity_type, AuditLog.entity_id == entity_id)
        .order_by(AuditLog.created_at.asc())
    )
    return list(db_session.execute(stmt).scalars().all())


# =========================================================================
# 1-6. Core mutations create audit rows
# =========================================================================


def test_letter_creation_creates_audit(client, db_session):
    department = make_department(db_session, name=f"Audit Dept {uuid.uuid4()}")
    user = _make_regular_user(db_session, department)

    response = client.post(LETTERS_URL, json=_letter_payload(), headers=_auth_headers(user))
    assert response.status_code == 201
    letter_id = uuid.UUID(response.json()["id"])

    entry = _latest_audit(db_session, "Letter", letter_id, "LETTER_CREATED")
    assert entry is not None
    assert entry.user_id == user.id
    assert entry.entity_id == letter_id


def test_letter_update_creates_audit(client, db_session):
    department = make_department(db_session, name=f"Audit Dept {uuid.uuid4()}")
    user = _make_regular_user(db_session, department)
    letter = make_letter(db_session, department, user)

    response = client.patch(
        f"{LETTERS_URL}/{letter.id}", json={"subject": "Updated subject line"}, headers=_auth_headers(user)
    )
    assert response.status_code == 200

    entry = _latest_audit(db_session, "Letter", letter.id, "LETTER_UPDATED")
    assert entry is not None
    assert entry.user_id == user.id
    assert "subject" in entry.new_values["changed_fields"]


def test_letter_archive_creates_audit(client, db_session):
    department = make_department(db_session, name=f"Audit Dept {uuid.uuid4()}")
    user = _make_regular_user(db_session, department)
    letter = make_letter(db_session, department, user)

    response = client.delete(f"{LETTERS_URL}/{letter.id}", headers=_auth_headers(user))
    assert response.status_code == 200

    entry = _latest_audit(db_session, "Letter", letter.id, "LETTER_ARCHIVED")
    assert entry is not None
    assert entry.old_values == {"status": "ACTIVE"}
    assert entry.new_values == {"status": "ARCHIVED"}


def test_letter_archive_twice_creates_only_one_audit_entry(client, db_session):
    """Idempotent re-archiving must not produce a redundant trail entry."""
    department = make_department(db_session, name=f"Audit Dept {uuid.uuid4()}")
    user = _make_regular_user(db_session, department)
    letter = make_letter(db_session, department, user)

    client.delete(f"{LETTERS_URL}/{letter.id}", headers=_auth_headers(user))
    client.delete(f"{LETTERS_URL}/{letter.id}", headers=_auth_headers(user))

    entries = [
        e for e in _all_audit_for_entity(db_session, "Letter", letter.id) if e.action == "LETTER_ARCHIVED"
    ]
    assert len(entries) == 1


def test_letter_classification_change_creates_audit(client, db_session):
    department = make_department(db_session, name=f"Audit Dept {uuid.uuid4()}")
    user = _make_regular_user(db_session, department)
    old_classification = make_classification(db_session, name=f"Old {uuid.uuid4()}")
    new_classification = make_classification(db_session, name=f"New {uuid.uuid4()}")
    letter = make_letter(db_session, department, user, classification=old_classification)

    response = client.patch(
        f"{LETTERS_URL}/{letter.id}",
        json={"classification_id": str(new_classification.id)},
        headers=_auth_headers(user),
    )
    assert response.status_code == 200

    entry = _latest_audit(db_session, "Letter", letter.id, "LETTER_CLASSIFICATION_CHANGED")
    assert entry is not None
    assert entry.old_values == {"classification_id": str(old_classification.id)}
    assert entry.new_values == {"classification_id": str(new_classification.id)}


def test_letter_category_change_creates_audit(client, db_session):
    department = make_department(db_session, name=f"Audit Dept {uuid.uuid4()}")
    user = _make_regular_user(db_session, department)
    old_category = make_category(db_session, name=f"Old Cat {uuid.uuid4()}")
    new_category = make_category(db_session, name=f"New Cat {uuid.uuid4()}")
    letter = make_letter(db_session, department, user, category=old_category)

    response = client.patch(
        f"{LETTERS_URL}/{letter.id}",
        json={"category_id": str(new_category.id)},
        headers=_auth_headers(user),
    )
    assert response.status_code == 200

    entry = _latest_audit(db_session, "Letter", letter.id, "LETTER_CATEGORY_CHANGED")
    assert entry is not None
    assert entry.old_values == {"category_id": str(old_category.id)}
    assert entry.new_values == {"category_id": str(new_category.id)}


def test_document_upload_creates_audit(client, db_session, storage_root):
    department = make_department(db_session, name=f"Audit Dept {uuid.uuid4()}")
    user = _make_regular_user(db_session, department)
    letter = make_letter(db_session, department, user)

    response = client.post(
        f"{LETTERS_URL}/{letter.id}/documents",
        files={"file": ("letter.pdf", b"%PDF-1.4\nmock\n%%EOF", "application/pdf")},
        headers=_auth_headers(user),
    )
    assert response.status_code == 201
    document_id = uuid.UUID(response.json()["id"])

    entry = _latest_audit(db_session, "LetterDocument", document_id, "DOCUMENT_UPLOADED")
    assert entry is not None
    assert entry.user_id == user.id
    assert entry.new_values["letter_id"] == str(letter.id)
    assert entry.new_values["original_filename"] == "letter.pdf"
    # No document bytes are ever recorded.
    assert "content" not in entry.new_values
    assert b"%PDF" not in str(entry.new_values).encode()


# =========================================================================
# 7-9. User lifecycle
# =========================================================================


def test_user_approval_creates_audit(client, db_session):
    department = make_department(db_session, name=f"Audit Dept {uuid.uuid4()}")
    admin = _make_admin(db_session, department)
    target = _make_regular_user(db_session, department)
    target.status = UserStatus.PENDING_APPROVAL
    db_session.flush()

    response = client.post(f"{USERS_URL}/{target.id}/approve", headers=_auth_headers(admin))
    assert response.status_code == 200

    entry = _latest_audit(db_session, "User", target.id, "USER_APPROVED")
    assert entry is not None
    assert entry.user_id == admin.id  # actor is the Admin, not the target
    assert entry.entity_id == target.id


def test_user_deactivation_creates_audit(client, db_session):
    department = make_department(db_session, name=f"Audit Dept {uuid.uuid4()}")
    admin = _make_admin(db_session, department)
    target = _make_regular_user(db_session, department)

    response = client.post(f"{USERS_URL}/{target.id}/deactivate", headers=_auth_headers(admin))
    assert response.status_code == 200

    entry = _latest_audit(db_session, "User", target.id, "USER_DEACTIVATED")
    assert entry is not None
    assert entry.user_id == admin.id


def test_user_reactivation_creates_audit(client, db_session):
    department = make_department(db_session, name=f"Audit Dept {uuid.uuid4()}")
    admin = _make_admin(db_session, department)
    target = _make_regular_user(db_session, department)
    target.status = UserStatus.DEACTIVATED
    db_session.flush()

    response = client.post(f"{USERS_URL}/{target.id}/reactivate", headers=_auth_headers(admin))
    assert response.status_code == 200

    entry = _latest_audit(db_session, "User", target.id, "USER_REACTIVATED")
    assert entry is not None
    assert entry.user_id == admin.id


# =========================================================================
# 10-11. Admin / Department lifecycle
# =========================================================================


def test_admin_department_transfer_creates_audit(client, db_session):
    sys_admin = _make_system_admin(db_session)
    old_department = make_department(db_session, name=f"Old Dept {uuid.uuid4()}")
    new_department = make_department(db_session, name=f"New Dept {uuid.uuid4()}")
    admin = _make_admin(db_session, old_department)

    response = client.patch(
        f"{ADMINS_URL}/{admin.id}/department",
        json={"department_id": str(new_department.id)},
        headers=_auth_headers(sys_admin),
    )
    assert response.status_code == 200

    entry = _latest_audit(db_session, "User", admin.id, "ADMIN_DEPARTMENT_CHANGED")
    assert entry is not None
    assert entry.user_id == sys_admin.id
    assert entry.old_values == {"department_id": str(old_department.id)}
    assert entry.new_values == {"department_id": str(new_department.id)}


def test_department_lifecycle_creates_audit(client, db_session):
    sys_admin = _make_system_admin(db_session)

    create_response = client.post(
        DEPARTMENTS_URL, json={"name": f"Lifecycle Dept {uuid.uuid4()}"}, headers=_auth_headers(sys_admin)
    )
    assert create_response.status_code == 201
    department_id = uuid.UUID(create_response.json()["id"])
    assert _latest_audit(db_session, "Department", department_id, "DEPARTMENT_CREATED") is not None

    deactivate_response = client.post(
        f"{DEPARTMENTS_URL}/{department_id}/deactivate", headers=_auth_headers(sys_admin)
    )
    assert deactivate_response.status_code == 200
    assert _latest_audit(db_session, "Department", department_id, "DEPARTMENT_DEACTIVATED") is not None

    activate_response = client.post(
        f"{DEPARTMENTS_URL}/{department_id}/activate", headers=_auth_headers(sys_admin)
    )
    assert activate_response.status_code == 200
    assert _latest_audit(db_session, "Department", department_id, "DEPARTMENT_ACTIVATED") is not None


def test_category_and_classification_lifecycle_creates_audit(client, db_session):
    sys_admin = _make_system_admin(db_session)

    cat_response = client.post(
        CATEGORIES_URL, json={"name": f"Audit Category {uuid.uuid4()}"}, headers=_auth_headers(sys_admin)
    )
    assert cat_response.status_code == 201
    category_id = uuid.UUID(cat_response.json()["id"])
    assert _latest_audit(db_session, "Category", category_id, "CATEGORY_CREATED") is not None

    client.post(f"{CATEGORIES_URL}/{category_id}/deactivate", headers=_auth_headers(sys_admin))
    assert _latest_audit(db_session, "Category", category_id, "CATEGORY_DEACTIVATED") is not None

    cls_response = client.post(
        CLASSIFICATIONS_URL,
        json={"name": f"Audit Classification {uuid.uuid4()}", "restricts_access": False},
        headers=_auth_headers(sys_admin),
    )
    assert cls_response.status_code == 201
    classification_id = uuid.UUID(cls_response.json()["id"])
    assert _latest_audit(db_session, "Classification", classification_id, "CLASSIFICATION_CREATED") is not None


# =========================================================================
# 12. Authorization lifecycle
# =========================================================================


def test_authorization_lifecycle_creates_audit(client, db_session):
    department = make_department(db_session, name=f"Audit Dept {uuid.uuid4()}")
    admin = _make_admin(db_session, department)

    create_response = client.post(
        f"{USERS_URL}/authorizations",
        json={"email": f"candidate.{uuid.uuid4()}@example.gov"},
        headers=_auth_headers(admin),
    )
    assert create_response.status_code == 201
    authorization_id = uuid.UUID(create_response.json()["id"])
    assert (
        _latest_audit(db_session, "UserAuthorization", authorization_id, "USER_AUTHORIZATION_CREATED")
        is not None
    )

    revoke_response = client.delete(
        f"{USERS_URL}/authorizations/{authorization_id}", headers=_auth_headers(admin)
    )
    assert revoke_response.status_code == 200
    assert (
        _latest_audit(db_session, "UserAuthorization", authorization_id, "USER_AUTHORIZATION_REVOKED")
        is not None
    )


def test_admin_authorization_creates_audit(client, db_session):
    sys_admin = _make_system_admin(db_session)
    department = make_department(db_session, name=f"Audit Dept {uuid.uuid4()}")

    response = client.post(
        f"{ADMINS_URL}/authorizations",
        json={"email": f"admin.candidate.{uuid.uuid4()}@example.gov", "department_id": str(department.id)},
        headers=_auth_headers(sys_admin),
    )
    assert response.status_code == 201
    authorization_id = uuid.UUID(response.json()["id"])

    entry = _latest_audit(db_session, "UserAuthorization", authorization_id, "ADMIN_AUTHORIZATION_CREATED")
    assert entry is not None
    assert entry.user_id == sys_admin.id


# =========================================================================
# 13-16. Actor/target correctness, targeted values, no sensitive data
# =========================================================================


def test_actor_is_the_caller_not_the_target(client, db_session):
    """Admin approves User: actor = Admin, target = User — never
    confused (docs/architecture/audit-notifications.md §6)."""
    department = make_department(db_session, name=f"Audit Dept {uuid.uuid4()}")
    admin = _make_admin(db_session, department)
    target = _make_regular_user(db_session, department)
    target.status = UserStatus.PENDING_APPROVAL
    db_session.flush()

    client.post(f"{USERS_URL}/{target.id}/approve", headers=_auth_headers(admin))

    entry = _latest_audit(db_session, "User", target.id, "USER_APPROVED")
    assert entry.user_id == admin.id
    assert entry.user_id != target.id
    assert entry.entity_id == target.id


def test_target_entity_type_and_id_are_correct(client, db_session):
    department = make_department(db_session, name=f"Audit Dept {uuid.uuid4()}")
    user = _make_regular_user(db_session, department)

    response = client.post(LETTERS_URL, json=_letter_payload(), headers=_auth_headers(user))
    letter_id = uuid.UUID(response.json()["id"])

    entry = _latest_audit(db_session, "Letter", letter_id, "LETTER_CREATED")
    assert entry.entity_type == "Letter"
    assert entry.entity_id == letter_id
    # Never the acting User's own id, unless it happens to equal the
    # letter's id (impossible — different tables, different UUIDs).
    assert entry.entity_id != user.id


def test_targeted_old_new_values_are_correct_not_full_snapshot(client, db_session):
    department = make_department(db_session, name=f"Audit Dept {uuid.uuid4()}")
    user = _make_regular_user(db_session, department)
    old_classification = make_classification(db_session, name=f"Old {uuid.uuid4()}")
    new_classification = make_classification(db_session, name=f"New {uuid.uuid4()}")
    letter = make_letter(db_session, department, user, classification=old_classification)

    client.patch(
        f"{LETTERS_URL}/{letter.id}",
        json={"classification_id": str(new_classification.id)},
        headers=_auth_headers(user),
    )

    entry = _latest_audit(db_session, "Letter", letter.id, "LETTER_CLASSIFICATION_CHANGED")
    # Only the targeted id pair — no other Letter field present.
    assert set(entry.old_values.keys()) == {"classification_id"}
    assert set(entry.new_values.keys()) == {"classification_id"}


def test_sensitive_values_are_never_stored_in_audit(client, db_session):
    department = make_department(db_session, name=f"Audit Dept {uuid.uuid4()}")
    user = _make_regular_user(db_session, department)
    secret_text = "TOP SECRET: attack plans and troop movements"

    response = client.post(
        LETTERS_URL,
        json=_letter_payload(text_content=secret_text, subject="A perfectly ordinary subject"),
        headers=_auth_headers(user),
    )
    letter_id = uuid.UUID(response.json()["id"])

    entries = _all_audit_for_entity(db_session, "Letter", letter_id)
    assert entries, "expected at least one audit entry"
    for entry in entries:
        blob = str(entry.old_values) + str(entry.new_values)
        assert secret_text not in blob
        assert "text_content" not in blob
        assert user.password_hash not in blob


# =========================================================================
# 17. Audit failure rolls back the business operation
# =========================================================================


def test_audit_failure_rolls_back_letter_creation(client, db_session, monkeypatch):
    department = make_department(db_session, name=f"Audit Dept {uuid.uuid4()}")
    user = _make_regular_user(db_session, department)

    def _boom(self, **kwargs):
        raise RuntimeError("simulated audit failure")

    monkeypatch.setattr(AuditService, "record", _boom)

    reference_number = f"REF-{uuid.uuid4()}"
    # TestClient re-raises unhandled server exceptions by default rather
    # than turning them into a 500 response — this project has no global
    # exception handler registered (unchanged, pre-existing behavior),
    # so the simulated failure surfaces here as a real exception.
    with pytest.raises(RuntimeError, match="simulated audit failure"):
        client.post(
            LETTERS_URL, json=_letter_payload(reference_number=reference_number), headers=_auth_headers(user)
        )

    # The letter was flushed (so it's visible within this still-open
    # transaction) but the audit failure happened before the service's
    # own `session.commit()` was ever reached — rolling back this
    # transaction must remove it entirely, proving the operation never
    # actually completed rather than merely appearing to via an
    # in-progress flush.
    db_session.rollback()
    remaining = db_session.execute(
        select(Letter).where(Letter.reference_number == reference_number)
    ).scalar_one_or_none()
    assert remaining is None


# =========================================================================
# 18. Audit entries cannot be modified/deleted through the API
# =========================================================================


def test_no_audit_mutation_endpoint_exists(client, db_session):
    department = make_department(db_session, name=f"Audit Dept {uuid.uuid4()}")
    sys_admin = _make_system_admin(db_session)
    user = _make_regular_user(db_session, department)
    response = client.post(LETTERS_URL, json=_letter_payload(), headers=_auth_headers(user))
    letter_id = response.json()["id"]
    entry = _latest_audit(db_session, "Letter", uuid.UUID(letter_id), "LETTER_CREATED")

    # No route exists anywhere under /api/v1 that could update or delete
    # this row — not even for SYSTEM_ADMIN.
    delete_response = client.delete(f"/api/v1/audit-logs/{entry.id}", headers=_auth_headers(sys_admin))
    assert delete_response.status_code in (404, 405)

    patch_response = client.patch(
        f"/api/v1/audit-logs/{entry.id}", json={"action": "TAMPERED"}, headers=_auth_headers(sys_admin)
    )
    assert patch_response.status_code in (404, 405)
