import { useCallback, useEffect, useState } from 'react'

import EmptyState from '../components/EmptyState'
import ErrorState from '../components/ErrorState'
import LoadingState from '../components/LoadingState'
import NotificationItem from '../components/NotificationItem'
import Pagination from '../components/Pagination'
import * as notificationService from '../services/notificationService'
import styles from './NotificationsPage.module.css'

/**
 * The full notifications page (Phase 5E,
 * docs/architecture/document-notification-ui.md §7.2/§16) —
 * `/app/notifications`, an already-slotted route/nav entry since
 * Phase 5A. Reuses `NotificationItem` (the same row rendering
 * `NotificationPanel`'s dropdown uses) and the existing `Pagination`
 * component (Phase 5C) — this is the one notification surface where
 * pagination controls make sense, since the backend genuinely supports
 * it here (`page`/`page_size`, unlike every Phase 5D administration
 * list). No `is_read` filter exists on the backend (confirmed,
 * `docs/architecture/document-notification-ui.md` §2.1) — none is
 * offered here.
 */
export default function NotificationsPage() {
  const [page, setPage] = useState(1)
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [markingId, setMarkingId] = useState(null)
  const [markingAll, setMarkingAll] = useState(false)
  const [markError, setMarkError] = useState(null)

  const fetchNotifications = useCallback(() => {
    setLoading(true)
    setError(null)
    notificationService
      .list({ page })
      .then((response) => setData(response))
      .catch((normalizedError) => setError(normalizedError))
      .finally(() => setLoading(false))
  }, [page])

  useEffect(() => {
    fetchNotifications()
  }, [fetchNotifications])

  async function handleMarkRead(notification) {
    setMarkingId(notification.id)
    setMarkError(null)
    try {
      const updated = await notificationService.markRead(notification.id)
      setData((previous) => ({
        ...previous,
        items: previous.items.map((item) => (item.id === updated.id ? updated : item)),
      }))
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
    } catch (normalizedError) {
      setMarkError(normalizedError.message ?? 'Unable to mark all notifications read.')
    } finally {
      setMarkingAll(false)
    }
  }

  const hasUnread = data?.items.some((item) => !item.is_read) ?? false

  return (
    <section className={styles.root}>
      <div className={styles.header}>
        <div>
          <h1>Notifications</h1>
          {data && <p className={styles.count}>{data.total} total</p>}
        </div>
        <div className={styles.headerActions}>
          <button type="button" onClick={fetchNotifications}>
            Refresh
          </button>
          {hasUnread && (
            <button type="button" onClick={handleMarkAllRead} disabled={markingAll}>
              {markingAll ? 'Marking…' : 'Mark all read'}
            </button>
          )}
        </div>
      </div>

      {markError && <ErrorState message={markError} />}

      {loading && <LoadingState label="Loading notifications..." />}
      {!loading && error && <ErrorState message={error.message} onRetry={fetchNotifications} />}
      {!loading && !error && data && data.items.length === 0 && (
        <EmptyState message="No notifications yet." />
      )}
      {!loading && !error && data && data.items.length > 0 && (
        <>
          <ul className={styles.list}>
            {data.items.map((notification) => (
              <NotificationItem
                key={notification.id}
                notification={notification}
                onMarkRead={handleMarkRead}
                marking={markingId === notification.id}
              />
            ))}
          </ul>
          <Pagination
            page={data.page}
            totalPages={data.total_pages}
            total={data.total}
            onPageChange={setPage}
          />
        </>
      )}
    </section>
  )
}
