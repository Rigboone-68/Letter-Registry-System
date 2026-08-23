import styles from './LoadingState.module.css'

/** Minimal, reusable loading primitive (docs/architecture/frontend.md
 * §17). `role="status"`/`aria-live="polite"` so assistive tech
 * announces the loading state without stealing focus (§25). */
export default function LoadingState({ label = 'Loading...' }) {
  return (
    <div className={styles.root} role="status" aria-live="polite">
      <span className={styles.spinner} aria-hidden="true" />
      <span>{label}</span>
    </div>
  )
}
