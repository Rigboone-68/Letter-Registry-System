import { Link } from 'react-router-dom'

import StatusBadge from './StatusBadge'
import { statusLabel } from '../utils/statusLabels'
import styles from './DataTable.module.css'

/**
 * Users list table (Phase 5D, docs/architecture/administration-ui.md
 * §5.1) — no department column: every row is, by construction, the
 * viewing Admin's own department (`GET /users` is always
 * department-scoped server-side); showing it would be redundant.
 */
export default function UserTable({ users }) {
  return (
    <div className={styles.scroller}>
      <table className={styles.table}>
        <thead>
          <tr>
            <th scope="col">Name</th>
            <th scope="col">Email</th>
            <th scope="col">Status</th>
          </tr>
        </thead>
        <tbody>
          {users.map((user) => (
            <tr key={user.id}>
              <th scope="row" className={styles.primaryCell}>
                <Link to={`/app/admin/users/${user.id}`}>{user.full_name}</Link>
              </th>
              <td>{user.email}</td>
              <td>
                <StatusBadge value={user.status} label={statusLabel(user.status)} domain="User" />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
