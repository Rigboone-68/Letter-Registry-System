"""LetterDocument upload/list/download endpoints — nested under their
Letter (docs/architecture/document-management.md §19), never a flat
`/api/v1/documents/{id}`, so the letter-first authorization chain is the
only structurally possible code path.

Every route uses `get_current_user` only — the same one-check-not-two
principle `app/api/v1/endpoints/letters.py` already established for
GET/PATCH/DELETE: the real authorization decision happens inside
`app/services/document_service.py` (via `LetterService.get_letter`,
which applies `assert_letter_access`), not a second time at the
dependency layer. This deliberately differs from `POST /letters`
(`require_user_or_admin`, SYSTEM_ADMIN excluded because it has no
department to record a letter against) — uploading a document attaches
to an *existing* letter, which SYSTEM_ADMIN can already fully read and
update, so it retains the same system-wide access here (brief §13: "Do
not create a separate document permission hierarchy").

No delete endpoint exists in this module, and none is planned for V1 —
see docs/architecture/document-management.md §14. A document upload is
never a "replace" of an earlier one either (§13/§19 of the review) —
uploading again simply adds another `LetterDocument`; nothing here ever
removes a prior one.
"""

import re
import uuid

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import settings
from app.database.session import get_db
from app.models.letter_document import LetterDocument
from app.models.user import User
from app.schemas.document import DocumentListResponse, DocumentResponse
from app.services.document_service import DocumentService
from app.services.document_storage import StorageError, build_storage_path
from app.services.document_validation import (
    EmptyFileError,
    FileContentMismatchError,
    FileTooLargeError,
    UnsupportedFileTypeError,
)
from app.services.exceptions import DocumentNotFoundError, LetterNotFoundError

router = APIRouter(prefix="/letters/{letter_id}/documents", tags=["letters", "documents"])

# Strips characters that could inject additional HTTP headers or
# otherwise misbehave in a Content-Disposition header — defense in depth
# beyond what HTTP header parsing already disallows in an inbound value.
# See docs/architecture/document-management.md §19.
_CONTROL_CHARS = re.compile(r"[\r\n\x00-\x1f\x7f]")


def _safe_download_filename(original_filename: str) -> str:
    cleaned = _CONTROL_CHARS.sub("", original_filename).strip()
    return cleaned or "document"


def _letter_not_found() -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Letter not found.")


def _document_not_found() -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found.")


def _storage_unavailable() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Failed to store the uploaded document.",
    )


def _handle_validation_error(exc: Exception) -> HTTPException:
    if isinstance(exc, EmptyFileError):
        return HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Uploaded file is empty."
        )
    if isinstance(exc, FileTooLargeError):
        return HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail=f"File exceeds the maximum allowed size of {settings.MAX_DOCUMENT_SIZE_BYTES} bytes.",
        )
    if isinstance(exc, (UnsupportedFileTypeError, FileContentMismatchError)):
        return HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Unsupported, unrecognized, or mismatched file type.",
        )
    raise exc  # pragma: no cover - defensive, every caller passes a handled type


@router.post(
    "",
    response_model=DocumentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload a document attachment for a letter, subject to department/classified access",
)
def upload_document(
    letter_id: uuid.UUID,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> LetterDocument:
    # Bound how much is read into memory before size validation even
    # runs — read one byte past the configured limit so an oversized
    # upload is detected without buffering an unbounded amount of data
    # (docs/architecture/document-management.md §27).
    content = file.file.read(settings.MAX_DOCUMENT_SIZE_BYTES + 1)
    filename = file.filename or ""

    service = DocumentService(db)
    try:
        return service.upload_document(
            letter_id, user=current_user, filename=filename, content=content
        )
    except LetterNotFoundError:
        raise _letter_not_found()
    except (EmptyFileError, FileTooLargeError, UnsupportedFileTypeError, FileContentMismatchError) as exc:
        raise _handle_validation_error(exc)
    except StorageError:
        raise _storage_unavailable()


@router.get(
    "",
    response_model=DocumentListResponse,
    summary="List document attachments for a letter, subject to department/classified access",
)
def list_documents(
    letter_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DocumentListResponse:
    service = DocumentService(db)
    try:
        items = service.list_documents(letter_id, user=current_user)
    except LetterNotFoundError:
        raise _letter_not_found()
    return DocumentListResponse(items=items, total=len(items))


@router.get(
    "/{document_id}",
    summary="Download a document's content, subject to department/classified access",
)
def download_document(
    letter_id: uuid.UUID,
    document_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> FileResponse:
    service = DocumentService(db)
    try:
        document = service.get_document(letter_id, document_id, user=current_user)
    except LetterNotFoundError:
        raise _letter_not_found()
    except DocumentNotFoundError:
        raise _document_not_found()

    # Reconstruct the path from trusted primitives (letter/document id,
    # the server-validated mime_type) and re-verify storage-root
    # containment, rather than trusting the stored `storage_path` column
    # as-is — docs/architecture/document-management.md §15 steps 5-6.
    try:
        resolved_path = build_storage_path(letter_id, document_id, document.mime_type)
    except (StorageError, KeyError):
        raise _storage_unavailable()

    if not resolved_path.is_file():
        # The database row exists but the file is missing on disk (e.g.
        # storage restored from a database-only backup — see
        # docs/architecture/document-management.md §22). Never a raw
        # FileNotFoundError/stack trace to the client.
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Document content is unavailable.",
        )

    return FileResponse(
        resolved_path,
        media_type=document.mime_type,
        filename=_safe_download_filename(document.original_filename),
        headers={"X-Content-Type-Options": "nosniff"},
    )
