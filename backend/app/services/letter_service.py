"""Letter registry business logic.

Role scope, uniform across create/read/update/archive ("delete") — see
docs/architecture/letter-registry.md §9, an explicit IMPLEMENTATION
DECISION: `USER` and `ADMIN` share identical access within their own
`recipient_department_id`, narrowed only by the classified-access
boundary (`app/services/authorization.py:assert_letter_access`) for a
`USER` who didn't record the letter. `SYSTEM_ADMIN` has global read
access (via `assert_department_access`'s existing bypass) but never
creates a letter — it has no `department_id` to record one against.

Unlike `app/services/user_service.py` (Phase 3B.4), this service does
**not** split "read/lock-down" from "state-elevating" department-ACTIVE
requirements — every operation here uses `assert_letter_access`/
`assert_department_access` uniformly, including a caller's own inactive
department blocking even a plain read of their own department's letters.
This is a deliberate simplification, not an oversight: the finalized
Phase 4B decisions did not ask for a User-management-style nuanced
per-action policy for Letters, and reusing the plain, original
`assert_department_access` behavior (Phase 3B.1/3B.2) is the smaller,
more consistent change. See docs/architecture/letter-registry.md §9.

`recorded_by` and `recipient_department_id` are always derived from the
calling User/Admin's own identity — never accepted as a parameter that
could trace back to client input. `LetterService` has no method that
takes either as a caller-suppliable argument for `create_letter`.

"Archiving" ("delete", brief §11) never issues a SQL DELETE — see
`app/models/letter.py`'s docstring and docs/architecture/letter-registry.md
§9 for why this reuses, not reopens, Phase 2's original decision.
"""

import uuid
from datetime import datetime
from typing import List, Optional, Tuple

from sqlalchemy.orm import Session

from app.models.enums import ActiveStatus, LetterStatus, UserRole
from app.models.letter import Letter
from app.models.user import User
from app.repositories.category_repository import CategoryRepository
from app.repositories.classification_repository import ClassificationRepository
from app.repositories.department_repository import DepartmentRepository
from app.repositories.letter_repository import LetterRepository
from app.services.authorization import (
    assert_department_access,
    assert_letter_access,
    letter_visibility_filter,
)
from app.services.exceptions import (
    CategoryNotActiveError,
    CategoryNotFoundError,
    ClassificationNotActiveError,
    ClassificationNotFoundError,
    ClassifiedAccessDeniedError,
    DepartmentAccessDeniedError,
    InvalidDateRangeError,
    LetterNotFoundError,
    SourceDepartmentNotActiveError,
    SourceDepartmentNotFoundError,
)

MAX_PAGE_SIZE = 100
DEFAULT_PAGE_SIZE = 25


