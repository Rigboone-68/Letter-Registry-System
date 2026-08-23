/**
 * `GET /api/v1/departments` (backend/app/api/v1/endpoints/departments.py,
 * verified fresh this session) → `DepartmentListResponse { items, total }`.
 *
 * CONFIRMED: this endpoint is `require_system_admin`-only. Used only by
 * the SYSTEM_ADMIN Letters view (`pages/LetterListPage.jsx`) to resolve
 * `recipient_department_id` to a readable name and to power the
 * SYSTEM_ADMIN-only department filter — this is reference-data reuse for
 * the Letters screens this phase builds, not a Departments management
 * UI (explicitly out of scope; see `docs/PROJECT_STATUS.md`).
 */

import apiClient from './apiClient'

export async function list() {
  const response = await apiClient.get('/departments')
  return response.data
}
