"""User management endpoints — ADMIN only, scoped to the calling Admin's
own department.

Endpoints stay thin, same division of responsibility as
app/api/v1/endpoints/admins.py: request validation is the schema's job,
business rules are the service's job (app/services/user_service.py), this
module only translates service-layer exceptions into HTTP responses.

Every route depends on `require_admin` (app/api/deps.py, Phase 3B.1) —
strictly ADMIN, not `require_admin_or_system_admin`: System Admin has no
department of its own to scope these endpoints to, so it is not a valid
caller here (brief). USER and SYSTEM_ADMIN both receive `403` from the
role dependency before any of this module's code runs; an unauthenticated
caller receives `401` from `get_current_user` first.

The "authorizations" routes are declared before `/{user_id}` so that
`GET /users/authorizations` cannot be mis-parsed as
`GET /users/{user_id}` with `user_id="authorizations"` — path-matching
order matters here, not just readability.
"""

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import require_admin
from app.database.session import get_db
from app.models.enums import AuthorizationStatus, UserStatus
from app.models.user import User
from app.models.user_authorization import UserAuthorization
from app.schemas.user import (
    UserAuthorizationCreate,
    UserAuthorizationListResponse,
    UserAuthorizationResponse,
    UserListResponse,
    UserResponse,
)
from app.services.exceptions import (
    AuthorizationNotFoundError,
    AuthorizationNotRevocableError,
    DepartmentAccessDeniedError,
    EmailAlreadyActiveUserError,
    UnresolvedUserAuthorizationExistsError,
    UserNotFoundError,
    UserNotPendingApprovalError,
)
from app.services.user_service import UserService

router = APIRouter(prefix="/users", tags=["users"])


def _user_not_found() -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")


def _authorization_not_found() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND, detail="Authorization not found."
    )


def _forbidden() -> HTTPException:
    # Mirrors app/api/deps.py:_FORBIDDEN_ERROR exactly — same generic,
    # no-detail 403 for a department-authorization failure raised from the
    # service layer rather than a FastAPI dependency.
    return HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="You do not have permission to perform this action.",
    )


# --- Authorizations ----------------------------------------------------------


@router.post(
    "/authorizations",
    response_model=UserAuthorizationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Authorize an email to sign up as a User in your own department (ADMIN only)",
)
def authorize_user(
    payload: UserAuthorizationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> UserAuthorization:
    service = UserService(db)
    try:
        return service.authorize_user(email=payload.email, admin=current_user)
    except DepartmentAccessDeniedError:
        raise _forbidden()
    except EmailAlreadyActiveUserError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This email already belongs to an active User.",
        )
    except UnresolvedUserAuthorizationExistsError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This email already has an unresolved User authorization.",
        )


@router.get(
    "/authorizations",
    response_model=UserAuthorizationListResponse,
    summary="List User-purpose authorizations in your own department (ADMIN only)",
)
def list_authorizations(
    status_filter: Optional[AuthorizationStatus] = Query(default=None, alias="status"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> UserAuthorizationListResponse:
    service = UserService(db)
    authorizations = service.list_authorizations(admin=current_user, status_filter=status_filter)
    return UserAuthorizationListResponse(items=authorizations, total=len(authorizations))


@router.delete(
    "/authorizations/{authorization_id}",
    response_model=UserAuthorizationResponse,
    summary="Revoke a User authorization you created — idempotent (ADMIN only)",
)
def revoke_authorization(
    authorization_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> UserAuthorization:
    service = UserService(db)
    try:
        return service.revoke_authorization(authorization_id, admin=current_user)
    except AuthorizationNotFoundError:
        raise _authorization_not_found()
    except AuthorizationNotRevocableError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This authorization has already been used and cannot be revoked.",
        )


# --- Users ---------------------------------------------------------------------


@router.get(
    "",
    response_model=UserListResponse,
    summary="List Users in your own department (ADMIN only)",
)
def list_users(
    status_filter: Optional[UserStatus] = Query(default=None, alias="status"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> UserListResponse:
    service = UserService(db)
    users = service.list_users(admin=current_user, status_filter=status_filter)
    return UserListResponse(items=users, total=len(users))


@router.get(
    "/{user_id}",
    response_model=UserResponse,
    summary="Get a single User in your own department by id (ADMIN only)",
)
def get_user(
    user_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> User:
    service = UserService(db)
    try:
        return service.get_user(user_id, admin=current_user)
    except UserNotFoundError:
        raise _user_not_found()


@router.post(
    "/{user_id}/approve",
    response_model=UserResponse,
    summary="Approve a PENDING_APPROVAL User — not idempotent (ADMIN only)",
)
def approve_user(
    user_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> User:
    service = UserService(db)
    try:
        return service.approve_user(user_id, admin=current_user)
    except UserNotFoundError:
        raise _user_not_found()
    except UserNotPendingApprovalError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This User is not awaiting approval.",
        )
    except DepartmentAccessDeniedError:
        raise _forbidden()


@router.post(
    "/{user_id}/deactivate",
    response_model=UserResponse,
    summary="Deactivate a User — idempotent (ADMIN only)",
)
def deactivate_user(
    user_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> User:
    service = UserService(db)
    try:
        return service.deactivate_user(user_id, admin=current_user)
    except UserNotFoundError:
        raise _user_not_found()


@router.post(
    "/{user_id}/reactivate",
    response_model=UserResponse,
    summary="Reactivate a User — idempotent, requires your own department be ACTIVE (ADMIN only)",
)
def reactivate_user(
    user_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> User:
    service = UserService(db)
    try:
        return service.reactivate_user(user_id, admin=current_user)
    except UserNotFoundError:
        raise _user_not_found()
    except DepartmentAccessDeniedError:
        raise _forbidden()
