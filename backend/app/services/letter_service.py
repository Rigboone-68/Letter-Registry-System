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

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.enums import ActiveStatus, LetterDirection, LetterStatus, UserRole
from app.models.letter import Letter
from app.models.user import User
from app.models.designation import Designation
from app.repositories.category_repository import CategoryRepository
from app.repositories.classification_repository import ClassificationRepository
from app.repositories.department_repository import DepartmentRepository
from app.repositories.designation_repository import DesignationRepository
from app.repositories.letter_repository import LetterRepository
from app.repositories.letter_sequence_repository import LetterSequenceRepository
from app.services.audit_service import AuditService
from app.services.authorization import (
    assert_department_access,
    assert_dispatch_recipient_access,
    assert_letter_access,
    letter_visibility_filter,
)
from app.services.notification_service import NotificationService
from app.services.exceptions import (
    CategoryNotActiveError,
    CategoryNotFoundError,
    ClassificationNotActiveError,
    ClassificationNotFoundError,
    ClassifiedAccessDeniedError,
    DepartmentAccessDeniedError,
    DesignationNotActiveError,
    DesignationNotFoundError,
    DispatchDepartmentNotActiveError,
    DispatchDepartmentNotAllowedError,
    DispatchDepartmentNotFoundError,
    DispatchDepartmentRequiredError,
    InvalidDateRangeError,
    LetterNotDispatchedToCallerError,
    LetterNotFoundError,
    SelfDispatchNotAllowedError,
    SourceDepartmentNotActiveError,
    SourceDepartmentNotFoundError,
)

MAX_PAGE_SIZE = 100
DEFAULT_PAGE_SIZE = 25


