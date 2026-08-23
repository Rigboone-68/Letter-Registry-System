import { Navigate } from 'react-router-dom'

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
 */
export default function RoleGuard({ allowedRoles, children }) {
  const { user } = useAuth()

  if (!user || !allowedRoles.includes(user.role)) {
    return <Navigate to="/app" replace />
  }

  return children
}
