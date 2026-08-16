"""Notification — an in-system notification for a User, generated when a
Letter-related event occurs (V1: letter registration; see Section 10).

Only the schema is defined here. No notification is ever created by this
phase — that requires the letter-registration workflow (a later phase) to
call into a service that writes these rows. No delivery mechanism (email,
push, WebSocket) is implemented or assumed.

`letter_id` is nullable: today's only known use case (a letter was
registered) always has one, but leaving it optional avoids forcing a schema
change the first time a non-letter notification type is needed.
"""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String, Text, false, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.models.mixins import UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.letter import Letter
    from app.models.user import User


class Notification(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "notifications"

    recipient_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    # CASCADE, same reasoning as LetterDocument.letter_id: a notification
    # about a letter has no independent meaning once that letter is gone, and
    # letters are never deleted in normal operation.
    letter_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("letters.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    notification_type: Mapped[str] = mapped_column(String(100), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    # server_default (not just the Python-side default=) so a row inserted
    # outside the ORM — a raw-SQL script, a future admin tool — still gets a
    # safe value instead of failing NOT NULL.
    is_read: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=false()
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    read_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    recipient: Mapped["User"] = relationship(
        back_populates="notifications", foreign_keys=[recipient_user_id]
    )
    letter: Mapped[Optional["Letter"]] = relationship(back_populates="notifications")

    __table_args__ = (
        # Supports the primary future query: "this user's unread notifications".
        Index("ix_notifications_recipient_is_read", "recipient_user_id", "is_read"),
    )

    def __repr__(self) -> str:  # pragma: no cover - debug convenience only
        return f"<Notification id={self.id} recipient_user_id={self.recipient_user_id} is_read={self.is_read}>"
