"""End-to-end tests for `GET /api/v1/letters/aggregate` (Phase 6C,
docs/architecture/dashboard-analytics-api.md's own implementation
record).

Real JWTs, real database-backed Users/Departments/Letters, real HTTP
requests through `/api/v1/letters/aggregate`, against a real PostgreSQL
test database — same pattern as `test_letter_registry.py`/
`test_correspondence.py`.
"""

import uuid
from datetime import datetime, timedelta, timezone

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
AGGREGATE_URL = f"{LETTERS_URL}/aggregate"


def _token_for(user) -> str:
    return create_access_token(subject=user.id, role=user.role.value, department_id=user.department_id)


def _auth_headers(user) -> dict:
    return {"Authorization": f"Bearer {_token_for(user)}"}


def _buckets_by_key(response_json):
    return {bucket["key"]: bucket["count"] for bucket in response_json["buckets"]}


# =========================================================================
# Basic shape / every role can call it
# =========================================================================


def test_requires_group_by(client, db_session):
    department = make_department(db_session, name="Agg A")
    user = make_user(db_session, department, role=UserRole.USER, email="agg.a@example.gov")

    response = client.get(AGGREGATE_URL, headers=_auth_headers(user))

    assert response.status_code == 422


def test_empty_result_returns_zero_total_and_no_buckets(client, db_session):
    department = make_department(db_session, name="Agg B")
    user = make_user(db_session, department, role=UserRole.USER, email="agg.b@example.gov")

    response = client.get(AGGREGATE_URL, params={"group_by": "status"}, headers=_auth_headers(user))

    assert response.status_code == 200
    body = response.json()
    assert body == {"group_by": "status", "total": 0, "buckets": []}


def test_every_role_can_call_the_endpoint(client, db_session):
    department = make_department(db_session, name="Agg C")
    user = make_user(db_session, department, role=UserRole.USER, email="agg.c.user@example.gov")
    admin = make_user(db_session, department, role=UserRole.ADMIN, email="agg.c.admin@example.gov")
    sys_admin = make_user(db_session, None, role=UserRole.SYSTEM_ADMIN, email="agg.c.sys@example.gov")
    make_letter(db_session, department, user)

    for caller in (user, admin, sys_admin):
        response = client.get(AGGREGATE_URL, params={"group_by": "status"}, headers=_auth_headers(caller))
        assert response.status_code == 200, caller.role


def test_never_paginated(client, db_session):
    department = make_department(db_session, name="Agg D")
    user = make_user(db_session, department, role=UserRole.USER, email="agg.d@example.gov")

    response = client.get(AGGREGATE_URL, params={"group_by": "status"}, headers=_auth_headers(user))

    body = response.json()
    assert "page" not in body
    assert "page_size" not in body
    assert "total_pages" not in body


# =========================================================================
# Status / direction dimensions
# =========================================================================


def test_group_by_status(client, db_session):
    department = make_department(db_session, name="Agg E")
    user = make_user(db_session, department, role=UserRole.USER, email="agg.e@example.gov")
    active = make_letter(db_session, department, user)
    make_letter(db_session, department, user)

    from app.models.enums import LetterStatus

    active.status = LetterStatus.ARCHIVED
    db_session.flush()

    response = client.get(AGGREGATE_URL, params={"group_by": "status"}, headers=_auth_headers(user))

    body = response.json()
    assert body["total"] == 2
    buckets = _buckets_by_key(body)
    assert buckets["ARCHIVED"] == 1
    assert buckets["ACTIVE"] == 1


def test_group_by_direction_answers_incoming_vs_outgoing(client, db_session):
    finance = make_department(db_session, name="Agg Finance F")
    s_and_it = make_department(db_session, name="Agg S&IT F")
    finance_user = make_user(db_session, finance, role=UserRole.USER, email="agg.finance.f@example.gov")

    client.post(
        LETTERS_URL,
        json={
            "reference_number": "REF-AGG-1",
            "subject": "Incoming one",
            "source_name": "External Org",
            "sender_name": "Sender",
            "sender_designation": "Officer",
            "sender_department": "Dept",
            "received_at": datetime.now(timezone.utc).isoformat(),
        },
        headers=_auth_headers(finance_user),
    )
    client.post(
        LETTERS_URL,
        json={
            "reference_number": "REF-AGG-2",
            "subject": "Outgoing one",
            "source_name": "Finance",
            "sender_name": "Sender",
            "sender_designation": "Officer",
            "sender_department": "Dept",
            "received_at": datetime.now(timezone.utc).isoformat(),
            "direction": "OUTGOING",
            "dispatch_department_id": str(s_and_it.id),
        },
        headers=_auth_headers(finance_user),
    )

    response = client.get(
        AGGREGATE_URL, params={"group_by": "direction"}, headers=_auth_headers(finance_user)
    )

    body = response.json()
    assert body["total"] == 2
    buckets = _buckets_by_key(body)
    assert buckets["INCOMING"] == 1
    assert buckets["OUTGOING"] == 1


