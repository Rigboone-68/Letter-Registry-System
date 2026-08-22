"""Admin management endpoints — SYSTEM_ADMIN only.

Endpoints stay thin — request validation is the schema's job
(app/schemas/admin.py), business rules are the service's job
(app/services/admin_service.py); this module only translates service-layer
exceptions into HTTP responses, the same division of responsibility as
app/api/v1/endpoints/auth.py and departments.py.

Every route depends on `require_system_admin` (app/api/deps.py, Phase
3B.1) — reused as-is, not a new `require_admin_manager()` dependency (the
brief was explicit: System Admin is the only authority for Admin
management in this phase, so a second, more specific dependency would
decide nothing a plain role check doesn't already decide). ADMIN and USER
both receive `403` with the same generic message every other authorization
failure in this codebase uses; an unauthenticated caller receives `401`
from `get_current_user` before role is ever checked. This also means a
SYSTEM_ADMIN target is never reachable through these endpoints in a way
that could ever affect a caller who isn't already SYSTEM_ADMIN themselves
— see `AdminNotFoundError`'s docstring for how a SYSTEM_ADMIN id passed as
`{user_id}` is handled (a clean 404, not a 403 or a successful action).
"""

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import require_system_admin
from app.database.session import get_db
from app.models.enums import UserStatus
from app.models.user import User
from app.models.user_authorization import UserAuthorization
from app.schemas.admin import (
    AdminAuthorizationCreate,
    AdminAuthorizationResponse,
    AdminDepartmentUpdate,
    AdminListResponse,
    AdminResponse,
)
from app.services.admin_service import AdminService
from app.services.exceptions import (
    AdminNotFoundError,
    AdminNotPendingApprovalError,
    DepartmentNotActiveError,
    DepartmentNotFoundError,
    EmailAlreadyActiveAdminError,
    UnresolvedAdminAuthorizationExistsError,
)

router = APIRouter(prefix="/admins", tags=["admins"])


def _admin_not_found() -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Admin not found.")


def _department_not_found() -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Department not found.")


def _department_not_active() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail="The destination department is not ACTIVE.",
    )


@router.post(
    "/authorizations",
    response_model=AdminAuthorizationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Authorize an email to sign up as an Admin (SYSTEM_ADMIN only)",
)
def authorize_admin(
    payload: AdminAuthorizationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_system_admin),
) -> UserAuthorization:
    service = AdminService(db)
    try:
        return service.authorize_admin(
            email=payload.email,
            department_id=payload.department_id,
            authorized_by=current_user.id,
        )
    except DepartmentNotFoundError:
        raise _department_not_found()
    except DepartmentNotActiveError:
        raise _department_not_active()
    except EmailAlreadyActiveAdminError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This email already belongs to an active Admin.",
        )
    except UnresolvedAdminAuthorizationExistsError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This email already has an unresolved Admin authorization.",
        )


@router.get(
    "",
    response_model=AdminListResponse,
    summary="List Admins, optionally filtered by department/status (SYSTEM_ADMIN only)",
)
def list_admins(
    department_id: Optional[uuid.UUID] = Query(default=None),
    status_filter: Optional[UserStatus] = Query(default=None, alias="status"),
    db: Session = Depends(get_db),
    _current_user: User = Depends(require_system_admin),
) -> AdminListResponse:
    service = AdminService(db)
    admins = service.list_admins(department_id=department_id, status_filter=status_filter)
    return AdminListResponse(items=admins, total=len(admins))


@router.get(
    "/{user_id}",
    response_model=AdminResponse,
    summary="Get a single Admin by id (SYSTEM_ADMIN only)",
)
def get_admin(
    user_id: uuid.UUID,
    db: Session = Depends(get_db),
    _current_user: User = Depends(require_system_admin),
) -> User:
    service = AdminService(db)
    try:
        return service.get_admin(user_id)
    except AdminNotFoundError:
        raise _admin_not_found()


@router.post(
    "/{user_id}/approve",
    response_model=AdminResponse,
    summary="Approve a PENDING_APPROVAL Admin — not idempotent (SYSTEM_ADMIN only)",
)
def approve_admin(
    user_id: uuid.UUID,
    db: Session = Depends(get_db),
    _current_user: User = Depends(require_system_admin),
) -> User:
    service = AdminService(db)
    try:
        return service.approve_admin(user_id)
    except AdminNotFoundError:
        raise _admin_not_found()
    except AdminNotPendingApprovalError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This Admin is not awaiting approval.",
        )
    except DepartmentNotActiveError:
        raise _department_not_active()


@router.post(
    "/{user_id}/deactivate",
    response_model=AdminResponse,
    summary="Deactivate an Admin — idempotent (SYSTEM_ADMIN only)",
)
def deactivate_admin(
    user_id: uuid.UUID,
    db: Session = Depends(get_db),
    _current_user: User = Depends(require_system_admin),
) -> User:
    service = AdminService(db)
    try:
        return service.deactivate_admin(user_id)
    except AdminNotFoundError:
        raise _admin_not_found()


@router.post(
    "/{user_id}/reactivate",
    response_model=AdminResponse,
    summary="Reactivate an Admin — idempotent, requires an ACTIVE department (SYSTEM_ADMIN only)",
)
def reactivate_admin(
    user_id: uuid.UUID,
    db: Session = Depends(get_db),
    _current_user: User = Depends(require_system_admin),
) -> User:
    service = AdminService(db)
    try:
        return service.reactivate_admin(user_id)
    except AdminNotFoundError:
        raise _admin_not_found()
    except DepartmentNotActiveError:
        raise _department_not_active()


@router.patch(
    "/{user_id}/department",
    response_model=AdminResponse,
    summary="Move an Admin to a different (ACTIVE) department (SYSTEM_ADMIN only)",
)
def change_admin_department(
    user_id: uuid.UUID,
    payload: AdminDepartmentUpdate,
    db: Session = Depends(get_db),
    _current_user: User = Depends(require_system_admin),
) -> User:
    service = AdminService(db)
    try:
        return service.change_admin_department(user_id, department_id=payload.department_id)
    except AdminNotFoundError:
        raise _admin_not_found()
    except DepartmentNotFoundError:
        raise _department_not_found()
    except DepartmentNotActiveError:
        raise _department_not_active()
