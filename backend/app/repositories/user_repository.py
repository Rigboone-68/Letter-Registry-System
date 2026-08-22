"""Data access for User rows.

Every lookup by email goes through `func.lower(User.email)` to match the
database's own case-insensitive unique index (`uq_users_email_lower`) — see
app/utils/email.py. Callers are expected to pass an already-normalized
email (via `normalize_email`); this repository does not normalize on your
behalf, so the same value is guaranteed to match what was stored.

`find_admin_by_id`/`list_admins`/`update_status`/`update_department`
(Phase 3B.3) live here rather than in a new, separate repository — the
brief's own preference, and there's no real duplication to avoid: these
are still just queries and attribute-sets against `User`, the same table
every other method here already owns.
"""

import uuid
from typing import List, Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.enums import UserRole, UserStatus
from app.models.user import User


class UserRepository:
    def __init__(self, session: Session):
        self.session = session

    def find_by_email(self, normalized_email: str) -> Optional[User]:
        stmt = select(User).where(func.lower(User.email) == normalized_email)
        return self.session.execute(stmt).scalar_one_or_none()

    def find_by_id(self, user_id: uuid.UUID) -> Optional[User]:
        return self.session.get(User, user_id)

    def count_active_system_admins(self) -> int:
        stmt = (
            select(func.count())
            .select_from(User)
            .where(User.role == UserRole.SYSTEM_ADMIN, User.status == UserStatus.ACTIVE)
        )
        return self.session.execute(stmt).scalar_one()

    def create(
        self,
        *,
        full_name: str,
        email: str,
        password_hash: str,
        role: UserRole,
        department_id: Optional[uuid.UUID],
        status: UserStatus,
    ) -> User:
        user = User(
            full_name=full_name,
            email=email,
            password_hash=password_hash,
            role=role,
            department_id=department_id,
            status=status,
        )
        self.session.add(user)
        return user

    def find_admin_by_id(self, user_id: uuid.UUID) -> Optional[User]:
        """`None` both when no such `User` row exists at all, and when one
        exists but isn't role `ADMIN` — see
        app/services/exceptions.py:AdminNotFoundError for why the two are
        deliberately indistinguishable to a caller."""
        user = self.session.get(User, user_id)
        if user is None or user.role != UserRole.ADMIN:
            return None
        return user

    def list_admins(
        self,
        *,
        department_id: Optional[uuid.UUID] = None,
        status_filter: Optional[UserStatus] = None,
    ) -> List[User]:
        stmt = select(User).where(User.role == UserRole.ADMIN).order_by(User.created_at.asc())
        if department_id is not None:
            stmt = stmt.where(User.department_id == department_id)
        if status_filter is not None:
            stmt = stmt.where(User.status == status_filter)
        return list(self.session.execute(stmt).scalars().all())

    def update_status(self, user: User, status: UserStatus) -> None:
        user.status = status

    def update_department(self, user: User, department_id: uuid.UUID) -> None:
        user.department_id = department_id
