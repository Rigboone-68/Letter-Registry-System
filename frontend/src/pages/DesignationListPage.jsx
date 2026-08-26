import { useCallback, useEffect, useState } from 'react'

import ConfirmDialog from '../components/ConfirmDialog'
import DesignationTable from '../components/DesignationTable'
import EmptyState from '../components/EmptyState'
import ErrorState from '../components/ErrorState'
import LoadingState from '../components/LoadingState'
import * as designationService from '../services/designationService'
import { validateDesignationForm } from '../utils/formValidation'
import styles from './AdminPages.module.css'

const EMPTY_FORM = { name: '' }

/**
 * Designation management page (Phase 5H,
 * docs/architecture/source-designation.md §10/§12) —
 * `GET/POST /api/v1/designations`,
 * `POST /api/v1/designations/{id}/activate|deactivate`. SYSTEM_ADMIN
 * only, deliberately a single combined page (create form + list +
 * lifecycle actions) rather than Department's separate list/create/
 * detail pages — the review's own explicit "do not overbuild this
 * page" instruction, since Designation has no other fields to edit
 * (no code, no description) and no detail worth a dedicated route.
 *
 * The system intentionally starts with zero Designations (no seed
 * list was invented, per explicit instruction) — this page is the
 * only way to add the organization's first one; until at least one
 * exists, the Letter form's own Designation dropdown has nothing to
 * offer (see `pages/LetterFormPage.jsx`'s own handling of that case).
 */
export default function DesignationListPage() {
  const [status, setStatus] = useState('')
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const [form, setForm] = useState(EMPTY_FORM)
  const [fieldErrors, setFieldErrors] = useState({})
  const [createError, setCreateError] = useState(null)
  const [creating, setCreating] = useState(false)

  const [deactivateTarget, setDeactivateTarget] = useState(null)
  const [acting, setActing] = useState(false)
  const [actionError, setActionError] = useState(null)

  const fetchDesignations = useCallback(() => {
    setLoading(true)
    setError(null)
    const params = status ? { status } : {}
    designationService
      .list(params)
      .then((response) => setData(response))
      .catch((normalizedError) => setError(normalizedError))
      .finally(() => setLoading(false))
  }, [status])

  useEffect(() => {
    fetchDesignations()
  }, [fetchDesignations])

  function handleChange(event) {
    const { name, value } = event.target
    setForm((previous) => ({ ...previous, [name]: value }))
  }

  async function handleCreate(event) {
    event.preventDefault()
    setCreateError(null)

    const errors = validateDesignationForm(form)
    setFieldErrors(errors)
    if (Object.keys(errors).length > 0) return

    setCreating(true)
    try {
      await designationService.create({ name: form.name })
      setForm(EMPTY_FORM)
      fetchDesignations()
    } catch (normalizedError) {
      if (normalizedError.fieldErrors) {
        setFieldErrors(normalizedError.fieldErrors)
      } else {
        setCreateError(normalizedError.message ?? 'Unable to create this designation.')
      }
    } finally {
      setCreating(false)
    }
  }

  async function handleActivate(designation) {
    setActing(true)
    setActionError(null)
    try {
      const updated = await designationService.activate(designation.id)
      setData((previous) => ({
        ...previous,
        items: previous.items.map((item) => (item.id === updated.id ? updated : item)),
      }))
    } catch (normalizedError) {
      setActionError(normalizedError.message ?? 'Unable to activate this designation.')
    } finally {
      setActing(false)
    }
  }

  async function handleConfirmDeactivate() {
    setActing(true)
    setActionError(null)
    try {
      const updated = await designationService.deactivate(deactivateTarget.id)
      setData((previous) => ({
        ...previous,
        items: previous.items.map((item) => (item.id === updated.id ? updated : item)),
      }))
      setDeactivateTarget(null)
    } catch (normalizedError) {
      setActionError(normalizedError.message ?? 'Unable to deactivate this designation.')
    } finally {
      setActing(false)
    }
  }

  return (
    <section className={styles.root}>
      <div className={styles.header}>
        <div>
          <h1>Designations</h1>
          {data && <p className={styles.count}>{data.total} total</p>}
        </div>
        <div className={styles.headerActions}>
          <button type="button" onClick={fetchDesignations}>
            Refresh
          </button>
        </div>
      </div>

      <form onSubmit={handleCreate} noValidate className={styles.formCard}>
        {createError && <ErrorState message={createError} />}
        <div className={styles.field}>
          <label htmlFor="designation-name">New designation name *</label>
          <input
            id="designation-name"
            name="name"
            type="text"
            required
            value={form.name}
            onChange={handleChange}
            aria-invalid={Boolean(fieldErrors.name)}
            aria-describedby={fieldErrors.name ? 'designation-name-error' : undefined}
          />
          {fieldErrors.name && (
            <span id="designation-name-error" role="alert" className={styles.fieldError}>
              {fieldErrors.name}
            </span>
          )}
        </div>
        <div className={styles.actions}>
          <button type="submit" className={styles.submit} disabled={creating}>
            {creating ? 'Creating…' : 'Add Designation'}
          </button>
        </div>
      </form>

      <div className={styles.filters}>
        <div className={styles.field}>
          <label htmlFor="designation-status-filter">Status</label>
          <select
            id="designation-status-filter"
            value={status}
            onChange={(event) => setStatus(event.target.value)}
          >
            <option value="">Any</option>
            <option value="ACTIVE">Active</option>
            <option value="INACTIVE">Inactive</option>
          </select>
        </div>
      </div>

      {actionError && <ErrorState message={actionError} />}

      {loading && <LoadingState label="Loading designations..." />}
      {!loading && error && <ErrorState message={error.message} onRetry={fetchDesignations} />}
      {!loading && !error && data && data.items.length === 0 && (
        <EmptyState message="No designations match the current filter." />
      )}
      {!loading && !error && data && data.items.length > 0 && (
        <DesignationTable
          designations={data.items}
          onActivate={handleActivate}
          onDeactivate={(designation) => setDeactivateTarget(designation)}
          actingId={acting ? deactivateTarget?.id : null}
        />
      )}

      {deactivateTarget && (
        <ConfirmDialog
          title={`Deactivate "${deactivateTarget.name}"?`}
          message="Letters that already use this designation keep it unchanged and remain fully readable and editable. Once deactivated, it can no longer be selected for a new or changed designation assignment until reactivated."
          confirmLabel="Deactivate Designation"
          confirmingLabel="Deactivating…"
          tone="caution"
          confirming={acting}
          onConfirm={handleConfirmDeactivate}
          onCancel={() => setDeactivateTarget(null)}
        />
      )}
    </section>
  )
}
