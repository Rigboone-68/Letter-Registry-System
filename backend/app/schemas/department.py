"""Request/response contracts for department management.

`DepartmentCreate`/`DepartmentUpdate` have no `id`, `status`,
`created_at`, or `updated_at` field — not merely ignoring them if sent.
Both additionally set `model_config = ConfigDict(extra="forbid")`, so a
request that tries to inject any of them is rejected outright with `422`
before it ever reaches the service layer, the same pattern
`SignupRequest` (app/schemas/auth.py, Phase 3A) already established.
Status changes go through the dedicated activate/deactivate endpoints
instead — see app/api/v1/endpoints/departments.py.

`code` normalization is deliberately minimal: whitespace is trimmed and an
empty string becomes `None`, nothing else. No case transformation or
format validation is applied, because S&IT has not confirmed a
departmental coding convention (see docs/database/schema.md §7) — this
schema must not invent one.
"""

import uuid
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models.enums import ActiveStatus

_MAX_NAME_LENGTH = 255
_MAX_CODE_LENGTH = 50


def _normalize_name(value: str) -> str:
    value = value.strip()
    if not value:
        raise ValueError("name must not be blank.")
    return value


def _normalize_code(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    value = value.strip()
    return value or None


class DepartmentCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=_MAX_NAME_LENGTH)
    code: Optional[str] = Field(default=None, max_length=_MAX_CODE_LENGTH)

    @field_validator("name")
    @classmethod
    def _validate_name(cls, value: str) -> str:
        return _normalize_name(value)

    @field_validator("code")
    @classmethod
    def _validate_code(cls, value: Optional[str]) -> Optional[str]:
        return _normalize_code(value)


class DepartmentUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: Optional[str] = Field(default=None, max_length=_MAX_NAME_LENGTH)
    code: Optional[str] = Field(default=None, max_length=_MAX_CODE_LENGTH)

    @field_validator("name")
    @classmethod
    def _validate_name(cls, value: Optional[str]) -> Optional[str]:
        return None if value is None else _normalize_name(value)

    @field_validator("code")
    @classmethod
    def _validate_code(cls, value: Optional[str]) -> Optional[str]:
        return _normalize_code(value)

    @model_validator(mode="after")
    def _require_at_least_one_field(self) -> "DepartmentUpdate":
        if self.name is None and self.code is None:
            raise ValueError("At least one of name or code must be supplied.")
        return self


class DepartmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    code: Optional[str]
    status: ActiveStatus
    created_at: datetime
    updated_at: datetime


class DepartmentListResponse(BaseModel):
    """A thin envelope, not a bare list — adding pagination later (page/
    page_size/next_cursor) only ever needs new fields on this model, never
    a change to the response's fundamental shape. No pagination is
    implemented in this phase (brief §6)."""

    items: List[DepartmentResponse]
    total: int
