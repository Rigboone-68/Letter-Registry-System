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
    someone else, vs. exists and matches but is INACTIVE — see Phase 3B.2)
    or *what* the caller's own department is — see
    docs/architecture/authorization.md, "Error behavior"."""


class DepartmentNotFoundError(ServiceError):
    """No department exists with the given id — see
    app/services/department_service.py."""


class DuplicateDepartmentError(ServiceError):
    """A department already exists that conflicts with the requested name
    or code. Raised directly only as a fallback for a unique-constraint
    violation that doesn't match either named constraint below (should not
    happen given the current schema, but avoids a raw 500 if it ever does)
    — see the two specific subclasses for the expected cases."""


class DuplicateDepartmentNameError(DuplicateDepartmentError):
    """A department with this name already exists (`uq_departments_name`)."""


class DuplicateDepartmentCodeError(DuplicateDepartmentError):
    """A department with this code already exists (`uq_departments_code`)."""


class DepartmentNotActiveError(ServiceError):
    """A department exists but is `INACTIVE`, and the requested operation
    (authorizing an Admin candidate for it, approving/reactivating an Admin
    who belongs to it) requires it to be `ACTIVE` — see
    app/services/admin_service.py."""


class AdminNotFoundError(ServiceError):
    """No `User` exists with this id *and* role `ADMIN`. Deliberately used
    for both "no such user at all" and "a user exists but isn't an Admin"
    (e.g. the id belongs to a SYSTEM_ADMIN or a regular USER) — the two
    cases get an identical 404 from every endpoint in
    app/api/v1/endpoints/admins.py, so a caller can't use this API to probe
    which non-Admin ids exist, and a SYSTEM_ADMIN can never be targeted by
    an Admin-lifecycle endpoint (brief §15) by construction, not by a
    separate check."""


class AdminNotPendingApprovalError(ServiceError):
    """The target Admin exists but isn't `PENDING_APPROVAL`, so it cannot
    be approved (again). Approval is a one-time state transition, not an
    idempotent toggle — unlike Department activation/deactivation (Phase
    3B.2) or Admin deactivation/reactivation (this phase), approving an
    already-`ACTIVE` (or `DEACTIVATED`) account is rejected rather than
    silently accepted."""


class EmailAlreadyActiveAdminError(ServiceError):
    """This email already belongs to an ACTIVE Admin — see
    app/services/admin_service.py:authorize_admin."""


class UnresolvedAdminAuthorizationExistsError(ServiceError):
    """This email already has an ACTIVE, unexpired ADMIN-purpose
    authorization — see app/services/admin_service.py:authorize_admin."""


class UserNotFoundError(ServiceError):
    """No `User` exists with this id, role `USER`, *and* department_id
    matching the calling Admin's own department. All three failure modes
    (no such user, exists but isn't role USER, exists as a USER but in a
    different department) collapse to this one identical 404 from every
    endpoint in app/api/v1/endpoints/users.py — the same enumeration-
    prevention reasoning as AdminNotFoundError, extended one step further
    to also hide cross-department existence (brief: Admin A must never
    learn that a given id belongs to *any* account in Department B, not
    just be blocked from acting on it). This also makes an Admin's own id
    (role ADMIN, not USER) 404 on every lifecycle endpoint, so "a User/
    Admin cannot approve/deactivate/reactivate themselves" holds by
    construction — no separate self-check exists — see
    app/services/user_service.py."""


class UserNotPendingApprovalError(ServiceError):
    """The target User exists but isn't `PENDING_APPROVAL`, so it cannot
    be approved (again) — mirrors AdminNotPendingApprovalError; approval
    is a one-time transition, not an idempotent toggle."""


class EmailAlreadyActiveUserError(ServiceError):
    """This email already belongs to an ACTIVE User — see
    app/services/user_service.py:authorize_user."""


class UnresolvedUserAuthorizationExistsError(ServiceError):
    """This email already has an ACTIVE, unexpired USER-purpose
    authorization — see app/services/user_service.py:authorize_user."""


class AuthorizationNotFoundError(ServiceError):
    """No USER-purpose UserAuthorization exists with this id, created by
    the calling Admin, in the calling Admin's own department. All three
    failure modes (no such row, exists but is ADMIN-purpose, exists but
    was created by a different Admin or belongs to a different department)
    collapse to this one identical 404 — see
    app/services/user_service.py:revoke_authorization. Only the Admin who
    created an authorization may revoke it (brief); this is deliberately
    stricter than department-wide visibility (see
    app/services/user_service.py:list_authorizations, which has no such
    restriction)."""


class AuthorizationNotRevocableError(ServiceError):
    """The target authorization has already been consumed (`status ==
    USED`) — a completed signup cannot be un-done by revoking the
    authorization that produced it. Revoking an already-`REVOKED`
    authorization is treated as an idempotent no-op instead (unlike this
    case), matching the Department/Admin activate-deactivate convention
    for a "lock things down" action."""


# --- Category / Classification management (Phase 4B) -----------------------


class CategoryNotFoundError(ServiceError):
    """No `Category` exists with this id — see
    app/services/category_service.py."""


class DuplicateCategoryError(ServiceError):
    """A category with this name already exists
    (`uq_categories_name`)."""


class ClassificationNotFoundError(ServiceError):
    """No `Classification` exists with this id — see
    app/services/classification_service.py."""


class DuplicateClassificationError(ServiceError):
    """A classification with this name already exists
    (`uq_classifications_name`)."""


# --- Letter registry (Phase 4B) ---------------------------------------------


class LetterNotFoundError(ServiceError):
    """No `Letter` exists with this id, *or* it exists but the caller
    cannot access it — see app/services/authorization.py:assert_letter_access.
    Both a nonexistent id and a cross-department/classified-restricted one
    collapse to this one identical 404, the same enumeration-prevention
    reasoning `UserNotFoundError` established in Phase 3B.4: a 403 would
    confirm the id belongs to *something*."""


# DuplicateReferenceNumberError intentionally does not exist. `letters`
# has no reference_number uniqueness constraint (removed by migration
# c887ab35e4a3, a Phase 4B hardening finding — see
# app/models/letter.py's docstring) — the business confirmed reference
# numbers "must be unique" but never confirmed the scope, and this
# codebase does not add error handling for a constraint that no longer
# exists. See docs/architecture/letter-registry.md §2.3/§12.


class RecipientDepartmentNotFoundError(ServiceError):
    """No department exists with the given id — used only for a case that
    should be structurally unreachable in normal operation (a caller's own
    `department_id` always references a real row), kept as a defensive
    translation rather than a raw 500 if it ever somehow isn't."""


