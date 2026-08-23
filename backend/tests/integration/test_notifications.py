"""Notification generation/retrieval tests (Phase 4E implementation).

Real JWTs, real database-backed Letters/Users/Departments, real HTTP
requests through `/api/v1/letters` and `/api/v1/notifications`, against a
real PostgreSQL test database.
"""

import logging
import uuid
from datetime import datetime, timezone

from sqlalchemy import select

from app.core.security import create_access_token
from app.models.enums import UserRole, UserStatus
from app.models.letter import Letter
from app.models.notification import Notification
from app.repositories.notification_repository import NotificationRepository
from tests.factories import make_department, make_user

LETTERS_URL = "/api/v1/letters"
NOTIFICATIONS_URL = "/api/v1/notifications"


def _token_for(user) -> str:
    return create_access_token(subject=user.id, role=user.role.value, department_id=user.department_id)


def _auth_headers(user) -> dict:
    return {"Authorization": f"Bearer {_token_for(user)}"}


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


def _notifications_for(db_session, recipient_user_id):
    stmt = select(Notification).where(Notification.recipient_user_id == recipient_user_id)
    return list(db_session.execute(stmt).scalars().all())


# =========================================================================
# 19-20. Letter registration creates notification(s); recipient strategy
# =========================================================================


def test_letter_registration_creates_notification(client, db_session):
    department = make_department(db_session, name=f"Notif Dept {uuid.uuid4()}")
    admin = _make_admin(db_session, department)
    recorder = _make_regular_user(db_session, department)

    response = client.post(LETTERS_URL, json=_letter_payload(), headers=_auth_headers(recorder))
    assert response.status_code == 201
    letter_id = uuid.UUID(response.json()["id"])

    notifications = _notifications_for(db_session, admin.id)
    matching = [n for n in notifications if n.letter_id == letter_id]
    assert len(matching) == 1
    assert matching[0].notification_type == "LETTER_REGISTERED"
    assert matching[0].is_read is False


def test_recipient_strategy_is_department_admins(client, db_session):
    """PROVISIONAL default (docs/architecture/audit-notifications.md
    §13): the recipient department's ACTIVE Admins — not the whole
    department, not a different department's Admins."""
    department_a = make_department(db_session, name=f"Notif Dept A {uuid.uuid4()}")
    department_b = make_department(db_session, name=f"Notif Dept B {uuid.uuid4()}")
    admin_a = _make_admin(db_session, department_a, email=f"admin.a.{uuid.uuid4()}@example.gov")
    admin_b = _make_admin(db_session, department_b, email=f"admin.b.{uuid.uuid4()}@example.gov")
    recorder = _make_regular_user(db_session, department_a)

    response = client.post(LETTERS_URL, json=_letter_payload(), headers=_auth_headers(recorder))
    letter_id = uuid.UUID(response.json()["id"])

    assert any(n.letter_id == letter_id for n in _notifications_for(db_session, admin_a.id))
    assert not any(n.letter_id == letter_id for n in _notifications_for(db_session, admin_b.id))
    # A plain (non-Admin) recorder is not itself a recipient under this
    # provisional strategy.
    assert not any(n.letter_id == letter_id for n in _notifications_for(db_session, recorder.id))


def test_inactive_admin_is_not_a_recipient(client, db_session):
    department = make_department(db_session, name=f"Notif Dept {uuid.uuid4()}")
    inactive_admin = _make_admin(db_session, department, email=f"inactive.{uuid.uuid4()}@example.gov")
    inactive_admin.status = UserStatus.DEACTIVATED
    db_session.flush()
    recorder = _make_regular_user(db_session, department)

    response = client.post(LETTERS_URL, json=_letter_payload(), headers=_auth_headers(recorder))
    letter_id = uuid.UUID(response.json()["id"])

    assert not any(n.letter_id == letter_id for n in _notifications_for(db_session, inactive_admin.id))


# =========================================================================
# 21-23. Recipient isolation
# =========================================================================


def test_notification_belongs_to_exactly_one_recipient(client, db_session):
    department = make_department(db_session, name=f"Notif Dept {uuid.uuid4()}")
    admin = _make_admin(db_session, department)
    recorder = _make_regular_user(db_session, department)
    client.post(LETTERS_URL, json=_letter_payload(), headers=_auth_headers(recorder))

    response = client.get(NOTIFICATIONS_URL, headers=_auth_headers(admin))
    assert response.status_code == 200
    body = response.json()
    assert body["total"] >= 1
    for item in body["items"]:
        # No recipient_user_id field is even exposed — ownership is
        # implicit in "this is your own list".
        assert "recipient_user_id" not in item


