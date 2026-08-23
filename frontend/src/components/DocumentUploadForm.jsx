import { useRef, useState } from 'react'

import ErrorState from './ErrorState'
import * as documentService from '../services/documentService'
import { ALLOWED_DOCUMENT_EXTENSIONS, MAX_DOCUMENT_SIZE_BYTES } from '../services/documentService'
import { validateDocumentFile } from '../utils/formValidation'
import styles from './DocumentUploadForm.module.css'

const MAX_SIZE_LABEL = `${(MAX_DOCUMENT_SIZE_BYTES / (1024 * 1024)).toFixed(0)} MB`
const ACCEPT_ATTRIBUTE = ALLOWED_DOCUMENT_EXTENSIONS.map((extension) => `.${extension}`).join(',')

/**
 * Inline document upload form (Phase 5E,
 * docs/architecture/document-notification-ui.md §3, §5) — mounted
 * directly inside `LetterDetailPage`'s Documents section, not a modal
 * or a separate page/route (a document has no independent existence to
 * navigate to). Client-side extension/size pre-checks are a UX nicety
 * only, never authoritative — the backend's own magic-byte content-
 * signature sniff remains the real check, and a `422`/`413` from it is
 * rendered exactly like any other backend rejection, never assumed
 * already covered by the pre-check.
 *
 * "Replacement" is not a concept this form has any notion of — every
 * successful submission is simply another upload; the prior document
 * (if any) is never referenced, hidden, or implied to be superseded.
 */
export default function DocumentUploadForm({ letterId, onUploadSuccess }) {
  const [file, setFile] = useState(null)
  const [fieldError, setFieldError] = useState(null)
  const [formError, setFormError] = useState(null)
  const [uploading, setUploading] = useState(false)
  const [progress, setProgress] = useState(null)
  const inputRef = useRef(null)

  function handleFileChange(event) {
    setFile(event.target.files[0] ?? null)
    setFieldError(null)
    setFormError(null)
  }

  async function handleSubmit(event) {
    event.preventDefault()
    setFormError(null)

    const error = validateDocumentFile(file, {
      allowedExtensions: ALLOWED_DOCUMENT_EXTENSIONS,
      maxSizeBytes: MAX_DOCUMENT_SIZE_BYTES,
    })
    setFieldError(error)
    if (error) return

    setUploading(true)
    setProgress(0)
    try {
      const document = await documentService.upload(letterId, file, (progressEvent) => {
        if (progressEvent.total) {
          setProgress(Math.round((progressEvent.loaded / progressEvent.total) * 100))
        }
      })
      setFile(null)
      setFieldError(null)
      if (inputRef.current) inputRef.current.value = ''
      onUploadSuccess(document)
    } catch (normalizedError) {
      // Failed uploads keep the selected file in place — retrying just
      // means submitting again, not re-choosing the file.
      setFormError(normalizedError.message ?? 'Unable to upload this document.')
    } finally {
      setUploading(false)
      setProgress(null)
    }
  }

  return (
    <form onSubmit={handleSubmit} noValidate className={styles.form}>
      {formError && <ErrorState message={formError} />}

      <div className={styles.field}>
        <label htmlFor="document-file">Upload document</label>
        <input
          id="document-file"
          name="file"
          type="file"
          ref={inputRef}
          accept={ACCEPT_ATTRIBUTE}
          onChange={handleFileChange}
          disabled={uploading}
          aria-invalid={Boolean(fieldError)}
          aria-describedby={fieldError ? 'document-file-hint document-file-error' : 'document-file-hint'}
        />
        <p id="document-file-hint" className={styles.hint}>
          Accepted types: {ALLOWED_DOCUMENT_EXTENSIONS.join(', ')}. Maximum size: {MAX_SIZE_LABEL}.
        </p>
        {fieldError && (
          <span id="document-file-error" role="alert" className={styles.fieldError}>
            {fieldError}
          </span>
        )}
      </div>

      {uploading && (
        <p role="status" className={styles.progress}>
          {progress != null ? `Uploading… ${progress}%` : 'Uploading…'}
        </p>
      )}

      <button type="submit" className={styles.submit} disabled={uploading}>
        {uploading ? 'Uploading…' : 'Upload document'}
      </button>
    </form>
  )
}
