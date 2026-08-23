/**
 * Single, isolated module owning where the access token lives.
 *
 * V1 approach (PROVISIONAL, per docs/architecture/frontend.md §28):
 * `localStorage`. This is a deliberate, documented placeholder, not a
 * settled decision — the architecture review flags the exact
 * storage strategy as a pending deployment decision (a shared/kiosk
 * workstation would favor `sessionStorage` instead; a cookie-based
 * approach would require a backend change this project has not made).
 *
 * Every other module reads/writes the token exclusively through the
 * three functions below — never `localStorage` directly — so changing
 * the storage strategy later means editing only this file.
 */

const TOKEN_STORAGE_KEY = 'lrs.accessToken'

export function getToken() {
  try {
    return window.localStorage.getItem(TOKEN_STORAGE_KEY)
  } catch {
    // Storage unavailable (e.g. disabled site data) — treat as "no
    // session" rather than throwing during app bootstrap.
    return null
  }
}

export function setToken(token) {
  try {
    window.localStorage.setItem(TOKEN_STORAGE_KEY, token)
  } catch {
    // See getToken — the session simply won't persist across reloads.
  }
}

export function clearToken() {
  try {
    window.localStorage.removeItem(TOKEN_STORAGE_KEY)
  } catch {
    // See getToken.
  }
}
