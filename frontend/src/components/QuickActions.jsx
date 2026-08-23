import { Link } from 'react-router-dom'

import styles from './QuickActions.module.css'

/**
 * Role-scoped dashboard shortcuts (Phase 5F,
 * docs/architecture/dashboard.md §17). Every link points at an
 * already-existing route — this component invents no new page, form,
 * or endpoint, and lists only actions the current role can actually
 * perform (matching what each target route's own `RoleGuard`/backend
 * dependency already requires). "View Letters" is deliberately not
 * included for any role — the review marked it PROVISIONAL, and the
 * existing Sidebar link is already one click away, so a duplicate
 * shortcut here would add clutter without adding capability.
 */
const ACTIONS_BY_ROLE = Object.freeze({
  SYSTEM_ADMIN: [
    { label: 'Create Department', path: '/app/system/departments/new' },
    { label: 'Authorize Admin', path: '/app/system/admins/authorize' },
  ],
  ADMIN: [{ label: 'Authorize User', path: '/app/admin/users/authorize' }],
  USER: [{ label: 'Record a Letter', path: '/app/letters/new' }],
})

export default function QuickActions({ role }) {
  const actions = ACTIONS_BY_ROLE[role] ?? []

  if (actions.length === 0) return null

  return (
    <nav className={styles.root} aria-label="Quick actions">
      <ul className={styles.list}>
        {actions.map((action) => (
          <li key={action.path}>
            <Link to={action.path} className={styles.action}>
              {action.label}
            </Link>
          </li>
        ))}
      </ul>
    </nav>
  )
}
