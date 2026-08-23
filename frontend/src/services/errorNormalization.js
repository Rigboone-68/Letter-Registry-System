/**
 * Normalizes every API failure into one predictable shape:
 *
 *   { status, message, fieldErrors }
 *
 * This backend returns two different error-body shapes depending on
 * failure origin (docs/architecture/frontend.md §21, verified against
 * the actual backend code, not assumed):
 *
 *   - a raised `HTTPException` (every business-rule rejection
 *     throughout every service) → { "detail": "<plain string>" }
 *   - a Pydantic/FastAPI request-validation failure (422) →
 *     { "detail": [{ "loc": [...], "msg": "...", "type": "..." }] }
 *
 * A caller that assumes only one of these shapes will break on whichever
 * it didn't test — this module is the one place that distinction is
 * handled, so nothing else in the frontend needs to know about it.
 */

export function normalizeApiError(error) {
  if (!error?.response) {
    // The request never reached a server, or no response came back
    // (network failure, backend unreachable, CORS failure, etc.).
    return {
      status: 0,
      message: 'Unable to reach the server. Check your connection and try again.',
      fieldErrors: null,
    }
  }

  const { status, data } = error.response
  const detail = data?.detail

  if (Array.isArray(detail)) {
    // Pydantic validation error array.
    const fieldErrors = {}
    for (const item of detail) {
      const field = Array.isArray(item.loc) ? item.loc[item.loc.length - 1] : 'field'
      fieldErrors[field] = item.msg
    }
    return {
      status,
      message: 'Please correct the highlighted fields.',
      fieldErrors,
    }
  }

  if (typeof detail === 'string') {
    return { status, message: detail, fieldErrors: null }
  }

  // Anything else (an empty body, an unexpected shape) — never expose
  // internal detail, just a generic message tied to the real status.
  return { status, message: 'An unexpected error occurred.', fieldErrors: null }
}
