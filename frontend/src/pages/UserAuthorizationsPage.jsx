import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'

import AuthorizationTable from '../components/AuthorizationTable'
import ConfirmDialog from '../components/ConfirmDialog'
import EmptyState from '../components/EmptyState'
import ErrorState from '../components/ErrorState'
import LoadingState from '../components/LoadingState'
import * as userService from '../services/userService'
import styles from './AdminPages.module.css'

/**
 * User-purpose authorization list page (Phase 5D,
 * docs/architecture/administration-ui.md §5.3/§5.4) —
 * `GET /api/v1/users/authorizations`, department-wide (every
 * authorization any Admin in this department created, not just this
 * caller's own) — a separate resource from the Users list itself: this
 * renders `UserAuthorization` rows (candidates who may not have signed
 * up yet), not `User` rows.
 *
 * Defaults to `status=ACTIVE` (PROVISIONAL, per the review — the
 * operationally relevant subset) with an explicit control to widen to
 * "All."
 */
export default function UserAuthorizationsPage() {
  const [status, setStatus] = useState('ACTIVE')
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const [revokeTarget, setRevokeTarget] = useState(null)
  const [revoking, setRevoking] = useState(false)
  const [revokeError, setRevokeError] = useState(null)

  const fetchAuthorizations = useCallback(() => {
    setLoading(true)
    setError(null)
    const params = status ? { status } : {}
    userService
      .listAuthorizations(params)
      .then((response) => setData(response))
      .catch((normalizedError) => setError(normalizedError))
      .finally(() => setLoading(false))
  }, [status])

  useEffect(() => {
    fetchAuthorizations()
  }, [fetchAuthorizations])

  async function handleConfirmRevoke() {
    setRevoking(true)
    setRevokeError(null)
    try {
      const updated = await userService.revokeAuthorization(revokeTarget.id)
      setData((previous) => ({
        ...previous,
        items: previous.items.map((item) => (item.id === updated.id ? updated : item)),
      }))
      setRevokeTarget(null)
    } catch (normalizedError) {
      setRevokeError(normalizedError.message ?? 'Unable to revoke this authorization.')
    } finally {
      setRevoking(false)
    }
  }

  return (
    <section className={styles.root}>
      <div className={styles.header}>
        <div className={styles.headerText}>
          <p className={styles.eyebrow}>Authorization Management</p>
          <div className={styles.titleRow}>
            <h1>User Authorizations</h1>
            <span className={styles.headerMark} aria-hidden="true" />
          </div>
          {data && <p className={styles.count}>{data.total} total</p>}
        </div>
        <div className={styles.headerActions}>
          <button type="button" onClick={fetchAuthorizations}>
            Refresh
          </button>
          <Link to="/app/admin/users">Back to Users</Link>
        </div>
      </div>

      <div className={styles.filters}>
        <div className={styles.field}>
          <label htmlFor="authorization-status-filter">Status</label>
          <select
            id="authorization-status-filter"
            value={status}
            onChange={(event) => setStatus(event.target.value)}
          >
            <option value="ACTIVE">Active</option>
            <option value="">All</option>
            <option value="USED">Used</option>
            <option value="REVOKED">Revoked</option>
          </select>
        </div>
      </div>

      {revokeError && <ErrorState message={revokeError} />}

      {loading && <LoadingState label="Loading authorizations..." />}
      {!loading && error && <ErrorState message={error.message} onRetry={fetchAuthorizations} />}
      {!loading && !error && data && data.items.length === 0 && (
        <EmptyState message="No authorizations match the current filter." />
      )}
      {!loading && !error && data && data.items.length > 0 && (
        <AuthorizationTable
          authorizations={data.items}
          onRevoke={(authorization) => setRevokeTarget(authorization)}
          revokingId={revoking ? revokeTarget?.id : null}
        />
      )}

      {revokeTarget && (
        <ConfirmDialog
          title={`Revoke authorization for ${revokeTarget.email}?`}
          message="This cannot be undone. The candidate will need a new authorization to sign up. If you did not create this authorization, this action may not be permitted."
          confirmLabel="Revoke Authorization"
          confirmingLabel="Revoking…"
          tone="caution"
          confirming={revoking}
          onConfirm={handleConfirmRevoke}
          onCancel={() => setRevokeTarget(null)}
        />
      )}
    </section>
  )
}
