"""End-to-end tests for correspondence direction, Diary Number, the
"Record" action, and continuation/response relationships (Phase 6A,
docs/architecture/correspondence.md).

Real JWTs, real database-backed Users/Departments, real HTTP requests
through `/api/v1/letters*`, against a real PostgreSQL test database — same
pattern as `test_letter_registry.py`.
"""

import uuid
from datetime import datetime, timezone

from app.core.security import create_access_token
from app.models.enums import LetterDirection, UserRole
from app.models.notification import Notification
from tests.factories import make_department, make_letter, make_user

LETTERS_URL = "/api/v1/letters"


def _letter_url(letter_id) -> str:
    return f"{LETTERS_URL}/{letter_id}"


def _record_url(letter_id) -> str:
    return f"{LETTERS_URL}/{letter_id}/record"


def _token_for(user) -> str:
    return create_access_token(subject=user.id, role=user.role.value, department_id=user.department_id)


def _auth_headers(user) -> dict:
    return {"Authorization": f"Bearer {_token_for(user)}"}


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


def _admin_notifications(db_session, admin, notification_type=None):
    query = db_session.query(Notification).filter(Notification.recipient_user_id == admin.id)
    if notification_type is not None:
        query = query.filter(Notification.notification_type == notification_type)
    return query.all()


# =========================================================================
# Backward compatibility — every existing letter/client keeps working
# =========================================================================


def test_create_letter_without_direction_defaults_to_incoming(client, db_session):
    department = make_department(db_session, name="Finance A")
    user = make_user(db_session, department, role=UserRole.USER, email="u1@example.gov")

    response = client.post(LETTERS_URL, json=_valid_payload(), headers=_auth_headers(user))

    assert response.status_code == 201
    body = response.json()
    assert body["direction"] == "INCOMING"
    assert body["dispatch_department_id"] is None
    assert body["recorded_from_letter_id"] is None
    assert body["continuation_of_letter_id"] is None
    assert body["diary_number"] is not None


def test_historical_letter_created_directly_in_db_reads_back_as_incoming(client, db_session):
    department = make_department(db_session, name="Finance B")
    user = make_user(db_session, department, role=UserRole.USER, email="u2@example.gov")
    letter = make_letter(db_session, department, user)  # no direction override

    response = client.get(_letter_url(letter.id), headers=_auth_headers(user))

    assert response.status_code == 200
    assert response.json()["direction"] == "INCOMING"
    assert response.json()["diary_number"] is None


# =========================================================================
# Outgoing letter creation
# =========================================================================


def test_create_outgoing_letter_succeeds_and_notifies_dispatch_department(client, db_session):
    finance = make_department(db_session, name="Finance C")
    s_and_it = make_department(db_session, name="S&IT C")
    finance_user = make_user(db_session, finance, role=UserRole.USER, email="finance.c@example.gov")
    s_and_it_admin = make_user(
        db_session, s_and_it, role=UserRole.ADMIN, email="sit.admin.c@example.gov"
    )

    response = client.post(
        LETTERS_URL,
        json=_valid_payload(direction="OUTGOING", dispatch_department_id=str(s_and_it.id)),
        headers=_auth_headers(finance_user),
    )

    assert response.status_code == 201
    body = response.json()
    assert body["direction"] == "OUTGOING"
    assert body["dispatch_department_id"] == str(s_and_it.id)
    assert body["recipient_department_id"] == str(finance.id)  # owned by the dispatcher

    dispatched = _admin_notifications(db_session, s_and_it_admin, "LETTER_DISPATCHED")
    assert len(dispatched) == 1
    assert body["reference_number"] in dispatched[0].message
    assert "Finance C" in dispatched[0].message


def test_outgoing_letter_requires_dispatch_department(client, db_session):
    department = make_department(db_session, name="Finance D")
    user = make_user(db_session, department, role=UserRole.USER, email="u3@example.gov")

    response = client.post(
        LETTERS_URL, json=_valid_payload(direction="OUTGOING"), headers=_auth_headers(user)
    )

    assert response.status_code == 422


