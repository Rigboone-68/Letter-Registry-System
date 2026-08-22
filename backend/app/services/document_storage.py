"""Server-controlled filesystem storage for `LetterDocument` bytes.

Implements the architecture approved in
docs/architecture/document-management.md §5-7, §23:

* Every path segment is server-generated (UUIDs) or server-derived (a
  canonical extension mapped from the already-validated MIME type) —
  never client input (no client-supplied filename, extension, or path
  fragment is ever used to build a filesystem location).
* `STORAGE_PATH` is resolved to an absolute path fresh on every call
  (never cached at import time), so a relative value in configuration is
  never interpreted against a variable process working directory, and so
  tests can override `settings.STORAGE_PATH` per run without any
  cache-invalidation machinery.
* Writes are staged to a unique temporary file in the destination
  directory and atomically renamed into place (`os.replace`), so a
  concurrent reader or an interrupted write can never observe a
  partially-written file at the final path.
* A resolved-path containment check runs before every write, as defense
  in depth beyond "we never used untrusted input" — structurally
  unreachable given every input above is a UUID/fixed extension, but
  cheap insurance against a future mistake.

No delete-by-user-action exists anywhere in this module — the only
removal helper (`delete_document_file`) exists purely to compensate for a
failed database commit after a successful write (docs/architecture/
document-management.md §14/§23), never a user-facing operation.
"""

import os
import uuid
from pathlib import Path

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

# Canonical, server-derived extension for each accepted, signature-
# validated MIME type — never taken from a client-supplied filename. Kept
# in sync by hand with app/services/document_validation.py's signature
# map (four types, not expected to change often enough to justify a
# shared source).
EXTENSION_BY_MIME_TYPE = {
    "application/pdf": "pdf",
    "image/jpeg": "jpg",
    "image/png": "png",
    "text/plain": "txt",
}


class StorageError(Exception):
    """Filesystem storage failed — disk full, a permission error, an
    unavailable mount, or the path-containment check below. Translated to
    a clean 5xx at the API layer, never a raw stack trace or an internal
    path in the response. See docs/architecture/document-management.md
    §21/§23."""


def get_storage_root() -> Path:
    """Resolve `STORAGE_PATH` to an absolute path, creating it if it
    doesn't exist yet. Resolved fresh on every call rather than cached at
    import time, so a relative configured value is always interpreted
    against the current working directory rather than whatever it
    happened to be the first time this ran — see
    docs/architecture/document-management.md §5."""
    root = Path(settings.STORAGE_PATH).resolve()
    try:
        root.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise StorageError(f"Storage root is not writable: {exc}") from exc
    return root


def build_storage_path(letter_id: uuid.UUID, document_id: uuid.UUID, mime_type: str) -> Path:
    """Build the final, entirely server-controlled filesystem path for one
    document: `<STORAGE_PATH>/<letter_id>/<document_id>.<extension>`. Both
    UUIDs are server-generated; the extension is derived from the already
    magic-byte-validated `mime_type`, never from a client-supplied
    filename. See docs/architecture/document-management.md §7."""
    extension = EXTENSION_BY_MIME_TYPE[mime_type]
    root = get_storage_root()
    candidate = (root / str(letter_id) / f"{document_id}.{extension}").resolve()
    if candidate.parent.parent != root:
        # Structurally unreachable given the inputs above are UUIDs and a
        # fixed extension map, never client input — defense in depth only.
        raise StorageError("Resolved document path escaped the storage root.")
    return candidate


def write_document_file(final_path: Path, content: bytes) -> None:
    """Write `content` to `final_path` safely: stage it in a uniquely
    named temporary file in the same directory, flush and fsync it, then
    atomically rename it into place. A reader can never observe a
    partially-written file, and an interrupted write never leaves a
    corrupt file sitting at the final path. See
    docs/architecture/document-management.md §23."""
    tmp_path = final_path.parent / f".{final_path.name}.{uuid.uuid4().hex}.tmp"
    try:
        final_path.parent.mkdir(parents=True, exist_ok=True)
        with open(tmp_path, "wb") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_path, final_path)
    except OSError as exc:
        try:
            tmp_path.unlink(missing_ok=True)
        except OSError:
            pass
        raise StorageError(f"Failed to write document to storage: {exc}") from exc


def delete_document_file(final_path: Path) -> None:
    """Best-effort removal of a file. Used only as failure-path
    compensation — cleaning up a file that was successfully written but
    whose database row failed to commit (an orphan, per
    docs/architecture/document-management.md §23) — never as a
    user-facing delete operation (§14: V1 has no document deletion
    endpoint of any kind). A missing file is not an error.

    If the cleanup itself fails (e.g. the same disk problem that caused
    the database failure also blocks the delete), that is logged at
    WARNING — otherwise an orphan left behind by this rarer, secondary
    failure would have no trace anywhere. The successful path is
    deliberately silent (removing a file that no longer references
    anything is routine, not an event worth a log line). Only the
    already-server-controlled path is logged — never file contents,
    credentials, or any other request data — since it isn't sensitive
    beyond what `docs/architecture/document-management.md` §24 already
    treats as fine to know internally (it is exactly the value never
    exposed to a *client*, not something withheld from the operator log
    meant to explain a failure in this same path)."""
    try:
        final_path.unlink(missing_ok=True)
    except OSError as exc:
        logger.warning(
            "Failed to clean up orphaned document file %s after a prior failure: %s",
            final_path, exc,
        )
