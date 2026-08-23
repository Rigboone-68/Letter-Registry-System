/**
 * API service functions for the three confirmed auth endpoints
 * (backend/app/api/v1/endpoints/auth.py, verified fresh this session):
 *
 *   POST /auth/login   → TokenResponse { access_token, token_type,
 *                         expires_in (seconds), user: UserPublic }
 *   POST /auth/signup  → UserPublic (201) — the account starts
 *                         PENDING_APPROVAL; never auto-login after this
 *                         (docs/architecture/frontend.md §4)
 *   GET  /auth/me      → UserPublic — the one authoritative source of
 *                         the caller's own role/department/status
 *                         (docs/architecture/frontend.md §22); never
 *                         decode the JWT client-side for this instead
 *
 * All three pass `skipAuthRedirect: true` — see apiClient.js for why:
 * none of these three calls should trigger the global "session died,
 * redirect to login" handler; each is handled locally by its caller
 * (the login/signup forms, or AuthContext's own session-restore logic).
 *
 * `full_name`/`email`/`password`/`role`/`department`/`status` are never
 * assigned by this module — every field on these request bodies is
 * exactly what `SignupRequest`/`LoginRequest` accept, nothing more; role/
 * department/status have no field to bind to on either schema (backend,
 * `app/schemas/auth.py`) and are not present here either.
 */

import apiClient from './apiClient'

/**
 * The exact `detail` strings the backend returns for a login attempt
 * against a not-yet-approved / deactivated account (auth.py, verified
 * fresh this session). These are compared verbatim so the UI can present
 * a dedicated pending/deactivated state instead of a generic credentials
 * error — this is the one place that string coupling lives, rather than
 * being duplicated wherever a login failure is handled.
 */
export const PENDING_APPROVAL_MESSAGE = 'Your account is awaiting administrator approval.'
export const DEACTIVATED_MESSAGE = 'Your account has been deactivated.'

export async function login(email, password) {
  const response = await apiClient.post(
    '/auth/login',
    { email, password },
    { skipAuthRedirect: true }
  )
  return response.data
}

export async function signup({ full_name, email, password, password_confirm }) {
  const response = await apiClient.post(
    '/auth/signup',
    { full_name, email, password, password_confirm },
    { skipAuthRedirect: true }
  )
  return response.data
}

export async function getCurrentUser() {
  const response = await apiClient.get('/auth/me', { skipAuthRedirect: true })
  return response.data
}
