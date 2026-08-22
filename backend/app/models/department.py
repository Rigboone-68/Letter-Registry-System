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
`letters.recipient_department_id` (Phase 4B rename of the old
`department_id`; `letters.source_department_id` is RESTRICT-protected too
but has no collection here — see `Letter.letters`' own comment). Without
it, the ORM's default behavior is to try to
set each child's foreign key to NULL before the delete, which — for `users`
specifically — trips the unrelated `ck_users_role_department_pairing` CHECK
constraint instead of ever reaching the FK restriction, producing a
confusing error and, if `users.department_id` were ever nullable without
that constraint, could have silently orphaned rows instead of blocking the
delete. See docs/database/schema.md, "ORM deletion behavior" for the full
reasoning and `tests/integration/test_models.py` for the regression tests.

`name`/`code` use explicit, named `UniqueConstraint`s in `__table_args__`
rather than the `unique=True` column shorthand (found and fixed in Phase
3B.2). The shorthand lets SQLAlchemy auto-name the constraint however the
DDL backend prefers — `Base.metadata.create_all()` (used to build the
`lrs_test` schema for the test suite) and the Alembic migration that built
the real schema produced *different* auto-generated names for the same
constraint before this fix, even though both point at the same column. That
was harmless until `app/services/department_service.py` started reading
`IntegrityError.orig.diag.constraint_name` to report *which* field
conflicted — at which point it broke, but only against the test database,
since `lrs_dev` already had the migration's explicitly-named constraint.
Naming both here matches the migration's names (`uq_departments_name`,
`uq_departments_code`) exactly, so `create_all()` and the migration now
produce byte-identical DDL and `alembic check` still reports zero drift.
The same latent inconsistency exists on `categories.name` and
`classifications.name` (both still use the `unique=True` shorthand) — not
fixed here because nothing in this phase depends on their constraint
names; the same technique applies if a future phase ever needs it there.
"""

from typing import List, Optional

from sqlalchemy import String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.models.enums import ActiveStatus, active_status_enum
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class Department(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "departments"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    # Nullable + unique: PostgreSQL treats multiple NULLs as distinct, so any
    # number of departments may go without a code until one is confirmed.
    code: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    status: Mapped[ActiveStatus] = mapped_column(
        active_status_enum, nullable=False, default=ActiveStatus.ACTIVE, index=True
    )

    __table_args__ = (
        UniqueConstraint("name", name="uq_departments_name"),
        UniqueConstraint("code", name="uq_departments_code"),
    )

    users: Mapped[List["User"]] = relationship(
        back_populates="department", passive_deletes="all"
    )
    user_authorizations: Mapped[List["UserAuthorization"]] = relationship(
        back_populates="department", passive_deletes="all"
    )
    # Recipient side only — `Letter.source_department` (Phase 4B) is a
    # separate, one-directional relationship with no corresponding
    # collection here; a department's role as a letter's *source* carries
    # no isolation/ownership meaning, unlike being its recipient. See
    # docs/architecture/letter-registry.md §2.1.
    letters: Mapped[List["Letter"]] = relationship(
        back_populates="recipient_department",
        foreign_keys="Letter.recipient_department_id",
        passive_deletes="all",
    )

    def __repr__(self) -> str:  # pragma: no cover - debug convenience only
        return f"<Department id={self.id} name={self.name!r} status={self.status}>"