def test_incoming_letter_rejects_dispatch_department(client, db_session):
    department = make_department(db_session, name="Finance E")
    other = make_department(db_session, name="Other E")
    user = make_user(db_session, department, role=UserRole.USER, email="u4@example.gov")

    response = client.post(
        LETTERS_URL,
        json=_valid_payload(direction="INCOMING", dispatch_department_id=str(other.id)),
        headers=_auth_headers(user),
    )

    assert response.status_code == 422


def test_outgoing_letter_rejects_nonexistent_dispatch_department(client, db_session):
    department = make_department(db_session, name="Finance F")
    user = make_user(db_session, department, role=UserRole.USER, email="u5@example.gov")

    response = client.post(
        LETTERS_URL,
        json=_valid_payload(direction="OUTGOING", dispatch_department_id=str(uuid.uuid4())),
        headers=_auth_headers(user),
    )

    assert response.status_code == 404


def test_outgoing_letter_rejects_inactive_dispatch_department(client, db_session):
    from app.models.enums import ActiveStatus

    department = make_department(db_session, name="Finance G")
    inactive = make_department(db_session, name="Inactive G", status=ActiveStatus.INACTIVE)
    user = make_user(db_session, department, role=UserRole.USER, email="u6@example.gov")

    response = client.post(
        LETTERS_URL,
        json=_valid_payload(direction="OUTGOING", dispatch_department_id=str(inactive.id)),
        headers=_auth_headers(user),
    )

    assert response.status_code == 409


def test_self_dispatch_is_rejected(client, db_session):
    department = make_department(db_session, name="Finance H")
    user = make_user(db_session, department, role=UserRole.USER, email="u7@example.gov")

    response = client.post(
        LETTERS_URL,
        json=_valid_payload(direction="OUTGOING", dispatch_department_id=str(department.id)),
        headers=_auth_headers(user),
    )

    assert response.status_code == 422


# =========================================================================
# Record incoming correspondence — the full dispatch -> record lifecycle
# =========================================================================


def test_record_creates_incoming_letter_without_manual_reentry(client, db_session):
    finance = make_department(db_session, name="Finance I")
    s_and_it = make_department(db_session, name="S&IT I")
    finance_user = make_user(db_session, finance, role=UserRole.USER, email="finance.i@example.gov")
    s_and_it_user = make_user(db_session, s_and_it, role=UserRole.USER, email="sit.i@example.gov")
    finance_admin = make_user(db_session, finance, role=UserRole.ADMIN, email="finance.admin.i@example.gov")

    outgoing = client.post(
        LETTERS_URL,
        json=_valid_payload(
            direction="OUTGOING",
            dispatch_department_id=str(s_and_it.id),
            subject="Budget Approval Request",
            sender_name="Jane Finance",
        ),
        headers=_auth_headers(finance_user),
    ).json()

    record_response = client.post(_record_url(outgoing["id"]), headers=_auth_headers(s_and_it_user))

    assert record_response.status_code == 201
    incoming = record_response.json()
    assert incoming["direction"] == "INCOMING"
    assert incoming["recipient_department_id"] == str(s_and_it.id)
    assert incoming["recorded_from_letter_id"] == outgoing["id"]
    # Copied verbatim — the recipient never re-enters these.
    assert incoming["subject"] == "Budget Approval Request"
    assert incoming["sender_name"] == "Jane Finance"
    assert incoming["reference_number"] == outgoing["reference_number"]
    # Its own department's INCOMING sequence — independent of Finance's
    # OUTGOING sequence, not merely "different" (see the dedicated
    # sequence-independence tests below for why they may coincide).
    assert incoming["diary_number"] == "1"

    # Receipt confirmation reaches the original dispatching department.
    recorded_notifications = _admin_notifications(db_session, finance_admin, "LETTER_RECORDED")
    assert len(recorded_notifications) == 1
    assert "S&IT I" in recorded_notifications[0].message


