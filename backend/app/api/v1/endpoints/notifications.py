"""Notification retrieval/read-state endpoints (Phase 4E implementation).

Every route uses `get_current_user` only — there is no role restriction,
because a notification's entire access rule is per-account ownership
(docs/architecture/audit-notifications.md §17), not department/role
scoping. Every route is unconditionally scoped to `current_user` for
every role including `SYSTEM_ADMIN` — there is no `recipient_user_id`
query parameter anywhere, unlike `GET /api/v1/letters`'s
`department_id` (meaningful for `SYSTEM_ADMIN` specifically); a
notification has no equivalent "browse on someone else's behalf" use
case for any role.
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.database.session import get_db
from app.models.user import User
from app.schemas.notification import NotificationListResponse, NotificationResponse, UnreadCountResponse
from app.services.exceptions import NotificationNotFoundError
from app.services.notification_service import DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE, NotificationService

router = APIRouter(prefix="/notifications", tags=["notifications"])


def _not_found() -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found.")


@router.get(
    "",
    response_model=NotificationListResponse,
    summary="List your own notifications, newest first",
)
def list_notifications(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> NotificationListResponse:
    service = NotificationService(db)
    items, total = service.list_notifications(user=current_user, page=page, page_size=page_size)
    total_pages = (total + page_size - 1) // page_size if total else 0
    return NotificationListResponse(
        items=items, total=total, page=page, page_size=page_size, total_pages=total_pages
    )


@router.get(
    "/unread-count",
    response_model=UnreadCountResponse,
    summary="Count of your own unread notifications",
)
def unread_count(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> UnreadCountResponse:
    service = NotificationService(db)
    return UnreadCountResponse(unread_count=service.unread_count(user=current_user))


@router.patch(
    "/{notification_id}/read",
    response_model=NotificationResponse,
    summary="Mark one of your own notifications read — idempotent",
)
def mark_read(
    notification_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> NotificationResponse:
    service = NotificationService(db)
    try:
        return service.mark_read(notification_id, user=current_user)
    except NotificationNotFoundError:
        raise _not_found()


@router.patch(
    "/read-all",
    summary="Mark all of your own notifications read",
)
def mark_all_read(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    service = NotificationService(db)
    count = service.mark_all_read(user=current_user)
    return {"marked_read": count}
