import { APP_NAME } from '../constants/app'
import { useAuth } from '../context/AuthContext'
import NotificationBell from '../components/NotificationBell'
import styles from './Topbar.module.css'

/** Current user's display identity, role indicator, notification
 * indicator, and logout control (docs/architecture/frontend.md §14;
 * `NotificationBell` added Phase 5E — renders identically for every
 * role, since no role dependency exists on any notification endpoint,
 * docs/architecture/document-notification-ui.md §13). Logout is
 * centralized — this button calls the one `logout()` in AuthContext,
 * never its own ad hoc token-clearing logic. */
export default function Topbar() {
  const { user, logout } = useAuth()

  return (
    <header className={styles.root}>
      <span className={styles.appName}>{APP_NAME}</span>
      {user && (
        <div className={styles.identity}>
          <NotificationBell />
          <span className={styles.name}>{user.full_name}</span>
          <span className={styles.role}>{user.role.replace('_', ' ')}</span>
          <button type="button" className={styles.logout} onClick={logout}>
            Log out
          </button>
        </div>
      )}
    </header>
  )
}
