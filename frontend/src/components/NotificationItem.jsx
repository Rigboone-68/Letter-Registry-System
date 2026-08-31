import { useState } from 'react'
import { Link } from 'react-router-dom'

import styles from './NotificationItem.module.css'

function formatDateTime(value) {
  if (!value) return '—'
  return new Date(value).toLocaleString(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

/**
 * One notification row (Phase 5E,
 * docs/architecture/document-notification-ui.md §7.1/§14.2) — reused
 * by both `NotificationPanel` (the Topbar dropdown) and the full
 * `/app/notifications` page, the one genuine duplication this phase
 * found worth factoring out.
 *
 * `message` is rendered as ordinary JSX text — the backend's one
 * generated message is a fixed, non-sensitive template (never Letter
 * subject/content/classification, confirmed in
 * `notification_service.py`), so plain interpolation (auto-escaped by
 * React) is correct and sufficient; `dangerouslySetInnerHTML` is never
 * used here or anywhere in this component.
 *
 * Mark-read is **only ever explicit** — clicking through to the
 * related Letter never marks a notification read as a side effect.
 * The architecture review (§7.4) left "mark-read-on-navigate" as an
 * open business question rather than a confirmed requirement; this
 * implementation does not silently pick the automatic behavior, per
 * the explicit instruction accompanying this phase's implementation
 * brief.
 *
 * Phase 5I.4D (docs/architecture/ui-design-system.md §11) adds one
 * more static, non-animated unread signal — a small filled dot before
 * the message, `aria-hidden` — alongside the existing accent bar,
 * background tint, and bolder weight already established in Phase
 * 5I.3. No continuous animation, no pulsing; unread remains understood
 * through text (the sr-only prefix) first.
 *
 * Phase 6A (docs/architecture/correspondence.md §9) adds exactly one
 * type-specific branch — the one this component's own docstring above
 * used to say never happens — for `LETTER_DISPATCHED` only: `letter_id`
 * on that notification type is the *outgoing* letter, which this
 * department cannot open (`GET /letters/{id}` 404s — it isn't the
 * owning department; see `app/services/authorization.py:assert_letter_access`).
 * Linking to it the normal way would be a dead link, so this type
 * renders a `Record` button instead, calling the parent-owned
 * `onRecord(notification)` (mirroring `onMarkRead`'s ownership split —
 * the actual `POST /letters/{id}/record` call and any list-level state
 * lives in the parent; only the resulting incoming letter is tracked
 * here, locally, since it's transient, row-scoped UI state with no
 * other consumer). On success, the row shows a real, safe link to the
 * newly created (or already-existing, idempotent) incoming letter —
 * one this department *does* own.
 */
export default function NotificationItem({ notification, onMarkRead, marking, onNavigate, onRecord }) {
  const [recording, setRecording] = useState(false)
  const [recordError, setRecordError] = useState(null)
  const [recordedLetter, setRecordedLetter] = useState(null)

  const {
    letter_id: letterId,
    notification_type: notificationType,
    message,
    is_read: isRead,
    created_at: createdAt,
  } = notification
  const isDispatch = notificationType === 'LETTER_DISPATCHED' && !recordedLetter

  async function handleRecord() {
    setRecording(true)
    setRecordError(null)
    try {
      const letter = await onRecord(notification)
      setRecordedLetter(letter)
    } catch (normalizedError) {
      setRecordError(normalizedError.message ?? 'Unable to record this correspondence.')
    } finally {
      setRecording(false)
    }
  }

  return (
    <li className={`${styles.item} ${isRead ? '' : styles.unread}`}>
      <div className={styles.content}>
        <span className="sr-only">{isRead ? 'Read notification: ' : 'Unread notification: '}</span>
        <span className={styles.messageRow}>
          {!isRead && <span className={styles.unreadDot} aria-hidden="true" />}
          {isDispatch ? (
            <span className={styles.message}>{message}</span>
          ) : recordedLetter ? (
            <Link to={`/app/letters/${recordedLetter.id}`} className={styles.message} onClick={onNavigate}>
              {message}
            </Link>
          ) : letterId ? (
            <Link to={`/app/letters/${letterId}`} className={styles.message} onClick={onNavigate}>
              {message}
            </Link>
          ) : (
            <span className={styles.message}>{message}</span>
          )}
        </span>
        <span className={styles.timestamp}>{formatDateTime(createdAt)}</span>
        {recordError && (
          <span role="alert" className={styles.recordError}>
            {recordError}
          </span>
        )}
      </div>
      {isDispatch && (
        <button type="button" className={styles.markRead} onClick={handleRecord} disabled={recording}>
          {recording ? 'Recording…' : 'Record'}
        </button>
      )}
      {!isDispatch && !isRead && (
        <button
          type="button"
          className={styles.markRead}
          onClick={() => onMarkRead(notification)}
          disabled={marking}
        >
          {marking ? 'Marking…' : 'Mark as read'}
        </button>
      )}
    </li>
  )
}
