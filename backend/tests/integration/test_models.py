"""Model-level tests for the Phase 2 core schema.

Requires a live PostgreSQL test database (see backend/tests/conftest.py and
docs/database/README.md). Tests are skipped automatically if none is
reachable — they are never run against SQLite or any other stand-in, because
this schema depends on PostgreSQL-specific behavior (native enums, JSONB,
functional unique indexes) that a stand-in database cannot faithfully
reproduce.

No application logic (services, repositories, API) exists yet, so these
tests exercise the ORM layer directly: creating rows, relationship
navigation, and constraints enforced by the database itself.
"""

import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from app.models import (
    AuditLog,
    Category,
    Classification,
    Department,
    Letter,
    LetterDocument,
    Notification,
    User,
    UserAuthorization,
)
from app.models.enums import ActiveStatus, AuthorizationStatus, LetterStatus, UserRole, UserStatus


def make_department(db_session, name="Ministry of Testing", code=None):
    department = Department(name=name, code=code)
    db_session.add(department)
    db_session.flush()
    return department


def make_user(db_session, department, role=UserRole.USER, email="user@example.gov", full_name="Test User"):
    user = User(
        full_name=full_name,
        email=email,
        password_hash="not-a-real-hash",
        role=role,
        department_id=department.id if department else None,
        status=UserStatus.ACTIVE,
    )
    db_session.add(user)
    db_session.flush()
    return user


# 1. Department creation -----------------------------------------------------

def test_department_creation(db_session):
    department = make_department(db_session, name="Department of Roads")
    assert department.id is not None
    assert department.status == ActiveStatus.ACTIVE
    assert department.created_at is not None
    assert department.created_at.tzinfo is not None


# 2. User creation ------------------------------------------------------------

def test_user_creation(db_session):
    department = make_department(db_session, name="Department of Finance")
    user = make_user(db_session, department, email="finance.user@example.gov")
    assert user.id is not None
    assert user.status == UserStatus.ACTIVE
    assert user.password_hash == "not-a-real-hash"


# 3. User -> Department relationship ------------------------------------------

def test_user_department_relationship(db_session):
    department = make_department(db_session, name="Department of Health")
    user = make_user(db_session, department, email="health.user@example.gov")
    db_session.refresh(user)
    db_session.refresh(department)

    assert user.department.id == department.id
    assert user in department.users


# 4-6. Role/department pairing — every combination the CHECK constraint governs.
# ck_users_role_department_pairing: SYSTEM_ADMIN <-> no department,
# ADMIN/USER <-> a department, in both directions (accept the valid pairing,
# reject the invalid one). See app/models/user.py for why this is a CHECK
# constraint built from UserRole.*.value rather than typed-out literals.

@pytest.mark.parametrize(
    "role,has_department,should_succeed",
    [
        (UserRole.SYSTEM_ADMIN, False, True),
        (UserRole.SYSTEM_ADMIN, True, False),
        (UserRole.ADMIN, True, True),
        (UserRole.ADMIN, False, False),
        (UserRole.USER, True, True),
        (UserRole.USER, False, False),
    ],
    ids=[
        "system_admin-no_department-accepted",
        "system_admin-with_department-rejected",
        "admin-with_department-accepted",
        "admin-no_department-rejected",
        "user-with_department-accepted",
        "user-no_department-rejected",
    ],
)
def test_role_department_pairing_constraint(db_session, role, has_department, should_succeed):
    department = (
        make_department(db_session, name=f"Dept for {role.value}-{has_department}")
        if has_department
        else None
    )
    user = User(
        full_name="Constraint Test User",
        email=f"constraint-{role.value.lower()}-{has_department}@example.gov",
        password_hash="hash",
        role=role,
        department_id=department.id if department else None,
        status=UserStatus.ACTIVE,
    )
    db_session.add(user)

    if should_succeed:
        db_session.flush()
        assert user.id is not None
        assert (user.department_id is not None) == has_department
    else:
        with pytest.raises(IntegrityError) as exc_info:
            db_session.flush()
        assert "ck_users_role_department_pairing" in str(exc_info.value.orig)


# 7. UserAuthorization relationship --------------------------------------------

def test_user_authorization_relationship(db_session):
    department = make_department(db_session, name="Department of Interior")
    admin = make_user(
        db_session, department, role=UserRole.ADMIN, email="interior.admin@example.gov"
    )

    authorization = UserAuthorization(
        email="new.hire@example.gov",
        department_id=department.id,
        authorized_by=admin.id,
        status=AuthorizationStatus.ACTIVE,
    )
    db_session.add(authorization)
    db_session.flush()
    db_session.refresh(admin)
    db_session.refresh(department)

    assert authorization.department.id == department.id
    assert authorization.authorized_by_user.id == admin.id
    assert authorization in department.user_authorizations
    assert authorization in admin.authorizations_created


