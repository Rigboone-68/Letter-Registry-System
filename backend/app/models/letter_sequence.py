"""LetterNumberSequence — the per-department, per-direction counter behind
Diary/Dispatch Number generation (Phase 6A,
docs/architecture/correspondence.md §3).

A pure counter table, not a business entity: one row per
`(department_id, direction)` pair, created lazily on first use rather than
pre-seeded for every department. `next_number` is read and incremented
under `SELECT ... FOR UPDATE` (see
`app/repositories/letter_repository.py:allocate_diary_number`) — the same
row-locking technique `app/repositories/user_authorization_repository.py`
already uses — so two concurrent letter creations in the same department
can never be handed the same number.

Deliberately department + direction scoped, not global and not date/year
scoped: each department already manages its own registry independently
everywhere else in this schema (Letters, notifications), and no reset
cadence (annual, monthly) was ever confirmed — see
docs/architecture/correspondence.md §4 for why a perpetually incrementing
counter is the safe default, and what a future confirmed reset rule would
change here (this table's shape, not any other code).
"""

import uuid

from sqlalchemy import ForeignKey, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base
from app.models.enums import LetterDirection, letter_direction_enum


class LetterNumberSequence(Base):
    __tablename__ = "letter_number_sequences"

    department_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("departments.id", ondelete="RESTRICT"),
        primary_key=True,
    )
    direction: Mapped[LetterDirection] = mapped_column(letter_direction_enum, primary_key=True)
    next_number: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")

    def __repr__(self) -> str:  # pragma: no cover - debug convenience only
        return (
            f"<LetterNumberSequence department_id={self.department_id} "
            f"direction={self.direction} next_number={self.next_number}>"
        )