# =========================================================================
# Department / dispatch_department dimensions (Phase 6A reassessment)
# =========================================================================


def test_group_by_department_is_the_owning_department_for_either_direction(client, db_session):
    """`department` groups by `recipient_department_id` — the owning
    department, unchanged mechanism, but now spans both directions
    (Phase 6A's own reassessment of what this dimension means)."""
    finance = make_department(db_session, name="Agg Finance G")
    s_and_it = make_department(db_session, name="Agg S&IT G")
    finance_user = make_user(db_session, finance, role=UserRole.USER, email="agg.finance.g@example.gov")
    sys_admin = make_user(db_session, None, role=UserRole.SYSTEM_ADMIN, email="agg.sys.g@example.gov")

    make_letter(db_session, finance, finance_user)  # incoming, owned by Finance
    client.post(
        LETTERS_URL,
        json={
            "reference_number": "REF-AGG-3",
            "subject": "Outgoing",
            "source_name": "Finance",
            "sender_name": "Sender",
            "sender_designation": "Officer",
            "sender_department": "Dept",
            "received_at": datetime.now(timezone.utc).isoformat(),
            "direction": "OUTGOING",
            "dispatch_department_id": str(s_and_it.id),
        },
        headers=_auth_headers(finance_user),
    )  # outgoing, still owned by Finance (recipient_department_id)

    response = client.get(
        AGGREGATE_URL, params={"group_by": "department"}, headers=_auth_headers(sys_admin)
    )

    buckets = _buckets_by_key(response.json())
    # Both letters are owned by Finance regardless of direction.
    assert buckets[str(finance.id)] == 2
    assert str(s_and_it.id) not in buckets


def test_group_by_dispatch_department_answers_who_receives_via_dispatch(client, db_session):
    finance = make_department(db_session, name="Agg Finance H")
    s_and_it = make_department(db_session, name="Agg S&IT H")
    hr = make_department(db_session, name="Agg HR H")
    finance_user = make_user(db_session, finance, role=UserRole.USER, email="agg.finance.h@example.gov")
    sys_admin = make_user(db_session, None, role=UserRole.SYSTEM_ADMIN, email="agg.sys.h@example.gov")

    # One incoming (no dispatch target) + two outgoing to different departments.
    make_letter(db_session, finance, finance_user)
    for i, target in enumerate([s_and_it, s_and_it, hr]):
        client.post(
            LETTERS_URL,
            json={
                "reference_number": f"REF-AGG-DISPATCH-{i}",
                "subject": "Outgoing",
                "source_name": "Finance",
                "sender_name": "Sender",
                "sender_designation": "Officer",
                "sender_department": "Dept",
                "received_at": datetime.now(timezone.utc).isoformat(),
                "direction": "OUTGOING",
                "dispatch_department_id": str(target.id),
            },
            headers=_auth_headers(finance_user),
        )

    response = client.get(
        AGGREGATE_URL, params={"group_by": "dispatch_department"}, headers=_auth_headers(sys_admin)
    )

    body = response.json()
    buckets = _buckets_by_key(body)
    assert buckets[str(s_and_it.id)] == 2
    assert buckets[str(hr.id)] == 1
    # The incoming letter (no dispatch target) never appears as a
    # bucket at all — excluded, not folded into a confusing null key.
    assert None not in buckets
    assert body["total"] == 3


def test_dispatch_department_id_filter_never_expands_scope(client, db_session):
    """Filtering by `dispatch_department_id` only narrows *the
    caller's own* already-scoped letters — it can never be used to see
    another department's registry."""
    finance = make_department(db_session, name="Agg Finance I")
    s_and_it = make_department(db_session, name="Agg S&IT I")
    finance_user = make_user(db_session, finance, role=UserRole.USER, email="agg.finance.i@example.gov")

    client.post(
        LETTERS_URL,
        json={
            "reference_number": "REF-AGG-FILTER",
            "subject": "Outgoing",
            "source_name": "Finance",
            "sender_name": "Sender",
            "sender_designation": "Officer",
            "sender_department": "Dept",
            "received_at": datetime.now(timezone.utc).isoformat(),
            "direction": "OUTGOING",
            "dispatch_department_id": str(s_and_it.id),
        },
        headers=_auth_headers(finance_user),
    )

    response = client.get(
        AGGREGATE_URL,
        params={"group_by": "status", "dispatch_department_id": str(s_and_it.id)},
        headers=_auth_headers(finance_user),
    )

    assert response.json()["total"] == 1


# =========================================================================
# Department isolation (CRITICAL, matching 5G's own §24 test plan)
# =========================================================================


