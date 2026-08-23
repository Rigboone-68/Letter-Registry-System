import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import DepartmentDetailPage from './DepartmentDetailPage'

vi.mock('../services/departmentService', () => ({
  get: vi.fn(),
  update: vi.fn(),
  activate: vi.fn(),
  deactivate: vi.fn(),
}))

import * as departmentService from '../services/departmentService'

const DEPARTMENT = {
  id: 'd1',
  name: 'Finance',
  code: 'FIN',
  status: 'ACTIVE',
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-01T00:00:00Z',
}

function renderPage(id = 'd1') {
  return render(
    <MemoryRouter initialEntries={[`/app/system/departments/${id}`]}>
      <Routes>
        <Route path="/app/system/departments" element={<div>Department List</div>} />
        <Route path="/app/system/departments/:id" element={<DepartmentDetailPage />} />
      </Routes>
    </MemoryRouter>
  )
}

describe('DepartmentDetailPage', () => {
  beforeEach(() => vi.resetAllMocks())

  it('renders department fields', async () => {
    departmentService.get.mockResolvedValue(DEPARTMENT)
    renderPage()
    expect(await screen.findByRole('heading', { name: 'Finance' })).toBeInTheDocument()
    expect(screen.getByText('FIN')).toBeInTheDocument()
  })

  it('renders a generic not-found state for a 404', async () => {
    departmentService.get.mockRejectedValue({ status: 404, message: 'Department not found.', fieldErrors: null })
    renderPage()
    expect(await screen.findByRole('alert')).toHaveTextContent('Department not found.')
  })

  it('edits name/code and saves', async () => {
    departmentService.get.mockResolvedValue(DEPARTMENT)
    departmentService.update.mockResolvedValue({ ...DEPARTMENT, name: 'Finance & Treasury' })
    renderPage()
    await screen.findByRole('heading', { name: 'Finance' })

    await userEvent.click(screen.getByRole('button', { name: /^edit$/i }))
    const nameInput = screen.getByLabelText(/name/i)
    await userEvent.clear(nameInput)
    await userEvent.type(nameInput, 'Finance & Treasury')
    await userEvent.click(screen.getByRole('button', { name: /save changes/i }))

    expect(await screen.findByRole('heading', { name: 'Finance & Treasury' })).toBeInTheDocument()
  })

  it('activates without a confirmation dialog', async () => {
    departmentService.get.mockResolvedValue({ ...DEPARTMENT, status: 'INACTIVE' })
    departmentService.activate.mockResolvedValue({ ...DEPARTMENT, status: 'ACTIVE' })
    renderPage()
    await screen.findByRole('heading', { name: 'Finance' })

    await userEvent.click(screen.getByRole('button', { name: /^activate$/i }))

    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
    await waitFor(() => expect(departmentService.activate).toHaveBeenCalledWith('d1'))
  })

  it('requires confirmation before deactivating, using non-permanent wording', async () => {
    departmentService.get.mockResolvedValue(DEPARTMENT)
    departmentService.deactivate.mockResolvedValue({ ...DEPARTMENT, status: 'INACTIVE' })
    renderPage()
    await screen.findByRole('heading', { name: 'Finance' })

    await userEvent.click(screen.getByRole('button', { name: /^deactivate$/i }))
    const dialog = await screen.findByRole('dialog')
    expect(dialog.textContent.toLowerCase()).not.toMatch(/delete/)

    await userEvent.click(within(dialog).getByRole('button', { name: /deactivate department/i }))

    await waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument())
    expect(departmentService.deactivate).toHaveBeenCalledWith('d1')
  })
})
