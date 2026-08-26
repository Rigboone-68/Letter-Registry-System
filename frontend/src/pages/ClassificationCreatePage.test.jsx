import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import ClassificationCreatePage from './ClassificationCreatePage'

vi.mock('../services/classificationService', () => ({ create: vi.fn() }))

import * as classificationService from '../services/classificationService'

function renderPage() {
  return render(
    <MemoryRouter initialEntries={['/app/system/classifications/new']}>
      <Routes>
        <Route path="/app/system/classifications" element={<div>Classification List</div>} />
        <Route path="/app/system/classifications/new" element={<ClassificationCreatePage />} />
        <Route path="/app/system/classifications/:id" element={<div>Classification Detail</div>} />
      </Routes>
    </MemoryRouter>
  )
}

describe('ClassificationCreatePage', () => {
  beforeEach(() => vi.resetAllMocks())

  it('requires a name before submitting', async () => {
    renderPage()
    await userEvent.click(screen.getByRole('button', { name: /create classification/i }))
    expect(await screen.findByText(/name is required/i)).toBeInTheDocument()
    expect(classificationService.create).not.toHaveBeenCalled()
  })

  it('defaults restricts_access to false when left unchecked', async () => {
    classificationService.create.mockResolvedValue({
      id: 'cl9',
      name: 'General',
      description: null,
      restricts_access: false,
      status: 'ACTIVE',
    })
    renderPage()
    await userEvent.type(screen.getByLabelText(/^name/i), 'General')
    await userEvent.click(screen.getByRole('button', { name: /create classification/i }))

    await waitFor(() => expect(screen.getByText('Classification Detail')).toBeInTheDocument())
    expect(classificationService.create).toHaveBeenCalledWith({
      name: 'General',
      description: null,
      restricts_access: false,
    })
  })

  it('sends restricts_access: true when the checkbox is checked', async () => {
    classificationService.create.mockResolvedValue({
      id: 'cl9',
      name: 'Confidential',
      description: null,
      restricts_access: true,
      status: 'ACTIVE',
    })
    renderPage()
    await userEvent.type(screen.getByLabelText(/^name/i), 'Confidential')
    await userEvent.click(screen.getByLabelText(/restricts access/i))
    await userEvent.click(screen.getByRole('button', { name: /create classification/i }))

    await waitFor(() => expect(classificationService.create).toHaveBeenCalled())
    expect(classificationService.create).toHaveBeenCalledWith({
      name: 'Confidential',
      description: null,
      restricts_access: true,
    })
  })

  it('shows a duplicate-name conflict from the backend', async () => {
    classificationService.create.mockRejectedValue({
      status: 409,
      message: 'A classification with this name already exists.',
      fieldErrors: null,
    })
    renderPage()
    await userEvent.type(screen.getByLabelText(/^name/i), 'Confidential')
    await userEvent.click(screen.getByRole('button', { name: /create classification/i }))
    expect(await screen.findByRole('alert')).toHaveTextContent(/already exists/i)
  })

  it('never sends id, status, or timestamps', async () => {
    classificationService.create.mockResolvedValue({
      id: 'cl9',
      name: 'General',
      description: null,
      restricts_access: false,
      status: 'ACTIVE',
    })
    renderPage()
    await userEvent.type(screen.getByLabelText(/^name/i), 'General')
    await userEvent.click(screen.getByRole('button', { name: /create classification/i }))

    await waitFor(() => expect(classificationService.create).toHaveBeenCalled())
    const payload = classificationService.create.mock.calls[0][0]
    expect(Object.keys(payload).sort()).toEqual(['description', 'name', 'restricts_access'])
  })

  it('cancels back to the classification list', async () => {
    renderPage()
    await userEvent.click(screen.getByRole('button', { name: /cancel/i }))
    expect(await screen.findByText('Classification List')).toBeInTheDocument()
  })
})
