import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import UserAuthorizationsPage from './UserAuthorizationsPage'

vi.mock('../services/userService', () => ({ listAuthorizations: vi.fn(), revokeAuthorization: vi.fn() }))

import * as userService from '../services/userService'

function makeAuthorization(overrides = {}) {
  return { id: 'auth1', email: 'candidate@example.gov', department_id: 'd1', status: 'ACTIVE', created_at: '2026-01-01T00:00:00Z', expires_at: null, ...overrides }
}

function renderPage() {
  return render(
    <MemoryRouter initialEntries={['/app/admin/users/authorizations']}>
      <Routes>
        <Route path="/app/admin/users" element={<div>User List</div>} />
        <Route path="/app/admin/users/authorizations" element={<UserAuthorizationsPage />} />
      </Routes>
    </MemoryRouter>
  )
}

describe('UserAuthorizationsPage', () => {
  beforeEach(() => vi.resetAllMocks())

  it('defaults to filtering by ACTIVE status', async () => {
    userService.listAuthorizations.mockResolvedValue({ items: [], total: 0 })
    renderPage()
    await waitFor(() => expect(userService.listAuthorizations).toHaveBeenCalledWith({ status: 'ACTIVE' }))
  })

  it('renders a successful list', async () => {
    userService.listAuthorizations.mockResolvedValue({ items: [makeAuthorization()], total: 1 })
    renderPage()
    expect(await screen.findByText('candidate@example.gov')).toBeInTheDocument()
  })

  it('widening the filter to All re-requests without a status parameter', async () => {
    userService.listAuthorizations.mockResolvedValue({ items: [], total: 0 })
    renderPage()
    await waitFor(() => expect(userService.listAuthorizations).toHaveBeenCalledWith({ status: 'ACTIVE' }))

    await userEvent.selectOptions(screen.getByLabelText(/status/i), '')

    await waitFor(() => expect(userService.listAuthorizations).toHaveBeenLastCalledWith({}))
  })

  it('shows Revoke only for ACTIVE rows', async () => {
    userService.listAuthorizations.mockResolvedValue({
      items: [makeAuthorization({ id: 'auth2', status: 'REVOKED' })],
      total: 1,
    })
    renderPage()
    await screen.findByText('candidate@example.gov')
    expect(screen.queryByRole('button', { name: /revoke/i })).not.toBeInTheDocument()
  })

  it('revokes with confirmation, stating it cannot be undone, and updates the row in place', async () => {
    userService.listAuthorizations.mockResolvedValue({ items: [makeAuthorization()], total: 1 })
    userService.revokeAuthorization.mockResolvedValue(makeAuthorization({ status: 'REVOKED' }))
    renderPage()
    await screen.findByText('candidate@example.gov')

    await userEvent.click(screen.getByRole('button', { name: /^revoke$/i }))
    const dialog = await screen.findByRole('dialog')
    expect(dialog.textContent.toLowerCase()).toMatch(/cannot be undone/)

    await userEvent.click(within(dialog).getByRole('button', { name: /revoke authorization/i }))

    await waitFor(() => expect(userService.revokeAuthorization).toHaveBeenCalledWith('auth1'))
    await waitFor(() => expect(screen.queryByRole('button', { name: /^revoke$/i })).not.toBeInTheDocument())
  })

  it('shows a 409 when the authorization was already used (a race)', async () => {
    userService.listAuthorizations.mockResolvedValue({ items: [makeAuthorization()], total: 1 })
    userService.revokeAuthorization.mockRejectedValue({
      status: 409,
      message: 'This authorization has already been used and cannot be revoked.',
      fieldErrors: null,
    })
    renderPage()
    await screen.findByText('candidate@example.gov')
    await userEvent.click(screen.getByRole('button', { name: /^revoke$/i }))
    const dialog = await screen.findByRole('dialog')
    await userEvent.click(within(dialog).getByRole('button', { name: /revoke authorization/i }))

    expect(await screen.findByRole('alert')).toHaveTextContent(/already been used/i)
  })
})
