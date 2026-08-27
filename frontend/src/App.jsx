/**
 * Application shell (Phase 5A). Provides the single authentication
 * state mechanism (AuthContext, docs/architecture/frontend.md §22) to
 * the whole route tree (routes/index.jsx) — no feature screens are
 * mounted here directly; every real screen lives under /app, guarded by
 * ProtectedRoute/RoleGuard.
 *
 * Phase 5I.5 (docs/architecture/ui-design-system.md §29) adds one
 * gate here, using `AuthContext`'s own existing `status === 'loading'`
 * value — never a duplicated timer or a second loading flag: while the
 * very first, genuine session-restoration check is still in flight,
 * `<BootScreen />` renders instead of the router. This is the "inside
 * AuthContext's existing loading state" option the phase brief itself
 * offered, chosen because it is the one point that covers every entry
 * route (`/`, `/login`, `/signup`, `/app/*`) uniformly, without
 * touching `ProtectedRoute`/`RootRedirect`'s own, still-necessary
 * `status === 'loading'` branches (each is exercised directly by its
 * own isolated test, not through this component, and remains a valid
 * defensive fallback). Once `status` leaves `'loading'` for the first
 * and only time, `RouterProvider` mounts and the router takes over for
 * the rest of the session — logout/login never revert `status` back to
 * `'loading'`, so the boot screen is never seen again mid-session.
 */

import { RouterProvider } from 'react-router-dom'

import BootScreen from './components/BootScreen'
import { AuthProvider, useAuth } from './context/AuthContext'
import { router } from './routes'
import styles from './App.module.css'

function AppGate() {
  const { status } = useAuth()

  if (status === 'loading') {
    return <BootScreen />
  }

  return (
    <div className={styles.appEnter}>
      <RouterProvider router={router} />
    </div>
  )
}

export default function App() {
  return (
    <AuthProvider>
      <AppGate />
    </AuthProvider>
  )
}
