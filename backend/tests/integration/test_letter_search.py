"""End-to-end tests for Registry Operations & Search (Phase 4C).

Real JWTs, real database-backed Letters (via the `make_letter` factory,
not the HTTP create endpoint, for efficient multi-row setup), real HTTP
requests through `GET /api/v1/letters`, against a real PostgreSQL test
database. Covers pagination, sorting, per-field search, date filtering,
multi-filter AND behavior, department isolation, and — highest priority —
the classified-access query-level fix (docs/architecture/registry-search.md
§8): an inaccessible letter must never inflate `total` or appear on any
page, not just be excluded from `items` on page 1.

Letter CRUD itself (create/get/update/archive) is covered in
test_letter_registry.py — this file is search/list only.
"""

import uuid
from datetime import datetime, timedelta, timezone

from app.core.security import create_access_token
from app.models.enums import UserRole
from tests.factories import make_category, make_classification, make_department, make_letter, make_user

LETTERS_URL = "/api/v1/letters"


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


def _received_at(days_ago=0):
    return datetime.now(timezone.utc) - timedelta(days=days_ago)


# =========================================================================
# PAGINATION
# =========================================================================


def test_default_pagination(client, db_session):
    department = make_department(db_session, name="Pagination Dept 1")
    user = _make_regular_user(db_session, department, email="user.page1@example.gov")
    for i in range(3):
        make_letter(db_session, department, user, reference_number=f"PAGE1-{i}")

    response = client.get(LETTERS_URL, headers=_auth_headers(user))

    assert response.status_code == 200
    body = response.json()
    assert body["page"] == 1
    assert body["page_size"] == 25
    assert body["total"] == 3
    assert body["total_pages"] == 1
    assert len(body["items"]) == 3


def test_custom_page_and_page_size(client, db_session):
    department = make_department(db_session, name="Pagination Dept 2")
    user = _make_regular_user(db_session, department, email="user.page2@example.gov")
    for i in range(5):
        make_letter(db_session, department, user, reference_number=f"PAGE2-{i}", received_at=_received_at(i))

    response = client.get(f"{LETTERS_URL}?page=2&page_size=2", headers=_auth_headers(user))

    assert response.status_code == 200
    body = response.json()
    assert body["page"] == 2
    assert body["page_size"] == 2
    assert body["total"] == 5
    assert body["total_pages"] == 3
    assert len(body["items"]) == 2


def test_page_beyond_available_records_returns_empty(client, db_session):
    department = make_department(db_session, name="Pagination Dept 3")
    user = _make_regular_user(db_session, department, email="user.page3@example.gov")
    make_letter(db_session, department, user, reference_number="PAGE3-ONLY")

    response = client.get(f"{LETTERS_URL}?page=5&page_size=10", headers=_auth_headers(user))

    assert response.status_code == 200
    body = response.json()
    assert body["items"] == []
    assert body["total"] == 1  # total reflects all matching rows, not just this page


def test_page_size_zero_rejected(client, db_session):
    department = make_department(db_session, name="Pagination Dept 4")
    user = _make_regular_user(db_session, department, email="user.page4@example.gov")
    response = client.get(f"{LETTERS_URL}?page_size=0", headers=_auth_headers(user))
    assert response.status_code == 422


def test_page_size_over_maximum_rejected(client, db_session):
    department = make_department(db_session, name="Pagination Dept 5")
    user = _make_regular_user(db_session, department, email="user.page5@example.gov")
    response = client.get(f"{LETTERS_URL}?page_size=101", headers=_auth_headers(user))
    assert response.status_code == 422


def test_page_below_one_rejected(client, db_session):
    department = make_department(db_session, name="Pagination Dept 6")
    user = _make_regular_user(db_session, department, email="user.page6@example.gov")
    response = client.get(f"{LETTERS_URL}?page=0", headers=_auth_headers(user))
    assert response.status_code == 422


# =========================================================================
# SORTING
# =========================================================================


def test_sort_by_received_at_descending_is_default(client, db_session):
    department = make_department(db_session, name="Sort Dept 1")
    user = _make_regular_user(db_session, department, email="user.sort1@example.gov")
    make_letter(db_session, department, user, reference_number="SORT1-OLD", received_at=_received_at(5))
    make_letter(db_session, department, user, reference_number="SORT1-NEW", received_at=_received_at(1))

    response = client.get(LETTERS_URL, headers=_auth_headers(user))
    refs = [item["reference_number"] for item in response.json()["items"]]
    assert refs == ["SORT1-NEW", "SORT1-OLD"]


