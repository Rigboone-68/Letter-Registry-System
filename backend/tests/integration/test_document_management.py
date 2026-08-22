"""End-to-end tests for document upload/retrieval (Phase 4D implementation).

Real JWTs, real database-backed Users/Departments/Letters, real HTTP
requests through `/api/v1/letters/{letter_id}/documents*`, against a
real PostgreSQL test database — same pattern as every integration test
file since Phase 3A.

`storage_root` (autouse) redirects every test's `STORAGE_PATH` to a
pytest-managed temporary directory, so no test ever writes into the
real `storage/letters/` tree and every test starts from an empty
directory regardless of what an earlier test wrote — the filesystem
equivalent of `db_session`'s per-test rollback isolation. This works
because `app/services/document_storage.py:get_storage_root` re-reads
`settings.STORAGE_PATH` on every call rather than caching it.
"""

import uuid

import pytest

from app.core.config import settings
from app.core.security import create_access_token
from app.models.enums import ActiveStatus, UserRole, UserStatus
from app.models.letter_document import LetterDocument
from app.services import document_storage
from app.services.document_service import DocumentService
from tests.factories import (
    make_classification,
    make_department,
    make_letter,
    make_user,
)

LETTERS_URL = "/api/v1/letters"

PDF_BYTES = b"%PDF-1.4\n%mock pdf content for testing\n%%EOF"
JPEG_BYTES = b"\xff\xd8\xff\xe0" + b"\x00" * 32 + b"mock jpeg content"
PNG_BYTES = b"\x89PNG\r\n\x1a\n" + b"\x00" * 32 + b"mock png content"
TXT_BYTES = b"Hello, this is a plain text letter attachment.\n"


@pytest.fixture(autouse=True)
def storage_root(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "STORAGE_PATH", str(tmp_path))
    return tmp_path


def _token_for(user) -> str:
    return create_access_token(subject=user.id, role=user.role.value, department_id=user.department_id)


def _auth_headers(user) -> dict:
    return {"Authorization": f"Bearer {_token_for(user)}"}


def _documents_url(letter_id) -> str:
    return f"{LETTERS_URL}/{letter_id}/documents"


def _document_url(letter_id, document_id) -> str:
    return f"{_documents_url(letter_id)}/{document_id}"


def _make_system_admin(db_session, email="sys.admin.docs@example.gov"):
    return make_user(db_session, department=None, role=UserRole.SYSTEM_ADMIN, email=email)


def _make_admin(db_session, department, email="admin.docs@example.gov"):
    return make_user(db_session, department, role=UserRole.ADMIN, email=email)


def _make_user(db_session, department, email="user.docs@example.gov"):
    return make_user(db_session, department, role=UserRole.USER, email=email)


def _upload(client, letter_id, headers, filename="letter.pdf", content=PDF_BYTES, content_type="application/pdf"):
    return client.post(
        _documents_url(letter_id),
        files={"file": (filename, content, content_type)},
        headers=headers,
    )


def _setup_letter(db_session, *, classification=None):
    department = make_department(db_session, name=f"Docs Dept {uuid.uuid4()}")
    recorder = _make_user(db_session, department, email=f"recorder.{uuid.uuid4()}@example.gov")
    letter = make_letter(db_session, department, recorder, classification=classification)
    return department, recorder, letter


# =========================================================================
# File acceptance
# =========================================================================


def test_valid_pdf_accepted(client, db_session):
    _, recorder, letter = _setup_letter(db_session)
    response = _upload(client, letter.id, _auth_headers(recorder))
    assert response.status_code == 201
    body = response.json()
    assert body["mime_type"] == "application/pdf"
    assert body["original_filename"] == "letter.pdf"
    assert body["letter_id"] == str(letter.id)


def test_valid_jpeg_accepted(client, db_session):
    _, recorder, letter = _setup_letter(db_session)
    response = _upload(
        client, letter.id, _auth_headers(recorder),
        filename="photo.jpg", content=JPEG_BYTES, content_type="image/jpeg",
    )
    assert response.status_code == 201
    assert response.json()["mime_type"] == "image/jpeg"


def test_valid_png_accepted(client, db_session):
    _, recorder, letter = _setup_letter(db_session)
    response = _upload(
        client, letter.id, _auth_headers(recorder),
        filename="scan.png", content=PNG_BYTES, content_type="image/png",
    )
    assert response.status_code == 201
    assert response.json()["mime_type"] == "image/png"


def test_valid_txt_accepted(client, db_session):
    _, recorder, letter = _setup_letter(db_session)
    response = _upload(
        client, letter.id, _auth_headers(recorder),
        filename="notes.txt", content=TXT_BYTES, content_type="text/plain",
    )
    assert response.status_code == 201
    assert response.json()["mime_type"] == "text/plain"


