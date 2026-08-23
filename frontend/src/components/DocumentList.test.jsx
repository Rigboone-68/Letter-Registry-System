import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import DocumentList from './DocumentList'

vi.mock('../services/documentService', async () => {
  const actual = await vi.importActual('../services/documentService')
  return { ...actual, download: vi.fn() }
})

import * as documentService from '../services/documentService'

const DOCUMENTS = [
  {
    id: 'd1',
    letter_id: 'l1',
    original_filename: 'scan.pdf',
    mime_type: 'application/pdf',
    file_size: 204800,
    uploaded_by: 'u1',
    uploaded_at: '2026-01-05T09:00:00Z',
  },
]

describe('DocumentList', () => {
  beforeEach(() => {
    vi.resetAllMocks()
    URL.createObjectURL = vi.fn().mockReturnValue('blob:mock-url')
    URL.revokeObjectURL = vi.fn()
    // jsdom doesn't implement the `download` attribute's non-navigating
    // save behavior, so a real .click() on the synthetic anchor attempts
    // an unsupported navigation and logs stderr noise unrelated to this
    // component's own behavior.
    vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => {})
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('renders only fields the backend actually returns', () => {
    render(<DocumentList letterId="l1" documents={DOCUMENTS} />)
    expect(screen.getByText('scan.pdf')).toBeInTheDocument()
    expect(screen.getByText('200.0 KB')).toBeInTheDocument()
    expect(screen.getByText('application/pdf')).toBeInTheDocument()
    // No storage path, no raw uploader id, ever rendered.
    expect(screen.queryByText(/storage/i)).not.toBeInTheDocument()
    expect(screen.queryByText('u1')).not.toBeInTheDocument()
  })

  it('never renders a delete or replace action', () => {
    render(<DocumentList letterId="l1" documents={DOCUMENTS} />)
    expect(screen.queryByRole('button', { name: /delete/i })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /replace/i })).not.toBeInTheDocument()
  })

  it('has an accessible, per-row download button name', () => {
    render(<DocumentList letterId="l1" documents={DOCUMENTS} />)
    expect(screen.getByRole('button', { name: 'Download scan.pdf' })).toBeInTheDocument()
  })

  it('downloads successfully via authenticated fetch + blob, not a plain link', async () => {
    const blob = new Blob(['content'], { type: 'application/pdf' })
    documentService.download.mockResolvedValue(blob)
    render(<DocumentList letterId="l1" documents={DOCUMENTS} />)

    await userEvent.click(screen.getByRole('button', { name: 'Download scan.pdf' }))

    await waitFor(() => expect(documentService.download).toHaveBeenCalledWith('l1', 'd1'))
    expect(URL.createObjectURL).toHaveBeenCalledWith(blob)
  })

  it('shows a retryable error on download failure', async () => {
    documentService.download.mockRejectedValue({
      status: 0,
      message: 'Unable to reach the server. Check your connection and try again.',
      fieldErrors: null,
    })
    render(<DocumentList letterId="l1" documents={DOCUMENTS} />)

    await userEvent.click(screen.getByRole('button', { name: 'Download scan.pdf' }))

    expect(await screen.findByRole('alert')).toHaveTextContent(/reach the server/i)
  })

  it('renders a generic message for a 404 (Letter or Document not found, either cause)', async () => {
    documentService.download.mockRejectedValue({ status: 404, message: 'Document not found.', fieldErrors: null })
    render(<DocumentList letterId="l1" documents={DOCUMENTS} />)

    await userEvent.click(screen.getByRole('button', { name: 'Download scan.pdf' }))

    const alert = await screen.findByRole('alert')
    expect(alert).toHaveTextContent('Document not found.')
    expect(alert.textContent.toLowerCase()).not.toMatch(/classif|permission/)
  })

  it('disables the row action while its own download is in flight', async () => {
    let resolveDownload
    documentService.download.mockReturnValue(new Promise((resolve) => { resolveDownload = resolve }))
    render(<DocumentList letterId="l1" documents={DOCUMENTS} />)

    await userEvent.click(screen.getByRole('button', { name: 'Download scan.pdf' }))

    expect(screen.getByRole('button', { name: /downloading/i })).toBeDisabled()
    resolveDownload(new Blob(['content']))
  })
})