def test_sort_by_reference_number_ascending(client, db_session):
    department = make_department(db_session, name="Sort Dept 2")
    user = _make_regular_user(db_session, department, email="user.sort2@example.gov")
    make_letter(db_session, department, user, reference_number="B-SORT2")
    make_letter(db_session, department, user, reference_number="A-SORT2")

    response = client.get(
        f"{LETTERS_URL}?sort_by=reference_number&sort_order=asc", headers=_auth_headers(user)
    )
    refs = [item["reference_number"] for item in response.json()["items"]]
    assert refs == ["A-SORT2", "B-SORT2"]


def test_sort_by_subject_descending(client, db_session):
    department = make_department(db_session, name="Sort Dept 3")
    user = _make_regular_user(db_session, department, email="user.sort3@example.gov")
    make_letter(db_session, department, user, reference_number="SORT3-A", subject="Alpha")
    make_letter(db_session, department, user, reference_number="SORT3-Z", subject="Zeta")

    response = client.get(
        f"{LETTERS_URL}?sort_by=subject&sort_order=desc", headers=_auth_headers(user)
    )
    refs = [item["reference_number"] for item in response.json()["items"]]
    assert refs == ["SORT3-Z", "SORT3-A"]


def test_sort_by_created_at(client, db_session):
    department = make_department(db_session, name="Sort Dept 4")
    user = _make_regular_user(db_session, department, email="user.sort4@example.gov")
    make_letter(db_session, department, user, reference_number="SORT4-A")
    make_letter(db_session, department, user, reference_number="SORT4-B")

    response = client.get(f"{LETTERS_URL}?sort_by=created_at&sort_order=asc", headers=_auth_headers(user))
    assert response.status_code == 200
    assert len(response.json()["items"]) == 2


def test_invalid_sort_field_rejected(client, db_session):
    department = make_department(db_session, name="Sort Dept 5")
    user = _make_regular_user(db_session, department, email="user.sort5@example.gov")
    response = client.get(f"{LETTERS_URL}?sort_by=text_content", headers=_auth_headers(user))
    assert response.status_code == 422


def test_invalid_sort_order_rejected(client, db_session):
    department = make_department(db_session, name="Sort Dept 6")
    user = _make_regular_user(db_session, department, email="user.sort6@example.gov")
    response = client.get(f"{LETTERS_URL}?sort_order=sideways", headers=_auth_headers(user))
    assert response.status_code == 422


def test_stable_ordering_via_secondary_sort_key(client, db_session):
    """Two letters with an identical received_at must still order
    consistently across repeated requests — proven here by requesting
    the same query twice and comparing item order, not just item
    membership."""
    department = make_department(db_session, name="Sort Dept 7")
    user = _make_regular_user(db_session, department, email="user.sort7@example.gov")
    same_time = _received_at(2)
    make_letter(db_session, department, user, reference_number="SORT7-A", received_at=same_time)
    make_letter(db_session, department, user, reference_number="SORT7-B", received_at=same_time)
    make_letter(db_session, department, user, reference_number="SORT7-C", received_at=same_time)

    first = client.get(LETTERS_URL, headers=_auth_headers(user))
    second = client.get(LETTERS_URL, headers=_auth_headers(user))
    first_order = [item["id"] for item in first.json()["items"]]
    second_order = [item["id"] for item in second.json()["items"]]
    assert first_order == second_order


# =========================================================================
# TEXT SEARCH
# =========================================================================


def test_search_by_reference_number_contains(client, db_session):
    department = make_department(db_session, name="Search Dept 1")
    user = _make_regular_user(db_session, department, email="user.search1@example.gov")
    make_letter(db_session, department, user, reference_number="ABC-2026-XYZ")
    make_letter(db_session, department, user, reference_number="OTHER-REF")

    response = client.get(f"{LETTERS_URL}?reference_number=2026", headers=_auth_headers(user))
    refs = {item["reference_number"] for item in response.json()["items"]}
    assert refs == {"ABC-2026-XYZ"}