# =========================================================================
# File rejection
# =========================================================================


def test_executable_extension_rejected(client, db_session):
    _, recorder, letter = _setup_letter(db_session)
    response = _upload(
        client, letter.id, _auth_headers(recorder),
        filename="malware.exe", content=b"MZ\x90\x00\x03\x00\x00\x00", content_type="application/octet-stream",
    )
    assert response.status_code == 422


def test_html_extension_rejected(client, db_session):
    _, recorder, letter = _setup_letter(db_session)
    response = _upload(
        client, letter.id, _auth_headers(recorder),
        filename="page.html", content=b"<html><body>hi</body></html>", content_type="text/html",
    )
    assert response.status_code == 422


def test_unsupported_extension_rejected(client, db_session):
    _, recorder, letter = _setup_letter(db_session)
    response = _upload(
        client, letter.id, _auth_headers(recorder),
        filename="report.docx", content=b"whatever", content_type="application/msword",
    )
    assert response.status_code == 422


def test_mime_spoofing_rejected(client, db_session):
    """Real PNG bytes, but the filename and declared Content-Type both
    claim PDF — the client-supplied Content-Type is never trusted, and
    the sniffed content must match the extension or be rejected."""
    _, recorder, letter = _setup_letter(db_session)
    response = _upload(
        client, letter.id, _auth_headers(recorder),
        filename="fake.pdf", content=PNG_BYTES, content_type="application/pdf",
    )
    assert response.status_code == 422


def test_malformed_pdf_rejected(client, db_session):
    _, recorder, letter = _setup_letter(db_session)
    response = _upload(
        client, letter.id, _auth_headers(recorder),
        filename="broken.pdf", content=b"this is not a real pdf file", content_type="application/pdf",
    )
    assert response.status_code == 422


def test_malformed_image_rejected(client, db_session):
    _, recorder, letter = _setup_letter(db_session)
    response = _upload(
        client, letter.id, _auth_headers(recorder),
        filename="broken.jpg", content=b"\xd0\xd1\xd2\xd3\xff\xfe\x00\x01garbage",
        content_type="image/jpeg",
    )
    assert response.status_code == 422


def test_oversized_document_rejected(client, db_session, monkeypatch):
    monkeypatch.setattr(settings, "MAX_DOCUMENT_SIZE_BYTES", 10)
    _, recorder, letter = _setup_letter(db_session)
    response = _upload(client, letter.id, _auth_headers(recorder))
    assert response.status_code == 413


def test_empty_file_rejected(client, db_session):
    _, recorder, letter = _setup_letter(db_session)
    response = _upload(client, letter.id, _auth_headers(recorder), content=b"")
    assert response.status_code == 422


# =========================================================================
# Path security
# =========================================================================


@pytest.mark.parametrize(
    "malicious_filename",
    [
        "../../etc/passwd.pdf",
        "..\\..\\windows\\system32\\evil.pdf",
        "/etc/passwd.pdf",
        "C:\\Windows\\System32\\evil.pdf",
        "letter\x00.pdf",
    ],
)
def test_malicious_filename_never_becomes_storage_path(client, db_session, storage_root, malicious_filename):
    """A hostile original_filename must never influence where the file
    actually lands on disk — the stored path is always server-generated
    (letter_id/document_id-based) regardless of what filename was
    supplied. The upload may succeed or fail depending on whether the
    filename parses to an allowed extension, but if it succeeds, the
    file must land only inside storage_root/<letter_id>/."""
    _, recorder, letter = _setup_letter(db_session)
    response = _upload(client, letter.id, _auth_headers(recorder), filename=malicious_filename)

    if response.status_code != 201:
        # Rejected outright (e.g. no recognized extension after the
        # traversal prefix) — nothing was ever written, which is also a
        # safe outcome for this test.
        return

    body = response.json()
    document_id = uuid.UUID(body["id"])
    expected_path = (storage_root / str(letter.id) / f"{document_id}.pdf").resolve()
    assert expected_path.is_file()
    # No file was written anywhere outside the per-letter subdirectory.
    written_files = list(storage_root.rglob("*"))
    written_files = [p for p in written_files if p.is_file()]
    assert written_files == [expected_path]


def test_constructed_path_stays_within_storage_root(db_session, storage_root):
    _, _, letter = _setup_letter(db_session)
    document_id = uuid.uuid4()
    path = document_storage.build_storage_path(letter.id, document_id, "application/pdf")
    assert storage_root.resolve() in path.parents


