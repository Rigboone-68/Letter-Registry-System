"""Shared FastAPI dependencies for the API layer.

`get_current_user` is the authentication foundation Phase 3B's
role/department authorization decorators will build on (brief §15) — it
establishes *who* is calling, nothing about what they're allowed to do.
"""

import uuid

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.security import InvalidTokenError, decode_access_token
from app.database.session import get_db
from app.models.enums import UserStatus
from app.models.user import User
from app.repositories.user_repository import UserRepository

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
