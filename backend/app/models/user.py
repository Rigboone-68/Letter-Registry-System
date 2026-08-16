"""User — a person with an LRS account.

Role/department pairing: ADMIN and USER must belong to a department;
SYSTEM_ADMIN must not (it has system-wide authority, not a department's).
That invariant is encoded twice on purpose:

  1. `ck_users_role_department_pairing` — a CHECK constraint, so the database
     itself refuses a row that violates it. The condition is a plain
     equality/IN check against enum labels, which is not PostgreSQL-exotic
     or hard to maintain, so it earns its place here.
  2. It will ALSO be enforced at the service layer in a later phase (e.g. on
     role change, or department transfer) — the constraint only protects
     column values at write time, not multi-step workflows like "promote
     this user to SYSTEM_ADMIN and clear their department", which needs
     transactional business logic a CHECK constraint cannot express.

The constraint's SQL text is built from `UserRole.SYSTEM_ADMIN.value` /
`.ADMIN.value` / `.USER.value` rather than typed-out literals, so the model
and the enum can't silently drift apart. This does NOT extend to the
Alembic migration that created the equivalent constraint in the database —
migrations are frozen, self-contained snapshots (see the migration file's
own docstring), so that copy is, correctly, a literal string. If `UserRole`
ever gains, loses, or renames a member, both this constraint's condition AND
a new corrective migration must be updated together — there is no mechanism
that makes one edit do both, and there shouldn't be, since a new role may
not simply join the ADMIN/USER bucket. `tests/integration/test_models.py`
exercises all six role/has-department combinations, so a role change that
isn't reflected here will show up as a test failure, not a silent gap.

Password hashing is out of scope for this phase — `password_hash` only
stores whatever the future auth module produces; nothing here computes it.

Users are never physically deleted (`status` moves to DEACTIVATED instead),
because Letters, LetterDocuments, Notifications, and AuditLog rows must keep
pointing at the real user who acted, indefinitely.

`passive_deletes` on the collections below defers deletion handling to the
database's own FK actions (`RESTRICT` for most, `SET NULL` for `audit_logs`)
instead of the ORM's default of loading each collection and updating child
foreign keys itself — see docs/database/schema.md, "ORM deletion behavior".
"""

import uuid
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import CheckConstraint, ForeignKey, Index, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.models.enums import UserRole, UserStatus, user_role_enum, user_status_enum
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.audit_log import AuditLog
    from app.models.department import Department
    from app.models.letter import Letter
    from app.models.letter_document import LetterDocument
    from app.models.notification import Notification
    from app.models.user_authorization import UserAuthorization


class User(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "users"

    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    # No plain unique index on `email` itself — uniqueness is enforced by the
    # case-insensitive functional index below, which is the single source of
    # truth for "is this email already registered".
    email: Mapped[str] = mapped_column(String(320), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(user_role_enum, nullable=False, index=True)
    department_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("departments.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    status: Mapped[UserStatus] = mapped_column(
        user_status_enum,
        nullable=False,
        default=UserStatus.PENDING_APPROVAL,
        index=True,
    )

    department: Mapped[Optional["Department"]] = relationship(back_populates="users")
    authorizations_created: Mapped[List["UserAuthorization"]] = relationship(
        back_populates="authorized_by_user",
        foreign_keys="UserAuthorization.authorized_by",
        passive_deletes="all",
    )
    letters_recorded: Mapped[List["Letter"]] = relationship(
        back_populates="recorded_by_user",
        foreign_keys="Letter.recorded_by",
        passive_deletes="all",
    )
    documents_uploaded: Mapped[List["LetterDocument"]] = relationship(
        back_populates="uploaded_by_user",
        foreign_keys="LetterDocument.uploaded_by",
        passive_deletes="all",
    )
    notifications: Mapped[List["Notification"]] = relationship(
        back_populates="recipient",
        foreign_keys="Notification.recipient_user_id",
        passive_deletes="all",
    )
    audit_logs: Mapped[List["AuditLog"]] = relationship(
        back_populates="user",
        foreign_keys="AuditLog.user_id",
        passive_deletes="all",
    )

    __table_args__ = (
        Index("uq_users_email_lower", func.lower(email), unique=True),
        CheckConstraint(
            f"(role = '{UserRole.SYSTEM_ADMIN.value}' AND department_id IS NULL) OR "
            f"(role IN ('{UserRole.ADMIN.value}', '{UserRole.USER.value}') "
            "AND department_id IS NOT NULL)",
            name="ck_users_role_department_pairing",
        ),
    )

    def __repr__(self) -> str:  # pragma: no cover - debug convenience only
        return f"<User id={self.id} email={self.email!r} role={self.role}>"
