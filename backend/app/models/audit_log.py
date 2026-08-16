"""AuditLog — an immutable record of who changed what, when, and to what value.

Required for a government correspondence system's accountability trail
(Section 11). No row in this table is ever written by this phase — automatic
audit-log generation (e.g. via SQLAlchemy events or a service-layer hook) is
future work; only the table exists so later phases have a stable place to
write to.

`user_id` is nullable for system-generated actions (e.g. a scheduled job)
that have no human actor, not because Users can be deleted. It uses
`ON DELETE SET NULL` purely as defense in depth, since this schema does not
otherwise support physically deleting a User.

`old_values`/`new_values` use JSONB (not JSON) because PostgreSQL indexes and
queries JSONB efficiently and stores it in a more compact binary form; this
schema has no requirement to preserve the exact original key ordering/
whitespace that only plain JSON would retain.

`entity_id` is a bare UUID with no foreign key: `entity_type` names which
table it points into, and that table varies per row, so a single FK
constraint cannot target it.
"""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DateTime, ForeignKey, Index, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.models.mixins import UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.user import User


class AuditLog(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "audit_logs"

    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    entity_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)
    old_values: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    new_values: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )

    user: Mapped[Optional["User"]] = relationship(
        back_populates="audit_logs", foreign_keys=[user_id]
    )

    __table_args__ = (
        # Supports "audit trail for this specific record" — the other
        # frequent query shape besides "everything by this user" or
        # "everything in this time range", both already covered by the
        # single-column indexes above.
        Index("ix_audit_logs_entity_type_entity_id", "entity_type", "entity_id"),
    )

    def __repr__(self) -> str:  # pragma: no cover - debug convenience only
        return f"<AuditLog id={self.id} action={self.action!r} entity_type={self.entity_type!r}>"
