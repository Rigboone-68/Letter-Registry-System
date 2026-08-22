"""Classification management endpoints — SYSTEM_ADMIN only.

Mirrors app/api/v1/endpoints/categories.py, plus `restricts_access` on
create/update. No classification value is seeded by this phase — see
docs/architecture/letter-registry.md §2.5/§12.
"""

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import require_system_admin
from app.database.session import get_db
from app.models.classification import Classification
from app.models.enums import ActiveStatus
from app.models.user import User
from app.schemas.classification import (
    ClassificationCreate,
    ClassificationListResponse,
    ClassificationResponse,
    ClassificationUpdate,
)
from app.services.classification_service import ClassificationService
from app.services.exceptions import ClassificationNotFoundError, DuplicateClassificationError

router = APIRouter(prefix="/classifications", tags=["classifications"])


def _not_found() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND, detail="Classification not found."
    )


def _duplicate() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail="A classification with this name already exists.",
    )


@router.post(
    "",
    response_model=ClassificationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a classification (SYSTEM_ADMIN only)",
)
def create_classification(
    payload: ClassificationCreate,
    db: Session = Depends(get_db),
    _current_user: User = Depends(require_system_admin),
) -> Classification:
    service = ClassificationService(db)
    try:
        return service.create_classification(
            name=payload.name,
            description=payload.description,
            restricts_access=payload.restricts_access,
        )
    except DuplicateClassificationError:
        raise _duplicate()


@router.get(
    "",
    response_model=ClassificationListResponse,
    summary="List classifications, optionally filtered by status (SYSTEM_ADMIN only)",
)
def list_classifications(
    status_filter: Optional[ActiveStatus] = Query(default=None, alias="status"),
    db: Session = Depends(get_db),
    _current_user: User = Depends(require_system_admin),
) -> ClassificationListResponse:
    service = ClassificationService(db)
    classifications = service.list_classifications(status_filter=status_filter)
    return ClassificationListResponse(items=classifications, total=len(classifications))


@router.get(
    "/{classification_id}",
    response_model=ClassificationResponse,
    summary="Get a single classification by id (SYSTEM_ADMIN only)",
)
def get_classification(
    classification_id: uuid.UUID,
    db: Session = Depends(get_db),
    _current_user: User = Depends(require_system_admin),
) -> Classification:
    service = ClassificationService(db)
    try:
        return service.get_classification(classification_id)
    except ClassificationNotFoundError:
        raise _not_found()


@router.patch(
    "/{classification_id}",
    response_model=ClassificationResponse,
    summary="Update a classification's name/description/restricts_access (SYSTEM_ADMIN only)",
)
def update_classification(
    classification_id: uuid.UUID,
    payload: ClassificationUpdate,
    db: Session = Depends(get_db),
    _current_user: User = Depends(require_system_admin),
) -> Classification:
    service = ClassificationService(db)
    try:
        return service.update_classification(
            classification_id,
            name=payload.name,
            description=payload.description,
            restricts_access=payload.restricts_access,
        )
    except ClassificationNotFoundError:
        raise _not_found()
    except DuplicateClassificationError:
        raise _duplicate()


@router.post(
    "/{classification_id}/activate",
    response_model=ClassificationResponse,
    summary="Activate a classification — idempotent (SYSTEM_ADMIN only)",
)
def activate_classification(
    classification_id: uuid.UUID,
    db: Session = Depends(get_db),
    _current_user: User = Depends(require_system_admin),
) -> Classification:
    service = ClassificationService(db)
    try:
        return service.activate_classification(classification_id)
    except ClassificationNotFoundError:
        raise _not_found()


@router.post(
    "/{classification_id}/deactivate",
    response_model=ClassificationResponse,
    summary="Deactivate a classification — idempotent (SYSTEM_ADMIN only)",
)
def deactivate_classification(
    classification_id: uuid.UUID,
    db: Session = Depends(get_db),
    _current_user: User = Depends(require_system_admin),
) -> Classification:
    service = ClassificationService(db)
    try:
        return service.deactivate_classification(classification_id)
    except ClassificationNotFoundError:
        raise _not_found()
