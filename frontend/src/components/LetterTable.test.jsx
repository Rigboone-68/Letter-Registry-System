import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it, vi } from 'vitest'

import LetterTable from './LetterTable'

const LETTERS = [
  {
    id: 'l1',
    reference_number: 'REF-001',
    recipient_department_id: 'd1',
    source_name: 'Ministry of Finance',
    source_department_id: null,
    source_location: null,
    sender_name: 'Jane Sender',
    sender_designation: 'Director',
    sender_department: 'Finance',
    sender_address: null,
    subject: 'Budget approval',
    category_id: null,
    classification_id: null,
    received_at: '2026-01-05T09:00:00Z',
    recorded_by: 'u1',
    status: 'ACTIVE',
    created_at: '2026-01-05T09:00:00Z',
    updated_at: '2026-01-05T09:00:00Z',
  },
]

function renderTable(props = {}) {
  return render(
    <MemoryRouter>
      <LetterTable letters={LETTERS} sortBy="received_at" sortOrder="desc" onSort={vi.fn()} {...props} />
    </MemoryRouter>
  )
}

describe('LetterTable', () => {
  it('renders accessible column headers with scope', () => {
    renderTable()
    const header = screen.getByRole('columnheader', { name: /reference number/i })
    expect(header).toHaveAttribute('scope', 'col')
  })

  it('marks the active sort column with aria-sort', () => {
    renderTable({ sortBy: 'subject', sortOrder: 'asc' })
    expect(screen.getByRole('columnheader', { name: /subject/i })).toHaveAttribute(
      'aria-sort',
      'ascending'
    )
    expect(screen.getByRole('columnheader', { name: /reference number/i })).toHaveAttribute(
      'aria-sort',
      'none'
    )
  })

  it('calls onSort with the column key when a sortable header is clicked', async () => {
    const onSort = vi.fn()
    renderTable({ onSort })
    await userEvent.click(screen.getByRole('button', { name: /subject/i }))
    expect(onSort).toHaveBeenCalledWith('subject')
  })

  it('renders only the columns for which a lookup map was supplied', () => {
    renderTable()
    expect(screen.queryByRole('columnheader', { name: /^category$/i })).not.toBeInTheDocument()

    renderTable({ categoryById: { c1: 'General Letter' } })
    expect(screen.getAllByRole('columnheader', { name: /^category$/i })).toHaveLength(1)
  })

  it('links each row to its detail page', () => {
    renderTable()
    expect(screen.getByRole('link', { name: 'REF-001' })).toHaveAttribute('href', '/app/letters/l1')
  })
})
