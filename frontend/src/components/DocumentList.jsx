import { useState } from 'react'

import ErrorState from './ErrorState'
import * as documentService from '../services/documentService'
import styles from './DataTable.module.css'

function formatFileSize(bytes) {
  if (bytes == null) return '—'
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

function formatDateTime(value) {
  if (!value) return '—'
  return new Date(value).toLocaleString(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

/**
 * Document list for one Letter (Phase 5E,
 * docs/architecture/document-notification-ui.md §6/§14.1) — renders
 * only fields `DocumentResponse` actually returns
 * (`backend/app/schemas/document.py`): no `storage_path` (never
 * serialized), no resolved uploader name (no cross-role user-lookup
 * endpoint is in scope, matching `LetterDetailPage`'s own precedent for
 * `recorded_by`). Shares `DataTable.module.css` with the Phase 5D
 * administration tables — the same plain-table visual structure, no
 * sortable-header logic needed (this list has no backend sort/filter
 * to control, §11 of the review).
 *
 * Download is inlined here, not a separate `DownloadButton` component
 * (docs/architecture/document-notification-ui.md §14.1 explicitly
 * recommends against factoring out a single-button click handler this
 * small). Authenticated fetch + blob is required — a plain
 * `<a href>` cannot carry the Bearer token a download requires — so a
 * synthetic, immediately-clicked anchor triggers the save once the
 * blob has actually been fetched through `apiClient`.
 */
export default function DocumentList({ letterId, documents }) {
  const [downloadingId, setDownloadingId] = useState(null)
  const [downloadError, setDownloadError] = useState(null)

  async function handleDownload(doc) {
    setDownloadingId(doc.id)
    setDownloadError(null)
    try {
      const blob = await documentService.download(letterId, doc.id)
      const url = URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = doc.original_filename
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      // A short delay before revoking — some browsers need the download
      // to actually start before the object URL is torn down.
      setTimeout(() => URL.revokeObjectURL(url), 1000)
    } catch (normalizedError) {
      setDownloadError(normalizedError.message ?? 'Unable to download this document.')
    } finally {
      setDownloadingId(null)
    }
  }

  return (
    <div>
      {downloadError && <ErrorState message={downloadError} />}
      <div className={styles.scroller}>
        <table className={styles.table}>
          <thead>
            <tr>
              <th scope="col">Filename</th>
              <th scope="col">Size</th>
              <th scope="col">Type</th>
              <th scope="col">Uploaded</th>
              <th scope="col">Actions</th>
            </tr>
          </thead>
          <tbody>
            {documents.map((doc) => (
              <tr key={doc.id}>
                <th scope="row" className={styles.primaryCell}>
                  {doc.original_filename}
                </th>
                <td>{formatFileSize(doc.file_size)}</td>
                <td>{doc.mime_type ?? '—'}</td>
                <td>{formatDateTime(doc.uploaded_at)}</td>
                <td>
                  <div className={styles.actionsCell}>
                    <button
                      type="button"
                      onClick={() => handleDownload(doc)}
                      disabled={downloadingId === doc.id}
                    >
                      {downloadingId === doc.id
                        ? 'Downloading…'
                        : `Download ${doc.original_filename}`}
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
