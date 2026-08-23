import { Link } from 'react-router-dom'

import StatusBadge from './StatusBadge'
import { statusLabel } from '../utils/statusLabels'
import styles from './DataTable.module.css'

/**
 * Department list table (Phase 5D,
 * docs/architecture/administration-ui.md §4.1). Renders only fields
 * `DepartmentResponse` actually returns — no admin/user count column,
 * since no such field exists on the backend response (§7/§22, marked
 * PENDING BACKEND API, not calculated client-side).
 */
export default function DepartmentTable({ departments }) {
  return (
    <div className={styles.scroller}>
      <table className={styles.table}>
        <thead>
          <tr>
            <th scope="col">Name</th>
            <th scope="col">Code</th>
            <th scope="col">Status</th>
          </tr>
        </thead>
        <tbody>
          {departments.map((department) => (
            <tr key={department.id}>
              <th scope="row" className={styles.primaryCell}>
                <Link to={`/app/system/departments/${department.id}`}>{department.name}</Link>
              </th>
              <td>{department.code ?? '—'}</td>
              <td>
                <StatusBadge
                  value={department.status}
                  label={statusLabel(department.status)}
                  domain="Department"
                />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
