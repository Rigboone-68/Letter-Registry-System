import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import ClassificationListPage from './ClassificationListPage'

vi.mock('../services/classificationService', () => ({ list: vi.fn() }))

import * as classificationService from '../services/classificationService'

function makeClassification(overrides = {}) {
  return {
    id: 'cl1',
    name: 'Confidential',
    description: 'Restricted-distribution correspondence',
    restricts_access: true,
    status: 'ACTIVE',
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
    ...overrides,
  }
}

function renderPage() {
  return render(
    <MemoryRouter initialEntries={['/app/system/classifications']}>
      <Routes>
        <Route path="/app/system/classifications" element={<ClassificationListPage />} />
      </Routes>
    </MemoryRouter>
  )
}

describe('ClassificationListPage', () => {
  beforeEach(() => vi.resetAllMocks())

  it('renders a successful list, including the restricts-access column', async () => {
    classificationService.list.mockResolvedValue({ items: [makeClassification()], total: 1 })
    renderPage()
    expect(await screen.findByText('Confidential')).toBeInTheDocument()
    expect(screen.getByText('1 total')).toBeInTheDocument()
    expect(screen.getByText('Yes')).toBeInTheDocument()
  })

  it('renders "No" for a classification that does not restrict access', async () => {
    classificationService.list.mockResolvedValue({
      items: [makeClassification({ id: 'cl2', name: 'General', restricts_access: false })],
      total: 1,
    })
    renderPage()
    expect(await screen.findByText('General')).toBeInTheDocument()
    expect(screen.getByText('No')).toBeInTheDocument()
  })

  it('shows an empty state when there are no results', async () => {
    classificationService.list.mockResolvedValue({ items: [], total: 0 })
    renderPage()
    expect(await screen.findByText(/no classifications match/i)).toBeInTheDocument()
  })

  it('shows an error state with a working retry', async () => {
    classificationService.list
      .mockRejectedValueOnce({ status: 0, message: 'Unable to reach the server.', fieldErrors: null })
      .mockResolvedValueOnce({ items: [makeClassification()], total: 1 })
    renderPage()
    expect(await screen.findByRole('alert')).toHaveTextContent(/reach the server/i)
    await userEvent.click(screen.getByRole('button', { name: /try again/i }))
    expect(await screen.findByText('Confidential')).toBeInTheDocument()
  })

  it('re-requests with the selected status filter', async () => {
    classificationService.list.mockResolvedValue({ items: [], total: 0 })
    renderPage()
    await waitFor(() => expect(classificationService.list).toHaveBeenCalledWith({}))

    await userEvent.selectOptions(screen.getByLabelText(/status/i), 'INACTIVE')

    await waitFor(() =>
      expect(classificationService.list).toHaveBeenLastCalledWith({ status: 'INACTIVE' })
    )
  })

  it('links to the create-classification page', async () => {
    classificationService.list.mockResolvedValue({ items: [], total: 0 })
    renderPage()
    expect(await screen.findByRole('link', { name: /create classification/i })).toHaveAttribute(
      'href',
      '/app/system/classifications/new'
    )
  })

  it('never renders a delete action', async () => {
    classificationService.list.mockResolvedValue({ items: [makeClassification()], total: 1 })
    renderPage()
    await screen.findByText('Confidential')
    expect(screen.queryByRole('button', { name: /delete/i })).not.toBeInTheDocument()
  })
})
