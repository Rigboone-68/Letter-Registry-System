/**
 * API service functions for the confirmed Classification management
 * endpoints (backend/app/api/v1/endpoints/classifications.py, verified
 * fresh this session) — all `require_system_admin`:
 *
 *   GET    /classifications             → ClassificationListResponse {items, total}
 *                                          — no pagination/search/sort; only
 *                                          an optional `status` filter
 *   POST   /classifications             → ClassificationResponse (201); 409 on
 *                                          duplicate name
 *   GET    /classifications/{id}        → ClassificationResponse; 404
 *   PATCH  /classifications/{id}        → ClassificationResponse — `name`/
 *                                          `description`/`restricts_access`,
 *                                          at least one required; omitted
 *                                          means "leave unchanged"
 *   POST   /classifications/{id}/activate    → ClassificationResponse, idempotent
 *   POST   /classifications/{id}/deactivate  → ClassificationResponse, idempotent
 *
 * `restricts_access` is the data-model half of the classified-access
 * authorization boundary (`app/models/classification.py`) — this
 * service only ever forwards whatever boolean value the SYSTEM_ADMIN
 * caller explicitly set; it never infers, defaults, or overrides it,
 * and nothing here evaluates or acts on it (the actual classified-
 * access decision is entirely `assert_letter_access`'s job, on the
 * backend, unaffected by this file). `id`/`status`/`created_at`/
 * `updated_at` are never sent by `create`/`update` —
 * `ClassificationCreate`/`ClassificationUpdate` (backend,
 * `extra="forbid"`) have no field for any of them; status changes only
 * ever go through the two dedicated activate/deactivate calls below.
 * Mirrors `departmentService.js`'s exact shape (Phase 5H.1 — this
 * resource's management UI previously had only `list()`).
 */

import apiClient from './apiClient'

const WRITE_FIELDS = ['name', 'description', 'restricts_access']

function pickFields(fields, allowed) {
  const payload = {}
  for (const key of allowed) {
    if (Object.prototype.hasOwnProperty.call(fields, key)) {
      payload[key] = fields[key]
    }
  }
  return payload
}

export async function list(params = {}) {
  const response = await apiClient.get('/classifications', { params })
  return response.data
}

export async function get(classificationId) {
  const response = await apiClient.get(`/classifications/${classificationId}`)
  return response.data
}

export async function create(fields) {
  const response = await apiClient.post('/classifications', pickFields(fields, WRITE_FIELDS))
  return response.data
}

export async function update(classificationId, fields) {
  const response = await apiClient.patch(
    `/classifications/${classificationId}`,
    pickFields(fields, WRITE_FIELDS)
  )
  return response.data
}

export async function activate(classificationId) {
  const response = await apiClient.post(`/classifications/${classificationId}/activate`)
  return response.data
}

export async function deactivate(classificationId) {
  const response = await apiClient.post(`/classifications/${classificationId}/deactivate`)
  return response.data
}
