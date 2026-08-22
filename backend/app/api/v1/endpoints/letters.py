"""Letter registry endpoints.

Role scope (docs/architecture/letter-registry.md §9, an explicit
IMPLEMENTATION DECISION):

* `POST /letters` (create) — `require_user_or_admin`. SYSTEM_ADMIN is
  excluded here, not by a new role check, but because it structurally has
  no `department_id` to record a letter against (the same fact that
  already keeps it out of every other department-scoped write in this
  project).
* Every other route — `get_current_user` only (any authenticated,
  ACTIVE account), because the *real* authorization decision is made
  inside `app/services/letter_service.py` via
  `app/services/authorization.py:assert_letter_access` — department
  isolation for USER/ADMIN, full access for SYSTEM_ADMIN (explicit
  instruction: "System Administrator must retain complete administrative
  control"), narrowed by the classified-access boundary for a USER who
  isn't the letter's own recorder. Gating a second time at the dependency
  layer would either duplicate that logic or contradict it; this project
  reuses one check, not two competing ones. This is not "no additional
  role" — it's the same one-check-not-two principle already used for
  User management's cross-department 404s (Phase 3B.4): the dependency
  establishes identity, the service decides visibility.

`recorded_by` and `recipient_department_id` are always derived from
`current_user` — neither has a field on `LetterCreate` at all.

`reference_number` has no uniqueness handling here — there is no
database constraint to violate (removed by migration `c887ab35e4a3`, a
Phase 4B hardening finding; see `app/models/letter.py`). Duplicate
reference numbers are currently accepted; the actual uniqueness scope
remains PENDING BUSINESS CLARIFICATION — see
docs/architecture/letter-registry.md §2.3/§12.
"""

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_user_or_admin
from app.database.session import get_db
from app.models.enums import LetterStatus
from app.models.letter import Letter
from app.models.user import User
from app.schemas.letter import LetterCreate, LetterListResponse, LetterResponse, LetterUpdate
from app.services.exceptions import (
    CategoryNotActiveError,
    CategoryNotFoundError,
    ClassificationNotActiveError,
    ClassificationNotFoundError,
    DepartmentAccessDeniedError,
    LetterNotFoundError,
    SourceDepartmentNotActiveError,
    SourceDepartmentNotFoundError,
)
from app.services.letter_service import LetterService

router = APIRouter(prefix="/letters", tags=["letters"])


def _not_found() -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Letter not found.")


def _forbidden() -> HTTPException:
    # Mirrors app/api/deps.py:_FORBIDDEN_ERROR — same generic 403 for a
    # department-authorization failure raised from the service layer
    # (the caller's own department is inactive) rather than a FastAPI
    # dependency. See app/services/letter_service.py:create_letter.
    return HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="You do not have permission to perform this action.",
    )


def _handle_reference_data_errors(exc: Exception) -> HTTPException:
    if isinstance(exc, SourceDepartmentNotFoundError):
        return HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Source department not found."
        )
    if isinstance(exc, SourceDepartmentNotActiveError):
        return HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Source department is not ACTIVE."
        )
    if isinstance(exc, CategoryNotFoundError):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found.")
    if isinstance(exc, CategoryNotActiveError):
        return HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Category is not ACTIVE.")
    if isinstance(exc, ClassificationNotFoundError):
        return HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Classification not found."
        )
    if isinstance(exc, ClassificationNotActiveError):
        return HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Classification is not ACTIVE."
        )
    raise exc  # pragma: no cover - defensive, every caller passes a handled type


@router.post(
    "",
    response_model=LetterResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Record a new letter in your own department (USER or ADMIN only)",
)
def create_letter(
    payload: LetterCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_user_or_admin),
) -> Letter:
    service = LetterService(db)
    try:
        return service.create_letter(
            recorder=current_user,
            reference_number=payload.reference_number,
            source_name=payload.source_name,
            source_department_id=payload.source_department_id,
            source_location=payload.source_location,
            sender_name=payload.sender_name,
            sender_designation=payload.sender_designation,
            sender_department=payload.sender_department,
            sender_address=payload.sender_address,
            subject=payload.subject,
            reason=payload.reason,
            category_id=payload.category_id,
            classification_id=payload.classification_id,
            received_at=payload.received_at,
            text_content=payload.text_content,
        )
    except DepartmentAccessDeniedError:
        raise _forbidden()
    except (
        SourceDepartmentNotFoundError,
        SourceDepartmentNotActiveError,
        CategoryNotFoundError,
        CategoryNotActiveError,
        ClassificationNotFoundError,
        ClassificationNotActiveError,
    ) as exc:
        raise _handle_reference_data_errors(exc)


@router.get(
    "",
    response_model=LetterListResponse,
    summary="List letters visible to you — own department (USER/ADMIN) or all (SYSTEM_ADMIN)",
)
def list_letters(
    department_id: Optional[uuid.UUID] = Query(
        default=None, description="SYSTEM_ADMIN only — ignored for USER/ADMIN"
    ),
    status_filter: Optional[LetterStatus] = Query(default=None, alias="status"),
    category_id: Optional[uuid.UUID] = Query(default=None),
    classification_id: Optional[uuid.UUID] = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> LetterListResponse:
    service = LetterService(db)
    letters = service.list_letters(
        user=current_user,
        department_id=department_id,
        status_filter=status_filter,
        category_id=category_id,
        classification_id=classification_id,
    )
    return LetterListResponse(items=letters, total=len(letters))


@router.get(
    "/{letter_id}",
    response_model=LetterResponse,
    summary="Get a single letter by id, subject to department/classified access",
)
def get_letter(
    letter_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Letter:
    service = LetterService(db)
    try:
        return service.get_letter(letter_id, user=current_user)
    except LetterNotFoundError:
        raise _not_found()


@router.patch(
    "/{letter_id}",
    response_model=LetterResponse,
    summary="Update a letter, subject to department/classified access",
)
def update_letter(
    letter_id: uuid.UUID,
    payload: LetterUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Letter:
    service = LetterService(db)
    try:
        return service.update_letter(
            letter_id,
            user=current_user,
            reference_number=payload.reference_number,
            source_name=payload.source_name,
            source_department_id=payload.source_department_id,
            source_location=payload.source_location,
            sender_name=payload.sender_name,
            sender_designation=payload.sender_designation,
            sender_department=payload.sender_department,
            sender_address=payload.sender_address,
            subject=payload.subject,
            reason=payload.reason,
            category_id=payload.category_id,
            classification_id=payload.classification_id,
            received_at=payload.received_at,
            text_content=payload.text_content,
        )
    except LetterNotFoundError:
        raise _not_found()
    except (
        SourceDepartmentNotFoundError,
        SourceDepartmentNotActiveError,
        CategoryNotFoundError,
        CategoryNotActiveError,
        ClassificationNotFoundError,
        ClassificationNotActiveError,
    ) as exc:
        raise _handle_reference_data_errors(exc)


@router.delete(
    "/{letter_id}",
    response_model=LetterResponse,
    summary="Archive a letter (soft-delete — never a physical DELETE), subject to department/classified access",
)
def archive_letter(
    letter_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Letter:
    service = LetterService(db)
    try:
        return service.archive_letter(letter_id, user=current_user)
    except LetterNotFoundError:
        raise _not_found()
