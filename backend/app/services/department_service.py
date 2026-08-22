"""Department management business logic.

SYSTEM_ADMIN-only, but that authorization decision is made entirely at the
API layer (`require_system_admin`, see app/api/v1/endpoints/departments.py)
— nothing in this service re-checks role, matching how
app/services/auth_service.py doesn't re-check "is this really a login
request" either. This service assumes it is only ever called by a caller
who has already been authorized.

Owns its own transaction boundary, same pattern as
app/services/auth_service.py / bootstrap_service.py: explicit commit on
success, explicit rollback (via the IntegrityError branch) on failure.

Duplicate name/code handling (brief §5): this service does **not**
pre-check `find_by_name` before inserting/updating — a check-then-insert
has the same race window Phase 3A's signup consumption was written to
avoid (two concurrent requests could both pass the pre-check before either
commits). Instead it always attempts the write and relies on the
database's own unique constraints (`uq_departments_name`,
`uq_departments_code`) to be the single source of truth, catching the
resulting `IntegrityError` and translating it into a clean domain
exception via `_raise_for_integrity_error` — the constraint name reported
by PostgreSQL (via psycopg2's `diag.constraint_name`) says which column
conflicted, so the caller gets a specific, accurate error without a
second query.
"""

import uuid
from typing import List, Optional

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.department import Department
from app.models.enums import ActiveStatus
from app.repositories.department_repository import DepartmentRepository
from app.services.exceptions import (
    DepartmentNotFoundError,
    DuplicateDepartmentCodeError,
    DuplicateDepartmentError,
    DuplicateDepartmentNameError,
)


def _raise_for_integrity_error(exc: IntegrityError) -> None:
    constraint = getattr(getattr(exc.orig, "diag", None), "constraint_name", None)
    if constraint == "uq_departments_name":
        raise DuplicateDepartmentNameError() from exc
    if constraint == "uq_departments_code":
        raise DuplicateDepartmentCodeError() from exc
    raise DuplicateDepartmentError() from exc  # pragma: no cover - no other unique constraint exists today


class DepartmentService:
    def __init__(self, session: Session):
        self.session = session
        self.departments = DepartmentRepository(session)

    def create_department(self, *, name: str, code: Optional[str]) -> Department:
        """New departments are always created ACTIVE — there is no
        documented reason for any other default (brief §4)."""
        department = self.departments.create(name=name, code=code, status=ActiveStatus.ACTIVE)
        try:
            self.session.flush()
        except IntegrityError as exc:
            self.session.rollback()
            _raise_for_integrity_error(exc)
        self.session.commit()
        self.session.refresh(department)
        return department

    def get_department(self, department_id: uuid.UUID) -> Department:
        department = self.departments.find_by_id(department_id)
        if department is None:
            raise DepartmentNotFoundError()
        return department

    def list_departments(
        self, *, status_filter: Optional[ActiveStatus] = None
    ) -> List[Department]:
        return self.departments.list_all(status_filter=status_filter)

    def update_department(
        self,
        department_id: uuid.UUID,
        *,
        name: Optional[str],
        code: Optional[str],
    ) -> Department:
        """`name`/`code` of `None` means "leave unchanged", not "clear the
        field" — a client that supplies neither is rejected earlier, at the
        schema layer (app/schemas/department.py:DepartmentUpdate). This
        means an already-set `code` cannot currently be cleared back to
        null through this endpoint; see
        docs/architecture/department-management.md, "Known limitations"."""
        department = self.get_department(department_id)
        self.departments.update(department, name=name, code=code)
        try:
            self.session.flush()
        except IntegrityError as exc:
            self.session.rollback()
            _raise_for_integrity_error(exc)
        self.session.commit()
        self.session.refresh(department)
        return department

    def activate_department(self, department_id: uuid.UUID) -> Department:
        """Idempotent (brief §9): activating an already-ACTIVE department
        just returns its current state rather than erroring — the brief
        explicitly preferred this over a conflict response "if it keeps
        client behavior simple", and it does: a caller never needs to
        check current status before calling this."""
        department = self.get_department(department_id)
        self.departments.update_status(department, ActiveStatus.ACTIVE)
        self.session.commit()
        self.session.refresh(department)
        return department

    def deactivate_department(self, department_id: uuid.UUID) -> Department:
        """Idempotent, same reasoning as activate_department. Never
        touches `users`, `letters`, or any other row — see
        app/models/department.py and
        docs/architecture/department-management.md, "Historical data
        preservation"."""
        department = self.get_department(department_id)
        self.departments.update_status(department, ActiveStatus.INACTIVE)
        self.session.commit()
        self.session.refresh(department)
        return department
