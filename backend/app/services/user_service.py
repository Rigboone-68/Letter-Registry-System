"""User management business logic (Admin only, scoped to the Admin's own
department — enforced at the API layer via require_admin; nothing in this
service re-checks role, same convention as every other service in this
codebase).

Unlike app/services/admin_service.py (whose caller, SYSTEM_ADMIN, is
global and never department-scoped), every method here genuinely needs
department isolation, since the caller — an Admin — only has authority
within their own department. This is the first place
app/services/authorization.py:assert_department_access is exercised as a
*resource-level* check rather than only the URL-path-param wrapper
(require_department_access) — see that module's docstring, which
anticipated exactly this.

Three different isolation strengths are used deliberately, not
interchangeably:

* **Read** (`get_user`, `list_users`, `list_authorizations`) and
  **lock-down** (`deactivate_user`, `revoke_authorization`) actions only
  require the target to belong to the Admin's own department — they do
  *not* require that department to currently be ACTIVE. An Admin must
  always be able to see their team and always be able to shut off access,
  even in (especially in) a department that has itself been deactivated;
  gating these on department-ACTIVE would make it impossible to lock
  things down at exactly the moment you'd most want to.
* **State-elevating** actions (`authorize_user`, `approve_user`,
  `reactivate_user`) call `assert_department_access(admin,
  admin.department_id)` — a tautological self-check — which additionally
  requires the Admin's own department to be ACTIVE, mirroring
  app/services/admin_service.py's `approve_admin`/`reactivate_admin`
  precedent of re-validating department health before granting active
  access.
* `get_user` folds "wrong role" and "wrong department" into the same
  `UserNotFoundError` (see that exception's docstring) rather than using
  `assert_department_access`/`DepartmentAccessDeniedError` — a 403 would
  confirm the id belongs to *something*; brief requires Admin A to never
  learn that much about Department B's accounts.

Self-protection ("a User/Admin cannot approve/deactivate/reactivate
themselves") is not a separate check anywhere in this file — it holds by
construction, because `get_user` only ever resolves ids that are role
`USER`, and an Admin's own id is role `ADMIN`. See
app/repositories/user_repository.py:find_user_by_id.

Owns its own transaction boundary, same pattern as every other service.
"""

import uuid
from typing import List, Optional

from sqlalchemy.orm import Session

from app.models.enums import AuthorizationPurpose, AuthorizationStatus, UserRole, UserStatus
from app.models.user import User
from app.models.user_authorization import UserAuthorization
from app.repositories.user_authorization_repository import UserAuthorizationRepository
from app.repositories.user_repository import UserRepository
from app.services.audit_service import AuditService
from app.services.authorization import assert_department_access
from app.services.exceptions import (
    AuthorizationNotFoundError,
    AuthorizationNotRevocableError,
    EmailAlreadyActiveUserError,
    UnresolvedUserAuthorizationExistsError,
    UserNotFoundError,
    UserNotPendingApprovalError,
)
from app.utils.email import normalize_email


