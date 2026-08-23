import styles from './EmptyState.module.css'

/** Minimal, reusable empty-state primitive (docs/architecture/frontend.md
 * §17), for a future list screen that legitimately has zero rows —
 * distinct from ErrorState, never used to mask a failed request. */
export default function EmptyState({ message = 'Nothing to show yet.' }) {
  return (
    <div className={styles.root}>
      <p>{message}</p>
    </div>
  )
}
