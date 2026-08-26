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

from app.models.enums import LetterStatus


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
