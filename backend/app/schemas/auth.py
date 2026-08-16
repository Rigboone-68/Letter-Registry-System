"""Request/response contracts for the authentication API.

SQLAlchemy models are never returned directly from an endpoint — `UserPublic`
is the one shape a User is ever exposed as, and it has no `password_hash`
field, so there is no way for that value to leak through this layer even by
accident (as opposed to, say, a field explicitly excluded at serialization
time, which a future edit could silently un-exclude).

`SignupRequest` has no `role`, `department_id`, or `status` field at all —
not merely ignoring them if sent. FastAPI/Pydantic reject unknown fields
in strict mode, but even without that, there is simply nothing in this
model for a client-supplied `role` to bind to; see
app/services/auth_service.py:AuthService.signup for where those values
actually come from.
"""

import uuid
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator

from app.core.security import validate_password_policy
from app.models.enums import UserRole, UserStatus


class SignupRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    full_name: str = Field(min_length=1, max_length=255)
    email: EmailStr
    password: str
    password_confirm: str

    @model_validator(mode="after")
    def _validate_password(self) -> "SignupRequest":
        # Raising ValueError inside a Pydantic validator is the documented
        # way to surface a 422 — see app/core/security.py for why this is
        # the one place the policy itself is defined.
        validate_password_policy(self.password)
        if self.password != self.password_confirm:
            raise ValueError("password and password_confirm do not match.")
        return self


class LoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: EmailStr
    password: str = Field(min_length=1)


class UserPublic(BaseModel):
    """The only shape a User is ever exposed as over the API. No
    `password_hash` field exists here — see module docstring."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    full_name: str
    email: str
    role: UserRole
    department_id: Optional[uuid.UUID]
    status: UserStatus


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserPublic
