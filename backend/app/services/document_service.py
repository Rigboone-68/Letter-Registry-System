"""Document upload/retrieval business logic (Phase 4D implementation).

Implements the architecture approved in
docs/architecture/document-management.md: storage-path safety (§5-7),
layered validation (§8-9), the letter-first authorization chain (§16-17
— every operation resolves and authorizes the parent Letter via
`LetterService.get_letter` before touching a document, never a parallel
check), write-then-commit-with-compensation transaction handling (§23),
and the explicit no-deletion policy (§14: nothing in this module removes
a document; §13/§19: "replacement" is simply calling `upload_document`
again — the prior document row and file are untouched).
"""

import uuid
from typing import List

from sqlalchemy.orm import Session

from app.models.letter import Letter
from app.models.letter_document import LetterDocument
from app.models.user import User
from app.repositories.letter_document_repository import LetterDocumentRepository
from app.services.audit_service import AuditService
from app.services.document_storage import build_storage_path, delete_document_file, write_document_file
from app.services.document_validation import validate_upload
from app.services.exceptions import DocumentNotFoundError
from app.services.letter_service import LetterService


class DocumentService:
    def __init__(self, session: Session):
        self.session = session
        self.documents = LetterDocumentRepository(session)
        self.letters = LetterService(session)
        self.audit = AuditService(session)

    def _get_letter_for_access(self, letter_id: uuid.UUID, *, user: User) -> Letter:
        """Reuses `LetterService.get_letter` rather than a parallel
        check — it already collapses "doesn't exist"/"wrong department"/
        "classified and inaccessible" into one `LetterNotFoundError`.
        This *is* the letter-first authorization chain
        (docs/architecture/document-management.md §16-17);
        `DocumentService` has no department/classification logic of its
        own to duplicate it with."""
        return self.letters.get_letter(letter_id, user=user)

    def upload_document(
        self,
        letter_id: uuid.UUID,
        *,
        user: User,
        filename: str,
        content: bytes,
    ) -> LetterDocument:
        letter = self._get_letter_for_access(letter_id, user=user)

        # Layered validation (§8-9): extension allowlist -> size ->
        # authoritative content-signature sniff -> extension/content
        # agreement. Raises one of document_validation's exceptions,
        # caught and translated at the endpoint layer.
        mime_type = validate_upload(filename, content)

        document_id = uuid.uuid4()
        final_path = build_storage_path(letter.id, document_id, mime_type)

        # Write-then-commit (§23): the file must exist on disk *before*
        # any database row references it, so a write failure never
        # leaves a dangling DB reference to a file that was never
        # created.
        write_document_file(final_path, content)

        try:
            document = self.documents.create(
                id=document_id,
                letter_id=letter.id,
                original_filename=filename,
                storage_path=str(final_path),
                file_size=len(content),
                mime_type=mime_type,
                uploaded_by=user.id,
            )
            self.session.flush()

            # Audit is mandatory (docs/architecture/audit-notifications.md
            # §20) and, per §10 of this implementation phase, must commit
            # atomically with the document row — recording it inside this
            # same try block means an audit failure is caught below and
            # triggers the existing file-cleanup compensation exactly as
            # a database failure would, never leaving the file and the
            # (now-uncommitted) audit/document rows out of sync. Only
            # safe metadata is recorded — never document bytes.
            self.audit.record(
                actor_id=user.id,
                action="DOCUMENT_UPLOADED",
                entity_type="LetterDocument",
                entity_id=document.id,
                new_values={
                    "letter_id": str(letter.id),
                    "original_filename": filename,
                    "mime_type": mime_type,
                    "file_size": len(content),
                },
            )

            self.session.commit()
            self.session.refresh(document)
        except Exception:
            # The file already exists on disk; a DB failure here must
            # not leave a row-less orphan silently mismatched against
            # what the caller was told happened. Roll back the
            # transaction and remove the now-orphaned file as
            # compensation — an orphan file that never got this far is a
            # safer failure mode than a DB row referencing nothing (§23).
            self.session.rollback()
            delete_document_file(final_path)
            raise

        return document

    def list_documents(self, letter_id: uuid.UUID, *, user: User) -> List[LetterDocument]:
        self._get_letter_for_access(letter_id, user=user)
        return self.documents.list_by_letter(letter_id)

    def get_document(
        self, letter_id: uuid.UUID, document_id: uuid.UUID, *, user: User
    ) -> LetterDocument:
        """Metadata (plus `storage_path`, for the endpoint layer to
        stream from) for a single document. Letter access is checked
        *before* the document lookup even runs — an inaccessible
        letter's document must not be distinguishable from a nonexistent
        one (§17)."""
        self._get_letter_for_access(letter_id, user=user)
        document = self.documents.find_by_id_and_letter(document_id, letter_id)
        if document is None:
            raise DocumentNotFoundError()
        return document
