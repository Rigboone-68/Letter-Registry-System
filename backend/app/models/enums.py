"""Python enums backing native PostgreSQL ENUM columns.

Each enum below is paired with a single, module-level `sqlalchemy.Enum`
instance (not re-instantiated per column). Reusing the same instance across
columns lets SQLAlchemy recognize a shared PostgreSQL type and emit exactly
one `CREATE TYPE` statement instead of a duplicate per table.

Storing roles/statuses as native enums (rather than plain strings) means the
database itself rejects a value that isn't one of the defined labels — the
constraint referenced throughout this phase as "do not allow arbitrary role
strings" comes from this choice, not from application code.
"""

import enum

from sqlalchemy import Enum as SAEnum


class UserRole(str, enum.Enum):
    """Roles recognized by LRS. See docs/architecture/overview.md for the
    department hierarchy each role sits in."""

    SYSTEM_ADMIN = "SYSTEM_ADMIN"
    ADMIN = "ADMIN"
    USER = "USER"


class UserStatus(str, enum.Enum):
    """Account lifecycle status. Deliberately minimal for V1 — accounts are
    never physically deleted, only moved to DEACTIVATED."""

    PENDING_APPROVAL = "PENDING_APPROVAL"
    ACTIVE = "ACTIVE"
    DEACTIVATED = "DEACTIVATED"


class AuthorizationStatus(str, enum.Enum):
    """Lifecycle of a pre-signup email authorization (see UserAuthorization)."""

    ACTIVE = "ACTIVE"
    USED = "USED"
    REVOKED = "REVOKED"


class AuthorizationPurpose(str, enum.Enum):
    """What role a UserAuthorization's eventual signup produces (Phase
    3B.3). Added to UserAuthorization rather than introducing a parallel
    AdminAuthorization table — see that model's docstring for why extending
    was the clean choice here. An explicit enum, not an inferred value: role
    is never guessed from department, `authorized_by`, or any other field —
    only from this one."""

    USER = "USER"
    ADMIN = "ADMIN"


class LetterStatus(str, enum.Enum):
    """V1 letter lifecycle. Archive *behavior* is not implemented in this
    phase — only the status value a future archive feature will set."""

    ACTIVE = "ACTIVE"
    ARCHIVED = "ARCHIVED"


class ActiveStatus(str, enum.Enum):
    """Shared active/inactive status for reference entities (Department,
    Category, Classification). These entities are never physically deleted —
    see each model's docstring for why."""

    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"


# Single shared type instances — import these into model modules rather than
# constructing `SAEnum(...)` again, so the PostgreSQL type is created once.
user_role_enum = SAEnum(UserRole, name="user_role")
user_status_enum = SAEnum(UserStatus, name="user_status")
authorization_status_enum = SAEnum(AuthorizationStatus, name="authorization_status")
authorization_purpose_enum = SAEnum(AuthorizationPurpose, name="authorization_purpose")
letter_status_enum = SAEnum(LetterStatus, name="letter_status")
active_status_enum = SAEnum(ActiveStatus, name="active_status")