def test_record_is_idempotent_and_never_creates_a_duplicate(client, db_session):
    finance = make_department(db_session, name="Finance J")
    s_and_it = make_department(db_session, name="S&IT J")
    finance_user = make_user(db_session, finance, role=UserRole.USER, email="finance.j@example.gov")
    s_and_it_user = make_user(db_session, s_and_it, role=UserRole.USER, email="sit.j@example.gov")

    outgoing = client.post(
        LETTERS_URL,
        json=_valid_payload(direction="OUTGOING", dispatch_department_id=str(s_and_it.id)),
        headers=_auth_headers(finance_user),
    ).json()

    first = client.post(_record_url(outgoing["id"]), headers=_auth_headers(s_and_it_user))
    second = client.post(_record_url(outgoing["id"]), headers=_auth_headers(s_and_it_user))

    assert first.status_code == 201
    assert second.status_code == 200
    assert first.json()["id"] == second.json()["id"]

    listed = client.get(
        LETTERS_URL, params={"direction": "INCOMING"}, headers=_auth_headers(s_and_it_user)
    ).json()
    matching = [item for item in listed["items"] if item["recipient_department_id"] == str(s_and_it.id)]
    assert len(matching) == 1


def test_record_rejected_for_department_not_the_dispatch_target(client, db_session):
    finance = make_department(db_session, name="Finance K")
    s_and_it = make_department(db_session, name="S&IT K")
    unrelated = make_department(db_session, name="Unrelated K")
    finance_user = make_user(db_session, finance, role=UserRole.USER, email="finance.k@example.gov")
    unrelated_user = make_user(db_session, unrelated, role=UserRole.USER, email="unrelated.k@example.gov")

    outgoing = client.post(
        LETTERS_URL,
        json=_valid_payload(direction="OUTGOING", dispatch_department_id=str(s_and_it.id)),
        headers=_auth_headers(finance_user),
    ).json()

    response = client.post(_record_url(outgoing["id"]), headers=_auth_headers(unrelated_user))

    assert response.status_code == 404


def test_record_rejected_for_an_incoming_letter(client, db_session):
    department = make_department(db_session, name="Finance L")
    user = make_user(db_session, department, role=UserRole.USER, email="u8@example.gov")
    incoming = make_letter(db_session, department, user)

    response = client.post(_record_url(incoming.id), headers=_auth_headers(user))

    assert response.status_code == 404


def test_receipt_confirmation_notification_links_to_a_letter_the_recipient_can_open(client, db_session):
    """A notification must never point its own recipient at a letter
    they can't access — `notify_correspondence_recorded` links back to
    the *outgoing* letter (which the dispatching department already
    owns), never the destination department's own incoming copy."""
    finance = make_department(db_session, name="Finance V")
    s_and_it = make_department(db_session, name="S&IT V")
    finance_user = make_user(db_session, finance, role=UserRole.USER, email="finance.v@example.gov")
    finance_admin = make_user(db_session, finance, role=UserRole.ADMIN, email="finance.admin.v@example.gov")
    s_and_it_user = make_user(db_session, s_and_it, role=UserRole.USER, email="sit.v@example.gov")

    outgoing = client.post(
        LETTERS_URL,
        json=_valid_payload(direction="OUTGOING", dispatch_department_id=str(s_and_it.id)),
        headers=_auth_headers(finance_user),
    ).json()
    client.post(_record_url(outgoing["id"]), headers=_auth_headers(s_and_it_user))

    recorded_notifications = _admin_notifications(db_session, finance_admin, "LETTER_RECORDED")
    assert len(recorded_notifications) == 1
    assert str(recorded_notifications[0].letter_id) == outgoing["id"]

    # And Finance can actually open it.
    response = client.get(_letter_url(recorded_notifications[0].letter_id), headers=_auth_headers(finance_user))
    assert response.status_code == 200


def test_record_returns_404_for_nonexistent_letter(client, db_session):
    department = make_department(db_session, name="Finance M")
    user = make_user(db_session, department, role=UserRole.USER, email="u9@example.gov")

    response = client.post(_record_url(uuid.uuid4()), headers=_auth_headers(user))

    assert response.status_code == 404


