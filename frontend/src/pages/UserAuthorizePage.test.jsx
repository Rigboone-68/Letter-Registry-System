import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import UserAuthorizePage from './UserAuthorizePage'

vi.mock('../services/userService', () => ({ authorize: vi.fn() }))

import * as userService from '../services/userService'

function renderPage() {
  return render(
    <MemoryRouter initialEntries={['/app/admin/users/authorize']}>
      <Routes>
        <Route path="/app/admin/users" element={<div>User List</div>} />
        <Route path="/app/admin/users/authorize" element={<UserAuthorizePage />} />
      </Routes>
    </MemoryRouter>
  )
}

describe('UserAuthorizePage', () => {
  beforeEach(() => vi.resetAllMocks())

  it('has no department field of any kind', () => {
    renderPage()
    expect(screen.queryByLabelText(/department/i)).not.toBeInTheDocument()
    expect(screen.queryByRole('combobox')).not.toBeInTheDocument()
  })

  it('requires email before submitting', async () => {
    renderPage()
    await userEvent.click(screen.getByRole('button', { name: /authorize user/i }))
    expect(await screen.findByText(/email is required/i)).toBeInTheDocument()
    expect(userService.authorize).not.toHaveBeenCalled()
  })

  it('authorizes successfully and returns to the Users list', async () => {
    userService.authorize.mockResolvedValue({ id: 'auth1', email: 'new@example.gov', department_id: 'd1', status: 'ACTIVE' })
    renderPage()
    await userEvent.type(screen.getByLabelText(/email/i), 'new@example.gov')
    await userEvent.click(screen.getByRole('button', { name: /authorize user/i }))

    await waitFor(() => expect(screen.getByText('User List')).toBeInTheDocument())
    expect(userService.authorize).toHaveBeenCalledWith({ email: 'new@example.gov' })
  })

  it('shows the backend own-department-inactive 403', async () => {
    userService.authorize.mockRejectedValue({
      status: 403,
      message: 'You do not have permission to perform this action.',
      fieldErrors: null,
    })
    renderPage()
    await userEvent.type(screen.getByLabelText(/email/i), 'new@example.gov')
    await userEvent.click(screen.getByRole('button', { name: /authorize user/i }))
    expect(await screen.findByRole('alert')).toHaveTextContent(/permission/i)
  })

  it('shows the backend duplicate-user conflict', async () => {
    userService.authorize.mockRejectedValue({
      status: 409,
      message: 'This email already belongs to an active User.',
      fieldErrors: null,
    })
    renderPage()
    await userEvent.type(screen.getByLabelText(/email/i), 'new@example.gov')
    await userEvent.click(screen.getByRole('button', { name: /authorize user/i }))
    expect(await screen.findByRole('alert')).toHaveTextContent(/already belongs to an active user/i)
  })

  it('never sends more than the email field', async () => {
    userService.authorize.mockResolvedValue({ id: 'auth1', email: 'new@example.gov', department_id: 'd1', status: 'ACTIVE' })
    renderPage()
    await userEvent.type(screen.getByLabelText(/email/i), 'new@example.gov')
    await userEvent.click(screen.getByRole('button', { name: /authorize user/i }))

    await waitFor(() => expect(userService.authorize).toHaveBeenCalled())
    const payload = userService.authorize.mock.calls[0][0]
    expect(Object.keys(payload)).toEqual(['email'])
  })
})
