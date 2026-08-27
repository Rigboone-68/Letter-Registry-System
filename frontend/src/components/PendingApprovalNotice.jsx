import styles from './AccountStateNotice.module.css'

/**
 * Reusable "your account is not approved yet" state (docs/architecture/
 * frontend.md — Phase 5B §8). Shown in two places: right after a
 * successful signup, and after a login attempt against a
 * `PENDING_APPROVAL` account (both surface the same backend fact).
 *
 * Deliberately does not state an approval timeline, promise an email
 * notification, or name an administrator to contact — none of that is
 * something the backend tells the frontend, so none of it is invented
 * here (§8 of the brief).
 *
 * Phase 5I.4E (docs/architecture/ui-design-system.md §28) adds one
 * `aria-hidden` color marker before the heading — purely decorative,
 * the heading text itself remains the actual state signal.
 */
export default function PendingApprovalNotice({ onBackToLogin }) {
  return (
    <div className={styles.notice} role="status">
      <h1>
        <span className={`${styles.marker} ${styles.markerInfo}`} aria-hidden="true" />
        Account pending approval
      </h1>
      <p>
        Your account has been created successfully. It must be approved by an
        administrator before you can sign in.
      </p>
      <button type="button" className={styles.action} onClick={onBackToLogin}>
        Back to sign in
      </button>
    </div>
  )
}
