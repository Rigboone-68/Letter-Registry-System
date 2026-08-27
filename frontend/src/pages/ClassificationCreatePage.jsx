import { useState } from 'react'
import { useNavigate } from 'react-router-dom'

import ClassificationForm from '../components/ClassificationForm'
import ErrorState from '../components/ErrorState'
import * as classificationService from '../services/classificationService'
import { validateClassificationForm } from '../utils/formValidation'
import styles from './AdminPages.module.css'

const EMPTY_FORM = { name: '', description: '', restricts_access: false }

/**
 * Classification creation page (Phase 5H.1, mirroring
 * `CategoryCreatePage.jsx`) — `POST /api/v1/classifications`. New
 * classifications are always created `ACTIVE` server-side; `restricts_access`
 * defaults to `false` unless explicitly checked — a brand-new
 * classification never restricts access until a SYSTEM_ADMIN
 * deliberately opts it in, matching the backend's own default exactly.
 */
export default function ClassificationCreatePage() {
  const navigate = useNavigate()

  const [form, setForm] = useState(EMPTY_FORM)
  const [fieldErrors, setFieldErrors] = useState({})
  const [formError, setFormError] = useState(null)
  const [submitting, setSubmitting] = useState(false)

  function handleChange(event) {
    const { name, value, type, checked } = event.target
    setForm((previous) => ({ ...previous, [name]: type === 'checkbox' ? checked : value }))
  }

  async function handleSubmit(event) {
    event.preventDefault()
    setFormError(null)

    const errors = validateClassificationForm(form)
    setFieldErrors(errors)
    if (Object.keys(errors).length > 0) return

    setSubmitting(true)
    try {
      const classification = await classificationService.create({
        name: form.name,
        description: form.description || null,
        restricts_access: form.restricts_access,
      })
      navigate(`/app/system/classifications/${classification.id}`, { replace: true })
    } catch (normalizedError) {
      if (normalizedError.fieldErrors) {
        setFieldErrors(normalizedError.fieldErrors)
      } else {
        setFormError(normalizedError.message ?? 'Unable to create this classification.')
      }
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <section className={styles.root}>
      <div className={styles.headerText}>
        <p className={styles.eyebrow}>Classification Master Data</p>
        <div className={styles.titleRow}>
          <h1>Create Classification</h1>
          <span className={styles.headerMark} aria-hidden="true" />
        </div>
      </div>
      <form onSubmit={handleSubmit} noValidate className={styles.formCard}>
        {formError && <ErrorState message={formError} />}

        <ClassificationForm form={form} fieldErrors={fieldErrors} onChange={handleChange} />

        <div className={styles.actions}>
          <button type="submit" className={styles.submit} disabled={submitting}>
            {submitting ? 'Creating…' : 'Create Classification'}
          </button>
          <button
            type="button"
            className={styles.cancel}
            onClick={() => navigate('/app/system/classifications')}
          >
            Cancel
          </button>
        </div>
      </form>
    </section>
  )
}
