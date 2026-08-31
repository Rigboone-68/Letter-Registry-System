"""Request/response contracts for the Letter registry.

`LetterCreate` has no `recipient_department_id`, `recorded_by`, or
`status` field — not merely ignored if sent; both, along with `extra=
"forbid"`, mean a client cannot inject either. Both are always derived
server-side from the authenticated caller in
`app/services/letter_service.py:create_letter`.

Required-at-creation fields (Phase 4B finalized decisions,
docs/architecture/letter-registry.md §2): `reference_number`, `subject`,
`sender_name`, `sender_designation`, `sender_department`, `source_name`,
`received_at`. `sender_address` is deliberately optional — "do not make
Sender Address artificially mandatory" (explicit instruction).
`source_department_id`/`source_location`/`category_id`/
`classification_id`/`reason`/`text_content` are all optional; neither
`category_id` nor `classification_id` is required by the finalized
decisions (only *which* categories are valid, and classification's
*behavior*, were confirmed — not that every letter must have one
assigned).

`subject` is required here even though the underlying database column
remains nullable (unchanged from Phase 2/4A) — this phase's finalized
validation requirements confirm it must be supplied through the API, but
nothing asked for a database migration narrowing the column itself; see
docs/architecture/letter-registry.md §3.

No format is imposed on `reference_number` beyond "a non-empty string" —
letters, numbers, and special characters are all permitted, per explicit
instruction not to invent a format the business didn't specify.
"""

import enum
import uuid
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.enums import LetterDirection, LetterStatus


class LetterSortField(str, enum.Enum):
    """The explicit sort-field whitelist (Phase 4C) — a client value
    outside this set is rejected by FastAPI/Pydantic with `422` before
    ever reaching the service/repository layer. Never accept a raw
    client string for `ORDER BY`; see
    app/repositories/letter_repository.py:SORTABLE_COLUMNS, which this
    enum's values are kept in sync with by hand (four fields, not
    expected to change often enough to justify a shared source)."""

    RECEIVED_AT = "received_at"
    CREATED_AT = "created_at"
    REFERENCE_NUMBER = "reference_number"
    SUBJECT = "subject"


class SortOrder(str, enum.Enum):
    ASC = "asc"
    DESC = "desc"


class LetterGroupByField(str, enum.Enum):
    """The explicit `group_by` whitelist for `GET /letters/aggregate`
    (Phase 6C, docs/architecture/dashboard-analytics-api.md's own
    implementation record) — the same "reject anything outside a fixed
    set with 422 before the service/repository layer ever runs"
    discipline `LetterSortField` already established. Kept in sync by
    hand with `app/repositories/letter_repository.py:GROUP_BY_COLUMNS`/
    `GROUP_BY_DATE_TRUNC`, the same convention `LetterSortField` already
    uses for `SORTABLE_COLUMNS`.

    `DEPARTMENT` groups by the *owning* department (`recipient_department_id`)
    for either correspondence direction — Phase 6A's own reassessment of
    what this dimension means now that a department can both receive and
    dispatch letters. `DISPATCH_DEPARTMENT` (new this phase) groups by
    `dispatch_department_id`, the destination of an `OUTGOING` letter —
    answers "which departments are receiving correspondence via
    dispatch," a genuinely different question from `DEPARTMENT` narrowed
    to `direction=INCOMING` (which answers "which departments have
    recorded incoming correspondence in their own registry," regardless
    of whether it arrived via the new dispatch workflow or the
    traditional external-sender path). `DIRECTION` answers "how much
    correspondence is Incoming vs. Outgoing" directly.
    """

    STATUS = "status"
    CATEGORY = "category"
    CLASSIFICATION = "classification"
    DEPARTMENT = "department"
    DISPATCH_DEPARTMENT = "dispatch_department"
    DIRECTION = "direction"
    DAY = "day"
    WEEK = "week"
    MONTH = "month"


class LetterAggregateBucket(BaseModel):
    """One `GROUP BY` result row. `key` is the raw grouping value — a
    bare id (category/classification/department/dispatch_department), an
    enum string (status/direction), or an ISO 8601 timestamp string
    (day/week/month) — never a resolved display name (resolving an id to
    a name remains the frontend's own existing job, matching
    `docs/architecture/dashboard-analytics-api.md` §13). `None` when the
    underlying column is legitimately unset for that row (e.g. a Letter
    with no `category_id`) — a real, meaningful bucket, not an error."""

    key: Optional[str] = None
    count: int


