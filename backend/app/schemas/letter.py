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

import uuid
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.enums import LetterStatus


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
    sender_designation: str = Field(min_length=1, max_length=255)
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
    sender_designation: Optional[str] = Field(default=None, max_length=255)
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


class LetterListResponse(BaseModel):
    items: List[LetterResponse]
    total: int
