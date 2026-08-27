import { useEffect, useRef, useState } from 'react'

import DepartmentSelector from './DepartmentSelector'
import styles from './ConfirmDialog.module.css'

/**
 * Admin department-transfer dialog (Phase 5D,
 * docs/architecture/administration-ui.md §9.3) —
 * `PATCH /api/v1/admins/{id}/department`. Not built on top of
 * `ConfirmDialog` directly (it needs its own input, not just a
 * confirm/cancel pair), but reuses the identical accessible-dialog
 * mechanics (`role="dialog"`, `aria-modal`, Escape-to-cancel, a Tab
 * trap — here across three focusable elements: the department select,
 * Cancel, and Confirm, in that order).
 *
 * States plainly, using the backend's own confirmed guarantee
 * (`app/services/admin_service.py:change_admin_department`'s own
 * docstring — verified fresh, not assumed): this changes only the
 * Admin's *current* department going forward. Historical Letters they
 * already recorded keep the department they were recorded under
 * forever — `Letter.recipient_department_id` is captured once, at
 * recording time, and never re-derived from the recorder later.
 *
 * Phase 5I.4C (docs/architecture/ui-design-system.md §6) gives this
 * high-impact action clearer visual separation — a bordered "current
 * department" block, the department field, then the consequences
 * paragraph — reordered for hierarchy only; its wording is byte-for-byte
 * unchanged (a test asserts the exact phrase "does not move or reassign
 * any historical record" verbatim), and no business semantics changed.
 */
export default function AdminTransferDialog({
  currentDepartmentName,
  departments,
  onConfirm,
  onCancel,
  confirming,
  error,
}) {
  const [departmentId, setDepartmentId] = useState('')
  const selectRef = useRef(null)
  const confirmRef = useRef(null)

  useEffect(() => {
    selectRef.current?.focus()

    function handleKeyDown(event) {
      if (event.key === 'Escape') {
        onCancel()
        return
      }
      if (event.key === 'Tab') {
        const first = selectRef.current
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
        aria-labelledby="transfer-dialog-title"
        onClick={(event) => event.stopPropagation()}
      >
        <h2 id="transfer-dialog-title">Transfer to a different department</h2>

        <div className={styles.currentInfo}>
          <p className={styles.currentInfoLabel}>Current department</p>
          <p className={styles.currentInfoValue}>{currentDepartmentName ?? 'None'}</p>
        </div>

        <div>
          <label htmlFor="transfer-department">New department</label>
          <DepartmentSelector
            id="transfer-department"
            name="department_id"
            ref={selectRef}
            departments={departments}
            value={departmentId}
            onChange={(event) => setDepartmentId(event.target.value)}
            activeOnly
            required
          />
        </div>

        <p className={styles.consequences}>
          This changes only this Admin's current department going forward. Letters
          they've already recorded remain attached to the department they belonged
          to when recorded — this action does not move or reassign any historical
          record.
        </p>

        {error && (
          <p role="alert" className={styles.error}>
            {error}
          </p>
        )}

        <div className={styles.actions}>
          <button type="button" onClick={onCancel} className={styles.cancel}>
            Cancel
          </button>
          <button
            type="button"
            ref={confirmRef}
            onClick={() => onConfirm(departmentId)}
            className={styles.confirm}
            disabled={confirming || !departmentId}
          >
            {confirming ? 'Transferring…' : 'Transfer Admin'}
          </button>
        </div>
      </div>
    </div>
  )
}
