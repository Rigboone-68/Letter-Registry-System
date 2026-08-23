"""Response contracts for `Notification`.

No request schema exists for creating a notification — generation is
always server-side, triggered by a business event (Phase 4E: Letter
registration only), never a client-supplied payload. There is also no
`recipient_user_id` field anywhere a client could set — every endpoint
(`app/api/v1/endpoints/notifications.py`) derives it from
`current_user`, the same "no field for it, not just an ignored one"
discipline `LetterCreate`/`DocumentResponse` already established.
"""

import uuid
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict


class NotificationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    letter_id: Optional[uuid.UUID]
    notification_type: str
    message: str
    is_read: bool
    created_at: datetime
    read_at: Optional[datetime]


class NotificationListResponse(BaseModel):
    """Same `{"items": [...], "total": N}`-plus-pagination-metadata shape
    `LetterListResponse` established in Phase 4C."""

    items: List[NotificationResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class UnreadCountResponse(BaseModel):
    unread_count: int
