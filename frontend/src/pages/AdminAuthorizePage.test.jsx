import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import AdminAuthorizePage from './AdminAuthorizePage'

vi.mock('../services/adminService', () => ({ authorize: vi.fn() }))
vi.mock('../services/departmentService', () => ({ list: vi.fn() }))

import * as adminService from '../services/adminService'
import * as departmentService from '../services/departmentService'

function renderPage() {
  return render(
    <MemoryRouter initialEntries={['/app/system/admins/authorize']}>
      <Routes>
        <Route path="/app/system/admins" element={<div>Admin List</div>} />
        <Route path="/app/system/admins/authorize" element={<AdminAuthorizePage />} />
      </Routes>
    </MemoryRouter>
  )
}

describe('AdminAuthorizePage', () => {
  beforeEach(() => {
    vi.resetAllMocks()
    departmentService.list.mockResolvedValue({
      items: [
        { id: 'd1', name: 'Finance', code: 'FIN', status: 'ACTIVE' },
        { id: 'd2', name: 'Legacy Dept', code: null, status: 'INACTIVE' },
      ],
      total: 2,
    })
  })

  it('requires email and department before submitting', async () => {
    renderPage()
    await userEvent.click(await screen.findByRole('button', { name: /authorize admin/i }))
    expect(await screen.findByText(/email is required/i)).toBeInTheDocument()
    expect(screen.getByText(/department is required/i)).toBeInTheDocument()
    expect(adminService.authorize).not.toHaveBeenCalled()
  })

  it('only offers ACTIVE departments as selectable options', async () => {
    renderPage()
    await screen.findByLabelText(/department/i)
    expect(screen.getByRole('option', { name: 'Finance' })).toBeInTheDocument()
    expect(screen.queryByRole('option', { name: /legacy dept/i })).not.toBeInTheDocument()
  })

  it('authorizes successfully and returns to the Administrators list', async () => {
    adminService.authorize.mockResolvedValue({ id: 'auth1', email: 'new@example.gov', department_id: 'd1', status: 'ACTIVE' })
    renderPage()
    await userEvent.type(await screen.findByLabelText(/email/i), 'new@example.gov')
    await userEvent.selectOptions(screen.getByLabelText(/department/i), 'd1')
    await userEvent.click(screen.getByRole('button', { name: /authorize admin/i }))

    await waitFor(() => expect(screen.getByText('Admin List')).toBeInTheDocument())
    expect(adminService.authorize).toHaveBeenCalledWith({ email: 'new@example.gov', department_id: 'd1' })
  })

  it('shows the backend duplicate-authorization conflict', async () => {
    adminService.authorize.mockRejectedValue({
      status: 409,
      message: 'This email already has an unresolved Admin authorization.',
      fieldErrors: null,
    })
    renderPage()
    await userEvent.type(await screen.findByLabelText(/email/i), 'new@example.gov')
    await userEvent.selectOptions(screen.getByLabelText(/department/i), 'd1')
    await userEvent.click(screen.getByRole('button', { name: /authorize admin/i }))
    expect(await screen.findByRole('alert')).toHaveTextContent(/unresolved admin authorization/i)
  })

  it('never sends role or status fields', async () => {
    adminService.authorize.mockResolvedValue({ id: 'auth1', email: 'new@example.gov', department_id: 'd1', status: 'ACTIVE' })
    renderPage()
    await userEvent.type(await screen.findByLabelText(/email/i), 'new@example.gov')
    await userEvent.selectOptions(screen.getByLabelText(/department/i), 'd1')
    await userEvent.click(screen.getByRole('button', { name: /authorize admin/i }))

    await waitFor(() => expect(adminService.authorize).toHaveBeenCalled())
    const payload = adminService.authorize.mock.calls[0][0]
    expect(Object.keys(payload).sort()).toEqual(['department_id', 'email'])
  })

  describe('department selection (manual E2E regression)', () => {
    // Reproduces the exact reported real-world bug: with Finance as the
    // only ACTIVE department, a controlled `<select value="">` with no
    // matching `<option value="">` desynced from the DOM — the browser
    // defaulted to visually showing Finance selected while the form's
    // own `department_id` state stayed empty, so a genuine selection
    // never actually changed anything from the DOM's own point of view.
    beforeEach(() => {
      departmentService.list.mockResolvedValue({
        items: [{ id: 'finance-uuid', name: 'Finance', code: 'FIN', status: 'ACTIVE' }],
        total: 1,
      })
    })

    it('does not silently pre-select Finance before the user chooses anything', async () => {
      renderPage()
      const select = await screen.findByLabelText(/department/i)
      expect(select).toHaveValue('')
      expect(screen.getByRole('option', { name: /select a department/i })).toBeInTheDocument()
    })

    it('selecting the sole Finance department is accepted — no "Department is required." error, and adminService receives the real department_id', async () => {
      adminService.authorize.mockResolvedValue({
        id: 'auth1',
        email: 'new@example.gov',
        department_id: 'finance-uuid',
        status: 'ACTIVE',
      })
      renderPage()

      await userEvent.type(await screen.findByLabelText(/email/i), 'new@example.gov')
      await userEvent.selectOptions(screen.getByLabelText(/department/i), 'finance-uuid')
      expect(screen.getByLabelText(/department/i)).toHaveValue('finance-uuid')

      await userEvent.click(screen.getByRole('button', { name: /authorize admin/i }))

      await waitFor(() => expect(adminService.authorize).toHaveBeenCalled())
      expect(screen.queryByText(/department is required/i)).not.toBeInTheDocument()
      expect(adminService.authorize).toHaveBeenCalledWith({
        email: 'new@example.gov',
        department_id: 'finance-uuid',
      })
    })

    it('still rejects submission with no department selected', async () => {
      renderPage()
      await userEvent.type(await screen.findByLabelText(/email/i), 'new@example.gov')
      await userEvent.click(screen.getByRole('button', { name: /authorize admin/i }))

      expect(await screen.findByText(/department is required/i)).toBeInTheDocument()
      expect(adminService.authorize).not.toHaveBeenCalled()
    })

    it('keeps the selected department across an unrelated re-render (email field edits)', async () => {
      renderPage()
      await userEvent.selectOptions(await screen.findByLabelText(/department/i), 'finance-uuid')
      await userEvent.type(screen.getByLabelText(/email/i), 'new@example.gov')

      expect(screen.getByLabelText(/department/i)).toHaveValue('finance-uuid')
    })
  })
})