class LetterAggregateResponse(BaseModel):
    """Response for `GET /letters/aggregate`. `total` is the sum of
    every bucket's `count` — by construction, since every matching row
    falls into exactly one bucket, this always equals what `GET
    /letters`'s own `total` would return for the identical filter set,
    without a second `COUNT` query. Never paginated — see
    `app/repositories/letter_repository.py:aggregate_letters`'s own
    docstring for why."""

    group_by: LetterGroupByField
    total: int
    buckets: List[LetterAggregateBucket]


def _require_non_blank(value: str) -> str:
    value = value.strip()
    if not value:
        raise ValueError("must not be blank.")
    return value


class LetterCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reference_number: str = Field(min_length=1, max_length=255)
    subject: str = Field(min_length=1, max_length=500)

    source_name: str = Field(min_length=1, max_length=500)
    source_department_id: Optional[uuid.UUID] = None
    source_location: Optional[str] = Field(default=None, max_length=255)

    sender_name: str = Field(min_length=1, max_length=255)
    # Remains required text — the historical snapshot, unchanged since
    # Phase 4B. `designation_id` (Phase 5H) is a new, optional structured
    # reference; when supplied, the service overrides whatever value is
    # sent here with the referenced Designation's own current name — the
    # master-data selection is authoritative, never the client's text.
    # Omitting `designation_id` (old API clients, or a source that isn't
    # backed by master data) preserves this field's original, unchanged
    # behavior exactly. See docs/architecture/source-designation.md §9.
    sender_designation: str = Field(min_length=1, max_length=255)
    designation_id: Optional[uuid.UUID] = None
    sender_department: str = Field(min_length=1, max_length=255)
    sender_address: Optional[str] = None

    reason: Optional[str] = None
    category_id: Optional[uuid.UUID] = None
    classification_id: Optional[uuid.UUID] = None
    received_at: datetime
    text_content: Optional[str] = None

    # Phase 6A (docs/architecture/correspondence.md §9). `direction`
    # defaults to `INCOMING` — an old client that has never heard of this
    # field gets exactly the same behavior it always had.
    # `dispatch_department_id` is required (service-validated, not a
    # Pydantic-level requirement, since it depends on `direction`) only
    # when `direction == OUTGOING`. `continuation_of_letter_id` is valid
    # for either direction — a response is typically OUTGOING, but
    # nothing here forces that; the service verifies the caller can
    # access the referenced letter, exactly like any other reference
    # field.
    direction: LetterDirection = LetterDirection.INCOMING
    dispatch_department_id: Optional[uuid.UUID] = None
    continuation_of_letter_id: Optional[uuid.UUID] = None

    @field_validator(
        "reference_number", "subject", "source_name", "sender_name",
        "sender_designation", "sender_department",
    )
    @classmethod
    def _validate_non_blank(cls, value: str) -> str:
        return _require_non_blank(value)


# `reason` is kept (not requested by the finalized field list, not
# conflicting with it either — see app/models/letter.py) and exposed on
# both Create and Update for consistency; a field settable only after the
# fact would be an odd asymmetry.


class LetterUpdate(BaseModel):
    """Every field is optional; `None` means "leave unchanged" (the same
    convention `DepartmentUpdate` established) — a nullable field
    (`source_location`/`sender_address`/`reason`/`category_id`/
    `classification_id`) cannot currently be explicitly cleared back to
    `null` through this endpoint, the same known limitation Department's
    `code` already has."""

    model_config = ConfigDict(extra="forbid")

    reference_number: Optional[str] = Field(default=None, max_length=255)
    subject: Optional[str] = Field(default=None, max_length=500)

    source_name: Optional[str] = Field(default=None, max_length=500)
    source_department_id: Optional[uuid.UUID] = None
    source_location: Optional[str] = Field(default=None, max_length=255)

    sender_name: Optional[str] = Field(default=None, max_length=255)
    # `None` means "leave unchanged," the same convention every other
    # field on this schema already uses — including for an already-
    # assigned, now-INACTIVE designation: omitting this field never
    # re-validates or disturbs it (docs/architecture/
    # source-designation.md §9). Supplying a genuinely different value
    # requires the newly selected Designation to be ACTIVE, and
    # overrides `sender_designation` with its current name.
    sender_designation: Optional[str] = Field(default=None, max_length=255)
    designation_id: Optional[uuid.UUID] = None
    sender_department: Optional[str] = Field(default=None, max_length=255)
    sender_address: Optional[str] = None

    reason: Optional[str] = None
    category_id: Optional[uuid.UUID] = None
    classification_id: Optional[uuid.UUID] = None
    received_at: Optional[datetime] = None
    text_content: Optional[str] = None

    @field_validator(
        "reference_number", "subject", "source_name", "sender_name",
        "sender_designation", "sender_department",
    )
    @classmethod
    def _validate_non_blank(cls, value: Optional[str]) -> Optional[str]:
        return None if value is None else _require_non_blank(value)


class LetterResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    reference_number: str
    recipient_department_id: uuid.UUID

    source_name: str
    source_department_id: Optional[uuid.UUID]
    source_location: Optional[str]

    sender_name: str
    sender_designation: str
    designation_id: Optional[uuid.UUID]
    sender_department: str
    sender_address: Optional[str]

    subject: Optional[str]
    reason: Optional[str]
    category_id: Optional[uuid.UUID]
    classification_id: Optional[uuid.UUID]
    received_at: datetime
    recorded_by: uuid.UUID
    text_content: Optional[str]
    status: LetterStatus
    created_at: datetime
    updated_at: datetime

    # Phase 6A. `dispatch_department_id`/`recorded_from_letter_id`/
    # `continuation_of_letter_id` are plain ids, resolved into a Letter/
    # Department by the frontend through the existing, already-authorized
    # `GET /letters/{id}` and `GET /departments` — this schema never
    # exposes a related row's own sensitive fields (mirrors how
    # `source_department_id` already works).
    direction: LetterDirection
    dispatch_department_id: Optional[uuid.UUID]
    diary_number: Optional[str]
    recorded_from_letter_id: Optional[uuid.UUID]
    continuation_of_letter_id: Optional[uuid.UUID]


class LetterListItem(BaseModel):
    """A lightweight registry-row shape for `GET /api/v1/letters`
    (Phase 4C) — every field except `text_content` and `reason`, which a
    tabular list view has no use for and which cost more to transfer per
    row at no benefit; `GET /api/v1/letters/{id}` keeps returning the
    full `LetterResponse` unchanged. See
    docs/architecture/registry-search.md §17/§9 (implemented, not just
    recommended, as of this phase)."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    reference_number: str
    recipient_department_id: uuid.UUID

    source_name: str
    source_department_id: Optional[uuid.UUID]
    source_location: Optional[str]

    sender_name: str
    sender_designation: str
    designation_id: Optional[uuid.UUID]
    sender_department: str
    sender_address: Optional[str]

    subject: Optional[str]
    category_id: Optional[uuid.UUID]
    classification_id: Optional[uuid.UUID]
    received_at: datetime
    recorded_by: uuid.UUID
    status: LetterStatus
    created_at: datetime
    updated_at: datetime

    # Phase 6A — the same three fields the registry row/table view needs
    # to show a direction badge and the Diary/Dispatch Number prominently;
    # `recorded_from_letter_id`/`continuation_of_letter_id` are left off
    # this lightweight shape (a detail-page concern), matching this
    # schema's existing `text_content`/`reason` exclusion.
    direction: LetterDirection
    dispatch_department_id: Optional[uuid.UUID]
    diary_number: Optional[str]


class LetterListResponse(BaseModel):
    """Extends the original `{"items": [...], "total": N}` envelope
    (unchanged field names, so existing consumers of `items`/`total`
    keep working) with pagination metadata (Phase 4C):
    `page`/`page_size` echo the effective request; `total_pages` is
    computed from `total`/`page_size`. `total` (and therefore
    `total_pages`) already reflects the caller's full authorization
    scope — department isolation and the classified-access boundary are
    both applied inside the query that produces it, never after — see
    app/repositories/letter_repository.py:list_letters."""

    items: List[LetterListItem]
    total: int
    page: int
    page_size: int
    total_pages: int
