"""Data access for UserAuthorization rows.

`find_and_lock_active` is the piece that makes signup race-safe (brief
§13): it selects the oldest matching authorization with `SELECT ... FOR
UPDATE`, taking a row lock inside the caller's transaction. A second,
concurrent signup attempt for the same email blocks on that lock until the
first transaction commits or rolls back — at which point it re-evaluates
the same WHERE clause and finds either nothing (already consumed) or a
different row (if more than one active authorization exists for that
email), rather than racing to update the same row twice. This is why
`app/services/auth_service.py` does not do a plain "check status, then
update" — the check and the lock happen together, atomically, in one
statement.
"""

from typing import Optional

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models.enums import AuthorizationStatus
from app.models.user_authorization import UserAuthorization


class UserAuthorizationRepository:
    def __init__(self, session: Session):
        self.session = session

    def find_and_lock_active(self, normalized_email: str) -> Optional[UserAuthorization]:
        stmt = (
            select(UserAuthorization)
            .where(
                func.lower(UserAuthorization.email) == normalized_email,
                UserAuthorization.status == AuthorizationStatus.ACTIVE,
                or_(
                    UserAuthorization.expires_at.is_(None),
                    UserAuthorization.expires_at > func.now(),
                ),
            )
            .order_by(UserAuthorization.created_at.asc())
            .limit(1)
            .with_for_update()
        )
        return self.session.execute(stmt).scalar_one_or_none()

    def mark_used(self, authorization: UserAuthorization) -> None:
        authorization.status = AuthorizationStatus.USED
