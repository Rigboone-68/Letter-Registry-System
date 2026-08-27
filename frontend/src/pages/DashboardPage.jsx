import { useCallback, useEffect, useState } from 'react'

import QuickActions from '../components/QuickActions'
import RecentLetters from '../components/RecentLetters'
import SummaryCard from '../components/SummaryCard'
import { useAuth } from '../context/AuthContext'
import * as adminService from '../services/adminService'
import * as departmentService from '../services/departmentService'
import * as letterService from '../services/letterService'
import * as notificationService from '../services/notificationService'
import * as userService from '../services/userService'
import styles from './DashboardPage.module.css'

const RECENT_LETTERS_PAGE_SIZE = 5

/**
 * Dashboard & Operational Overview (Phase 5F,
 * docs/architecture/dashboard.md). Implements only the metrics the
 * review classified as directly available or cheaply derivable from
 * existing, already-isolated endpoints (§3/§14) — no aggregate/
 * dashboard-specific backend endpoint exists or is called; every
 * request below is one an existing service module already exposes.
 *
 * One dashboard, not three — every request except the administration
 * summary (§ below) is identical regardless of role, because the
 * backend itself already scopes the result (SYSTEM_ADMIN sees every
 * department, ADMIN/USER are narrowed server-side to their own). This
 * component never inspects `user.department_id` or sends it as a
 * parameter — department scoping is entirely the backend's decision
 * (§6 of the review).
 *
 * Four independently-fetched, independently-failing widgets (§15/§20 of
 * the implementation brief): a failed request in one never blocks or
 * hides the others. A failed request renders "Unavailable"
 * (`SummaryCard`) or the existing `ErrorState` — never a silent zero.
 *
 * Phase 5I.4A (docs/architecture/ui-design-system.md) is a visual-only
 * recomposition into a header/metrics/activity/actions layout — no
 * metric, request, role branch, or fetch above was added, removed, or
 * reordered; every string the new header renders ("Registry Overview,"
 * the subtitle) is a neutral section label, never a system-health or
 * security claim this application has no data to back.
 */
