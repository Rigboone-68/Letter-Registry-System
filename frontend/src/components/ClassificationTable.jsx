import { Link } from 'react-router-dom'

import StatusBadge from './StatusBadge'
import { statusLabel } from '../utils/statusLabels'
import styles from './DataTable.module.css'

/**
 * Classification list table (Phase 5H.1, mirroring
 * `DepartmentTable.jsx`/`CategoryTable.jsx`). Renders only fields
 * `ClassificationResponse` actually returns — `restricts_access` is
 * shown as plain "Yes"/"No" text (never color-only) so its real,
 * backend-enforced effect on classified-Letter visibility is legible
 * at a glance; this table does not compute or infer that effect
 * itself.
 */
export default function ClassificationTable({ classifications }) {
  return (
    <div className={styles.scroller}>
      <table className={styles.table}>
        <thead>
          <tr>
            <th scope="col">Name</th>
            <th scope="col">Restricts Access</th>
            <th scope="col">Status</th>
          </tr>
        </thead>
        <tbody>
          {classifications.map((classification) => (
            <tr key={classification.id}>
              <th scope="row" className={styles.primaryCell}>
                <Link to={`/app/system/classifications/${classification.id}`}>
                  {classification.name}
                </Link>
              </th>
              <td>{classification.restricts_access ? 'Yes' : 'No'}</td>
              <td>
                <StatusBadge
                  value={classification.status}
                  label={statusLabel(classification.status)}
                  domain="Classification"
                />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
