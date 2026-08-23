import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import LetterDetailPage from './LetterDetailPage'

vi.mock('../services/letterService', async () => {
  const actual = await vi.importActual('../services/letterService')
  return { ...actual, get: vi.fn(), archive: vi.fn() }
})

import * as letterService from '../services/letterService'

const LETTER = {
  id: 'l1',
  reference_number: 'REF-001',
  recipient_department_id: 'd1',
  source_name: 'Ministry of Finance',
  source_department_id: null,
  source_location: 'Capital City',
  sender_name: 'Jane Sender',
  sender_designation: 'Director',
  sender_department: 'Finance',
  sender_address: null,
  subject: 'Budget approval',
  reason: null,
  category_id: null,
  classification_id: null,
  received_at: '2026-01-05T09:00:00Z',
  recorded_by: 'u1',
  text_content: null,
  status: 'ACTIVE',
  created_at: '2026-01-05T09:00:00Z',
  updated_at: '2026-01-05T09:00:00Z',
}

function renderDetail(id = 'l1') {
  return render(
    <MemoryRouter initialEntries={[`/app/letters/${id}`]}>
      <Routes>
        <Route path="/app/letters" element={<div>Registry List</div>} />
        <Route path="/app/letters/:id" element={<LetterDetailPage />} />
        <Route path="/app/letters/:id/edit" element={<div>Edit Page</div>} />
      </Routes>
    </MemoryRouter>
  )
}

describe('LetterDetailPage', () => {
  beforeEach(() => vi.resetAllMocks())

  it('renders the confirmed LetterResponse fields', async () => {
    letterService.get.mockResolvedValue(LETTER)
    renderDetail()

    expect(await screen.findByRole('heading', { name: 'REF-001' })).toBeInTheDocument()
    expect(screen.getByText('Budget approval')).toBeInTheDocument()
    expect(screen.getByText('Ministry of Finance')).toBeInTheDocument()
    expect(screen.getByText('Jane Sender')).toBeInTheDocument()
  })

  it('renders a generic not-found state for a 404, with no distinguishing classified language', async () => {
    letterService.get.mockRejectedValue({ status: 404, message: 'Letter not found.', fieldErrors: null })
    renderDetail()

    const alert = await screen.findByRole('alert')
    expect(alert).toHaveTextContent('Letter not found.')
    expect(alert.textContent.toLowerCase()).not.toMatch(/classif/)
    expect(alert.textContent.toLowerCase()).not.toMatch(/permission/)
  })

  it('renders a retryable error for a non-404 failure', async () => {
    letterService.get.mockRejectedValueOnce({ status: 0, message: 'Unable to reach the server.', fieldErrors: null })
    letterService.get.mockResolvedValueOnce(LETTER)
    renderDetail()

    expect(await screen.findByRole('alert')).toHaveTextContent(/reach the server/i)
    await userEvent.click(screen.getByRole('button', { name: /try again/i }))
    expect(await screen.findByRole('heading', { name: 'REF-001' })).toBeInTheDocument()
  })

  it('opens a confirmation dialog before archiving, using non-permanent language', async () => {
    letterService.get.mockResolvedValue(LETTER)
    renderDetail()
    await screen.findByRole('heading', { name: 'REF-001' })

    await userEvent.click(screen.getByRole('button', { name: /archive letter/i }))

    const dialog = screen.getByRole('dialog')
    expect(dialog.textContent.toLowerCase()).not.toMatch(/permanent/)
    expect(dialog.textContent.toLowerCase()).not.toMatch(/delete permanently|permanently delete/)
  })

  it('archives successfully and reflects the new status', async () => {
    letterService.get.mockResolvedValue(LETTER)
    letterService.archive.mockResolvedValue({ ...LETTER, status: 'ARCHIVED' })
    renderDetail()
    await screen.findByRole('heading', { name: 'REF-001' })

    await userEvent.click(screen.getByRole('button', { name: /archive letter/i }))
    await userEvent.click(within(screen.getByRole('dialog')).getByRole('button', { name: /archive letter/i }))

    await waitFor(() => expect(screen.getByText('Archived')).toBeInTheDocument())
    expect(screen.queryByText('Active')).not.toBeInTheDocument()
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
  })

  it('shows an error and keeps the dialog open when archiving fails', async () => {
    letterService.get.mockResolvedValue(LETTER)
    letterService.archive.mockRejectedValue({ status: 0, message: 'Unable to reach the server.', fieldErrors: null })
    renderDetail()
    await screen.findByRole('heading', { name: 'REF-001' })

    await userEvent.click(screen.getByRole('button', { name: /archive letter/i }))
    await userEvent.click(within(screen.getByRole('dialog')).getByRole('button', { name: /archive letter/i }))

    expect(await screen.findByText(/unable to reach the server/i)).toBeInTheDocument()
    expect(screen.getByRole('dialog')).toBeInTheDocument()
  })

  it('hides the archive action once a letter is already archived', async () => {
    letterService.get.mockResolvedValue({ ...LETTER, status: 'ARCHIVED' })
    renderDetail()
    await screen.findByRole('heading', { name: 'REF-001' })

    expect(screen.queryByRole('button', { name: /archive letter/i })).not.toBeInTheDocument()
  })
})
