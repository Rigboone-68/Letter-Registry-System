"""Layered file-type/size validation for document uploads.

Implements docs/architecture/document-management.md §8-9:

1. Extension allowlist — a fast, weak first filter (easily spoofed).
2. Client-supplied `Content-Type` — deliberately never used to decide
   anything (see `upload_file.content_type` at the call site in
   `app/services/document_service.py`, which is read only for logging-
   shaped context, never passed into any function here).
3. Magic-byte content-signature verification — the authoritative check.
   A file whose declared extension doesn't match its actual, sniffed
   content type is rejected as mismatched, not silently accepted under
   whichever type "wins".
4. Size limit (`settings.MAX_DOCUMENT_SIZE_BYTES` — an ARCHITECTURAL
   RECOMMENDATION, not a confirmed organizational limit; see §9).

Passing this validation proves a file's bytes structurally match a
PDF/JPEG/PNG/text signature — it is not malware scanning and is not a
substitute for it (explicitly out of scope; see §8).
"""

from app.core.config import settings

ALLOWED_EXTENSIONS = {"pdf", "jpg", "jpeg", "png", "txt"}

# Canonical MIME type each allowed extension is expected to actually
# contain, once its content is sniffed — kept in sync by hand with
# app/services/document_storage.py's reverse mapping.
MIME_TYPE_BY_EXTENSION = {
    "pdf": "application/pdf",
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "png": "image/png",
    "txt": "text/plain",
}

# Content-signature (magic-byte) checks for the binary types. Deliberately
# hand-rolled rather than a `python-magic`/libmagic dependency: the
# accepted type set is small and fixed, so a few literal byte-prefix
# checks are simpler, have no native-library install story on Windows,
# and are exactly as authoritative for this closed set of types.
_SIGNATURES = {
    "application/pdf": (b"%PDF-",),
    "image/jpeg": (b"\xff\xd8\xff",),
    "image/png": (b"\x89PNG\r\n\x1a\n",),
}


class UnsupportedFileTypeError(Exception):
    """The filename extension isn't in the V1 allowlist, or the content's
    actual signature doesn't match any accepted type."""


class FileContentMismatchError(Exception):
    """The content's actual, sniffed type doesn't match what the
    filename's extension claims (e.g. a `.pdf` upload whose bytes are
    actually a PNG) — rejected rather than silently accepted under
    whichever type the sniff found. See §7/§8, "reject malformed/
    mismatched content"."""


class FileTooLargeError(Exception):
    """The uploaded content exceeds `settings.MAX_DOCUMENT_SIZE_BYTES`."""


class EmptyFileError(Exception):
    """The uploaded content is empty."""


def validate_extension(filename: str) -> str:
    """Fast, weak first filter — easily spoofed, never authoritative on
    its own. Returns the lower-cased extension for later comparison
    against the sniffed content type."""
    extension = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if extension not in ALLOWED_EXTENSIONS:
        raise UnsupportedFileTypeError()
    return extension


def validate_size(content: bytes) -> None:
    if len(content) == 0:
        raise EmptyFileError()
    if len(content) > settings.MAX_DOCUMENT_SIZE_BYTES:
        raise FileTooLargeError()


def _looks_like_text(content: bytes) -> bool:
    """Plain text has no magic-byte signature. Validated instead by
    confirming the content decodes as UTF-8 and contains none of the
    control characters a genuine text document wouldn't (a NUL byte or
    other non-printable C0 control character strongly suggests binary
    content that merely happens to decode)."""
    if b"\x00" in content:
        return False
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError:
        return False
    return all(ch in "\t\n\r" or ch >= " " for ch in text)


def detect_mime_type(content: bytes) -> str:
    """Return the validated MIME type for `content`, based only on its
    actual bytes — the authoritative check; the client-supplied
    `Content-Type` header is never consulted here. Raises
    `UnsupportedFileTypeError` if the content matches none of the
    accepted signatures."""
    for mime_type, signatures in _SIGNATURES.items():
        if any(content.startswith(sig) for sig in signatures):
            return mime_type
    if _looks_like_text(content):
        return "text/plain"
    raise UnsupportedFileTypeError()


def validate_upload(filename: str, content: bytes) -> str:
    """Run the full layered pipeline and return the validated,
    server-trusted MIME type. Order: extension allowlist -> size ->
    content-signature sniff -> extension/content agreement. Raises one of
    this module's exceptions on any failure; never returns a type the
    content itself doesn't actually match."""
    extension = validate_extension(filename)
    validate_size(content)
    detected_mime_type = detect_mime_type(content)
    if MIME_TYPE_BY_EXTENSION[extension] != detected_mime_type:
        raise FileContentMismatchError()
    return detected_mime_type