def test_search_by_subject_contains(client, db_session):
    department = make_department(db_session, name="Search Dept 2")
    user = _make_regular_user(db_session, department, email="user.search2@example.gov")
    make_letter(db_session, department, user, reference_number="SUBJ2-A", subject="Annual Budget Review")
    make_letter(db_session, department, user, reference_number="SUBJ2-B", subject="Staff Meeting Notes")

    response = client.get(f"{LETTERS_URL}?subject=budget", headers=_auth_headers(user))
    refs = {item["reference_number"] for item in response.json()["items"]}
    assert refs == {"SUBJ2-A"}


def test_search_by_sender_name_contains(client, db_session):
    department = make_department(db_session, name="Search Dept 3")
    user = _make_regular_user(db_session, department, email="user.search3@example.gov")
    make_letter(db_session, department, user, reference_number="SENDER3-A", sender_name="Ahmad Khan")
    make_letter(db_session, department, user, reference_number="SENDER3-B", sender_name="Bilal Raza")

    response = client.get(f"{LETTERS_URL}?sender_name=khan", headers=_auth_headers(user))
    refs = {item["reference_number"] for item in response.json()["items"]}
    assert refs == {"SENDER3-A"}


def test_search_by_sender_designation_contains(client, db_session):
    department = make_department(db_session, name="Search Dept 4")
    user = _make_regular_user(db_session, department, email="user.search4@example.gov")
    make_letter(db_session, department, user, reference_number="DESIG4-A", sender_designation="Director General")
    make_letter(db_session, department, user, reference_number="DESIG4-B", sender_designation="Clerk")

    response = client.get(f"{LETTERS_URL}?sender_designation=director", headers=_auth_headers(user))
    refs = {item["reference_number"] for item in response.json()["items"]}
    assert refs == {"DESIG4-A"}


def test_search_by_sender_department_contains(client, db_session):
    department = make_department(db_session, name="Search Dept 5")
    user = _make_regular_user(db_session, department, email="user.search5@example.gov")
    make_letter(db_session, department, user, reference_number="SDEPT5-A", sender_department="Planning and Development")
    make_letter(db_session, department, user, reference_number="SDEPT5-B", sender_department="Finance")

    response = client.get(f"{LETTERS_URL}?sender_department=planning", headers=_auth_headers(user))
    refs = {item["reference_number"] for item in response.json()["items"]}
    assert refs == {"SDEPT5-A"}


def test_search_by_source_name_contains(client, db_session):
    department = make_department(db_session, name="Search Dept 6")
    user = _make_regular_user(db_session, department, email="user.search6@example.gov")
    make_letter(db_session, department, user, reference_number="SRC6-A", source_name="Regional Power Authority")
    make_letter(db_session, department, user, reference_number="SRC6-B", source_name="Vendor Ltd.")

    response = client.get(f"{LETTERS_URL}?source_name=power", headers=_auth_headers(user))
    refs = {item["reference_number"] for item in response.json()["items"]}
    assert refs == {"SRC6-A"}


def test_search_by_source_location_contains(client, db_session):
    department = make_department(db_session, name="Search Dept 7")
    user = _make_regular_user(db_session, department, email="user.search7@example.gov")
    make_letter(db_session, department, user, reference_number="LOC7-A", source_location="Quetta")
    make_letter(db_session, department, user, reference_number="LOC7-B", source_location="Karachi")

    response = client.get(f"{LETTERS_URL}?source_location=quetta", headers=_auth_headers(user))
    refs = {item["reference_number"] for item in response.json()["items"]}
    assert refs == {"LOC7-A"}


def test_search_is_case_insensitive(client, db_session):
    department = make_department(db_session, name="Search Dept 8")
    user = _make_regular_user(db_session, department, email="user.search8@example.gov")
    make_letter(db_session, department, user, reference_number="CASE8-A", subject="URGENT MATTER")

    response = client.get(f"{LETTERS_URL}?subject=urgent", headers=_auth_headers(user))
    refs = {item["reference_number"] for item in response.json()["items"]}
    assert refs == {"CASE8-A"}


def test_search_no_results(client, db_session):
    department = make_department(db_session, name="Search Dept 9")
    user = _make_regular_user(db_session, department, email="user.search9@example.gov")
    make_letter(db_session, department, user, reference_number="NORESULT9-A", subject="Something")

    response = client.get(f"{LETTERS_URL}?subject=nonexistentterm", headers=_auth_headers(user))
    assert response.status_code == 200
    body = response.json()
    assert body["items"] == []
    assert body["total"] == 0


