import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import CorrespondenceTrendChart from './CorrespondenceTrendChart'

const POINTS = [
  { key: '2026-01-01T00:00:00+00:00', label: 'Jan 2026', incoming: 10, outgoing: 2 },
  { key: '2026-02-01T00:00:00+00:00', label: 'Feb 2026', incoming: 4, outgoing: 6 },
]

describe('CorrespondenceTrendChart', () => {
  it('renders loading state', () => {
    render(<CorrespondenceTrendChart points={[]} loading error={null} />)
    expect(screen.getByRole('status')).toBeInTheDocument()
  })

  it('renders error state', () => {
    render(
      <CorrespondenceTrendChart
        points={[]}
        loading={false}
        error={{ message: 'Unable to reach the server.' }}
      />
    )
    expect(screen.getByRole('alert')).toHaveTextContent('Unable to reach the server.')
  })

  it('renders an empty state when there are no points', () => {
    render(
      <CorrespondenceTrendChart
        points={[]}
        loading={false}
        error={null}
        emptyMessage="No correspondence recorded yet."
      />
    )
    expect(screen.getByText('No correspondence recorded yet.')).toBeInTheDocument()
  })

  it('labels both series in a visible, text-based legend', () => {
    render(<CorrespondenceTrendChart points={POINTS} loading={false} error={null} />)

    expect(screen.getByText('Incoming / Diary')).toBeInTheDocument()
    expect(screen.getByText('Outgoing / Dispatch')).toBeInTheDocument()
  })

  it('provides an accessible textual table with the exact monthly counts, in chronological order', () => {
    render(<CorrespondenceTrendChart points={POINTS} loading={false} error={null} />)

    const table = screen.getByRole('table')
    const rows = screen.getAllByRole('row').slice(1) // skip header row
    expect(rows).toHaveLength(2)
    expect(rows[0]).toHaveTextContent('Jan 2026')
    expect(rows[0]).toHaveTextContent('10')
    expect(rows[0]).toHaveTextContent('2')
    expect(rows[1]).toHaveTextContent('Feb 2026')
    expect(table).toBeInTheDocument()
  })

  it('hides the decorative SVG plot from assistive technology', () => {
    const { container } = render(
      <CorrespondenceTrendChart points={POINTS} loading={false} error={null} />
    )
    const plot = container.querySelector('svg.plot, svg[class*="plot"]')
    expect(plot ?? container.querySelector('svg')).toHaveAttribute('aria-hidden', 'true')
  })

  it('does not crash on a single data point', () => {
    render(
      <CorrespondenceTrendChart
        points={[{ key: '2026-01-01T00:00:00+00:00', label: 'Jan 2026', incoming: 3, outgoing: 0 }]}
        loading={false}
        error={null}
      />
    )
    expect(screen.getAllByText('Jan 2026').length).toBeGreaterThan(0)
  })

  it('labels the middle month on the graphic, not just the first and last', () => {
    // Regression test: an earlier version only rendered an axis label
    // for points[0] and points[points.length - 1], which happened to
    // cover every month when there were only ever 1-2 months of real
    // data, but silently hid every month in between once a third
    // appeared.
    const threeMonths = [
      { key: '2026-01-01T00:00:00+00:00', label: 'Jan 2026', incoming: 1, outgoing: 0 },
      { key: '2026-02-01T00:00:00+00:00', label: 'Feb 2026', incoming: 2, outgoing: 1 },
      { key: '2026-03-01T00:00:00+00:00', label: 'Mar 2026', incoming: 3, outgoing: 2 },
    ]
    render(<CorrespondenceTrendChart points={threeMonths} loading={false} error={null} />)

    // "Feb 2026" appears only in the axis label (not the legend, and
    // only once in the always-collapsed table), so a plain query is
    // unambiguous here.
    const axisFeb = screen
      .getAllByText('Feb 2026')
      .find((element) => element.hasAttribute('data-anchor'))
    expect(axisFeb).toBeDefined()
  })

  it('thins axis labels for a long series rather than overlapping every one', () => {
    const twelveMonths = Array.from({ length: 12 }, (_, index) => ({
      key: `2026-${String(index + 1).padStart(2, '0')}-01T00:00:00+00:00`,
      label: `Month ${index + 1}`,
      incoming: index,
      outgoing: 0,
    }))
    const { container } = render(
      <CorrespondenceTrendChart points={twelveMonths} loading={false} error={null} />
    )

    const axisLabels = container.querySelectorAll('[data-anchor]')
    expect(axisLabels.length).toBeLessThan(12)
    expect(axisLabels.length).toBeGreaterThanOrEqual(2)
    // The first and last months are always kept, never thinned away.
    // ("Month 1"/"Month 12" also appear in the always-present table, so
    // read the label text directly off the axis nodes themselves.)
    const axisText = Array.from(axisLabels).map((element) => element.textContent)
    expect(axisText).toContain('Month 1')
    expect(axisText).toContain('Month 12')
  })
})
