/**
 * API service functions for the confirmed Designation management
 * endpoints (backend/app/api/v1/endpoints/designations.py, Phase 5H):
 *
 *   GET    /designations                → DesignationListResponse {items, total}
 *                                          — readable by every authenticated
 *                                          role (USER/ADMIN/SYSTEM_ADMIN),
 *                                          not SYSTEM_ADMIN-only like
 *                                          Category/Classification's own
 *                                          list endpoints — see
 *                                          docs/architecture/
 *                                          source-designation.md §11 for why
 *   POST   /designations                → DesignationResponse (201, SYSTEM_ADMIN only)
 *   PATCH  /designations/{id}           → DesignationResponse (SYSTEM_ADMIN only)
 *   POST   /designations/{id}/activate  → DesignationResponse, idempotent (SYSTEM_ADMIN only)
 *   POST   /designations/{id}/deactivate → DesignationResponse, idempotent (SYSTEM_ADMIN only)
 *
 * No `status` field is ever accepted from a client on create/update —
 * `DesignationCreate`/`DesignationUpdate` (backend, `extra="forbid"`)
 * have no field for it; status changes only ever go through the
 * dedicated activate/deactivate calls below. No delete function exists
 * — designations are never physically deleted.
 */

import apiClient from './apiClient'

export async function list(params = {}) {
  const response = await apiClient.get('/designations', { params })
  return response.data
}

export async function create({ name }) {
  const response = await apiClient.post('/designations', { name })
  return response.data
}

export async function update(designationId, { name }) {
  const response = await apiClient.patch(`/designations/${designationId}`, { name })
  return response.data
}

export async function activate(designationId) {
  const response = await apiClient.post(`/designations/${designationId}/activate`)
  return response.data
}

export async function deactivate(designationId) {
  const response = await apiClient.post(`/designations/${designationId}/deactivate`)
  return response.data
}
