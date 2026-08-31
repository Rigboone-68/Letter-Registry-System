/**
 * Pure helpers for turning `letterService.aggregate()` responses
 * (Phase 6C, `GET /letters/aggregate`) into chart-ready shapes for the
 * Dashboard (Phase 6D, docs/architecture/dashboard.md "Phase 6D"
 * section). No React, no Axios — every value here is derived only
 * from a bucket the backend already computed; nothing re-aggregates a
 * count client-side.
 */

import { LETTER_DIRECTION_OPTIONS } from '../services/letterService'

/**
 * Direction buckets in a fixed, deterministic order (Incoming, then
 * Outgoing) rather than whatever order the backend happened to return
 * — a two-category comparison should not flip which bar appears first
 * between page loads. A direction with genuinely zero letters still
 * appears as an explicit zero-value bar (real information); only a
 * wholly empty bucket list means "no data yet" (handled by the caller
 * via the response's own `total`).
 */
export function directionBars(buckets) {
  const countsByKey = Object.fromEntries(buckets.map((bucket) => [bucket.key, bucket.count]))
  return LETTER_DIRECTION_OPTIONS.map((option) => ({
    key: option.value,
    label: option.label,
    count: countsByKey[option.value] ?? 0,
  }))
}

/**
 * Department-id buckets resolved to display names, preserving the
 * backend's own ordering (count descending, key ascending) exactly —
 * never re-sorted client-side. A department id with no matching name
 * (a stale/deleted reference) falls back to a labeled placeholder
 * rather than showing a bare UUID or crashing.
 */
export function departmentBars(buckets, namesById) {
  return buckets.map((bucket) => ({
    key: bucket.key,
    label: namesById.get(bucket.key) ?? 'Unknown department',
    count: bucket.count,
  }))
}

const MONTH_FORMATTER = new Intl.DateTimeFormat(undefined, { month: 'short', year: 'numeric' })

/** `date_trunc('month', ...)` returns an ISO timestamp for the first
 * instant of the month — formatted as "Jan 2026", never the raw ISO
 * string. */
export function formatMonthLabel(isoKey) {
  return MONTH_FORMATTER.format(new Date(isoKey))
}

/**
 * Merges two independently-fetched, direction-filtered time-series
 * responses (`group_by=month&direction=INCOMING` /
 * `...direction=OUTGOING`) into one chronologically-ordered series —
 * the Phase 6C API has no two-dimensional `group_by`, so this is the
 * bounded, two-request way to compare Incoming vs Outgoing over time
 * without a client-side pseudo-aggregation over raw Letters
 * (docs/architecture/dashboard-analytics-api.md §32.9). Each
 * individual response is already chronologically sorted by the
 * backend; only the *union* of their date keys needs ordering here,
 * since one series can have a month bucket the other doesn't.
 */
export function mergeTrendSeries(incomingBuckets, outgoingBuckets) {
  const incomingByKey = new Map(incomingBuckets.map((bucket) => [bucket.key, bucket.count]))
  const outgoingByKey = new Map(outgoingBuckets.map((bucket) => [bucket.key, bucket.count]))
  const keys = Array.from(new Set([...incomingByKey.keys(), ...outgoingByKey.keys()])).sort()

  return keys.map((key) => ({
    key,
    label: formatMonthLabel(key),
    incoming: incomingByKey.get(key) ?? 0,
    outgoing: outgoingByKey.get(key) ?? 0,
  }))
}
