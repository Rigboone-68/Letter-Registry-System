/**
 * The single authentication state mechanism for the whole application
 * (docs/architecture/frontend.md §22). `status` is always one of
 * `'loading' | 'authenticated' | 'unauthenticated'` — nothing renders a
 * protected route before `status` leaves `'loading'` (§9), which avoids
 * an authentication flicker (a brief flash of the wrong screen while
 * the session is still being restored).
 *
 * `user` is always the `UserPublic` object most recently returned by
 * `POST /auth/login` or `GET /auth/me` — never decoded from the JWT
 * payload client-side, and never assumed from anything the caller
 * supplied. The backend remains the sole authority on role/department/
 * status; this context only caches what it was told.
 */

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from 'react'

import * as authService from '../services/authService'
import { setUnauthorizedHandler } from '../services/apiClient'
import { clearToken, getToken, setToken } from '../services/tokenStorage'

const AuthContext = createContext(undefined)

export function AuthProvider({ children }) {
  const [status, setStatus] = useState('loading')
  const [user, setUser] = useState(null)
  // Set only when session restoration fails because the server could not
  // be reached at all (status 0 — see services/errorNormalization.js),
  // as opposed to a definite rejection of the token itself. Surfaced so
  // LoginPage can explain *why* the user landed back on the login screen
  // and offer a retry, instead of silently behaving as if the stored
  // credential were simply invalid.
  const [restoreError, setRestoreError] = useState(null)

  const clearSession = useCallback(() => {
    clearToken()
    setUser(null)
    setRestoreError(null)
    setStatus('unauthenticated')
  }, [])

  // Registered once — this is the centralized 401 handler apiClient.js
  // calls for any authenticated request that comes back 401 (excluding
  // calls that opt out via skipAuthRedirect, e.g. the login call itself).
  useEffect(() => {
    setUnauthorizedHandler(clearSession)
    return () => setUnauthorizedHandler(null)
  }, [clearSession])

  // Session restoration (§9): if a token exists, validate it against
  // GET /auth/me before ever settling on 'authenticated' — a locally
  // stored token is never trusted on its own.
  //
  // A network failure here is deliberately NOT treated the same as a
  // rejected token: the stored credential might still be perfectly
  // valid, we simply couldn't confirm it, so it is never treated as a
  // successful authenticated state, but it is also not discarded —
  // that would force a needless fresh login once connectivity returns.
  // Only a definite rejection (401, or any other real response) clears
  // the stored token. This function is also exposed as
  // `retryRestoreSession` so the login screen can retry it directly.
  const restoreSession = useCallback(async () => {
    const token = getToken()
    if (!token) {
      setStatus('unauthenticated')
      return
    }
    setRestoreError(null)
    try {
      const currentUser = await authService.getCurrentUser()
      setUser(currentUser)
      setStatus('authenticated')
    } catch (err) {
      if (err?.status === 0) {
        setRestoreError('Unable to verify your session. Check your connection and try again.')
        setStatus('unauthenticated')
      } else {
        clearSession()
      }
    }
  }, [clearSession])

  useEffect(() => {
    restoreSession()
    // Runs once on mount only — restoreSession is stable (its only
    // dependency, clearSession, never changes identity).
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const login = useCallback(async (email, password) => {
    // Throws the normalized error (see services/errorNormalization.js)
    // on failure — the caller (the login form) is responsible for
    // displaying it; this function does not swallow or reinterpret it.
    const result = await authService.login(email, password)
    setToken(result.access_token)
    setUser(result.user)
    setRestoreError(null)
    setStatus('authenticated')
    return result.user
  }, [])

  const logout = useCallback(() => {
    // No server-side revocation endpoint exists (unchanged since Phase
    // 3A — docs/architecture/authentication.md §16) — logout is purely
    // client-side: forget the token and the cached user.
    clearSession()
  }, [clearSession])

  const value = useMemo(
    () => ({ status, user, restoreError, login, logout, retryRestoreSession: restoreSession }),
    [status, user, restoreError, login, logout, restoreSession]
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}
