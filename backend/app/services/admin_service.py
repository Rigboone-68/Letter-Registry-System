"""Admin management business logic (System Admin only — enforced at the
API layer via require_system_admin; nothing in this service re-checks
role, same convention as app/services/department_service.py).

Owns its own transaction boundary, same pattern as every other service in
this codebase: explicit commit on success, explicit rollback (via the
IntegrityError branch, where relevant) on failure.

Historical data (brief §24): nothing here ever touches `letters.department_id`
or any other historical column. `Letter.department_id` is its own,
independently-stored column (see app/models/letter.py) — it is set once,
at recording time, from the recording user's department, and is never
re-derived from that user later. Moving an Admin between departments
(`change_admin_department`) therefore cannot retroactively change which
department a Letter they previously recorded belongs to; the schema
already guarantees this structurally, so no snapshot/copy field or special
handling was added here for it. Verified directly in
tests/integration/test_admin_management.py, not just asserted.
"""

import uuid
from typing import List, Optional

from sqlalchemy.orm import Session

from app.models.enums import ActiveStatus, AuthorizationPurpose, UserRole, UserStatus
from app.models.user import User
from app.models.user_authorization import UserAuthorization
from app.repositories.department_repository import DepartmentRepository
from app.repositories.user_authorization_repository import UserAuthorizationRepository
from app.repositories.user_repository import UserRepository
from app.services.exceptions import (
    AdminNotFoundError,
    AdminNotPendingApprovalError,
    DepartmentNotActiveError,
    DepartmentNotFoundError,
    EmailAlreadyActiveAdminError,
    UnresolvedAdminAuthorizationExistsError,
)
from app.utils.email import normalize_email


class AdminService:
    def __init__(self, session: Session):
        self.session = session
        self.users = UserRepository(session)
        self.authorizations = UserAuthorizationRepository(session)
        self.departments = DepartmentRepository(session)

    # --- Authorization -----------------------------------------------------

    def authorize_admin(
        self, *, email: str, department_id: uuid.UUID, authorized_by: uuid.UUID
    ) -> UserAuthorization:
        """Create an ACTIVE, ADMIN-purpose UserAuthorization. `authorized_by`
        is always the calling SYSTEM_ADMIN's own id, supplied by the
        endpoint from `current_user` — never accepted from the request body
        (brief §5)."""
        normalized_email = normalize_email(email)

        department = self.departments.find_by_id(department_id)
        if department is None:
            raise DepartmentNotFoundError()
        if department.status != ActiveStatus.ACTIVE:
            raise DepartmentNotActiveError()

        existing_user = self.users.find_by_email(normalized_email)
        if (
            existing_user is not None
            and existing_user.role == UserRole.ADMIN
            and existing_user.status == UserStatus.ACTIVE
        ):
            raise EmailAlreadyActiveAdminError()

        if (
            self.authorizations.find_unresolved(normalized_email, AuthorizationPurpose.ADMIN)
            is not None
        ):
            raise UnresolvedAdminAuthorizationExistsError()

        authorization = self.authorizations.create(
            email=normalized_email,
            department_id=department_id,
            authorized_by=authorized_by,
            purpose=AuthorizationPurpose.ADMIN,
        )
        self.session.commit()
        self.session.refresh(authorization)
        return authorization

    # --- Read ----------------------------------------------------------------

    def get_admin(self, user_id: uuid.UUID) -> User:
        admin = self.users.find_admin_by_id(user_id)
        if admin is None:
            raise AdminNotFoundError()
        return admin

    def list_admins(
        self,
        *,
        department_id: Optional[uuid.UUID] = None,
        status_filter: Optional[UserStatus] = None,
    ) -> List[User]:
        return self.users.list_admins(department_id=department_id, status_filter=status_filter)

    # --- Lifecycle -------------------------------------------------------------

    def approve_admin(self, user_id: uuid.UUID) -> User:
        """PENDING_APPROVAL -> ACTIVE. Not idempotent (brief §8/test §22):
        approval is a one-time event, not a status toggle — approving an
        already-ACTIVE or DEACTIVATED account is rejected, unlike
        deactivate/reactivate below."""
        admin = self.get_admin(user_id)
        if admin.status != UserStatus.PENDING_APPROVAL:
            raise AdminNotPendingApprovalError()
        if admin.department is None or admin.department.status != ActiveStatus.ACTIVE:
            raise DepartmentNotActiveError()

        self.users.update_status(admin, UserStatus.ACTIVE)
        self.session.commit()
        self.session.refresh(admin)
        return admin

    def deactivate_admin(self, user_id: uuid.UUID) -> User:
        """Idempotent (consistent with Department activate/deactivate,
        Phase 3B.2) — always allowed regardless of department status; you
        can always deactivate an Admin. Deletes nothing: no letters, no
        audit history, no other row — only this User's own `status`."""
        admin = self.get_admin(user_id)
        self.users.update_status(admin, UserStatus.DEACTIVATED)
        self.session.commit()
        self.session.refresh(admin)
        return admin

    def reactivate_admin(self, user_id: uuid.UUID) -> User:
        """DEACTIVATED -> ACTIVE, idempotent if already ACTIVE — but
        *always* re-validates the Admin's department is ACTIVE first, even
        in the already-ACTIVE case (brief §10's preferred behavior): an
        Admin can end up ACTIVE while their department is INACTIVE (Phase
        3B.2 deactivation never touches User rows), and this endpoint must
        not pretend that's a safe, fully-operational state to (re)confirm.
        department-scoped authorization (assert_department_access) would
        still block them either way, but this endpoint's own contract is
        "ensure ACTIVE only when that's currently valid", not merely
        "ensure ACTIVE"."""
        admin = self.get_admin(user_id)
        if admin.department is None or admin.department.status != ActiveStatus.ACTIVE:
            raise DepartmentNotActiveError()

        self.users.update_status(admin, UserStatus.ACTIVE)
        self.session.commit()
        self.session.refresh(admin)
        return admin

    def change_admin_department(self, user_id: uuid.UUID, *, department_id: uuid.UUID) -> User:
        """Changes only `department_id` — role and status are untouched by
        this operation, and there is no field on
        app/schemas/admin.py:AdminDepartmentUpdate for a client to attempt
        either. Does not, and structurally cannot, rewrite any historical
        Letter's `department_id` — see this module's docstring."""
        admin = self.get_admin(user_id)

        department = self.departments.find_by_id(department_id)
        if department is None:
            raise DepartmentNotFoundError()
        if department.status != ActiveStatus.ACTIVE:
            raise DepartmentNotActiveError()

        self.users.update_department(admin, department_id)
        self.session.commit()
        self.session.refresh(admin)
        return admin
