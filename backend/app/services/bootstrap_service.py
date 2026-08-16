"""Bootstrap the first System Admin account.

Deliberately has no HTTP endpoint — see app/cli.py, the only caller. The
first System Admin cannot come through public signup (there is no admin yet
to authorize them via UserAuthorization), and a bootstrap HTTP endpoint
would expose a "create a privileged account" operation to the network for
a capability that only ever needs to run once, locally, on the application
server. A CLI command run by whoever has server access is the smaller
attack surface for this specific operation.

No race-condition hardening beyond a single transaction: unlike signup
(app/services/auth_service.py), this is a rare, deliberate, operator-run
action, not a concurrent-request-prone endpoint — the brief's race-condition
requirement (§13) is scoped to signup specifically.
"""

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.security import hash_password, validate_password_policy
from app.models.enums import UserRole, UserStatus
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.services.exceptions import (
    DuplicateEmailError,
    InvalidPasswordError,
    SystemAdminAlreadyExistsError,
)
from app.utils.email import normalize_email


def create_system_admin(
    session: Session,
    *,
    full_name: str,
    email: str,
    password: str,
    password_confirm: str,
) -> User:
    if password != password_confirm:
        raise InvalidPasswordError("Passwords do not match.")
    try:
        validate_password_policy(password)
    except ValueError as exc:
        raise InvalidPasswordError(str(exc)) from exc

    users = UserRepository(session)
    if users.count_active_system_admins() > 0:
        raise SystemAdminAlreadyExistsError()

    user = users.create(
        full_name=full_name,
        email=normalize_email(email),
        password_hash=hash_password(password),
        role=UserRole.SYSTEM_ADMIN,
        department_id=None,
        status=UserStatus.ACTIVE,
    )

    try:
        session.flush()
    except IntegrityError as exc:
        session.rollback()
        raise DuplicateEmailError() from exc

    session.commit()
    session.refresh(user)
    return user
