/**
 * Role-to-navigation mapping (docs/architecture/frontend.md §5-§8, §19).
 *
 * Configuration only — every path below resolves to a placeholder route
 * this phase also wires up (routes/index.jsx), never a feature page.
 * Navigation is convenience, not security (§5): hiding an item here
 * does not and cannot substitute for the backend's own authorization,
 * which runs on every request regardless of what this file lists.
 *
 * "Documents" has no standalone feature route in the architecture
 * review's own recommended design (it's always reached from within a
 * Letter's detail page) — it is still listed here per explicit
 * instruction, pointing at a placeholder that says so, rather than
 * silently dropping it or silently building a page the review didn't
 * recommend.
 *
 * No department id appears anywhere in this file — department scoping
 * is entirely server-derived (docs/architecture/frontend.md §13); there
 * is nothing here for a route to parameterize on.
 *
 * "Dashboard" (Phase 5F, docs/architecture/dashboard.md §4) is the one
 * entry every role gets first — a single real page, not a placeholder,
 * that renders role-appropriate content itself rather than needing a
 * separate nav entry per role's own dashboard variant.
 */

export const NAVIGATION_BY_ROLE = Object.freeze({
  SYSTEM_ADMIN: [
    { label: 'Dashboard', path: '/app/dashboard' },
    { label: 'Letters', path: '/app/system/letters' },
    { label: 'Documents', path: '/app/documents' },
    { label: 'Notifications', path: '/app/notifications' },
    { label: 'Departments', path: '/app/system/departments' },
    { label: 'Administrators', path: '/app/system/admins' },
    { label: 'Designations', path: '/app/system/designations' },
    { label: 'Categories', path: '/app/system/categories' },
    { label: 'Classifications', path: '/app/system/classifications' },
  ],
  ADMIN: [
    { label: 'Dashboard', path: '/app/dashboard' },
    { label: 'Letters', path: '/app/letters' },
    { label: 'Documents', path: '/app/documents' },
    { label: 'Notifications', path: '/app/notifications' },
    { label: 'Users', path: '/app/admin/users' },
  ],
  USER: [
    { label: 'Dashboard', path: '/app/dashboard' },
    { label: 'Letters', path: '/app/letters' },
    { label: 'Documents', path: '/app/documents' },
    { label: 'Notifications', path: '/app/notifications' },
  ],
})

export function getNavigationForRole(role) {
  return NAVIGATION_BY_ROLE[role] ?? []
}
