"""Designation management endpoints (Phase 5H).

Mirrors app/api/v1/endpoints/categories.py exactly, with one deliberate
authorization departure: `list_designations` depends on
`get_current_user` (any authenticated, ACTIVE account), **not**
`require_system_admin`. Every write endpoint below (`create`/`update`/
`activate`/`deactivate`) stays SYSTEM_ADMIN-only, matching the approved
business decision exactly ("SYSTEM_ADMIN manages Designations. USER and
ADMIN can read the active Designation list.").

This is not an oversight or an inconsistency with Category/
Classification — it is the direct, documented fix for the access gap
those two resources' own SYSTEM_ADMIN-only list endpoints already
created (docs/architecture/frontend.md §36, docs/architecture/
source-designation.md §0.1/§11): USER/ADMIN are the only roles that can
ever call `POST /letters`, so if this list endpoint were SYSTEM_ADMIN-
only too, neither role could ever populate the Designation dropdown on
the Letter form — the one thing this resource exists to support.
"""

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_system_admin
from app.database.session import get_db
from app.models.designation import Designation
from app.models.enums import ActiveStatus
from app.models.user import User
from app.schemas.designation import (
    DesignationCreate,
    DesignationListResponse,
    DesignationResponse,
    DesignationUpdate,
)
from app.services.designation_service import DesignationService
from app.services.exceptions import DesignationNotFoundError, DuplicateDesignationError

router = APIRouter(prefix="/designations", tags=["designations"])


def _not_found() -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Designation not found.")


def _duplicate() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail="A designation with this name already exists.",
    )


@router.post(
    "",
    response_model=DesignationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a designation (SYSTEM_ADMIN only)",
)
def create_designation(
    payload: DesignationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_system_admin),
) -> Designation:
    service = DesignationService(db)
    try:
        return service.create_designation(name=payload.name, actor_id=current_user.id)
    except DuplicateDesignationError:
        raise _duplicate()


@router.get(
    "",
    response_model=DesignationListResponse,
    summary="List designations, optionally filtered by status (any authenticated role)",
)
def list_designations(
    status_filter: Optional[ActiveStatus] = Query(default=None, alias="status"),
    db: Session = Depends(get_db),
    _current_user: User = Depends(get_current_user),
) -> DesignationListResponse:
    service = DesignationService(db)
    designations = service.list_designations(status_filter=status_filter)
    return DesignationListResponse(items=designations, total=len(designations))


@router.get(
    "/{designation_id}",
    response_model=DesignationResponse,
    summary="Get a single designation by id (SYSTEM_ADMIN only)",
)
def get_designation(
    designation_id: uuid.UUID,
    db: Session = Depends(get_db),
    _current_user: User = Depends(require_system_admin),
) -> Designation:
    service = DesignationService(db)
    try:
        return service.get_designation(designation_id)
    except DesignationNotFoundError:
        raise _not_found()


@router.patch(
    "/{designation_id}",
    response_model=DesignationResponse,
    summary="Rename a designation (SYSTEM_ADMIN only)",
)
def update_designation(
    designation_id: uuid.UUID,
    payload: DesignationUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_system_admin),
) -> Designation:
    service = DesignationService(db)
    try:
        return service.update_designation(
            designation_id, name=payload.name, actor_id=current_user.id
        )
    except DesignationNotFoundError:
        raise _not_found()
    except DuplicateDesignationError:
        raise _duplicate()


@router.post(
    "/{designation_id}/activate",
    response_model=DesignationResponse,
    summary="Activate a designation — idempotent (SYSTEM_ADMIN only)",
)
def activate_designation(
    designation_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_system_admin),
) -> Designation:
    service = DesignationService(db)
    try:
        return service.activate_designation(designation_id, actor_id=current_user.id)
    except DesignationNotFoundError:
        raise _not_found()


@router.post(
    "/{designation_id}/deactivate",
    response_model=DesignationResponse,
    summary="Deactivate a designation — idempotent (SYSTEM_ADMIN only)",
)
def deactivate_designation(
    designation_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_system_admin),
) -> Designation:
    service = DesignationService(db)
    try:
        return service.deactivate_designation(designation_id, actor_id=current_user.id)
    except DesignationNotFoundError:
        raise _not_found()
