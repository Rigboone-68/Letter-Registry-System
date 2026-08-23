import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import AdminListPage from './AdminListPage'

vi.mock('../services/adminService', () => ({ list: vi.fn() }))
vi.mock('../services/departmentService', () => ({ list: vi.fn() }))

import * as adminService from '../services/adminService'
import * as departmentService from '../services/departmentService'

function renderPage() {
  return render(
    <MemoryRouter initialEntries={['/app/system/admins']}>
      <Routes>
        <Route path="/app/system/admins" element={<AdminListPage />} />
      </Routes>
    </MemoryRouter>
  )
}

describe('AdminListPage', () => {
  beforeEach(() => {
    vi.resetAllMocks()
    departmentService.list.mockResolvedValue({
      items: [{ id: 'd1', name: 'Finance', code: 'FIN', status: 'ACTIVE' }],
      total: 1,
    })
  })

  it('renders a successful list with resolved department names', async () => {
    adminService.list.mockResolvedValue({
      items: [{ id: 'a1', full_name: 'Jane Admin', email: 'jane@example.gov', role: 'ADMIN', department_id: 'd1', status: 'ACTIVE' }],
      total: 1,
    })
    renderPage()
    expect(await screen.findByText('Jane Admin')).toBeInTheDocument()
    const table = screen.getByRole('table')
    expect(await within(table).findByText('Finance')).toBeInTheDocument()
  })

  it('shows an empty state when there are no results', async () => {
    adminService.list.mockResolvedValue({ items: [], total: 0 })
    renderPage()
    expect(await screen.findByText(/no administrators match/i)).toBeInTheDocument()
  })

  it('shows an error state on API failure', async () => {
    adminService.list.mockRejectedValue({ status: 0, message: 'Unable to reach the server.', fieldErrors: null })
    renderPage()
    expect(await screen.findByRole('alert')).toHaveTextContent(/reach the server/i)
  })

  it('re-requests with both status and department filters', async () => {
    adminService.list.mockResolvedValue({ items: [], total: 0 })
    renderPage()
    await waitFor(() => expect(adminService.list).toHaveBeenCalledWith({}))
    await screen.findByLabelText(/department/i)

    await userEvent.selectOptions(screen.getByLabelText(/^status/i), 'ACTIVE')
    await userEvent.selectOptions(screen.getByLabelText(/department/i), 'd1')

    await waitFor(() =>
      expect(adminService.list).toHaveBeenLastCalledWith({ status: 'ACTIVE', department_id: 'd1' })
    )
  })

  it('links to the Authorize form', async () => {
    adminService.list.mockResolvedValue({ items: [], total: 0 })
    renderPage()
    expect(await screen.findByRole('link', { name: /authorize new admin/i })).toHaveAttribute(
      'href',
      '/app/system/admins/authorize'
    )
  })
})
