"""Data access for `LetterNumberSequence` — atomic Diary/Dispatch Number
allocation (Phase 6A, docs/architecture/correspondence.md §3).
"""

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.enums import LetterDirection
from app.models.letter_sequence import LetterNumberSequence


class LetterSequenceRepository:
    def __init__(self, session: Session):
        self.session = session

    def next_number(self, department_id: uuid.UUID, direction: LetterDirection) -> int:
        """Atomically returns the next number for
        `(department_id, direction)` and advances the counter, using
        `SELECT ... FOR UPDATE` — the same row-locking technique
        `app/repositories/user_authorization_repository.py` already uses
        — so two concurrent letter creations in the same department can
        never be handed the same value. Creates the counter row lazily
        (starting at 1) the first time a given department/direction pair
        is used, rather than requiring every department to be pre-seeded.

        Caller is responsible for the surrounding transaction (this
        method only flushes, never commits) — the letter row this number
        is destined for is inserted in the same unit of work, so a
        failure anywhere in that create still rolls the allocation back
        too, leaving no permanent gap.
        """
        stmt = (
            select(LetterNumberSequence)
            .where(
                LetterNumberSequence.department_id == department_id,
                LetterNumberSequence.direction == direction,
            )
            .with_for_update()
        )
        sequence = self.session.execute(stmt).scalar_one_or_none()
        if sequence is None:
            sequence = LetterNumberSequence(
                department_id=department_id, direction=direction, next_number=1
            )
            self.session.add(sequence)
            self.session.flush()

        value = sequence.next_number
        sequence.next_number = value + 1
        self.session.flush()
        return value
