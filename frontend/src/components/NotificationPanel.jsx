import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'

import EmptyState from './EmptyState'
import ErrorState from './ErrorState'
import LoadingState from './LoadingState'
import NotificationItem from './NotificationItem'
import * as notificationService from '../services/notificationService'
import styles from './NotificationPanel.module.css'

const PANEL_PAGE_SIZE = 10

/**
 * The Topbar notification dropdown (Phase 5E,
 * docs/architecture/document-notification-ui.md §7.1/§7.2) — a bounded
 * recent slice (`page_size=10`), with a "View all" link into the full
 * paginated `/app/notifications` page for anything beyond that. Not a
 * `role="dialog"` modal (it doesn't block interaction with the rest of
 * the page the way `ConfirmDialog`/`AdminTransferDialog` do, Phase 5D)
 * — a lighter disclosure pattern: `Escape` closes it and returns focus
 * to the bell button (owned by the parent `NotificationBell`, via
 * `onClose`), but there is no backdrop and no Tab-trap.
 *
 * Phase 5I.4D (docs/architecture/ui-design-system.md §10) adds an
 * "Operational Signals" eyebrow above the unchanged "Notifications"
 * heading, and a small CSS-only pointer connecting the panel visually
 * to the bell it opened from. Mark-read stays explicit-button-only;
 * nothing here marks a notification read on navigation.
 */
export default function NotificationPanel({ onClose, onUnreadCountChange }) {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [markingId, setMarkingId] = useState(null)
  const [markingAll, setMarkingAll] = useState(false)
  const [markError, setMarkError] = useState(null)
  const panelRef = useRef(null)

  useEffect(() => {
    notificationService
      .list({ page: 1, page_size: PANEL_PAGE_SIZE })
      .then((response) => setData(response))
      .catch((normalizedError) => setError(normalizedError))
      .finally(() => setLoading(false))
  }, [])

  useEffect(() => {
    panelRef.current?.focus()

    function handleKeyDown(event) {
      if (event.key === 'Escape') {
        onClose()
      }
    }
    document.addEventListener('keydown', handleKeyDown)
    return () => document.removeEventListener('keydown', handleKeyDown)
  }, [onClose])

  async function handleMarkRead(notification) {
    setMarkingId(notification.id)
    setMarkError(null)
    try {
      const updated = await notificationService.markRead(notification.id)
      setData((previous) => ({
        ...previous,
        items: previous.items.map((item) => (item.id === updated.id ? updated : item)),
      }))
      const countResponse = await notificationService.unreadCount()
      onUnreadCountChange(countResponse.unread_count)
    } catch (normalizedError) {
      setMarkError(normalizedError.message ?? 'Unable to mark this notification read.')
    } finally {
      setMarkingId(null)
    }
  }

  async function handleMarkAllRead() {
    setMarkingAll(true)
    setMarkError(null)
    try {
      await notificationService.markAllRead()
      setData((previous) => ({
        ...previous,
        items: previous.items.map((item) => ({ ...item, is_read: true })),
      }))
      onUnreadCountChange(0)
    } catch (normalizedError) {
      setMarkError(normalizedError.message ?? 'Unable to mark all notifications read.')
    } finally {
      setMarkingAll(false)
    }
  }

  const hasUnread = data?.items.some((item) => !item.is_read) ?? false

  return (
    <div ref={panelRef} tabIndex={-1} role="region" aria-label="Notifications" className={styles.panel}>
      <div className={styles.header}>
        <div className={styles.headerText}>
          <p className={styles.eyebrow}>Operational Signals</p>
          <h2>Notifications</h2>
        </div>
        {hasUnread && (
          <button
            type="button"
            className={styles.markAllButton}
            onClick={handleMarkAllRead}
            disabled={markingAll}
          >
            {markingAll ? 'Marking…' : 'Mark all read'}
          </button>
        )}
      </div>

      {markError && <ErrorState message={markError} />}

      {loading && <LoadingState label="Loading notifications..." />}
      {!loading && error && <ErrorState message={error.message} />}
      {!loading && !error && data && data.items.length === 0 && (
        <EmptyState message="No notifications yet." />
      )}
      {!loading && !error && data && data.items.length > 0 && (
        <ul className={styles.list}>
          {data.items.map((notification) => (
            <NotificationItem
              key={notification.id}
              notification={notification}
              onMarkRead={handleMarkRead}
              marking={markingId === notification.id}
              onNavigate={onClose}
            />
          ))}
        </ul>
      )}

      <Link to="/app/notifications" className={styles.viewAll} onClick={onClose}>
        View all notifications
      </Link>
    </div>
  )
}