# =========================================================================
# EXACT FILTERS
# =========================================================================


def test_filter_by_category(client, db_session):
    department = make_department(db_session, name="Filter Dept 1")
    user = _make_regular_user(db_session, department, email="user.filter1@example.gov")
    category_a = make_category(db_session, name="Category Filter A")
    category_b = make_category(db_session, name="Category Filter B")
    make_letter(db_session, department, user, reference_number="CATF1-A", category=category_a)
    make_letter(db_session, department, user, reference_number="CATF1-B", category=category_b)

    response = client.get(f"{LETTERS_URL}?category_id={category_a.id}", headers=_auth_headers(user))
    refs = {item["reference_number"] for item in response.json()["items"]}
    assert refs == {"CATF1-A"}


def test_filter_by_classification(client, db_session):
    department = make_department(db_session, name="Filter Dept 2")
    user = _make_regular_user(db_session, department, email="user.filter2@example.gov")
    classification_a = make_classification(db_session, name="Classification Filter A")
    classification_b = make_classification(db_session, name="Classification Filter B")
    make_letter(db_session, department, user, reference_number="CLSF2-A", classification=classification_a)
    make_letter(db_session, department, user, reference_number="CLSF2-B", classification=classification_b)

    response = client.get(
        f"{LETTERS_URL}?classification_id={classification_a.id}", headers=_auth_headers(user)
    )
    refs = {item["reference_number"] for item in response.json()["items"]}
    assert refs == {"CLSF2-A"}


def test_filter_by_status(client, db_session):
    department = make_department(db_session, name="Filter Dept 3")
    user = _make_regular_user(db_session, department, email="user.filter3@example.gov")
    letter = make_letter(db_session, department, user, reference_number="STATF3-ARCHIVED")
    make_letter(db_session, department, user, reference_number="STATF3-ACTIVE")
    client.delete(f"{LETTERS_URL}/{letter.id}", headers=_auth_headers(user))  # archive

    response = client.get(f"{LETTERS_URL}?status=ARCHIVED", headers=_auth_headers(user))
    refs = {item["reference_number"] for item in response.json()["items"]}
    assert refs == {"STATF3-ARCHIVED"}


# =========================================================================
# DATE FILTERS
# =========================================================================


def test_received_from_filters_out_earlier_letters(client, db_session):
    department = make_department(db_session, name="Date Dept 1")
    user = _make_regular_user(db_session, department, email="user.date1@example.gov")
    make_letter(db_session, department, user, reference_number="DATE1-OLD", received_at=_received_at(30))
    make_letter(db_session, department, user, reference_number="DATE1-NEW", received_at=_received_at(1))

    # `params=` (not raw f-string URL interpolation) so httpx correctly
    # URL-encodes the ISO timestamp's "+00:00" offset — an unencoded "+"
    # in a query string is interpreted as a space, corrupting the value.
    response = client.get(
        LETTERS_URL, params={"received_from": _received_at(10).isoformat()}, headers=_auth_headers(user)
    )
    refs = {item["reference_number"] for item in response.json()["items"]}
    assert refs == {"DATE1-NEW"}


def test_received_to_filters_out_later_letters(client, db_session):
    department = make_department(db_session, name="Date Dept 2")
    user = _make_regular_user(db_session, department, email="user.date2@example.gov")
    make_letter(db_session, department, user, reference_number="DATE2-OLD", received_at=_received_at(30))
    make_letter(db_session, department, user, reference_number="DATE2-NEW", received_at=_received_at(1))

    response = client.get(
        LETTERS_URL, params={"received_to": _received_at(10).isoformat()}, headers=_auth_headers(user)
    )
    refs = {item["reference_number"] for item in response.json()["items"]}
    assert refs == {"DATE2-OLD"}


def test_received_date_boundaries_are_inclusive(client, db_session):
    department = make_department(db_session, name="Date Dept 3")
    user = _make_regular_user(db_session, department, email="user.date3@example.gov")
    exact_time = _received_at(5)
    make_letter(db_session, department, user, reference_number="DATE3-BOUNDARY", received_at=exact_time)

    iso = exact_time.isoformat()
    response = client.get(
        LETTERS_URL, params={"received_from": iso, "received_to": iso}, headers=_auth_headers(user)
    )
    refs = {item["reference_number"] for item in response.json()["items"]}
    assert refs == {"DATE3-BOUNDARY"}


