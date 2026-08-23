import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'

import DepartmentSelector from '../components/DepartmentSelector'
import ErrorState from '../components/ErrorState'
import LoadingState from '../components/LoadingState'
import * as adminService from '../services/adminService'
import * as departmentService from '../services/departmentService'
import { validateAdminAuthorizeForm } from '../utils/formValidation'
import styles from './AdminPages.module.css'

const EMPTY_FORM = { email: '', department_id: '' }

/**
 * Admin authorization form (Phase 5D,
 * docs/architecture/administration-ui.md §4.2/§10) —
 * `POST /api/v1/admins/authorizations`. A dedicated form, deliberately
 * kept separate from `UserAuthorizePage` (§6.3 of the review): the
 * department field here is a real, meaningful selection a System Admin
 * makes (`AdminAuthorizationCreate {email, department_id}`), unlike
 * User authorization, whose schema has no such field at all — merging
 * the two into one conditionally-rendered form would obscure that
 * structural difference for a small amount of saved duplication.
 *
 * This creates an *authorization* — permission for a candidate to sign
 * up — never an account. There is no Admin to navigate to yet, so a
 * successful submission returns to the Administrators list, not a
 * detail page.
 */
export default function AdminAuthorizePage() {
  const navigate = useNavigate()

  const [departments, setDepartments] = useState(null)
  const [loadError, setLoadError] = useState(null)

  const [form, setForm] = useState(EMPTY_FORM)
  const [fieldErrors, setFieldErrors] = useState({})
  const [formError, setFormError] = useState(null)
  const [submitting, setSubmitting] = useState(false)

  useEffect(() => {
    departmentService
      .list({ status: 'ACTIVE' })
      .then((response) => setDepartments(response.items))
      .catch((normalizedError) => setLoadError(normalizedError))
  }, [])

  function handleChange(event) {
    const { name, value } = event.target
    setForm((previous) => ({ ...previous, [name]: value }))
  }

  async function handleSubmit(event) {
    event.preventDefault()
    setFormError(null)

    const errors = validateAdminAuthorizeForm(form)
    setFieldErrors(errors)
    if (Object.keys(errors).length > 0) return

    setSubmitting(true)
    try {
      await adminService.authorize(form)
      navigate('/app/system/admins', { replace: true })
    } catch (normalizedError) {
      if (normalizedError.fieldErrors) {
        setFieldErrors(normalizedError.fieldErrors)
      } else {
        setFormError(normalizedError.message ?? 'Unable to authorize this email.')
      }
    } finally {
      setSubmitting(false)
    }
  }

  if (loadError) return <ErrorState message={loadError.message} />
  if (!departments) return <LoadingState label="Loading departments..." />

  return (
    <section className={styles.root}>
      <h1>Authorize new Admin</h1>
      <form onSubmit={handleSubmit} noValidate className={styles.formCard}>
        {formError && <ErrorState message={formError} />}

        <div className={styles.field}>
          <label htmlFor="admin-authorize-email">Email *</label>
          <input
            id="admin-authorize-email"
            name="email"
            type="email"
            required
            value={form.email}
            onChange={handleChange}
            aria-invalid={Boolean(fieldErrors.email)}
            aria-describedby={fieldErrors.email ? 'admin-authorize-email-error' : undefined}
          />
          {fieldErrors.email && (
            <span id="admin-authorize-email-error" role="alert" className={styles.fieldError}>
              {fieldErrors.email}
            </span>
          )}
        </div>

        <div className={styles.field}>
          <label htmlFor="admin-authorize-department">Department *</label>
          <DepartmentSelector
            id="admin-authorize-department"
            name="department_id"
            departments={departments}
            value={form.department_id}
            onChange={handleChange}
            activeOnly
            required
            aria-invalid={Boolean(fieldErrors.department_id)}
            aria-describedby={fieldErrors.department_id ? 'admin-authorize-department-error' : undefined}
          />
          {fieldErrors.department_id && (
            <span id="admin-authorize-department-error" role="alert" className={styles.fieldError}>
              {fieldErrors.department_id}
            </span>
          )}
        </div>

        <div className={styles.actions}>
          <button type="submit" className={styles.submit} disabled={submitting}>
            {submitting ? 'Authorizing…' : 'Authorize Admin'}
          </button>
          <button type="button" className={styles.cancel} onClick={() => navigate('/app/system/admins')}>
            Cancel
          </button>
        </div>
      </form>
    </section>
  )
}
