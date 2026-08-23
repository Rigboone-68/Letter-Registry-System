/**
 * Application shell (Phase 5A). Provides the single authentication
 * state mechanism (AuthContext, docs/architecture/frontend.md §22) to
 * the whole route tree (routes/index.jsx) — no feature screens are
 * mounted here directly; every real screen lives under /app, guarded by
 * ProtectedRoute/RoleGuard.
 */

import { RouterProvider } from 'react-router-dom'

import { AuthProvider } from './context/AuthContext'
import { router } from './routes'

export default function App() {
  return (
    <AuthProvider>
      <RouterProvider router={router} />
    </AuthProvider>
  )
}