def test_reversed_date_range_rejected(client, db_session):
    department = make_department(db_session, name="Date Dept 4")
    user = _make_regular_user(db_session, department, email="user.date4@example.gov")

    response = client.get(
        LETTERS_URL,
        params={"received_from": _received_at(1).isoformat(), "received_to": _received_at(10).isoformat()},
        headers=_auth_headers(user),
    )
    assert response.status_code == 422


# =========================================================================
# MULTI-FILTER AND BEHAVIOR
# =========================================================================


def test_multiple_filters_combine_with_and(client, db_session):
    department = make_department(db_session, name="Combo Dept 1")
    user = _make_regular_user(db_session, department, email="user.combo1@example.gov")
    category = make_category(db_session, name="Combo Category")
    make_letter(
        db_session, department, user, reference_number="COMBO1-MATCH",
        category=category, subject="Budget Report", received_at=_received_at(2),
    )
    # Matches category but not subject.
    make_letter(
        db_session, department, user, reference_number="COMBO1-CATONLY",
        category=category, subject="Staff Notice", received_at=_received_at(2),
    )
    # Matches subject but not category.
    make_letter(
        db_session, department, user, reference_number="COMBO1-SUBJONLY",
        subject="Budget Notes", received_at=_received_at(2),
    )

    response = client.get(
        f"{LETTERS_URL}?category_id={category.id}&subject=budget", headers=_auth_headers(user)
    )
    refs = {item["reference_number"] for item in response.json()["items"]}
    assert refs == {"COMBO1-MATCH"}


# =========================================================================
# DEPARTMENT ISOLATION / AUTHORIZATION
# =========================================================================


def test_user_search_scoped_to_own_department(client, db_session):
    dept_a = make_department(db_session, name="Isolation Dept A1")
    dept_b = make_department(db_session, name="Isolation Dept B1")
    user_a = _make_regular_user(db_session, dept_a, email="user.isoA1@example.gov")
    user_b = _make_regular_user(db_session, dept_b, email="user.isoB1@example.gov")
    make_letter(db_session, dept_a, user_a, reference_number="ISOA1")
    make_letter(db_session, dept_b, user_b, reference_number="ISOB1")

    response = client.get(LETTERS_URL, headers=_auth_headers(user_a))
    refs = {item["reference_number"] for item in response.json()["items"]}
    assert refs == {"ISOA1"}


def test_user_cannot_expand_scope_via_department_filter(client, db_session):
    dept_a = make_department(db_session, name="Isolation Dept A2")
    dept_b = make_department(db_session, name="Isolation Dept B2")
    user_a = _make_regular_user(db_session, dept_a, email="user.isoA2@example.gov")
    user_b = _make_regular_user(db_session, dept_b, email="user.isoB2@example.gov")
    make_letter(db_session, dept_a, user_a, reference_number="ISOA2")
    make_letter(db_session, dept_b, user_b, reference_number="ISOB2")

    response = client.get(f"{LETTERS_URL}?department_id={dept_b.id}", headers=_auth_headers(user_a))
    refs = {item["reference_number"] for item in response.json()["items"]}
    assert refs == {"ISOA2"}  # department_id parameter silently ignored


def test_admin_search_scoped_to_own_department(client, db_session):
    dept_a = make_department(db_session, name="Isolation Dept A3")
    dept_b = make_department(db_session, name="Isolation Dept B3")
    admin_a = _make_department_admin(db_session, dept_a, email="admin.isoA3@example.gov")
    user_b = _make_regular_user(db_session, dept_b, email="user.isoB3@example.gov")
    make_letter(db_session, dept_a, admin_a, reference_number="ISOA3")
    make_letter(db_session, dept_b, user_b, reference_number="ISOB3")

    response = client.get(LETTERS_URL, headers=_auth_headers(admin_a))
    refs = {item["reference_number"] for item in response.json()["items"]}
    assert refs == {"ISOA3"}


def test_admin_cannot_expand_scope_via_department_filter(client, db_session):
    dept_a = make_department(db_session, name="Isolation Dept A4")
    dept_b = make_department(db_session, name="Isolation Dept B4")
    admin_a = _make_department_admin(db_session, dept_a, email="admin.isoA4@example.gov")
    user_b = _make_regular_user(db_session, dept_b, email="user.isoB4@example.gov")
    make_letter(db_session, dept_a, admin_a, reference_number="ISOA4")
    make_letter(db_session, dept_b, user_b, reference_number="ISOB4")

    response = client.get(f"{LETTERS_URL}?department_id={dept_b.id}", headers=_auth_headers(admin_a))
    refs = {item["reference_number"] for item in response.json()["items"]}
    assert refs == {"ISOA4"}


