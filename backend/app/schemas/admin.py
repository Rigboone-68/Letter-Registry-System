"""Request/response contracts for Admin management.

`AdminAuthorizationCreate`/`AdminDepartmentUpdate` have no `role`,
`status`, `authorization status`, `created_at`, `used_at`, or
`authorized_by` field — not merely ignored if sent. Both additionally set
`model_config = ConfigDict(extra="forbid")`, so a request that tries to
inject any of them is rejected outright with `422`, the same pattern
`SignupRequest` (Phase 3A) and `DepartmentCreate`/`DepartmentUpdate`
(Phase 3B.2) already established. `authorized_by` in particular is always
the calling SYSTEM_ADMIN's own id (from `current_user`, via
`app/api/deps.py:require_system_admin`) — never client-supplied.

`AdminResponse` never exposes `password_hash` — the field doesn't exist on
this model, the same structural guarantee `UserPublic`
(app/schemas/auth.py) already relies on.
"""

import uuid
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, EmailStr

from app.models.enums import AuthorizationStatus, UserRole, UserStatus


class AdminAuthorizationCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: EmailStr
    department_id: uuid.UUID


class AdminAuthorizationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    department_id: uuid.UUID
    status: AuthorizationStatus
    created_at: datetime
    expires_at: Optional[datetime]


class AdminResponse(BaseModel):
    """The only shape an Admin's `User` row is ever exposed as — no
    `password_hash` field exists here, see module docstring."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    full_name: str
    email: str
    role: UserRole
    department_id: Optional[uuid.UUID]
    status: UserStatus
    created_at: datetime
    updated_at: datetime


class AdminListResponse(BaseModel):
    """A thin envelope, not a bare list — same reasoning as
    app/schemas/department.py:DepartmentListResponse: adding pagination
    later only ever needs new fields here, never a shape change. No
    pagination is implemented in this phase."""

    items: List[AdminResponse]
    total: int


class AdminDepartmentUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    department_id: uuid.UUID
