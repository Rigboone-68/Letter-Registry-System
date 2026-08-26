import StatusBadge from './StatusBadge'
import { statusLabel } from '../utils/statusLabels'
import styles from './DataTable.module.css'

/**
 * Designation list table (Phase 5H,
 * docs/architecture/source-designation.md §12) — renders only fields
 * `DesignationResponse` actually returns. Activate/Deactivate are
 * inline per-row actions (mirroring `AuthorizationTable`'s own Revoke
 * pattern) rather than a separate detail page — this resource has no
 * detail page at all, per the review's own "do not overbuild" scope:
 * a single list+create+lifecycle page is the complete SYSTEM_ADMIN
 * surface for Designations. No Delete action exists anywhere —
 * designations are never physically deleted.
 */
export default function DesignationTable({ designations, onActivate, onDeactivate, actingId }) {
  return (
    <div className={styles.scroller}>
      <table className={styles.table}>
        <thead>
          <tr>
            <th scope="col">Name</th>
            <th scope="col">Status</th>
            <th scope="col">Actions</th>
          </tr>
        </thead>
        <tbody>
          {designations.map((designation) => (
            <tr key={designation.id}>
              <th scope="row" className={styles.primaryCell}>
                {designation.name}
              </th>
              <td>
                <StatusBadge
                  value={designation.status}
                  label={statusLabel(designation.status)}
                  domain="Designation"
                />
              </td>
              <td>
                <div className={styles.actionsCell}>
                  {designation.status === 'ACTIVE' ? (
                    <button
                      type="button"
                      onClick={() => onDeactivate(designation)}
                      disabled={actingId === designation.id}
                    >
                      {actingId === designation.id ? 'Deactivating…' : 'Deactivate'}
                    </button>
                  ) : (
                    <button
                      type="button"
                      onClick={() => onActivate(designation)}
                      disabled={actingId === designation.id}
                    >
                      {actingId === designation.id ? 'Activating…' : 'Activate'}
                    </button>
                  )}
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
