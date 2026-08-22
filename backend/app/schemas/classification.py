"""Request/response contracts for Classification management.

Mirrors app/schemas/category.py, plus `restricts_access` — the data-model
half of the classified-access authorization boundary
(docs/architecture/letter-registry.md §8). Defaults to `False` on create,
so a newly created classification has no access-control effect until a
System Admin explicitly opts it in.
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


class ClassificationCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=_MAX_NAME_LENGTH)
    description: Optional[str] = Field(default=None)
    restricts_access: bool = Field(default=False)

    @field_validator("name")
    @classmethod
    def _validate_name(cls, value: str) -> str:
        return _normalize_name(value)


class ClassificationUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: Optional[str] = Field(default=None, max_length=_MAX_NAME_LENGTH)
    description: Optional[str] = Field(default=None)
    restricts_access: Optional[bool] = Field(default=None)

    @field_validator("name")
    @classmethod
    def _validate_name(cls, value: Optional[str]) -> Optional[str]:
        return None if value is None else _normalize_name(value)

    @model_validator(mode="after")
    def _require_at_least_one_field(self) -> "ClassificationUpdate":
        if self.name is None and self.description is None and self.restricts_access is None:
            raise ValueError(
                "At least one of name, description, or restricts_access must be supplied."
            )
        return self


class ClassificationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    description: Optional[str]
    restricts_access: bool
    status: ActiveStatus
    created_at: datetime
    updated_at: datetime


class ClassificationListResponse(BaseModel):
    items: List[ClassificationResponse]
    total: int
