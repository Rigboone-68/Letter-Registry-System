import styles from './Pagination.module.css'

const MAX_VISIBLE_PAGES = 5

function visiblePageNumbers(page, totalPages) {
  if (totalPages <= MAX_VISIBLE_PAGES) {
    return Array.from({ length: totalPages }, (_, index) => index + 1)
  }
  const half = Math.floor(MAX_VISIBLE_PAGES / 2)
  let start = Math.max(1, page - half)
  const end = Math.min(totalPages, start + MAX_VISIBLE_PAGES - 1)
  start = Math.max(1, end - MAX_VISIBLE_PAGES + 1)
  return Array.from({ length: end - start + 1 }, (_, index) => start + index)
}

/**
 * A reusable pagination control driven entirely by the backend's own
 * `page`/`page_size`/`total`/`total_pages` (docs/architecture/frontend.md
 * §9/§20) — this component never recomputes `total_pages` itself.
 */
export default function Pagination({ page, totalPages, total, onPageChange }) {
  if (totalPages <= 1) {
    return (
      <p className={styles.summary}>
        {total} {total === 1 ? 'result' : 'results'}
      </p>
    )
  }

  const pages = visiblePageNumbers(page, totalPages)

  return (
    <nav className={styles.root} aria-label="Registry pagination">
      <p className={styles.summary}>{total} results</p>
      <div className={styles.controls}>
        <button
          type="button"
          onClick={() => onPageChange(page - 1)}
          disabled={page <= 1}
          aria-label="Previous page"
        >
          Previous
        </button>
        {pages[0] > 1 && <span className={styles.ellipsis}>…</span>}
        {pages.map((pageNumber) => (
          <button
            key={pageNumber}
            type="button"
            className={pageNumber === page ? styles.current : undefined}
            aria-current={pageNumber === page ? 'page' : undefined}
            onClick={() => onPageChange(pageNumber)}
          >
            {pageNumber}
          </button>
        ))}
        {pages[pages.length - 1] < totalPages && <span className={styles.ellipsis}>…</span>}
        <button
          type="button"
          onClick={() => onPageChange(page + 1)}
          disabled={page >= totalPages}
          aria-label="Next page"
        >
          Next
        </button>
      </div>
    </nav>
  )
}
