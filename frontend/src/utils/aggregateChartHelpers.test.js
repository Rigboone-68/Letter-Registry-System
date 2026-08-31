import { describe, expect, it } from 'vitest'

import {
  departmentBars,
  directionBars,
  formatMonthLabel,
  mergeTrendSeries,
} from './aggregateChartHelpers'

describe('directionBars', () => {
  it('returns Incoming before Outgoing regardless of backend order', () => {
    const bars = directionBars([
      { key: 'OUTGOING', count: 5 },
      { key: 'INCOMING', count: 12 },
    ])

    expect(bars.map((bar) => bar.key)).toEqual(['INCOMING', 'OUTGOING'])
    expect(bars[0]).toMatchObject({ label: 'Incoming / Diary', count: 12 })
    expect(bars[1]).toMatchObject({ label: 'Outgoing / Dispatch', count: 5 })
  })

  it('shows an explicit zero for a direction with no letters, rather than omitting it', () => {
    const bars = directionBars([{ key: 'INCOMING', count: 8 }])

    expect(bars).toEqual([
      { key: 'INCOMING', label: 'Incoming / Diary', count: 8 },
      { key: 'OUTGOING', label: 'Outgoing / Dispatch', count: 0 },
    ])
  })

  it('handles a wholly empty bucket list as all-zero, not a crash', () => {
    expect(directionBars([])).toEqual([
      { key: 'INCOMING', label: 'Incoming / Diary', count: 0 },
      { key: 'OUTGOING', label: 'Outgoing / Dispatch', count: 0 },
    ])
  })
})

describe('departmentBars', () => {
  it('resolves department ids to names, preserving backend order exactly', () => {
    const namesById = new Map([
      ['dept-1', 'Finance'],
      ['dept-2', 'S&IT'],
    ])
    const bars = departmentBars(
      [
        { key: 'dept-2', count: 9 },
        { key: 'dept-1', count: 3 },
      ],
      namesById
    )

    expect(bars).toEqual([
      { key: 'dept-2', label: 'S&IT', count: 9 },
      { key: 'dept-1', label: 'Finance', count: 3 },
    ])
  })

  it('falls back to a labeled placeholder for an unresolved department id', () => {
    const bars = departmentBars([{ key: 'dept-stale', count: 1 }], new Map())

    expect(bars).toEqual([{ key: 'dept-stale', label: 'Unknown department', count: 1 }])
  })
})

describe('formatMonthLabel', () => {
  it('formats a date_trunc month timestamp as a short month and year', () => {
    expect(formatMonthLabel('2026-01-01T00:00:00+00:00')).toMatch(/Jan.*2026/)
  })
})

describe('mergeTrendSeries', () => {
  it('merges two direction-filtered series into one chronologically-ordered series', () => {
    const incoming = [
      { key: '2026-02-01T00:00:00+00:00', count: 4 },
      { key: '2026-01-01T00:00:00+00:00', count: 10 },
    ]
    const outgoing = [{ key: '2026-01-01T00:00:00+00:00', count: 2 }]

    const points = mergeTrendSeries(incoming, outgoing)

    expect(points.map((point) => point.key)).toEqual([
      '2026-01-01T00:00:00+00:00',
      '2026-02-01T00:00:00+00:00',
    ])
    expect(points[0]).toMatchObject({ incoming: 10, outgoing: 2 })
    // February exists only in the incoming series — outgoing defaults
    // to an explicit 0, not a missing point.
    expect(points[1]).toMatchObject({ incoming: 4, outgoing: 0 })
  })

  it('returns an empty series when both inputs are empty', () => {
    expect(mergeTrendSeries([], [])).toEqual([])
  })
})
