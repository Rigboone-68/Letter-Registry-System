"""End-to-end tests for the Letter registry core (Phase 4B).

Real JWTs, real database-backed Users/Departments/Categories/
Classifications, real HTTP requests through `/api/v1/letters*`, against a
real PostgreSQL test database — same pattern as every integration test
file since Phase 3A. Covers every lettered item (A-X) in the Phase 4B
brief's test list; Category/Classification management authorization
(items Y/Z) live in their own files
(test_category_management.py/test_classification_management.py).
"""

import uuid
from datetime import datetime, timezone

from app.core.security import create_access_token
from app.models.enums import ActiveStatus, UserRole
from tests.factories import (
    make_category,
    make_classification,
    make_department,
    make_letter,
    make_user,
)

LETTERS_URL = "/api/v1/letters"


def _letter_url(letter_id) -> str:
    return f"{LETTERS_URL}/{letter_id}"


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


def _valid_payload(**overrides):
    payload = {
        "reference_number": f"REF-{uuid.uuid4()}",
        "subject": "Test Subject",
        "source_name": "Test Source Organization",
        "sender_name": "Test Sender",
        "sender_designation": "Test Designation",
        "sender_department": "Test Sender Department",
        "received_at": datetime.now(timezone.utc).isoformat(),
    }
    payload.update(overrides)
    return payload


# =========================================================================
# A/T. CREATE LETTER — basic model fields
# =========================================================================


def test_create_letter_returns_all_fields(client, db_session):
    department = make_department(db_session, name="Create Dept 1")
    user = _make_regular_user(db_session, department, email="user.create1@example.gov")

    response = client.post(LETTERS_URL, json=_valid_payload(), headers=_auth_headers(user))

    assert response.status_code == 201
    body = response.json()
    assert body["subject"] == "Test Subject"
    assert body["source_name"] == "Test Source Organization"
    assert body["sender_name"] == "Test Sender"
    assert body["sender_designation"] == "Test Designation"
    assert body["sender_department"] == "Test Sender Department"
    assert body["status"] == "ACTIVE"
    assert body["recipient_department_id"] == str(department.id)


def test_admin_can_also_create_letter(client, db_session):
    department = make_department(db_session, name="Create Dept 2")
    admin = _make_department_admin(db_session, department, email="admin.create2@example.gov")
    response = client.post(LETTERS_URL, json=_valid_payload(), headers=_auth_headers(admin))
    assert response.status_code == 201


def test_system_admin_cannot_create_letter(client, db_session):
    sys_admin = _make_system_admin(db_session, email="sys.admin.create3@example.gov")
    response = client.post(LETTERS_URL, json=_valid_payload(), headers=_auth_headers(sys_admin))
    assert response.status_code == 403


# =========================================================================
# B. RECIPIENT DEPARTMENT RELATIONSHIP
# =========================================================================


def test_recipient_department_derived_from_recorder(client, db_session):
    department = make_department(db_session, name="Recipient Dept 1")
    user = _make_regular_user(db_session, department, email="user.recipient1@example.gov")
    response = client.post(LETTERS_URL, json=_valid_payload(), headers=_auth_headers(user))
    assert response.json()["recipient_department_id"] == str(department.id)


def test_client_cannot_inject_recipient_department(client, db_session):
    dept_a = make_department(db_session, name="Recipient Dept A2")
    dept_b = make_department(db_session, name="Recipient Dept B2")
    user = _make_regular_user(db_session, dept_a, email="user.recipient2@example.gov")

    response = client.post(
        LETTERS_URL,
        json=_valid_payload(recipient_department_id=str(dept_b.id)),
        headers=_auth_headers(user),
    )
    assert response.status_code == 422  # extra="forbid" — no such field


# =========================================================================
# C/D. SOURCE NAME / OPTIONAL SOURCE DEPARTMENT
# =========================================================================


