"""Department-isolation authorization logic.

Framework-agnostic on purpose: `assert_department_access` takes a plain
`User` and a department UUID and raises or doesn't — it has no FastAPI
import and no knowledge of requests, paths, or HTTP status codes. That
means it can be called from exactly two kinds of places without
duplicating the rule between them:

  1. `app/api/deps.py:require_department_access` — a thin FastAPI
     dependency wrapper for endpoints where the department is a URL path
     parameter (see docs/architecture/authorization.md §5).
  2. A future resource-level check — e.g. a Letter service that has
     already loaded a `Letter` row and needs to verify the *caller* may
     touch *that letter's* `department_id`, which isn't a URL parameter at
     all (see docs/architecture/authorization.md §6, "Resource-level
     authorization pattern"). No such resource exists yet in this phase —
     this function is the reusable pattern future ones are meant to call.

The rule itself (brief §2, §4, §8; extended in Phase 3B.2 §11):

  * SYSTEM_ADMIN: always allowed, regardless of `department_id` — including
    when it's `None` — and regardless of that department's `status`.
    SYSTEM_ADMIN's own `department_id` is always `None` (enforced by
    `ck_users_role_department_pairing`, Phase 2), so this rule is checked
    *before* anything ever compares `user.department_id` to the target —
    no code path here assumes `user.department_id` is set. This is also
    what keeps historical records in an INACTIVE department reachable for
    administrative purposes (brief §11) — nothing below this early return
    ever runs for SYSTEM_ADMIN.
  * ADMIN / USER: allowed only if `department_id` equals their own
    `user.department_id`, checked with a plain equality — not "does this
    department exist", so a made-up UUID is rejected exactly like a real
    but foreign one, with an identical error either way (see
    `DepartmentAccessDeniedError`'s docstring) — AND only if their
    department's `status` is `ACTIVE`. A Department moving to `INACTIVE`
    (Phase 3B.2) does not delete or modify any User row — this is the
    "small, clean extension" the brief asked for instead: the *same*
    department match that already succeeded is now also required to point
    at a currently-active department. `user.department` is read via the
    existing SQLAlchemy relationship (a lazy-loaded attribute on the
    already-loaded `User`), not a new query built here — no repository or
    session parameter was added to this function's signature to support
    this.
"""

import uuid
from typing import Optional

from app.models.enums import ActiveStatus, UserRole
from app.models.letter import Letter
from app.models.user import User
from app.services.exceptions import ClassifiedAccessDeniedError, DepartmentAccessDeniedError


def assert_department_access(user: User, department_id: Optional[uuid.UUID]) -> None:
    """Raise `DepartmentAccessDeniedError` unless `user` may access
    `department_id`. Returns normally (no value) when access is allowed."""
    if user.role == UserRole.SYSTEM_ADMIN:
        return
    if user.department_id is None or user.department_id != department_id:
        raise DepartmentAccessDeniedError()
    if user.department is not None and user.department.status != ActiveStatus.ACTIVE:
        raise DepartmentAccessDeniedError()


def assert_letter_access(user: User, letter: Letter) -> None:
    """Raise `DepartmentAccessDeniedError` or `ClassifiedAccessDeniedError`
    unless `user` may access `letter`. Returns normally when allowed. This
    is `Letter`'s first-ever use of `assert_department_access` as a
    resource-level check (Phase 4B) — see
    docs/architecture/letter-registry.md §5, the same pattern Phase 3B.4
    established for User management.

    Order matters (docs/architecture/letter-registry.md §8):

    1. Department isolation always runs first, against
       `letter.recipient_department_id` — never `source_department_id`,
       which carries no authorization meaning at all (an external sender
       has no LRS account). An out-of-department caller learns nothing
       more by also being told a letter is classified.
    2. SYSTEM_ADMIN retains complete access beyond this point (explicit
       product requirement — "System Administrator must retain complete
       administrative control").
    3. A classification that restricts access (`Classification.
       restricts_access`) narrows further for a plain USER who did not
       record the letter — ADMIN is never narrowed by this clause.

    This is the single seam every future refinement of the classified-
    visibility policy needs to change — no Letter CRUD code duplicates or
    bypasses this check. The exact policy below is a documented,
    conservative default, not a confirmed final one — see
    docs/architecture/letter-registry.md §8/§12.
    """
    assert_department_access(user, letter.recipient_department_id)

    if user.role == UserRole.SYSTEM_ADMIN:
        return

    if (
        letter.classification is not None
        and letter.classification.restricts_access
        and user.role == UserRole.USER
        and letter.recorded_by != user.id
    ):
        raise ClassifiedAccessDeniedError()


def can_view_letter(user: User, letter: Letter) -> bool:
    """Boolean convenience wrapper around `assert_letter_access`, for
    filtering a list of letters (app/services/letter_service.py:list_letters)
    rather than gating a single-resource endpoint. Shares the exact same
    policy — never reimplemented as a second, potentially-drifting
    check."""
    try:
        assert_letter_access(user, letter)
        return True
    except (DepartmentAccessDeniedError, ClassifiedAccessDeniedError):
        return False
