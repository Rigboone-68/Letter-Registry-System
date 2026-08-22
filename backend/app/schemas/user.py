"""Request/response contracts for User management.

`UserAuthorizationCreate` has no `department_id` field — unlike
app/schemas/admin.py:AdminAuthorizationCreate, an Admin does not pick a
target department; it is always derived from the calling Admin's own
`department_id` (see app/services/user_service.py:authorize_user), so
there is nothing here for a client-supplied value to bind to. It also has
no `role`, `status`, `authorized_by`, `created_at`, or `used_at` field, and
sets `model_config = ConfigDict(extra="forbid")`, same pattern as every
other request schema in this codebase.

`UserResponse` never exposes `password_hash` — the field doesn't exist on
this model, same structural guarantee as `UserPublic`/`AdminResponse`.
"""

import uuid
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, EmailStr

from app.models.enums import AuthorizationStatus, UserRole, UserStatus


class UserAuthorizationCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: EmailStr


class UserAuthorizationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    department_id: uuid.UUID
    status: AuthorizationStatus
    created_at: datetime
    expires_at: Optional[datetime]


class UserAuthorizationListResponse(BaseModel):
    """A thin envelope, not a bare list — same reasoning as
    AdminListResponse/DepartmentListResponse. No pagination is implemented
    in this phase."""

    items: List[UserAuthorizationResponse]
    total: int


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    full_name: str
    email: str
    role: UserRole
    department_id: Optional[uuid.UUID]
    status: UserStatus
    created_at: datetime
    updated_at: datetime


class UserListResponse(BaseModel):
    items: List[UserResponse]
    total: int