# 8. Category -> Letter relationship -------------------------------------------

def test_category_letter_relationship(db_session):
    department = make_department(db_session, name="Department of Legal Affairs")
    recorder = make_user(db_session, department, email="legal.clerk@example.gov")
    category = Category(name="Legal")
    db_session.add(category)
    db_session.flush()

    letter = Letter(
        reference_number=f"REF-{uuid.uuid4()}",
        recipient_department_id=department.id,
        source_name="Office of the Attorney General",
        sender_name="A. General",
        sender_designation="Attorney General",
        sender_department="Office of the Attorney General",
        received_at=datetime.now(timezone.utc),
        recorded_by=recorder.id,
        category_id=category.id,
    )
    db_session.add(letter)
    db_session.flush()
    db_session.refresh(category)

    assert letter.category.id == category.id
    assert letter in category.letters


# 9. Classification -> Letter relationship -------------------------------------

def test_classification_letter_relationship(db_session):
    department = make_department(db_session, name="Department of Procurement")
    recorder = make_user(db_session, department, email="procurement.clerk@example.gov")
    classification = Classification(name="Routine")
    db_session.add(classification)
    db_session.flush()

    letter = Letter(
        reference_number=f"REF-{uuid.uuid4()}",
        recipient_department_id=department.id,
        source_name="Vendor XYZ Ltd.",
        sender_name="J. Vendor",
        sender_designation="Account Manager",
        sender_department="Vendor XYZ Ltd.",
        received_at=datetime.now(timezone.utc),
        recorded_by=recorder.id,
        classification_id=classification.id,
    )
    db_session.add(letter)
    db_session.flush()
    db_session.refresh(classification)

    assert letter.classification.id == classification.id
    assert letter in classification.letters


# 10. Letter -> Department relationship ----------------------------------------

def test_letter_department_relationship(db_session):
    department = make_department(db_session, name="Department of Agriculture")
    recorder = make_user(db_session, department, email="agriculture.clerk@example.gov")

    letter = Letter(
        reference_number=f"REF-{uuid.uuid4()}",
        recipient_department_id=department.id,
        source_name="Regional Farmers Union",
        sender_name="F. Union",
        sender_designation="Secretary",
        sender_department="Regional Farmers Union",
        received_at=datetime.now(timezone.utc),
        recorded_by=recorder.id,
    )
    db_session.add(letter)
    db_session.flush()
    db_session.refresh(department)

    assert letter.recipient_department.id == department.id
    assert letter in department.letters


# 11. Letter -> recorded_by relationship ---------------------------------------

def test_letter_recorded_by_relationship(db_session):
    department = make_department(db_session, name="Department of Housing")
    recorder = make_user(db_session, department, email="housing.clerk@example.gov")

    letter = Letter(
        reference_number=f"REF-{uuid.uuid4()}",
        recipient_department_id=department.id,
        source_name="National Housing Authority",
        sender_name="H. Authority",
        sender_designation="Director",
        sender_department="National Housing Authority",
        received_at=datetime.now(timezone.utc),
        recorded_by=recorder.id,
    )
    db_session.add(letter)
    db_session.flush()
    db_session.refresh(recorder)

    assert letter.recorded_by_user.id == recorder.id
    assert letter in recorder.letters_recorded


# 12. Letter -> multiple LetterDocuments ----------------------------------------

def test_letter_multiple_documents(db_session):
    department = make_department(db_session, name="Department of Energy")
    recorder = make_user(db_session, department, email="energy.clerk@example.gov")

    letter = Letter(
        reference_number=f"REF-{uuid.uuid4()}",
        recipient_department_id=department.id,
        source_name="Regional Power Authority",
        sender_name="P. Authority",
        sender_designation="Engineer",
        sender_department="Regional Power Authority",
        received_at=datetime.now(timezone.utc),
        recorded_by=recorder.id,
    )
    db_session.add(letter)
    db_session.flush()

    doc_one = LetterDocument(
        letter_id=letter.id,
        original_filename="cover-letter.pdf",
        storage_path="2026/08/cover-letter.pdf",
        uploaded_by=recorder.id,
    )
    doc_two = LetterDocument(
        letter_id=letter.id,
        original_filename="attachment.pdf",
        storage_path="2026/08/attachment.pdf",
        uploaded_by=recorder.id,
    )
    db_session.add_all([doc_one, doc_two])
    db_session.flush()
    db_session.refresh(letter)

    assert len(letter.documents) == 2
    assert {doc.original_filename for doc in letter.documents} == {
        "cover-letter.pdf",
        "attachment.pdf",
    }


