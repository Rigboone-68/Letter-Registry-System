"""Department management endpoints — SYSTEM_ADMIN only.

Endpoints stay thin — request validation is the schema's job
(app/schemas/department.py), business rules are the service's job
(app/services/department_service.py); this module only translates
service-layer exceptions into HTTP responses, the same division of
responsibility as app/api/v1/endpoints/auth.py.

Every route depends on `require_system_admin` (app/api/deps.py, Phase
3B.1) — ADMIN and USER both receive a `403` with the same generic message
every other authorization failure in this codebase uses (see
docs/architecture/authorization.md, "Error behavior"); an unauthenticated
caller receives `401` from `get_current_user` before role is ever checked.
"""

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import require_system_admin
from app.database.session import get_db
from app.models.department import Department
from app.models.enums import ActiveStatus
from app.models.user import User
from app.schemas.department import (
    DepartmentCreate,
    DepartmentListResponse,
    DepartmentResponse,
    DepartmentUpdate,
)
from app.services.department_service import DepartmentService
from app.services.exceptions import (
    DepartmentNotFoundError,
    DuplicateDepartmentCodeError,
    DuplicateDepartmentNameError,
)

router = APIRouter(prefix="/departments", tags=["departments"])


def _not_found() -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Department not found.")


@router.post(
    "",
    response_model=DepartmentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a department (SYSTEM_ADMIN only)",
)
def create_department(
    payload: DepartmentCreate,
    db: Session = Depends(get_db),
    _current_user: User = Depends(require_system_admin),
) -> Department:
    service = DepartmentService(db)
    try:
        return service.create_department(name=payload.name, code=payload.code)
    except DuplicateDepartmentNameError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A department with this name already exists.",
        )
    except DuplicateDepartmentCodeError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A department with this code already exists.",
        )


@router.get(
    "",
    response_model=DepartmentListResponse,
    summary="List departments, optionally filtered by status (SYSTEM_ADMIN only)",
)
def list_departments(
    status_filter: Optional[ActiveStatus] = Query(default=None, alias="status"),
    db: Session = Depends(get_db),
    _current_user: User = Depends(require_system_admin),
) -> DepartmentListResponse:
    service = DepartmentService(db)
    departments = service.list_departments(status_filter=status_filter)
    return DepartmentListResponse(items=departments, total=len(departments))


@router.get(
    "/{department_id}",
    response_model=DepartmentResponse,
    summary="Get a single department by id (SYSTEM_ADMIN only)",
)
def get_department(
    department_id: uuid.UUID,
    db: Session = Depends(get_db),
    _current_user: User = Depends(require_system_admin),
) -> Department:
    service = DepartmentService(db)
    try:
        return service.get_department(department_id)
    except DepartmentNotFoundError:
        raise _not_found()


@router.patch(
    "/{department_id}",
    response_model=DepartmentResponse,
    summary="Update a department's name/code (SYSTEM_ADMIN only)",
)
def update_department(
    department_id: uuid.UUID,
    payload: DepartmentUpdate,
    db: Session = Depends(get_db),
    _current_user: User = Depends(require_system_admin),
) -> Department:
    service = DepartmentService(db)
    try:
        return service.update_department(department_id, name=payload.name, code=payload.code)
    except DepartmentNotFoundError:
        raise _not_found()
    except DuplicateDepartmentNameError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A department with this name already exists.",
        )
    except DuplicateDepartmentCodeError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A department with this code already exists.",
        )


@router.post(
    "/{department_id}/activate",
    response_model=DepartmentResponse,
    summary="Activate a department — idempotent (SYSTEM_ADMIN only)",
)
def activate_department(
    department_id: uuid.UUID,
    db: Session = Depends(get_db),
    _current_user: User = Depends(require_system_admin),
) -> Department:
    service = DepartmentService(db)
    try:
        return service.activate_department(department_id)
    except DepartmentNotFoundError:
        raise _not_found()


@router.post(
    "/{department_id}/deactivate",
    response_model=DepartmentResponse,
    summary="Deactivate a department — idempotent (SYSTEM_ADMIN only)",
)
def deactivate_department(
    department_id: uuid.UUID,
    db: Session = Depends(get_db),
    _current_user: User = Depends(require_system_admin),
) -> Department:
    service = DepartmentService(db)
    try:
        return service.deactivate_department(department_id)
    except DepartmentNotFoundError:
        raise _not_found()
