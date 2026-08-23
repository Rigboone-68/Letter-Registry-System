import StatusBadge from './StatusBadge'
import { statusLabel } from '../utils/statusLabels'
import styles from './DataTable.module.css'

function formatDate(value) {
  if (!value) return '—'
  return new Date(value).toLocaleDateString(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  })
}

/**
 * User-purpose authorization list table (Phase 5D,
 * docs/architecture/administration-ui.md §5.3/§5.4) — a
 * `UserAuthorization` row, not a `User` row: department-wide visibility
 * (every authorization in the Admin's department, not just ones they
 * created), but Revoke is creator-scoped server-side
 * (`DELETE /users/authorizations/{id}` 404s for a row the calling Admin
 * didn't create). The Revoke button is shown on every `ACTIVE` row
 * regardless — `UserAuthorizationResponse` has no `authorized_by` field
 * to pre-filter on, so hiding it for rows the Admin didn't create isn't
 * possible without guessing; a mismatched attempt 404s like any other,
 * rendered generically (§5.4 — never a distinguishing "not yours"
 * message that would leak who created what).
 */
export default function AuthorizationTable({ authorizations, onRevoke, revokingId }) {
  return (
    <div className={styles.scroller}>
      <table className={styles.table}>
        <thead>
          <tr>
            <th scope="col">Email</th>
            <th scope="col">Status</th>
            <th scope="col">Created</th>
            {onRevoke && <th scope="col">Actions</th>}
          </tr>
        </thead>
        <tbody>
          {authorizations.map((authorization) => (
            <tr key={authorization.id}>
              <th scope="row" className={styles.primaryCell}>
                {authorization.email}
              </th>
              <td>
                <StatusBadge
                  value={authorization.status}
                  label={statusLabel(authorization.status)}
                  domain="Authorization"
                />
              </td>
              <td>{formatDate(authorization.created_at)}</td>
              {onRevoke && (
                <td>
                  {authorization.status === 'ACTIVE' && (
                    <div className={styles.actionsCell}>
                      <button
                        type="button"
                        onClick={() => onRevoke(authorization)}
                        disabled={revokingId === authorization.id}
                      >
                        {revokingId === authorization.id ? 'Revoking…' : 'Revoke'}
                      </button>
                    </div>
                  )}
                </td>
              )}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
