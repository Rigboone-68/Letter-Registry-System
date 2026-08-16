"""Data access for User rows.

Every lookup by email goes through `func.lower(User.email)` to match the
database's own case-insensitive unique index (`uq_users_email_lower`) — see
app/utils/email.py. Callers are expected to pass an already-normalized
email (via `normalize_email`); this repository does not normalize on your
behalf, so the same value is guaranteed to match what was stored.
"""

import uuid
from typing import Optional

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