# =========================================================================
# Authorization
# =========================================================================


def test_user_can_upload_within_own_department(client, db_session):
    _, recorder, letter = _setup_letter(db_session)
    response = _upload(client, letter.id, _auth_headers(recorder))
    assert response.status_code == 201


def test_user_cannot_upload_to_other_department_letter(client, db_session):
    _, _, letter = _setup_letter(db_session)
    other_department = make_department(db_session, name=f"Other Dept {uuid.uuid4()}")
    outsider = _make_user(db_session, other_department, email=f"outsider.{uuid.uuid4()}@example.gov")
    response = _upload(client, letter.id, _auth_headers(outsider))
    assert response.status_code == 404


def test_admin_can_upload_within_own_department(client, db_session):
    department, _, letter = _setup_letter(db_session)
    admin = _make_admin(db_session, department, email=f"admin.{uuid.uuid4()}@example.gov")
    response = _upload(client, letter.id, _auth_headers(admin))
    assert response.status_code == 201


def test_admin_cannot_upload_to_other_department_letter(client, db_session):
    _, _, letter = _setup_letter(db_session)
    other_department = make_department(db_session, name=f"Other Admin Dept {uuid.uuid4()}")
    other_admin = _make_admin(db_session, other_department, email=f"other.admin.{uuid.uuid4()}@example.gov")
    response = _upload(client, letter.id, _auth_headers(other_admin))
    assert response.status_code == 404


def test_system_admin_can_upload_to_any_department_letter(client, db_session):
    _, _, letter = _setup_letter(db_session)
    sys_admin = _make_system_admin(db_session, email=f"sys.{uuid.uuid4()}@example.gov")
    response = _upload(client, letter.id, _auth_headers(sys_admin))
    assert response.status_code == 201


def test_non_recorder_user_cannot_access_classified_letter_documents(client, db_session):
    classification = make_classification(
        db_session, name=f"Restricted {uuid.uuid4()}", restricts_access=True
    )
    department, recorder, letter = _setup_letter(db_session, classification=classification)
    upload = _upload(client, letter.id, _auth_headers(recorder))
    assert upload.status_code == 201

    other_user = _make_user(db_session, department, email=f"other.user.{uuid.uuid4()}@example.gov")
    response = client.get(_documents_url(letter.id), headers=_auth_headers(other_user))
    assert response.status_code == 404


def test_recorder_can_access_own_classified_letter_documents(client, db_session):
    classification = make_classification(
        db_session, name=f"Restricted {uuid.uuid4()}", restricts_access=True
    )
    _, recorder, letter = _setup_letter(db_session, classification=classification)
    upload = _upload(client, letter.id, _auth_headers(recorder))
    assert upload.status_code == 201

    response = client.get(_documents_url(letter.id), headers=_auth_headers(recorder))
    assert response.status_code == 200
    assert response.json()["total"] == 1


def test_document_from_wrong_letter_is_not_found(client, db_session):
    _, recorder, letter_a = _setup_letter(db_session)
    _, _, letter_b = _setup_letter(db_session)
    upload = _upload(client, letter_a.id, _auth_headers(recorder))
    document_id = upload.json()["id"]

    response = client.get(_document_url(letter_b.id, document_id), headers=_auth_headers(recorder))
    assert response.status_code == 404


def test_nonexistent_document_is_not_found(client, db_session):
    _, recorder, letter = _setup_letter(db_session)
    response = client.get(_document_url(letter.id, uuid.uuid4()), headers=_auth_headers(recorder))
    assert response.status_code == 404


def test_nonexistent_letter_is_not_found(client, db_session):
    _, recorder, _ = _setup_letter(db_session)
    response = client.get(_documents_url(uuid.uuid4()), headers=_auth_headers(recorder))
    assert response.status_code == 404


# =========================================================================
# Historical integrity
# =========================================================================


def test_deactivated_uploader_still_represented(client, db_session):
    _, recorder, letter = _setup_letter(db_session)
    upload = _upload(client, letter.id, _auth_headers(recorder))
    assert upload.status_code == 201
    uploaded_by = upload.json()["uploaded_by"]

    recorder.status = UserStatus.DEACTIVATED
    db_session.flush()

    admin_view = _make_system_admin(db_session, email=f"sys.check.{uuid.uuid4()}@example.gov")
    response = client.get(_documents_url(letter.id), headers=_auth_headers(admin_view))
    assert response.status_code == 200
    assert response.json()["items"][0]["uploaded_by"] == uploaded_by


