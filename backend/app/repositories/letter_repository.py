"""Data access for Letter rows.

`find_by_id` eagerly loads `classification` — `app/services/authorization.py:assert_letter_access`
needs `letter.classification.restricts_access` for a single already-
loaded row, without a second query being an easy-to-forget requirement
at every single-resource call site (get/update/archive).

`list_letters` is different on purpose: it does **not** eager-load
`classification` and does **not** filter its results in Python. The
classified-access rule is instead expressed as a SQL `WHERE` clause
(`visibility_filter`, built by
`app/services/authorization.py:letter_visibility_filter` and passed in by
the service) so that `COUNT` and `LIMIT`/`OFFSET` both operate on the
exact same, already-authorized row set — see
docs/architecture/registry-search.md §8 for why a fetch-then-filter
pattern here would be a count/pagination leakage risk once pagination
exists (which, as of this phase, it does).

Phase 6C (docs/architecture/dashboard-analytics-api.md's own Phase 6C
implementation record) extracts the filter-building logic below into
`_build_filter_conditions` — a real refactor Phase 5G's review named
but did not perform — so `list_letters` and the new `aggregate_letters`
share exactly one filter implementation, never two independently-
maintained copies that could silently drift apart. `aggregate_letters`
reuses this for a `GROUP BY` in place of pagination; nothing about the
filters themselves changed.
"""

import uuid
from datetime import datetime
from typing import Any, List, Optional, Tuple

from sqlalchemy import ColumnElement, func, select
from sqlalchemy.orm import Session, joinedload

from app.models.classification import Classification
from app.models.enums import LetterDirection, LetterStatus
from app.models.letter import Letter

# Explicit whitelist — the only columns a client's `sort_by` value may
# ever select. Never build an ORDER BY from a raw client string; see
# app/api/v1/endpoints/letters.py for how a client value is mapped to one
# of these keys (and rejected with 422 if it isn't one of them) before it
# ever reaches this module.
SORTABLE_COLUMNS = {
    "received_at": Letter.received_at,
    "created_at": Letter.created_at,
    "reference_number": Letter.reference_number,
    "subject": Letter.subject,
}

# The plain-column `group_by` dimensions `aggregate_letters` supports —
# keyed by the same plain strings `LetterGroupByField` (schemas/letter.py)
# takes its values from, the same "repository never imports the schema
# enum, the caller passes `.value`" convention `SORTABLE_COLUMNS` above
# already established. Every column here is already individually indexed
# (docs/architecture/dashboard-analytics-api.md §3, re-confirmed
# unchanged by Phase 6A's migration). `"department"` groups by
# `recipient_department_id` — the *owning* department for either
# direction (Phase 6A's own reassessment of Phase 5G's original, pre-6A
# "department" dimension, which only ever meant "recipient" in a system
# with no outgoing letters) — `"dispatch_department"` (new this phase)
# groups by `dispatch_department_id`, the destination of an `OUTGOING`
# letter, always `NULL` for `INCOMING` ones. `diary_number`/
# `recorded_from_letter_id`/`continuation_of_letter_id` deliberately have
# no dimension here — nothing in the confirmed dashboard requirements
# asks to group by any of them.
GROUP_BY_COLUMNS = {
    "status": Letter.status,
    "category": Letter.category_id,
    "classification": Letter.classification_id,
    "department": Letter.recipient_department_id,
    "dispatch_department": Letter.dispatch_department_id,
    "direction": Letter.direction,
}

# The three time-bucket dimensions — `func.date_trunc`, not application-
# side date math (docs/architecture/dashboard-analytics-api.md §11's own
# recommendation, still valid: PostgreSQL's native bucketing function
# against the already-indexed `received_at` column). `received_at` is
# reused for both directions per `docs/architecture/correspondence.md`
# §5 — "the date this correspondence record pertains to."
GROUP_BY_DATE_TRUNC = {"day", "week", "month"}


def _ilike_escape(term: str) -> str:
    """Escape SQL LIKE/ILIKE wildcards (`%`, `_`) and the escape
    character itself in free-text search input, so a search term that
    happens to contain a literal `%` or `_` (e.g. a reference number
    fragment like "50%-approved") matches literally rather than acting as
    a wildcard. `\\` is PostgreSQL's default `LIKE` escape character."""
    return term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


