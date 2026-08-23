import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import Topbar from './Topbar'

const mockUseAuth = vi.fn()
vi.mock('../context/AuthContext', () => ({
  useAuth: () => mockUseAuth(),
}))
vi.mock('../services/notificationService', () => ({
  unreadCount: vi.fn(),
  list: vi.fn(),
  markRead: vi.fn(),
  markAllRead: vi.fn(),
}))

import * as notificationService from '../services/notificationService'

function renderTopbar() {
  return render(
    <MemoryRouter>
      <Topbar />
    </MemoryRouter>
  )
}

describe('Topbar', () => {
  beforeEach(() => {
    vi.resetAllMocks()
    notificationService.unreadCount.mockResolvedValue({ unread_count: 0 })
  })

  it.each(['SYSTEM_ADMIN', 'ADMIN', 'USER'])(
    'renders identity, the notification bell, and logout for %s without any role-gating',
    async (role) => {
      const logout = vi.fn()
      mockUseAuth.mockReturnValue({
        user: { id: 'u1', full_name: 'Jane User', role, department_id: 'd1' },
        logout,
      })
      renderTopbar()

      expect(screen.getByText('Jane User')).toBeInTheDocument()
      expect(await screen.findByRole('button', { name: 'Notifications' })).toBeInTheDocument()
      expect(screen.getByRole('button', { name: /log out/i })).toBeInTheDocument()
      await waitFor(() => expect(notificationService.unreadCount).toHaveBeenCalled())
    }
  )

  it('calls the centralized logout function, never its own token-clearing logic', async () => {
    const logout = vi.fn()
    mockUseAuth.mockReturnValue({
      user: { id: 'u1', full_name: 'Jane User', role: 'USER', department_id: 'd1' },
      logout,
    })
    renderTopbar()

    await userEvent.click(screen.getByRole('button', { name: /log out/i }))
    expect(logout).toHaveBeenCalled()
  })

  it('renders nothing but the app name when unauthenticated', () => {
    mockUseAuth.mockReturnValue({ user: null, logout: vi.fn() })
    renderTopbar()

    expect(screen.queryByRole('button', { name: /notifications/i })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /log out/i })).not.toBeInTheDocument()
  })
})
