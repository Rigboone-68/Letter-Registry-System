import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'

import EmptyState from '../components/EmptyState'
import ErrorState from '../components/ErrorState'
import LoadingState from '../components/LoadingState'
import UserTable from '../components/UserTable'
import * as userService from '../services/userService'
import styles from './AdminPages.module.css'

/**
 * Users list page (Phase 5D, docs/architecture/administration-ui.md
 * §5.1) — `GET /api/v1/users`, always scoped server-side to the calling
 * Admin's own department. No pagination/search/sort exists (§11); only
 * `status` is a real filter — there is no `department_id` parameter on
 * this endpoint at all (nothing to filter by; an Admin only ever sees
 * their own department). `ADMIN`-only route.
 */
export default function UserListPage() {
  const [status, setStatus] = useState('')
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const fetchUsers = useCallback(() => {
    setLoading(true)
    setError(null)
    const params = status ? { status } : {}
    userService
      .list(params)
      .then((response) => setData(response))
      .catch((normalizedError) => setError(normalizedError))
      .finally(() => setLoading(false))
  }, [status])

  useEffect(() => {
    fetchUsers()
  }, [fetchUsers])

  return (
    <section className={styles.root}>
      <div className={styles.header}>
        <div>
          <h1>Users</h1>
          {data && <p className={styles.count}>{data.total} total</p>}
        </div>
        <div className={styles.headerActions}>
          <button type="button" onClick={fetchUsers}>
            Refresh
          </button>
          <Link to="/app/admin/users/authorizations">Authorizations</Link>
          <Link to="/app/admin/users/authorize" className={styles.createLink}>
            Authorize new User
          </Link>
        </div>
      </div>

      <div className={styles.filters}>
        <div className={styles.field}>
          <label htmlFor="user-status-filter">Status</label>
          <select
            id="user-status-filter"
            value={status}
            onChange={(event) => setStatus(event.target.value)}
          >
            <option value="">Any</option>
            <option value="PENDING_APPROVAL">Pending Approval</option>
            <option value="ACTIVE">Active</option>
            <option value="DEACTIVATED">Deactivated</option>
          </select>
        </div>
      </div>

      {loading && <LoadingState label="Loading users..." />}
      {!loading && error && <ErrorState message={error.message} onRetry={fetchUsers} />}
      {!loading && !error && data && data.items.length === 0 && (
        <EmptyState message="No users match the current filter." />
      )}
      {!loading && !error && data && data.items.length > 0 && <UserTable users={data.items} />}
    </section>
  )
}
