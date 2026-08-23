/**
 * API service functions for the confirmed Document endpoints
 * (backend/app/api/v1/endpoints/documents.py, verified fresh this
 * session) — all `get_current_user` only, authorized entirely through
 * the parent Letter (`LetterService.get_letter`, which applies
 * `assert_letter_access` — department isolation, then classified-access
 * narrowing):
 *
 *   GET  /letters/{letter_id}/documents             → DocumentListResponse
 *                                                       {items, total} — no
 *                                                       pagination/sort/filter
 *   POST /letters/{letter_id}/documents              → DocumentResponse (201),
 *                                                       multipart/form-data,
 *                                                       one `file` field
 *   GET  /letters/{letter_id}/documents/{document_id} → raw file bytes
 *                                                       (fetched here as a
 *                                                       Blob)
 *
 * `DocumentResponse` has no `storage_path` field — never serialized by
 * the backend, so there is nothing here that could expose one even by
 * accident (docs/architecture/document-notification-ui.md §1.2/§6.6).
 *
 * No `delete`/`replace`/`archive` function exists in this module —
 * confirmed no such endpoint exists anywhere in `documents.py`;
 * "replacement" is calling `upload` again, which leaves every prior
 * document fully untouched (§1.8/§5).
 */

import apiClient from './apiClient'

// Mirrors the backend's own confirmed pipeline exactly
// (backend/app/services/document_validation.py's ALLOWED_EXTENSIONS,
// backend/app/core/config.py's MAX_DOCUMENT_SIZE_BYTES) — used here only
// to power lightweight, non-authoritative client-side pre-checks
// (services/../utils/formValidation.js:validateDocumentFile) and the
// upload form's own accepted-type/size explanation text. The backend's
// magic-byte content-signature check remains the sole authority; a file
// that passes this allowlist but fails that sniff is still rejected
// with a `422`.
export const ALLOWED_DOCUMENT_EXTENSIONS = Object.freeze(['pdf', 'jpg', 'jpeg', 'png', 'txt'])
export const MAX_DOCUMENT_SIZE_BYTES = 10 * 1024 * 1024

export async function list(letterId) {
  const response = await apiClient.get(`/letters/${letterId}/documents`)
  return response.data
}

export async function upload(letterId, file, onUploadProgress) {
  const formData = new FormData()
  formData.append('file', file)
  const response = await apiClient.post(`/letters/${letterId}/documents`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    onUploadProgress,
  })
  return response.data
}

// Returns the raw response Blob only — never an object URL and never a
// triggered download. Creating/revoking an object URL is a component-
// lifecycle concern (docs/architecture/document-notification-ui.md
// §4.2), not this service layer's job; the caller already has the
// document's own `original_filename` from the list metadata, so there
// is no need to parse it back out of a response header here either.
export async function download(letterId, documentId) {
  const response = await apiClient.get(`/letters/${letterId}/documents/${documentId}`, {
    responseType: 'blob',
  })
  return response.data
}