class LetterRepository:
    def __init__(self, session: Session):
        self.session = session

    def find_by_id(self, letter_id: uuid.UUID) -> Optional[Letter]:
        stmt = (
            select(Letter)
            .where(Letter.id == letter_id)
            .options(joinedload(Letter.classification))
        )
        return self.session.execute(stmt).unique().scalar_one_or_none()

    def _build_filter_conditions(
        self,
        *,
        recipient_department_id: Optional[uuid.UUID] = None,
        status_filter: Optional[LetterStatus] = None,
        direction_filter: Optional[LetterDirection] = None,
        category_id: Optional[uuid.UUID] = None,
        classification_id: Optional[uuid.UUID] = None,
        dispatch_department_id: Optional[uuid.UUID] = None,
        reference_number: Optional[str] = None,
        subject: Optional[str] = None,
        sender_name: Optional[str] = None,
        sender_designation: Optional[str] = None,
        sender_department: Optional[str] = None,
        source_name: Optional[str] = None,
        source_location: Optional[str] = None,
        received_from: Optional[datetime] = None,
        received_to: Optional[datetime] = None,
        visibility_filter: Optional[ColumnElement[bool]] = None,
    ) -> Tuple[List[ColumnElement[bool]], bool]:
        """Returns `(conditions, needs_classification_join)` — every
        `WHERE` predicate `list_letters` and `aggregate_letters` (Phase
        6C) both need, built exactly once so the two can never drift
        apart (docs/architecture/dashboard-analytics-api.md §4's own
        recommendation, performed here). Callers apply `conditions` to
        their own `select(...)` — a full `Letter` entity select for
        `list_letters`, a `GROUP BY`/`func.count()` projection for
        `aggregate_letters` — since the two need different `SELECT`
        clauses, not just different `WHERE` clauses; only the predicate-
        building is shared.

        `dispatch_department_id` (Phase 6A/6C) filters
        `Letter.dispatch_department_id` — safe for any role, unlike
        `recipient_department_id`: it can never expand a caller's scope
        beyond their own already-enforced `recipient_department_id`
        boundary, it only narrows *which of the caller's own letters*
        match, the same reasoning `category_id`/`classification_id`
        already rely on.
        """
        conditions: List[ColumnElement[bool]] = []
        needs_join = visibility_filter is not None

        if visibility_filter is not None:
            conditions.append(visibility_filter)
        if recipient_department_id is not None:
            conditions.append(Letter.recipient_department_id == recipient_department_id)
        if status_filter is not None:
            conditions.append(Letter.status == status_filter)
        if direction_filter is not None:
            conditions.append(Letter.direction == direction_filter)
        if category_id is not None:
            conditions.append(Letter.category_id == category_id)
        if classification_id is not None:
            conditions.append(Letter.classification_id == classification_id)
        if dispatch_department_id is not None:
            conditions.append(Letter.dispatch_department_id == dispatch_department_id)

        if reference_number is not None:
            conditions.append(Letter.reference_number.ilike(f"%{_ilike_escape(reference_number)}%"))
        if subject is not None:
            conditions.append(Letter.subject.ilike(f"%{_ilike_escape(subject)}%"))
        if sender_name is not None:
            conditions.append(Letter.sender_name.ilike(f"%{_ilike_escape(sender_name)}%"))
        if sender_designation is not None:
            conditions.append(Letter.sender_designation.ilike(f"%{_ilike_escape(sender_designation)}%"))
        if sender_department is not None:
            conditions.append(Letter.sender_department.ilike(f"%{_ilike_escape(sender_department)}%"))
        if source_name is not None:
            conditions.append(Letter.source_name.ilike(f"%{_ilike_escape(source_name)}%"))
        if source_location is not None:
            conditions.append(Letter.source_location.ilike(f"%{_ilike_escape(source_location)}%"))

        if received_from is not None:
            conditions.append(Letter.received_at >= received_from)
        if received_to is not None:
            conditions.append(Letter.received_at <= received_to)

        return conditions, needs_join

    def list_letters(
        self,
        *,
        recipient_department_id: Optional[uuid.UUID] = None,
        status_filter: Optional[LetterStatus] = None,
        direction_filter: Optional[LetterDirection] = None,
        category_id: Optional[uuid.UUID] = None,
        classification_id: Optional[uuid.UUID] = None,
        reference_number: Optional[str] = None,
        subject: Optional[str] = None,
        sender_name: Optional[str] = None,
        sender_designation: Optional[str] = None,
        sender_department: Optional[str] = None,
        source_name: Optional[str] = None,
        source_location: Optional[str] = None,
        received_from: Optional[datetime] = None,
        received_to: Optional[datetime] = None,
        visibility_filter: Optional[ColumnElement[bool]] = None,
        sort_column_key: str = "received_at",
        sort_descending: bool = True,
        page: int = 1,
        page_size: int = 25,
    ) -> Tuple[List[Letter], int]:
        """Returns `(items_for_this_page, total_matching_rows)`. Both
        numbers come from the *same* filtered statement (`stmt`,
        built once below) — `count_stmt` and the paginated `items_stmt`
        are both derived from it, not built as two independently-
        maintained queries, so there is no way for them to disagree
        about which rows are visible. This is the direct fix for the
        finding in docs/architecture/registry-search.md §8: an
        inaccessible row can no longer inflate `total` or slip into a
        page, because it was never in `stmt` to begin with.

        `recipient_department_id=None` means "no department filter" —
        only a valid query for a SYSTEM_ADMIN caller; a USER/ADMIN
        caller's service-layer call always supplies their own
        department_id (unchanged from before this phase).
        """
        conditions, needs_join = self._build_filter_conditions(
            recipient_department_id=recipient_department_id,
            status_filter=status_filter,
            direction_filter=direction_filter,
            category_id=category_id,
            classification_id=classification_id,
            reference_number=reference_number,
            subject=subject,
            sender_name=sender_name,
            sender_designation=sender_designation,
            sender_department=sender_department,
            source_name=source_name,
            source_location=source_location,
            received_from=received_from,
            received_to=received_to,
            visibility_filter=visibility_filter,
        )

        stmt = select(Letter)
        if needs_join:
            # Only joined when actually needed (USER caller) — an
            # ADMIN/SYSTEM_ADMIN query pays no extra join cost.
            stmt = stmt.outerjoin(Classification, Letter.classification_id == Classification.id)
        stmt = stmt.where(*conditions)

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = self.session.execute(count_stmt).scalar_one()

        sort_column = SORTABLE_COLUMNS[sort_column_key]
        order = sort_column.desc() if sort_descending else sort_column.asc()
        # Deterministic secondary sort by primary key — without it, rows
        # with equal sort-column values (e.g. two letters both received
        # at the same recorded timestamp) could appear in a different
        # order across requests, making page N's contents unstable.
        items_stmt = (
            stmt.order_by(order, Letter.id.asc())
            .limit(page_size)
            .offset((page - 1) * page_size)
        )
        items = list(self.session.execute(items_stmt).unique().scalars().all())

        return items, total

    def aggregate_letters(
        self,
        *,
        group_by: str,
        recipient_department_id: Optional[uuid.UUID] = None,
        status_filter: Optional[LetterStatus] = None,
        direction_filter: Optional[LetterDirection] = None,
        category_id: Optional[uuid.UUID] = None,
        classification_id: Optional[uuid.UUID] = None,
        dispatch_department_id: Optional[uuid.UUID] = None,
        received_from: Optional[datetime] = None,
        received_to: Optional[datetime] = None,
        visibility_filter: Optional[ColumnElement[bool]] = None,
    ) -> List[Tuple[Any, int]]:
        """Phase 6C (docs/architecture/dashboard-analytics-api.md's own
        implementation record). One `GROUP BY`/`func.count()` query,
        built from the *identical* filter predicates `list_letters`
        applies (`_build_filter_conditions` above) — never a second,
        independently-maintained authorization/filter path, and never a
        row fetched into Python for counting (docs/architecture/
        dashboard-analytics-api.md §11's own "no N+1, no client-side
        aggregation" instruction). `group_by` is a plain string — the
        caller (the service layer) passes an already-validated
        `LetterGroupByField.value`; this repository has no reason to
        import the schema-layer enum (the same "repository takes a
        plain string key" convention `list_letters`'s own
        `sort_column_key` already uses).

        Returns a list of `(bucket_key, count)` tuples, raw from the
        database — a UUID, an enum string, a `datetime`, or `None`
        (never a resolved category/classification/department *name*;
        resolving an id to a display name is the frontend's own
        existing job, matching `docs/architecture/
        dashboard-analytics-api.md` §13's explicit instruction). Not
        paginated — `group_by` has no `page`/`page_size` parameter at
        all, since a bucket count, unlike a row list, is never too large
        to return in one response at this project's expected scale
        (a handful of departments/categories/classifications, or one
        row per day/week/month bucket).
        """
        conditions, needs_join = self._build_filter_conditions(
            recipient_department_id=recipient_department_id,
            status_filter=status_filter,
            direction_filter=direction_filter,
            category_id=category_id,
            classification_id=classification_id,
            dispatch_department_id=dispatch_department_id,
            received_from=received_from,
            received_to=received_to,
            visibility_filter=visibility_filter,
        )

        if group_by == "dispatch_department":
            # Grouping "incoming letters" (always NULL here) alongside
            # real dispatch-department buckets isn't a meaningful
            # answer to "which departments are receiving correspondence
            # via dispatch" — excluded here, as a natural consequence of
            # this one dimension, not a silent override of any
            # `direction` filter the caller may have also supplied.
            conditions.append(Letter.dispatch_department_id.isnot(None))

        if group_by in GROUP_BY_DATE_TRUNC:
            group_expression = func.date_trunc(group_by, Letter.received_at)
        else:
            group_expression = GROUP_BY_COLUMNS[group_by]

        count_expression = func.count()
        stmt = select(group_expression.label("bucket_key"), count_expression.label("bucket_count"))
        if needs_join:
            stmt = stmt.outerjoin(Classification, Letter.classification_id == Classification.id)
        stmt = stmt.where(*conditions).group_by(group_expression)

        if group_by in GROUP_BY_DATE_TRUNC:
            # Chronological order for a time series — a trend chart
            # needs points in date order, not ranked by frequency (a
            # deliberate departure from the frequency-ranked order
            # below, reassessed for this specific dimension).
            stmt = stmt.order_by(group_expression.asc())
        else:
            # Ranked by frequency for a bar/pie-style breakdown; ties
            # broken by key for determinism, the same "always add a
            # deterministic secondary sort" discipline `list_letters`
            # already applies via its own `Letter.id.asc()`.
            stmt = stmt.order_by(count_expression.desc(), group_expression.asc())

        return list(self.session.execute(stmt).all())

    def create(
        self,
        *,
        reference_number: str,
        recipient_department_id: uuid.UUID,
        source_name: str,
        source_department_id: Optional[uuid.UUID],
        source_location: Optional[str],
        sender_name: str,
        sender_designation: str,
        designation_id: Optional[uuid.UUID],
        sender_department: str,
        sender_address: Optional[str],
        subject: Optional[str],
        reason: Optional[str],
        category_id: Optional[uuid.UUID],
        classification_id: Optional[uuid.UUID],
        received_at,
        recorded_by: uuid.UUID,
        text_content: Optional[str],
        direction: Optional[LetterDirection] = None,
        dispatch_department_id: Optional[uuid.UUID] = None,
        diary_number: Optional[str] = None,
        recorded_from_letter_id: Optional[uuid.UUID] = None,
        continuation_of_letter_id: Optional[uuid.UUID] = None,
    ) -> Letter:
        letter = Letter(
            reference_number=reference_number,
            recipient_department_id=recipient_department_id,
            source_name=source_name,
            source_department_id=source_department_id,
            source_location=source_location,
            sender_name=sender_name,
            sender_designation=sender_designation,
            designation_id=designation_id,
            sender_department=sender_department,
            sender_address=sender_address,
            subject=subject,
            reason=reason,
            category_id=category_id,
            classification_id=classification_id,
            received_at=received_at,
            recorded_by=recorded_by,
            text_content=text_content,
            diary_number=diary_number,
            dispatch_department_id=dispatch_department_id,
            recorded_from_letter_id=recorded_from_letter_id,
            continuation_of_letter_id=continuation_of_letter_id,
        )
        # `direction` keeps the model's own default (INCOMING) when the
        # caller doesn't pass one — matches the model's `server_default`/
        # `default=` for any caller that predates Phase 6A.
        if direction is not None:
            letter.direction = direction
        self.session.add(letter)
        return letter

    def find_by_recorded_from_letter_id(self, outgoing_letter_id: uuid.UUID) -> Optional[Letter]:
        """The Phase 6A idempotency lookup: has this OUTGOING letter
        already been recorded into an INCOMING one? See
        app/services/letter_service.py:record_incoming_correspondence."""
        stmt = select(Letter).where(Letter.recorded_from_letter_id == outgoing_letter_id)
        return self.session.execute(stmt).scalar_one_or_none()

    def update(self, letter: Letter, **fields) -> None:
        """Plain attribute-set helper, same convention as
        DepartmentRepository.update — only `None`-valued keys are skipped,
        so a caller passes exactly the fields it wants changed (already
        filtered by the service layer, which knows the "None means
        unchanged" contract from the request schema)."""
        for key, value in fields.items():
            if value is not None:
                setattr(letter, key, value)

    def update_status(self, letter: Letter, status: LetterStatus) -> None:
        letter.status = status
