/**
 * `GET /api/v1/categories` (backend/app/api/v1/endpoints/categories.py,
 * verified fresh this session) → `CategoryListResponse { items, total }`.
 *
 * CONFIRMED: this endpoint is `require_system_admin`-only — a USER or
 * ADMIN caller gets a `401`/`403`, not category data. Callers of this
 * module must only invoke it for a SYSTEM_ADMIN caller (see
 * `pages/LetterFormPage.jsx`'s own comment for the resulting, documented
 * V1 limitation this creates for Letter creation/editing).
 */

import apiClient from './apiClient'

export async function list() {
  const response = await apiClient.get('/categories')
  return response.data
}
