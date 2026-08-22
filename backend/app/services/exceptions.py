"""Service-layer domain errors for authentication and account lifecycle.

Kept deliberately small and flat — one exception per distinct decision the
API layer needs to map to an HTTP response (see
app/api/v1/endpoints/auth.py), not one per possible failure detail. Several
of these are intentionally coarse-grained on purpose (see each docstring)
to avoid leaking information an attacker could use for account enumeration.
"""


class ServiceError(Exception):
    """Base class for authentication/account service-layer errors."""


class InvalidPasswordError(ServiceError):
    """A password fails the policy in app/core/security.py, or a
    password/password_confirm pair doesn't match."""


class SignupNotAuthorizedError(ServiceError):
    """No usable UserAuthorization exists for this email — covers "never
    authorized", "expired", "revoked", and "already used" identically and
    deliberately: signup should not reveal which of these applies."""


class DuplicateEmailError(ServiceError):
    """A User with this (normalized) email already exists."""


class InvalidCredentialsError(ServiceError):
    """Login: unknown email or wrong password — deliberately not
    distinguished, to avoid account enumeration via the login form."""


class AccountPendingApprovalError(ServiceError):
    """Login: credentials were correct, but the account is
    PENDING_APPROVAL. Only raised after a successful password check — see
    app/services/auth_service.py for why that ordering matters."""


class AccountDeactivatedError(ServiceError):
    """Login: credentials were correct, but the account is DEACTIVATED."""


class SystemAdminAlreadyExistsError(ServiceError):
    """Bootstrap: an active SYSTEM_ADMIN already exists; refuse to create
    a second one."""


class DepartmentAccessDeniedError(ServiceError):
    """The caller is not permitted to act on the given department — see
    app/services/authorization.py:assert_department_access. Deliberately
    carries no detail about *why* (department doesn't exist vs. belongs to
    someone else) or *what* the caller's own department is — see
    docs/architecture/authorization.md, "Error behavior"."""