class UserService:
    def __init__(self, session: Session):
        self.session = session
        self.users = UserRepository(session)
        self.authorizations = UserAuthorizationRepository(session)
        self.audit = AuditService(session)

    # --- Authorization -------------------------------------------------------

    def authorize_user(self, *, email: str, admin: User) -> UserAuthorization:
        """Create an ACTIVE, USER-purpose UserAuthorization in the calling
        Admin's own department — `department_id` and `authorized_by` are
        always derived from `admin`, never accepted from the request body
        (there is no `department_id` field on
        app/schemas/user.py:UserAuthorizationCreate at all, unlike
        AdminAuthorizationCreate — a System Admin picks a target
        department; an Admin cannot, they only have one)."""
        assert_department_access(admin, admin.department_id)

        normalized_email = normalize_email(email)

        existing_user = self.users.find_by_email(normalized_email)
        if (
            existing_user is not None
            and existing_user.role == UserRole.USER
            and existing_user.status == UserStatus.ACTIVE
        ):
            raise EmailAlreadyActiveUserError()

        if (
            self.authorizations.find_unresolved(normalized_email, AuthorizationPurpose.USER)
            is not None
        ):
            raise UnresolvedUserAuthorizationExistsError()

        authorization = self.authorizations.create(
            email=normalized_email,
            department_id=admin.department_id,
            authorized_by=admin.id,
            purpose=AuthorizationPurpose.USER,
        )
        self.session.flush()
        self.audit.record(
            actor_id=admin.id,
            action="USER_AUTHORIZATION_CREATED",
            entity_type="UserAuthorization",
            entity_id=authorization.id,
            new_values={"email": normalized_email, "department_id": str(admin.department_id)},
        )
        self.session.commit()
        self.session.refresh(authorization)
        return authorization

    def list_authorizations(
        self, *, admin: User, status_filter: Optional[AuthorizationStatus] = None
    ) -> List[UserAuthorization]:
        return self.authorizations.list_by_department(
            department_id=admin.department_id,
            purpose=AuthorizationPurpose.USER,
            status_filter=status_filter,
        )

    def revoke_authorization(
        self, authorization_id: uuid.UUID, *, admin: User
    ) -> UserAuthorization:
        """Revocation is creator-scoped, not department-scoped (brief:
        "only the creating Admin can revoke") — deliberately stricter than
        `list_authorizations`' department-wide visibility. Idempotent for
        an already-REVOKED row (locking something down twice is still
        "locked down"); rejected for an already-USED row (see
        AuthorizationNotRevocableError) since the account it produced
        already exists and this can't retroactively un-create it. Never
        physically deletes the row — only flips `status`."""
        authorization = self.authorizations.find_by_id(authorization_id)
        if (
            authorization is None
            or authorization.purpose != AuthorizationPurpose.USER
            or authorization.department_id != admin.department_id
            or authorization.authorized_by != admin.id
        ):
            raise AuthorizationNotFoundError()

        if authorization.status == AuthorizationStatus.USED:
            raise AuthorizationNotRevocableError()

        if authorization.status == AuthorizationStatus.ACTIVE:
            self.authorizations.revoke(authorization)
            self.session.flush()
            self.audit.record(
                actor_id=admin.id,
                action="USER_AUTHORIZATION_REVOKED",
                entity_type="UserAuthorization",
                entity_id=authorization.id,
                old_values={"status": "ACTIVE"},
                new_values={"status": "REVOKED"},
            )
            self.session.commit()
            self.session.refresh(authorization)

        return authorization

    # --- Read ------------------------------------------------------------------

    def get_user(self, user_id: uuid.UUID, *, admin: User) -> User:
        user = self.users.find_user_by_id(user_id)
        if user is None or user.department_id != admin.department_id:
            raise UserNotFoundError()
        return user

    def list_users(
        self, *, admin: User, status_filter: Optional[UserStatus] = None
    ) -> List[User]:
        return self.users.list_users(
            department_id=admin.department_id, status_filter=status_filter
        )

    # --- Lifecycle ---------------------------------------------------------------

    def approve_user(self, user_id: uuid.UUID, *, admin: User) -> User:
        """PENDING_APPROVAL -> ACTIVE. Not idempotent, same one-time-event
        reasoning as AdminService.approve_admin."""
        user = self.get_user(user_id, admin=admin)
        if user.status != UserStatus.PENDING_APPROVAL:
            raise UserNotPendingApprovalError()
        assert_department_access(admin, admin.department_id)

        self.users.update_status(user, UserStatus.ACTIVE)
        self.session.flush()
        self.audit.record(
            actor_id=admin.id,
            action="USER_APPROVED",
            entity_type="User",
            entity_id=user.id,
            old_values={"status": "PENDING_APPROVAL"},
            new_values={"status": "ACTIVE"},
        )
        self.session.commit()
        self.session.refresh(user)
        return user

    def deactivate_user(self, user_id: uuid.UUID, *, admin: User) -> User:
        """Idempotent, always allowed regardless of the Admin's own
        department status — see module docstring."""
        user = self.get_user(user_id, admin=admin)
        was_active = user.status == UserStatus.ACTIVE
        self.users.update_status(user, UserStatus.DEACTIVATED)
        self.session.flush()
        if was_active:
            self.audit.record(
                actor_id=admin.id,
                action="USER_DEACTIVATED",
                entity_type="User",
                entity_id=user.id,
                old_values={"status": "ACTIVE"},
                new_values={"status": "DEACTIVATED"},
            )
        self.session.commit()
        self.session.refresh(user)
        return user

    def reactivate_user(self, user_id: uuid.UUID, *, admin: User) -> User:
        """DEACTIVATED -> ACTIVE, idempotent if already ACTIVE — but always
        re-validates the Admin's own department is ACTIVE first, same
        reasoning as AdminService.reactivate_admin."""
        user = self.get_user(user_id, admin=admin)
        assert_department_access(admin, admin.department_id)

        was_deactivated = user.status == UserStatus.DEACTIVATED
        self.users.update_status(user, UserStatus.ACTIVE)
        self.session.flush()
        if was_deactivated:
            self.audit.record(
                actor_id=admin.id,
                action="USER_REACTIVATED",
                entity_type="User",
                entity_id=user.id,
                old_values={"status": "DEACTIVATED"},
                new_values={"status": "ACTIVE"},
            )
        self.session.commit()
        self.session.refresh(user)
        return user
