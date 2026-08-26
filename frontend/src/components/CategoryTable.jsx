import { Link } from 'react-router-dom'

import StatusBadge from './StatusBadge'
import { statusLabel } from '../utils/statusLabels'
import styles from './DataTable.module.css'

/**
 * Category list table (Phase 5H.1, mirroring `DepartmentTable.jsx`
 * exactly). Renders only fields `CategoryResponse` actually returns.
 */
export default function CategoryTable({ categories }) {
  return (
    <div className={styles.scroller}>
      <table className={styles.table}>
        <thead>
          <tr>
            <th scope="col">Name</th>
            <th scope="col">Description</th>
            <th scope="col">Status</th>
          </tr>
        </thead>
        <tbody>
          {categories.map((category) => (
            <tr key={category.id}>
              <th scope="row" className={styles.primaryCell}>
                <Link to={`/app/system/categories/${category.id}`}>{category.name}</Link>
              </th>
              <td>{category.description ?? '—'}</td>
              <td>
                <StatusBadge
                  value={category.status}
                  label={statusLabel(category.status)}
                  domain="Category"
                />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
