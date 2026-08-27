import { useCallback, useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'

import ArchiveConfirmDialog from '../components/ArchiveConfirmDialog'
import DocumentList from '../components/DocumentList'
import DocumentUploadForm from '../components/DocumentUploadForm'
import EmptyState from '../components/EmptyState'
import ErrorState from '../components/ErrorState'
import LoadingState from '../components/LoadingState'
import StatusBadge from '../components/StatusBadge'
import * as documentService from '../services/documentService'
import * as letterService from '../services/letterService'
import { LETTER_STATUS_OPTIONS } from '../services/letterService'
import styles from './LetterDetailPage.module.css'

function statusLabel(value) {
  return LETTER_STATUS_OPTIONS.find((option) => option.value === value)?.label ?? value
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

function Field({ label, value }) {
  return (
    <div className={styles.field}>
      <dt>{label}</dt>
      <dd>{value || value === 0 ? value : '—'}</dd>
    </div>
  )
}

/**
 * Letter detail page (docs/architecture/frontend.md §9/§12, Phase 5C) —
 * `GET /api/v1/letters/{id}`. Renders exactly the fields
 * `LetterResponse` returns (`app/schemas/letter.py`) — `recorded_by` is
 * deliberately not shown as a raw id (no cross-role name-resolution
 * endpoint is in scope for this phase — only Category/Classification
 * reference data is, per the brief's own §40 scope limit); `created_at`
 * conveys "when this was recorded" without needing one.
 *
 * CRITICAL (§12/§7 of the brief): a `404` here — whether the letter
 * genuinely doesn't exist, belongs to another department, or is
 * classified and inaccessible to this caller — is collapsed by the
 * backend into one identical response (`LetterNotFoundError`,
 * `app/services/letter_service.py:_get_for_access`) and is rendered
 * here as the same generic "Letter not found," with no distinguishing
 * language of any kind.
 */
export default function LetterDetailPage() {
  const { id } = useParams()

  const [letter, setLetter] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [notFound, setNotFound] = useState(false)
  const [showArchiveDialog, setShowArchiveDialog] = useState(false)
  const [archiving, setArchiving] = useState(false)
  const [archiveError, setArchiveError] = useState(null)

  const [documents, setDocuments] = useState(null)
  const [documentsLoading, setDocumentsLoading] = useState(true)
  const [documentsError, setDocumentsError] = useState(null)

  const fetchDocuments = useCallback(() => {
    setDocumentsLoading(true)
    setDocumentsError(null)
    documentService
      .list(id)
      .then((response) => setDocuments(response.items))
      .catch((normalizedError) => setDocumentsError(normalizedError))
      .finally(() => setDocumentsLoading(false))
  }, [id])

  const fetchLetter = useCallback(() => {
    setLoading(true)
    setError(null)
    setNotFound(false)
    letterService
      .get(id)
      .then((response) => {
        setLetter(response)
        // Documents are only ever fetched once the Letter itself is
        // confirmed accessible — an inaccessible Letter never reaches
        // this branch, so there is no wasted/leaking document request
        // for a Letter this caller can't see (docs/architecture/
        // document-notification-ui.md §10.1).
        fetchDocuments()
      })
      .catch((normalizedError) => {
        if (normalizedError.status === 404) {
          setNotFound(true)
        } else {
          setError(normalizedError)
        }
      })
      .finally(() => setLoading(false))
  }, [id, fetchDocuments])

  useEffect(() => {
    fetchLetter()
  }, [fetchLetter])

  function handleUploadSuccess(document) {
    // Appended directly from the upload's own response, matching every
    // other Phase 5C/5D mutation's "refresh from the response, not a
    // second fetch" convention — the backend lists documents oldest
    // first (`uploaded_at asc`), so a newly uploaded document correctly
    // belongs at the end.
    setDocuments((previous) => [...(previous ?? []), document])
  }

  function handleConfirmArchive() {
    setArchiving(true)
    setArchiveError(null)
    letterService
      .archive(id)
      .then((response) => {
        setLetter(response)
        setShowArchiveDialog(false)
      })
      .catch((normalizedError) => setArchiveError(normalizedError.message ?? 'Unable to archive this letter.'))
      .finally(() => setArchiving(false))
  }

  if (loading) return <LoadingState label="Loading letter..." />
  if (notFound) return <ErrorState message="Letter not found." />
  if (error) return <ErrorState message={error.message} onRetry={fetchLetter} />
  if (!letter) return null

  return (
    <section className={styles.root}>
      <div className={styles.header}>
        <div>
          <Link to="/app/letters" className={styles.backLink}>
            ← Back to registry
          </Link>
          <p className={styles.eyebrow}>Registry Record</p>
          <div className={styles.titleRow}>
            <h1>{letter.reference_number}</h1>
            <StatusBadge value={letter.status} label={statusLabel(letter.status)} />
          </div>
        </div>
        <div className={styles.actions}>
          <Link to={`/app/letters/${id}/edit`} className={styles.editLink}>
            Edit
          </Link>
          {letter.status !== 'ARCHIVED' && (
            <button type="button" className={styles.archiveButton} onClick={() => setShowArchiveDialog(true)}>
              Archive Letter
            </button>
          )}
        </div>
      </div>

      {archiveError && <ErrorState message={archiveError} />}

      <div className={styles.dossier}>
        <div className={styles.dossierSection}>
          <h2 className={styles.dossierHeading}>Correspondence</h2>
          <dl className={styles.grid}>
            <Field label="Subject" value={letter.subject} />
            <Field label="Received" value={formatDateTime(letter.received_at)} />
            <Field label="Recorded" value={formatDateTime(letter.created_at)} />
            <Field label="Last updated" value={formatDateTime(letter.updated_at)} />
          </dl>
        </div>

        <div className={styles.dossierSection}>
          <h2 className={styles.dossierHeading}>Source</h2>
          <dl className={styles.grid}>
            <Field label="Source" value={letter.source_name} />
            <Field label="Source location" value={letter.source_location} />
          </dl>
        </div>

        <div className={styles.dossierSection}>
          <h2 className={styles.dossierHeading}>Sender</h2>
          <dl className={styles.grid}>
            <Field label="Sender name" value={letter.sender_name} />
            <Field label="Sender designation" value={letter.sender_designation} />
            <Field label="Sender's department" value={letter.sender_department} />
            <Field label="Sender address" value={letter.sender_address} />
          </dl>
        </div>

        <div className={styles.dossierSection}>
          <h2 className={styles.dossierHeading}>Additional details</h2>
          <dl className={styles.grid}>
            <Field label="Reason" value={letter.reason} />
          </dl>
        </div>
      </div>

      {letter.text_content && (
        <div className={styles.content}>
          <h2>Content</h2>
          <p>{letter.text_content}</p>
        </div>
      )}

      <div className={styles.documentsSection}>
        <div className={styles.sectionHeaderRow}>
          <h2>Documents</h2>
          {!documentsLoading && !documentsError && documents && (
            <span className={styles.docCount}>
              {documents.length} {documents.length === 1 ? 'attachment' : 'attachments'}
            </span>
          )}
        </div>
        <DocumentUploadForm letterId={id} onUploadSuccess={handleUploadSuccess} />
        {documentsLoading && <LoadingState label="Loading documents..." />}
        {!documentsLoading && documentsError && (
          <ErrorState message={documentsError.message} onRetry={fetchDocuments} />
        )}
        {!documentsLoading && !documentsError && documents && documents.length === 0 && (
          <EmptyState message="No documents have been uploaded for this letter yet." />
        )}
        {!documentsLoading && !documentsError && documents && documents.length > 0 && (
          <DocumentList letterId={id} documents={documents} />
        )}
      </div>

      {showArchiveDialog && (
        <ArchiveConfirmDialog
          referenceNumber={letter.reference_number}
          confirming={archiving}
          onConfirm={handleConfirmArchive}
          onCancel={() => setShowArchiveDialog(false)}
        />
      )}
    </section>
  )
}
