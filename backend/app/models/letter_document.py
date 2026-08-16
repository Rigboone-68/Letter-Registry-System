"""LetterDocument — metadata for one file attached to a Letter.

Separate from Letter because a letter may eventually have multiple
attachments (Section 9) — a single `storage_path` column on Letter would cap
every letter at exactly one document.

This table stores metadata ONLY. No binary content is stored in PostgreSQL;
`storage_path` is a relative/logical path into `storage/letters/` (see
STORAGE_PATH in app/core/config.py), resolved by a future storage service —
never a machine-specific absolute path, and never interpreted by the model
layer itself. Upload handling, path generation, and file I/O are explicitly
out of scope for this phase.

`document_type` is a plain string, not an enum: the set of meaningful
document types isn't confirmed yet, and unlike role/status (where an invalid
value is a security-relevant bug) an unrecognized document type here is
harmless.
"""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import BigInteger, DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.models.mixins import UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.letter import Letter
    from app.models.user import User


class LetterDocument(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "letter_documents"

    # CASCADE is intentional here, unlike every FK pointing at Department/
    # Category/Classification/User in this schema: a LetterDocument has no
    # meaning without its parent Letter (it is a true owned child, not a
    # shared reference entity), and Letters are never physically deleted in
    # normal operation — so this only fires on deliberate manual cleanup.
    letter_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("letters.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    document_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    original_filename: Mapped[str] = mapped_column(String(500), nullable=False)
    storage_path: Mapped[str] = mapped_column(String(1000), nullable=False)
    file_size: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    mime_type: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    uploaded_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    letter: Mapped["Letter"] = relationship(back_populates="documents")
    uploaded_by_user: Mapped["User"] = relationship(
        back_populates="documents_uploaded", foreign_keys=[uploaded_by]
    )

    def __repr__(self) -> str:  # pragma: no cover - debug convenience only
        return f"<LetterDocument id={self.id} letter_id={self.letter_id} filename={self.original_filename!r}>"