def test_source_name_only_succeeds(client, db_session):
    department = make_department(db_session, name="Source Dept 1")
    user = _make_regular_user(db_session, department, email="user.source1@example.gov")
    response = client.post(
        LETTERS_URL, json=_valid_payload(source_name="External Vendor Ltd."), headers=_auth_headers(user)
    )
    assert response.status_code == 201
    assert response.json()["source_name"] == "External Vendor Ltd."
    assert response.json()["source_department_id"] is None


def test_source_department_optional_reference_succeeds(client, db_session):
    department = make_department(db_session, name="Source Dept 2")
    source_department = make_department(db_session, name="Planning and Development Dept")
    user = _make_regular_user(db_session, department, email="user.source2@example.gov")

    response = client.post(
        LETTERS_URL,
        json=_valid_payload(source_department_id=str(source_department.id)),
        headers=_auth_headers(user),
    )
    assert response.status_code == 201
    assert response.json()["source_department_id"] == str(source_department.id)


def test_nonexistent_source_department_rejected(client, db_session):
    department = make_department(db_session, name="Source Dept 3")
    user = _make_regular_user(db_session, department, email="user.source3@example.gov")
    response = client.post(
        LETTERS_URL,
        json=_valid_payload(source_department_id=str(uuid.uuid4())),
        headers=_auth_headers(user),
    )
    assert response.status_code == 404


def test_inactive_source_department_rejected(client, db_session):
    department = make_department(db_session, name="Source Dept 4")
    inactive_source = make_department(
        db_session, name="Retired Source Dept", status=ActiveStatus.INACTIVE
    )
    user = _make_regular_user(db_session, department, email="user.source4@example.gov")
    response = client.post(
        LETTERS_URL,
        json=_valid_payload(source_department_id=str(inactive_source.id)),
        headers=_auth_headers(user),
    )
    assert response.status_code == 409


# =========================================================================
# E. SOURCE LOCATION
# =========================================================================


def test_source_location_free_text_roundtrips(client, db_session):
    department = make_department(db_session, name="Location Dept 1")
    user = _make_regular_user(db_session, department, email="user.location1@example.gov")
    response = client.post(
        LETTERS_URL, json=_valid_payload(source_location="Quetta"), headers=_auth_headers(user)
    )
    assert response.status_code == 201
    assert response.json()["source_location"] == "Quetta"


def test_source_location_omitted_succeeds(client, db_session):
    department = make_department(db_session, name="Location Dept 2")
    user = _make_regular_user(db_session, department, email="user.location2@example.gov")
    response = client.post(LETTERS_URL, json=_valid_payload(), headers=_auth_headers(user))
    assert response.status_code == 201
    assert response.json()["source_location"] is None


# =========================================================================
# F/G/H/I. SENDER DETAILS
# =========================================================================


def test_missing_sender_name_rejected(client, db_session):
    department = make_department(db_session, name="Sender Dept 1")
    user = _make_regular_user(db_session, department, email="user.sender1@example.gov")
    payload = _valid_payload()
    del payload["sender_name"]
    response = client.post(LETTERS_URL, json=payload, headers=_auth_headers(user))
    assert response.status_code == 422


def test_missing_sender_designation_rejected(client, db_session):
    department = make_department(db_session, name="Sender Dept 2")
    user = _make_regular_user(db_session, department, email="user.sender2@example.gov")
    payload = _valid_payload()
    del payload["sender_designation"]
    response = client.post(LETTERS_URL, json=payload, headers=_auth_headers(user))
    assert response.status_code == 422


def test_missing_sender_department_rejected(client, db_session):
    department = make_department(db_session, name="Sender Dept 3")
    user = _make_regular_user(db_session, department, email="user.sender3@example.gov")
    payload = _valid_payload()
    del payload["sender_department"]
    response = client.post(LETTERS_URL, json=payload, headers=_auth_headers(user))
    assert response.status_code == 422


