import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import UserDetailPage from './UserDetailPage'

vi.mock('../services/userService', () => ({
  get: vi.fn(),
  approve: vi.fn(),
  deactivate: vi.fn(),
  reactivate: vi.fn(),
}))

import * as userService from '../services/userService'

function makeUser(overrides = {}) {
  return {
    id: 'u1',
    full_name: 'Sam User',
    email: 'sam@example.gov',
    role: 'USER',
    department_id: 'd1',
    status: 'ACTIVE',
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
    ...overrides,
  }
}

function renderPage(id = 'u1') {
  return render(
    <MemoryRouter initialEntries={[`/app/admin/users/${id}`]}>
      <Routes>
        <Route path="/app/admin/users" element={<div>User List</div>} />
        <Route path="/app/admin/users/:id" element={<UserDetailPage />} />
      </Routes>
    </MemoryRouter>
  )
}

describe('UserDetailPage', () => {
  beforeEach(() => vi.resetAllMocks())

  it('renders user fields', async () => {
    userService.get.mockResolvedValue(makeUser())
    renderPage()
    expect(await screen.findByRole('heading', { name: 'Sam User' })).toBeInTheDocument()
    expect(screen.getByText('sam@example.gov')).toBeInTheDocument()
  })

  it('renders a generic not-found state for a 404 — never distinguishing cross-department existence', async () => {
    userService.get.mockRejectedValue({ status: 404, message: 'User not found.', fieldErrors: null })
    renderPage()
    const alert = await screen.findByRole('alert')
    expect(alert).toHaveTextContent('User not found.')
    expect(alert.textContent.toLowerCase()).not.toMatch(/department|admin/)
  })

  it('confirms before approving', async () => {
    userService.get.mockResolvedValue(makeUser({ status: 'PENDING_APPROVAL' }))
    userService.approve.mockResolvedValue(makeUser({ status: 'ACTIVE' }))
    renderPage()
    await screen.findByRole('heading', { name: 'Sam User' })

    await userEvent.click(screen.getByRole('button', { name: /^approve$/i }))
    const dialog = await screen.findByRole('dialog')
    await userEvent.click(within(dialog).getByRole('button', { name: /approve user/i }))

    await waitFor(() => expect(userService.approve).toHaveBeenCalledWith('u1'))
  })

  it('phrases a 403 on approve around the Admin\'s own department, not the target user', async () => {
    userService.get.mockResolvedValue(makeUser({ status: 'PENDING_APPROVAL' }))
    userService.approve.mockRejectedValue({
      status: 403,
      message: 'You do not have permission to perform this action.',
      fieldErrors: null,
    })
    renderPage()
    await screen.findByRole('heading', { name: 'Sam User' })
    await userEvent.click(screen.getByRole('button', { name: /^approve$/i }))
    const dialog = await screen.findByRole('dialog')
    await userEvent.click(within(dialog).getByRole('button', { name: /approve user/i }))

    expect(await screen.findByRole('alert')).toHaveTextContent(/your department is not active/i)
  })

  it('confirms before deactivating, with non-permanent wording', async () => {
    userService.get.mockResolvedValue(makeUser({ status: 'ACTIVE' }))
    userService.deactivate.mockResolvedValue(makeUser({ status: 'DEACTIVATED' }))
    renderPage()
    await screen.findByRole('heading', { name: 'Sam User' })

    await userEvent.click(screen.getByRole('button', { name: /^deactivate$/i }))
    const dialog = await screen.findByRole('dialog')
    expect(dialog.textContent.toLowerCase()).not.toMatch(/delete|permanent/)
    await userEvent.click(within(dialog).getByRole('button', { name: /deactivate user/i }))

    await waitFor(() => expect(userService.deactivate).toHaveBeenCalledWith('u1'))
  })

  it('reactivates without a confirmation dialog', async () => {
    userService.get.mockResolvedValue(makeUser({ status: 'DEACTIVATED' }))
    userService.reactivate.mockResolvedValue(makeUser({ status: 'ACTIVE' }))
    renderPage()
    await screen.findByRole('heading', { name: 'Sam User' })

    await userEvent.click(screen.getByRole('button', { name: /^reactivate$/i }))

    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
    await waitFor(() => expect(userService.reactivate).toHaveBeenCalledWith('u1'))
  })
})
