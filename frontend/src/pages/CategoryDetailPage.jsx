import { useCallback, useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'

import CategoryForm from '../components/CategoryForm'
import ConfirmDialog from '../components/ConfirmDialog'
import ErrorState from '../components/ErrorState'
import LoadingState from '../components/LoadingState'
import StatusBadge from '../components/StatusBadge'
import * as categoryService from '../services/categoryService'
import { validateCategoryForm } from '../utils/formValidation'
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
 * Category detail page (Phase 5H.1, mirroring
 * `DepartmentDetailPage.jsx` exactly) — one page, an inline edit mode
 * rather than a separate route, matching Department's own precedent
 * for a form this small.
 *
 * Activate/Deactivate are both backend-idempotent
 * (`app/services/category_service.py`), but only Deactivate is
 * confirmed here — a Letter already tagged with this category keeps
 * its reference either way (never deleted), but a retired category
 * should no longer be assignable to a *new* letter without a
 * deliberate confirmation, matching Department's own confirmation-
 * matrix precedent (Deactivate confirmed, Activate purely restorative).
 */
export default function CategoryDetailPage() {
  const { id } = useParams()

  const [category, setCategory] = useState(null)
  const [loading, setLoading] = useState(true)
  const [notFound, setNotFound] = useState(false)
  const [error, setError] = useState(null)

  const [editing, setEditing] = useState(false)
  const [form, setForm] = useState({ name: '', description: '' })
  const [fieldErrors, setFieldErrors] = useState({})
  const [formError, setFormError] = useState(null)
  const [saving, setSaving] = useState(false)

  const [showDeactivateDialog, setShowDeactivateDialog] = useState(false)
  const [actionPending, setActionPending] = useState(false)
  const [actionError, setActionError] = useState(null)

  const fetchCategory = useCallback(() => {
    setLoading(true)
    setError(null)
    setNotFound(false)
    categoryService
      .get(id)
      .then((response) => {
        setCategory(response)
        setForm({ name: response.name, description: response.description ?? '' })
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
    fetchCategory()
  }, [fetchCategory])

  function handleFieldChange(event) {
    const { name, value } = event.target
    setForm((previous) => ({ ...previous, [name]: value }))
  }

  function startEditing() {
    setForm({ name: category.name, description: category.description ?? '' })
    setFieldErrors({})
    setFormError(null)
    setEditing(true)
  }

  async function handleSave(event) {
    event.preventDefault()
    setFormError(null)

    const errors = validateCategoryForm(form)
    setFieldErrors(errors)
    if (Object.keys(errors).length > 0) return

    setSaving(true)
    try {
      const updated = await categoryService.update(id, {
        name: form.name,
        description: form.description || null,
      })
      setCategory(updated)
      setEditing(false)
    } catch (normalizedError) {
      if (normalizedError.fieldErrors) {
        setFieldErrors(normalizedError.fieldErrors)
      } else {
        setFormError(normalizedError.message ?? 'Unable to save this category.')
      }
    } finally {
      setSaving(false)
    }
  }

  async function handleActivate() {
    setActionPending(true)
    setActionError(null)
    try {
      const updated = await categoryService.activate(id)
      setCategory(updated)
    } catch (normalizedError) {
      setActionError(normalizedError.message ?? 'Unable to activate this category.')
    } finally {
      setActionPending(false)
    }
  }

  async function handleConfirmDeactivate() {
    setActionPending(true)
    setActionError(null)
    try {
      const updated = await categoryService.deactivate(id)
      setCategory(updated)
      setShowDeactivateDialog(false)
    } catch (normalizedError) {
      setActionError(normalizedError.message ?? 'Unable to deactivate this category.')
    } finally {
      setActionPending(false)
    }
  }

  if (loading) return <LoadingState label="Loading category..." />
  if (notFound) return <ErrorState message="Category not found." />
  if (error) return <ErrorState message={error.message} onRetry={fetchCategory} />
  if (!category) return null

  return (
    <section className={styles.detailCard}>
      <div>
        <Link to="/app/system/categories" className={styles.backLink}>
          ← Back to categories
        </Link>
        <p className={styles.eyebrow}>Category Master Data</p>
        <div className={styles.titleRow}>
          <h1>{category.name}</h1>
          <StatusBadge value={category.status} label={statusLabel(category.status)} domain="Category" />
        </div>
      </div>

      {actionError && <ErrorState message={actionError} />}

      {!editing && (
        <>
          <dl className={styles.grid}>
            <div className={styles.gridField}>
              <dt>Description</dt>
              <dd>{category.description ?? '—'}</dd>
            </div>
            <div className={styles.gridField}>
              <dt>Created</dt>
              <dd>{formatDateTime(category.created_at)}</dd>
            </div>
            <div className={styles.gridField}>
              <dt>Last updated</dt>
              <dd>{formatDateTime(category.updated_at)}</dd>
            </div>
          </dl>

          <div className={styles.actionsPanel}>
            <button type="button" onClick={startEditing}>
              Edit
            </button>
            {category.status !== 'ACTIVE' && (
              <button type="button" onClick={handleActivate} disabled={actionPending}>
                {actionPending ? 'Activating…' : 'Activate'}
              </button>
            )}
            {category.status !== 'INACTIVE' && (
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
          <CategoryForm form={form} fieldErrors={fieldErrors} onChange={handleFieldChange} />
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
          title={`Deactivate ${category.name}?`}
          message="Letters already tagged with this category keep it unchanged and remain fully readable and editable. Once deactivated, it can no longer be assigned to a new or changed Letter until reactivated."
          confirmLabel="Deactivate Category"
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
