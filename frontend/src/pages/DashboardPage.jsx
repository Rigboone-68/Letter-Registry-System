import { useCallback, useEffect, useState } from 'react'

import CorrespondenceTrendChart from '../components/CorrespondenceTrendChart'
import HorizontalBarChart from '../components/HorizontalBarChart'
import QuickActions from '../components/QuickActions'
import RecentLetters from '../components/RecentLetters'
import SummaryCard from '../components/SummaryCard'
import { useAuth } from '../context/AuthContext'
import * as departmentService from '../services/departmentService'
import * as letterService from '../services/letterService'
import * as notificationService from '../services/notificationService'
import { departmentBars, directionBars, mergeTrendSeries } from '../utils/aggregateChartHelpers'
import styles from './DashboardPage.module.css'

const RECENT_LETTERS_PAGE_SIZE = 5

/**
 * Dashboard & Operational Overview — Phase 6D rework
 * (docs/architecture/dashboard.md "Phase 6D" section). A confirmed
 * supervisor requirement replaced the Phase 5F/5I KPI-card
 * presentation with graphs, since numeric cards were difficult for
 * non-technical staff to interpret at a glance. The eight role-
 * dependent SummaryCards this page used to render are gone; only two
 * small headline figures remain (Total Letters, Unread Notifications)
 * — genuinely orienting numbers, not a shrunk-down copy of the old
 * card wall. The previous SYSTEM_ADMIN/ADMIN administration cards
 * (Active Departments, Pending Admin Approvals, Active Users, Pending
 * User Approvals) are deliberately not reintroduced as charts — they
 * answer an administration question, not the confirmed correspondence-
 * volume question this phase's brief actually asked for, and the
 * Departments/Administrators/Users screens already show that data.
 *
 * Four charts, each backed by exactly one (or, for the trend chart,
 * two bounded) `GET /letters/aggregate` request (Phase 6C) — never the
 * full Letter registry, never a client-side aggregation, never one
 * request per department. Every chart fails independently: a failed
 * request renders that chart's own `ErrorState`, never blanking the
 * rest of the page. No chart is hidden by role — the aggregate API
 * itself is the authorization boundary (SYSTEM_ADMIN unrestricted,
 * ADMIN/USER server-scoped to their own department), so this component
 * never inspects `user.department_id` or sends one as a parameter.
 *
 * Department × Direction (e.g. "which department sent the most
 * Outgoing correspondence") is explicitly out of scope this phase —
 * DEFERRED, requires a two-dimensional aggregate endpoint the backend
 * deliberately does not provide (docs/architecture/
 * dashboard-analytics-api.md §32.9).
 */