class LetterService:
    def __init__(self, session: Session):
        self.session = session
        self.letters = LetterRepository(session)
        self.categories = CategoryRepository(session)
        self.classifications = ClassificationRepository(session)
        self.departments = DepartmentRepository(session)

    # --- Shared validation ---------------------------------------------------

    def _validate_source_department(self, source_department_id: Optional[uuid.UUID]) -> None:
        if source_department_id is None:
            return
        department = self.departments.find_by_id(source_department_id)
        if department is None:
            raise SourceDepartmentNotFoundError()
        if department.status != ActiveStatus.ACTIVE:
            raise SourceDepartmentNotActiveError()

    def _validate_category(self, category_id: Optional[uuid.UUID]) -> None:
        if category_id is None:
            return
        category = self.categories.find_by_id(category_id)
        if category is None:
            raise CategoryNotFoundError()
        if category.status != ActiveStatus.ACTIVE:
            raise CategoryNotActiveError()

    def _validate_classification(self, classification_id: Optional[uuid.UUID]) -> None:
        if classification_id is None:
            return
        classification = self.classifications.find_by_id(classification_id)
        if classification is None:
            raise ClassificationNotFoundError()
        if classification.status != ActiveStatus.ACTIVE:
            raise ClassificationNotActiveError()

    def _get_for_access(self, letter_id: uuid.UUID, *, user: User) -> Letter:
        """Load a letter and enforce `assert_letter_access`, collapsing
        both "doesn't exist" and "exists but inaccessible" into the one
        `LetterNotFoundError` — same enumeration-prevention reasoning as
        `UserService.get_user` (Phase 3B.4), reusing (not duplicating)
        `assert_letter_access` rather than re-implementing the check."""
        letter = self.letters.find_by_id(letter_id)
        if letter is None:
            raise LetterNotFoundError()
        try:
            assert_letter_access(user, letter)
        except (DepartmentAccessDeniedError, ClassifiedAccessDeniedError) as exc:
            raise LetterNotFoundError() from exc
        return letter

    # --- Create ------------------------------------------------------------

    def create_letter(
        self,
        *,
        recorder: User,
        reference_number: str,
        source_name: str,
        source_department_id: Optional[uuid.UUID],
        source_location: Optional[str],
        sender_name: str,
        sender_designation: str,
        sender_department: str,
        sender_address: Optional[str],
        subject: Optional[str],
        reason: Optional[str],
        category_id: Optional[uuid.UUID],
        classification_id: Optional[uuid.UUID],
        received_at,
        text_content: Optional[str],
    ) -> Letter:
        # Tautological self-check: the recording User/Admin's own
        # department must be ACTIVE — mirrors
        # app/services/user_service.py:authorize_user's identical pattern.
        assert_department_access(recorder, recorder.department_id)

        self._validate_source_department(source_department_id)
        self._validate_category(category_id)
        self._validate_classification(classification_id)

        letter = self.letters.create(
            reference_number=reference_number,
            recipient_department_id=recorder.department_id,
            source_name=source_name,
            source_department_id=source_department_id,
            source_location=source_location,
            sender_name=sender_name,
            sender_designation=sender_designation,
            sender_department=sender_department,
            sender_address=sender_address,
            subject=subject,
            reason=reason,
            category_id=category_id,
            classification_id=classification_id,
            received_at=received_at,
            recorded_by=recorder.id,
            text_content=text_content,
        )
        # No try/except IntegrityError here: every FK on this insert is
        # validated beforehand (_validate_source_department/_category/
        # _classification), and recipient_department_id/recorded_by come
        # from an already-loaded, trusted User — there is no remaining
        # constraint this flush could realistically violate.
        # `reference_number` has no uniqueness constraint (removed by
        # migration c887ab35e4a3 — see app/models/letter.py).
        self.session.flush()
        self.session.commit()
        self.session.refresh(letter)
        return letter

    # --- Read ----------------------------------------------------------------

    def get_letter(self, letter_id: uuid.UUID, *, user: User) -> Letter:
        return self._get_for_access(letter_id, user=user)

    def list_letters(
        self,
        *,
        user: User,
        department_id: Optional[uuid.UUID] = None,
        status_filter: Optional[LetterStatus] = None,
        category_id: Optional[uuid.UUID] = None,
        classification_id: Optional[uuid.UUID] = None,
        reference_number: Optional[str] = None,
        subject: Optional[str] = None,
        sender_name: Optional[str] = None,
        sender_designation: Optional[str] = None,
        sender_department: Optional[str] = None,
        source_name: Optional[str] = None,
        source_location: Optional[str] = None,
        received_from: Optional[datetime] = None,
        received_to: Optional[datetime] = None,
        sort_by: str = "received_at",
        sort_descending: bool = True,
        page: int = 1,
        page_size: int = DEFAULT_PAGE_SIZE,
    ) -> Tuple[List[Letter], int]:
        """Returns `(items, total)`. `department_id` is only meaningful
        for a SYSTEM_ADMIN caller (optionally scope to one department;
        omit to see every department). A USER/ADMIN caller is always
        scoped to their own department regardless of what (if anything)
        they pass — the same "the caller doesn't get to choose the
        isolation-relevant parameter" convention `UserService.authorize_user`
        already established. Unchanged from before this phase.

        The classified-access rule is applied as a query-level predicate
        (`letter_visibility_filter`), not a post-fetch Python filter —
        `total` therefore already excludes anything the caller can't see,
        at every page, not just page 1. See
        docs/architecture/registry-search.md §8.

        `sort_by` is expected to already be a validated key from
        `app/repositories/letter_repository.py:SORTABLE_COLUMNS` — the
        endpoint layer maps a client-supplied enum value to one of these
        keys (rejecting anything else with `422`) before calling this
        method; this method does not re-validate it against arbitrary
        input, since it is never called with unvalidated client input
        directly.
        """
        if user.role == UserRole.SYSTEM_ADMIN:
            recipient_department_id = department_id
        else:
            recipient_department_id = user.department_id

        if received_from is not None and received_to is not None and received_from > received_to:
            raise InvalidDateRangeError()

        return self.letters.list_letters(
            recipient_department_id=recipient_department_id,
            status_filter=status_filter,
            category_id=category_id,
            classification_id=classification_id,
            reference_number=reference_number,
            subject=subject,
            sender_name=sender_name,
            sender_designation=sender_designation,
            sender_department=sender_department,
            source_name=source_name,
            source_location=source_location,
            received_from=received_from,
            received_to=received_to,
            visibility_filter=letter_visibility_filter(user),
            sort_column_key=sort_by,
            sort_descending=sort_descending,
            page=page,
            page_size=page_size,
        )

    # --- Update / Archive ------------------------------------------------------

    def update_letter(
        self,
        letter_id: uuid.UUID,
        *,
        user: User,
        reference_number: Optional[str] = None,
        source_name: Optional[str] = None,
        source_department_id: Optional[uuid.UUID] = None,
        source_location: Optional[str] = None,
        sender_name: Optional[str] = None,
        sender_designation: Optional[str] = None,
        sender_department: Optional[str] = None,
        sender_address: Optional[str] = None,
        subject: Optional[str] = None,
        reason: Optional[str] = None,
        category_id: Optional[uuid.UUID] = None,
        classification_id: Optional[uuid.UUID] = None,
        received_at=None,
        text_content: Optional[str] = None,
    ) -> Letter:
        letter = self._get_for_access(letter_id, user=user)

        if source_department_id is not None:
            self._validate_source_department(source_department_id)
        if category_id is not None:
            self._validate_category(category_id)
        if classification_id is not None:
            self._validate_classification(classification_id)

        self.letters.update(
            letter,
            reference_number=reference_number,
            source_name=source_name,
            source_department_id=source_department_id,
            source_location=source_location,
            sender_name=sender_name,
            sender_designation=sender_designation,
            sender_department=sender_department,
            sender_address=sender_address,
            subject=subject,
            reason=reason,
            category_id=category_id,
            classification_id=classification_id,
            received_at=received_at,
            text_content=text_content,
        )
        self.session.flush()
        self.session.commit()
        self.session.refresh(letter)
        return letter

    def archive_letter(self, letter_id: uuid.UUID, *, user: User) -> Letter:
        """Sets `status = ARCHIVED` — never a SQL DELETE. Idempotent:
        archiving an already-ARCHIVED letter just returns its current
        state, matching this project's established convention for
        "lock things down" actions (Department/Admin/User
        deactivate)."""
        letter = self._get_for_access(letter_id, user=user)
        self.letters.update_status(letter, LetterStatus.ARCHIVED)
        self.session.commit()
        self.session.refresh(letter)
        return letter
