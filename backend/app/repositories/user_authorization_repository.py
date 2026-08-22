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

`find_and_lock_active` deliberately does **not** filter by `purpose`
(Phase 3B.3) — it can't: at signup time the system doesn't yet know
whether the caller is a USER or ADMIN candidate; that's exactly what the
found row's own `purpose` tells it (see `AuthService.signup`). Filtering by
a caller-supplied purpose isn't possible here, and searching across all
purposes with the existing "oldest wins" tie-break (unchanged from Phase
3A) is the only design that actually fits the described signup flow.

`find_unresolved` (Phase 3B.3, used only when *creating* a new
authorization, never at signup) intentionally does not lock — the race it
would guard against (two System Admins simultaneously authorizing the same
email) is far lower-stakes than signup consumption: the worst case is two
ACTIVE authorization rows for one email, which `find_and_lock_active`
already resolves safely (picks one, locks it, the other remains unused).
"""

from typing import Optional
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models.enums import AuthorizationPurpose, AuthorizationStatus
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

    def find_unresolved(
        self, normalized_email: str, purpose: AuthorizationPurpose
    ) -> Optional[UserAuthorization]:
        """Is there a currently-consumable authorization (ACTIVE status,
        not expired) for this email/purpose already? Deliberately the same
        "not expired" condition as `find_and_lock_active` — an authorization
        whose `expires_at` has passed can never be consumed regardless of
        its `status` still reading `ACTIVE` (nothing flips status on
        expiry), so treating it as still "unresolved" would block
        re-authorizing an email forever with no way to clear it (there is
        no revoke endpoint in this phase). See
        docs/architecture/admin-management.md, "Known limitations"."""
        stmt = select(UserAuthorization).where(
            func.lower(UserAuthorization.email) == normalized_email,
            UserAuthorization.purpose == purpose,
            UserAuthorization.status == AuthorizationStatus.ACTIVE,
            or_(
                UserAuthorization.expires_at.is_(None),
                UserAuthorization.expires_at > func.now(),
            ),
        )
        return self.session.execute(stmt).scalars().first()

    def create(
        self,
        *,
        email: str,
        department_id: UUID,
        authorized_by: UUID,
        purpose: AuthorizationPurpose,
    ) -> UserAuthorization:
        authorization = UserAuthorization(
            email=email,
            department_id=department_id,
            authorized_by=authorized_by,
            purpose=purpose,
            status=AuthorizationStatus.ACTIVE,
        )
        self.session.add(authorization)
        return authorization

    def mark_used(self, authorization: UserAuthorization) -> None:
        authorization.status = AuthorizationStatus.USED
