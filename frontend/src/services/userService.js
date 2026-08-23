/**
 * API service functions for the confirmed User management endpoints
 * (backend/app/api/v1/endpoints/users.py, verified fresh this
 * session) — all `require_admin` (strictly ADMIN, scoped to the
 * calling Admin's own department):
 *
 *   POST   /users/authorizations             → UserAuthorizationResponse (201)
 *                                               — `{email}` only; there is
 *                                               NO `department_id` field on
 *                                               `UserAuthorizationCreate` at
 *                                               all (unlike Admin
 *                                               authorization) — it is
 *                                               always derived server-side
 *                                               from the calling Admin's own
 *                                               department, so there is
 *                                               nothing here for a client
 *                                               value to bind to
 *   GET    /users/authorizations             → UserAuthorizationListResponse
 *                                               {items, total} — department-
 *                                               wide (every authorization in
 *                                               the Admin's department, not
 *                                               just ones they created); no
 *                                               pagination/search/sort, only
 *                                               an optional `status` filter
 *   DELETE /users/authorizations/{id}        → UserAuthorizationResponse —
 *                                               idempotent for an
 *                                               already-REVOKED row; 404 if
 *                                               the calling Admin didn't
 *                                               create it (creator-scoped,
 *                                               stricter than the list's own
 *                                               department-wide visibility);
 *                                               409 if already USED
 *   GET    /users                            → UserListResponse {items, total}
 *                                               — scoped to the Admin's own
 *                                               department; no pagination/
 *                                               search/sort/department
 *                                               param, only `status`
 *   GET    /users/{id}                       → UserResponse; 404 collapses
 *                                               "doesn't exist," "wrong
 *                                               role," and "different
 *                                               department" identically
 *   POST   /users/{id}/approve               → UserResponse; NOT idempotent
 *   POST   /users/{id}/deactivate            → UserResponse; idempotent
 *   POST   /users/{id}/reactivate            → UserResponse; idempotent
 */

import apiClient from './apiClient'

export async function list(params = {}) {
  const response = await apiClient.get('/users', { params })
  return response.data
}

export async function get(userId) {
  const response = await apiClient.get(`/users/${userId}`)
  return response.data
}

export async function authorize({ email }) {
  const response = await apiClient.post('/users/authorizations', { email })
  return response.data
}

export async function listAuthorizations(params = {}) {
  const response = await apiClient.get('/users/authorizations', { params })
  return response.data
}

export async function revokeAuthorization(authorizationId) {
  const response = await apiClient.delete(`/users/authorizations/${authorizationId}`)
  return response.data
}

export async function approve(userId) {
  const response = await apiClient.post(`/users/${userId}/approve`)
  return response.data
}

export async function deactivate(userId) {
  const response = await apiClient.post(`/users/${userId}/deactivate`)
  return response.data
}

export async function reactivate(userId) {
  const response = await apiClient.post(`/users/${userId}/reactivate`)
  return response.data
}
