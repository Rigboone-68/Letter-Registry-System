import { Outlet } from 'react-router-dom'

import Sidebar from './Sidebar'
import Topbar from './Topbar'
import styles from './AppShell.module.css'

/**
 * AppShell → Sidebar / Topbar / MainContent (docs/architecture/frontend.md
 * §14/§20). Mounted once, inside `ProtectedRoute` (so `useAuth()` is
 * always guaranteed a non-loading, authenticated user by the time this
 * renders) — every feature screen renders inside `<Outlet />` here, not
 * a per-page copy of this chrome.
 */
export default function AppShell() {
  return (
    <div className={styles.root}>
      <Sidebar />
      <div className={styles.main}>
        <Topbar />
        <main className={styles.content}>
          <Outlet />
        </main>
      </div>
    </div>
  )
}
