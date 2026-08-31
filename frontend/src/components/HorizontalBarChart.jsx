import EmptyState from './EmptyState'
import ErrorState from './ErrorState'
import LoadingState from './LoadingState'
import styles from './HorizontalBarChart.module.css'

/**
 * A calm, restrained horizontal bar comparison (Phase 6D,
 * docs/architecture/dashboard.md "Phase 6D" section) — reused for
 * every bar-shaped dashboard chart (Incoming vs Outgoing, Letters
 * Received by Department, Letters Sent by Department) rather than one
 * bespoke chart per metric, since none of them differs in shape, only
 * in which bars and label it carries.
 *
 * Deliberately plain CSS `<div>` bars, not SVG or a charting library —
 * every label and count is real, always-visible HTML text (never a
 * tooltip-only value), so no separate "accessible text equivalent" has
 * to be built alongside the visual: the visual *is* the accessible
 * text, with a decorative fill bar layered next to it. A horizontal
 * layout also means a long department name never gets truncated or
 * crowded — it grows the row's height, never the page's width.
 */
export default function HorizontalBarChart({ title, description, bars, loading, error, emptyMessage }) {
  if (loading) return <LoadingState label={`Loading ${title}...`} />
  if (error) return <ErrorState message={error.message} />
  if (!bars || bars.length === 0) return <EmptyState message={emptyMessage} />

  const maxCount = Math.max(...bars.map((bar) => bar.count), 1)

  return (
    <div className={styles.root}>
      {description && <p className={styles.description}>{description}</p>}
      <ul className={styles.list} aria-label={title}>
        {bars.map((bar) => (
          <li key={bar.key} className={styles.row}>
            <span className={styles.label}>{bar.label}</span>
            <span className={styles.track} aria-hidden="true">
              <span className={styles.fill} style={{ width: `${(bar.count / maxCount) * 100}%` }} />
            </span>
            <span className={styles.value}>{bar.count}</span>
          </li>
        ))}
      </ul>
    </div>
  )
}
