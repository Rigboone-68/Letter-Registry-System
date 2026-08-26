"""Data access for Designation rows.

Mirrors app/repositories/category_repository.py's shape exactly — the
only difference is `find_by_name_ci`, a case-insensitive lookup (§7 of
docs/architecture/source-designation.md) that Category/Classification's
own case-sensitive `find_by_name` doesn't need.
"""

import uuid
from typing import List, Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.designation import Designation
from app.models.enums import ActiveStatus


class DesignationRepository:
    def __init__(self, session: Session):
        self.session = session

    def find_by_id(self, designation_id: uuid.UUID) -> Optional[Designation]:
        return self.session.get(Designation, designation_id)

    def find_by_name_ci(self, name: str) -> Optional[Designation]:
        stmt = select(Designation).where(func.lower(Designation.name) == func.lower(name))
        return self.session.execute(stmt).scalar_one_or_none()

    def list_all(self, *, status_filter: Optional[ActiveStatus] = None) -> List[Designation]:
        stmt = select(Designation).order_by(Designation.name.asc())
        if status_filter is not None:
            stmt = stmt.where(Designation.status == status_filter)
        return list(self.session.execute(stmt).scalars().all())

    def create(self, *, name: str, status: ActiveStatus) -> Designation:
        designation = Designation(name=name, status=status)
        self.session.add(designation)
        return designation

    def update(self, designation: Designation, *, name: Optional[str] = None) -> None:
        if name is not None:
            designation.name = name

    def update_status(self, designation: Designation, status: ActiveStatus) -> None:
        designation.status = status
