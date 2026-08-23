import { Navigate } from 'react-router-dom'

import LoadingState from '../components/LoadingState'
import { useAuth } from '../context/AuthContext'

/** `/` has no content of its own — this is an internal operational
 * tool, not a marketing site (docs/architecture/frontend.md §24). It
 * only ever decides where to send the caller once the session-restore
 * decision (§9) has actually completed. */
export default function RootRedirect() {
  const { status } = useAuth()

  if (status === 'loading') {
    return <LoadingState />
  }

  return <Navigate to={status === 'authenticated' ? '/app' : '/login'} replace />
}