def test_original_outgoing_letter_is_unchanged_after_being_recorded(client, db_session):
    finance = make_department(db_session, name="Finance N")
    s_and_it = make_department(db_session, name="S&IT N")
    finance_user = make_user(db_session, finance, role=UserRole.USER, email="finance.n@example.gov")
    s_and_it_user = make_user(db_session, s_and_it, role=UserRole.USER, email="sit.n@example.gov")

    outgoing = client.post(
        LETTERS_URL,
        json=_valid_payload(direction="OUTGOING", dispatch_department_id=str(s_and_it.id)),
        headers=_auth_headers(finance_user),
    ).json()

    client.post(_record_url(outgoing["id"]), headers=_auth_headers(s_and_it_user))

    reloaded = client.get(_letter_url(outgoing["id"]), headers=_auth_headers(finance_user)).json()
    assert reloaded == outgoing


# =========================================================================
# Department isolation — unchanged, re-verified for the new fields
# =========================================================================


def test_outgoing_letter_invisible_to_unrelated_department(client, db_session):
    finance = make_department(db_session, name="Finance O")
    s_and_it = make_department(db_session, name="S&IT O")
    unrelated = make_department(db_session, name="Unrelated O")
    finance_user = make_user(db_session, finance, role=UserRole.USER, email="finance.o@example.gov")
    unrelated_user = make_user(db_session, unrelated, role=UserRole.USER, email="unrelated.o@example.gov")

    outgoing = client.post(
        LETTERS_URL,
        json=_valid_payload(direction="OUTGOING", dispatch_department_id=str(s_and_it.id)),
        headers=_auth_headers(finance_user),
    ).json()

    response = client.get(_letter_url(outgoing["id"]), headers=_auth_headers(unrelated_user))
    assert response.status_code == 404


def test_dispatch_department_cannot_see_outgoing_letter_before_recording(client, db_session):
    """A LETTER_DISPATCHED notification exists, but the letter itself is
    still owned by the dispatching department until Record is called —
    department isolation is not weakened by the mere existence of a
    dispatch relationship."""
    finance = make_department(db_session, name="Finance P")
    s_and_it = make_department(db_session, name="S&IT P")
    finance_user = make_user(db_session, finance, role=UserRole.USER, email="finance.p@example.gov")
    s_and_it_user = make_user(db_session, s_and_it, role=UserRole.USER, email="sit.p@example.gov")

    outgoing = client.post(
        LETTERS_URL,
        json=_valid_payload(direction="OUTGOING", dispatch_department_id=str(s_and_it.id)),
        headers=_auth_headers(finance_user),
    ).json()

    response = client.get(_letter_url(outgoing["id"]), headers=_auth_headers(s_and_it_user))
    assert response.status_code == 404


# =========================================================================
# Continuation / response relationship
# =========================================================================


def test_continuation_creates_a_new_letter_linked_to_the_original(client, db_session):
    finance = make_department(db_session, name="Finance Q")
    s_and_it = make_department(db_session, name="S&IT Q")
    finance_user = make_user(db_session, finance, role=UserRole.USER, email="finance.q@example.gov")
    s_and_it_user = make_user(db_session, s_and_it, role=UserRole.USER, email="sit.q@example.gov")

    outgoing = client.post(
        LETTERS_URL,
        json=_valid_payload(direction="OUTGOING", dispatch_department_id=str(s_and_it.id)),
        headers=_auth_headers(finance_user),
    ).json()
    incoming = client.post(_record_url(outgoing["id"]), headers=_auth_headers(s_and_it_user)).json()

    response = client.post(
        LETTERS_URL,
        json=_valid_payload(
            direction="OUTGOING",
            dispatch_department_id=str(finance.id),
            continuation_of_letter_id=incoming["id"],
            subject="Re: Budget Approval Request",
        ),
        headers=_auth_headers(s_and_it_user),
    )

    assert response.status_code == 201
    continuation = response.json()
    assert continuation["id"] != incoming["id"]
    assert continuation["continuation_of_letter_id"] == incoming["id"]

    # The incoming letter it responds to is completely unchanged.
    reloaded_incoming = client.get(
        _letter_url(incoming["id"]), headers=_auth_headers(s_and_it_user)
    ).json()
    assert reloaded_incoming == incoming