def test_sender_address_optional(client, db_session):
    department = make_department(db_session, name="Sender Dept 4")
    user = _make_regular_user(db_session, department, email="user.sender4@example.gov")

    without_address = client.post(LETTERS_URL, json=_valid_payload(), headers=_auth_headers(user))
    assert without_address.status_code == 201
    assert without_address.json()["sender_address"] is None

    with_address = client.post(
        LETTERS_URL,
        json=_valid_payload(
            reference_number=f"REF-{uuid.uuid4()}", sender_address="123 Main St, Quetta"
        ),
        headers=_auth_headers(user),
    )
    assert with_address.status_code == 201
    assert with_address.json()["sender_address"] == "123 Main St, Quetta"


# =========================================================================
# J/K. REFERENCE NUMBER
# =========================================================================


def test_reference_number_accepts_letters_numbers_special_characters(client, db_session):
    department = make_department(db_session, name="Ref Dept 1")
    user = _make_regular_user(db_session, department, email="user.ref1@example.gov")
    response = client.post(
        LETTERS_URL,
        json=_valid_payload(reference_number="REF/2026-A#001!"),
        headers=_auth_headers(user),
    )
    assert response.status_code == 201
    assert response.json()["reference_number"] == "REF/2026-A#001!"


def test_reference_number_required(client, db_session):
    department = make_department(db_session, name="Ref Dept 2")
    user = _make_regular_user(db_session, department, email="user.ref2@example.gov")
    payload = _valid_payload()
    del payload["reference_number"]
    response = client.post(LETTERS_URL, json=payload, headers=_auth_headers(user))
    assert response.status_code == 422


def test_duplicate_reference_number_currently_allowed_pending_clarification(client, db_session):
    """Hardening-pass finding: the business confirmed reference numbers
    "must be unique" but never confirmed the *scope* (global? per
    receiving department? per source? per year?). A global
    `UniqueConstraint` was implemented first, then removed
    (migration `c887ab35e4a3`) rather than kept on a guess or replaced
    with a different guessed scope — see
    docs/architecture/letter-registry.md §2.3/§12, PENDING BUSINESS
    CLARIFICATION. This test locks in and documents the current,
    deliberately permissive behavior so a future change is a conscious
    decision, not a silent regression."""
    department = make_department(db_session, name="Ref Dept 3")
    user = _make_regular_user(db_session, department, email="user.ref3@example.gov")
    payload = _valid_payload(reference_number="DUPLICATE-REF-001")

    first = client.post(LETTERS_URL, json=payload, headers=_auth_headers(user))
    assert first.status_code == 201
    second_payload = _valid_payload(reference_number="DUPLICATE-REF-001")
    second = client.post(LETTERS_URL, json=second_payload, headers=_auth_headers(user))
    assert second.status_code == 201


def test_duplicate_reference_number_currently_allowed_across_departments(client, db_session):
    """Same finding as above, across departments — a plausible real-world
    case (two departments each issuing their own overlapping numbering),
    which is exactly why global uniqueness was removed rather than kept
    as a safe-sounding default."""
    dept_a = make_department(db_session, name="Ref Dept A4")
    dept_b = make_department(db_session, name="Ref Dept B4")
    user_a = _make_regular_user(db_session, dept_a, email="user.ref4a@example.gov")
    user_b = _make_regular_user(db_session, dept_b, email="user.ref4b@example.gov")

    first = client.post(
        LETTERS_URL, json=_valid_payload(reference_number="SHARED-REF-001"), headers=_auth_headers(user_a)
    )
    assert first.status_code == 201
    second = client.post(
        LETTERS_URL, json=_valid_payload(reference_number="SHARED-REF-001"), headers=_auth_headers(user_b)
    )
    assert second.status_code == 201


def test_reference_number_never_auto_generated_if_not_supplied(client, db_session):
    department = make_department(db_session, name="Ref Dept 5")
    user = _make_regular_user(db_session, department, email="user.ref5@example.gov")
    payload = _valid_payload()
    del payload["reference_number"]
    response = client.post(LETTERS_URL, json=payload, headers=_auth_headers(user))
    assert response.status_code == 422  # rejected, not silently generated


# =========================================================================
# L/M. CATEGORY
# =========================================================================


