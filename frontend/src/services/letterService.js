/**
 * API service functions for the confirmed Letter registry endpoints
 * (backend/app/api/v1/endpoints/letters.py, verified fresh this
 * session):
 *
 *   GET    /letters          → LetterListResponse
 *                               { items, total, page, page_size, total_pages }
 *   POST   /letters          → LetterResponse (201) — USER/ADMIN only;
 *                               SYSTEM_ADMIN has no department to record
 *                               a letter against and gets 403
 *   GET    /letters/{id}     → LetterResponse; 404 collapses "doesn't
 *                               exist"/"wrong department"/"classified and
 *                               inaccessible" into one identical response
 *   PATCH  /letters/{id}     → LetterResponse — every field optional,
 *                               `null`/omitted means "leave unchanged"
 *   DELETE /letters/{id}     → LetterResponse — archives (status →
 *                               ARCHIVED); never a physical delete
 *
 * `recipient_department_id`/`recorded_by`/`status`/`id`/`created_at`/
 * `updated_at` are never sent by this module — `LetterCreate`/
 * `LetterUpdate` (backend, `extra="forbid"`) have no field for any of
 * them, so a caller of `create`/`update` below cannot inject one even by
 * passing extra keys in `fields` — only the named fields are forwarded.
 */

import apiClient from './apiClient'

export const LETTER_SORT_FIELDS = Object.freeze([
  { value: 'received_at', label: 'Received date' },
  { value: 'created_at', label: 'Recorded date' },
  { value: 'reference_number', label: 'Reference number' },
  { value: 'subject', label: 'Subject' },
])

export const LETTER_STATUS_OPTIONS = Object.freeze([
  { value: 'ACTIVE', label: 'Active' },
  { value: 'ARCHIVED', label: 'Archived' },
])

const CREATE_FIELDS = [
  'reference_number',
  'subject',
  'source_name',
  'source_department_id',
  'source_location',
  'sender_name',
  'sender_designation',
  'sender_department',
  'sender_address',
  'reason',
  'category_id',
  'classification_id',
  'received_at',
  'text_content',
]

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
  const response = await apiClient.get('/letters', { params })
  return response.data
}

export async function get(letterId) {
  const response = await apiClient.get(`/letters/${letterId}`)
  return response.data
}

export async function create(fields) {
  const response = await apiClient.post('/letters', pickFields(fields, CREATE_FIELDS))
  return response.data
}

export async function update(letterId, fields) {
  const response = await apiClient.patch(`/letters/${letterId}`, pickFields(fields, CREATE_FIELDS))
  return response.data
}

export async function archive(letterId) {
  const response = await apiClient.delete(`/letters/${letterId}`)
  return response.data
}