# 13. Notification -> User and Letter --------------------------------------------

def test_notification_user_and_letter(db_session):
    department = make_department(db_session, name="Department of Communications")
    recorder = make_user(db_session, department, email="comms.clerk@example.gov")
    admin = make_user(
        db_session,
        department,
        role=UserRole.ADMIN,
        email="comms.admin@example.gov",
        full_name="Comms Admin",
    )

    letter = Letter(
        reference_number=f"REF-{uuid.uuid4()}",
        recipient_department_id=department.id,
        source_name="Press Office",
        sender_name="P. Officer",
        sender_designation="Press Secretary",
        sender_department="Press Office",
        received_at=datetime.now(timezone.utc),
        recorded_by=recorder.id,
    )
    db_session.add(letter)
    db_session.flush()

    notification = Notification(
        recipient_user_id=admin.id,
        letter_id=letter.id,
        notification_type="LETTER_REGISTERED",
        message="A new letter has been registered.",
    )
    db_session.add(notification)
    db_session.flush()
    db_session.refresh(admin)
    db_session.refresh(letter)

    assert notification.recipient.id == admin.id
    assert notification.letter.id == letter.id
    assert notification.is_read is False
    assert notification in admin.notifications
    assert notification in letter.notifications


# 14. AuditLog creation -----------------------------------------------------------

def test_audit_log_creation(db_session):
    department = make_department(db_session, name="Department of Justice")
    actor = make_user(db_session, department, email="justice.clerk@example.gov")

    entry = AuditLog(
        user_id=actor.id,
        action="CREATE",
        entity_type="Letter",
        entity_id=None,
        old_values=None,
        new_values={"subject": "Sample subject"},
    )
    db_session.add(entry)
    db_session.flush()
    db_session.refresh(actor)

    assert entry.id is not None
    assert entry.user.id == actor.id
    assert entry.new_values == {"subject": "Sample subject"}
    assert entry in actor.audit_logs


def test_audit_log_allows_null_user_for_system_actions(db_session):
    entry = AuditLog(
        user_id=None,
        action="SYSTEM_MAINTENANCE",
        entity_type="Letter",
        entity_id=None,
    )
    db_session.add(entry)
    db_session.flush()
    assert entry.user_id is None
    assert entry.user is None


# 15. Uniqueness constraints -------------------------------------------------------

def test_department_name_uniqueness(db_session):
    make_department(db_session, name="Duplicate Department")
    db_session.flush()
    with pytest.raises(IntegrityError):
        make_department(db_session, name="Duplicate Department")


def test_user_email_uniqueness_is_case_insensitive(db_session):
    department = make_department(db_session, name="Department of Trade")
    make_user(db_session, department, email="clerk@example.gov")
    db_session.flush()
    with pytest.raises(IntegrityError):
        make_user(
            db_session,
            department,
            email="CLERK@example.gov",
            full_name="Different Person, Same Email",
        )


def test_category_name_uniqueness(db_session):
    db_session.add(Category(name="Budget"))
    db_session.flush()
    db_session.add(Category(name="Budget"))
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_classification_name_uniqueness(db_session):
    db_session.add(Classification(name="Confidential"))
    db_session.flush()
    db_session.add(Classification(name="Confidential"))
    with pytest.raises(IntegrityError):
        db_session.flush()


# 16. ON DELETE RESTRICT — Department -------------------------------------------
# Regression coverage for the Phase 2 self-review finding: deleting a
# Department with dependent Users must be blocked by the database's FK
# RESTRICT, not by SQLAlchemy's default "null out the child FK first"
# behavior (which used to surface a confusing CHECK-constraint error
# instead — see passive_deletes="all" on Department.users in
# app/models/department.py).

def test_department_deletion_restricted_by_dependent_user(db_session):
    department = make_department(db_session, name="Restrict Test Department")
    make_user(db_session, department, email="restrict.user@example.gov")
    db_session.flush()

    db_session.delete(department)
    with pytest.raises(IntegrityError) as exc_info:
        db_session.flush()
    message = str(exc_info.value.orig).lower()
    assert "foreign key" in message
    assert "ck_users_role_department_pairing" not in message