def test_user_cannot_retrieve_another_users_notification(client, db_session):
    department = make_department(db_session, name=f"Notif Dept {uuid.uuid4()}")
    admin_a = _make_admin(db_session, department, email=f"admin.a.{uuid.uuid4()}@example.gov")
    admin_b = _make_admin(db_session, department, email=f"admin.b.{uuid.uuid4()}@example.gov")
    recorder = _make_regular_user(db_session, department)
    client.post(LETTERS_URL, json=_letter_payload(), headers=_auth_headers(recorder))

    admin_a_notifications = client.get(NOTIFICATIONS_URL, headers=_auth_headers(admin_a)).json()["items"]
    admin_b_notifications = client.get(NOTIFICATIONS_URL, headers=_auth_headers(admin_b)).json()["items"]
    a_ids = {item["id"] for item in admin_a_notifications}
    b_ids = {item["id"] for item in admin_b_notifications}
    assert a_ids.isdisjoint(b_ids) or (not a_ids and not b_ids)
    assert len(a_ids) >= 1
    assert len(b_ids) >= 1
    # Each admin only ever sees their own rows even though both are
    # recipients of the *same* letter's notification.
    assert a_ids != b_ids


def test_user_cannot_mark_another_users_notification_read(client, db_session):
    department = make_department(db_session, name=f"Notif Dept {uuid.uuid4()}")
    admin_a = _make_admin(db_session, department, email=f"admin.a.{uuid.uuid4()}@example.gov")
    admin_b = _make_admin(db_session, department, email=f"admin.b.{uuid.uuid4()}@example.gov")
    recorder = _make_regular_user(db_session, department)
    client.post(LETTERS_URL, json=_letter_payload(), headers=_auth_headers(recorder))

    admin_a_notification_id = client.get(NOTIFICATIONS_URL, headers=_auth_headers(admin_a)).json()["items"][0][
        "id"
    ]

    response = client.patch(
        f"{NOTIFICATIONS_URL}/{admin_a_notification_id}/read", headers=_auth_headers(admin_b)
    )
    assert response.status_code == 404

    # Confirm it genuinely wasn't marked read by the attempt.
    notification = db_session.get(Notification, uuid.UUID(admin_a_notification_id))
    assert notification.is_read is False


# =========================================================================
# 24-26. Read state
# =========================================================================


def test_unread_count_is_user_scoped(client, db_session):
    department = make_department(db_session, name=f"Notif Dept {uuid.uuid4()}")
    admin_a = _make_admin(db_session, department, email=f"admin.a.{uuid.uuid4()}@example.gov")
    admin_b = _make_admin(db_session, department, email=f"admin.b.{uuid.uuid4()}@example.gov")
    recorder = _make_regular_user(db_session, department)
    client.post(LETTERS_URL, json=_letter_payload(), headers=_auth_headers(recorder))

    count_a = client.get(f"{NOTIFICATIONS_URL}/unread-count", headers=_auth_headers(admin_a)).json()
    count_b = client.get(f"{NOTIFICATIONS_URL}/unread-count", headers=_auth_headers(admin_b)).json()
    assert count_a["unread_count"] >= 1
    assert count_b["unread_count"] >= 1

    # Marking Admin A's own notification(s) read must not move Admin B's count.
    for item in client.get(NOTIFICATIONS_URL, headers=_auth_headers(admin_a)).json()["items"]:
        client.patch(f"{NOTIFICATIONS_URL}/{item['id']}/read", headers=_auth_headers(admin_a))
    new_count_a = client.get(f"{NOTIFICATIONS_URL}/unread-count", headers=_auth_headers(admin_a)).json()
    new_count_b = client.get(f"{NOTIFICATIONS_URL}/unread-count", headers=_auth_headers(admin_b)).json()
    assert new_count_a["unread_count"] == 0
    assert new_count_b["unread_count"] == count_b["unread_count"]


def test_mark_read_updates_is_read_and_read_at(client, db_session):
    department = make_department(db_session, name=f"Notif Dept {uuid.uuid4()}")
    admin = _make_admin(db_session, department)
    recorder = _make_regular_user(db_session, department)
    client.post(LETTERS_URL, json=_letter_payload(), headers=_auth_headers(recorder))

    item = client.get(NOTIFICATIONS_URL, headers=_auth_headers(admin)).json()["items"][0]
    assert item["is_read"] is False
    assert item["read_at"] is None

    response = client.patch(f"{NOTIFICATIONS_URL}/{item['id']}/read", headers=_auth_headers(admin))
    assert response.status_code == 200
    body = response.json()
    assert body["is_read"] is True
    assert body["read_at"] is not None


