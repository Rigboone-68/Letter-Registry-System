import styles from './EmptyState.module.css'

/** Minimal, reusable empty-state primitive (docs/architecture/frontend.md
 * §17), for a future list screen that legitimately has zero rows —
 * distinct from ErrorState, never used to mask a failed request.
 * `.icon` (Phase 5I.3, docs/architecture/ui-design-system.md §19) is a
 * small, `aria-hidden`, CSS-only document/registry motif — decorative
 * only; the message text remains the sole real content. No next-action
 * is invented here — a caller that has a valid one already renders it
 * itself, alongside this component. */
export default function EmptyState({ message = 'Nothing to show yet.' }) {
  return (
    <div className={styles.root}>
      <span className={styles.icon} aria-hidden="true" />
      <p className={styles.message}>{message}</p>
    </div>
  )
}
