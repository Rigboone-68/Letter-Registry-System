"""Classification management business logic.

Mirrors app/services/category_service.py exactly, plus `restricts_access`
— settable only through this SYSTEM_ADMIN-only service, never derived
from `name` (no string-matching on "Classified" or similar anywhere in
this codebase). See docs/architecture/letter-registry.md §8 for how this
flag participates in Letter-level authorization
(app/services/authorization.py:assert_letter_access).

No classification value is seeded by this phase — unlike Category, the
finalized decisions did not close Classification's value list; see
docs/architecture/letter-registry.md §2.5/§12.
"""

import uuid
from typing import List, Optional

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.classification import Classification
from app.models.enums import ActiveStatus
from app.repositories.classification_repository import ClassificationRepository
from app.services.exceptions import ClassificationNotFoundError, DuplicateClassificationError


class ClassificationService:
    def __init__(self, session: Session):
        self.session = session
        self.classifications = ClassificationRepository(session)

    def create_classification(
        self, *, name: str, description: Optional[str], restricts_access: bool
    ) -> Classification:
        classification = self.classifications.create(
            name=name,
            description=description,
            restricts_access=restricts_access,
            status=ActiveStatus.ACTIVE,
        )
        try:
            self.session.flush()
        except IntegrityError as exc:
            self.session.rollback()
            raise DuplicateClassificationError() from exc
        self.session.commit()
        self.session.refresh(classification)
        return classification

    def get_classification(self, classification_id: uuid.UUID) -> Classification:
        classification = self.classifications.find_by_id(classification_id)
        if classification is None:
            raise ClassificationNotFoundError()
        return classification

    def list_classifications(
        self, *, status_filter: Optional[ActiveStatus] = None
    ) -> List[Classification]:
        return self.classifications.list_all(status_filter=status_filter)

    def update_classification(
        self,
        classification_id: uuid.UUID,
        *,
        name: Optional[str],
        description: Optional[str],
        restricts_access: Optional[bool],
    ) -> Classification:
        classification = self.get_classification(classification_id)
        self.classifications.update(
            classification,
            name=name,
            description=description,
            restricts_access=restricts_access,
        )
        try:
            self.session.flush()
        except IntegrityError as exc:
            self.session.rollback()
            raise DuplicateClassificationError() from exc
        self.session.commit()
        self.session.refresh(classification)
        return classification

    def activate_classification(self, classification_id: uuid.UUID) -> Classification:
        classification = self.get_classification(classification_id)
        self.classifications.update_status(classification, ActiveStatus.ACTIVE)
        self.session.commit()
        self.session.refresh(classification)
        return classification

    def deactivate_classification(self, classification_id: uuid.UUID) -> Classification:
        classification = self.get_classification(classification_id)
        self.classifications.update_status(classification, ActiveStatus.INACTIVE)
        self.session.commit()
        self.session.refresh(classification)
        return classification
