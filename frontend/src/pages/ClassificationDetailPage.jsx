import { useCallback, useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'

import ClassificationForm from '../components/ClassificationForm'
import ConfirmDialog from '../components/ConfirmDialog'
import ErrorState from '../components/ErrorState'
import LoadingState from '../components/LoadingState'
import StatusBadge from '../components/StatusBadge'
import * as classificationService from '../services/classificationService'
import { validateClassificationForm } from '../utils/formValidation'
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
 * Classification detail page (Phase 5H.1, mirroring
 * `CategoryDetailPage.jsx`/`DepartmentDetailPage.jsx`) — one page, an
 * inline edit mode. Displays `restricts_access` as plain text (never
 * color-only) alongside the status badge.
 *
 * **Security note, unchanged by this phase**: this page only ever
 * forwards the SYSTEM_ADMIN caller's own explicit `restricts_access`
 * choice to the backend — it never infers, computes, or enforces
 * classified-access visibility itself. Whether a given USER can see a
 * Letter tagged with this classification remains entirely
 * `assert_letter_access`'s decision, on the backend, exercised at
 * Letter read/list time — nothing here participates in that decision.
 */
export default function ClassificationDetailPage() {
  const { id } = useParams()

  const [classification, setClassification] = useState(null)
  const [loading, setLoading] = useState(true)
  const [notFound, setNotFound] = useState(false)
  const [error, setError] = useState(null)

  const [editing, setEditing] = useState(false)
  const [form, setForm] = useState({ name: '', description: '', restricts_access: false })
  const [fieldErrors, setFieldErrors] = useState({})
  const [formError, setFormError] = useState(null)
  const [saving, setSaving] = useState(false)

  const [showDeactivateDialog, setShowDeactivateDialog] = useState(false)
  const [actionPending, setActionPending] = useState(false)
  const [actionError, setActionError] = useState(null)

  const fetchClassification = useCallback(() => {
    setLoading(true)
    setError(null)
    setNotFound(false)
    classificationService
      .get(id)
      .then((response) => {
        setClassification(response)
        setForm({
          name: response.name,
          description: response.description ?? '',
          restricts_access: response.restricts_access,
        })
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
    fetchClassification()
  }, [fetchClassification])

  function handleFieldChange(event) {
    const { name, value, type, checked } = event.target
    setForm((previous) => ({ ...previous, [name]: type === 'checkbox' ? checked : value }))
  }

  function startEditing() {
    setForm({
      name: classification.name,
      description: classification.description ?? '',
      restricts_access: classification.restricts_access,
    })
    setFieldErrors({})
    setFormError(null)
    setEditing(true)
  }

  async function handleSave(event) {
    event.preventDefault()
    setFormError(null)

    const errors = validateClassificationForm(form)
    setFieldErrors(errors)
    if (Object.keys(errors).length > 0) return

    setSaving(true)
    try {
      const updated = await classificationService.update(id, {
        name: form.name,
        description: form.description || null,
        restricts_access: form.restricts_access,
      })
      setClassification(updated)
      setEditing(false)
    } catch (normalizedError) {
      if (normalizedError.fieldErrors) {
        setFieldErrors(normalizedError.fieldErrors)
      } else {
        setFormError(normalizedError.message ?? 'Unable to save this classification.')
      }
    } finally {
      setSaving(false)
    }
  }

  async function handleActivate() {
    setActionPending(true)
    setActionError(null)
    try {
      const updated = await classificationService.activate(id)
      setClassification(updated)
    } catch (normalizedError) {
      setActionError(normalizedError.message ?? 'Unable to activate this classification.')
    } finally {
      setActionPending(false)
    }
  }

  async function handleConfirmDeactivate() {
    setActionPending(true)
    setActionError(null)
    try {
      const updated = await classificationService.deactivate(id)
      setClassification(updated)
      setShowDeactivateDialog(false)
    } catch (normalizedError) {
      setActionError(normalizedError.message ?? 'Unable to deactivate this classification.')
    } finally {
      setActionPending(false)
    }
  }

  if (loading) return <LoadingState label="Loading classification..." />
  if (notFound) return <ErrorState message="Classification not found." />
  if (error) return <ErrorState message={error.message} onRetry={fetchClassification} />
  if (!classification) return null

  return (
    <section className={styles.detailCard}>
      <div>
        <Link to="/app/system/classifications" className={styles.backLink}>
          ← Back to classifications
        </Link>
        <p className={styles.eyebrow}>Classification Master Data</p>
        <div className={styles.titleRow}>
          <h1>{classification.name}</h1>
          <StatusBadge
            value={classification.status}
            label={statusLabel(classification.status)}
            domain="Classification"
          />
        </div>
      </div>

      {actionError && <ErrorState message={actionError} />}

      {!editing && (
        <>
          <dl className={styles.grid}>
            <div className={styles.gridField}>
              <dt>Description</dt>
              <dd>{classification.description ?? '—'}</dd>
            </div>
            <div className={styles.gridField}>
              <dt>Restricts access to classified Letters</dt>
              <dd>{classification.restricts_access ? 'Yes' : 'No'}</dd>
            </div>
            <div className={styles.gridField}>
              <dt>Created</dt>
              <dd>{formatDateTime(classification.created_at)}</dd>
            </div>
            <div className={styles.gridField}>
              <dt>Last updated</dt>
              <dd>{formatDateTime(classification.updated_at)}</dd>
            </div>
          </dl>

          <div className={styles.actionsPanel}>
            <button type="button" onClick={startEditing}>
              Edit
            </button>
            {classification.status !== 'ACTIVE' && (
              <button type="button" onClick={handleActivate} disabled={actionPending}>
                {actionPending ? 'Activating…' : 'Activate'}
              </button>
            )}
            {classification.status !== 'INACTIVE' && (
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
          <ClassificationForm form={form} fieldErrors={fieldErrors} onChange={handleFieldChange} />
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
          title={`Deactivate ${classification.name}?`}
          message="Letters already tagged with this classification keep it unchanged and remain fully readable and editable, subject to the same access rules as always. Once deactivated, it can no longer be assigned to a new or changed Letter until reactivated."
          confirmLabel="Deactivate Classification"
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
