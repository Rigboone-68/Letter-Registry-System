import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import LetterDetailPage from './LetterDetailPage'

vi.mock('../services/letterService', async () => {
  const actual = await vi.importActual('../services/letterService')
  return { ...actual, get: vi.fn(), archive: vi.fn() }
})
vi.mock('../services/documentService', async () => {
  const actual = await vi.importActual('../services/documentService')
  return { ...actual, list: vi.fn(), upload: vi.fn(), download: vi.fn() }
})

import * as documentService from '../services/documentService'
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
  beforeEach(() => {
    vi.resetAllMocks()
    documentService.list.mockResolvedValue({ items: [], total: 0 })
  })

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

  describe('Documents integration (Phase 5E)', () => {
    it('fetches and renders the document list once the letter loads', async () => {
      letterService.get.mockResolvedValue(LETTER)
      documentService.list.mockResolvedValue({
        items: [
          {
            id: 'd1',
            letter_id: 'l1',
            original_filename: 'scan.pdf',
            mime_type: 'application/pdf',
            file_size: 1024,
            uploaded_by: 'u1',
            uploaded_at: '2026-01-05T09:00:00Z',
          },
        ],
        total: 1,
      })
      renderDetail()

      await screen.findByRole('heading', { name: 'REF-001' })
      expect(documentService.list).toHaveBeenCalledWith('l1')
      expect(await screen.findByText('scan.pdf')).toBeInTheDocument()
    })

    it('shows an empty state when the letter has no documents', async () => {
      letterService.get.mockResolvedValue(LETTER)
      documentService.list.mockResolvedValue({ items: [], total: 0 })
      renderDetail()

      expect(await screen.findByText(/no documents have been uploaded/i)).toBeInTheDocument()
    })

    it('shows a retryable error state for the document list, independent of the letter itself', async () => {
      letterService.get.mockResolvedValue(LETTER)
      documentService.list.mockRejectedValueOnce({ status: 0, message: 'Unable to reach the server.', fieldErrors: null })
      documentService.list.mockResolvedValueOnce({ items: [], total: 0 })
      renderDetail()

      await screen.findByRole('heading', { name: 'REF-001' })
      expect(await screen.findByRole('alert')).toHaveTextContent(/reach the server/i)

      await userEvent.click(screen.getByRole('button', { name: /try again/i }))
      expect(await screen.findByText(/no documents have been uploaded/i)).toBeInTheDocument()
    })

    it('never fetches documents when the Letter itself is inaccessible', async () => {
      letterService.get.mockRejectedValue({ status: 404, message: 'Letter not found.', fieldErrors: null })
      renderDetail()

      await screen.findByRole('alert')
      expect(documentService.list).not.toHaveBeenCalled()
    })

    it('appends a newly uploaded document to the list from the upload response, without a second list request', async () => {
      letterService.get.mockResolvedValue(LETTER)
      documentService.list.mockResolvedValue({ items: [], total: 0 })
      documentService.upload.mockResolvedValue({
        id: 'd2',
        letter_id: 'l1',
        original_filename: 'new-scan.pdf',
        mime_type: 'application/pdf',
        file_size: 2048,
        uploaded_by: 'u1',
        uploaded_at: '2026-01-06T09:00:00Z',
      })
      renderDetail()
      await screen.findByRole('heading', { name: 'REF-001' })
      await screen.findByText(/no documents have been uploaded/i)

      const file = new File([new Uint8Array(10)], 'new-scan.pdf', { type: 'application/pdf' })
      await userEvent.upload(screen.getByLabelText(/upload document/i), file)
      await userEvent.click(screen.getByRole('button', { name: /^upload document$/i }))

      expect(await screen.findByText('new-scan.pdf')).toBeInTheDocument()
      expect(documentService.list).toHaveBeenCalledTimes(1)
    })

    it('preserves Letter metadata, edit, and archive alongside the Documents section', async () => {
      letterService.get.mockResolvedValue(LETTER)
      documentService.list.mockResolvedValue({ items: [], total: 0 })
      renderDetail()

      await screen.findByRole('heading', { name: 'REF-001' })
      expect(screen.getByText('Budget approval')).toBeInTheDocument()
      expect(screen.getByRole('link', { name: /edit/i })).toHaveAttribute('href', '/app/letters/l1/edit')
      expect(screen.getByRole('button', { name: /archive letter/i })).toBeInTheDocument()
      expect(await screen.findByText(/no documents have been uploaded/i)).toBeInTheDocument()
    })
  })
})
