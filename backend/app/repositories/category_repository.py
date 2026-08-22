"""Data access for Category rows.

Mirrors app/repositories/department_repository.py's shape exactly —
`find_by_id`/`find_by_name`/`list_all`/`create`/`update`/`update_status`,
same named-method (not generic reflection) convention.
"""

import uuid
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.category import Category
from app.models.enums import ActiveStatus


class CategoryRepository:
    def __init__(self, session: Session):
        self.session = session

    def find_by_id(self, category_id: uuid.UUID) -> Optional[Category]:
        return self.session.get(Category, category_id)

    def find_by_name(self, name: str) -> Optional[Category]:
        stmt = select(Category).where(Category.name == name)
        return self.session.execute(stmt).scalar_one_or_none()

    def list_all(self, *, status_filter: Optional[ActiveStatus] = None) -> List[Category]:
        stmt = select(Category).order_by(Category.name.asc())
        if status_filter is not None:
            stmt = stmt.where(Category.status == status_filter)
        return list(self.session.execute(stmt).scalars().all())

    def create(self, *, name: str, description: Optional[str], status: ActiveStatus) -> Category:
        category = Category(name=name, description=description, status=status)
        self.session.add(category)
        return category

    def update(
        self,
        category: Category,
        *,
        name: Optional[str] = None,
        description: Optional[str] = None,
    ) -> None:
        if name is not None:
            category.name = name
        if description is not None:
            category.description = description

    def update_status(self, category: Category, status: ActiveStatus) -> None:
        category.status = status
