import { useState } from 'react'
import { Link, Navigate, useLocation, useNavigate } from 'react-router-dom'

import AuthShell from '../components/AuthShell'
import DeactivatedAccountNotice from '../components/DeactivatedAccountNotice'
import ErrorState from '../components/ErrorState'
import PendingApprovalNotice from '../components/PendingApprovalNotice'
import { useAuth } from '../context/AuthContext'
import { DEACTIVATED_MESSAGE, PENDING_APPROVAL_MESSAGE } from '../services/authService'
import { validateLoginForm } from '../utils/formValidation'
import styles from './AuthPages.module.css'

/**
 * Production login page (docs/architecture/frontend.md — Phase 5B §3-5).
 *
 * Backend contract this page relies on (confirmed against
 * backend/app/api/v1/endpoints/auth.py, not assumed):
 *   200 → TokenResponse { access_token, user }
 *   401 "Incorrect email or password."            → generic credentials error,
 *                                                     never distinguishing a
 *                                                     nonexistent account from
 *                                                     a wrong password
 *   403 "Your account is awaiting administrator
 *        approval."                                → PendingApprovalNotice
 *   403 "Your account has been deactivated."        → DeactivatedAccountNotice
 *
 * `AuthContext.login()` already refreshes `user` from the backend's own
 * `TokenResponse.user` — that object comes from the same `UserPublic`
 * source `/auth/me` would return, so this page never decodes the JWT or
 * invents authorization state of its own.
 *
 * Phase 6B moved the shared `AuthShell` (brand/image/credit chrome)
 * into its own component file (`components/AuthShell.jsx`) once it
 * grew a genuine split-screen layout — every field, handler, and
 * state transition below is unchanged.
 */
export default function LoginPage() {
  const { status, restoreError, login, retryRestoreSession } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()

  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [fieldErrors, setFieldErrors] = useState({})
  const [formError, setFormError] = useState(null)
  const [accountNotice, setAccountNotice] = useState(null) // null | 'pending' | 'deactivated'
  const [submitting, setSubmitting] = useState(false)

  if (status === 'authenticated') {
    const redirectTo = location.state?.from?.pathname ?? '/app'
    return <Navigate to={redirectTo} replace />
  }

  function resetToForm() {
    setAccountNotice(null)
    setFormError(null)
    setFieldErrors({})
    setPassword('')
  }

  async function handleSubmit(event) {
    event.preventDefault()
    setFormError(null)
    setAccountNotice(null)

    const errors = validateLoginForm({ email, password })
    setFieldErrors(errors)
    if (Object.keys(errors).length > 0) {
      return
    }

    setSubmitting(true)
    try {
      await login(email, password)
      const redirectTo = location.state?.from?.pathname ?? '/app'
      navigate(redirectTo, { replace: true })
    } catch (normalizedError) {
      if (normalizedError.status === 403 && normalizedError.message === PENDING_APPROVAL_MESSAGE) {
        setAccountNotice('pending')
      } else if (normalizedError.status === 403 && normalizedError.message === DEACTIVATED_MESSAGE) {
        setAccountNotice('deactivated')
      } else if (normalizedError.fieldErrors) {
        setFieldErrors(normalizedError.fieldErrors)
      } else {
        setFormError(normalizedError.message ?? 'Unable to sign in.')
      }
    } finally {
      setSubmitting(false)
    }
  }

  if (accountNotice === 'pending') {
    return (
      <AuthShell>
        <div className={styles.card}>
          <PendingApprovalNotice onBackToLogin={resetToForm} />
        </div>
      </AuthShell>
    )
  }

  if (accountNotice === 'deactivated') {
    return (
      <AuthShell>
        <div className={styles.card}>
          <DeactivatedAccountNotice onBackToLogin={resetToForm} />
        </div>
      </AuthShell>
    )
  }

  return (
    <AuthShell>
      <form className={styles.card} onSubmit={handleSubmit} noValidate aria-labelledby="login-heading">
        <p className={styles.formEyebrow}>Account Access</p>
        <h1 id="login-heading">Sign in</h1>

        {restoreError && <ErrorState message={restoreError} onRetry={retryRestoreSession} />}
        {formError && <ErrorState message={formError} />}

        <div className={styles.field}>
          <label htmlFor="email">Email</label>
          <input
            id="email"
            name="email"
            type="email"
            autoComplete="username"
            required
            value={email}
            onChange={(event) => setEmail(event.target.value)}
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
            autoComplete="current-password"
            required
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            aria-invalid={Boolean(fieldErrors.password)}
            aria-describedby={fieldErrors.password ? 'password-error' : undefined}
          />
          {fieldErrors.password && (
            <span id="password-error" role="alert" className={styles.fieldError}>
              {fieldErrors.password}
            </span>
          )}
        </div>

        <button type="submit" className={styles.submit} disabled={submitting}>
          {submitting ? 'Signing in…' : 'Sign in'}
        </button>

        <p className={styles.footerLink}>
          Need an account? <Link to="/signup">Sign up</Link>
        </p>
      </form>
    </AuthShell>
  )
}
