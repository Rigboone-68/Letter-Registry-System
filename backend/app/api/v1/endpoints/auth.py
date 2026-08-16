"""Authentication endpoints: signup, login, current-user.

Endpoints stay thin — request validation is the schema's job
(app/schemas/auth.py), business rules are the service's job
(app/services/auth_service.py); this module only translates service-layer
exceptions into HTTP responses.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import settings
from app.core.security import create_access_token
from app.database.session import get_db
from app.models.user import User
from app.schemas.auth import LoginRequest, SignupRequest, TokenResponse, UserPublic
from app.services.auth_service import AuthService
from app.services.exceptions import (
    AccountDeactivatedError,
    AccountPendingApprovalError,
    DuplicateEmailError,
    InvalidCredentialsError,
    SignupNotAuthorizedError,
)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/signup",
    response_model=UserPublic,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new account against a pre-authorized email",
)
def signup(payload: SignupRequest, db: Session = Depends(get_db)) -> User:
    service = AuthService(db)
    try:
        return service.signup(
            full_name=payload.full_name,
            email=payload.email,
            password=payload.password,
        )
    except SignupNotAuthorizedError:
        # Same response whether the email was never authorized, the
        # authorization expired, was revoked, or was already used — see
        # app/services/exceptions.py:SignupNotAuthorizedError.
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This email is not authorized to sign up.",
        )
    except DuplicateEmailError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists.",
        )


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Exchange email/password for a JWT access token",
)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    service = AuthService(db)
    try:
        user = service.login(email=payload.email, password=payload.password)
    except InvalidCredentialsError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password.",
        )
    except AccountPendingApprovalError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your account is awaiting administrator approval.",
        )
    except AccountDeactivatedError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your account has been deactivated.",
        )

    access_token = create_access_token(
        subject=user.id, role=user.role.value, department_id=user.department_id
    )
    return TokenResponse(
        access_token=access_token,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user=UserPublic.model_validate(user),
    )


@router.get(
    "/me",
    response_model=UserPublic,
    summary="Return the authenticated user's own profile",
)
def read_current_user(current_user: User = Depends(get_current_user)) -> User:
    return current_user
