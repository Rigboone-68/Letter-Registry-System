import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import AdminDetailPage from './AdminDetailPage'

vi.mock('../services/adminService', () => ({
  get: vi.fn(),
  approve: vi.fn(),
  deactivate: vi.fn(),
  reactivate: vi.fn(),
  changeDepartment: vi.fn(),
}))
vi.mock('../services/departmentService', () => ({ list: vi.fn() }))

import * as adminService from '../services/adminService'
import * as departmentService from '../services/departmentService'

const DEPARTMENTS = [
  { id: 'd1', name: 'Finance', code: 'FIN', status: 'ACTIVE' },
  { id: 'd2', name: 'Health', code: 'HLT', status: 'ACTIVE' },
]

function makeAdmin(overrides = {}) {
  return {
    id: 'a1',
    full_name: 'Jane Admin',
    email: 'jane@example.gov',
    role: 'ADMIN',
    department_id: 'd1',
    status: 'ACTIVE',
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
    ...overrides,
  }
}

function renderPage(id = 'a1') {
  return render(
    <MemoryRouter initialEntries={[`/app/system/admins/${id}`]}>
      <Routes>
        <Route path="/app/system/admins" element={<div>Admin List</div>} />
        <Route path="/app/system/admins/:id" element={<AdminDetailPage />} />
      </Routes>
    </MemoryRouter>
  )
}

describe('AdminDetailPage', () => {
  beforeEach(() => {
    vi.resetAllMocks()
    departmentService.list.mockResolvedValue({ items: DEPARTMENTS, total: 2 })
  })

  it('renders admin fields with resolved department name', async () => {
    adminService.get.mockResolvedValue(makeAdmin())
    renderPage()
    expect(await screen.findByRole('heading', { name: 'Jane Admin' })).toBeInTheDocument()
    expect(await screen.findByText('Finance')).toBeInTheDocument()
  })

  it('renders a generic not-found state for a 404, matching System Admin protection', async () => {
    adminService.get.mockRejectedValue({ status: 404, message: 'Admin not found.', fieldErrors: null })
    renderPage()
    const alert = await screen.findByRole('alert')
    expect(alert).toHaveTextContent('Admin not found.')
    expect(alert.textContent.toLowerCase()).not.toMatch(/system admin|yourself|permission/)
  })

  it('confirms before approving a pending admin', async () => {
    adminService.get.mockResolvedValue(makeAdmin({ status: 'PENDING_APPROVAL' }))
    adminService.approve.mockResolvedValue(makeAdmin({ status: 'ACTIVE' }))
    renderPage()
    await screen.findByRole('heading', { name: 'Jane Admin' })

    await userEvent.click(screen.getByRole('button', { name: /^approve$/i }))
    const dialog = await screen.findByRole('dialog')
    await userEvent.click(within(dialog).getByRole('button', { name: /approve admin/i }))

    await waitFor(() => expect(adminService.approve).toHaveBeenCalledWith('a1'))
  })

  it('shows a 409 when approval fails because the admin is no longer pending (a race)', async () => {
    adminService.get.mockResolvedValue(makeAdmin({ status: 'PENDING_APPROVAL' }))
    adminService.approve.mockRejectedValue({
      status: 409,
      message: 'This Admin is not awaiting approval.',
      fieldErrors: null,
    })
    renderPage()
    await screen.findByRole('heading', { name: 'Jane Admin' })
    await userEvent.click(screen.getByRole('button', { name: /^approve$/i }))
    const dialog = await screen.findByRole('dialog')
    await userEvent.click(within(dialog).getByRole('button', { name: /approve admin/i }))

    expect(await screen.findByRole('alert')).toHaveTextContent(/not awaiting approval/i)
  })

  it('confirms before deactivating, with non-permanent wording, and offers Transfer only while ACTIVE', async () => {
    adminService.get.mockResolvedValue(makeAdmin({ status: 'ACTIVE' }))
    adminService.deactivate.mockResolvedValue(makeAdmin({ status: 'DEACTIVATED' }))
    renderPage()
    await screen.findByRole('heading', { name: 'Jane Admin' })

    expect(screen.getByRole('button', { name: /transfer department/i })).toBeInTheDocument()

    await userEvent.click(screen.getByRole('button', { name: /^deactivate$/i }))
    const dialog = await screen.findByRole('dialog')
    expect(dialog.textContent.toLowerCase()).not.toMatch(/delete|permanent/)
    await userEvent.click(within(dialog).getByRole('button', { name: /deactivate admin/i }))

    await waitFor(() => expect(adminService.deactivate).toHaveBeenCalledWith('a1'))
    await waitFor(() =>
      expect(screen.queryByRole('button', { name: /transfer department/i })).not.toBeInTheDocument()
    )
  })

  it('reactivates without a confirmation dialog', async () => {
    adminService.get.mockResolvedValue(makeAdmin({ status: 'DEACTIVATED' }))
    adminService.reactivate.mockResolvedValue(makeAdmin({ status: 'ACTIVE' }))
    renderPage()
    await screen.findByRole('heading', { name: 'Jane Admin' })

    await userEvent.click(screen.getByRole('button', { name: /^reactivate$/i }))

    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
    await waitFor(() => expect(adminService.reactivate).toHaveBeenCalledWith('a1'))
  })

  it('transfers to a new department, states historical letters are not reassigned, and refreshes the shown department', async () => {
    adminService.get.mockResolvedValue(makeAdmin({ status: 'ACTIVE', department_id: 'd1' }))
    adminService.changeDepartment.mockResolvedValue(makeAdmin({ status: 'ACTIVE', department_id: 'd2' }))
    renderPage()
    await screen.findByRole('heading', { name: 'Jane Admin' })

    await userEvent.click(screen.getByRole('button', { name: /transfer department/i }))
    const dialog = await screen.findByRole('dialog')
    expect(dialog.textContent.toLowerCase()).toMatch(/does not move or reassign any historical record/i)

    await userEvent.selectOptions(within(dialog).getByLabelText(/new department/i), 'd2')
    await userEvent.click(within(dialog).getByRole('button', { name: /transfer admin/i }))

    await waitFor(() =>
      expect(adminService.changeDepartment).toHaveBeenCalledWith('a1', { department_id: 'd2' })
    )
    expect(await screen.findByText('Health')).toBeInTheDocument()
  })

  it('shows a 409 inline in the transfer dialog when the destination is not active', async () => {
    adminService.get.mockResolvedValue(makeAdmin({ status: 'ACTIVE' }))
    adminService.changeDepartment.mockRejectedValue({
      status: 409,
      message: 'The destination department is not ACTIVE.',
      fieldErrors: null,
    })
    renderPage()
    await screen.findByRole('heading', { name: 'Jane Admin' })

    await userEvent.click(screen.getByRole('button', { name: /transfer department/i }))
    const dialog = await screen.findByRole('dialog')
    await userEvent.selectOptions(within(dialog).getByLabelText(/new department/i), 'd2')
    await userEvent.click(within(dialog).getByRole('button', { name: /transfer admin/i }))

    expect(await within(dialog).findByRole('alert')).toHaveTextContent(/not active/i)
    expect(screen.getByRole('dialog')).toBeInTheDocument()
  })
})
