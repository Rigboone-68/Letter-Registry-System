/**
 * API service functions for the confirmed Admin management endpoints
 * (backend/app/api/v1/endpoints/admins.py, verified fresh this
 * session) — all `require_system_admin`:
 *
 *   POST   /admins/authorizations        → AdminAuthorizationResponse (201)
 *   GET    /admins                       → AdminListResponse {items, total}
 *                                           — no pagination/search/sort;
 *                                           `department_id`/`status` filters
 *   GET    /admins/{id}                  → AdminResponse; 404 collapses
 *                                           "doesn't exist" and "exists but
 *                                           isn't role ADMIN" (including a
 *                                           SYSTEM_ADMIN's own id) identically
 *   POST   /admins/{id}/approve          → AdminResponse; NOT idempotent
 *                                           (409 if not PENDING_APPROVAL)
 *   POST   /admins/{id}/deactivate       → AdminResponse; idempotent
 *   POST   /admins/{id}/reactivate       → AdminResponse; idempotent,
 *                                           re-validates destination
 *                                           department is ACTIVE even
 *                                           when already ACTIVE
 *   PATCH  /admins/{id}/department       → AdminResponse — transfers to a
 *                                           different (ACTIVE) department;
 *                                           never touches role/status, and
 *                                           never reassigns any historical
 *                                           Letter (see admin_service.py's
 *                                           own docstring — recipient_
 *                                           department_id is captured once,
 *                                           at recording time, and is never
 *                                           re-derived later)
 *
 * `authorized_by` is always the calling SYSTEM_ADMIN's own id, derived
 * server-side from the authenticated caller — `AdminAuthorizationCreate`
 * (backend, `extra="forbid"`) has no field for it, nor for `role`/
 * `status`; the only client-supplied fields are `email`/`department_id`.
 */

import apiClient from './apiClient'

export async function list(params = {}) {
  const response = await apiClient.get('/admins', { params })
  return response.data
}

export async function get(adminId) {
  const response = await apiClient.get(`/admins/${adminId}`)
  return response.data
}

export async function authorize({ email, department_id }) {
  const response = await apiClient.post('/admins/authorizations', { email, department_id })
  return response.data
}

export async function approve(adminId) {
  const response = await apiClient.post(`/admins/${adminId}/approve`)
  return response.data
}

export async function deactivate(adminId) {
  const response = await apiClient.post(`/admins/${adminId}/deactivate`)
  return response.data
}

export async function reactivate(adminId) {
  const response = await apiClient.post(`/admins/${adminId}/reactivate`)
  return response.data
}

export async function changeDepartment(adminId, { department_id }) {
  const response = await apiClient.patch(`/admins/${adminId}/department`, { department_id })
  return response.data
}
