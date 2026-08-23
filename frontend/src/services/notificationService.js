/**
 * API service functions for the confirmed Notification endpoints
 * (backend/app/api/v1/endpoints/notifications.py, verified fresh this
 * session) — all `get_current_user` only, unconditionally scoped to
 * the caller's own id at the query level (no role dependency, no
 * `recipient_user_id` parameter anywhere):
 *
 *   GET   /notifications             → NotificationListResponse
 *                                       {items, total, page, page_size,
 *                                       total_pages} — newest first;
 *                                       page/page_size only, no `is_read`
 *                                       filter exists
 *   GET   /notifications/unread-count → UnreadCountResponse {unread_count}
 *   PATCH /notifications/{id}/read   → NotificationResponse, idempotent
 *   PATCH /notifications/read-all    → {marked_read: number} — a raw
 *                                       dict; the backend declares no
 *                                       `response_model` on this one route
 *
 * There is no request field anywhere for a client to supply a
 * recipient — every function here only ever needs the resource's own
 * id (never a user id), matching the backend's own "no
 * recipient-selection capability exists" contract exactly.
 */

import apiClient from './apiClient'

export async function list(params = {}) {
  const response = await apiClient.get('/notifications', { params })
  return response.data
}

export async function unreadCount() {
  const response = await apiClient.get('/notifications/unread-count')
  return response.data
}

export async function markRead(notificationId) {
  const response = await apiClient.patch(`/notifications/${notificationId}/read`)
  return response.data
}

export async function markAllRead() {
  const response = await apiClient.patch('/notifications/read-all')
  return response.data
}