def test_system_admin_can_search_specific_department(client, db_session):
    dept_a = make_department(db_session, name="Isolation Dept A5")
    dept_b = make_department(db_session, name="Isolation Dept B5")
    user_a = _make_regular_user(db_session, dept_a, email="user.isoA5@example.gov")
    user_b = _make_regular_user(db_session, dept_b, email="user.isoB5@example.gov")
    sys_admin = _make_system_admin(db_session, email="sys.admin.iso5@example.gov")
    make_letter(db_session, dept_a, user_a, reference_number="ISOA5")
    make_letter(db_session, dept_b, user_b, reference_number="ISOB5")

    response = client.get(f"{LETTERS_URL}?department_id={dept_b.id}", headers=_auth_headers(sys_admin))
    refs = {item["reference_number"] for item in response.json()["items"]}
    assert refs == {"ISOB5"}


def test_system_admin_search_without_department_sees_everything(client, db_session):
    dept_a = make_department(db_session, name="Isolation Dept A6")
    dept_b = make_department(db_session, name="Isolation Dept B6")
    user_a = _make_regular_user(db_session, dept_a, email="user.isoA6@example.gov")
    user_b = _make_regular_user(db_session, dept_b, email="user.isoB6@example.gov")
    sys_admin = _make_system_admin(db_session, email="sys.admin.iso6@example.gov")
    make_letter(db_session, dept_a, user_a, reference_number="ISOA6")
    make_letter(db_session, dept_b, user_b, reference_number="ISOB6")

    response = client.get(LETTERS_URL, headers=_auth_headers(sys_admin))
    refs = {item["reference_number"] for item in response.json()["items"]}
    assert {"ISOA6", "ISOB6"} <= refs


# =========================================================================
# CLASSIFIED RECORDS — highest priority: the query-level authorization fix
# =========================================================================


def test_classified_letter_visible_to_recorder_in_search(client, db_session):
    department = make_department(db_session, name="Classified Search Dept 1")
    recorder = _make_regular_user(db_session, department, email="recorder.clssearch1@example.gov")
    classification = make_classification(db_session, name="Classified Search 1", restricts_access=True)
    make_letter(
        db_session, department, recorder, reference_number="CLSSEARCH1",
        classification=classification, subject="Restricted Matter",
    )

    response = client.get(f"{LETTERS_URL}?subject=restricted", headers=_auth_headers(recorder))
    refs = {item["reference_number"] for item in response.json()["items"]}
    assert refs == {"CLSSEARCH1"}


def test_classified_letter_invisible_to_non_recorder_in_search(client, db_session):
    department = make_department(db_session, name="Classified Search Dept 2")
    recorder = _make_regular_user(db_session, department, email="recorder.clssearch2@example.gov")
    other_user = _make_regular_user(db_session, department, email="other.clssearch2@example.gov")
    classification = make_classification(db_session, name="Classified Search 2", restricts_access=True)
    make_letter(
        db_session, department, recorder, reference_number="CLSSEARCH2",
        classification=classification, subject="Restricted Matter",
    )

    response = client.get(f"{LETTERS_URL}?subject=restricted", headers=_auth_headers(other_user))
    assert response.json()["items"] == []


def test_classified_record_excluded_from_total_count(client, db_session):
    """The central regression for docs/architecture/registry-search.md
    §8: a non-recording USER's `total` must equal exactly the number of
    letters they can actually see, not the number of rows matching the
    department/status/category/classification/date filters before
    classified-access narrowing. This is the direct proof that `total` is
    computed from the same query as `items`, not a separately-scoped
    count."""
    department = make_department(db_session, name="Classified Count Dept")
    recorder = _make_regular_user(db_session, department, email="recorder.clscount@example.gov")
    other_user = _make_regular_user(db_session, department, email="other.clscount@example.gov")
    classification = make_classification(db_session, name="Classified Count", restricts_access=True)

    # 3 ordinary letters other_user can see, plus 2 classified letters
    # recorded by someone else that other_user must NOT see or count.
    for i in range(3):
        make_letter(db_session, department, other_user, reference_number=f"CLSCOUNT-VISIBLE-{i}")
    for i in range(2):
        make_letter(
            db_session, department, recorder, reference_number=f"CLSCOUNT-HIDDEN-{i}",
            classification=classification,
        )

    response = client.get(LETTERS_URL, headers=_auth_headers(other_user))
    body = response.json()
    assert body["total"] == 3  # not 5
    refs = {item["reference_number"] for item in body["items"]}
    assert all(ref.startswith("CLSCOUNT-VISIBLE") for ref in refs)