def test_letter_archive_does_not_remove_documents(client, db_session):
    _, recorder, letter = _setup_letter(db_session)
    upload = _upload(client, letter.id, _auth_headers(recorder))
    assert upload.status_code == 201

    archive_response = client.delete(f"{LETTERS_URL}/{letter.id}", headers=_auth_headers(recorder))
    assert archive_response.status_code == 200
    assert archive_response.json()["status"] == "ARCHIVED"

    list_response = client.get(_documents_url(letter.id), headers=_auth_headers(recorder))
    assert list_response.status_code == 200
    assert list_response.json()["total"] == 1


def test_document_still_downloadable_after_letter_archive(client, db_session):
    _, recorder, letter = _setup_letter(db_session)
    upload = _upload(client, letter.id, _auth_headers(recorder))
    document_id = upload.json()["id"]

    client.delete(f"{LETTERS_URL}/{letter.id}", headers=_auth_headers(recorder))

    download = client.get(_document_url(letter.id, document_id), headers=_auth_headers(recorder))
    assert download.status_code == 200
    assert download.content == PDF_BYTES


# =========================================================================
# Storage
# =========================================================================


def test_storage_path_is_server_controlled_uuid_based(client, db_session, storage_root):
    _, recorder, letter = _setup_letter(db_session)
    response = _upload(client, letter.id, _auth_headers(recorder))
    document_id = response.json()["id"]

    document = db_session.get(LetterDocument, uuid.UUID(document_id))
    stored_path = document.storage_path
    assert "letter.pdf" not in stored_path  # never the original filename
    assert str(letter.id) in stored_path
    assert f"{document_id}.pdf" in stored_path


def test_document_metadata_never_exposes_storage_path(client, db_session):
    _, recorder, letter = _setup_letter(db_session)
    upload_body = _upload(client, letter.id, _auth_headers(recorder)).json()
    assert "storage_path" not in upload_body

    list_body = client.get(_documents_url(letter.id), headers=_auth_headers(recorder)).json()
    assert "storage_path" not in list_body["items"][0]


def test_no_static_file_route_exposes_storage(client, db_session):
    _, recorder, letter = _setup_letter(db_session)
    upload = _upload(client, letter.id, _auth_headers(recorder))
    document_id = upload.json()["id"]

    # No unauthenticated/static route should ever serve this content —
    # only the authenticated, authorized endpoint above does. A guessed
    # "raw" filesystem-style URL must not resolve to anything.
    response = client.get(f"/storage/letters/{letter.id}/{document_id}.pdf")
    assert response.status_code == 404


def test_download_content_type_and_disposition(client, db_session):
    _, recorder, letter = _setup_letter(db_session)
    upload = _upload(client, letter.id, _auth_headers(recorder))
    document_id = upload.json()["id"]

    response = client.get(_document_url(letter.id, document_id), headers=_auth_headers(recorder))
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert "letter.pdf" in response.headers.get("content-disposition", "")
    assert response.headers.get("x-content-type-options") == "nosniff"


# =========================================================================
# Failure handling
# =========================================================================


def test_db_failure_cleans_up_finalized_file(client, db_session, storage_root, monkeypatch):
    _, recorder, letter = _setup_letter(db_session)

    def _boom(self, **kwargs):
        raise RuntimeError("simulated database failure")

    monkeypatch.setattr(
        "app.repositories.letter_document_repository.LetterDocumentRepository.create", _boom
    )

    with pytest.raises(RuntimeError):
        DocumentService(db_session).upload_document(
            letter.id, user=recorder, filename="letter.pdf", content=PDF_BYTES
        )

    written_files = [p for p in storage_root.rglob("*") if p.is_file()]
    assert written_files == []


def test_file_write_failure_creates_no_db_record(client, db_session, monkeypatch):
    _, recorder, letter = _setup_letter(db_session)

    def _boom(path, content):
        raise document_storage.StorageError("simulated disk failure")

    monkeypatch.setattr(document_storage, "write_document_file", _boom)
    monkeypatch.setattr(
        "app.services.document_service.write_document_file", _boom
    )

    with pytest.raises(document_storage.StorageError):
        DocumentService(db_session).upload_document(
            letter.id, user=recorder, filename="letter.pdf", content=PDF_BYTES
        )

    remaining = db_session.query(LetterDocument).filter_by(letter_id=letter.id).count()
    assert remaining == 0


def test_successful_upload_leaves_no_orphan_files(client, db_session, storage_root):
    _, recorder, letter = _setup_letter(db_session)
    response = _upload(client, letter.id, _auth_headers(recorder))
    assert response.status_code == 201

    written_files = [p for p in storage_root.rglob("*") if p.is_file()]
    assert len(written_files) == 1
