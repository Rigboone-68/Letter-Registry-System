"""Category — a subject-matter grouping for letters.

Managed by System Admin. Phase 4B finalized the V1 category list as
exactly three — General Letter, Notification, Office Order — seeded by
migration 48ec742d9e8f as ordinary rows through this same table (no
schema change was needed; this table was already structurally suitable —
see docs/architecture/letter-registry.md §2.4/§7). "Budget", floated as a
Category example during Phase 2 requirements-gathering, was explicitly
confirmed *not* to be one. Nothing about the three seeded rows is
special-cased or hard-coded in application code — a System Admin manages
them through the same CRUD as any category, current or future.

Never physically deleted: `status` moves to INACTIVE so that Letters already
tagged with a retired category keep a valid, readable reference instead of a
dangling foreign key or a silently blanked-out field.
"""

from typing import List, Optional

from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.models.enums import ActiveStatus, active_status_enum
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class Category(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "categories"

    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[ActiveStatus] = mapped_column(
        active_status_enum, nullable=False, default=ActiveStatus.ACTIVE, index=True
    )

    # passive_deletes="all": defers to the database's ON DELETE RESTRICT on
    # letters.category_id instead of the ORM trying to null it out first —
    # see docs/database/schema.md, "ORM deletion behavior".
    letters: Mapped[List["Letter"]] = relationship(
        back_populates="category", passive_deletes="all"
    )

    def __repr__(self) -> str:  # pragma: no cover - debug convenience only
        return f"<Category id={self.id} name={self.name!r}>"
