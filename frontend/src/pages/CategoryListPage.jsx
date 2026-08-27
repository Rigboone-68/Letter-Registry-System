import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'

import CategoryTable from '../components/CategoryTable'
import EmptyState from '../components/EmptyState'
import ErrorState from '../components/ErrorState'
import LoadingState from '../components/LoadingState'
import * as categoryService from '../services/categoryService'
import styles from './AdminPages.module.css'

/**
 * Category list page (Phase 5H.1, mirroring `DepartmentListPage.jsx`
 * exactly) — `GET /api/v1/categories`. No pagination/search/sort
 * exists on this endpoint (same confirmed backend-contract limitation
 * as Departments) — the complete matching result set is rendered
 * as-is; only the one real backend filter (`status`) is exposed.
 * `SYSTEM_ADMIN`-only route (enforced by `RoleGuard` in
 * `routes/index.jsx`, not by anything in this component).
 *
 * This resource already existed on the backend since Phase 4B (the
 * three seeded V1 categories) — this page and its siblings
 * (`CategoryCreatePage`/`CategoryDetailPage`) are the first frontend
 * screens for it; nothing about the backend contract changed.
 */
export default function CategoryListPage() {
  const [status, setStatus] = useState('')
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const fetchCategories = useCallback(() => {
    setLoading(true)
    setError(null)
    const params = status ? { status } : {}
    categoryService
      .list(params)
      .then((response) => setData(response))
      .catch((normalizedError) => setError(normalizedError))
      .finally(() => setLoading(false))
  }, [status])

  useEffect(() => {
    fetchCategories()
  }, [fetchCategories])

  return (
    <section className={styles.root}>
      <div className={styles.header}>
        <div className={styles.headerText}>
          <p className={styles.eyebrow}>Category Master Data</p>
          <div className={styles.titleRow}>
            <h1>Categories</h1>
            <span className={styles.headerMark} aria-hidden="true" />
          </div>
          {data && <p className={styles.count}>{data.total} total</p>}
        </div>
        <div className={styles.headerActions}>
          <button type="button" onClick={fetchCategories}>
            Refresh
          </button>
          <Link to="/app/system/categories/new" className={styles.createLink}>
            Create Category
          </Link>
        </div>
      </div>

      <div className={styles.filters}>
        <div className={styles.field}>
          <label htmlFor="category-status-filter">Status</label>
          <select
            id="category-status-filter"
            value={status}
            onChange={(event) => setStatus(event.target.value)}
          >
            <option value="">Any</option>
            <option value="ACTIVE">Active</option>
            <option value="INACTIVE">Inactive</option>
          </select>
        </div>
      </div>

      {loading && <LoadingState label="Loading categories..." />}
      {!loading && error && <ErrorState message={error.message} onRetry={fetchCategories} />}
      {!loading && !error && data && data.items.length === 0 && (
        <EmptyState message="No categories match the current filter." />
      )}
      {!loading && !error && data && data.items.length > 0 && (
        <CategoryTable categories={data.items} />
      )}
    </section>
  )
}
