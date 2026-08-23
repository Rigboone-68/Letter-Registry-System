import { useCallback, useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'

import ConfirmDialog from '../components/ConfirmDialog'
import DepartmentForm from '../components/DepartmentForm'
import ErrorState from '../components/ErrorState'
import LoadingState from '../components/LoadingState'
import StatusBadge from '../components/StatusBadge'
import * as departmentService from '../services/departmentService'
import { validateDepartmentForm } from '../utils/formValidation'
import { statusLabel } from '../utils/statusLabels'
import styles from './AdminPages.module.css'

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
 * Department detail page (Phase 5D,
 * docs/architecture/administration-ui.md §4.1) — one page, an inline
 * edit mode rather than a separate route (the edit surface here is two
 * optional text fields, small enough that a route split would be pure
 * ceremony — a deliberate departure from `LetterFormPage`'s
 * separate-route convention, justified by the difference in form
 * complexity, not an inconsistency).
 *
 * Activate/Deactivate are both backend-idempotent
 * (`app/services/department_service.py`), but only Deactivate is
 * confirmed here — its operational impact (every ADMIN/USER in this
 * department immediately loses state-elevating, and per the backend's
 * own read/lock-down-vs-state-elevating asymmetry, potentially more,
 * access) is real even though the write itself is safe to repeat.
 * Activation only ever restores capability — nothing is lost by it.
 */
export default function DepartmentDetailPage() {
  const { id } = useParams()

  const [department, setDepartment] = useState(null)
  const [loading, setLoading] = useState(true)
  const [notFound, setNotFound] = useState(false)
  const [error, setError] = useState(null)

  const [editing, setEditing] = useState(false)
  const [form, setForm] = useState({ name: '', code: '' })
  const [fieldErrors, setFieldErrors] = useState({})
  const [formError, setFormError] = useState(null)
  const [saving, setSaving] = useState(false)

  const [showDeactivateDialog, setShowDeactivateDialog] = useState(false)
  const [actionPending, setActionPending] = useState(false)
  const [actionError, setActionError] = useState(null)

  const fetchDepartment = useCallback(() => {
    setLoading(true)
    setError(null)
    setNotFound(false)
    departmentService
      .get(id)
      .then((response) => {
        setDepartment(response)
        setForm({ name: response.name, code: response.code ?? '' })
      })
      .catch((normalizedError) => {
        if (normalizedError.status === 404) {
          setNotFound(true)
        } else {
          setError(normalizedError)
        }
      })
      .finally(() => setLoading(false))
  }, [id])

  useEffect(() => {
    fetchDepartment()
  }, [fetchDepartment])

  function handleFieldChange(event) {
    const { name, value } = event.target
    setForm((previous) => ({ ...previous, [name]: value }))
  }

  function startEditing() {
    setForm({ name: department.name, code: department.code ?? '' })
    setFieldErrors({})
    setFormError(null)
    setEditing(true)
  }

  async function handleSave(event) {
    event.preventDefault()
    setFormError(null)

    const errors = validateDepartmentForm(form)
    setFieldErrors(errors)
    if (Object.keys(errors).length > 0) return

    setSaving(true)
    try {
      const updated = await departmentService.update(id, { name: form.name, code: form.code || null })
      setDepartment(updated)
      setEditing(false)
    } catch (normalizedError) {
      if (normalizedError.fieldErrors) {
        setFieldErrors(normalizedError.fieldErrors)
      } else {
        setFormError(normalizedError.message ?? 'Unable to save this department.')
      }
    } finally {
      setSaving(false)
    }
  }

  async function handleActivate() {
    setActionPending(true)
    setActionError(null)
    try {
      const updated = await departmentService.activate(id)
      setDepartment(updated)
    } catch (normalizedError) {
      setActionError(normalizedError.message ?? 'Unable to activate this department.')
    } finally {
      setActionPending(false)
    }
  }

  async function handleConfirmDeactivate() {
    setActionPending(true)
    setActionError(null)
    try {
      const updated = await departmentService.deactivate(id)
      setDepartment(updated)
      setShowDeactivateDialog(false)
    } catch (normalizedError) {
      setActionError(normalizedError.message ?? 'Unable to deactivate this department.')
    } finally {
      setActionPending(false)
    }
  }

  if (loading) return <LoadingState label="Loading department..." />
  if (notFound) return <ErrorState message="Department not found." />
  if (error) return <ErrorState message={error.message} onRetry={fetchDepartment} />
  if (!department) return null

  return (
    <section className={styles.detailCard}>
      <div>
        <Link to="/app/system/departments" className={styles.backLink}>
          ← Back to departments
        </Link>
        <div className={styles.titleRow}>
          <h1>{department.name}</h1>
          <StatusBadge value={department.status} label={statusLabel(department.status)} domain="Department" />
        </div>
      </div>

      {actionError && <ErrorState message={actionError} />}

      {!editing && (
        <>
          <dl className={styles.grid}>
            <div className={styles.gridField}>
              <dt>Code</dt>
              <dd>{department.code ?? '—'}</dd>
            </div>
            <div className={styles.gridField}>
              <dt>Created</dt>
              <dd>{formatDateTime(department.created_at)}</dd>
            </div>
            <div className={styles.gridField}>
              <dt>Last updated</dt>
              <dd>{formatDateTime(department.updated_at)}</dd>
            </div>
          </dl>

          <div className={styles.actionsPanel}>
            <button type="button" onClick={startEditing}>
              Edit
            </button>
            {department.status !== 'ACTIVE' && (
              <button type="button" onClick={handleActivate} disabled={actionPending}>
                {actionPending ? 'Activating…' : 'Activate'}
              </button>
            )}
            {department.status !== 'INACTIVE' && (
              <button type="button" onClick={() => setShowDeactivateDialog(true)}>
                Deactivate
              </button>
            )}
          </div>
        </>
      )}

      {editing && (
        <form onSubmit={handleSave} noValidate className={styles.formCard}>
          {formError && <ErrorState message={formError} />}
          <DepartmentForm form={form} fieldErrors={fieldErrors} onChange={handleFieldChange} />
          <div className={styles.actions}>
            <button type="submit" className={styles.submit} disabled={saving}>
              {saving ? 'Saving…' : 'Save changes'}
            </button>
            <button type="button" className={styles.cancel} onClick={() => setEditing(false)}>
              Cancel
            </button>
          </div>
        </form>
      )}

      {showDeactivateDialog && (
        <ConfirmDialog
          title={`Deactivate ${department.name}?`}
          message="Admins and Users in this department will immediately lose access to state-elevating actions (and some read/lock-down actions), until it is reactivated. This department's record and history are not removed."
          confirmLabel="Deactivate Department"
          confirmingLabel="Deactivating…"
          tone="caution"
          confirming={actionPending}
          onConfirm={handleConfirmDeactivate}
          onCancel={() => setShowDeactivateDialog(false)}
        />
      )}
    </section>
  )
}
