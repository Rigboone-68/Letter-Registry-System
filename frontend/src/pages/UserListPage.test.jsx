import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import UserListPage from './UserListPage'

vi.mock('../services/userService', () => ({ list: vi.fn() }))

import * as userService from '../services/userService'

function renderPage() {
  return render(
    <MemoryRouter initialEntries={['/app/admin/users']}>
      <Routes>
        <Route path="/app/admin/users" element={<UserListPage />} />
      </Routes>
    </MemoryRouter>
  )
}

describe('UserListPage', () => {
  beforeEach(() => vi.resetAllMocks())

  it('renders a successful list, with no department column', async () => {
    userService.list.mockResolvedValue({
      items: [{ id: 'u1', full_name: 'Sam User', email: 'sam@example.gov', role: 'USER', department_id: 'd1', status: 'ACTIVE' }],
      total: 1,
    })
    renderPage()
    expect(await screen.findByText('Sam User')).toBeInTheDocument()
    expect(screen.queryByRole('columnheader', { name: /department/i })).not.toBeInTheDocument()
  })

  it('shows an empty state when there are no results', async () => {
    userService.list.mockResolvedValue({ items: [], total: 0 })
    renderPage()
    expect(await screen.findByText(/no users match/i)).toBeInTheDocument()
  })

  it('shows an error state on API failure', async () => {
    userService.list.mockRejectedValue({ status: 0, message: 'Unable to reach the server.', fieldErrors: null })
    renderPage()
    expect(await screen.findByRole('alert')).toHaveTextContent(/reach the server/i)
  })

  it('re-requests with the status filter only (no department parameter)', async () => {
    userService.list.mockResolvedValue({ items: [], total: 0 })
    renderPage()
    await waitFor(() => expect(userService.list).toHaveBeenCalledWith({}))

    await userEvent.selectOptions(screen.getByLabelText(/status/i), 'DEACTIVATED')

    await waitFor(() => expect(userService.list).toHaveBeenLastCalledWith({ status: 'DEACTIVATED' }))
  })

  it('links to Authorize and Authorizations', async () => {
    userService.list.mockResolvedValue({ items: [], total: 0 })
    renderPage()
    expect(await screen.findByRole('link', { name: /authorize new user/i })).toHaveAttribute(
      'href',
      '/app/admin/users/authorize'
    )
    expect(screen.getByRole('link', { name: /^authorizations$/i })).toHaveAttribute(
      'href',
      '/app/admin/users/authorizations'
    )
  })
})
