import styles from './AccountStateNotice.module.css'

/**
 * Reusable "this account is deactivated" state (docs/architecture/
 * frontend.md — Phase 5B §9). Only ever shown as the direct result of a
 * login attempt: the backend's distinct "Your account has been
 * deactivated." message is raised solely by `POST /auth/login`
 * (`auth_service.py`) — a deactivation that happens mid-session is
 * instead surfaced as a generic 401 on the next API call (handled by
 * apiClient's existing centralized 401 handler), because
 * `get_current_user` does not distinguish "deactivated" from any other
 * reason a token is no longer valid. So there is no "logged in, then
 * discovered deactivated" state for this component to represent, and no
 * logout action for it to offer.
 *
 * Deliberately does not imply the account was deleted, and does not
 * expose any administrative detail (who deactivated it, when, or why) —
 * none of that is available to the frontend (§9 of the brief).
 */
export default function DeactivatedAccountNotice({ onBackToLogin }) {
  return (
    <div className={styles.notice} role="status">
      <h1>Account deactivated</h1>
      <p>
        Access to this account has been disabled. Your account record has not
        been deleted.
      </p>
      <button type="button" className={styles.action} onClick={onBackToLogin}>
        Back to sign in
      </button>
    </div>
  )
}