def test_read_all_only_affects_current_users_notifications(client, db_session):
    department = make_department(db_session, name=f"Notif Dept {uuid.uuid4()}")
    admin_a = _make_admin(db_session, department, email=f"admin.a.{uuid.uuid4()}@example.gov")
    admin_b = _make_admin(db_session, department, email=f"admin.b.{uuid.uuid4()}@example.gov")
    recorder = _make_regular_user(db_session, department)
    client.post(LETTERS_URL, json=_letter_payload(), headers=_auth_headers(recorder))

    response = client.patch(f"{NOTIFICATIONS_URL}/read-all", headers=_auth_headers(admin_a))
    assert response.status_code == 200
    assert response.json()["marked_read"] >= 1

    assert client.get(f"{NOTIFICATIONS_URL}/unread-count", headers=_auth_headers(admin_a)).json()[
        "unread_count"
    ] == 0
    assert client.get(f"{NOTIFICATIONS_URL}/unread-count", headers=_auth_headers(admin_b)).json()[
        "unread_count"
    ] >= 1


# =========================================================================
# 27-28. Transactional consistency / failure logging
# =========================================================================


def test_notification_savepoint_failure_is_logged_and_does_not_block_letter(
    client, db_session, monkeypatch, caplog
):
    """Covers both 27 (notification failure does not roll back Letter
    creation) and 28 (the failure is logged) together — a failure
    *inside* the savepoint (here, the notification insert itself
    failing) is caught internally by `NotificationService` and logged,
    never re-raised and never swallowed silently. Exercises the real
    try/except-around-`begin_nested()` path (§20/§21), not a replacement
    of the whole generation method — the earlier version of this test
    that monkeypatched the method itself was removed as redundant/
    unrealistic: it bypassed the very safety net (`notify_letter_registered`
    never raises) this test now actually exercises."""
    department = make_department(db_session, name=f"Notif Dept {uuid.uuid4()}")
    admin = _make_admin(db_session, department)
    recorder = _make_regular_user(db_session, department)

    def _create_boom(self, **kwargs):
        raise RuntimeError("simulated savepoint failure")

    monkeypatch.setattr(NotificationRepository, "create", _create_boom)

    with caplog.at_level(logging.WARNING, logger="app.services.notification_service"):
        reference_number = f"REF-{uuid.uuid4()}"
        response = client.post(
            LETTERS_URL,
            json=_letter_payload(reference_number=reference_number),
            headers=_auth_headers(recorder),
        )

    assert response.status_code == 201
    assert any(
        "Failed to create LETTER_REGISTERED notification" in record.message for record in caplog.records
    )

    letter = db_session.execute(
        select(Letter).where(Letter.reference_number == reference_number)
    ).scalar_one_or_none()
    assert letter is not None
    # No notification row was created for this letter since the write
    # itself failed.
    assert not any(n.letter_id == letter.id for n in _notifications_for(db_session, admin.id))


# =========================================================================
# 29. Generic message content
# =========================================================================


def test_notification_message_contains_no_letter_content(client, db_session):
    department = make_department(db_session, name=f"Notif Dept {uuid.uuid4()}")
    admin = _make_admin(db_session, department)
    recorder = _make_regular_user(db_session, department)
    secret_subject = "TOP SECRET OPERATION NIGHTHAWK"

    response = client.post(
        LETTERS_URL, json=_letter_payload(subject=secret_subject), headers=_auth_headers(recorder)
    )
    letter_id = uuid.UUID(response.json()["id"])

    notifications = [n for n in _notifications_for(db_session, admin.id) if n.letter_id == letter_id]
    assert len(notifications) == 1
    assert secret_subject not in notifications[0].message
    assert "registered in your department" in notifications[0].message


# =========================================================================
# 30. Deactivated recipient's historical notification remains
# =========================================================================


def test_deactivated_recipients_notification_remains(client, db_session):
    department = make_department(db_session, name=f"Notif Dept {uuid.uuid4()}")
    admin = _make_admin(db_session, department)
    recorder = _make_regular_user(db_session, department)

    response = client.post(LETTERS_URL, json=_letter_payload(), headers=_auth_headers(recorder))
    letter_id = uuid.UUID(response.json()["id"])

    admin.status = UserStatus.DEACTIVATED
    db_session.flush()

    remaining = [n for n in _notifications_for(db_session, admin.id) if n.letter_id == letter_id]
    assert len(remaining) == 1

    # The deactivated recipient can no longer authenticate to read it —
    # confirms it's "unreachable", not "deleted".
    denied = client.get(NOTIFICATIONS_URL, headers=_auth_headers(admin))
    assert denied.status_code == 401