def test_valid_active_category_accepted(client, db_session):
    department = make_department(db_session, name="Category Dept 1")
    user = _make_regular_user(db_session, department, email="user.cat1@example.gov")
    category = make_category(db_session, name="General Letter Test")

    response = client.post(
        LETTERS_URL, json=_valid_payload(category_id=str(category.id)), headers=_auth_headers(user)
    )
    assert response.status_code == 201
    assert response.json()["category_id"] == str(category.id)


def test_nonexistent_category_rejected(client, db_session):
    department = make_department(db_session, name="Category Dept 2")
    user = _make_regular_user(db_session, department, email="user.cat2@example.gov")
    response = client.post(
        LETTERS_URL, json=_valid_payload(category_id=str(uuid.uuid4())), headers=_auth_headers(user)
    )
    assert response.status_code == 404


def test_inactive_category_rejected(client, db_session):
    department = make_department(db_session, name="Category Dept 3")
    user = _make_regular_user(db_session, department, email="user.cat3@example.gov")
    category = make_category(db_session, name="Retired Category", status=ActiveStatus.INACTIVE)
    response = client.post(
        LETTERS_URL, json=_valid_payload(category_id=str(category.id)), headers=_auth_headers(user)
    )
    assert response.status_code == 409


def test_category_optional_at_creation(client, db_session):
    department = make_department(db_session, name="Category Dept 4")
    user = _make_regular_user(db_session, department, email="user.cat4@example.gov")
    response = client.post(LETTERS_URL, json=_valid_payload(), headers=_auth_headers(user))
    assert response.status_code == 201
    assert response.json()["category_id"] is None


# =========================================================================
# N. CLASSIFICATION
# =========================================================================


def test_valid_active_classification_accepted(client, db_session):
    department = make_department(db_session, name="Classification Dept 1")
    user = _make_regular_user(db_session, department, email="user.cls1@example.gov")
    classification = make_classification(db_session, name="Routine Test")

    response = client.post(
        LETTERS_URL,
        json=_valid_payload(classification_id=str(classification.id)),
        headers=_auth_headers(user),
    )
    assert response.status_code == 201
    assert response.json()["classification_id"] == str(classification.id)


def test_nonexistent_classification_rejected(client, db_session):
    department = make_department(db_session, name="Classification Dept 2")
    user = _make_regular_user(db_session, department, email="user.cls2@example.gov")
    response = client.post(
        LETTERS_URL,
        json=_valid_payload(classification_id=str(uuid.uuid4())),
        headers=_auth_headers(user),
    )
    assert response.status_code == 404


def test_inactive_classification_rejected(client, db_session):
    department = make_department(db_session, name="Classification Dept 3")
    user = _make_regular_user(db_session, department, email="user.cls3@example.gov")
    classification = make_classification(
        db_session, name="Retired Classification", status=ActiveStatus.INACTIVE
    )
    response = client.post(
        LETTERS_URL,
        json=_valid_payload(classification_id=str(classification.id)),
        headers=_auth_headers(user),
    )
    assert response.status_code == 409


# =========================================================================
# O/P. RECORDED BY
# =========================================================================


def test_recorded_by_comes_from_authenticated_user(client, db_session):
    department = make_department(db_session, name="Recorded Dept 1")
    user = _make_regular_user(db_session, department, email="user.recorded1@example.gov")
    response = client.post(LETTERS_URL, json=_valid_payload(), headers=_auth_headers(user))
    assert response.json()["recorded_by"] == str(user.id)


def test_client_cannot_override_recorded_by(client, db_session):
    department = make_department(db_session, name="Recorded Dept 2")
    user = _make_regular_user(db_session, department, email="user.recorded2@example.gov")
    other_user = _make_regular_user(db_session, department, email="other.recorded2@example.gov")

    response = client.post(
        LETTERS_URL,
        json=_valid_payload(recorded_by=str(other_user.id)),
        headers=_auth_headers(user),
    )
    assert response.status_code == 422  # extra="forbid" — no such field


