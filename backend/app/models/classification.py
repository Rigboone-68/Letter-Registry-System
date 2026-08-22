"""Classification — a priority/sensitivity marker for letters, e.g. Important,
Classified, Routine.

Kept as its own table, separate from Category, because the two vary
independently: a letter's subject-matter grouping (Category) and its
priority/sensitivity (Classification) are orthogonal facts — a "Budget"
letter can be Routine or Classified, and merging them into one list would
force every category to be re-declared per priority level. Phase 4B
finalized that "Budget" is not a Category (see app/models/category.py);
it does not finalize Classification's exact value list, so nothing is
seeded here.

Managed by System Admin. S&IT has not confirmed final terminology for this
concept (the names "Important"/"Classified"/"Routine" used in requirements
gathering are examples only — see docs/PROJECT_STATUS.md). Nothing is seeded.

`restricts_access` (Phase 4B, migration 48ec742d9e8f) is the data-model
half of the classified-access authorization boundary — a letter whose
classification has this flag set must not be automatically visible to
every user who can otherwise access its recipient department (product
owner's own wording). See app/services/authorization.py:assert_letter_access
for the enforcement half, and docs/architecture/letter-registry.md §8 for
why this is a boolean flag (a single source of truth a System Admin sets
explicitly) rather than derived from `name` — no code anywhere
string-matches "Classified" to decide this. Defaults to `False`: a newly
created classification has no special access-control effect until a
System Admin explicitly opts it in.

Never physically deleted: `status` moves to INACTIVE so Letters already
tagged with a retired classification keep a valid reference.
"""

from typing import List, Optional

from sqlalchemy import Boolean, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.models.enums import ActiveStatus, active_status_enum
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class Classification(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "classifications"

    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[ActiveStatus] = mapped_column(
        active_status_enum, nullable=False, default=ActiveStatus.ACTIVE, index=True
    )
    restricts_access: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )

    # passive_deletes="all": defers to the database's ON DELETE RESTRICT on
    # letters.classification_id — see docs/database/schema.md, "ORM deletion
    # behavior".
    letters: Mapped[List["Letter"]] = relationship(
        back_populates="classification", passive_deletes="all"
    )

    def __repr__(self) -> str:  # pragma: no cover - debug convenience only
        return (
            f"<Classification id={self.id} name={self.name!r} "
            f"restricts_access={self.restricts_access}>"
        )
