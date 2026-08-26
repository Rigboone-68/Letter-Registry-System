"""Request/response contracts for Designation management (Phase 5H).

Mirrors app/schemas/category.py exactly — `extra="forbid"`, no
server-controlled field (`id`/`status`/timestamps) accepted from a
client, status changes go through dedicated activate/deactivate
endpoints only. No `description` field — the approved design
(docs/architecture/source-designation.md §7) deliberately keeps this
resource smaller than Category/Classification.
"""

import uuid
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.enums import ActiveStatus

_MAX_NAME_LENGTH = 255


def _normalize_name(value: str) -> str:
    value = value.strip()
    if not value:
        raise ValueError("name must not be blank.")
    return value


class DesignationCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=_MAX_NAME_LENGTH)

    @field_validator("name")
    @classmethod
    def _validate_name(cls, value: str) -> str:
        return _normalize_name(value)


class DesignationUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=_MAX_NAME_LENGTH)

    @field_validator("name")
    @classmethod
    def _validate_name(cls, value: str) -> str:
        return _normalize_name(value)


class DesignationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    status: ActiveStatus
    created_at: datetime
    updated_at: datetime


class DesignationListResponse(BaseModel):
    items: List[DesignationResponse]
    total: int
