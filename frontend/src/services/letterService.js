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
 *   POST   /letters/{id}/record → LetterResponse (201 first time, 200
 *                               on a repeat call — never a duplicate);
 *                               USER/ADMIN only. `id` is the *outgoing*
 *                               letter's id (Phase 6A).
 *
 * `recipient_department_id`/`recorded_by`/`status`/`id`/`created_at`/
 * `updated_at` are never sent by this module — `LetterCreate`/
 * `LetterUpdate` (backend, `extra="forbid"`) have no field for any of
 * them, so a caller of `create`/`update` below cannot inject one even by
 * passing extra keys in `fields` — only the named fields are forwarded.
 *
 * Phase 6A adds `direction`/`dispatch_department_id`/
 * `continuation_of_letter_id` to `CREATE_FIELDS` — all three are
 * write-once at creation (there is no field for any of them on
 * `LetterUpdate`, so a PATCH silently ignores them if ever passed,
 * exactly like every other create-only field already did before this
 * phase); `diary_number`/`recorded_from_letter_id` are server-derived
 * and never sent by this module at all.
 *
 * Phase 6C adds:
 *
 *   GET /letters/aggregate → LetterAggregateResponse
 *                             { group_by, total, buckets: [{ key, count }] }
 *
 * — a `group_by`-scoped count, never a full Letter list; department/
 * classified-visibility scoping is applied server-side, identically to
 * `list()` above (same authorization, no frontend-side filtering of
 * any kind).
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

export const LETTER_DIRECTION_OPTIONS = Object.freeze([
  { value: 'INCOMING', label: 'Incoming / Diary' },
  { value: 'OUTGOING', label: 'Outgoing / Dispatch' },
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
  'direction',
  'dispatch_department_id',
  'continuation_of_letter_id',
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

/**
 * The "Record" action (Phase 6A) — `outgoingLetterId` is the *outgoing*
 * letter's id (typically a `LETTER_DISPATCHED` notification's own
 * `letter_id`, which the caller cannot `get()` directly — see
 * `components/NotificationItem.jsx`). Idempotent: a repeat call for the
 * same outgoing letter returns the same, already-created incoming
 * letter rather than erroring or duplicating it.
 */
export async function recordFromDispatch(outgoingLetterId) {
  const response = await apiClient.post(`/letters/${outgoingLetterId}/record`)
  return response.data
}

/**
 * Group-by letter counts for dashboard analytics (Phase 6C). `params`
 * always requires `group_by`; every other key is an optional narrowing
 * filter the backend already supports on `GET /letters` (status,
 * category_id, classification_id, direction, dispatch_department_id,
 * received_from/received_to) — this module forwards them as-is rather
 * than allow-listing, since they are read-only query parameters, not a
 * write payload that could inject an unexpected field.
 */
export async function aggregate(params) {
  const response = await apiClient.get('/letters/aggregate', { params })
  return response.data
}
