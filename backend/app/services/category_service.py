"""Category management business logic.

SYSTEM_ADMIN-only, enforced at the API layer (`require_system_admin`) —
nothing here re-checks role, same convention as
app/services/department_service.py, which this module mirrors exactly:
race-safe duplicate-name handling via a caught `IntegrityError` (never a
pre-check), never-physically-deleted (`status` -> `INACTIVE`), idempotent
activate/deactivate.

The three finalized V1 category names (General Letter, Notification,
Office Order — docs/architecture/letter-registry.md §2.4) are seeded as
ordinary rows by migration 48ec742d9e8f, not created through this
service and not hard-coded here — this service has no knowledge of which
category names are "the real ones"; it is generic CRUD, exactly like
DepartmentService.
"""

import uuid
from typing import List, Optional

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.category import Category
from app.models.enums import ActiveStatus
from app.repositories.category_repository import CategoryRepository
from app.services.exceptions import CategoryNotFoundError, DuplicateCategoryError


class CategoryService:
    def __init__(self, session: Session):
        self.session = session
        self.categories = CategoryRepository(session)

    def create_category(self, *, name: str, description: Optional[str]) -> Category:
        category = self.categories.create(
            name=name, description=description, status=ActiveStatus.ACTIVE
        )
        try:
            self.session.flush()
        except IntegrityError as exc:
            self.session.rollback()
            raise DuplicateCategoryError() from exc
        self.session.commit()
        self.session.refresh(category)
        return category

    def get_category(self, category_id: uuid.UUID) -> Category:
        category = self.categories.find_by_id(category_id)
        if category is None:
            raise CategoryNotFoundError()
        return category

    def list_categories(self, *, status_filter: Optional[ActiveStatus] = None) -> List[Category]:
        return self.categories.list_all(status_filter=status_filter)

    def update_category(
        self, category_id: uuid.UUID, *, name: Optional[str], description: Optional[str]
    ) -> Category:
        category = self.get_category(category_id)
        self.categories.update(category, name=name, description=description)
        try:
            self.session.flush()
        except IntegrityError as exc:
            self.session.rollback()
            raise DuplicateCategoryError() from exc
        self.session.commit()
        self.session.refresh(category)
        return category

    def activate_category(self, category_id: uuid.UUID) -> Category:
        category = self.get_category(category_id)
        self.categories.update_status(category, ActiveStatus.ACTIVE)
        self.session.commit()
        self.session.refresh(category)
        return category

    def deactivate_category(self, category_id: uuid.UUID) -> Category:
        category = self.get_category(category_id)
        self.categories.update_status(category, ActiveStatus.INACTIVE)
        self.session.commit()
        self.session.refresh(category)
        return category