# =========================================================================
# Q/R. DEPARTMENT ISOLATION
# =========================================================================


def test_admin_cannot_get_letter_in_another_department(client, db_session):
    dept_a = make_department(db_session, name="Isolation Dept A1")
    dept_b = make_department(db_session, name="Isolation Dept B1")
    user_b = _make_regular_user(db_session, dept_b, email="user.iso1b@example.gov")
    admin_a = _make_department_admin(db_session, dept_a, email="admin.iso1a@example.gov")

    create_resp = client.post(LETTERS_URL, json=_valid_payload(), headers=_auth_headers(user_b))
    letter_id = create_resp.json()["id"]

    response = client.get(_letter_url(letter_id), headers=_auth_headers(admin_a))
    assert response.status_code == 404


def test_letter_list_excludes_other_departments(client, db_session):
    dept_a = make_department(db_session, name="Isolation Dept A2")
    dept_b = make_department(db_session, name="Isolation Dept B2")
    user_a = _make_regular_user(db_session, dept_a, email="user.iso2a@example.gov")
    user_b = _make_regular_user(db_session, dept_b, email="user.iso2b@example.gov")

    client.post(LETTERS_URL, json=_valid_payload(reference_number="ISO2-A"), headers=_auth_headers(user_a))
    client.post(LETTERS_URL, json=_valid_payload(reference_number="ISO2-B"), headers=_auth_headers(user_b))

    response = client.get(LETTERS_URL, headers=_auth_headers(user_a))
    reference_numbers = {item["reference_number"] for item in response.json()["items"]}
    assert "ISO2-A" in reference_numbers
    assert "ISO2-B" not in reference_numbers


def test_admin_cannot_update_letter_in_another_department(client, db_session):
    dept_a = make_department(db_session, name="Isolation Dept A3")
    dept_b = make_department(db_session, name="Isolation Dept B3")
    user_b = _make_regular_user(db_session, dept_b, email="user.iso3b@example.gov")
    admin_a = _make_department_admin(db_session, dept_a, email="admin.iso3a@example.gov")

    create_resp = client.post(LETTERS_URL, json=_valid_payload(), headers=_auth_headers(user_b))
    letter_id = create_resp.json()["id"]

    response = client.patch(
        _letter_url(letter_id), json={"subject": "Hijacked"}, headers=_auth_headers(admin_a)
    )
    assert response.status_code == 404


def test_admin_cannot_archive_letter_in_another_department(client, db_session):
    dept_a = make_department(db_session, name="Isolation Dept A4")
    dept_b = make_department(db_session, name="Isolation Dept B4")
    user_b = _make_regular_user(db_session, dept_b, email="user.iso4b@example.gov")
    admin_a = _make_department_admin(db_session, dept_a, email="admin.iso4a@example.gov")

    create_resp = client.post(LETTERS_URL, json=_valid_payload(), headers=_auth_headers(user_b))
    letter_id = create_resp.json()["id"]

    response = client.delete(_letter_url(letter_id), headers=_auth_headers(admin_a))
    assert response.status_code == 404


def test_system_admin_can_view_any_department_letter(client, db_session):
    department = make_department(db_session, name="SysAdmin Visibility Dept")
    user = _make_regular_user(db_session, department, email="user.sysvis@example.gov")
    sys_admin = _make_system_admin(db_session, email="sys.admin.sysvis@example.gov")

    create_resp = client.post(LETTERS_URL, json=_valid_payload(), headers=_auth_headers(user))
    letter_id = create_resp.json()["id"]

    response = client.get(_letter_url(letter_id), headers=_auth_headers(sys_admin))
    assert response.status_code == 200


# =========================================================================
# S. CLASSIFIED LETTER AUTHORIZATION BOUNDARY
# =========================================================================