def test_classified_record_excluded_across_all_pages(client, db_session):
    """Same finding as above, verified across pagination specifically —
    a classified letter must not occupy a page slot or shift pagination
    for a caller who can't see it."""
    department = make_department(db_session, name="Classified Pagination Dept")
    recorder = _make_regular_user(db_session, department, email="recorder.clspage@example.gov")
    other_user = _make_regular_user(db_session, department, email="other.clspage@example.gov")
    classification = make_classification(db_session, name="Classified Pagination", restricts_access=True)

    for i in range(4):
        make_letter(
            db_session, department, other_user, reference_number=f"CLSPAGE-VISIBLE-{i}",
            received_at=_received_at(i),
        )
    make_letter(
        db_session, department, recorder, reference_number="CLSPAGE-HIDDEN",
        classification=classification, received_at=_received_at(0),
    )

    page_1 = client.get(f"{LETTERS_URL}?page=1&page_size=2", headers=_auth_headers(other_user)).json()
    page_2 = client.get(f"{LETTERS_URL}?page=2&page_size=2", headers=_auth_headers(other_user)).json()

    assert page_1["total"] == 4
    assert page_1["total_pages"] == 2
    all_refs = {item["reference_number"] for item in page_1["items"] + page_2["items"]}
    assert "CLSPAGE-HIDDEN" not in all_refs
    assert len(all_refs) == 4


def test_admin_sees_classified_letters_in_search_and_count(client, db_session):
    department = make_department(db_session, name="Classified Admin Dept")
    recorder = _make_regular_user(db_session, department, email="recorder.clsadmin@example.gov")
    admin = _make_department_admin(db_session, department, email="admin.clsadmin@example.gov")
    classification = make_classification(db_session, name="Classified Admin", restricts_access=True)
    make_letter(
        db_session, department, recorder, reference_number="CLSADMIN", classification=classification
    )

    response = client.get(LETTERS_URL, headers=_auth_headers(admin))
    body = response.json()
    assert body["total"] == 1
    refs = {item["reference_number"] for item in body["items"]}
    assert refs == {"CLSADMIN"}


def test_system_admin_sees_classified_letters_in_search_and_count(client, db_session):
    department = make_department(db_session, name="Classified SysAdmin Dept")
    recorder = _make_regular_user(db_session, department, email="recorder.clssysadmin@example.gov")
    sys_admin = _make_system_admin(db_session, email="sys.admin.clssysadmin@example.gov")
    classification = make_classification(db_session, name="Classified SysAdmin", restricts_access=True)
    make_letter(
        db_session, department, recorder, reference_number="CLSSYSADMIN", classification=classification
    )

    response = client.get(LETTERS_URL, headers=_auth_headers(sys_admin))
    body = response.json()
    assert body["total"] == 1


# =========================================================================
# ENUMERATION SAFETY
# =========================================================================


def test_search_matching_only_inaccessible_letters_returns_safely_empty(client, db_session):
    """A search whose only matches are letters the caller cannot see must
    look identical to a search that matched nothing at all — no error, no
    hint that something exists but is forbidden."""
    department = make_department(db_session, name="Enumeration Dept")
    recorder = _make_regular_user(db_session, department, email="recorder.enum@example.gov")
    other_user = _make_regular_user(db_session, department, email="other.enum@example.gov")
    classification = make_classification(db_session, name="Enumeration Classified", restricts_access=True)
    make_letter(
        db_session, department, recorder, reference_number="ENUM-SECRET",
        classification=classification, subject="Secret Project Update",
    )

    response = client.get(f"{LETTERS_URL}?subject=secret", headers=_auth_headers(other_user))
    assert response.status_code == 200
    body = response.json()
    assert body["items"] == []
    assert body["total"] == 0