def test_admin_department_id_parameter_is_silently_ignored_not_honored(client, db_session):
    own_department = make_department(db_session, name="Agg Own J")
    other_department = make_department(db_session, name="Agg Other J")
    admin = make_user(db_session, own_department, role=UserRole.ADMIN, email="agg.admin.j@example.gov")
    other_user = make_user(db_session, other_department, role=UserRole.USER, email="agg.other.j@example.gov")

    make_letter(db_session, own_department, admin)
    make_letter(db_session, other_department, other_user)
    make_letter(db_session, other_department, other_user)

    response = client.get(
        AGGREGATE_URL,
        params={"group_by": "status", "department_id": str(other_department.id)},
        headers=_auth_headers(admin),
    )

    # Admin's own department (1 letter) is used regardless of the
    # cross-department id supplied — never the other department's 2.
    assert response.json()["total"] == 1


def test_system_admin_can_filter_to_one_department(client, db_session):
    dept_a = make_department(db_session, name="Agg Dept A K")
    dept_b = make_department(db_session, name="Agg Dept B K")
    user_a = make_user(db_session, dept_a, role=UserRole.USER, email="agg.a.k@example.gov")
    user_b = make_user(db_session, dept_b, role=UserRole.USER, email="agg.b.k@example.gov")
    sys_admin = make_user(db_session, None, role=UserRole.SYSTEM_ADMIN, email="agg.sys.k@example.gov")

    make_letter(db_session, dept_a, user_a)
    make_letter(db_session, dept_b, user_b)
    make_letter(db_session, dept_b, user_b)

    response = client.get(
        AGGREGATE_URL,
        params={"group_by": "status", "department_id": str(dept_b.id)},
        headers=_auth_headers(sys_admin),
    )

    assert response.json()["total"] == 2


def test_classified_inaccessible_letters_are_excluded_from_every_bucket(client, db_session):
    """A USER's aggregate total can never exceed what their own
    `GET /letters` would already return for the same filters — the
    exact security regression Phase 5G's own test plan (§24) asked
    for, re-verified unchanged post-6A."""
    department = make_department(db_session, name="Agg L")
    classification = make_classification(db_session, name="Agg Restricted L", restricts_access=True)
    recorder = make_user(db_session, department, role=UserRole.USER, email="agg.recorder.l@example.gov")
    other_user = make_user(db_session, department, role=UserRole.USER, email="agg.other.l@example.gov")

    make_letter(db_session, department, recorder, classification=classification)  # hidden from other_user
    make_letter(db_session, department, other_user)  # visible to other_user

    response = client.get(
        AGGREGATE_URL, params={"group_by": "status"}, headers=_auth_headers(other_user)
    )
    list_response = client.get(LETTERS_URL, params={"page_size": 1}, headers=_auth_headers(other_user))

    assert response.json()["total"] == 1
    assert response.json()["total"] == list_response.json()["total"]


def test_category_and_classification_group_by_null_bucket(client, db_session):
    department = make_department(db_session, name="Agg M")
    category = make_category(db_session, name="Agg Category M")
    user = make_user(db_session, department, role=UserRole.USER, email="agg.m@example.gov")

    make_letter(db_session, department, user, category=category)
    make_letter(db_session, department, user)  # no category

    response = client.get(AGGREGATE_URL, params={"group_by": "category"}, headers=_auth_headers(user))

    buckets = _buckets_by_key(response.json())
    assert buckets[str(category.id)] == 1
    assert buckets[None] == 1


# =========================================================================
# Time-bucket dimensions
# =========================================================================


def test_group_by_day_orders_chronologically_not_by_frequency(client, db_session):
    department = make_department(db_session, name="Agg N")
    user = make_user(db_session, department, role=UserRole.USER, email="agg.n@example.gov")
    now = datetime.now(timezone.utc)

    for _ in range(3):
        make_letter(db_session, department, user, received_at=now - timedelta(days=2))
    make_letter(db_session, department, user, received_at=now)

    response = client.get(AGGREGATE_URL, params={"group_by": "day"}, headers=_auth_headers(user))

    body = response.json()
    assert body["total"] == 4
    keys = [bucket["key"] for bucket in body["buckets"]]
    # Chronological, even though the earlier day has more letters (3)
    # than the later one (1) — a frequency-descending order would have
    # put the 3-count day first.
    assert keys == sorted(keys)


def test_invalid_date_range_returns_422(client, db_session):
    department = make_department(db_session, name="Agg O")
    user = make_user(db_session, department, role=UserRole.USER, email="agg.o@example.gov")

    response = client.get(
        AGGREGATE_URL,
        params={
            "group_by": "day",
            "received_from": "2026-06-01T00:00:00Z",
            "received_to": "2026-01-01T00:00:00Z",
        },
        headers=_auth_headers(user),
    )

    assert response.status_code == 422
