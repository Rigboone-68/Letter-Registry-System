import { useEffect, useRef } from 'react'

import styles from './ArchiveConfirmDialog.module.css'

/**
 * Confirmation dialog for archiving a Letter (docs/architecture/
 * frontend.md §17/§19, Phase 5C). Deliberately never says "delete" or
 * "permanently" — `DELETE /api/v1/letters/{id}` is a soft status
 * transition (`ACTIVE` → `ARCHIVED`), never a physical row deletion
 * (`backend/app/api/v1/endpoints/letters.py`'s own summary: "Archive a
 * letter (soft-delete — never a physical DELETE)").
 *
 * A minimal, dependency-free accessible dialog: `role="dialog"`,
 * `aria-modal`, initial focus on the safe default (Cancel), Escape
 * cancels, and Tab is trapped between the two actions rather than
 * escaping to the page behind it.
 */
export default function ArchiveConfirmDialog({ referenceNumber, onConfirm, onCancel, confirming }) {
  const cancelRef = useRef(null)
  const confirmRef = useRef(null)

  useEffect(() => {
    cancelRef.current?.focus()

    function handleKeyDown(event) {
      if (event.key === 'Escape') {
        onCancel()
        return
      }
      if (event.key === 'Tab') {
        const first = cancelRef.current
        const last = confirmRef.current
        if (event.shiftKey && document.activeElement === first) {
          event.preventDefault()
          last?.focus()
        } else if (!event.shiftKey && document.activeElement === last) {
          event.preventDefault()
          first?.focus()
        }
      }
    }

    document.addEventListener('keydown', handleKeyDown)
    return () => document.removeEventListener('keydown', handleKeyDown)
  }, [onCancel])

  return (
    <div className={styles.backdrop} onClick={onCancel}>
      <div
        className={styles.dialog}
        role="dialog"
        aria-modal="true"
        aria-labelledby="archive-dialog-title"
        onClick={(event) => event.stopPropagation()}
      >
        <h2 id="archive-dialog-title">Archive letter {referenceNumber}?</h2>
        <p>
          This moves the letter to Archived status. It remains fully visible in the
          registry and can still be opened — archiving does not delete or hide its
          record.
        </p>
        <div className={styles.actions}>
          <button type="button" ref={cancelRef} onClick={onCancel} className={styles.cancel}>
            Cancel
          </button>
          <button
            type="button"
            ref={confirmRef}
            onClick={onConfirm}
            className={styles.confirm}
            disabled={confirming}
          >
            {confirming ? 'Archiving…' : 'Archive Letter'}
          </button>
        </div>
      </div>
    </div>
  )
}