def test_department_deletion_restricted_with_relationship_preloaded(db_session):
    """Same as above, but with `.users` explicitly loaded first — the exact
    scenario a service layer would hit (e.g. loading a department's users to
    check something before attempting a delete)."""
    department = make_department(db_session, name="Restrict Preloaded Department")
    make_user(db_session, department, email="restrict.preloaded@example.gov")
    db_session.flush()
    db_session.refresh(department)
    _ = department.users  # force the relationship to load before deleting

    db_session.delete(department)
    with pytest.raises(IntegrityError) as exc_info:
        db_session.flush()
    message = str(exc_info.value.orig).lower()
    assert "foreign key" in message
    assert "ck_users_role_department_pairing" not in message


# 17. ON DELETE RESTRICT — User ---------------------------------------------------

def test_user_deletion_restricted_by_recorded_letter(db_session):
    department = make_department(db_session, name="Restrict User Department")
    recorder = make_user(db_session, department, email="restrict.recorder@example.gov")
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

    db_session.delete(recorder)
    with pytest.raises(IntegrityError) as exc_info:
        db_session.flush()
    assert "foreign key" in str(exc_info.value.orig).lower()


# 18. ON DELETE CASCADE — Letter -> LetterDocument / Notification -----------------

def test_letter_deletion_cascades_documents_and_notifications(db_session):
    department = make_department(db_session, name="Cascade Test Department")
    recorder = make_user(db_session, department, email="cascade.clerk@example.gov")
    admin = make_user(
        db_session,
        department,
        role=UserRole.ADMIN,
        email="cascade.admin@example.gov",
        full_name="Cascade Admin",
    )
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

    doc = LetterDocument(
        letter_id=letter.id,
        original_filename="f.pdf",
        storage_path="x/f.pdf",
        uploaded_by=recorder.id,
    )
    notification = Notification(
        recipient_user_id=admin.id,
        letter_id=letter.id,
        notification_type="LETTER_REGISTERED",
        message="A letter was registered.",
    )
    db_session.add_all([doc, notification])
    db_session.flush()
    doc_id, notification_id = doc.id, notification.id

    db_session.delete(letter)
    db_session.flush()

    # `Notification` uses passive_deletes="all" (no ORM-level delete-orphan
    # cascade — see app/models/letter.py) specifically so the *database*'s
    # ON DELETE CASCADE does the deleting, not the ORM. That means the ORM
    # never learns the notification row is gone: `notification` stays in
    # this session's identity map as a stale object, and session.get() would
    # return that stale copy rather than re-querying. expire_all() forces a
    # fresh read, which is what actually proves the database performed the
    # cascade (LetterDocument, by contrast, *does* have ORM delete-orphan
    # cascade, so it's correctly expunged without this step — the asymmetry
    # here is intentional, see the relationship docstrings).
    db_session.expire_all()

    assert db_session.get(LetterDocument, doc_id) is None
    assert db_session.get(Notification, notification_id) is None


# 19. Notification.is_read database default --------------------------------------

def test_notification_is_read_defaults_false_at_database_level(db_session):
    """Insert a notification via Core (bypassing the ORM's Python-side
    default entirely) to prove the *database* — not just the ORM — supplies
    a safe default for is_read."""
    department = make_department(db_session, name="DB Default Test Department")
    recorder = make_user(db_session, department, email="dbdefault.clerk@example.gov")
    admin = make_user(
        db_session,
        department,
        role=UserRole.ADMIN,
        email="dbdefault.admin@example.gov",
        full_name="DB Default Admin",
    )
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

    # A hand-written INSERT naming every column except is_read — this is the
    # one construct in this test suite that genuinely bypasses SQLAlchemy's
    # column-level Python default too (not just the ORM), so a pass here can
    # only be explained by PostgreSQL's own DEFAULT false on the column. The
    # id is generated in Python (uuid4), matching this schema's UUID
    # strategy (see app/models/mixins.py) rather than relying on a
    # PostgreSQL extension such as pgcrypto for gen_random_uuid().
    new_id = uuid.uuid4()
    db_session.execute(
        text(
            "INSERT INTO notifications "
            "(id, recipient_user_id, letter_id, notification_type, message) "
            "VALUES (:id, :recipient_id, :letter_id, :ntype, :message)"
        ),
        {
            "id": str(new_id),
            "recipient_id": str(admin.id),
            "letter_id": str(letter.id),
            "ntype": "LETTER_REGISTERED",
            "message": "Inserted without specifying is_read.",
        },
    )

    is_read = db_session.execute(
        text("SELECT is_read FROM notifications WHERE id = :id"),
        {"id": str(new_id)},
    ).scalar_one()
    assert is_read is False


# 20. Direct model imports in a fresh interpreter ---------------------------------
# See tests/unit/test_imports.py for the fresh-interpreter regression tests
# covering the Phase 2 self-review's circular-import finding. Those tests
# don't need a database and are kept in tests/unit for that reason.
