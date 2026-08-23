import { useState } from 'react'
import { useNavigate } from 'react-router-dom'

import DepartmentForm from '../components/DepartmentForm'
import ErrorState from '../components/ErrorState'
import * as departmentService from '../services/departmentService'
import { validateDepartmentForm } from '../utils/formValidation'
import styles from './AdminPages.module.css'

const EMPTY_FORM = { name: '', code: '' }

/**
 * Department creation page (Phase 5D,
 * docs/architecture/administration-ui.md §4.1) — `POST /api/v1/departments`.
 * New departments are always created `ACTIVE` server-side
 * (`DepartmentService.create_department`'s own docstring) — there is no
 * status field on this form, nothing for one to bind to.
 */
export default function DepartmentCreatePage() {
  const navigate = useNavigate()

  const [form, setForm] = useState(EMPTY_FORM)
  const [fieldErrors, setFieldErrors] = useState({})
  const [formError, setFormError] = useState(null)
  const [submitting, setSubmitting] = useState(false)

  function handleChange(event) {
    const { name, value } = event.target
    setForm((previous) => ({ ...previous, [name]: value }))
  }

  async function handleSubmit(event) {
    event.preventDefault()
    setFormError(null)

    const errors = validateDepartmentForm(form)
    setFieldErrors(errors)
    if (Object.keys(errors).length > 0) return

    setSubmitting(true)
    try {
      const department = await departmentService.create({
        name: form.name,
        code: form.code || null,
      })
      navigate(`/app/system/departments/${department.id}`, { replace: true })
    } catch (normalizedError) {
      if (normalizedError.fieldErrors) {
        setFieldErrors(normalizedError.fieldErrors)
      } else {
        setFormError(normalizedError.message ?? 'Unable to create this department.')
      }
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <section className={styles.root}>
      <h1>Create Department</h1>
      <form onSubmit={handleSubmit} noValidate className={styles.formCard}>
        {formError && <ErrorState message={formError} />}

        <DepartmentForm form={form} fieldErrors={fieldErrors} onChange={handleChange} />

        <div className={styles.actions}>
          <button type="submit" className={styles.submit} disabled={submitting}>
            {submitting ? 'Creating…' : 'Create Department'}
          </button>
          <button
            type="button"
            className={styles.cancel}
            onClick={() => navigate('/app/system/departments')}
          >
            Cancel
          </button>
        </div>
      </form>
    </section>
  )
}
