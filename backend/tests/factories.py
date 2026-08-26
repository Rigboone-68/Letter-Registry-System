"""Shared test data factories for the Phase 3A+ integration tests.

Plain functions, not fixtures — call with the test's `db_session`.

`make_letter` (Phase 4B) generates a fresh, unique `reference_number` per
call by default (`uuid.uuid4()`-derived) — every letter's reference
number is globally unique (`uq_letters_reference_number`), so a factory
that reused a fixed default would make every test needing more than one
letter collide unless it remembered to override it every time.
"""

import uuid
from datetime import datetime, timezone

from app.models.category import Category
from app.models.classification import Classification
from app.models.department import Department
from app.models.designation import Designation
from app.models.enums import (
    ActiveStatus,
    AuthorizationPurpose,
    AuthorizationStatus,
    UserRole,
    UserStatus,
)
from app.models.letter import Letter
from app.models.user import User
from app.models.user_authorization import UserAuthorization


def make_department(db_session, name="Ministry of Testing", code=None, status=ActiveStatus.ACTIVE):
    department = Department(name=name, code=code, status=status)
    db_session.add(department)
    db_session.flush()
    return department


def make_user(
    db_session,
    department,
    role=UserRole.USER,
    email="user@example.gov",
    full_name="Test User",
    status=UserStatus.ACTIVE,
    password_hash="not-a-real-hash",
):
    user = User(
        full_name=full_name,
        email=email,
        password_hash=password_hash,
        role=role,
        department_id=department.id if department else None,
        status=status,
    )
    db_session.add(user)
    db_session.flush()
    return user


def make_authorization(
    db_session,
    department,
    authorized_by,
    email="new.hire@example.gov",
    status=AuthorizationStatus.ACTIVE,
    purpose=AuthorizationPurpose.USER,
    expires_at=None,
):
    authorization = UserAuthorization(
        email=email,
        department_id=department.id,
        authorized_by=authorized_by.id,
        status=status,
        purpose=purpose,
        expires_at=expires_at,
    )
    db_session.add(authorization)
    db_session.flush()
    return authorization


def make_category(db_session, name="Test Category", status=ActiveStatus.ACTIVE):
    category = Category(name=name, status=status)
    db_session.add(category)
    db_session.flush()
    return category


def make_designation(db_session, name="Test Designation", status=ActiveStatus.ACTIVE):
    designation = Designation(name=name, status=status)
    db_session.add(designation)
    db_session.flush()
    return designation


def make_classification(
    db_session, name="Test Classification", restricts_access=False, status=ActiveStatus.ACTIVE
):
    classification = Classification(
        name=name, restricts_access=restricts_access, status=status
    )
    db_session.add(classification)
    db_session.flush()
    return classification


def make_letter(
    db_session,
    recipient_department,
    recorder,
    reference_number=None,
    source_name="Test Source Organization",
    source_department=None,
    source_location=None,
    sender_name="Test Sender",
    sender_designation="Test Designation",
    designation=None,
    sender_department="Test Sender Department",
    sender_address=None,
    subject=None,
    category=None,
    classification=None,
    received_at=None,
    text_content=None,
):
    letter = Letter(
        reference_number=reference_number or f"REF-{uuid.uuid4()}",
        recipient_department_id=recipient_department.id,
        source_name=source_name,
        source_department_id=source_department.id if source_department else None,
        source_location=source_location,
        sender_name=sender_name,
        sender_designation=sender_designation,
        designation_id=designation.id if designation else None,
        sender_department=sender_department,
        sender_address=sender_address,
        subject=subject,
        category_id=category.id if category else None,
        classification_id=classification.id if classification else None,
        received_at=received_at or datetime.now(timezone.utc),
        recorded_by=recorder.id,
        text_content=text_content,
    )
    db_session.add(letter)
    db_session.flush()
    return letter