def _serialize_bucket_key(value) -> Optional[str]:
    """Converts one raw `aggregate_letters` bucket key — a UUID, a
    `LetterStatus`/`LetterDirection` enum member, a `datetime` (from
    `date_trunc`), or `None` — into the single `Optional[str]` shape
    `LetterAggregateBucket.key` expects (Phase 6C). A `datetime` is
    rendered as a full ISO 8601 timestamp string (`.isoformat()`) rather
    than a bucket-granularity-specific format (e.g. `"2026-08"` for a
    month bucket) — simpler, always unambiguous, and the frontend
    already needs to parse/format dates for display regardless."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.isoformat()
    if hasattr(value, "value"):  # LetterStatus / LetterDirection
        return value.value
    return str(value)  # a UUID (category/classification/department id)


class LetterService:
    def __init__(self, session: Session):
        self.session = session
        self.letters = LetterRepository(session)
        self.categories = CategoryRepository(session)
        self.classifications = ClassificationRepository(session)
        self.departments = DepartmentRepository(session)
        self.designations = DesignationRepository(session)
        self.sequences = LetterSequenceRepository(session)
        self.audit = AuditService(session)
        self.notification_service = NotificationService(session)

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

    def _resolve_designation(self, designation_id: Optional[uuid.UUID]) -> Optional[Designation]:
        """Returns the referenced `Designation` when `designation_id` is
        supplied, requiring it to exist and be `ACTIVE` — the same shape
        as `_validate_category`, but returning the row (not just
        validating it) because the caller needs its *current* `name` to
        write into `sender_designation` (docs/architecture/
        source-designation.md §8/§9) — the master-data selection is
        authoritative, never the client-supplied `sender_designation`
        text, whenever a `designation_id` is actually being assigned."""
        if designation_id is None:
            return None
        designation = self.designations.find_by_id(designation_id)
        if designation is None:
            raise DesignationNotFoundError()
        if designation.status != ActiveStatus.ACTIVE:
            raise DesignationNotActiveError()
        return designation

    def _validate_correspondence_direction(
        self,
        *,
        recorder: User,
        direction: LetterDirection,
        dispatch_department_id: Optional[uuid.UUID],
    ) -> None:
        """Phase 6A (docs/architecture/correspondence.md §6). Keeps the
        two directions unambiguous: `OUTGOING` always names a real,
        `ACTIVE`, *different* destination department; `INCOMING` never
        carries one at all."""
        if direction == LetterDirection.INCOMING:
            if dispatch_department_id is not None:
                raise DispatchDepartmentNotAllowedError()
            return

        if dispatch_department_id is None:
            raise DispatchDepartmentRequiredError()
        if dispatch_department_id == recorder.department_id:
            raise SelfDispatchNotAllowedError()
        department = self.departments.find_by_id(dispatch_department_id)
        if department is None:
            raise DispatchDepartmentNotFoundError()
        if department.status != ActiveStatus.ACTIVE:
            raise DispatchDepartmentNotActiveError()

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
        designation_id: Optional[uuid.UUID],
        sender_department: str,
        sender_address: Optional[str],
        subject: Optional[str],
        reason: Optional[str],
        category_id: Optional[uuid.UUID],
        classification_id: Optional[uuid.UUID],
        received_at,
        text_content: Optional[str],
        direction: LetterDirection = LetterDirection.INCOMING,
        dispatch_department_id: Optional[uuid.UUID] = None,
        continuation_of_letter_id: Optional[uuid.UUID] = None,
    ) -> Letter:
        # Tautological self-check: the recording User/Admin's own
        # department must be ACTIVE — mirrors
        # app/services/user_service.py:authorize_user's identical pattern.
        assert_department_access(recorder, recorder.department_id)

        self._validate_source_department(source_department_id)
        self._validate_category(category_id)
        self._validate_classification(classification_id)
        self._validate_correspondence_direction(
            recorder=recorder, direction=direction, dispatch_department_id=dispatch_department_id
        )
        designation = self._resolve_designation(designation_id)
        if designation is not None:
            # Master-data selection is authoritative — never trust the
            # client's own sender_designation text once a designation_id
            # is supplied (docs/architecture/source-designation.md §9).
            sender_designation = designation.name

        # A continuation must reference a letter the caller can already
        # see — the same `_get_for_access` every other single-resource
        # read/write in this service reuses, never a bespoke check
        # (docs/architecture/correspondence.md §7). This also means a
        # continuation can only ever point at a letter within the
        # caller's own department (or, for SYSTEM_ADMIN, anywhere) —
        # never a silent cross-department reference.
        if continuation_of_letter_id is not None:
            self._get_for_access(continuation_of_letter_id, user=recorder)

        diary_number = str(self.sequences.next_number(recorder.department_id, direction))

        letter = self.letters.create(
            reference_number=reference_number,
            recipient_department_id=recorder.department_id,
            source_name=source_name,
            source_department_id=source_department_id,
            source_location=source_location,
            sender_name=sender_name,
            sender_designation=sender_designation,
            designation_id=designation_id,
            sender_department=sender_department,
            sender_address=sender_address,
            subject=subject,
            reason=reason,
            category_id=category_id,
            classification_id=classification_id,
            received_at=received_at,
            recorded_by=recorder.id,
            text_content=text_content,
            direction=direction,
            dispatch_department_id=dispatch_department_id,
            diary_number=diary_number,
            continuation_of_letter_id=continuation_of_letter_id,
        )
        # No try/except IntegrityError here: every FK on this insert is
        # validated beforehand (_validate_source_department/_category/
        # _classification/_resolve_designation/_validate_correspondence_direction),
        # and recipient_department_id/recorded_by come from an already-loaded,
        # trusted User — there is no remaining constraint this flush
        # could realistically violate.
        # `reference_number` has no uniqueness constraint (removed by
        # migration c887ab35e4a3 — see app/models/letter.py).
        self.session.flush()

        # Audit is mandatory (docs/architecture/audit-notifications.md
        # §20) — a failure here propagates uncaught, so the letter above
        # is never committed either. Only targeted, non-sensitive fields
        # are recorded — never text_content or sender details (§8/§10).
        self.audit.record(
            actor_id=recorder.id,
            action="LETTER_CREATED",
            entity_type="Letter",
            entity_id=letter.id,
            new_values={
                "reference_number": letter.reference_number,
                "recipient_department_id": str(letter.recipient_department_id),
                "direction": letter.direction.value,
            },
        )
        # Notification is best-effort (§20/§21) — notify_letter_registered
        # never raises; a failure there cannot affect the commit below.
        # Unchanged for every letter, direction notwithstanding: the
        # recording department's own admins still learn a new record was
        # registered in their department, exactly as before Phase 6A.
        self.notification_service.notify_letter_registered(letter)
        if direction == LetterDirection.OUTGOING:
            # New in Phase 6A — a *separate*, additional notification to
            # the dispatch department's own admins; never replaces the
            # one above.
            self.notification_service.notify_letter_dispatched(letter)

        self.session.commit()
        self.session.refresh(letter)
        return letter

    # --- Correspondence — record incoming from an outgoing dispatch ----------

    def record_incoming_correspondence(self, outgoing_letter_id: uuid.UUID, *, recorder: User) -> Tuple[Letter, bool]:
        """The "Record" action (Phase 6A,
        docs/architecture/correspondence.md §7). Returns
        `(incoming_letter, was_created)` — `was_created` is `False` when
        the outgoing letter had already been recorded, in which case the
        *existing* incoming letter is returned unchanged (idempotent,
        matching this project's established convention for a repeatable
        action, e.g. `archive_letter`).

        Every field copied onto the new incoming letter comes from the
        outgoing letter's own already-validated data — nothing here is
        re-entered or re-validated (category/classification/designation
        were already confirmed valid when the outgoing letter was
        created), satisfying the brief's explicit "do not require the
        recipient to manually re-enter" instruction.
        """
        assert_department_access(recorder, recorder.department_id)

        outgoing_letter = self.letters.find_by_id(outgoing_letter_id)
        if outgoing_letter is None:
            raise LetterNotFoundError()
        # Deliberately not `assert_letter_access` — that checks
        # `recipient_department_id` (the *dispatching* department here),
        # which is the wrong question for this action. This is the one
        # new, additive check Phase 6A introduces; see its own docstring
        # for why the two never overlap or duplicate each other.
        try:
            assert_dispatch_recipient_access(recorder, outgoing_letter)
        except LetterNotDispatchedToCallerError:
            # Same enumeration-prevention collapse every other
            # department-scoped 404 in this codebase already uses — a
            # caller outside the dispatch relationship learns nothing
            # from the response code.
            raise LetterNotFoundError()

        existing = self.letters.find_by_recorded_from_letter_id(outgoing_letter.id)
        if existing is not None:
            return existing, False

        diary_number = str(
            self.sequences.next_number(recorder.department_id, LetterDirection.INCOMING)
        )
        incoming_letter = self.letters.create(
            reference_number=outgoing_letter.reference_number,
            recipient_department_id=recorder.department_id,
            source_name=outgoing_letter.source_name,
            source_department_id=outgoing_letter.source_department_id,
            source_location=outgoing_letter.source_location,
            sender_name=outgoing_letter.sender_name,
            sender_designation=outgoing_letter.sender_designation,
            designation_id=outgoing_letter.designation_id,
            sender_department=outgoing_letter.sender_department,
            sender_address=outgoing_letter.sender_address,
            subject=outgoing_letter.subject,
            reason=outgoing_letter.reason,
            category_id=outgoing_letter.category_id,
            classification_id=outgoing_letter.classification_id,
            received_at=outgoing_letter.received_at,
            recorded_by=recorder.id,
            text_content=outgoing_letter.text_content,
            direction=LetterDirection.INCOMING,
            diary_number=diary_number,
            recorded_from_letter_id=outgoing_letter.id,
        )
        try:
            self.session.flush()
        except IntegrityError:
            # Race guard: two concurrent "Record" clicks both passed the
            # `existing is None` check above. The database's partial
            # unique index on `recorded_from_letter_id` is the actual
            # guarantee — whichever request loses the race rolls back and
            # returns the row the winner created, rather than erroring.
            self.session.rollback()
            existing = self.letters.find_by_recorded_from_letter_id(outgoing_letter.id)
            if existing is not None:
                return existing, False
            raise  # pragma: no cover - defensive, should be unreachable

        self.audit.record(
            actor_id=recorder.id,
            action="LETTER_RECORDED_FROM_DISPATCH",
            entity_type="Letter",
            entity_id=incoming_letter.id,
            new_values={
                "recorded_from_letter_id": str(outgoing_letter.id),
                "recipient_department_id": str(incoming_letter.recipient_department_id),
            },
        )
        # Best-effort, same as every other notification trigger — never
        # raises, never blocks the commit below.
        self.notification_service.notify_correspondence_recorded(
            outgoing_letter=outgoing_letter, incoming_letter=incoming_letter
        )

        self.session.commit()
        self.session.refresh(incoming_letter)
        return incoming_letter, True

    # --- Read ----------------------------------------------------------------

    def get_letter(self, letter_id: uuid.UUID, *, user: User) -> Letter:
        return self._get_for_access(letter_id, user=user)

    def list_letters(
        self,
        *,
        user: User,
        department_id: Optional[uuid.UUID] = None,
        status_filter: Optional[LetterStatus] = None,
        direction_filter: Optional[LetterDirection] = None,
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
            direction_filter=direction_filter,
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

    # --- Aggregate (Phase 6C, dashboard analytics) ----------------------------

    def aggregate_letters(
        self,
        *,
        user: User,
        group_by: str,
        department_id: Optional[uuid.UUID] = None,
        status_filter: Optional[LetterStatus] = None,
        direction_filter: Optional[LetterDirection] = None,
        category_id: Optional[uuid.UUID] = None,
        classification_id: Optional[uuid.UUID] = None,
        dispatch_department_id: Optional[uuid.UUID] = None,
        received_from: Optional[datetime] = None,
        received_to: Optional[datetime] = None,
    ) -> List[Tuple[Optional[str], int]]:
        """Returns a list of `(serialized_bucket_key, count)` tuples.
        Department-derivation and the classified-visibility predicate
        are the *exact* logic `list_letters` above already uses —
        reused, not reimplemented (docs/architecture/
        dashboard-analytics-api.md §8/§10's own explicit instruction:
        "there is exactly one authoritative authorization expression
        for Letter visibility in this system, and this review's design
        adds no second one" — still true after Phase 6A, since neither
        `assert_department_access` nor `letter_visibility_filter` was
        touched by that phase).
        """
        if user.role == UserRole.SYSTEM_ADMIN:
            recipient_department_id = department_id
        else:
            recipient_department_id = user.department_id

        if received_from is not None and received_to is not None and received_from > received_to:
            raise InvalidDateRangeError()

        rows = self.letters.aggregate_letters(
            group_by=group_by,
            recipient_department_id=recipient_department_id,
            status_filter=status_filter,
            direction_filter=direction_filter,
            category_id=category_id,
            classification_id=classification_id,
            dispatch_department_id=dispatch_department_id,
            received_from=received_from,
            received_to=received_to,
            visibility_filter=letter_visibility_filter(user),
        )
        return [(_serialize_bucket_key(key), count) for key, count in rows]

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
        designation_id: Optional[uuid.UUID] = None,
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

        # Captured before the repository mutates `letter` in place —
        # needed for the targeted old/new audit pairs below (§8/§11).
        old_category_id = letter.category_id
        old_classification_id = letter.classification_id
        old_designation_id = letter.designation_id

        # A resent-but-unchanged designation_id (e.g. a form that always
        # echoes the letter's current value) is never re-validated —
        # only an actual *change* requires the newly selected
        # Designation to be ACTIVE (docs/architecture/
        # source-designation.md §9). Deliberately more lenient than
        # _validate_category's own "any explicit value is re-validated"
        # behavior, specifically so an already-assigned, now-inactive
        # Designation never blocks an edit that isn't trying to change
        # it — preserving historical integrity.
        if designation_id is not None and designation_id != old_designation_id:
            designation = self._resolve_designation(designation_id)
            # Master-data selection is authoritative — overrides
            # whatever sender_designation text the client also sent.
            sender_designation = designation.name

        changed_fields = [
            field
            for field, value in (
                ("reference_number", reference_number),
                ("source_name", source_name),
                ("source_department_id", source_department_id),
                ("source_location", source_location),
                ("sender_name", sender_name),
                ("sender_designation", sender_designation),
                ("designation_id", designation_id),
                ("sender_department", sender_department),
                ("sender_address", sender_address),
                ("subject", subject),
                ("reason", reason),
                ("category_id", category_id),
                ("classification_id", classification_id),
                ("received_at", received_at),
                ("text_content", text_content),
            )
            if value is not None
        ]

        self.letters.update(
            letter,
            reference_number=reference_number,
            source_name=source_name,
            source_department_id=source_department_id,
            source_location=source_location,
            sender_name=sender_name,
            sender_designation=sender_designation,
            designation_id=designation_id,
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

        # A general edit trail records only which fields changed, never
        # their values (§8) — field *names* are safe; a value could be
        # sender/content data this project has no reason to duplicate
        # into the audit table.
        if changed_fields:
            self.audit.record(
                actor_id=user.id,
                action="LETTER_UPDATED",
                entity_type="Letter",
                entity_id=letter.id,
                new_values={"changed_fields": changed_fields},
            )

        # Designation changes get their own, higher-priority event with
        # a targeted old/new id pair, mirroring
        # LETTER_CLASSIFICATION_CHANGED/LETTER_CATEGORY_CHANGED below.
        if designation_id is not None and designation_id != old_designation_id:
            self.audit.record(
                actor_id=user.id,
                action="LETTER_DESIGNATION_CHANGED",
                entity_type="Letter",
                entity_id=letter.id,
                old_values={
                    "designation_id": str(old_designation_id) if old_designation_id else None
                },
                new_values={"designation_id": str(designation_id)},
            )

        # Classification/category changes get their own, higher-priority
        # events with targeted old/new id pairs (§11) — classification in
        # particular can alter who is even allowed to see the letter.
        if classification_id is not None and classification_id != old_classification_id:
            self.audit.record(
                actor_id=user.id,
                action="LETTER_CLASSIFICATION_CHANGED",
                entity_type="Letter",
                entity_id=letter.id,
                old_values={
                    "classification_id": str(old_classification_id)
                    if old_classification_id
                    else None
                },
                new_values={"classification_id": str(classification_id)},
            )
        if category_id is not None and category_id != old_category_id:
            self.audit.record(
                actor_id=user.id,
                action="LETTER_CATEGORY_CHANGED",
                entity_type="Letter",
                entity_id=letter.id,
                old_values={"category_id": str(old_category_id) if old_category_id else None},
                new_values={"category_id": str(category_id)},
            )

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
        was_already_archived = letter.status == LetterStatus.ARCHIVED
        self.letters.update_status(letter, LetterStatus.ARCHIVED)
        self.session.flush()

        # Only audit a real transition — re-archiving an already-ARCHIVED
        # letter is a no-op (idempotent, per this method's own docstring)
        # and shouldn't produce a redundant trail entry.
        if not was_already_archived:
            self.audit.record(
                actor_id=user.id,
                action="LETTER_ARCHIVED",
                entity_type="Letter",
                entity_id=letter.id,
                old_values={"status": "ACTIVE"},
                new_values={"status": "ARCHIVED"},
            )

        self.session.commit()
        self.session.refresh(letter)
        return letter