def test_user_who_did_not_record_cannot_view_classified_letter(client, db_session):
    department = make_department(db_session, name="Classified Dept 1")
    recorder = _make_regular_user(db_session, department, email="recorder.classified1@example.gov")
    other_user = _make_regular_user(db_session, department, email="other.classified1@example.gov")
    classification = make_classification(db_session, name="Classified Test 1", restricts_access=True)

    create_resp = client.post(
        LETTERS_URL,
        json=_valid_payload(classification_id=str(classification.id)),
        headers=_auth_headers(recorder),
    )
    letter_id = create_resp.json()["id"]

    response = client.get(_letter_url(letter_id), headers=_auth_headers(other_user))
    assert response.status_code == 404  # hidden, not 403 — see LetterNotFoundError


def test_recorder_can_view_own_classified_letter(client, db_session):
    department = make_department(db_session, name="Classified Dept 2")
    recorder = _make_regular_user(db_session, department, email="recorder.classified2@example.gov")
    classification = make_classification(db_session, name="Classified Test 2", restricts_access=True)

    create_resp = client.post(
        LETTERS_URL,
        json=_valid_payload(classification_id=str(classification.id)),
        headers=_auth_headers(recorder),
    )
    letter_id = create_resp.json()["id"]

    response = client.get(_letter_url(letter_id), headers=_auth_headers(recorder))
    assert response.status_code == 200


def test_admin_can_view_classified_letter_in_own_department(client, db_session):
    department = make_department(db_session, name="Classified Dept 3")
    recorder = _make_regular_user(db_session, department, email="recorder.classified3@example.gov")
    admin = _make_department_admin(db_session, department, email="admin.classified3@example.gov")
    classification = make_classification(db_session, name="Classified Test 3", restricts_access=True)

    create_resp = client.post(
        LETTERS_URL,
        json=_valid_payload(classification_id=str(classification.id)),
        headers=_auth_headers(recorder),
    )
    letter_id = create_resp.json()["id"]

    response = client.get(_letter_url(letter_id), headers=_auth_headers(admin))
    assert response.status_code == 200


def test_system_admin_can_view_classified_letter(client, db_session):
    department = make_department(db_session, name="Classified Dept 4")
    recorder = _make_regular_user(db_session, department, email="recorder.classified4@example.gov")
    sys_admin = _make_system_admin(db_session, email="sys.admin.classified4@example.gov")
    classification = make_classification(db_session, name="Classified Test 4", restricts_access=True)

    create_resp = client.post(
        LETTERS_URL,
        json=_valid_payload(classification_id=str(classification.id)),
        headers=_auth_headers(recorder),
    )
    letter_id = create_resp.json()["id"]

    response = client.get(_letter_url(letter_id), headers=_auth_headers(sys_admin))
    assert response.status_code == 200


def test_non_restricting_classification_visible_to_every_department_user(client, db_session):
    department = make_department(db_session, name="Classified Dept 5")
    recorder = _make_regular_user(db_session, department, email="recorder.classified5@example.gov")
    other_user = _make_regular_user(db_session, department, email="other.classified5@example.gov")
    classification = make_classification(db_session, name="Routine Test 5", restricts_access=False)

    create_resp = client.post(
        LETTERS_URL,
        json=_valid_payload(classification_id=str(classification.id)),
        headers=_auth_headers(recorder),
    )
    letter_id = create_resp.json()["id"]

    response = client.get(_letter_url(letter_id), headers=_auth_headers(other_user))
    assert response.status_code == 200


def test_classified_letter_excluded_from_non_recorder_users_list(client, db_session):
    department = make_department(db_session, name="Classified Dept 6")
    recorder = _make_regular_user(db_session, department, email="recorder.classified6@example.gov")
    other_user = _make_regular_user(db_session, department, email="other.classified6@example.gov")
    classification = make_classification(db_session, name="Classified Test 6", restricts_access=True)

    client.post(
        LETTERS_URL,
        json=_valid_payload(reference_number="CLASSIFIED-6", classification_id=str(classification.id)),
        headers=_auth_headers(recorder),
    )

    response = client.get(LETTERS_URL, headers=_auth_headers(other_user))
    reference_numbers = {item["reference_number"] for item in response.json()["items"]}
    assert "CLASSIFIED-6" not in reference_numbers


