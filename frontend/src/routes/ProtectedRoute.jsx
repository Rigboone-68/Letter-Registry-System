import { Navigate, Outlet, useLocation } from 'react-router-dom'

import LoadingState from '../components/LoadingState'
import { useAuth } from '../context/AuthContext'

/**
 * Authentication guard only (docs/architecture/frontend.md §12) —
 * deliberately does not perform any role authorization; see RoleGuard
 * for that, a separate, composable concern.
 *
 *   status === 'loading'          → LoadingState (avoids an auth
 *                                    flicker while the session restores)
 *   status === 'unauthenticated'  → redirect to /login, remembering
 *                                    where the caller was headed
 *   status === 'authenticated'    → render the protected subtree
 */
export default function ProtectedRoute() {
  const { status } = useAuth()
  const location = useLocation()

  if (status === 'loading') {
    return <LoadingState label="Restoring your session..." />
  }

  if (status === 'unauthenticated') {
    return <Navigate to="/login" replace state={{ from: location }} />
  }

  return <Outlet />
}
