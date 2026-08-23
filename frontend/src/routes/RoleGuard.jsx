import { Navigate, Outlet } from 'react-router-dom'

import { useAuth } from '../context/AuthContext'

/**
 * Role-based navigation convenience only (docs/architecture/frontend.md
 * §5/§12) — a deliberately separate component from `ProtectedRoute`
 * (which only ever asks "is anyone logged in"). This asks "is the
 * logged-in role one this screen is meant for," and it provides zero
 * actual security: the backend's own role/department checks
 * (`require_system_admin`, `require_admin`, `assert_letter_access`,
 * etc.) are what actually enforce access on every request, regardless
 * of whether this component ran or what it decided. Its only job is
 * to avoid showing a role a confusing dead-end screen.
 *
 * Usable two ways (Phase 5D): `<RoleGuard allowedRoles={[...]}><X/></RoleGuard>`
 * for a single route (the original Phase 5A usage, unchanged), or as a
 * layout route with no `children` — `{ element: <RoleGuard
 * allowedRoles={[...]} />, children: [...] }` — rendering `<Outlet/>`
 * so a whole group of nested routes (e.g. every `/app/system/admins/*`
 * route) shares one guard instance instead of repeating the same wrap
 * on each child (docs/architecture/administration-ui.md §13's own
 * "RoleGuard applied only at the existing top-level route... not
 * re-applied on every child route individually").
 */
export default function RoleGuard({ allowedRoles, children }) {
  const { user } = useAuth()

  if (!user || !allowedRoles.includes(user.role)) {
    return <Navigate to="/app" replace />
  }

  return children ?? <Outlet />
}
