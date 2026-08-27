import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'

import DepartmentTable from '../components/DepartmentTable'
import EmptyState from '../components/EmptyState'
import ErrorState from '../components/ErrorState'
import LoadingState from '../components/LoadingState'
import * as departmentService from '../services/departmentService'
import styles from './AdminPages.module.css'

/**
 * Department list page (Phase 5D,
 * docs/architecture/administration-ui.md §4.1) — `GET /api/v1/departments`.
 * No pagination/search/sort exists on this endpoint (§11) — the
 * complete matching result set is rendered as-is; only the one real
 * backend filter (`status`) is exposed. `SYSTEM_ADMIN`-only route.
 */
export default function DepartmentListPage() {
  const [status, setStatus] = useState('')
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const fetchDepartments = useCallback(() => {
    setLoading(true)
    setError(null)
    const params = status ? { status } : {}
    departmentService
      .list(params)
      .then((response) => setData(response))
      .catch((normalizedError) => setError(normalizedError))
      .finally(() => setLoading(false))
  }, [status])

  useEffect(() => {
    fetchDepartments()
  }, [fetchDepartments])

  return (
    <section className={styles.root}>
      <div className={styles.header}>
        <div className={styles.headerText}>
          <p className={styles.eyebrow}>Department Administration</p>
          <div className={styles.titleRow}>
            <h1>Departments</h1>
            <span className={styles.headerMark} aria-hidden="true" />
          </div>
          {data && <p className={styles.count}>{data.total} total</p>}
        </div>
        <div className={styles.headerActions}>
          <button type="button" onClick={fetchDepartments}>
            Refresh
          </button>
          <Link to="/app/system/departments/new" className={styles.createLink}>
            Create Department
          </Link>
        </div>
      </div>

      <div className={styles.filters}>
        <div className={styles.field}>
          <label htmlFor="department-status-filter">Status</label>
          <select
            id="department-status-filter"
            value={status}
            onChange={(event) => setStatus(event.target.value)}
          >
            <option value="">Any</option>
            <option value="ACTIVE">Active</option>
            <option value="INACTIVE">Inactive</option>
          </select>
        </div>
      </div>

      {loading && <LoadingState label="Loading departments..." />}
      {!loading && error && <ErrorState message={error.message} onRetry={fetchDepartments} />}
      {!loading && !error && data && data.items.length === 0 && (
        <EmptyState message="No departments match the current filter." />
      )}
      {!loading && !error && data && data.items.length > 0 && (
        <DepartmentTable departments={data.items} />
      )}
    </section>
  )
}