class SourceDepartmentNotFoundError(ServiceError):
    """`source_department_id` was supplied but does not reference an
    existing `Department` row."""


class SourceDepartmentNotActiveError(ServiceError):
    """`source_department_id` was supplied and exists, but that
    department is `INACTIVE`. Unlike the recipient department (whose
    ACTIVE-ness gates the calling User/Admin's own authority — see
    app/services/authorization.py:assert_department_access), an INACTIVE
    source department is rejected purely as a data-quality guard: citing
    a retired department as a letter's origin is very likely a mistake,
    not a legitimate historical fact to preserve the way a letter's own
    recipient-department history is preserved."""


class CategoryNotActiveError(ServiceError):
    """`category_id` was supplied and exists, but that category is
    `INACTIVE` — a retired category cannot be assigned to a *new* or
    *updated* letter (existing letters already tagged with it keep their
    reference; see app/models/category.py)."""


class ClassificationNotActiveError(ServiceError):
    """`classification_id` was supplied and exists, but that
    classification is `INACTIVE` — same reasoning as
    CategoryNotActiveError."""


class ClassifiedAccessDeniedError(ServiceError):
    """The target letter's classification restricts access
    (`Classification.restricts_access`), and the calling `USER` is
    neither the letter's recorder nor an `ADMIN`/`SYSTEM_ADMIN` — see
    app/services/authorization.py:assert_letter_access and
    docs/architecture/letter-registry.md §8 for why this specific rule is
    a documented, provisional default, not a confirmed final policy.
    Deliberately mapped to the same `404` as LetterNotFoundError by the
    API layer (not a distinguishable `403`) — a classified letter's mere
    existence should not be confirmable to a caller who can't see it."""
