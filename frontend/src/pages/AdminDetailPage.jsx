import { useCallback, useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'

import AdminTransferDialog from '../components/AdminTransferDialog'
import ConfirmDialog from '../components/ConfirmDialog'
import ErrorState from '../components/ErrorState'
import LoadingState from '../components/LoadingState'
import StatusBadge from '../components/StatusBadge'
import * as adminService from '../services/adminService'
import * as departmentService from '../services/departmentService'
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
 * Admin detail page (Phase 5D,
 * docs/architecture/administration-ui.md §4.2) — `GET /api/v1/admins/{id}`.
 * A `404` here (whether the id doesn't exist, or resolves to a non-Admin
 * — including a SYSTEM_ADMIN's own id, which cannot happen via this
 * screen's own links but could via a manually-typed URL) renders the
 * identical generic "not found," never a distinguishing message (§4.2/
 * §6.4/§18 — the same discipline Phase 5C's classified-Letter 404
 * handling already established, extended here).
 *
 * Actions shown depend entirely on current status (§8.3): Approve
 * (PENDING_APPROVAL, confirmed — not idempotent, a 409 on a double-click
 * is avoidable), Deactivate (ACTIVE, confirmed — real operational
 * impact) + Transfer (ACTIVE only), Reactivate (DEACTIVATED, not
 * confirmed — purely restorative).
 */
export default function AdminDetailPage() {
  const { id } = useParams()

  const [admin, setAdmin] = useState(null)
  const [loading, setLoading] = useState(true)
  const [notFound, setNotFound] = useState(false)
  const [error, setError] = useState(null)

  const [departments, setDepartments] = useState(null)

  const [showApproveDialog, setShowApproveDialog] = useState(false)
  const [showDeactivateDialog, setShowDeactivateDialog] = useState(false)
  const [showTransferDialog, setShowTransferDialog] = useState(false)
  const [actionPending, setActionPending] = useState(false)
  const [actionError, setActionError] = useState(null)
  const [transferError, setTransferError] = useState(null)

  const fetchAdmin = useCallback(() => {
    setLoading(true)
    setError(null)
    setNotFound(false)
    adminService
      .get(id)
      .then((response) => setAdmin(response))
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
    fetchAdmin()
  }, [fetchAdmin])

  useEffect(() => {
    departmentService
      .list()
      .then((response) => setDepartments(response.items))
      .catch(() => {
        // Department name resolution / transfer options are a
        // convenience — a failure here degrades gracefully (department
        // shown as "—", Transfer unavailable) rather than blocking the
        // rest of the page.
      })
  }, [])

  async function handleConfirmApprove() {
    setActionPending(true)
    setActionError(null)
    try {
      const updated = await adminService.approve(id)
      setAdmin(updated)
      setShowApproveDialog(false)
    } catch (normalizedError) {
      setActionError(normalizedError.message ?? 'Unable to approve this Admin.')
    } finally {
      setActionPending(false)
    }
  }

  async function handleConfirmDeactivate() {
    setActionPending(true)
    setActionError(null)
    try {
      const updated = await adminService.deactivate(id)
      setAdmin(updated)
      setShowDeactivateDialog(false)
    } catch (normalizedError) {
      setActionError(normalizedError.message ?? 'Unable to deactivate this Admin.')
    } finally {
      setActionPending(false)
    }
  }

  async function handleReactivate() {
    setActionPending(true)
    setActionError(null)
    try {
      const updated = await adminService.reactivate(id)
      setAdmin(updated)
    } catch (normalizedError) {
      setActionError(normalizedError.message ?? 'Unable to reactivate this Admin.')
    } finally {
      setActionPending(false)
    }
  }

  async function handleConfirmTransfer(departmentId) {
    setActionPending(true)
    setTransferError(null)
    try {
      const updated = await adminService.changeDepartment(id, { department_id: departmentId })
      setAdmin(updated)
      setShowTransferDialog(false)
    } catch (normalizedError) {
      setTransferError(normalizedError.message ?? 'Unable to transfer this Admin.')
    } finally {
      setActionPending(false)
    }
  }

  if (loading) return <LoadingState label="Loading administrator..." />
  if (notFound) return <ErrorState message="Admin not found." />
  if (error) return <ErrorState message={error.message} onRetry={fetchAdmin} />
  if (!admin) return null

  const departmentName = departments?.find((department) => department.id === admin.department_id)?.name

  return (
    <section className={styles.detailCard}>
      <div>
        <Link to="/app/system/admins" className={styles.backLink}>
          ← Back to administrators
        </Link>
        <p className={styles.eyebrow}>Administrator Management</p>
        <div className={styles.titleRow}>
          <h1>{admin.full_name}</h1>
          <StatusBadge value={admin.status} label={statusLabel(admin.status)} domain="Admin" />
        </div>
      </div>

      {actionError && <ErrorState message={actionError} />}

      <dl className={styles.grid}>
        <div className={styles.gridField}>
          <dt>Email</dt>
          <dd>{admin.email}</dd>
        </div>
        <div className={styles.gridField}>
          <dt>Department</dt>
          <dd>{departmentName ?? '—'}</dd>
        </div>
        <div className={styles.gridField}>
          <dt>Created</dt>
          <dd>{formatDateTime(admin.created_at)}</dd>
        </div>
        <div className={styles.gridField}>
          <dt>Last updated</dt>
          <dd>{formatDateTime(admin.updated_at)}</dd>
        </div>
      </dl>

      <div className={styles.actionsPanel}>
        {admin.status === 'PENDING_APPROVAL' && (
          <button type="button" className={styles.primary} onClick={() => setShowApproveDialog(true)}>
            Approve
          </button>
        )}
        {admin.status === 'ACTIVE' && (
          <>
            <button type="button" onClick={() => setShowDeactivateDialog(true)}>
              Deactivate
            </button>
            {departments && (
              <button type="button" onClick={() => setShowTransferDialog(true)}>
                Transfer department
              </button>
            )}
          </>
        )}
        {admin.status === 'DEACTIVATED' && (
          <button type="button" onClick={handleReactivate} disabled={actionPending}>
            {actionPending ? 'Reactivating…' : 'Reactivate'}
          </button>
        )}
      </div>

      {showApproveDialog && (
        <ConfirmDialog
          title={`Approve ${admin.full_name}?`}
          message="This activates the account, giving them Admin access in their department. This can be reversed later by deactivating the account."
          confirmLabel="Approve Admin"
          confirmingLabel="Approving…"
          confirming={actionPending}
          onConfirm={handleConfirmApprove}
          onCancel={() => setShowApproveDialog(false)}
        />
      )}

      {showDeactivateDialog && (
        <ConfirmDialog
          title={`Deactivate ${admin.full_name}?`}
          message="This immediately removes their Admin access. Their account and history are not removed, and access can be restored later by reactivating."
          confirmLabel="Deactivate Admin"
          confirmingLabel="Deactivating…"
          tone="caution"
          confirming={actionPending}
          onConfirm={handleConfirmDeactivate}
          onCancel={() => setShowDeactivateDialog(false)}
        />
      )}

      {showTransferDialog && departments && (
        <AdminTransferDialog
          currentDepartmentName={departmentName}
          departments={departments}
          confirming={actionPending}
          error={transferError}
          onConfirm={handleConfirmTransfer}
          onCancel={() => setShowTransferDialog(false)}
        />
      )}
    </section>
  )
}
