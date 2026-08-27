import { useState } from 'react'
import { Outlet } from 'react-router-dom'

import { PRODUCTION_CREDIT } from '../constants/app'
import Sidebar from './Sidebar'
import Topbar from './Topbar'
import styles from './AppShell.module.css'

/**
 * AppShell → Sidebar / Topbar / MainContent (docs/architecture/frontend.md
 * §14/§20). Mounted once, inside `ProtectedRoute` (so `useAuth()` is
 * always guaranteed a non-loading, authenticated user by the time this
 * renders) — every feature screen renders inside `<Outlet />` here, not
 * a per-page copy of this chrome.
 *
 * Phase 5I.2 (docs/architecture/ui-design-system.md §6/§11/§15) adds
 * two things at the shell level only:
 *  - `mobileNavOpen` — the one piece of state `Topbar`'s hamburger
 *    button and `Sidebar`'s drawer both need to share; owned here since
 *    neither component is an ancestor of the other. `Sidebar` itself
 *    closes it again once a route is actually selected (its own
 *    `location.pathname` effect) — this component does not duplicate
 *    that logic.
 *  - a footer rendering the existing `PRODUCTION_CREDIT` constant —
 *    present on every authenticated screen, since this component is
 *    the one place that renders unconditionally regardless of role or
 *    route.
 */
export default function AppShell() {
  const [mobileNavOpen, setMobileNavOpen] = useState(false)

  return (
    <div className={styles.root}>
      <Sidebar mobileOpen={mobileNavOpen} onCloseMobile={() => setMobileNavOpen(false)} />
      <div className={styles.main}>
        <Topbar
          mobileNavOpen={mobileNavOpen}
          onToggleMobileNav={() => setMobileNavOpen((previous) => !previous)}
        />
        <main className={styles.content}>
          <div className={styles.contentInner}>
            <Outlet />
          </div>
        </main>
        <footer className={styles.footer}>{PRODUCTION_CREDIT}</footer>
      </div>
    </div>
  )
}
