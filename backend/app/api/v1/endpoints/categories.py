"""Category management endpoints — SYSTEM_ADMIN only.

Mirrors app/api/v1/endpoints/departments.py exactly. The three finalized
V1 categories (General Letter, Notification, Office Order) are seeded by
migration 48ec742d9e8f as ordinary rows, not created through this API and
not treated specially by it — this router is generic category CRUD, the
same as department CRUD is generic department CRUD.
"""

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import require_system_admin
from app.database.session import get_db
from app.models.category import Category
from app.models.enums import ActiveStatus
from app.models.user import User
from app.schemas.category import (
    CategoryCreate,
    CategoryListResponse,
    CategoryResponse,
    CategoryUpdate,
)
from app.services.category_service import CategoryService
from app.services.exceptions import CategoryNotFoundError, DuplicateCategoryError

router = APIRouter(prefix="/categories", tags=["categories"])


def _not_found() -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found.")


def _duplicate() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail="A category with this name already exists.",
    )


@router.post(
    "",
    response_model=CategoryResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a category (SYSTEM_ADMIN only)",
)
def create_category(
    payload: CategoryCreate,
    db: Session = Depends(get_db),
    _current_user: User = Depends(require_system_admin),
) -> Category:
    service = CategoryService(db)
    try:
        return service.create_category(name=payload.name, description=payload.description)
    except DuplicateCategoryError:
        raise _duplicate()


@router.get(
    "",
    response_model=CategoryListResponse,
    summary="List categories, optionally filtered by status (SYSTEM_ADMIN only)",
)
def list_categories(
    status_filter: Optional[ActiveStatus] = Query(default=None, alias="status"),
    db: Session = Depends(get_db),
    _current_user: User = Depends(require_system_admin),
) -> CategoryListResponse:
    service = CategoryService(db)
    categories = service.list_categories(status_filter=status_filter)
    return CategoryListResponse(items=categories, total=len(categories))


@router.get(
    "/{category_id}",
    response_model=CategoryResponse,
    summary="Get a single category by id (SYSTEM_ADMIN only)",
)
def get_category(
    category_id: uuid.UUID,
    db: Session = Depends(get_db),
    _current_user: User = Depends(require_system_admin),
) -> Category:
    service = CategoryService(db)
    try:
        return service.get_category(category_id)
    except CategoryNotFoundError:
        raise _not_found()


@router.patch(
    "/{category_id}",
    response_model=CategoryResponse,
    summary="Update a category's name/description (SYSTEM_ADMIN only)",
)
def update_category(
    category_id: uuid.UUID,
    payload: CategoryUpdate,
    db: Session = Depends(get_db),
    _current_user: User = Depends(require_system_admin),
) -> Category:
    service = CategoryService(db)
    try:
        return service.update_category(
            category_id, name=payload.name, description=payload.description
        )
    except CategoryNotFoundError:
        raise _not_found()
    except DuplicateCategoryError:
        raise _duplicate()


@router.post(
    "/{category_id}/activate",
    response_model=CategoryResponse,
    summary="Activate a category — idempotent (SYSTEM_ADMIN only)",
)
def activate_category(
    category_id: uuid.UUID,
    db: Session = Depends(get_db),
    _current_user: User = Depends(require_system_admin),
) -> Category:
    service = CategoryService(db)
    try:
        return service.activate_category(category_id)
    except CategoryNotFoundError:
        raise _not_found()


@router.post(
    "/{category_id}/deactivate",
    response_model=CategoryResponse,
    summary="Deactivate a category — idempotent (SYSTEM_ADMIN only)",
)
def deactivate_category(
    category_id: uuid.UUID,
    db: Session = Depends(get_db),
    _current_user: User = Depends(require_system_admin),
) -> Category:
    service = CategoryService(db)
    try:
        return service.deactivate_category(category_id)
    except CategoryNotFoundError:
        raise _not_found()