def test_user_who_did_not_record_cannot_update_classified_letter(client, db_session):
    department = make_department(db_session, name="Classified Dept 7")
    recorder = _make_regular_user(db_session, department, email="recorder.classified7@example.gov")
    other_user = _make_regular_user(db_session, department, email="other.classified7@example.gov")
    classification = make_classification(db_session, name="Classified Test 7", restricts_access=True)

    create_resp = client.post(
        LETTERS_URL,
        json=_valid_payload(classification_id=str(classification.id)),
        headers=_auth_headers(recorder),
    )
    letter_id = create_resp.json()["id"]

    response = client.patch(
        _letter_url(letter_id), json={"subject": "Hijacked"}, headers=_auth_headers(other_user)
    )
    assert response.status_code == 404


# =========================================================================
# U. RETRIEVE LETTER
# =========================================================================


def test_get_letter_success(client, db_session):
    department = make_department(db_session, name="Retrieve Dept 1")
    user = _make_regular_user(db_session, department, email="user.retrieve1@example.gov")
    create_resp = client.post(LETTERS_URL, json=_valid_payload(), headers=_auth_headers(user))
    letter_id = create_resp.json()["id"]

    response = client.get(_letter_url(letter_id), headers=_auth_headers(user))
    assert response.status_code == 200
    assert response.json()["id"] == letter_id


def test_get_nonexistent_letter_returns_404(client, db_session):
    department = make_department(db_session, name="Retrieve Dept 2")
    user = _make_regular_user(db_session, department, email="user.retrieve2@example.gov")
    response = client.get(_letter_url(uuid.uuid4()), headers=_auth_headers(user))
    assert response.status_code == 404


# =========================================================================
# V. UPDATE LETTER
# =========================================================================


def test_update_letter_persists_changes(client, db_session):
    department = make_department(db_session, name="Update Dept 1")
    user = _make_regular_user(db_session, department, email="user.update1@example.gov")
    create_resp = client.post(LETTERS_URL, json=_valid_payload(), headers=_auth_headers(user))
    letter_id = create_resp.json()["id"]

    response = client.patch(
        _letter_url(letter_id),
        json={"subject": "Updated Subject", "source_location": "Karachi"},
        headers=_auth_headers(user),
    )
    assert response.status_code == 200
    assert response.json()["subject"] == "Updated Subject"
    assert response.json()["source_location"] == "Karachi"

    reget = client.get(_letter_url(letter_id), headers=_auth_headers(user))
    assert reget.json()["subject"] == "Updated Subject"


def test_update_letter_to_duplicate_reference_number_currently_allowed(client, db_session):
    """Same hardening-pass finding as
    test_duplicate_reference_number_currently_allowed_pending_clarification
    — no uniqueness constraint exists, so this update succeeds rather
    than conflicting."""
    department = make_department(db_session, name="Update Dept 2")
    user = _make_regular_user(db_session, department, email="user.update2@example.gov")
    client.post(
        LETTERS_URL, json=_valid_payload(reference_number="UPDATE2-TAKEN"), headers=_auth_headers(user)
    )
    second = client.post(
        LETTERS_URL, json=_valid_payload(reference_number="UPDATE2-FREE"), headers=_auth_headers(user)
    )
    letter_id = second.json()["id"]

    response = client.patch(
        _letter_url(letter_id),
        json={"reference_number": "UPDATE2-TAKEN"},
        headers=_auth_headers(user),
    )
    assert response.status_code == 200
    assert response.json()["reference_number"] == "UPDATE2-TAKEN"


def test_admin_can_update_letter_in_own_department(client, db_session):
    department = make_department(db_session, name="Update Dept 3")
    user = _make_regular_user(db_session, department, email="user.update3@example.gov")
    admin = _make_department_admin(db_session, department, email="admin.update3@example.gov")

    create_resp = client.post(LETTERS_URL, json=_valid_payload(), headers=_auth_headers(user))
    letter_id = create_resp.json()["id"]

    response = client.patch(
        _letter_url(letter_id), json={"subject": "Admin Updated"}, headers=_auth_headers(admin)
    )
    assert response.status_code == 200
    assert response.json()["subject"] == "Admin Updated"


