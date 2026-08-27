import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'

import ClassificationTable from '../components/ClassificationTable'
import EmptyState from '../components/EmptyState'
import ErrorState from '../components/ErrorState'
import LoadingState from '../components/LoadingState'
import * as classificationService from '../services/classificationService'
import styles from './AdminPages.module.css'

/**
 * Classification list page (Phase 5H.1, mirroring
 * `CategoryListPage.jsx`/`DepartmentListPage.jsx`) —
 * `GET /api/v1/classifications`. No pagination/search/sort exists on
 * this endpoint — the complete matching result set is rendered as-is;
 * only the one real backend filter (`status`) is exposed.
 * `SYSTEM_ADMIN`-only route (enforced by `RoleGuard`).
 *
 * This resource already existed on the backend since Phase 4B —
 * nothing about the classified-access authorization behavior
 * (`assert_letter_access`/`restricts_access`) changes here; this page
 * only renders what the backend already returns.
 */
export default function ClassificationListPage() {
  const [status, setStatus] = useState('')
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const fetchClassifications = useCallback(() => {
    setLoading(true)
    setError(null)
    const params = status ? { status } : {}
    classificationService
      .list(params)
      .then((response) => setData(response))
      .catch((normalizedError) => setError(normalizedError))
      .finally(() => setLoading(false))
  }, [status])

  useEffect(() => {
    fetchClassifications()
  }, [fetchClassifications])

  return (
    <section className={styles.root}>
      <div className={styles.header}>
        <div className={styles.headerText}>
          <p className={styles.eyebrow}>Classification Master Data</p>
          <div className={styles.titleRow}>
            <h1>Classifications</h1>
            <span className={styles.headerMark} aria-hidden="true" />
          </div>
          {data && <p className={styles.count}>{data.total} total</p>}
        </div>
        <div className={styles.headerActions}>
          <button type="button" onClick={fetchClassifications}>
            Refresh
          </button>
          <Link to="/app/system/classifications/new" className={styles.createLink}>
            Create Classification
          </Link>
        </div>
      </div>

      <div className={styles.filters}>
        <div className={styles.field}>
          <label htmlFor="classification-status-filter">Status</label>
          <select
            id="classification-status-filter"
            value={status}
            onChange={(event) => setStatus(event.target.value)}
          >
            <option value="">Any</option>
            <option value="ACTIVE">Active</option>
            <option value="INACTIVE">Inactive</option>
          </select>
        </div>
      </div>

      {loading && <LoadingState label="Loading classifications..." />}
      {!loading && error && <ErrorState message={error.message} onRetry={fetchClassifications} />}
      {!loading && !error && data && data.items.length === 0 && (
        <EmptyState message="No classifications match the current filter." />
      )}
      {!loading && !error && data && data.items.length > 0 && (
        <ClassificationTable classifications={data.items} />
      )}
    </section>
  )
}
