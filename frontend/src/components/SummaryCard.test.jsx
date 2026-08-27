import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import SummaryCard from './SummaryCard'

describe('SummaryCard', () => {
  it('renders the label and value', () => {
    render(<SummaryCard label="Total Letters" value={42} loading={false} error={null} />)
    expect(screen.getByText('Total Letters')).toBeInTheDocument()
    expect(screen.getByText('42')).toBeInTheDocument()
  })

  it('shows a placeholder while loading, never a stale or fabricated value', () => {
    render(<SummaryCard label="Total Letters" value={42} loading={true} error={null} />)
    expect(screen.queryByText('42')).not.toBeInTheDocument()
  })

  it('shows an accessible unavailable message on error, never a silent zero', () => {
    render(<SummaryCard label="Total Letters" value={undefined} loading={false} error={{ status: 0 }} />)
    expect(screen.getByRole('alert')).toHaveTextContent(/unavailable/i)
    expect(screen.queryByText('0')).not.toBeInTheDocument()
  })

  it('marks its corner mark as decorative, never replacing the label/value text (Phase 5I.4A)', () => {
    const { container } = render(<SummaryCard label="Total Letters" value={42} loading={false} error={null} />)
    const corner = container.querySelector('[aria-hidden="true"]')
    expect(corner).toBeInTheDocument()
    expect(corner).toHaveTextContent('')
    expect(screen.getByText('Total Letters')).toBeInTheDocument()
    expect(screen.getByText('42')).toBeInTheDocument()
  })
})
