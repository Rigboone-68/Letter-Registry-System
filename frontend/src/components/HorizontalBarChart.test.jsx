import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import HorizontalBarChart from './HorizontalBarChart'

const BARS = [
  { key: 'dept-1', label: 'Finance', count: 12 },
  { key: 'dept-2', label: 'S&IT', count: 4 },
]

describe('HorizontalBarChart', () => {
  it('renders loading state', () => {
    render(<HorizontalBarChart title="Test chart" bars={[]} loading error={null} />)
    expect(screen.getByRole('status')).toBeInTheDocument()
  })

  it('renders error state without exposing backend detail', () => {
    render(
      <HorizontalBarChart
        title="Test chart"
        bars={[]}
        loading={false}
        error={{ message: 'Unable to reach the server.' }}
      />
    )
    expect(screen.getByRole('alert')).toHaveTextContent('Unable to reach the server.')
  })

  it('renders an empty state with the caller-provided message when there are no bars', () => {
    render(
      <HorizontalBarChart
        title="Test chart"
        bars={[]}
        loading={false}
        error={null}
        emptyMessage="No correspondence recorded yet."
      />
    )
    expect(screen.getByText('No correspondence recorded yet.')).toBeInTheDocument()
  })

  it('renders every bar label and its exact count as real, visible text', () => {
    render(<HorizontalBarChart title="Test chart" bars={BARS} loading={false} error={null} />)

    expect(screen.getByText('Finance')).toBeInTheDocument()
    expect(screen.getByText('12')).toBeInTheDocument()
    expect(screen.getByText('S&IT')).toBeInTheDocument()
    expect(screen.getByText('4')).toBeInTheDocument()
  })

  it('preserves the caller-supplied bar order rather than re-sorting', () => {
    render(<HorizontalBarChart title="Test chart" bars={BARS} loading={false} error={null} />)

    const list = screen.getByRole('list', { name: 'Test chart' })
    const labels = Array.from(list.querySelectorAll('li')).map((row) => row.textContent)
    expect(labels[0]).toContain('Finance')
    expect(labels[1]).toContain('S&IT')
  })

  it('renders the optional description as visible text', () => {
    render(
      <HorizontalBarChart
        title="Test chart"
        description="Which departments are receiving the most correspondence."
        bars={BARS}
        loading={false}
        error={null}
      />
    )
    expect(
      screen.getByText('Which departments are receiving the most correspondence.')
    ).toBeInTheDocument()
  })

  it('does not truncate a long department name', () => {
    const longName = 'Department of Extremely Long Administrative Correspondence and Records'
    render(
      <HorizontalBarChart
        title="Test chart"
        bars={[{ key: 'dept-long', label: longName, count: 1 }]}
        loading={false}
        error={null}
      />
    )
    expect(screen.getByText(longName)).toBeInTheDocument()
  })

  it('hides the decorative fill track from assistive technology', () => {
    const { container } = render(
      <HorizontalBarChart title="Test chart" bars={BARS} loading={false} error={null} />
    )
    const hiddenTracks = container.querySelectorAll('[aria-hidden="true"]')
    expect(hiddenTracks.length).toBeGreaterThan(0)
  })
})
