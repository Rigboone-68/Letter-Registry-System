import { useState } from 'react'
import { useNavigate } from 'react-router-dom'

import ErrorState from '../components/ErrorState'
import * as userService from '../services/userService'
import { validateUserAuthorizeForm } from '../utils/formValidation'
import styles from './AdminPages.module.css'

const EMPTY_FORM = { email: '' }

/**
 * User authorization form (Phase 5D,
 * docs/architecture/administration-ui.md §5/§6/§13) —
 * `POST /api/v1/users/authorizations`. **Single field: `email`.**
 * `UserAuthorizationCreate` has no `department_id` field at all — the
 * target department is always the calling Admin's own, derived
 * server-side; there is nothing here for a department picker to bind
 * to even if one were added. This is the strongest possible structural
 * guarantee against department-injection for this form: no code path,
 * correct or malicious, can make a submitted department value reach
 * this endpoint (§6.3 of the review).
 *
 * Kept deliberately separate from `AdminAuthorizePage` — see that
 * page's own comment for why merging the two would obscure this exact
 * structural difference.
 */
export default function UserAuthorizePage() {
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

    const errors = validateUserAuthorizeForm(form)
    setFieldErrors(errors)
    if (Object.keys(errors).length > 0) return

    setSubmitting(true)
    try {
      await userService.authorize(form)
      navigate('/app/admin/users', { replace: true })
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

  return (
    <section className={styles.root}>
      <h1>Authorize new User</h1>
      <form onSubmit={handleSubmit} noValidate className={styles.formCard}>
        {formError && <ErrorState message={formError} />}

        <div className={styles.field}>
          <label htmlFor="user-authorize-email">Email *</label>
          <input
            id="user-authorize-email"
            name="email"
            type="email"
            required
            value={form.email}
            onChange={handleChange}
            aria-invalid={Boolean(fieldErrors.email)}
            aria-describedby={fieldErrors.email ? 'user-authorize-email-error' : undefined}
          />
          {fieldErrors.email && (
            <span id="user-authorize-email-error" role="alert" className={styles.fieldError}>
              {fieldErrors.email}
            </span>
          )}
        </div>
        <p className={styles.hint}>
          This authorizes the email to sign up as a User in your own department.
        </p>

        <div className={styles.actions}>
          <button type="submit" className={styles.submit} disabled={submitting}>
            {submitting ? 'Authorizing…' : 'Authorize User'}
          </button>
          <button type="button" className={styles.cancel} onClick={() => navigate('/app/admin/users')}>
            Cancel
          </button>
        </div>
      </form>
    </section>
  )
}
