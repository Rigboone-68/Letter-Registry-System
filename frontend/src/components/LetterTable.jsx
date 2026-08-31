import { Link } from 'react-router-dom'

import StatusBadge from './StatusBadge'
import { LETTER_STATUS_OPTIONS } from '../services/letterService'
import styles from './LetterTable.module.css'

const SORTABLE_COLUMNS = [
  { key: 'reference_number', label: 'Reference Number' },
  { key: 'subject', label: 'Subject' },
  { key: 'received_at', label: 'Received Date' },
]

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
 * The Letter registry table (docs/architecture/frontend.md §9, Phase
 * 5C). Renders only fields `LetterListItem` actually returns (backend,
 * `app/schemas/letter.py`) — no per-row API call for category/
 * classification/department names; those are resolved from lookup maps
 * the caller already loaded once, and the corresponding column is
 * omitted entirely (not shown as a raw id) when no map is supplied — see
 * `pages/LetterListPage.jsx` for why only a SYSTEM_ADMIN caller can
 * supply them (the reference-data endpoints are SYSTEM_ADMIN-only).
 *
 * Phase 6A (docs/architecture/correspondence.md §9) adds two always-
 * rendered columns — Direction (a plain text badge, never color-only —
 * `StatusBadge`'s own shape-per-tone convention would be overkill for a
 * two-value field with no lifecycle) and Diary/Dispatch No.
 * (`letter.diary_number`, `—` for the historical letters that predate
 * this phase) — the operational identifier the business actually uses
 * day-to-day, shown prominently alongside (never replacing)
 * `reference_number`.
 */
export default function LetterTable({
  letters,
  sortBy,
  sortOrder,
  onSort,
  departmentById,
  categoryById,
  classificationById,
}) {
  function ariaSortFor(columnKey) {
    if (sortBy !== columnKey) return 'none'
    return sortOrder === 'asc' ? 'ascending' : 'descending'
  }

  return (
    <div className={styles.scroller}>
      <table className={styles.table}>
        <thead>
          <tr>
            {SORTABLE_COLUMNS.map((column) => (
              <th key={column.key} aria-sort={ariaSortFor(column.key)} scope="col">
                <button type="button" className={styles.sortButton} onClick={() => onSort(column.key)}>
                  {column.label}
                  <span aria-hidden="true" className={styles.sortIndicator}>
                    {sortBy === column.key ? (sortOrder === 'asc' ? '▲' : '▼') : ''}
                  </span>
                </button>
              </th>
            ))}
            <th scope="col">Direction</th>
            <th scope="col">Diary/Dispatch No.</th>
            {departmentById && <th scope="col">Department</th>}
            {categoryById && <th scope="col">Category</th>}
            {classificationById && <th scope="col">Classification</th>}
            <th scope="col">Source</th>
            <th scope="col">Status</th>
          </tr>
        </thead>
        <tbody>
          {letters.map((letter) => (
            <tr key={letter.id}>
              <th scope="row" className={styles.referenceCell}>
                <Link to={`/app/letters/${letter.id}`}>{letter.reference_number}</Link>
              </th>
              <td>{letter.subject ?? '—'}</td>
              <td>{formatDate(letter.received_at)}</td>
              <td>
                <span className={styles.directionBadge}>
                  {letter.direction === 'OUTGOING' ? 'Outgoing' : 'Incoming'}
                </span>
              </td>
              <td className={styles.diaryCell}>{letter.diary_number ?? '—'}</td>
              {departmentById && <td>{departmentById[letter.recipient_department_id] ?? '—'}</td>}
              {categoryById && <td>{letter.category_id ? categoryById[letter.category_id] ?? '—' : '—'}</td>}
              {classificationById && (
                <td>{letter.classification_id ? classificationById[letter.classification_id] ?? '—' : '—'}</td>
              )}
              <td>{letter.source_name}</td>
              <td>
                <StatusBadge value={letter.status} label={statusLabel(letter.status)} />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
