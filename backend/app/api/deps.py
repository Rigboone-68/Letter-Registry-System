"""Shared FastAPI dependencies for the API layer.

`get_current_user` establishes *who* is calling (authentication — Phase
3A). Everything below it in this module establishes *what they're allowed
to do* (authorization — Phase 3B.1): role checks
(`require_system_admin`, `require_admin`, `require_admin_or_system_admin`,
`require_user_or_admin`) and the department-isolation check
(`require_department_access`). See docs/architecture/authorization.md for
the full design and the distinction between the two.

Every dependency here composes on top of `get_current_user` via FastAPI's
own `Depends()` mechanism rather than re-implementing token decoding or the
ACTIVE-status check — there is exactly one place either happens.
"""

import uuid
from typing import Iterable

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.security import InvalidTokenError, decode_access_token
from app.database.session import get_db
from app.models.enums import UserRole, UserStatus
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.services.authorization import assert_department_access
from app.services.exceptions import DepartmentAccessDeniedError

# HTTPBearer, not OAuth2PasswordBearer: this API's login endpoint accepts a
# JSON body (email/password), not an OAuth2 password-grant form, so the
# OAuth2 scheme's assumptions about the token endpoint's request shape
# don't apply. HTTPBearer only does what's actually happening here — read
# an `Authorization: Bearer <token>` header — and still gives Swagger UI a
# working "Authorize" field for manual verification.
_bearer_scheme = HTTPBearer()

# One error for every failure mode below (missing/malformed/expired/
# tampered token, unknown user, inactive user) — deliberately
# indistinguishable, for the same account-enumeration reasoning as
# InvalidCredentialsError in app/services/exceptions.py.
_CREDENTIALS_ERROR = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Could not validate credentials.",
    headers={"WWW-Authenticate": "Bearer"},
)


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    try:
        payload = decode_access_token(credentials.credentials)
    except InvalidTokenError:
        raise _CREDENTIALS_ERROR

    subject = payload.get("sub")
    try:
        user_id = uuid.UUID(str(subject))
    except (ValueError, TypeError, AttributeError):
        raise _CREDENTIALS_ERROR

    # Always re-fetch and re-check status from the database rather than
    # trusting the token's claims — an account deactivated after a token
    # was issued must stop working immediately, not wait for expiry
    # (brief §15, step 6; exercised by
    # tests/integration/test_auth_current_user.py).
    user = UserRepository(db).find_by_id(user_id)
    if user is None or user.status != UserStatus.ACTIVE:
        raise _CREDENTIALS_ERROR

    return user


# --- Role-based authorization (Phase 3B.1) --------------------------------
#
# Role is read from `current_user.role` — i.e. from the `User` row
# `get_current_user` just loaded from PostgreSQL — never from the JWT
# payload directly and never from anything client-supplied. The token does
# carry a `role` claim (see app/core/security.py:create_access_token), but
# that claim exists for a future fast-path/cache use, not as a trust
# source; every dependency below re-derives the source of truth itself via
# `current_user`.

# One generic 403 for every role/department authorization failure —
# deliberately no detail about which role or department was required, so a
# caller learns only "not permitted", never enough to map out the
# authorization rules of a resource they can't access. See
# docs/architecture/authorization.md, "Error behavior".
_FORBIDDEN_ERROR = HTTPException(
    status_code=status.HTTP_403_FORBIDDEN,
    detail="You do not have permission to perform this action.",
)


def _require_role(current_user: User, allowed_roles: Iterable[UserRole]) -> User:
    if current_user.role not in allowed_roles:
        raise _FORBIDDEN_ERROR
    return current_user


def require_system_admin(current_user: User = Depends(get_current_user)) -> User:
    return _require_role(current_user, {UserRole.SYSTEM_ADMIN})


def require_admin(current_user: User = Depends(get_current_user)) -> User:
    return _require_role(current_user, {UserRole.ADMIN})


def require_admin_or_system_admin(current_user: User = Depends(get_current_user)) -> User:
    return _require_role(current_user, {UserRole.ADMIN, UserRole.SYSTEM_ADMIN})


def require_user_or_admin(current_user: User = Depends(get_current_user)) -> User:
    return _require_role(current_user, {UserRole.USER, UserRole.ADMIN})


# --- Department-isolation authorization (Phase 3B.1) ----------------------


def require_department_access(
    department_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
) -> User:
    """FastAPI dependency wrapper for endpoints where the department being
    acted on is a URL path parameter of the same name — FastAPI resolves
    `department_id` from the path exactly as it would for the endpoint
    function itself. The actual rule lives in
    app/services/authorization.py:assert_department_access, which has no
    FastAPI dependency of its own and is what a future resource-level
    check (department not known until a row is loaded) should call
    directly instead of this wrapper — see that module's docstring."""
    try:
        assert_department_access(current_user, department_id)
    except DepartmentAccessDeniedError:
        raise _FORBIDDEN_ERROR
    return current_user