export default function DashboardPage() {
  const { user } = useAuth()
  const role = user?.role

  const [letterSummary, setLetterSummary] = useState({ loading: true, error: null, data: null })
  const [adminSummary, setAdminSummary] = useState({ loading: role !== 'USER', error: null, data: null })
  const [unreadCount, setUnreadCount] = useState({ loading: true, error: null, value: null })
  const [recentLetters, setRecentLetters] = useState({ loading: true, error: null, items: [] })

  // Total/active/archived — the three cheapest possible Letter counts
  // (docs/architecture/dashboard.md §3): one request each, `page_size: 1`,
  // reading only `.total`, which the backend computes as a real SQL
  // `COUNT` on the same department/classified-visibility-scoped
  // statement as any other Letter query (§2.1/§7 of the review) — no
  // frontend filtering of any kind is applied to these numbers.
  const fetchLetterSummary = useCallback(() => {
    setLetterSummary((previous) => ({ ...previous, loading: true, error: null }))
    Promise.all([
      letterService.list({ page_size: 1 }),
      letterService.list({ status: 'ACTIVE', page_size: 1 }),
      letterService.list({ status: 'ARCHIVED', page_size: 1 }),
    ])
      .then(([all, active, archived]) => {
        setLetterSummary({
          loading: false,
          error: null,
          data: { total: all.total, active: active.total, archived: archived.total },
        })
      })
      .catch((normalizedError) => setLetterSummary({ loading: false, error: normalizedError, data: null }))
  }, [])

  // Role-scoped administration summary (docs/architecture/dashboard.md
  // §14): SYSTEM_ADMIN sees active departments + pending Admin
  // approvals, ADMIN sees active users (own department, server-derived)
  // + pending User approvals, USER sees none of this — every
  // SYSTEM_ADMIN-only/ADMIN-only endpoint below is exactly the one the
  // existing Departments/Administrators/Users screens already call; no
  // new endpoint, no cross-department parameter.
  const fetchAdminSummary = useCallback(() => {
    if (role === 'SYSTEM_ADMIN') {
      setAdminSummary({ loading: true, error: null, data: null })
      Promise.all([
        departmentService.list({ status: 'ACTIVE' }),
        adminService.list({ status: 'PENDING_APPROVAL' }),
      ])
        .then(([departments, admins]) => {
          setAdminSummary({
            loading: false,
            error: null,
            data: { activeDepartments: departments.total, pendingAdmins: admins.total },
          })
        })
        .catch((normalizedError) => setAdminSummary({ loading: false, error: normalizedError, data: null }))
      return
    }
    if (role === 'ADMIN') {
      setAdminSummary({ loading: true, error: null, data: null })
      Promise.all([userService.list({ status: 'ACTIVE' }), userService.list({ status: 'PENDING_APPROVAL' })])
        .then(([users, pending]) => {
          setAdminSummary({
            loading: false,
            error: null,
            data: { activeUsers: users.total, pendingUsers: pending.total },
          })
        })
        .catch((normalizedError) => setAdminSummary({ loading: false, error: normalizedError, data: null }))
      return
    }
    setAdminSummary({ loading: false, error: null, data: null })
  }, [role])

  // A single, one-time fetch — never a second polling interval.
  // `NotificationBell` (Phase 5E) already owns the recurring
  // `/notifications/unread-count` poll for the Topbar badge; this is a
  // separate, one-shot read of the same cheap endpoint on dashboard
  // mount, not a duplicate timer (docs/architecture/dashboard.md §10/§19).
  const fetchUnreadCount = useCallback(() => {
    setUnreadCount({ loading: true, error: null, value: null })
    notificationService
      .unreadCount()
      .then((response) => setUnreadCount({ loading: false, error: null, value: response.unread_count }))
      .catch((normalizedError) => setUnreadCount({ loading: false, error: normalizedError, value: null }))
  }, [])

  // Newest-first, limited to a handful of rows — the same request
  // `LetterListPage` already makes, never the full registry
  // (docs/architecture/dashboard.md §8/§16).
  const fetchRecentLetters = useCallback(() => {
    setRecentLetters((previous) => ({ ...previous, loading: true, error: null }))
    letterService
      .list({ sort_by: 'received_at', sort_order: 'desc', page_size: RECENT_LETTERS_PAGE_SIZE })
      .then((response) => setRecentLetters({ loading: false, error: null, items: response.items }))
      .catch((normalizedError) => setRecentLetters({ loading: false, error: normalizedError, items: [] }))
  }, [])

  useEffect(() => {
    fetchLetterSummary()
  }, [fetchLetterSummary])

  useEffect(() => {
    fetchAdminSummary()
  }, [fetchAdminSummary])

  useEffect(() => {
    fetchUnreadCount()
  }, [fetchUnreadCount])

  useEffect(() => {
    fetchRecentLetters()
  }, [fetchRecentLetters])

  const cards = [
    {
      key: 'total',
      label: 'Total Letters',
      value: letterSummary.data?.total,
      loading: letterSummary.loading,
      error: letterSummary.error,
    },
    {
      key: 'active',
      label: 'Active Letters',
      value: letterSummary.data?.active,
      loading: letterSummary.loading,
      error: letterSummary.error,
    },
    {
      key: 'archived',
      label: 'Archived Letters',
      value: letterSummary.data?.archived,
      loading: letterSummary.loading,
      error: letterSummary.error,
    },
    {
      key: 'unread',
      label: 'Unread Notifications',
      value: unreadCount.value,
      loading: unreadCount.loading,
      error: unreadCount.error,
    },
  ]

  if (role === 'SYSTEM_ADMIN') {
    cards.push(
      {
        key: 'active-departments',
        label: 'Active Departments',
        value: adminSummary.data?.activeDepartments,
        loading: adminSummary.loading,
        error: adminSummary.error,
      },
      {
        key: 'pending-admins',
        label: 'Pending Admin Approvals',
        value: adminSummary.data?.pendingAdmins,
        loading: adminSummary.loading,
        error: adminSummary.error,
      }
    )
  } else if (role === 'ADMIN') {
    cards.push(
      {
        key: 'active-users',
        label: 'Active Users',
        value: adminSummary.data?.activeUsers,
        loading: adminSummary.loading,
        error: adminSummary.error,
      },
      {
        key: 'pending-users',
        label: 'Pending User Approvals',
        value: adminSummary.data?.pendingUsers,
        loading: adminSummary.loading,
        error: adminSummary.error,
      }
    )
  }

  return (
    <div className={styles.root}>
      <header className={styles.header}>
        <p className={styles.eyebrow}>Registry Overview</p>
        <div className={styles.headerRow}>
          <h1>Dashboard</h1>
          <span className={styles.headerMark} aria-hidden="true" />
        </div>
        <p className={styles.subtitle}>
          Current registry activity and quick actions for your role.
        </p>
      </header>

      <section aria-label="Summary" className={styles.cards}>
        {cards.map(({ key, ...card }) => (
          <SummaryCard key={key} {...card} />
        ))}
      </section>

      <div className={styles.grid}>
        <section className={styles.section}>
          <div className={styles.sectionHeader}>
            <h2>Recent Letters</h2>
            {!recentLetters.loading && !recentLetters.error && (
              <p className={styles.sectionMeta}>{recentLetters.items.length} shown</p>
            )}
          </div>
          <RecentLetters
            letters={recentLetters.items}
            loading={recentLetters.loading}
            error={recentLetters.error}
          />
        </section>

        <section className={styles.section}>
          <div className={styles.sectionHeader}>
            <h2>Quick Actions</h2>
          </div>
          <QuickActions role={role} />
        </section>
      </div>
    </div>
  )
}
