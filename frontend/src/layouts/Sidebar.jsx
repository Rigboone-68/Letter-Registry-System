import { NavLink } from 'react-router-dom'

import { useAuth } from '../context/AuthContext'
import { getNavigationForRole } from '../navigation/navigationConfig'
import styles from './Sidebar.module.css'

/** Navigation is derived entirely from the authenticated user's role
 * (docs/architecture/frontend.md §13/§19) — never a hardcoded list, and
 * never department-specific (department scoping is server-derived, not
 * a navigation concern). */
export default function Sidebar() {
  const { user } = useAuth()
  const items = getNavigationForRole(user?.role)

  return (
    <nav className={styles.root} aria-label="Main navigation">
      <ul className={styles.list}>
        {items.map((item) => (
          <li key={item.path}>
            <NavLink
              to={item.path}
              className={({ isActive }) =>
                isActive ? `${styles.link} ${styles.linkActive}` : styles.link
              }
            >
              {item.label}
            </NavLink>
          </li>
        ))}
      </ul>
    </nav>
  )
}
