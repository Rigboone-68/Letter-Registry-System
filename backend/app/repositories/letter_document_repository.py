"""Data access for `LetterDocument` rows — the only code that queries
`LetterDocument`.

`find_by_id_and_letter` is deliberately scoped by *both* ids at once,
not looked up by `document_id` alone and checked afterward — the caller
(`app/services/document_service.py`) always already knows which Letter it
authorized (via `LetterService.get_letter`), so a document that exists
but belongs to a different letter is treated identically to one that
doesn't exist at all, the same enumeration-resistant shape
`LetterRepository`/`UserRepository` already use.
"""

import uuid
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.letter_document import LetterDocument


class LetterDocumentRepository:
    def __init__(self, session: Session):
        self.session = session

    def find_by_id_and_letter(
        self, document_id: uuid.UUID, letter_id: uuid.UUID
    ) -> Optional[LetterDocument]:
        stmt = select(LetterDocument).where(
            LetterDocument.id == document_id,
            LetterDocument.letter_id == letter_id,
        )
        return self.session.execute(stmt).scalar_one_or_none()

    def list_by_letter(self, letter_id: uuid.UUID) -> List[LetterDocument]:
        stmt = (
            select(LetterDocument)
            .where(LetterDocument.letter_id == letter_id)
            .order_by(LetterDocument.uploaded_at.asc())
        )
        return list(self.session.execute(stmt).scalars().all())

    def create(
        self,
        *,
        id: uuid.UUID,
        letter_id: uuid.UUID,
        original_filename: str,
        storage_path: str,
        file_size: int,
        mime_type: str,
        uploaded_by: uuid.UUID,
    ) -> LetterDocument:
        """`id` is supplied by the caller (`DocumentService`), not
        left to the model's default `uuid.uuid4()` — the document id must
        be known *before* the row is created, since it's also part of the
        server-controlled storage path
        (`app/services/document_storage.py:build_storage_path`), and the
        file must be written before this row is committed (write-then-
        commit ordering — docs/architecture/document-management.md
        §23)."""
        document = LetterDocument(
            id=id,
            letter_id=letter_id,
            original_filename=original_filename,
            storage_path=storage_path,
            file_size=file_size,
            mime_type=mime_type,
            uploaded_by=uploaded_by,
        )
        self.session.add(document)
        return document
