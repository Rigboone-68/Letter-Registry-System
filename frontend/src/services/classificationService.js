/**
 * `GET /api/v1/classifications`
 * (backend/app/api/v1/endpoints/classifications.py, verified fresh this
 * session) → `ClassificationListResponse { items, total }`, each item
 * carrying `restricts_access` (the classified-access flag).
 *
 * CONFIRMED: this endpoint is `require_system_admin`-only — a USER or
 * ADMIN caller gets a `401`/`403`, not classification data. Callers of
 * this module must only invoke it for a SYSTEM_ADMIN caller (see
 * `pages/LetterFormPage.jsx`'s own comment for the resulting, documented
 * V1 limitation this creates for Letter creation/editing).
 */

import apiClient from './apiClient'

export async function list() {
  const response = await apiClient.get('/classifications')
  return response.data
}
