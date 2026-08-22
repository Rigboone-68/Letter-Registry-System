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
from typing import TYPE_CHECKING, Optional

from sqlalchemy import ColumnElement, or_

from app.models.classification import Classification
from app.models.enums import ActiveStatus, UserRole
from app.models.letter import Letter
from app.models.user import User
from app.services.exceptions import ClassifiedAccessDeniedError, DepartmentAccessDeniedError

if TYPE_CHECKING:
    from app.models.letter_document import LetterDocument


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
    """Boolean convenience wrapper around `assert_letter_access`, for a
    single already-loaded `Letter` (e.g. inside a loop, or a test
    assertion). **Not used by `list_letters`** — a query-level result set
    must never be filtered by fetching every row and then discarding some
    in Python; see `letter_visibility_filter` below and
    docs/architecture/registry-search.md §8 for why that pattern is a
    count/pagination leakage risk."""
    try:
        assert_letter_access(user, letter)
        return True
    except (DepartmentAccessDeniedError, ClassifiedAccessDeniedError):
        return False


def assert_document_access(user: User, document: "LetterDocument") -> None:
    """Raise `DepartmentAccessDeniedError` or `ClassifiedAccessDeniedError`
    unless `user` may access `document`. A thin delegate to
    `assert_letter_access(user, document.letter)` and nothing else — a
    `LetterDocument` has no authorization logic of its own to duplicate.
    `LetterDocument` also has no department field at all (only a
    transitive relationship via `letter.recipient_department_id`), so
    there is nothing here that could be derived from
    `document.uploaded_by_user.department_id` even by mistake — see
    docs/architecture/document-management.md §16-17.

    In practice, `app/services/document_service.py` reaches the same
    result by calling `LetterService.get_letter` directly (which already
    collapses "doesn't exist"/"wrong department"/"classified and
    inaccessible" into one `LetterNotFoundError`) rather than loading a
    `LetterDocument` first and calling this function — this function
    exists for any future caller that already holds a loaded
    `LetterDocument` and needs the same check without a second Letter
    fetch."""
    assert_letter_access(user, document.letter)


def letter_visibility_filter(user: User) -> Optional[ColumnElement[bool]]:
    """The SQL-expressible half of `assert_letter_access`'s classified-
    access rule (its third and final step) — for building a `Letter`
    *list/search* query whose `WHERE` clause, `COUNT`, and `LIMIT`/
    `OFFSET` all agree on which rows are visible, rather than fetching
    every department-scoped row and discarding some afterward. Department
    scoping (`assert_letter_access`'s first step) is not this function's
    job — the caller (`app/repositories/letter_repository.py:list_letters`)
    already applies `Letter.recipient_department_id == :dept` as a plain
    `WHERE` clause, computed exactly as before by
    `app/services/letter_service.py:list_letters`; nothing about that
    part changed or needed to.

    Returns `None` for `SYSTEM_ADMIN`/`ADMIN` — no additional restriction
    applies, so the caller should add no extra `WHERE` clause (and, not
    incidentally, does not need the `LEFT JOIN` to `classifications` this
    predicate would otherwise require). Returns a SQLAlchemy boolean
    expression for `USER` — true when the letter's classification doesn't
    restrict access, or the letter has no classification, or the caller
    themselves recorded it. Requires the query to join to
    `Classification` (on `Letter.classification_id ==
    Classification.id`) for `Classification.restricts_access` to be
    referenceable — the repository adds this join only when this function
    returns non-`None`, so an ADMIN/SYSTEM_ADMIN query pays no extra join
    cost.

    This expresses the *same* policy as `assert_letter_access`'s third
    step, not a second, independently-maintained one — both must be kept
    in sync by hand if the provisional policy ever changes, since one is
    Python boolean logic over an already-loaded row and the other is a
    SQL expression; there is no single shared implementation that could
    produce both without a much heavier abstraction than this policy
    (a three-line rule) justifies. See
    docs/architecture/registry-search.md §8 for the full reasoning.
    """
    if user.role != UserRole.USER:
        return None
    return or_(
        Letter.classification_id.is_(None),
        Classification.restricts_access.is_(False),
        Letter.recorded_by == user.id,
    )
