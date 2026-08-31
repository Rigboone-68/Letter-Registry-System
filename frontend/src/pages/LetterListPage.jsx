import { useCallback, useEffect, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'

import EmptyState from '../components/EmptyState'
import ErrorState from '../components/ErrorState'
import LetterFilters from '../components/LetterFilters'
import LetterTable from '../components/LetterTable'
import LoadingState from '../components/LoadingState'
import Pagination from '../components/Pagination'
import { useAuth } from '../context/AuthContext'
import * as categoryService from '../services/categoryService'
import * as classificationService from '../services/classificationService'
import * as departmentService from '../services/departmentService'
import * as letterService from '../services/letterService'
import { LETTER_SORT_FIELDS } from '../services/letterService'
import styles from './LetterListPage.module.css'

const DEFAULT_SORT_BY = 'received_at'
const DEFAULT_SORT_ORDER = 'desc'
const DEFAULT_PAGE_SIZE = 25

const FILTER_KEYS = [
  'reference_number',
  'subject',
  'sender_name',
  'sender_designation',
  'sender_department',
  'source_name',
  'source_location',
  'status',
  'direction',
  'category_id',
  'classification_id',
  'department_id',
  'received_from',
  'received_to',
]

function toLookupMap(items) {
  const map = {}
  for (const item of items) {
    map[item.id] = item.name
  }
  return map
}

/**
 * The Letter registry list/search page (docs/architecture/frontend.md
 * §9/§11, Phase 5C). Mounted at both `/app/letters` (USER/ADMIN — the
 * backend already scopes results to their own department; see
 * `app/services/letter_service.py:list_letters`) and
 * `/app/system/letters` (SYSTEM_ADMIN, `routes/index.jsx`) — this
 * component adapts to the caller's role rather than needing two
 * near-duplicate pages, the same "derive from the documented backend
 * contract, don't invent a frontend rule" approach `RoleGuard`/
 * `navigationConfig.js` already use.
 *
 * List/filter/sort/pagination state lives in the URL (`useSearchParams`,
 * already part of `react-router-dom` — no new dependency) so refresh,
 * back/forward, and bookmarking all preserve registry state (§11 of the
 * brief).
 *
 * CONFIRMED backend-contract limitation, deliberately not worked
 * around: `GET /api/v1/categories`, `/classifications`, and
 * `/departments` are all `require_system_admin`-only
 * (`app/api/v1/endpoints/{categories,classifications,departments}.py`).
 * A USER/ADMIN caller cannot resolve a category/classification/
 * department id to a name, so those columns/filters are only ever
 * rendered for a SYSTEM_ADMIN viewer, who is the only caller for whom
 * the underlying request would actually succeed.
 *
 * Phase 5I.4B (docs/architecture/ui-design-system.md) is a visual-only
 * recomposition of the header/filter/sort/table/pagination presentation
 * — every filter key, URL parameter, sort field, and request shape
 * above is unchanged; `activeCount` passed to `LetterFilters` is purely
 * decorative (a real count of already-computed `activeFilters`, never a
 * new filter concept).
 */
export default function LetterListPage() {
  const { user } = useAuth()
  const isSystemAdmin = user?.role === 'SYSTEM_ADMIN'
  const canCreate = user?.role === 'USER' || user?.role === 'ADMIN'

  const [searchParams, setSearchParams] = useSearchParams()
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [refreshToken, setRefreshToken] = useState(0)

  const [referenceData, setReferenceData] = useState({
    categories: null,
    classifications: null,
    departments: null,
  })

  const page = Number(searchParams.get('page') ?? '1') || 1
  const pageSize = Number(searchParams.get('page_size') ?? String(DEFAULT_PAGE_SIZE)) || DEFAULT_PAGE_SIZE
  const sortBy = searchParams.get('sort_by') ?? DEFAULT_SORT_BY
  const sortOrder = searchParams.get('sort_order') ?? DEFAULT_SORT_ORDER

  const activeFilters = {}
  for (const key of FILTER_KEYS) {
    const value = searchParams.get(key)
    if (value) activeFilters[key] = value
  }
  const hasActiveFilters = Object.keys(activeFilters).length > 0

  // Reference data (categories/classifications/departments) is loaded
  // once, only for SYSTEM_ADMIN — see the module docstring above.
  useEffect(() => {
    if (!isSystemAdmin) return
    let cancelled = false
    Promise.all([categoryService.list(), classificationService.list(), departmentService.list()])
      .then(([categories, classifications, departments]) => {
        if (cancelled) return
        setReferenceData({
          categories: categories.items,
          classifications: classifications.items,
          departments: departments.items,
        })
      })
      .catch(() => {
        // Reference data is a display/filter convenience, not the
        // registry's core function — a failure here degrades to the
        // base column/filter set rather than blocking the list.
      })
    return () => {
      cancelled = true
    }
  }, [isSystemAdmin])

  const fetchLetters = useCallback(() => {
    setLoading(true)
    setError(null)
    const params = { page, page_size: pageSize, sort_by: sortBy, sort_order: sortOrder, ...activeFilters }
    letterService
      .list(params)
      .then((response) => {
        setData(response)
        if (response.total_pages >= 1 && page > response.total_pages) {
          setSearchParams((previous) => {
            const next = new URLSearchParams(previous)
            next.set('page', String(response.total_pages))
            return next
          })
        }
      })
      .catch((normalizedError) => setError(normalizedError))
      .finally(() => setLoading(false))
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [searchParams.toString(), refreshToken])

  useEffect(() => {
    fetchLetters()
  }, [fetchLetters])

  function updateParams(updater) {
    setSearchParams((previous) => {
      const next = new URLSearchParams(previous)
      updater(next)
      return next
    })
  }

  function handleApplyFilters(values) {
    updateParams((next) => {
      for (const key of FILTER_KEYS) {
        if (values[key]) {
          next.set(key, values[key])
        } else {
          next.delete(key)
        }
      }
      next.set('page', '1')
    })
  }

  function handleClearFilters() {
    updateParams((next) => {
      for (const key of FILTER_KEYS) next.delete(key)
      next.set('page', '1')
      next.set('sort_by', DEFAULT_SORT_BY)
      next.set('sort_order', DEFAULT_SORT_ORDER)
    })
  }

  function handleSort(field) {
    updateParams((next) => {
      if (sortBy === field) {
        next.set('sort_order', sortOrder === 'asc' ? 'desc' : 'asc')
      } else {
        next.set('sort_by', field)
        next.set('sort_order', 'asc')
      }
      next.set('page', '1')
    })
  }

  function handlePageChange(nextPage) {
    updateParams((next) => next.set('page', String(nextPage)))
  }

  const categoryById = referenceData.categories ? toLookupMap(referenceData.categories) : null
  const classificationById = referenceData.classifications
    ? toLookupMap(referenceData.classifications)
    : null
  const departmentById = referenceData.departments ? toLookupMap(referenceData.departments) : null

  return (
    <section className={styles.root}>
      <div className={styles.header}>
        <div className={styles.headerText}>
          <p className={styles.eyebrow}>Letter Registry</p>
          <div className={styles.titleRow}>
            <h1>{isSystemAdmin ? 'Letters — all departments' : 'Letters'}</h1>
            <span className={styles.headerMark} aria-hidden="true" />
          </div>
          {data && <p className={styles.count}>{data.total} total</p>}
        </div>
        <div className={styles.headerActions}>
          <button
            type="button"
            className={styles.refreshButton}
            onClick={() => setRefreshToken((token) => token + 1)}
          >
            Refresh
          </button>
          {canCreate && (
            <Link to="/app/letters/new" className={styles.createLink}>
              Record New Letter
            </Link>
          )}
        </div>
      </div>

      <LetterFilters
        key={FILTER_KEYS.map((filterKey) => searchParams.get(filterKey) ?? '').join('|')}
        initialValues={activeFilters}
        onApply={handleApplyFilters}
        onClear={handleClearFilters}
        categoryOptions={referenceData.categories}
        classificationOptions={referenceData.classifications}
        departmentOptions={isSystemAdmin ? referenceData.departments : null}
        activeCount={Object.keys(activeFilters).length}
      />

      <div className={styles.sortRow}>
        <label htmlFor="sort-by-select">Sort by</label>
        <select
          id="sort-by-select"
          value={sortBy}
          onChange={(event) => {
            updateParams((next) => {
              next.set('sort_by', event.target.value)
              next.set('page', '1')
            })
          }}
        >
          {LETTER_SORT_FIELDS.map((field) => (
            <option key={field.value} value={field.value}>
              {field.label}
            </option>
          ))}
        </select>
        <button
          type="button"
          className={styles.sortToggle}
          onClick={() =>
            updateParams((next) => {
              next.set('sort_order', sortOrder === 'asc' ? 'desc' : 'asc')
              next.set('page', '1')
            })
          }
        >
          {sortOrder === 'asc' ? 'Ascending' : 'Descending'}
        </button>
      </div>

      {loading && <LoadingState label="Loading letters..." />}
      {!loading && error && <ErrorState message={error.message} onRetry={fetchLetters} />}
      {!loading && !error && data && data.items.length === 0 && (
        <EmptyState
          message={
            hasActiveFilters
              ? 'No letters match the current filters.'
              : 'No letters have been recorded yet.'
          }
        />
      )}
      {!loading && !error && data && data.items.length > 0 && (
        <>
          <LetterTable
            letters={data.items}
            sortBy={sortBy}
            sortOrder={sortOrder}
            onSort={handleSort}
            departmentById={isSystemAdmin ? departmentById : null}
            categoryById={categoryById}
            classificationById={classificationById}
          />
          <Pagination
            page={data.page}
            totalPages={data.total_pages}
            total={data.total}
            onPageChange={handlePageChange}
          />
        </>
      )}
    </section>
  )
}
