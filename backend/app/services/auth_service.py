"""Signup and login business logic.

Owns its own transaction boundary: `signup` explicitly commits on success
and rolls back on failure (there is no request-scoped commit-on-success
middleware in this project — see app/database/session.py:get_db), and
`login` never writes anything, so it never commits.
"""

import uuid
from typing import Optional

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.security import hash_password, verify_password
from app.models.enums import AuthorizationPurpose, UserRole, UserStatus
from app.models.user import User
from app.repositories.user_authorization_repository import UserAuthorizationRepository
from app.repositories.user_repository import UserRepository
from app.services.exceptions import (
    AccountDeactivatedError,
    AccountPendingApprovalError,
    DuplicateEmailError,
    InvalidCredentialsError,
    SignupNotAuthorizedError,
)
from app.utils.email import normalize_email

# A precomputed hash of a value nobody can ever type, verified against on a
# "user not found" login attempt so that path costs roughly the same
# Argon2 work as a real one — otherwise the two cases would be
# distinguishable by response time, which is its own account-enumeration
# channel (see app/services/exceptions.py:InvalidCredentialsError).
_DUMMY_PASSWORD_HASH = hash_password(f"dummy-{uuid.uuid4()}")


class AuthService:
    def __init__(self, session: Session):
        self.session = session
        self.users = UserRepository(session)
        self.authorizations = UserAuthorizationRepository(session)

    def signup(self, *, full_name: str, email: str, password: str) -> User:
        """Create a PENDING_APPROVAL User from a valid, unexpired, ACTIVE
        UserAuthorization, consuming it atomically. Role, department, and
        status are always derived here — never accepted from a caller; see
        app/schemas/auth.py:SignupRequest, which has no fields for them.

        Role (Phase 3B.3) comes from whichever authorization was found —
        `authorization.purpose == ADMIN` produces an ADMIN, anything else
        produces a USER. This is the *only* signup path for both: there is
        no separate "admin signup" endpoint (the brief was explicit that
        there must not be a second authentication workflow). A USER-purpose
        authorization can never produce an ADMIN, and vice versa, because
        role is read from this one field and nothing else — never guessed,
        never independently chosen."""
        normalized_email = normalize_email(email)

        authorization = self.authorizations.find_and_lock_active(normalized_email)
        if authorization is None:
            raise SignupNotAuthorizedError()

        self.authorizations.mark_used(authorization)

        role = (
            UserRole.ADMIN
            if authorization.purpose == AuthorizationPurpose.ADMIN
            else UserRole.USER
        )
        user = self.users.create(
            full_name=full_name,
            email=normalized_email,
            password_hash=hash_password(password),
            role=role,
            department_id=authorization.department_id,
            status=UserStatus.PENDING_APPROVAL,
        )

        try:
            self.session.flush()
        except IntegrityError as exc:
            # Rolling back here also un-consumes the authorization (same
            # transaction) — a failed signup never burns an authorization.
            self.session.rollback()
            raise DuplicateEmailError() from exc

        self.session.commit()
        self.session.refresh(user)
        return user

    def login(self, *, email: str, password: str) -> User:
        """Verify credentials and account status, in the order the brief
        specifies (§14): password before status. This means a wrong
        password never reveals whether the account is pending or
        deactivated — only a correct password does, which already proves
        the caller isn't blindly guessing."""
        normalized_email = normalize_email(email)
        user: Optional[User] = self.users.find_by_email(normalized_email)

        if user is None:
            verify_password(password, _DUMMY_PASSWORD_HASH)
            raise InvalidCredentialsError()

        if not verify_password(password, user.password_hash):
            raise InvalidCredentialsError()

        if user.status == UserStatus.PENDING_APPROVAL:
            raise AccountPendingApprovalError()
        if user.status == UserStatus.DEACTIVATED:
            raise AccountDeactivatedError()

        return user
