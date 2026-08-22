"""Request/response contracts for Category management.

Mirrors app/schemas/department.py exactly — `extra="forbid"`, no
server-controlled field (`id`/`status`/timestamps) accepted from a
client, status changes go through dedicated activate/deactivate
endpoints only.
"""

import uuid
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models.enums import ActiveStatus

_MAX_NAME_LENGTH = 255


def _normalize_name(value: str) -> str:
    value = value.strip()
    if not value:
        raise ValueError("name must not be blank.")
    return value


class CategoryCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=_MAX_NAME_LENGTH)
    description: Optional[str] = Field(default=None)

    @field_validator("name")
    @classmethod
    def _validate_name(cls, value: str) -> str:
        return _normalize_name(value)


class CategoryUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: Optional[str] = Field(default=None, max_length=_MAX_NAME_LENGTH)
    description: Optional[str] = Field(default=None)

    @field_validator("name")
    @classmethod
    def _validate_name(cls, value: Optional[str]) -> Optional[str]:
        return None if value is None else _normalize_name(value)

    @model_validator(mode="after")
    def _require_at_least_one_field(self) -> "CategoryUpdate":
        if self.name is None and self.description is None:
            raise ValueError("At least one of name or description must be supplied.")
        return self


class CategoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    description: Optional[str]
    status: ActiveStatus
    created_at: datetime
    updated_at: datetime


class CategoryListResponse(BaseModel):
    items: List[CategoryResponse]
    total: int
