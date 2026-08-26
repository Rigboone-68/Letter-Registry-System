import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import DesignationListPage from './DesignationListPage'

vi.mock('../services/designationService', () => ({
  list: vi.fn(),
  create: vi.fn(),
  activate: vi.fn(),
  deactivate: vi.fn(),
}))

import * as designationService from '../services/designationService'

function makeDesignation(overrides = {}) {
  return {
    id: 'des1',
    name: 'Section Officer',
    status: 'ACTIVE',
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
    ...overrides,
  }
}

function renderPage() {
  return render(
    <MemoryRouter>
      <DesignationListPage />
    </MemoryRouter>
  )
}

describe('DesignationListPage', () => {
  beforeEach(() => vi.resetAllMocks())

  it('renders a successful list', async () => {
    designationService.list.mockResolvedValue({ items: [makeDesignation()], total: 1 })
    renderPage()
    expect(await screen.findByText('Section Officer')).toBeInTheDocument()
  })

  it('shows an empty state when no designations match the filter', async () => {
    designationService.list.mockResolvedValue({ items: [], total: 0 })
    renderPage()
    expect(await screen.findByText(/no designations match/i)).toBeInTheDocument()
  })

  it('shows a retryable error state', async () => {
    designationService.list.mockRejectedValueOnce({
      status: 0,
      message: 'Unable to reach the server.',
      fieldErrors: null,
    })
    designationService.list.mockResolvedValueOnce({ items: [], total: 0 })
    renderPage()
    expect(await screen.findByRole('alert')).toHaveTextContent(/reach the server/i)
    await userEvent.click(screen.getByRole('button', { name: /try again/i }))
    expect(await screen.findByText(/no designations match/i)).toBeInTheDocument()
  })

  it('requires a name before creating', async () => {
    designationService.list.mockResolvedValue({ items: [], total: 0 })
    renderPage()
    await screen.findByText(/no designations match/i)

    await userEvent.click(screen.getByRole('button', { name: /add designation/i }))
    expect(await screen.findByText(/name is required/i)).toBeInTheDocument()
    expect(designationService.create).not.toHaveBeenCalled()
  })

  it('creates a designation and refreshes the list', async () => {
    designationService.list
      .mockResolvedValueOnce({ items: [], total: 0 })
      .mockResolvedValueOnce({ items: [makeDesignation()], total: 1 })
    designationService.create.mockResolvedValue(makeDesignation())
    renderPage()
    await screen.findByText(/no designations match/i)

    await userEvent.type(screen.getByLabelText(/new designation name/i), 'Section Officer')
    await userEvent.click(screen.getByRole('button', { name: /add designation/i }))

    await waitFor(() => expect(designationService.create).toHaveBeenCalledWith({ name: 'Section Officer' }))
    expect(await screen.findByText('Section Officer')).toBeInTheDocument()
    expect(screen.getByLabelText(/new designation name/i)).toHaveValue('')
  })

  it('shows a 409 for a duplicate name, case-insensitive or not', async () => {
    designationService.list.mockResolvedValue({ items: [], total: 0 })
    designationService.create.mockRejectedValue({
      status: 409,
      message: 'A designation with this name already exists.',
      fieldErrors: null,
    })
    renderPage()
    await screen.findByText(/no designations match/i)

    await userEvent.type(screen.getByLabelText(/new designation name/i), 'Secretary')
    await userEvent.click(screen.getByRole('button', { name: /add designation/i }))

    expect(await screen.findByRole('alert')).toHaveTextContent(/already exists/i)
  })

  it('activates an inactive designation directly, with no confirmation dialog', async () => {
    designationService.list.mockResolvedValue({
      items: [makeDesignation({ status: 'INACTIVE' })],
      total: 1,
    })
    designationService.activate.mockResolvedValue(makeDesignation({ status: 'ACTIVE' }))
    renderPage()
    await screen.findByText('Section Officer')

    await userEvent.click(screen.getByRole('button', { name: /^activate$/i }))

    await waitFor(() => expect(designationService.activate).toHaveBeenCalledWith('des1'))
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
    expect(await screen.findByRole('button', { name: /^deactivate$/i })).toBeInTheDocument()
  })

  it('deactivates only after confirmation, stating existing Letters keep their designation unchanged', async () => {
    designationService.list.mockResolvedValue({ items: [makeDesignation()], total: 1 })
    designationService.deactivate.mockResolvedValue(makeDesignation({ status: 'INACTIVE' }))
    renderPage()
    await screen.findByText('Section Officer')

    await userEvent.click(screen.getByRole('button', { name: /^deactivate$/i }))
    const dialog = await screen.findByRole('dialog')
    expect(dialog.textContent.toLowerCase()).toMatch(/keep it unchanged/)

    await userEvent.click(within(dialog).getByRole('button', { name: /deactivate designation/i }))

    await waitFor(() => expect(designationService.deactivate).toHaveBeenCalledWith('des1'))
    expect(await screen.findByRole('button', { name: /^activate$/i })).toBeInTheDocument()
  })

  it('cancelling the deactivate dialog makes no request', async () => {
    designationService.list.mockResolvedValue({ items: [makeDesignation()], total: 1 })
    renderPage()
    await screen.findByText('Section Officer')

    await userEvent.click(screen.getByRole('button', { name: /^deactivate$/i }))
    const dialog = await screen.findByRole('dialog')
    await userEvent.click(within(dialog).getByRole('button', { name: /cancel/i }))

    expect(designationService.deactivate).not.toHaveBeenCalled()
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
  })

  it('filters by status, sending it as a real query parameter', async () => {
    designationService.list.mockResolvedValue({ items: [], total: 0 })
    renderPage()
    await waitFor(() => expect(designationService.list).toHaveBeenCalledWith({}))

    await userEvent.selectOptions(screen.getByLabelText(/status/i), 'ACTIVE')

    await waitFor(() => expect(designationService.list).toHaveBeenLastCalledWith({ status: 'ACTIVE' }))
  })

  it('never renders a delete action of any kind', async () => {
    designationService.list.mockResolvedValue({ items: [makeDesignation()], total: 1 })
    renderPage()
    await screen.findByText('Section Officer')
    expect(screen.queryByRole('button', { name: /delete/i })).not.toBeInTheDocument()
  })
})
