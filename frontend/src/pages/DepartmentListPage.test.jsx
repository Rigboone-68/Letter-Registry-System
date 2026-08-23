import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import DepartmentListPage from './DepartmentListPage'

vi.mock('../services/departmentService', () => ({ list: vi.fn() }))

import * as departmentService from '../services/departmentService'

function makeDepartment(overrides = {}) {
  return { id: 'd1', name: 'Finance', code: 'FIN', status: 'ACTIVE', created_at: '2026-01-01T00:00:00Z', updated_at: '2026-01-01T00:00:00Z', ...overrides }
}

function renderPage() {
  return render(
    <MemoryRouter initialEntries={['/app/system/departments']}>
      <Routes>
        <Route path="/app/system/departments" element={<DepartmentListPage />} />
      </Routes>
    </MemoryRouter>
  )
}

describe('DepartmentListPage', () => {
  beforeEach(() => vi.resetAllMocks())

  it('renders a successful list', async () => {
    departmentService.list.mockResolvedValue({ items: [makeDepartment()], total: 1 })
    renderPage()
    expect(await screen.findByText('Finance')).toBeInTheDocument()
    expect(screen.getByText('1 total')).toBeInTheDocument()
  })

  it('shows an empty state when there are no results', async () => {
    departmentService.list.mockResolvedValue({ items: [], total: 0 })
    renderPage()
    expect(await screen.findByText(/no departments match/i)).toBeInTheDocument()
  })

  it('shows an error state with a working retry', async () => {
    departmentService.list
      .mockRejectedValueOnce({ status: 0, message: 'Unable to reach the server.', fieldErrors: null })
      .mockResolvedValueOnce({ items: [makeDepartment()], total: 1 })
    renderPage()
    expect(await screen.findByRole('alert')).toHaveTextContent(/reach the server/i)
    await userEvent.click(screen.getByRole('button', { name: /try again/i }))
    expect(await screen.findByText('Finance')).toBeInTheDocument()
  })

  it('re-requests with the selected status filter', async () => {
    departmentService.list.mockResolvedValue({ items: [], total: 0 })
    renderPage()
    await waitFor(() => expect(departmentService.list).toHaveBeenCalledWith({}))

    await userEvent.selectOptions(screen.getByLabelText(/status/i), 'INACTIVE')

    await waitFor(() =>
      expect(departmentService.list).toHaveBeenLastCalledWith({ status: 'INACTIVE' })
    )
  })

  it('links to the create-department page', async () => {
    departmentService.list.mockResolvedValue({ items: [], total: 0 })
    renderPage()
    expect(await screen.findByRole('link', { name: /create department/i })).toHaveAttribute(
      'href',
      '/app/system/departments/new'
    )
  })
})
