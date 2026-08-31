import { useState } from 'react'

import { LETTER_DIRECTION_OPTIONS, LETTER_STATUS_OPTIONS } from '../services/letterService'
import styles from './LetterFilters.module.css'

const CORRESPONDENCE_FIELDS = [
  { name: 'reference_number', label: 'Reference number' },
  { name: 'subject', label: 'Subject' },
]

const SENDER_SOURCE_FIELDS = [
  { name: 'sender_name', label: 'Sender name' },
  { name: 'sender_designation', label: 'Sender designation' },
  { name: 'sender_department', label: "Sender's department" },
  { name: 'source_name', label: 'Source name' },
  { name: 'source_location', label: 'Source location' },
]

const EMPTY_DRAFT = {
  reference_number: '',
  subject: '',
  sender_name: '',
  sender_designation: '',
  sender_department: '',
  source_name: '',
  source_location: '',
  status: '',
  direction: '',
  category_id: '',
  classification_id: '',
  department_id: '',
  received_from: '',
  received_to: '',
}

/**
 * The Letter registry filter panel (docs/architecture/frontend.md §11,
 * Phase 5C) — the seven confirmed text filters, the `status` exact
 * filter (available to every role), and an inclusive received-date
 * range, all backed by real `GET /letters` query parameters
 * (`app/api/v1/endpoints/letters.py`) — no invented global search box.
 *
 * `category_id`/`classification_id`/`department_id` are exact filters
 * that need a resolved name list to present as a usable dropdown
 * (a raw UUID text box would be unusable) — `categoryOptions`/
 * `classificationOptions`/`departmentOptions` are only ever supplied by
 * the caller for a SYSTEM_ADMIN viewer, the only role that can load
 * those reference-data endpoints (confirmed — see
 * `services/categoryService.js`/`classificationService.js`/
 * `departmentService.js`); when omitted, that filter is not rendered at
 * all, rather than shown broken.
 *
 * Local draft state only — nothing here triggers a request until Apply
 * is pressed (§9 of the brief: "avoid a request on every keystroke...
 * prefer explicit Apply for V1").
 *
 * Phase 5I.4B (docs/architecture/ui-design-system.md §4) recomposes this
 * into a "Registry Search" console — the same 13 fields, now grouped
 * into labeled `<fieldset>`s, with a purely decorative active-filter
 * count (`activeCount`, computed by the caller from the exact same
 * values this component already receives as `initialValues` — never a
 * new filter, never a second source of truth). Every field's `name`/
 * `id`/label text, the Apply/Clear behavior, and the draft-state model
 * are unchanged.
 */
export default function LetterFilters({
  initialValues,
  onApply,
  onClear,
  categoryOptions,
  classificationOptions,
  departmentOptions,
  activeCount = 0,
}) {
  const [draft, setDraft] = useState({ ...EMPTY_DRAFT, ...initialValues })

  function handleChange(event) {
    const { name, value } = event.target
    setDraft((previous) => ({ ...previous, [name]: value }))
  }

  function handleSubmit(event) {
    event.preventDefault()
    onApply(draft)
  }

  function handleClear() {
    setDraft(EMPTY_DRAFT)
    onClear()
  }

  function renderTextField(field) {
    return (
      <div className={styles.field} key={field.name}>
        <label htmlFor={`filter-${field.name}`}>{field.label}</label>
        <input
          id={`filter-${field.name}`}
          name={field.name}
          type="text"
          value={draft[field.name]}
          onChange={handleChange}
        />
      </div>
    )
  }

  const hasReferenceFilters = Boolean(categoryOptions || classificationOptions || departmentOptions)

  return (
    <form className={styles.root} onSubmit={handleSubmit} aria-label="Filter letters">
      <div className={styles.consoleHeader}>
        <p className={styles.eyebrow}>Registry Search</p>
        {activeCount > 0 && (
          <span className={styles.activeBadge}>
            {activeCount} active {activeCount === 1 ? 'filter' : 'filters'}
          </span>
        )}
      </div>

      <fieldset className={styles.group}>
        <legend>Correspondence</legend>
        <div className={styles.grid}>
          {CORRESPONDENCE_FIELDS.map(renderTextField)}
          <div className={styles.field}>
            <label htmlFor="filter-status">Status</label>
            <select id="filter-status" name="status" value={draft.status} onChange={handleChange}>
              <option value="">Any</option>
              {LETTER_STATUS_OPTIONS.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </div>
          <div className={styles.field}>
            <label htmlFor="filter-direction">Direction</label>
            <select id="filter-direction" name="direction" value={draft.direction} onChange={handleChange}>
              <option value="">Any</option>
              {LETTER_DIRECTION_OPTIONS.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </div>
        </div>
      </fieldset>

      <fieldset className={styles.group}>
        <legend>Sender &amp; source</legend>
        <div className={styles.grid}>{SENDER_SOURCE_FIELDS.map(renderTextField)}</div>
      </fieldset>

      {hasReferenceFilters && (
        <fieldset className={styles.group}>
          <legend>Classification</legend>
          <div className={styles.grid}>
            {categoryOptions && (
              <div className={styles.field}>
                <label htmlFor="filter-category">Category</label>
                <select
                  id="filter-category"
                  name="category_id"
                  value={draft.category_id}
                  onChange={handleChange}
                >
                  <option value="">Any</option>
                  {categoryOptions.map((option) => (
                    <option key={option.id} value={option.id}>
                      {option.name}
                      {option.status === 'INACTIVE' ? ' (inactive)' : ''}
                    </option>
                  ))}
                </select>
              </div>
            )}

            {classificationOptions && (
              <div className={styles.field}>
                <label htmlFor="filter-classification">Classification</label>
                <select
                  id="filter-classification"
                  name="classification_id"
                  value={draft.classification_id}
                  onChange={handleChange}
                >
                  <option value="">Any</option>
                  {classificationOptions.map((option) => (
                    <option key={option.id} value={option.id}>
                      {option.name}
                      {option.status === 'INACTIVE' ? ' (inactive)' : ''}
                    </option>
                  ))}
                </select>
              </div>
            )}

            {departmentOptions && (
              <div className={styles.field}>
                <label htmlFor="filter-department">Department</label>
                <select
                  id="filter-department"
                  name="department_id"
                  value={draft.department_id}
                  onChange={handleChange}
                >
                  <option value="">All departments</option>
                  {departmentOptions.map((option) => (
                    <option key={option.id} value={option.id}>
                      {option.name}
                      {option.status === 'INACTIVE' ? ' (inactive)' : ''}
                    </option>
                  ))}
                </select>
              </div>
            )}
          </div>
        </fieldset>
      )}

      <fieldset className={styles.group}>
        <legend>Received date range</legend>
        <div className={styles.grid}>
          <div className={styles.field}>
            <label htmlFor="filter-received-from">Received from</label>
            <input
              id="filter-received-from"
              name="received_from"
              type="date"
              value={draft.received_from}
              onChange={handleChange}
            />
          </div>

          <div className={styles.field}>
            <label htmlFor="filter-received-to">Received to</label>
            <input
              id="filter-received-to"
              name="received_to"
              type="date"
              value={draft.received_to}
              onChange={handleChange}
            />
          </div>
        </div>
      </fieldset>

      <div className={styles.actions}>
        <button type="submit" className={styles.apply}>
          Apply filters
        </button>
        <button type="button" className={styles.clear} onClick={handleClear}>
          Clear filters
        </button>
      </div>
    </form>
  )
}
