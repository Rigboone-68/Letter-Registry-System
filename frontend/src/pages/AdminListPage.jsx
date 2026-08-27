import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'

import AdminTable from '../components/AdminTable'
import DepartmentSelector from '../components/DepartmentSelector'
import EmptyState from '../components/EmptyState'
import ErrorState from '../components/ErrorState'
import LoadingState from '../components/LoadingState'
import * as adminService from '../services/adminService'
import * as departmentService from '../services/departmentService'
import styles from './AdminPages.module.css'

function toLookupMap(items) {
  const map = {}
  for (const item of items) map[item.id] = item.name
  return map
}

/**
 * Administrators list page (Phase 5D,
 * docs/architecture/administration-ui.md §4.2) — `GET /api/v1/admins`.
 * No pagination/search/sort exists (§11); `status` and `department_id`
 * are both real, supported filters here — unlike the Users list, where
 * only `status` applies. `SYSTEM_ADMIN`-only route.
 */
export default function AdminListPage() {
  const [status, setStatus] = useState('')
  const [departmentId, setDepartmentId] = useState('')
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [departments, setDepartments] = useState(null)

  useEffect(() => {
    departmentService
      .list()
      .then((response) => setDepartments(response.items))
      .catch(() => {
        // Department names/filter are a display convenience — a failure
        // here degrades to raw ids never being shown (— rendered as
        // "—") rather than blocking the Admins list itself.
      })
  }, [])

  const fetchAdmins = useCallback(() => {
    setLoading(true)
    setError(null)
    const params = {}
    if (status) params.status = status
    if (departmentId) params.department_id = departmentId
    adminService
      .list(params)
      .then((response) => setData(response))
      .catch((normalizedError) => setError(normalizedError))
      .finally(() => setLoading(false))
  }, [status, departmentId])

  useEffect(() => {
    fetchAdmins()
  }, [fetchAdmins])

  const departmentById = departments ? toLookupMap(departments) : null

  return (
    <section className={styles.root}>
      <div className={styles.header}>
        <div className={styles.headerText}>
          <p className={styles.eyebrow}>Administrator Management</p>
          <div className={styles.titleRow}>
            <h1>Administrators</h1>
            <span className={styles.headerMark} aria-hidden="true" />
          </div>
          {data && <p className={styles.count}>{data.total} total</p>}
        </div>
        <div className={styles.headerActions}>
          <button type="button" onClick={fetchAdmins}>
            Refresh
          </button>
          <Link to="/app/system/admins/authorize" className={styles.createLink}>
            Authorize new Admin
          </Link>
        </div>
      </div>

      <div className={styles.filters}>
        <div className={styles.field}>
          <label htmlFor="admin-status-filter">Status</label>
          <select
            id="admin-status-filter"
            value={status}
            onChange={(event) => setStatus(event.target.value)}
          >
            <option value="">Any</option>
            <option value="PENDING_APPROVAL">Pending Approval</option>
            <option value="ACTIVE">Active</option>
            <option value="DEACTIVATED">Deactivated</option>
          </select>
        </div>
        {departments && (
          <div className={styles.field}>
            <label htmlFor="admin-department-filter">Department</label>
            <DepartmentSelector
              id="admin-department-filter"
              departments={departments}
              value={departmentId}
              onChange={(event) => setDepartmentId(event.target.value)}
              activeOnly={false}
              includeAllOption
            />
          </div>
        )}
      </div>

      {loading && <LoadingState label="Loading administrators..." />}
      {!loading && error && <ErrorState message={error.message} onRetry={fetchAdmins} />}
      {!loading && !error && data && data.items.length === 0 && (
        <EmptyState message="No administrators match the current filters." />
      )}
      {!loading && !error && data && data.items.length > 0 && (
        <AdminTable admins={data.items} departmentById={departmentById} />
      )}
    </section>
  )
}
