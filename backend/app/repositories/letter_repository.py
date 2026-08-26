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
"""

import uuid
from datetime import datetime
from typing import List, Optional, Tuple

from sqlalchemy import ColumnElement, func, select
from sqlalchemy.orm import Session, joinedload

from app.models.classification import Classification
from app.models.enums import LetterStatus
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

    def list_letters(
        self,
        *,
        recipient_department_id: Optional[uuid.UUID] = None,
        status_filter: Optional[LetterStatus] = None,
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
        stmt = select(Letter)

        if visibility_filter is not None:
            # Only joined when actually needed (USER caller) — an
            # ADMIN/SYSTEM_ADMIN query pays no extra join cost.
            stmt = stmt.outerjoin(
                Classification, Letter.classification_id == Classification.id
            )
            stmt = stmt.where(visibility_filter)

        if recipient_department_id is not None:
            stmt = stmt.where(Letter.recipient_department_id == recipient_department_id)
        if status_filter is not None:
            stmt = stmt.where(Letter.status == status_filter)
        if category_id is not None:
            stmt = stmt.where(Letter.category_id == category_id)
        if classification_id is not None:
            stmt = stmt.where(Letter.classification_id == classification_id)

        if reference_number is not None:
            stmt = stmt.where(
                Letter.reference_number.ilike(f"%{_ilike_escape(reference_number)}%")
            )
        if subject is not None:
            stmt = stmt.where(Letter.subject.ilike(f"%{_ilike_escape(subject)}%"))
        if sender_name is not None:
            stmt = stmt.where(Letter.sender_name.ilike(f"%{_ilike_escape(sender_name)}%"))
        if sender_designation is not None:
            stmt = stmt.where(
                Letter.sender_designation.ilike(f"%{_ilike_escape(sender_designation)}%")
            )
        if sender_department is not None:
            stmt = stmt.where(
                Letter.sender_department.ilike(f"%{_ilike_escape(sender_department)}%")
            )
        if source_name is not None:
            stmt = stmt.where(Letter.source_name.ilike(f"%{_ilike_escape(source_name)}%"))
        if source_location is not None:
            stmt = stmt.where(
                Letter.source_location.ilike(f"%{_ilike_escape(source_location)}%")
            )

        if received_from is not None:
            stmt = stmt.where(Letter.received_at >= received_from)
        if received_to is not None:
            stmt = stmt.where(Letter.received_at <= received_to)

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
        )
        self.session.add(letter)
        return letter

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
