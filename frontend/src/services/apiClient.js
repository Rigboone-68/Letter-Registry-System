/**
 * The one centralized Axios instance. Every API call in this
 * application goes through this module — components never construct a
 * URL or call Axios directly (docs/architecture/frontend.md §21, and
 * the project's own established convention, `frontend/README.md`).
 *
 * Responsibilities:
 *   - base URL, from the existing `VITE_API_BASE_URL` env var (never
 *     hardcoded — see src/constants/app.js)
 *   - attaching `Authorization: Bearer <token>` to every request that
 *     has one, via `services/tokenStorage.js` (the one place the token
 *     is read from)
 *   - normalizing every error response into one predictable shape
 *     (services/errorNormalization.js)
 *   - a single, centralized 401 handler: any authenticated call that
 *     comes back 401 clears the session and lets `AuthContext` redirect
 *     to `/login` — *except* a call that explicitly opts out via
 *     `{ skipAuthRedirect: true }`, which the login/signup/session-restore
 *     calls do (docs/architecture/frontend.md §4 — a 401 on the login
 *     call itself is a wrong-password form error, not "your session
 *     died"; the caller handles it locally instead).
 */

import axios from 'axios'

import { API_BASE_URL } from '../constants/app'
import { normalizeApiError } from './errorNormalization'
import { getToken } from './tokenStorage'

const apiClient = axios.create({
  baseURL: API_BASE_URL,
})

apiClient.interceptors.request.use((config) => {
  const token = getToken()
  if (token) {
    config.headers = config.headers ?? {}
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

let unauthorizedHandler = null

/** Registered once by `AuthContext` on mount — not exported state,
 * just a single callback slot, so this module never needs to know
 * anything about React. */
export function setUnauthorizedHandler(handler) {
  unauthorizedHandler = handler
}

apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    const normalized = normalizeApiError(error)
    const skipAuthRedirect = error.config?.skipAuthRedirect === true
    if (normalized.status === 401 && !skipAuthRedirect && unauthorizedHandler) {
      unauthorizedHandler()
    }
    return Promise.reject(normalized)
  }
)

export default apiClient