def test_continuation_must_reference_a_letter_the_caller_can_access(client, db_session):
    finance = make_department(db_session, name="Finance R")
    other = make_department(db_session, name="Other R")
    finance_user = make_user(db_session, finance, role=UserRole.USER, email="finance.r@example.gov")
    other_user = make_user(db_session, other, role=UserRole.USER, email="other.r@example.gov")
    others_letter = make_letter(db_session, other, other_user)

    response = client.post(
        LETTERS_URL,
        json=_valid_payload(continuation_of_letter_id=str(others_letter.id)),
        headers=_auth_headers(finance_user),
    )

    assert response.status_code == 404


# =========================================================================
# Diary Number behavior
# =========================================================================


def test_diary_numbers_increment_independently_per_department_and_direction(client, db_session):
    dept_a = make_department(db_session, name="Dept Diary A")
    dept_b = make_department(db_session, name="Dept Diary B")
    user_a = make_user(db_session, dept_a, role=UserRole.USER, email="diary.a@example.gov")
    user_b = make_user(db_session, dept_b, role=UserRole.USER, email="diary.b@example.gov")

    a1 = client.post(LETTERS_URL, json=_valid_payload(), headers=_auth_headers(user_a)).json()
    a2 = client.post(LETTERS_URL, json=_valid_payload(), headers=_auth_headers(user_a)).json()
    b1 = client.post(LETTERS_URL, json=_valid_payload(), headers=_auth_headers(user_b)).json()

    assert int(a2["diary_number"]) == int(a1["diary_number"]) + 1
    # A different department's sequence starts independently — no
    # cross-department collision, and no forced global uniqueness.
    assert b1["diary_number"] == a1["diary_number"]


def test_outgoing_and_incoming_sequences_are_independent_within_one_department(client, db_session):
    finance = make_department(db_session, name="Finance S")
    s_and_it = make_department(db_session, name="S&IT S")
    finance_user = make_user(db_session, finance, role=UserRole.USER, email="finance.s@example.gov")

    incoming = client.post(LETTERS_URL, json=_valid_payload(), headers=_auth_headers(finance_user)).json()
    outgoing = client.post(
        LETTERS_URL,
        json=_valid_payload(direction="OUTGOING", dispatch_department_id=str(s_and_it.id)),
        headers=_auth_headers(finance_user),
    ).json()

    # Same department, but INCOMING and OUTGOING each start their own
    # sequence at 1 — never sharing a counter.
    assert incoming["diary_number"] == outgoing["diary_number"] == "1"


# =========================================================================
# Classification / role scope still apply to correspondence letters
# =========================================================================


def test_system_admin_cannot_create_a_letter_of_either_direction(client, db_session):
    admin_user = make_user(db_session, None, role=UserRole.SYSTEM_ADMIN, email="sysadmin.t@example.gov")

    response = client.post(LETTERS_URL, json=_valid_payload(), headers=_auth_headers(admin_user))

    assert response.status_code == 403


def test_system_admin_cannot_record_correspondence(client, db_session):
    finance = make_department(db_session, name="Finance U")
    s_and_it = make_department(db_session, name="S&IT U")
    finance_user = make_user(db_session, finance, role=UserRole.USER, email="finance.u@example.gov")
    admin_user = make_user(db_session, None, role=UserRole.SYSTEM_ADMIN, email="sysadmin.u@example.gov")

    outgoing = client.post(
        LETTERS_URL,
        json=_valid_payload(direction="OUTGOING", dispatch_department_id=str(s_and_it.id)),
        headers=_auth_headers(finance_user),
    ).json()

    response = client.post(_record_url(outgoing["id"]), headers=_auth_headers(admin_user))

    assert response.status_code == 403
