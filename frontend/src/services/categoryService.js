/**
 * API service functions for the confirmed Category management endpoints
 * (backend/app/api/v1/endpoints/categories.py, verified fresh this
 * session) — all `require_system_admin`:
 *
 *   GET    /categories             → CategoryListResponse {items, total}
 *                                     — no pagination/search/sort; only
 *                                     an optional `status` filter
 *   POST   /categories             → CategoryResponse (201); 409 on
 *                                     duplicate name
 *   GET    /categories/{id}        → CategoryResponse; 404
 *   PATCH  /categories/{id}        → CategoryResponse — `name`/`description`
 *                                     optional but at least one required;
 *                                     omitted means "leave unchanged"
 *   POST   /categories/{id}/activate    → CategoryResponse, idempotent
 *   POST   /categories/{id}/deactivate  → CategoryResponse, idempotent
 *
 * `id`/`status`/`created_at`/`updated_at` are never sent by `create`/
 * `update` — `CategoryCreate`/`CategoryUpdate` (backend, `extra="forbid"`)
 * have no field for any of them; status changes only ever go through
 * the two dedicated activate/deactivate calls below. Mirrors
 * `departmentService.js`'s exact shape (Phase 5H.1 — this resource's
 * management UI previously had only `list()`; the three seeded V1
 * categories, and any others a SYSTEM_ADMIN has since added, were
 * already fully manageable via this API — only the frontend was
 * incomplete).
 */

import apiClient from './apiClient'

const WRITE_FIELDS = ['name', 'description']

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
  const response = await apiClient.get('/categories', { params })
  return response.data
}

export async function get(categoryId) {
  const response = await apiClient.get(`/categories/${categoryId}`)
  return response.data
}

export async function create(fields) {
  const response = await apiClient.post('/categories', pickFields(fields, WRITE_FIELDS))
  return response.data
}

export async function update(categoryId, fields) {
  const response = await apiClient.patch(`/categories/${categoryId}`, pickFields(fields, WRITE_FIELDS))
  return response.data
}

export async function activate(categoryId) {
  const response = await apiClient.post(`/categories/${categoryId}/activate`)
  return response.data
}

export async function deactivate(categoryId) {
  const response = await apiClient.post(`/categories/${categoryId}/deactivate`)
  return response.data
}
