"""Category — a subject-matter grouping for letters (e.g. Budget, HR, Legal).

Managed by System Admin. The final category list is not confirmed — nothing
in the application is allowed to hard-code category names, and no example
categories are seeded by this migration (Section 6).

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
