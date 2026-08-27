import { useCallback, useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'

import ConfirmDialog from '../components/ConfirmDialog'
import ErrorState from '../components/ErrorState'
import LoadingState from '../components/LoadingState'
import StatusBadge from '../components/StatusBadge'
import * as userService from '../services/userService'
import { statusLabel } from '../utils/statusLabels'
import styles from './AdminPages.module.css'

function formatDateTime(value) {
  if (!value) return '—'
  return new Date(value).toLocaleString(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

/**
 * User detail page (Phase 5D, docs/architecture/administration-ui.md
 * §5.2) — `GET /api/v1/users/{id}`. A `404` here collapses four
 * distinct backend realities identically (nonexistent id, a
 * SYSTEM_ADMIN's id, an Admin's own id, or a User in a *different*
 * department) — rendered as the same generic "not found," never
 * elaborated (§6.4/§18).
 *
 * CRITICAL distinction from the Admin-detail screen, preserved here
 * (§2.6/§5.2 of the review): Approve and Reactivate can fail with a
 * generic `403` for a reason that has nothing to do with this User —
 * the calling Admin's *own* department went inactive. Deactivate can
 * never return this 403 (unconditional server-side) — no pre-emptive
 * department-inactive warning is shown for it.
 */
export default function UserDetailPage() {
  const { id } = useParams()

  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)
  const [notFound, setNotFound] = useState(false)
  const [error, setError] = useState(null)

  const [showApproveDialog, setShowApproveDialog] = useState(false)
  const [showDeactivateDialog, setShowDeactivateDialog] = useState(false)
  const [actionPending, setActionPending] = useState(false)
  const [actionError, setActionError] = useState(null)

  const fetchUser = useCallback(() => {
    setLoading(true)
    setError(null)
    setNotFound(false)
    userService
      .get(id)
      .then((response) => setUser(response))
      .catch((normalizedError) => {
        if (normalizedError.status === 404) {
          setNotFound(true)
        } else {
          setError(normalizedError)
        }
      })
      .finally(() => setLoading(false))
  }, [id])

  useEffect(() => {
    fetchUser()
  }, [fetchUser])

  function describeActionError(normalizedError, fallback) {
    if (normalizedError.status === 403) {
      return 'You do not currently have permission to perform this action — this may be because your department is not active.'
    }
    return normalizedError.message ?? fallback
  }

  async function handleConfirmApprove() {
    setActionPending(true)
    setActionError(null)
    try {
      const updated = await userService.approve(id)
      setUser(updated)
      setShowApproveDialog(false)
    } catch (normalizedError) {
      setActionError(describeActionError(normalizedError, 'Unable to approve this User.'))
    } finally {
      setActionPending(false)
    }
  }

  async function handleConfirmDeactivate() {
    setActionPending(true)
    setActionError(null)
    try {
      const updated = await userService.deactivate(id)
      setUser(updated)
      setShowDeactivateDialog(false)
    } catch (normalizedError) {
      setActionError(normalizedError.message ?? 'Unable to deactivate this User.')
    } finally {
      setActionPending(false)
    }
  }

  async function handleReactivate() {
    setActionPending(true)
    setActionError(null)
    try {
      const updated = await userService.reactivate(id)
      setUser(updated)
    } catch (normalizedError) {
      setActionError(describeActionError(normalizedError, 'Unable to reactivate this User.'))
    } finally {
      setActionPending(false)
    }
  }

  if (loading) return <LoadingState label="Loading user..." />
  if (notFound) return <ErrorState message="User not found." />
  if (error) return <ErrorState message={error.message} onRetry={fetchUser} />
  if (!user) return null

  return (
    <section className={styles.detailCard}>
      <div>
        <Link to="/app/admin/users" className={styles.backLink}>
          ← Back to users
        </Link>
        <p className={styles.eyebrow}>User Management</p>
        <div className={styles.titleRow}>
          <h1>{user.full_name}</h1>
          <StatusBadge value={user.status} label={statusLabel(user.status)} domain="User" />
        </div>
      </div>

      {actionError && <ErrorState message={actionError} />}

      <dl className={styles.grid}>
        <div className={styles.gridField}>
          <dt>Email</dt>
          <dd>{user.email}</dd>
        </div>
        <div className={styles.gridField}>
          <dt>Created</dt>
          <dd>{formatDateTime(user.created_at)}</dd>
        </div>
        <div className={styles.gridField}>
          <dt>Last updated</dt>
          <dd>{formatDateTime(user.updated_at)}</dd>
        </div>
      </dl>

      <div className={styles.actionsPanel}>
        {user.status === 'PENDING_APPROVAL' && (
          <button type="button" className={styles.primary} onClick={() => setShowApproveDialog(true)}>
            Approve
          </button>
        )}
        {user.status === 'ACTIVE' && (
          <button type="button" onClick={() => setShowDeactivateDialog(true)}>
            Deactivate
          </button>
        )}
        {user.status === 'DEACTIVATED' && (
          <button type="button" onClick={handleReactivate} disabled={actionPending}>
            {actionPending ? 'Reactivating…' : 'Reactivate'}
          </button>
        )}
      </div>

      {showApproveDialog && (
        <ConfirmDialog
          title={`Approve ${user.full_name}?`}
          message="This activates the account, giving them User access in your department. This can be reversed later by deactivating the account."
          confirmLabel="Approve User"
          confirmingLabel="Approving…"
          confirming={actionPending}
          onConfirm={handleConfirmApprove}
          onCancel={() => setShowApproveDialog(false)}
        />
      )}

      {showDeactivateDialog && (
        <ConfirmDialog
          title={`Deactivate ${user.full_name}?`}
          message="This immediately removes their access. Their account and history are not removed, and access can be restored later by reactivating."
          confirmLabel="Deactivate User"
          confirmingLabel="Deactivating…"
          tone="caution"
          confirming={actionPending}
          onConfirm={handleConfirmDeactivate}
          onCancel={() => setShowDeactivateDialog(false)}
        />
      )}
    </section>
  )
}
