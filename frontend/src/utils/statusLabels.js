/**
 * Human-readable labels for the raw enum values this app renders via
 * `StatusBadge` (Phase 5D, docs/architecture/administration-ui.md §19)
 * — one small shared map rather than repeating the same
 * value→label pairs in every table/detail page. Never used to decide
 * behavior, only display text; `StatusBadge` itself still keys its
 * visual tone off the raw value.
 */
const STATUS_LABELS = {
  ACTIVE: 'Active',
  INACTIVE: 'Inactive',
  ARCHIVED: 'Archived',
  PENDING_APPROVAL: 'Pending Approval',
  DEACTIVATED: 'Deactivated',
  USED: 'Used',
  REVOKED: 'Revoked',
}

export function statusLabel(value) {
  return STATUS_LABELS[value] ?? value
}
