"""Data access for Department rows.

`find_by_name` is an exact match, matching the database's own uniqueness
constraint (`uq_departments_name`), which is case-sensitive — unlike
`users.email`, department names have no functional `lower()` index (Phase
2 never introduced one, and this phase doesn't either; see
docs/architecture/department-management.md, "Duplicate detection" for why
that's deliberate, not an oversight).

`update`/`update_status` are named, single-purpose methods — not a
generic `update(model, **kwargs)` reflection helper — mirroring the
existing precedent in app/repositories/user_authorization_repository.py:
mark_used, which also just sets attributes on an already-loaded row.
"""

import uuid
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.department import Department
from app.models.enums import ActiveStatus


class DepartmentRepository:
    def __init__(self, session: Session):
        self.session = session

    def find_by_id(self, department_id: uuid.UUID) -> Optional[Department]:
        return self.session.get(Department, department_id)

    def find_by_name(self, name: str) -> Optional[Department]:
        stmt = select(Department).where(Department.name == name)
        return self.session.execute(stmt).scalar_one_or_none()

    def list_all(self, *, status_filter: Optional[ActiveStatus] = None) -> List[Department]:
        stmt = select(Department).order_by(Department.name.asc())
        if status_filter is not None:
            stmt = stmt.where(Department.status == status_filter)
        return list(self.session.execute(stmt).scalars().all())

    def create(self, *, name: str, code: Optional[str], status: ActiveStatus) -> Department:
        department = Department(name=name, code=code, status=status)
        self.session.add(department)
        return department

    def update(
        self, department: Department, *, name: Optional[str] = None, code: Optional[str] = None
    ) -> None:
        if name is not None:
            department.name = name
        if code is not None:
            department.code = code

    def update_status(self, department: Department, status: ActiveStatus) -> None:
        department.status = status
