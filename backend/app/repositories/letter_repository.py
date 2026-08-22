"""Data access for Letter rows.

Every read that returns a `Letter` a caller might act on eagerly loads
`classification` — `app/services/authorization.py:assert_letter_access`
needs `letter.classification.restricts_access` without a second query
being an easy-to-forget requirement at every call site.
"""

import uuid
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.models.enums import LetterStatus
from app.models.letter import Letter


class LetterRepository:
    def __init__(self, session: Session):
        self.session = session

    def find_by_id(self, letter_id: uuid.UUID) -> Optional[Letter]:
        stmt = (
            select(Letter)
            .where(Letter.id == letter_id)
            .options(joinedload(Letter.classification))
        )
        return self.session.execute(stmt).unique().scalar_one_or_none()

    def list_letters(
        self,
        *,
        recipient_department_id: Optional[uuid.UUID] = None,
        status_filter: Optional[LetterStatus] = None,
        category_id: Optional[uuid.UUID] = None,
        classification_id: Optional[uuid.UUID] = None,
    ) -> List[Letter]:
        """`recipient_department_id=None` means "no department filter" —
        only a valid query for a SYSTEM_ADMIN caller, whose global
        visibility is decided at the service layer
        (app/services/letter_service.py), not here. A USER/ADMIN caller's
        service-layer call always supplies their own department_id."""
        stmt = (
            select(Letter)
            .options(joinedload(Letter.classification))
            .order_by(Letter.received_at.desc())
        )
        if recipient_department_id is not None:
            stmt = stmt.where(Letter.recipient_department_id == recipient_department_id)
        if status_filter is not None:
            stmt = stmt.where(Letter.status == status_filter)
        if category_id is not None:
            stmt = stmt.where(Letter.category_id == category_id)
        if classification_id is not None:
            stmt = stmt.where(Letter.classification_id == classification_id)
        return list(self.session.execute(stmt).unique().scalars().all())

    def create(
        self,
        *,
        reference_number: str,
        recipient_department_id: uuid.UUID,
        source_name: str,
        source_department_id: Optional[uuid.UUID],
        source_location: Optional[str],
        sender_name: str,
        sender_designation: str,
        sender_department: str,
        sender_address: Optional[str],
        subject: Optional[str],
        reason: Optional[str],
        category_id: Optional[uuid.UUID],
        classification_id: Optional[uuid.UUID],
        received_at,
        recorded_by: uuid.UUID,
        text_content: Optional[str],
    ) -> Letter:
        letter = Letter(
            reference_number=reference_number,
            recipient_department_id=recipient_department_id,
            source_name=source_name,
            source_department_id=source_department_id,
            source_location=source_location,
            sender_name=sender_name,
            sender_designation=sender_designation,
            sender_department=sender_department,
            sender_address=sender_address,
            subject=subject,
            reason=reason,
            category_id=category_id,
            classification_id=classification_id,
            received_at=received_at,
            recorded_by=recorded_by,
            text_content=text_content,
        )
        self.session.add(letter)
        return letter

    def update(self, letter: Letter, **fields) -> None:
        """Plain attribute-set helper, same convention as
        DepartmentRepository.update — only `None`-valued keys are skipped,
        so a caller passes exactly the fields it wants changed (already
        filtered by the service layer, which knows the "None means
        unchanged" contract from the request schema)."""
        for key, value in fields.items():
            if value is not None:
                setattr(letter, key, value)

    def update_status(self, letter: Letter, status: LetterStatus) -> None:
        letter.status = status
