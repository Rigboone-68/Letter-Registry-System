import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import ClassificationDetailPage from './ClassificationDetailPage'

vi.mock('../services/classificationService', () => ({
  get: vi.fn(),
  update: vi.fn(),
  activate: vi.fn(),
  deactivate: vi.fn(),
}))

import * as classificationService from '../services/classificationService'

const CLASSIFICATION = {
  id: 'cl1',
  name: 'Confidential',
  description: 'Restricted-distribution correspondence',
  restricts_access: true,
  status: 'ACTIVE',
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-01T00:00:00Z',
}

function renderPage(id = 'cl1') {
  return render(
    <MemoryRouter initialEntries={[`/app/system/classifications/${id}`]}>
      <Routes>
        <Route path="/app/system/classifications" element={<div>Classification List</div>} />
        <Route path="/app/system/classifications/:id" element={<ClassificationDetailPage />} />
      </Routes>
    </MemoryRouter>
  )
}

describe('ClassificationDetailPage', () => {
  beforeEach(() => vi.resetAllMocks())

  it('renders classification fields, including restricts_access as plain text', async () => {
    classificationService.get.mockResolvedValue(CLASSIFICATION)
    renderPage()
    expect(await screen.findByRole('heading', { name: 'Confidential' })).toBeInTheDocument()
    expect(screen.getByText('Restricted-distribution correspondence')).toBeInTheDocument()
    expect(screen.getByText('Yes')).toBeInTheDocument()
  })

  it('renders a generic not-found state for a 404', async () => {
    classificationService.get.mockRejectedValue({
      status: 404,
      message: 'Classification not found.',
      fieldErrors: null,
    })
    renderPage()
    expect(await screen.findByRole('alert')).toHaveTextContent('Classification not found.')
  })

  it('edits name/description/restricts_access and saves', async () => {
    classificationService.get.mockResolvedValue({ ...CLASSIFICATION, restricts_access: false })
    classificationService.update.mockResolvedValue({
      ...CLASSIFICATION,
      name: 'Confidential — Legal',
      restricts_access: true,
    })
    renderPage()
    await screen.findByRole('heading', { name: 'Confidential' })

    await userEvent.click(screen.getByRole('button', { name: /^edit$/i }))
    const nameInput = screen.getByLabelText(/^name/i)
    await userEvent.clear(nameInput)
    await userEvent.type(nameInput, 'Confidential — Legal')
    await userEvent.click(screen.getByLabelText(/restricts access/i))
    await userEvent.click(screen.getByRole('button', { name: /save changes/i }))

    expect(await screen.findByRole('heading', { name: 'Confidential — Legal' })).toBeInTheDocument()
    expect(classificationService.update).toHaveBeenCalledWith('cl1', {
      name: 'Confidential — Legal',
      description: 'Restricted-distribution correspondence',
      restricts_access: true,
    })
  })

  it('activates without a confirmation dialog', async () => {
    classificationService.get.mockResolvedValue({ ...CLASSIFICATION, status: 'INACTIVE' })
    classificationService.activate.mockResolvedValue({ ...CLASSIFICATION, status: 'ACTIVE' })
    renderPage()
    await screen.findByRole('heading', { name: 'Confidential' })

    await userEvent.click(screen.getByRole('button', { name: /^activate$/i }))

    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
    await waitFor(() => expect(classificationService.activate).toHaveBeenCalledWith('cl1'))
  })

  it('requires confirmation before deactivating, using non-permanent wording', async () => {
    classificationService.get.mockResolvedValue(CLASSIFICATION)
    classificationService.deactivate.mockResolvedValue({ ...CLASSIFICATION, status: 'INACTIVE' })
    renderPage()
    await screen.findByRole('heading', { name: 'Confidential' })

    await userEvent.click(screen.getByRole('button', { name: /^deactivate$/i }))
    const dialog = await screen.findByRole('dialog')
    expect(dialog.textContent.toLowerCase()).not.toMatch(/delete/)

    await userEvent.click(within(dialog).getByRole('button', { name: /deactivate classification/i }))

    await waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument())
    expect(classificationService.deactivate).toHaveBeenCalledWith('cl1')
  })

  it('never renders a delete action', async () => {
    classificationService.get.mockResolvedValue(CLASSIFICATION)
    renderPage()
    await screen.findByRole('heading', { name: 'Confidential' })
    expect(screen.queryByRole('button', { name: /^delete$/i })).not.toBeInTheDocument()
  })
})
