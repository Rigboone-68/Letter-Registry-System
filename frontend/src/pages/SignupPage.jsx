import { useState } from 'react'
import { Link, Navigate, useNavigate } from 'react-router-dom'

import AuthShell from '../components/AuthShell'
import ErrorState from '../components/ErrorState'
import PendingApprovalNotice from '../components/PendingApprovalNotice'
import { useAuth } from '../context/AuthContext'
import * as authService from '../services/authService'
import { validateSignupForm } from '../utils/formValidation'
import styles from './AuthPages.module.css'

const INITIAL_FORM = { full_name: '', email: '', password: '', password_confirm: '' }

/**
 * Production signup page (docs/architecture/frontend.md — Phase 5B §6-8).
 *
 * Phase 6B moved the shared `AuthShell` (brand/image/credit chrome,
 * previously duplicated here and in `LoginPage.jsx`) into its own
 * component file (`components/AuthShell.jsx`) once it grew a genuine
 * split-screen layout — every field, handler, and state transition
 * below is unchanged.
 *
 * Calls `authService.signup` directly, not through `AuthContext`, because
 * signup never logs the caller in: a fresh account always starts
 * `PENDING_APPROVAL` (`app/services/auth_service.py`), and attempting to
 * log in immediately would just surface the backend's own "awaiting
 * administrator approval" error. `role`/`department`/`status` have no
 * field on this form — `SignupRequest` (backend, `extra="forbid"`) has
 * no field for any of them either, so there is nothing here for a
 * client value to bind to even accidentally; the payload sent below is
 * built from exactly the four fields this form collects.
 */
export default function SignupPage() {
  const { status } = useAuth()
  const navigate = useNavigate()

  const [form, setForm] = useState(INITIAL_FORM)
  const [fieldErrors, setFieldErrors] = useState({})
  const [formError, setFormError] = useState(null)
  const [submitting, setSubmitting] = useState(false)
  const [success, setSuccess] = useState(false)

  if (status === 'authenticated') {
    return <Navigate to="/app" replace />
  }

  function handleChange(event) {
    const { name, value } = event.target
    setForm((previous) => ({ ...previous, [name]: value }))
  }

  async function handleSubmit(event) {
    event.preventDefault()
    setFormError(null)

    const errors = validateSignupForm(form)
    setFieldErrors(errors)
    if (Object.keys(errors).length > 0) {
      return
    }

    setSubmitting(true)
    try {
      await authService.signup(form)
      setSuccess(true)
    } catch (normalizedError) {
      if (normalizedError.fieldErrors) {
        setFieldErrors(normalizedError.fieldErrors)
      } else {
        setFormError(normalizedError.message ?? 'Unable to create your account.')
      }
    } finally {
      setSubmitting(false)
    }
  }

  if (success) {
    return (
      <AuthShell>
        <div className={styles.card}>
          <PendingApprovalNotice onBackToLogin={() => navigate('/login')} />
        </div>
      </AuthShell>
    )
  }

  return (
    <AuthShell>
      <form className={styles.card} onSubmit={handleSubmit} noValidate aria-labelledby="signup-heading">
        <p className={styles.formEyebrow}>New Account Request</p>
        <h1 id="signup-heading">Create account</h1>

        {formError && <ErrorState message={formError} />}

        <div className={styles.field}>
          <label htmlFor="full_name">Full name</label>
          <input
            id="full_name"
            name="full_name"
            type="text"
            autoComplete="name"
            required
            value={form.full_name}
            onChange={handleChange}
            aria-invalid={Boolean(fieldErrors.full_name)}
            aria-describedby={fieldErrors.full_name ? 'full_name-error' : undefined}
          />
          {fieldErrors.full_name && (
            <span id="full_name-error" role="alert" className={styles.fieldError}>
              {fieldErrors.full_name}
            </span>
          )}
        </div>

        <div className={styles.field}>
          <label htmlFor="email">Email</label>
          <input
            id="email"
            name="email"
            type="email"
            autoComplete="username"
            required
            value={form.email}
            onChange={handleChange}
            aria-invalid={Boolean(fieldErrors.email)}
            aria-describedby={fieldErrors.email ? 'email-error' : undefined}
          />
          {fieldErrors.email && (
            <span id="email-error" role="alert" className={styles.fieldError}>
              {fieldErrors.email}
            </span>
          )}
        </div>

        <div className={styles.field}>
          <label htmlFor="password">Password</label>
          <input
            id="password"
            name="password"
            type="password"
            autoComplete="new-password"
            required
            value={form.password}
            onChange={handleChange}
            aria-invalid={Boolean(fieldErrors.password)}
            aria-describedby={fieldErrors.password ? 'password-error' : undefined}
          />
          {fieldErrors.password && (
            <span id="password-error" role="alert" className={styles.fieldError}>
              {fieldErrors.password}
            </span>
          )}
        </div>

        <div className={styles.field}>
          <label htmlFor="password_confirm">Confirm password</label>
          <input
            id="password_confirm"
            name="password_confirm"
            type="password"
            autoComplete="new-password"
            required
            value={form.password_confirm}
            onChange={handleChange}
            aria-invalid={Boolean(fieldErrors.password_confirm)}
            aria-describedby={fieldErrors.password_confirm ? 'password_confirm-error' : undefined}
          />
          {fieldErrors.password_confirm && (
            <span id="password_confirm-error" role="alert" className={styles.fieldError}>
              {fieldErrors.password_confirm}
            </span>
          )}
        </div>

        <button type="submit" className={styles.submit} disabled={submitting}>
          {submitting ? 'Creating account…' : 'Create account'}
        </button>

        <p className={styles.footerLink}>
          Already have an account? <Link to="/login">Sign in</Link>
        </p>
      </form>
    </AuthShell>
  )
}
