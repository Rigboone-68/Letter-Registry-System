"""Designation management business logic (Phase 5H).

SYSTEM_ADMIN-only for every write, enforced at the API layer
(`require_system_admin`) — nothing here re-checks role, the same
convention `CategoryService`/`DepartmentService` already establish:
race-safe duplicate-name handling via a caught `IntegrityError` (never a
pre-check, avoiding a check-then-act race), never-physically-deleted
(`status` -> `INACTIVE`), idempotent activate/deactivate.

`list_designations` has no role restriction of its own here — the read
path is deliberately open to every authenticated role (USER/ADMIN/
SYSTEM_ADMIN), enforced at the endpoint layer, not this service. See
docs/architecture/source-designation.md §11 for why this is a
deliberate departure from Category/Classification's own SYSTEM_ADMIN-
only list endpoint: USER/ADMIN are the only roles that ever record a
Letter, so they must be able to read the active Designation list to
populate the dropdown.
"""

import uuid
from typing import List, Optional

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.designation import Designation
from app.models.enums import ActiveStatus
from app.repositories.designation_repository import DesignationRepository
from app.services.audit_service import AuditService
from app.services.exceptions import DesignationNotFoundError, DuplicateDesignationError


class DesignationService:
    def __init__(self, session: Session):
        self.session = session
        self.designations = DesignationRepository(session)
        self.audit = AuditService(session)

    def create_designation(self, *, name: str, actor_id: uuid.UUID) -> Designation:
        designation = self.designations.create(name=name, status=ActiveStatus.ACTIVE)
        try:
            self.session.flush()
        except IntegrityError as exc:
            self.session.rollback()
            raise DuplicateDesignationError() from exc
        self.audit.record(
            actor_id=actor_id,
            action="DESIGNATION_CREATED",
            entity_type="Designation",
            entity_id=designation.id,
            new_values={"name": designation.name},
        )
        self.session.commit()
        self.session.refresh(designation)
        return designation

    def get_designation(self, designation_id: uuid.UUID) -> Designation:
        designation = self.designations.find_by_id(designation_id)
        if designation is None:
            raise DesignationNotFoundError()
        return designation

    def list_designations(self, *, status_filter: Optional[ActiveStatus] = None) -> List[Designation]:
        return self.designations.list_all(status_filter=status_filter)

    def update_designation(
        self, designation_id: uuid.UUID, *, name: Optional[str], actor_id: uuid.UUID
    ) -> Designation:
        designation = self.get_designation(designation_id)
        changed_fields = ["name"] if name is not None else []
        self.designations.update(designation, name=name)
        try:
            self.session.flush()
        except IntegrityError as exc:
            self.session.rollback()
            raise DuplicateDesignationError() from exc
        if changed_fields:
            self.audit.record(
                actor_id=actor_id,
                action="DESIGNATION_UPDATED",
                entity_type="Designation",
                entity_id=designation.id,
                new_values={"changed_fields": changed_fields},
            )
        self.session.commit()
        self.session.refresh(designation)
        return designation

    def activate_designation(self, designation_id: uuid.UUID, *, actor_id: uuid.UUID) -> Designation:
        designation = self.get_designation(designation_id)
        was_active = designation.status == ActiveStatus.ACTIVE
        self.designations.update_status(designation, ActiveStatus.ACTIVE)
        self.session.flush()
        if not was_active:
            self.audit.record(
                actor_id=actor_id,
                action="DESIGNATION_ACTIVATED",
                entity_type="Designation",
                entity_id=designation.id,
                old_values={"status": "INACTIVE"},
                new_values={"status": "ACTIVE"},
            )
        self.session.commit()
        self.session.refresh(designation)
        return designation

    def deactivate_designation(self, designation_id: uuid.UUID, *, actor_id: uuid.UUID) -> Designation:
        designation = self.get_designation(designation_id)
        was_inactive = designation.status == ActiveStatus.INACTIVE
        self.designations.update_status(designation, ActiveStatus.INACTIVE)
        self.session.flush()
        if not was_inactive:
            self.audit.record(
                actor_id=actor_id,
                action="DESIGNATION_DEACTIVATED",
                entity_type="Designation",
                entity_id=designation.id,
                old_values={"status": "ACTIVE"},
                new_values={"status": "INACTIVE"},
            )
        self.session.commit()
        self.session.refresh(designation)
        return designation
