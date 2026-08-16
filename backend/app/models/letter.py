"""Letter — the central business entity: one piece of incoming correspondence.

Department isolation: `department_id` is required and is the field every
future query/service must filter on. This model does not (and cannot) stop a
caller from passing an arbitrary `department_id` — that enforcement is a
service-layer concern, described in docs/architecture/overview.md, where the
value will be derived from the authenticated user's own department rather
than accepted as client input.

Deliberately excluded from this phase: an official reference/letter number.
Its existence and format are unconfirmed by S&IT (Section 8) — adding one now
would mean guessing a government numbering convention, so it is left out
entirely rather than stubbed with a placeholder format.

Assumptions made where the brief did not specify nullability (documented in
docs/database/schema.md as pending S&IT confirmation, not treated as final):
  * `reason` — nullable, same reasoning as `subject`: useful, but its exact
    requirement-ness is unconfirmed.
  * `received_at` — NOT NULL: a letter record only exists because a physical
    letter was received, so this timestamp is treated as always known at
    creation time (unlike `subject`/`reason`, which describe content that may
    not yet have been reviewed).

category_id/classification_id are nullable because the categorization
workflow itself (who assigns it, at intake or later) is still being defined.
"""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import DateTime, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.models.enums import LetterStatus, letter_status_enum
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.category import Category
    from app.models.classification import Classification
    from app.models.department import Department
    from app.models.letter_document import LetterDocument
    from app.models.notification import Notification
    from app.models.user import User


class Letter(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "letters"

    department_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("departments.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    # Sender is not assumed to always be a government department (Section 8) —
    # kept as free text rather than a foreign key until S&IT confirms the set
    # of possible sender types.
    received_from: Mapped[str] = mapped_column(String(500), nullable=False)
    subject: Mapped[Optional[str]] = mapped_column(String(500), nullable=True, index=True)
    reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    category_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("categories.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    classification_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("classifications.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    recorded_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    text_content: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[LetterStatus] = mapped_column(
        letter_status_enum, nullable=False, default=LetterStatus.ACTIVE, index=True
    )

    department: Mapped["Department"] = relationship(back_populates="letters")
    category: Mapped[Optional["Category"]] = relationship(back_populates="letters")
    classification: Mapped[Optional["Classification"]] = relationship(
        back_populates="letters"
    )
    recorded_by_user: Mapped["User"] = relationship(
        back_populates="letters_recorded", foreign_keys=[recorded_by]
    )
    # Letters are never physically deleted in this system (no delete endpoint
    # is planned; V1 archival is a status change — see LetterStatus). The
    # cascade below only matters if a row is ever removed outside normal
    # application flow (e.g. manual cleanup); it deletes the *metadata* rows
    # only, never the files on disk (Section 9).
    #
    # cascade="all, delete-orphan": each LetterDocument is a true owned
    # child with no life of its own (see LetterDocument's docstring), so the
    # ORM actively deleting each one on parent delete — or when removed from
    # this collection — is the correct, intended behavior here. (SQLAlchemy
    # does not allow combining this with passive_deletes="all"; that option
    # is for the RESTRICT/SET NULL relationships elsewhere in this schema,
    # not this one — see docs/database/schema.md, "ORM deletion behavior".)
    documents: Mapped[List["LetterDocument"]] = relationship(
        back_populates="letter", cascade="all, delete-orphan"
    )
    # No ORM-level delete-orphan cascade here (unlike `documents`): removing
    # a notification from this collection should not delete it. But on
    # parent delete, passive_deletes="all" still defers to the database's
    # own ON DELETE CASCADE (notifications.letter_id) — without it, the ORM's
    # default behavior is to UPDATE notifications SET letter_id = NULL
    # instead, which doesn't match what a direct SQL DELETE against the same
    # row already does.
    notifications: Mapped[List["Notification"]] = relationship(
        back_populates="letter", passive_deletes="all"
    )

    __table_args__ = (
        # Supports the primary access pattern once department isolation is
        # enforced at the service layer: "this department's letters, ordered
        # by receipt date".
        Index("ix_letters_department_received_at", "department_id", "received_at"),
    )

    def __repr__(self) -> str:  # pragma: no cover - debug convenience only
        return f"<Letter id={self.id} department_id={self.department_id} status={self.status}>"
