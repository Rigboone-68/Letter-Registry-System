import { useEffect, useRef } from 'react'

import styles from './ConfirmDialog.module.css'

/**
 * Generic accessible confirmation dialog (Phase 5D,
 * docs/architecture/administration-ui.md §14.2) — the same dialog
 * mechanics `components/ArchiveConfirmDialog.jsx` (Phase 5C) already
 * proved: `role="dialog"`, `aria-modal`, initial focus on the safe
 * default (Cancel), Escape cancels, Tab trapped between the two
 * actions. Generalized here so every Phase 5D confirmation (deactivate
 * Department/Admin/User, approve Admin/User, revoke a User
 * authorization) reuses one component instead of six near-identical
 * ones — see the architecture doc for why `ArchiveConfirmDialog` itself
 * is left as-is rather than refactored onto this (out of this phase's
 * scope: no Letter file is touched).
 *
 * `tone` only ever affects visual weight, never wording — the caller
 * always supplies exact, action-specific copy (never a generic "Are you
 * sure?"), so a screen reader user and a sighted user get the same
 * information.
 */
export default function ConfirmDialog({
  title,
  message,
  confirmLabel,
  confirmingLabel,
  onConfirm,
  onCancel,
  confirming,
  tone = 'default',
}) {
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
        aria-labelledby="confirm-dialog-title"
        onClick={(event) => event.stopPropagation()}
      >
        <h2 id="confirm-dialog-title">{title}</h2>
        <p>{message}</p>
        <div className={styles.actions}>
          <button type="button" ref={cancelRef} onClick={onCancel} className={styles.cancel}>
            Cancel
          </button>
          <button
            type="button"
            ref={confirmRef}
            onClick={onConfirm}
            className={tone === 'caution' ? styles.confirmCaution : styles.confirm}
            disabled={confirming}
          >
            {confirming ? confirmingLabel ?? 'Working…' : confirmLabel}
          </button>
        </div>
      </div>
    </div>
  )
}
