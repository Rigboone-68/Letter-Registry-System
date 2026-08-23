import { Link } from 'react-router-dom'

import EmptyState from './EmptyState'
import ErrorState from './ErrorState'
import LoadingState from './LoadingState'
import StatusBadge from './StatusBadge'
import { LETTER_STATUS_OPTIONS } from '../services/letterService'
import styles from './RecentLetters.module.css'

function statusLabel(value) {
  return LETTER_STATUS_OPTIONS.find((option) => option.value === value)?.label ?? value
}

function formatDate(value) {
  if (!value) return '—'
  return new Date(value).toLocaleDateString(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  })
}

/**
 * The dashboard's "Recent Letters" widget (Phase 5F,
 * docs/architecture/dashboard.md §16). A small, fixed-size list, not
 * the full `LetterTable` — this widget has no sorting/filtering
 * interaction, just the same request `LetterListPage` already makes
 * (`letterService.list`), sorted newest-first and limited, so it
 * inherits that endpoint's own department/classified-access scoping
 * with no additional frontend logic (§7 of the review).
 *
 * A Letter this component renders is exactly what the backend returned
 * — nothing here infers or hides anything beyond that. Clicking through
 * to a Letter that later 404s (e.g. its access changed since this list
 * was fetched) is handled by the existing `LetterDetailPage` 404
 * behavior, unchanged.
 */
export default function RecentLetters({ letters, loading, error }) {
  if (loading) return <LoadingState label="Loading recent letters..." />
  if (error) return <ErrorState message={error.message} />
  if (letters.length === 0) return <EmptyState message="No letters recorded yet." />

  return (
    <ul className={styles.list}>
      {letters.map((letter) => (
        <li key={letter.id} className={styles.item}>
          <Link to={`/app/letters/${letter.id}`} className={styles.link}>
            <span className={styles.reference}>{letter.reference_number}</span>
            <span className={styles.subject}>{letter.subject ?? '—'}</span>
          </Link>
          <span className={styles.meta}>
            <StatusBadge value={letter.status} label={statusLabel(letter.status)} domain="Letter" />
            <span className={styles.date}>{formatDate(letter.received_at)}</span>
          </span>
        </li>
      ))}
    </ul>
  )
}
