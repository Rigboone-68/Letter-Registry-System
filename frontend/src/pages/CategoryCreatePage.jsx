import { useState } from 'react'
import { useNavigate } from 'react-router-dom'

import CategoryForm from '../components/CategoryForm'
import ErrorState from '../components/ErrorState'
import * as categoryService from '../services/categoryService'
import { validateCategoryForm } from '../utils/formValidation'
import styles from './AdminPages.module.css'

const EMPTY_FORM = { name: '', description: '' }

/**
 * Category creation page (Phase 5H.1, mirroring
 * `DepartmentCreatePage.jsx`) — `POST /api/v1/categories`. New
 * categories are always created `ACTIVE` server-side
 * (`CategoryService.create_category`'s own docstring) — there is no
 * status field on this form, nothing for one to bind to.
 */
export default function CategoryCreatePage() {
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

    const errors = validateCategoryForm(form)
    setFieldErrors(errors)
    if (Object.keys(errors).length > 0) return

    setSubmitting(true)
    try {
      const category = await categoryService.create({
        name: form.name,
        description: form.description || null,
      })
      navigate(`/app/system/categories/${category.id}`, { replace: true })
    } catch (normalizedError) {
      if (normalizedError.fieldErrors) {
        setFieldErrors(normalizedError.fieldErrors)
      } else {
        setFormError(normalizedError.message ?? 'Unable to create this category.')
      }
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <section className={styles.root}>
      <div className={styles.headerText}>
        <p className={styles.eyebrow}>Category Master Data</p>
        <div className={styles.titleRow}>
          <h1>Create Category</h1>
          <span className={styles.headerMark} aria-hidden="true" />
        </div>
      </div>
      <form onSubmit={handleSubmit} noValidate className={styles.formCard}>
        {formError && <ErrorState message={formError} />}

        <CategoryForm form={form} fieldErrors={fieldErrors} onChange={handleChange} />

        <div className={styles.actions}>
          <button type="submit" className={styles.submit} disabled={submitting}>
            {submitting ? 'Creating…' : 'Create Category'}
          </button>
          <button
            type="button"
            className={styles.cancel}
            onClick={() => navigate('/app/system/categories')}
          >
            Cancel
          </button>
        </div>
      </form>
    </section>
  )
}