# =========================================================================
# W. DELETE (ARCHIVE) LETTER
# =========================================================================


def test_archive_letter_sets_status_archived_not_physical_delete(client, db_session):
    department = make_department(db_session, name="Archive Dept 1")
    user = _make_regular_user(db_session, department, email="user.archive1@example.gov")
    create_resp = client.post(LETTERS_URL, json=_valid_payload(), headers=_auth_headers(user))
    letter_id = create_resp.json()["id"]

    response = client.delete(_letter_url(letter_id), headers=_auth_headers(user))
    assert response.status_code == 200
    assert response.json()["status"] == "ARCHIVED"

    # Still retrievable — never physically deleted.
    reget = client.get(_letter_url(letter_id), headers=_auth_headers(user))
    assert reget.status_code == 200
    assert reget.json()["status"] == "ARCHIVED"


def test_archive_is_idempotent(client, db_session):
    department = make_department(db_session, name="Archive Dept 2")
    user = _make_regular_user(db_session, department, email="user.archive2@example.gov")
    create_resp = client.post(LETTERS_URL, json=_valid_payload(), headers=_auth_headers(user))
    letter_id = create_resp.json()["id"]

    first = client.delete(_letter_url(letter_id), headers=_auth_headers(user))
    assert first.status_code == 200
    second = client.delete(_letter_url(letter_id), headers=_auth_headers(user))
    assert second.status_code == 200
    assert second.json()["status"] == "ARCHIVED"


def test_archive_letter_in_another_department_rejected(client, db_session):
    dept_a = make_department(db_session, name="Archive Dept A3")
    dept_b = make_department(db_session, name="Archive Dept B3")
    user_a = _make_regular_user(db_session, dept_a, email="user.archive3a@example.gov")
    user_b = _make_regular_user(db_session, dept_b, email="user.archive3b@example.gov")

    create_resp = client.post(LETTERS_URL, json=_valid_payload(), headers=_auth_headers(user_b))
    letter_id = create_resp.json()["id"]

    response = client.delete(_letter_url(letter_id), headers=_auth_headers(user_a))
    assert response.status_code == 404


# =========================================================================
# X. HISTORICAL DEPARTMENT OWNERSHIP (invariant proof, not a migration replay
# — the migration itself was verified manually against a real pre-existing
# row; see the Phase 4B final report and docs/architecture/letter-registry.md
# §4/§6. This proves the same *invariant* the migration must preserve:
# recipient_department_id is independently stored, never re-derived from
# recorded_by_user.department_id, exactly mirroring the precedent
# tests/integration/test_admin_management.py::test_transfer_does_not_rewrite_historical_records.)
# =========================================================================


def test_letter_recipient_department_survives_recorders_department_transfer(client, db_session):
    from app.models.letter import Letter

    department_a = make_department(db_session, name="Historical Dept A1")
    department_b = make_department(db_session, name="Historical Dept B1")
    sys_admin = _make_system_admin(db_session, email="sys.admin.historical1@example.gov")
    admin = _make_department_admin(db_session, department_a, email="admin.historical1@example.gov")

    create_resp = client.post(LETTERS_URL, json=_valid_payload(), headers=_auth_headers(admin))
    letter_id = create_resp.json()["id"]
    assert create_resp.json()["recipient_department_id"] == str(department_a.id)

    transfer_resp = client.patch(
        f"/api/v1/admins/{admin.id}/department",
        json={"department_id": str(department_b.id)},
        headers=_auth_headers(sys_admin),
    )
    assert transfer_resp.status_code == 200

    db_session.expire_all()
    reloaded_letter = db_session.get(Letter, uuid.UUID(letter_id))
    assert reloaded_letter.recipient_department_id == department_a.id  # unchanged
