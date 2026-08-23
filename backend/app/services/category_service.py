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
from app.services.audit_service import AuditService
from app.services.exceptions import CategoryNotFoundError, DuplicateCategoryError


class CategoryService:
    def __init__(self, session: Session):
        self.session = session
        self.categories = CategoryRepository(session)
        self.audit = AuditService(session)

    def create_category(
        self, *, name: str, description: Optional[str], actor_id: uuid.UUID
    ) -> Category:
        category = self.categories.create(
            name=name, description=description, status=ActiveStatus.ACTIVE
        )
        try:
            self.session.flush()
        except IntegrityError as exc:
            self.session.rollback()
            raise DuplicateCategoryError() from exc
        self.audit.record(
            actor_id=actor_id,
            action="CATEGORY_CREATED",
            entity_type="Category",
            entity_id=category.id,
            new_values={"name": category.name},
        )
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
        self,
        category_id: uuid.UUID,
        *,
        name: Optional[str],
        description: Optional[str],
        actor_id: uuid.UUID,
    ) -> Category:
        category = self.get_category(category_id)
        changed_fields = [
            field for field, value in (("name", name), ("description", description)) if value is not None
        ]
        self.categories.update(category, name=name, description=description)
        try:
            self.session.flush()
        except IntegrityError as exc:
            self.session.rollback()
            raise DuplicateCategoryError() from exc
        if changed_fields:
            self.audit.record(
                actor_id=actor_id,
                action="CATEGORY_UPDATED",
                entity_type="Category",
                entity_id=category.id,
                new_values={"changed_fields": changed_fields},
            )
        self.session.commit()
        self.session.refresh(category)
        return category

    def activate_category(self, category_id: uuid.UUID, *, actor_id: uuid.UUID) -> Category:
        category = self.get_category(category_id)
        was_active = category.status == ActiveStatus.ACTIVE
        self.categories.update_status(category, ActiveStatus.ACTIVE)
        self.session.flush()
        if not was_active:
            self.audit.record(
                actor_id=actor_id,
                action="CATEGORY_ACTIVATED",
                entity_type="Category",
                entity_id=category.id,
                old_values={"status": "INACTIVE"},
                new_values={"status": "ACTIVE"},
            )
        self.session.commit()
        self.session.refresh(category)
        return category

    def deactivate_category(self, category_id: uuid.UUID, *, actor_id: uuid.UUID) -> Category:
        category = self.get_category(category_id)
        was_inactive = category.status == ActiveStatus.INACTIVE
        self.categories.update_status(category, ActiveStatus.INACTIVE)
        self.session.flush()
        if not was_inactive:
            self.audit.record(
                actor_id=actor_id,
                action="CATEGORY_DEACTIVATED",
                entity_type="Category",
                entity_id=category.id,
                old_values={"status": "ACTIVE"},
                new_values={"status": "INACTIVE"},
            )
        self.session.commit()
        self.session.refresh(category)
        return category
