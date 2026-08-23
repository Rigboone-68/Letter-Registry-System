import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import DepartmentCreatePage from './DepartmentCreatePage'

vi.mock('../services/departmentService', () => ({ create: vi.fn() }))

import * as departmentService from '../services/departmentService'

function renderPage() {
  return render(
    <MemoryRouter initialEntries={['/app/system/departments/new']}>
      <Routes>
        <Route path="/app/system/departments" element={<div>Department List</div>} />
        <Route path="/app/system/departments/new" element={<DepartmentCreatePage />} />
        <Route path="/app/system/departments/:id" element={<div>Department Detail</div>} />
      </Routes>
    </MemoryRouter>
  )
}

describe('DepartmentCreatePage', () => {
  beforeEach(() => vi.resetAllMocks())

  it('requires a name before submitting', async () => {
    renderPage()
    await userEvent.click(screen.getByRole('button', { name: /create department/i }))
    expect(await screen.findByText(/name is required/i)).toBeInTheDocument()
    expect(departmentService.create).not.toHaveBeenCalled()
  })

  it('creates successfully and navigates to the new department', async () => {
    departmentService.create.mockResolvedValue({ id: 'd9', name: 'Health', code: null, status: 'ACTIVE' })
    renderPage()
    await userEvent.type(screen.getByLabelText(/name/i), 'Health')
    await userEvent.click(screen.getByRole('button', { name: /create department/i }))

    await waitFor(() => expect(screen.getByText('Department Detail')).toBeInTheDocument())
    expect(departmentService.create).toHaveBeenCalledWith({ name: 'Health', code: null })
  })

  it('shows a duplicate-name conflict from the backend', async () => {
    departmentService.create.mockRejectedValue({
      status: 409,
      message: 'A department with this name already exists.',
      fieldErrors: null,
    })
    renderPage()
    await userEvent.type(screen.getByLabelText(/name/i), 'Finance')
    await userEvent.click(screen.getByRole('button', { name: /create department/i }))
    expect(await screen.findByRole('alert')).toHaveTextContent(/already exists/i)
  })

  it('never sends id, status, or timestamps', async () => {
    departmentService.create.mockResolvedValue({ id: 'd9', name: 'Health', code: null, status: 'ACTIVE' })
    renderPage()
    await userEvent.type(screen.getByLabelText(/name/i), 'Health')
    await userEvent.click(screen.getByRole('button', { name: /create department/i }))

    await waitFor(() => expect(departmentService.create).toHaveBeenCalled())
    const payload = departmentService.create.mock.calls[0][0]
    expect(Object.keys(payload).sort()).toEqual(['code', 'name'])
  })

  it('cancels back to the department list', async () => {
    renderPage()
    await userEvent.click(screen.getByRole('button', { name: /cancel/i }))
    expect(await screen.findByText('Department List')).toBeInTheDocument()
  })
})
