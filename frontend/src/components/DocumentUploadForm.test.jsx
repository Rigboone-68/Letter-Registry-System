import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import DocumentUploadForm from './DocumentUploadForm'

vi.mock('../services/documentService', async () => {
  const actual = await vi.importActual('../services/documentService')
  return { ...actual, upload: vi.fn() }
})

import * as documentService from '../services/documentService'

function makeFile({ name = 'letter.pdf', size = 1024, type = 'application/pdf' } = {}) {
  return new File([new Uint8Array(size)], name, { type })
}

describe('DocumentUploadForm', () => {
  beforeEach(() => vi.resetAllMocks())

  it('renders a labeled file input with the accepted-type/size explanation', () => {
    render(<DocumentUploadForm letterId="l1" onUploadSuccess={vi.fn()} />)
    const input = screen.getByLabelText(/upload document/i)
    expect(input).toHaveAttribute('type', 'file')
    expect(screen.getByText(/accepted types:.*pdf.*maximum size: 10 mb/i)).toBeInTheDocument()
  })

  it('requires a file before submitting', async () => {
    render(<DocumentUploadForm letterId="l1" onUploadSuccess={vi.fn()} />)
    await userEvent.click(screen.getByRole('button', { name: /upload document/i }))
    expect(await screen.findByText(/select a file/i)).toBeInTheDocument()
    expect(documentService.upload).not.toHaveBeenCalled()
  })

  it('rejects an unsupported file type client-side', async () => {
    render(<DocumentUploadForm letterId="l1" onUploadSuccess={vi.fn()} />)
    const input = screen.getByLabelText(/upload document/i)
    // fireEvent.change (not userEvent.upload) bypasses the input's `accept`
    // filtering, simulating a file arriving via drag-and-drop rather than the
    // native picker, so the client-side extension check actually gets exercised.
    fireEvent.change(input, { target: { files: [makeFile({ name: 'archive.zip', type: 'application/zip' })] } })
    await userEvent.click(screen.getByRole('button', { name: /upload document/i }))
    expect(await screen.findByText(/unsupported file type/i)).toBeInTheDocument()
    expect(documentService.upload).not.toHaveBeenCalled()
  })

  it('rejects an oversized file client-side', async () => {
    render(<DocumentUploadForm letterId="l1" onUploadSuccess={vi.fn()} />)
    const input = screen.getByLabelText(/upload document/i)
    await userEvent.upload(input, makeFile({ size: 11 * 1024 * 1024 }))
    await userEvent.click(screen.getByRole('button', { name: /upload document/i }))
    expect(await screen.findByText(/exceeds the maximum allowed size/i)).toBeInTheDocument()
    expect(documentService.upload).not.toHaveBeenCalled()
  })

  it('uploads successfully, clears the field, and calls onUploadSuccess with the response', async () => {
    const created = { id: 'd1', letter_id: 'l1', original_filename: 'letter.pdf', mime_type: 'application/pdf', file_size: 1024, uploaded_by: 'u1', uploaded_at: '2026-01-01T00:00:00Z' }
    documentService.upload.mockResolvedValue(created)
    const onUploadSuccess = vi.fn()
    render(<DocumentUploadForm letterId="l1" onUploadSuccess={onUploadSuccess} />)
    const input = screen.getByLabelText(/upload document/i)
    await userEvent.upload(input, makeFile())
    await userEvent.click(screen.getByRole('button', { name: /upload document/i }))

    await waitFor(() => expect(onUploadSuccess).toHaveBeenCalledWith(created))
    expect(documentService.upload).toHaveBeenCalledWith('l1', expect.any(File), expect.any(Function))
    expect(input.files).toHaveLength(0)
  })

  it('shows a distinct message for a backend 422 (unsupported/mismatched content)', async () => {
    documentService.upload.mockRejectedValue({
      status: 422,
      message: 'Unsupported, unrecognized, or mismatched file type.',
      fieldErrors: null,
    })
    render(<DocumentUploadForm letterId="l1" onUploadSuccess={vi.fn()} />)
    await userEvent.upload(screen.getByLabelText(/upload document/i), makeFile())
    await userEvent.click(screen.getByRole('button', { name: /upload document/i }))
    expect(await screen.findByRole('alert')).toHaveTextContent(/mismatched file type/i)
  })

  it('shows a distinct message for a backend 413 (too large)', async () => {
    documentService.upload.mockRejectedValue({
      status: 413,
      message: 'File exceeds the maximum allowed size of 10485760 bytes.',
      fieldErrors: null,
    })
    render(<DocumentUploadForm letterId="l1" onUploadSuccess={vi.fn()} />)
    await userEvent.upload(screen.getByLabelText(/upload document/i), makeFile())
    await userEvent.click(screen.getByRole('button', { name: /upload document/i }))
    expect(await screen.findByRole('alert')).toHaveTextContent(/exceeds the maximum allowed size/i)
  })

  it('shows a retryable network-failure message and keeps the selected file', async () => {
    documentService.upload.mockRejectedValue({ status: 0, message: 'Unable to reach the server. Check your connection and try again.', fieldErrors: null })
    render(<DocumentUploadForm letterId="l1" onUploadSuccess={vi.fn()} />)
    const input = screen.getByLabelText(/upload document/i)
    await userEvent.upload(input, makeFile())
    await userEvent.click(screen.getByRole('button', { name: /upload document/i }))
    expect(await screen.findByRole('alert')).toHaveTextContent(/reach the server/i)
    expect(input.files).toHaveLength(1)
  })

  it('disables the submit button and shows an uploading state while in flight', async () => {
    let resolveUpload
    documentService.upload.mockReturnValue(new Promise((resolve) => { resolveUpload = resolve }))
    render(<DocumentUploadForm letterId="l1" onUploadSuccess={vi.fn()} />)
    await userEvent.upload(screen.getByLabelText(/upload document/i), makeFile())
    await userEvent.click(screen.getByRole('button', { name: /upload document/i }))

    expect(screen.getByRole('button', { name: /uploading/i })).toBeDisabled()
    expect(screen.getByRole('status')).toHaveTextContent(/uploading/i)
    resolveUpload({ id: 'd1', original_filename: 'letter.pdf' })
  })
})
