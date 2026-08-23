"""Data access for `Notification` rows — the only code that queries
`Notification`.

Every read/write method here that isn't `create` is scoped by
`recipient_user_id` — a notification belongs to exactly one recipient
(docs/architecture/audit-notifications.md §17), so recipient isolation
lives here, once, rather than being re-checked ad hoc at each call site.
"""

import uuid
from datetime import datetime, timezone
from typing import List, Optional, Tuple

from sqlalchemy import func, select
from sqlalchemy import update as sa_update
from sqlalchemy.orm import Session

from app.models.notification import Notification


class NotificationRepository:
    def __init__(self, session: Session):
        self.session = session

    def create(
        self,
        *,
        recipient_user_id: uuid.UUID,
        letter_id: Optional[uuid.UUID],
        notification_type: str,
        message: str,
    ) -> Notification:
        notification = Notification(
            recipient_user_id=recipient_user_id,
            letter_id=letter_id,
            notification_type=notification_type,
            message=message,
        )
        self.session.add(notification)
        return notification

    def list_by_recipient(
        self, recipient_user_id: uuid.UUID, *, page: int, page_size: int
    ) -> Tuple[List[Notification], int]:
        """Newest first, stabilized by a secondary id sort — the same
        deterministic-ordering convention `LetterRepository.list_letters`
        already established."""
        stmt = select(Notification).where(Notification.recipient_user_id == recipient_user_id)

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = self.session.execute(count_stmt).scalar_one()

        items_stmt = (
            stmt.order_by(Notification.created_at.desc(), Notification.id.asc())
            .limit(page_size)
            .offset((page - 1) * page_size)
        )
        items = list(self.session.execute(items_stmt).scalars().all())
        return items, total

    def find_by_id_and_recipient(
        self, notification_id: uuid.UUID, recipient_user_id: uuid.UUID
    ) -> Optional[Notification]:
        stmt = select(Notification).where(
            Notification.id == notification_id,
            Notification.recipient_user_id == recipient_user_id,
        )
        return self.session.execute(stmt).scalar_one_or_none()

    def count_unread(self, recipient_user_id: uuid.UUID) -> int:
        stmt = (
            select(func.count())
            .select_from(Notification)
            .where(
                Notification.recipient_user_id == recipient_user_id,
                Notification.is_read.is_(False),
            )
        )
        return self.session.execute(stmt).scalar_one()

    def mark_read(self, notification: Notification) -> None:
        notification.is_read = True
        notification.read_at = datetime.now(timezone.utc)

    def mark_all_read(self, recipient_user_id: uuid.UUID) -> int:
        """Bulk update, not a fetch-and-loop — potentially many rows, and
        every row gets the identical `is_read`/`read_at` values, so there
        is nothing per-row to compute. Returns the number of rows
        actually flipped (0 if the caller had none unread)."""
        stmt = (
            sa_update(Notification)
            .where(
                Notification.recipient_user_id == recipient_user_id,
                Notification.is_read.is_(False),
            )
            .values(is_read=True, read_at=datetime.now(timezone.utc))
        )
        result = self.session.execute(stmt)
        return result.rowcount
