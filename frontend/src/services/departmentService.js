/**
 * API service functions for the confirmed Department management
 * endpoints (backend/app/api/v1/endpoints/departments.py, verified
 * fresh this session) — all `require_system_admin`:
 *
 *   GET    /departments             → DepartmentListResponse {items, total}
 *                                      — no pagination/search/sort; only
 *                                      an optional `status` filter
 *   POST   /departments             → DepartmentResponse (201); 409 on
 *                                      duplicate name/code
 *   GET    /departments/{id}        → DepartmentResponse; 404
 *   PATCH  /departments/{id}        → DepartmentResponse — `name`/`code`
 *                                      optional but at least one required;
 *                                      omitted means "leave unchanged"
 *   POST   /departments/{id}/activate    → DepartmentResponse, idempotent
 *   POST   /departments/{id}/deactivate  → DepartmentResponse, idempotent
 *
 * `id`/`status`/`created_at`/`updated_at` are never sent by `create`/
 * `update` — `DepartmentCreate`/`DepartmentUpdate` (backend,
 * `extra="forbid"`) have no field for any of them; status changes only
 * ever go through the two dedicated activate/deactivate calls below.
 *
 * Originally built in Phase 5C as a SYSTEM_ADMIN-only reference-data
 * wrapper for the Letters screens (`list()` only); extended in Phase 5D
 * into the full Department management data layer. `list()`'s signature
 * is unchanged, so Phase 5C's own callers are unaffected.
 */

import apiClient from './apiClient'

const WRITE_FIELDS = ['name', 'code']

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
  const response = await apiClient.get('/departments', { params })
  return response.data
}

export async function get(departmentId) {
  const response = await apiClient.get(`/departments/${departmentId}`)
  return response.data
}

export async function create(fields) {
  const response = await apiClient.post('/departments', pickFields(fields, WRITE_FIELDS))
  return response.data
}

export async function update(departmentId, fields) {
  const response = await apiClient.patch(
    `/departments/${departmentId}`,
    pickFields(fields, WRITE_FIELDS)
  )
  return response.data
}

export async function activate(departmentId) {
  const response = await apiClient.post(`/departments/${departmentId}/activate`)
  return response.data
}

export async function deactivate(departmentId) {
  const response = await apiClient.post(`/departments/${departmentId}/deactivate`)
  return response.data
}