export default function DashboardPage() {
  const { user } = useAuth()
  const role = user?.role

  const [totalLetters, setTotalLetters] = useState({ loading: true, error: null, value: null })
  const [unreadCount, setUnreadCount] = useState({ loading: true, error: null, value: null })
  const [recentLetters, setRecentLetters] = useState({ loading: true, error: null, items: [] })

  const [directionSummary, setDirectionSummary] = useState({ loading: true, error: null, buckets: [] })
  const [departmentNames, setDepartmentNames] = useState({ loading: true, error: null, byId: new Map() })
  const [receivedSummary, setReceivedSummary] = useState({ loading: true, error: null, buckets: [] })
  const [sentSummary, setSentSummary] = useState({ loading: true, error: null, buckets: [] })
  const [trendSummary, setTrendSummary] = useState({ loading: true, error: null, points: [] })

  // Total Letters — the same cheap `page_size: 1`/`.total` request
  // this page has always used (docs/architecture/dashboard.md §3),
  // kept as the one headline figure that orients a reader before the
  // charts below break it down further.
  const fetchTotalLetters = useCallback(() => {
    setTotalLetters((previous) => ({ ...previous, loading: true, error: null }))
    letterService
      .list({ page_size: 1 })
      .then((response) => setTotalLetters({ loading: false, error: null, value: response.total }))
      .catch((normalizedError) => setTotalLetters({ loading: false, error: normalizedError, value: null }))
  }, [])

  // A single, one-time fetch — `NotificationBell` already owns the
  // recurring poll for the Topbar badge; this is a separate, one-shot
  // read of the same cheap endpoint on dashboard mount, not a second
  // polling loop.
  const fetchUnreadCount = useCallback(() => {
    setUnreadCount({ loading: true, error: null, value: null })
    notificationService
      .unreadCount()
      .then((response) => setUnreadCount({ loading: false, error: null, value: response.unread_count }))
      .catch((normalizedError) => setUnreadCount({ loading: false, error: normalizedError, value: null }))
  }, [])

  const fetchRecentLetters = useCallback(() => {
    setRecentLetters((previous) => ({ ...previous, loading: true, error: null }))
    letterService
      .list({ sort_by: 'received_at', sort_order: 'desc', page_size: RECENT_LETTERS_PAGE_SIZE })
      .then((response) => setRecentLetters({ loading: false, error: null, items: response.items }))
      .catch((normalizedError) => setRecentLetters({ loading: false, error: normalizedError, items: [] }))
  }, [])

  // Graph 1 — Incoming vs. Outgoing (§4).
  const fetchDirectionSummary = useCallback(() => {
    setDirectionSummary((previous) => ({ ...previous, loading: true, error: null }))
    letterService
      .aggregate({ group_by: 'direction' })
      .then((response) => setDirectionSummary({ loading: false, error: null, buckets: response.buckets }))
      .catch((normalizedError) => setDirectionSummary({ loading: false, error: normalizedError, buckets: [] }))
  }, [])

  // Shared department-id → name lookup for Graphs 2 and 3 — one
  // request, reused by both, never one request per department. Reuses
  // the existing `GET /departments` endpoint the Letter form's Source
  // Department selector already calls (readable by any authenticated
  // role since Phase 5H).
  const fetchDepartmentNames = useCallback(() => {
    setDepartmentNames((previous) => ({ ...previous, loading: true, error: null }))
    departmentService
      .list()
      .then((response) => {
        const byId = new Map(response.items.map((department) => [department.id, department.name]))
        setDepartmentNames({ loading: false, error: null, byId })
      })
      .catch((normalizedError) => setDepartmentNames({ loading: false, error: normalizedError, byId: new Map() }))
  }, [])

  // Graph 2 — Letters Received by Department (§5): `group_by=department`
  // is `recipient_department_id` — the owning department regardless of
  // direction (docs/architecture/dashboard-analytics-api.md §32.2).
  const fetchReceivedSummary = useCallback(() => {
    setReceivedSummary((previous) => ({ ...previous, loading: true, error: null }))
    letterService
      .aggregate({ group_by: 'department' })
      .then((response) => setReceivedSummary({ loading: false, error: null, buckets: response.buckets }))
      .catch((normalizedError) => setReceivedSummary({ loading: false, error: normalizedError, buckets: [] }))
  }, [])

  // Graph 3 — Letters Sent by Department (§6): `group_by=dispatch_department`
  // is the real Phase 6A dispatch target, never `source_department_id`
  // (which carries no authorization meaning and answers a different
  // question — see docs/architecture/dashboard-analytics-api.md §6).
  const fetchSentSummary = useCallback(() => {
    setSentSummary((previous) => ({ ...previous, loading: true, error: null }))
    letterService
      .aggregate({ group_by: 'dispatch_department' })
      .then((response) => setSentSummary({ loading: false, error: null, buckets: response.buckets }))
      .catch((normalizedError) => setSentSummary({ loading: false, error: normalizedError, buckets: [] }))
  }, [])

  // Graph 4 — Correspondence Activity Over Time (§7): two bounded,
  // direction-filtered `group_by=month` requests, merged client-side
  // by date key only (never by re-counting Letters) — the Phase 6C API
  // has no two-dimensional `group_by`, and this is the one safe way to
  // compare Incoming vs Outgoing over time without one (see
  // `mergeTrendSeries`, `utils/aggregateChartHelpers.js`).
  const fetchTrendSummary = useCallback(() => {
    setTrendSummary((previous) => ({ ...previous, loading: true, error: null }))
    Promise.all([
      letterService.aggregate({ group_by: 'month', direction: 'INCOMING' }),
      letterService.aggregate({ group_by: 'month', direction: 'OUTGOING' }),
    ])
      .then(([incoming, outgoing]) => {
        setTrendSummary({ loading: false, error: null, points: mergeTrendSeries(incoming.buckets, outgoing.buckets) })
      })
      .catch((normalizedError) => setTrendSummary({ loading: false, error: normalizedError, points: [] }))
  }, [])

  useEffect(() => {
    fetchTotalLetters()
  }, [fetchTotalLetters])

  useEffect(() => {
    fetchUnreadCount()
  }, [fetchUnreadCount])

  useEffect(() => {
    fetchRecentLetters()
  }, [fetchRecentLetters])

  useEffect(() => {
    fetchDirectionSummary()
  }, [fetchDirectionSummary])

  useEffect(() => {
    fetchDepartmentNames()
  }, [fetchDepartmentNames])

  useEffect(() => {
    fetchReceivedSummary()
  }, [fetchReceivedSummary])

  useEffect(() => {
    fetchSentSummary()
  }, [fetchSentSummary])

  useEffect(() => {
    fetchTrendSummary()
  }, [fetchTrendSummary])

  // The received/sent charts need both their own aggregate response
  // and the shared department-name lookup before they can render a
  // meaningful label — so each treats a department-name failure as its
  // own failure, without affecting the direction or trend charts.
  const receivedLoading = receivedSummary.loading || departmentNames.loading
  const receivedError = receivedSummary.error || departmentNames.error
  const sentLoading = sentSummary.loading || departmentNames.loading
  const sentError = sentSummary.error || departmentNames.error

  return (
    <div className={styles.root}>
      <header className={styles.header}>
        <p className={styles.eyebrow}>Registry Overview</p>
        <div className={styles.headerRow}>
          <h1>Dashboard</h1>
          <span className={styles.headerMark} aria-hidden="true" />
        </div>
        <p className={styles.subtitle}>Correspondence activity across your registry, at a glance.</p>
      </header>

      <section aria-label="Summary" className={styles.headline}>
        <SummaryCard
          label="Total Letters"
          value={totalLetters.value}
          loading={totalLetters.loading}
          error={totalLetters.error}
        />
        <SummaryCard
          label="Unread Notifications"
          value={unreadCount.value}
          loading={unreadCount.loading}
          error={unreadCount.error}
        />
      </section>

      <div className={styles.charts}>
        <section className={styles.chartSection} aria-labelledby="chart-direction-heading">
          <div className={styles.sectionHeader}>
            <h2 id="chart-direction-heading">Incoming vs. Outgoing Correspondence</h2>
          </div>
          <HorizontalBarChart
            title="Incoming vs. Outgoing Correspondence"
            description="Total correspondence recorded, split by direction."
            bars={directionBars(directionSummary.buckets)}
            loading={directionSummary.loading}
            error={directionSummary.error}
            emptyMessage="No correspondence recorded yet."
          />
        </section>

        <section className={styles.chartSection} aria-labelledby="chart-received-heading">
          <div className={styles.sectionHeader}>
            <h2 id="chart-received-heading">Letters Received by Department</h2>
          </div>
          <HorizontalBarChart
            title="Letters Received by Department"
            description="Which departments are receiving the most correspondence."
            bars={departmentBars(receivedSummary.buckets, departmentNames.byId)}
            loading={receivedLoading}
            error={receivedError}
            emptyMessage="No correspondence recorded yet."
          />
        </section>

        <section className={styles.chartSection} aria-labelledby="chart-sent-heading">
          <div className={styles.sectionHeader}>
            <h2 id="chart-sent-heading">Letters Sent by Department</h2>
          </div>
          <HorizontalBarChart
            title="Letters Sent by Department"
            description="Which departments are sending the most outgoing correspondence."
            bars={departmentBars(sentSummary.buckets, departmentNames.byId)}
            loading={sentLoading}
            error={sentError}
            emptyMessage="No outgoing correspondence has been dispatched yet."
          />
        </section>

        <section className={styles.chartSection} aria-labelledby="chart-trend-heading">
          <div className={styles.sectionHeader}>
            <h2 id="chart-trend-heading">Correspondence Activity Over Time</h2>
          </div>
          <CorrespondenceTrendChart
            points={trendSummary.points}
            loading={trendSummary.loading}
            error={trendSummary.error}
            emptyMessage="No correspondence recorded yet."
          />
        </section>
      </div>

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
