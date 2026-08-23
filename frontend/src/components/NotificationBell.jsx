import { useCallback, useEffect, useRef, useState } from 'react'

import NotificationPanel from './NotificationPanel'
import * as notificationService from '../services/notificationService'
import styles from './NotificationBell.module.css'

// PROVISIONAL V1 default (docs/architecture/document-notification-ui.md
// §11.2) — nothing in the confirmed backend or business requirements
// mandates this exact number; 60s keeps request volume low for an
// internal, human-paced operational tool. Polls only
// `/notifications/unread-count` (a single COUNT query, §11.1) — never
// the full notification list on an interval.
const POLL_INTERVAL_MS = 60000

/**
 * Topbar notification indicator (Phase 5E,
 * docs/architecture/document-notification-ui.md §7.1/§11/§14.2) — owns
 * the unread-count fetch/poll and the open/closed state of the
 * dropdown; renders identically for every role (no role dependency
 * exists on any notification endpoint, §13 of the review).
 *
 * Polling pauses when the tab is hidden (`visibilitychange`, a native
 * browser API — no new dependency) and resumes, with an immediate
 * refresh, when it becomes visible again. Mounted once inside `Topbar`,
 * inside `AppShell` (Phase 5A) — the interval's lifecycle is tied
 * directly to this component's own mount/unmount, no separate manager
 * needed.
 */
export default function NotificationBell() {
  const [unreadCount, setUnreadCount] = useState(0)
  const [open, setOpen] = useState(false)
  const buttonRef = useRef(null)

  const fetchUnreadCount = useCallback(() => {
    notificationService
      .unreadCount()
      .then((response) => setUnreadCount(response.unread_count))
      .catch(() => {
        // A failed poll tick isn't worth an error banner in the Topbar
        // — the badge simply keeps its last-known value until the next
        // successful tick or the next explicit panel open.
      })
  }, [])

  useEffect(() => {
    fetchUnreadCount()

    let intervalId = null
    function startPolling() {
      if (intervalId === null) {
        intervalId = setInterval(fetchUnreadCount, POLL_INTERVAL_MS)
      }
    }
    function stopPolling() {
      if (intervalId !== null) {
        clearInterval(intervalId)
        intervalId = null
      }
    }
    function handleVisibilityChange() {
      if (document.visibilityState === 'visible') {
        fetchUnreadCount()
        startPolling()
      } else {
        stopPolling()
      }
    }

    if (document.visibilityState === 'visible') {
      startPolling()
    }
    document.addEventListener('visibilitychange', handleVisibilityChange)

    return () => {
      stopPolling()
      document.removeEventListener('visibilitychange', handleVisibilityChange)
    }
  }, [fetchUnreadCount])

  function handleClose() {
    setOpen(false)
    buttonRef.current?.focus()
  }

  return (
    <div className={styles.root}>
      <button
        type="button"
        ref={buttonRef}
        className={styles.bell}
        onClick={() => setOpen((previous) => !previous)}
        aria-expanded={open}
        aria-label={unreadCount > 0 ? `Notifications, ${unreadCount} unread` : 'Notifications'}
      >
        <span aria-hidden="true" className={styles.icon}>
          🔔
        </span>
        {unreadCount > 0 && (
          <span className={styles.badge} aria-hidden="true">
            {unreadCount > 99 ? '99+' : unreadCount}
          </span>
        )}
      </button>
      {open && <NotificationPanel onClose={handleClose} onUnreadCountChange={setUnreadCount} />}
    </div>
  )
}
