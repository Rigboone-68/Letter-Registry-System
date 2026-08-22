"""UserAuthorization — a pre-approved email allowed to sign up.

Deliberately a separate table from `User`, not a flag on it: a
UserAuthorization can exist (and be REVOKED) before anyone ever signs up
against it, and its lifecycle (ACTIVE → USED/REVOKED) belongs to the admin
who granted access, not to an account that may never be created. Collapsing
the two into one table would force `User` rows to exist for people who never
completed signup, which breaks "Users must not be able to access another
department's records" reasoning built on `User` always meaning a real
account holder.

No invitation token or email delivery exists yet (Section 5) — this table
only records that signup *may* happen for this email/department pair.

The requirement that `authorized_by` must have ADMIN role is a workflow rule
about *who is allowed to call* "authorize this email", not a fact about the
column's value in isolation — it belongs at the service layer once the
authorization API exists, not as a CHECK constraint here.

`purpose` (Phase 3B.3) says what role the eventual signup produces —
`USER` or `ADMIN`. Extending this table with an explicit column, rather
than introducing a parallel `AdminAuthorization` table, was the brief's
own preferred approach and remains a clean one: every other column here
(department, expiry, race-safe consumption) means exactly the same thing
regardless of purpose, so duplicating the whole table would only have
duplicated that machinery for no benefit. `AuthService.signup`
(`app/services/auth_service.py`) derives the created `User`'s `role`
*from this field* on whichever authorization it finds — never the other
way around, and never from anything client-supplied — which is what
makes "a USER authorization cannot produce an ADMIN, and vice versa"
true by construction rather than by a separate check.
"""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DateTime, ForeignKey, Index, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.models.enums import (
    AuthorizationPurpose,
    AuthorizationStatus,
    authorization_purpose_enum,
    authorization_status_enum,
)
from app.models.mixins import UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.department import Department
    from app.models.user import User


class UserAuthorization(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "user_authorizations"

    # Not unique: the same email may be authorized, used, revoked, and
    # re-authorized over time. Preventing more than one *ACTIVE* authorization
    # per email at once is a service-layer rule, not a schema constraint.
    email: Mapped[str] = mapped_column(String(320), nullable=False)
    department_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("departments.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    authorized_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    purpose: Mapped[AuthorizationPurpose] = mapped_column(
        authorization_purpose_enum,
        nullable=False,
        default=AuthorizationPurpose.USER,
        index=True,
    )
    status: Mapped[AuthorizationStatus] = mapped_column(
        authorization_status_enum,
        nullable=False,
        default=AuthorizationStatus.ACTIVE,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    expires_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    department: Mapped["Department"] = relationship(back_populates="user_authorizations")
    authorized_by_user: Mapped["User"] = relationship(
        back_populates="authorizations_created", foreign_keys=[authorized_by]
    )

    __table_args__ = (
        Index("ix_user_authorizations_email_lower", func.lower(email)),
    )

    def __repr__(self) -> str:  # pragma: no cover - debug convenience only
        return f"<UserAuthorization id={self.id} email={self.email!r} status={self.status}>"
