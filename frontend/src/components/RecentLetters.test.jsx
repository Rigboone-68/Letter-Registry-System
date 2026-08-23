import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it } from 'vitest'

import RecentLetters from './RecentLetters'

const LETTERS = [
  {
    id: 'l1',
    reference_number: 'REF-001',
    subject: 'Budget approval',
    status: 'ACTIVE',
    received_at: '2026-01-05T09:00:00Z',
  },
  {
    id: 'l2',
    reference_number: 'REF-002',
    subject: 'Policy update',
    status: 'ARCHIVED',
    received_at: '2026-01-03T09:00:00Z',
  },
]

function renderWithRouter(ui) {
  return render(<MemoryRouter>{ui}</MemoryRouter>)
}

describe('RecentLetters', () => {
  it('shows a loading state', () => {
    renderWithRouter(<RecentLetters letters={[]} loading={true} error={null} />)
    expect(screen.getByRole('status')).toBeInTheDocument()
  })

  it('shows an error state, not a silently empty list', () => {
    renderWithRouter(
      <RecentLetters letters={[]} loading={false} error={{ message: 'Unable to reach the server.' }} />
    )
    expect(screen.getByRole('alert')).toHaveTextContent(/reach the server/i)
  })

  it('shows an empty state when there are no letters', () => {
    renderWithRouter(<RecentLetters letters={[]} loading={false} error={null} />)
    expect(screen.getByText(/no letters recorded yet/i)).toBeInTheDocument()
  })

  it('renders each letter as a link to its detail route, exactly as the backend returned it', () => {
    renderWithRouter(<RecentLetters letters={LETTERS} loading={false} error={null} />)

    const first = screen.getByRole('link', { name: /ref-001/i })
    expect(first).toHaveAttribute('href', '/app/letters/l1')
    expect(screen.getByText('Budget approval')).toBeInTheDocument()

    const second = screen.getByRole('link', { name: /ref-002/i })
    expect(second).toHaveAttribute('href', '/app/letters/l2')
  })

  it('never infers or fabricates a letter beyond what was passed in', () => {
    renderWithRouter(<RecentLetters letters={[LETTERS[0]]} loading={false} error={null} />)
    expect(screen.getAllByRole('link')).toHaveLength(1)
    expect(screen.queryByText('REF-002')).not.toBeInTheDocument()
  })
})
