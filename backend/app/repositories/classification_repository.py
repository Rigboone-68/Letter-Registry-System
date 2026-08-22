"""Data access for Classification rows.

Mirrors app/repositories/category_repository.py exactly, plus
`update_restricts_access` — the one field Category has no equivalent of.
"""

import uuid
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.classification import Classification
from app.models.enums import ActiveStatus


class ClassificationRepository:
    def __init__(self, session: Session):
        self.session = session

    def find_by_id(self, classification_id: uuid.UUID) -> Optional[Classification]:
        return self.session.get(Classification, classification_id)

    def find_by_name(self, name: str) -> Optional[Classification]:
        stmt = select(Classification).where(Classification.name == name)
        return self.session.execute(stmt).scalar_one_or_none()

    def list_all(
        self, *, status_filter: Optional[ActiveStatus] = None
    ) -> List[Classification]:
        stmt = select(Classification).order_by(Classification.name.asc())
        if status_filter is not None:
            stmt = stmt.where(Classification.status == status_filter)
        return list(self.session.execute(stmt).scalars().all())

    def create(
        self,
        *,
        name: str,
        description: Optional[str],
        restricts_access: bool,
        status: ActiveStatus,
    ) -> Classification:
        classification = Classification(
            name=name,
            description=description,
            restricts_access=restricts_access,
            status=status,
        )
        self.session.add(classification)
        return classification

    def update(
        self,
        classification: Classification,
        *,
        name: Optional[str] = None,
        description: Optional[str] = None,
        restricts_access: Optional[bool] = None,
    ) -> None:
        if name is not None:
            classification.name = name
        if description is not None:
            classification.description = description
        if restricts_access is not None:
            classification.restricts_access = restricts_access

    def update_status(self, classification: Classification, status: ActiveStatus) -> None:
        classification.status = status
