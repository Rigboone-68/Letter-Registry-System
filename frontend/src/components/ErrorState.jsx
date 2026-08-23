import styles from './ErrorState.module.css'

/** Minimal, reusable error primitive (docs/architecture/frontend.md
 * §17/§23). `role="alert"` so assistive tech announces it immediately
 * (§25) — meaningful text is required; this component never renders a
 * bare status code. */
export default function ErrorState({ message = 'Something went wrong.', onRetry }) {
  return (
    <div className={styles.root} role="alert">
      <p className={styles.message}>{message}</p>
      {onRetry && (
        <button type="button" className={styles.retry} onClick={onRetry}>
          Try again
        </button>
      )}
    </div>
  )
}
