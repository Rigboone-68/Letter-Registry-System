import { Link } from 'react-router-dom'

import StatusBadge from './StatusBadge'
import { statusLabel } from '../utils/statusLabels'
import styles from './DataTable.module.css'

/**
 * Administrators list table (Phase 5D,
 * docs/architecture/administration-ui.md §4.2). Department name is
 * resolved via a lookup map the caller already loaded once from
 * `departmentService.js` — no per-row API call.
 */
export default function AdminTable({ admins, departmentById }) {
  return (
    <div className={styles.scroller}>
      <table className={styles.table}>
        <thead>
          <tr>
            <th scope="col">Name</th>
            <th scope="col">Email</th>
            <th scope="col">Department</th>
            <th scope="col">Status</th>
          </tr>
        </thead>
        <tbody>
          {admins.map((admin) => (
            <tr key={admin.id}>
              <th scope="row" className={styles.primaryCell}>
                <Link to={`/app/system/admins/${admin.id}`}>{admin.full_name}</Link>
              </th>
              <td>{admin.email}</td>
              <td>{departmentById?.[admin.department_id] ?? '—'}</td>
              <td>
                <StatusBadge value={admin.status} label={statusLabel(admin.status)} domain="Admin" />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
