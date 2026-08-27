import styles from './SummaryCard.module.css'

/**
 * A single operational-count card (Phase 5F,
 * docs/architecture/dashboard.md §14). Deliberately minimal — a label
 * and a value, nothing else — reused across every dashboard summary
 * figure (Letters, Departments, Admins, Users, Notifications) rather
 * than one bespoke card per metric, since none of them differs in
 * shape, only in the number and label they carry.
 *
 * `loading`/`error` are per-card so a widget's own failed request never
 * has to hide every other card on the page (docs/architecture/
 * dashboard.md §20) — the caller decides what counts as one widget
 * (e.g. Total/Active/Archived Letters share one fetch and therefore one
 * loading/error state, passed to all three cards at once).
 *
 * `.corner` (Phase 5I.4A, docs/architecture/ui-design-system.md) is a
 * small `aria-hidden` corner-bracket mark — purely decorative, never a
 * replacement for the real label/value text.
 */
export default function SummaryCard({ label, value, loading, error }) {
  return (
    <div className={styles.root}>
      <span className={styles.corner} aria-hidden="true" />
      <p className={styles.label}>{label}</p>
      {loading && <p className={styles.value}>—</p>}
      {!loading && error && (
        <p className={styles.error} role="alert">
          Unavailable
        </p>
      )}
      {!loading && !error && <p className={styles.value}>{value}</p>}
    </div>
  )
}
