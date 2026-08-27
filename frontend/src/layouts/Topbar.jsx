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
 * never its own ad hoc token-clearing logic.
 *
 * Phase 5I.2 (docs/architecture/ui-design-system.md §11) adds the
 * mobile-navigation toggle only — a plain, controlled button whose
 * open/closed state is owned by `AppShell` and mirrored into
 * `Sidebar`; this component makes no navigation or authorization
 * decision of its own. `onToggleMobileNav`/`mobileNavOpen` default to a
 * no-op/`false` so this component still renders correctly on its own
 * (e.g. in isolation in a test) without a parent wiring them up.
 */
export default function Topbar({ onToggleMobileNav = () => {}, mobileNavOpen = false }) {
  const { user, logout } = useAuth()

  return (
    <header className={styles.root}>
      <div className={styles.left}>
        <button
          type="button"
          className={styles.menuToggle}
          onClick={onToggleMobileNav}
          aria-expanded={mobileNavOpen}
          aria-controls="sidebar-nav-list"
          aria-label={mobileNavOpen ? 'Close navigation menu' : 'Open navigation menu'}
        >
          <span aria-hidden="true">{mobileNavOpen ? '✕' : '☰'}</span>
        </button>
        <span className={styles.appName}>{APP_NAME}</span>
      </div>
      {user && (
        <div className={styles.identity}>
          <NotificationBell />
          <span className={styles.divider} aria-hidden="true" />
          <span className={styles.identityText}>
            <span className={styles.name}>{user.full_name}</span>
            <span className={styles.role}>{user.role.replace('_', ' ')}</span>
          </span>
          <button type="button" className={styles.logout} onClick={logout}>
            Log out
          </button>
        </div>
      )}
    </header>
  )
}
