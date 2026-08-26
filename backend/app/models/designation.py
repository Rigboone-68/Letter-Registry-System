"""Designation — a sender job title/role, e.g. Section Officer, Deputy
Director (Phase 5H).

System-wide master data, managed by System Admin, exactly like Category/
Classification — this model mirrors app/models/category.py's shape
directly. Deliberately has **no relationship to Department** — the
business decision is explicit that designations are not department-
specific (docs/architecture/source-designation.md §7).

`name` uniqueness is case-insensitive, a deliberate departure from
Category/Classification's plain case-sensitive `unique=True`: reusing
the exact functional-index technique `User.email` already uses
(`uq_users_email_lower`) — "Secretary"/"secretary"/" SECRETARY " must
not become separate rows. See docs/architecture/source-designation.md
§7 for why this project's own reference-data precedent doesn't apply
unchanged here (Category/Classification are a short, curated list set
once; Designations are added to "over time" under less careful
conditions).

Never physically deleted: `status` moves to INACTIVE so Letters already
carrying a `designation_id` pointing at a retired Designation keep a
valid, readable reference — see app/models/letter.py's own
`designation_id`/`sender_designation` docstring for the full historical-
integrity strategy (a new nullable FK alongside the existing, unchanged,
required `sender_designation` text snapshot).
"""

from typing import List

from sqlalchemy import Index, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.models.enums import ActiveStatus, active_status_enum
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class Designation(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "designations"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[ActiveStatus] = mapped_column(
        active_status_enum, nullable=False, default=ActiveStatus.ACTIVE, index=True
    )

    __table_args__ = (
        Index("uq_designations_name_lower", func.lower(name), unique=True),
    )

    # passive_deletes="all": defers to the database's ON DELETE RESTRICT
    # on letters.designation_id — see docs/database/schema.md, "ORM
    # deletion behavior".
    letters: Mapped[List["Letter"]] = relationship(
        back_populates="designation", passive_deletes="all"
    )

    def __repr__(self) -> str:  # pragma: no cover - debug convenience only
        return f"<Designation id={self.id} name={self.name!r} status={self.status}>"
