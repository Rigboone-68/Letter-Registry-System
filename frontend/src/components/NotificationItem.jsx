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
 */
export default function NotificationItem({ notification, onMarkRead, marking, onNavigate }) {
  // `notification_type` is intentionally not read here — it's a plain
  // string on the backend, not a closed enum
  // (docs/architecture/document-notification-ui.md §2.2), so this
  // component renders every notification's `message` uniformly rather
  // than branching on a type value that could be anything.
  const { letter_id: letterId, message, is_read: isRead, created_at: createdAt } = notification

  return (
    <li className={`${styles.item} ${isRead ? '' : styles.unread}`}>
      <div className={styles.content}>
        <span className="sr-only">{isRead ? 'Read notification: ' : 'Unread notification: '}</span>
        {letterId ? (
          <Link to={`/app/letters/${letterId}`} className={styles.message} onClick={onNavigate}>
            {message}
          </Link>
        ) : (
          <span className={styles.message}>{message}</span>
        )}
        <span className={styles.timestamp}>{formatDateTime(createdAt)}</span>
      </div>
      {!isRead && (
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
