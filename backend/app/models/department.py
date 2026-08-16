"""Department — a government department using LRS.

Departments are the isolation boundary the whole schema is built around
(see docs/architecture/overview.md, "Department isolation"). They are never
physically deleted: `status` moves to INACTIVE instead, so that historical
Users, UserAuthorizations, and Letters remain attached to a real row rather
than a dangling foreign key.

`code` is nullable because S&IT has not yet confirmed a departmental coding
convention — see docs/PROJECT_STATUS.md, "Pending Confirmation". No format is
assumed here; when the convention is confirmed, this column gains validation
at the service layer, not a schema change.

`passive_deletes="all"` on every relationship below tells SQLAlchemy not to
load these collections (or act on them if already loaded) when a Department
is deleted — it defers entirely to the database's `ON DELETE RESTRICT` on
`users.department_id` / `user_authorizations.department_id` /
`letters.department_id`. Without it, the ORM's default behavior is to try to
set each child's foreign key to NULL before the delete, which — for `users`
specifically — trips the unrelated `ck_users_role_department_pairing` CHECK
constraint instead of ever reaching the FK restriction, producing a
confusing error and, if `users.department_id` were ever nullable without
that constraint, could have silently orphaned rows instead of blocking the
delete. See docs/database/schema.md, "ORM deletion behavior" for the full
reasoning and `tests/integration/test_models.py` for the regression tests.
"""

from typing import List, Optional

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.models.enums import ActiveStatus, active_status_enum
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class Department(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "departments"

    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    # Nullable + unique: PostgreSQL treats multiple NULLs as distinct, so any
    # number of departments may go without a code until one is confirmed.
    code: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, unique=True)
    status: Mapped[ActiveStatus] = mapped_column(
        active_status_enum, nullable=False, default=ActiveStatus.ACTIVE, index=True
    )

    users: Mapped[List["User"]] = relationship(
        back_populates="department", passive_deletes="all"
    )
    user_authorizations: Mapped[List["UserAuthorization"]] = relationship(
        back_populates="department", passive_deletes="all"
    )
    letters: Mapped[List["Letter"]] = relationship(
        back_populates="department", passive_deletes="all"
    )

    def __repr__(self) -> str:  # pragma: no cover - debug convenience only
        return f"<Department id={self.id} name={self.name!r} status={self.status}>"
