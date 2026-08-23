import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { AuthProvider } from '../context/AuthContext'
import AppShell from '../layouts/AppShell'
import LoginPage from '../pages/LoginPage'
import ProtectedRoute from './ProtectedRoute'

vi.mock('../services/authService', async () => {
  const actual = await vi.importActual('../services/authService')
  return {
    ...actual,
    login: vi.fn(),
    signup: vi.fn(),
    getCurrentUser: vi.fn(),
  }
})
vi.mock('../services/tokenStorage', () => ({
  getToken: vi.fn(),
  setToken: vi.fn(),
  clearToken: vi.fn(),
}))

import * as authService from '../services/authService'
import * as tokenStorage from '../services/tokenStorage'

const ACTIVE_USER = {
  id: 'u1',
  full_name: 'Jane User',
  email: 'jane@example.gov',
  role: 'USER',
  department_id: 'd1',
  status: 'ACTIVE',
}

/**
 * A minimal stand-in for the real route tree (routes/index.jsx) — enough
 * to exercise the real ProtectedRoute + AppShell + Topbar + AuthProvider
 * wiring end-to-end without depending on `createBrowserRouter`'s history,
 * which isn't practical to seed with an initial path in a test.
 */
function TestApp() {
  return (
    <AuthProvider>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/app" element={<ProtectedRoute />}>
          <Route element={<AppShell />}>
            <Route index element={<div>Protected Home</div>} />
          </Route>
        </Route>
      </Routes>
    </AuthProvider>
  )
}

describe('routing: logout', () => {
  beforeEach(() => vi.resetAllMocks())

  it('clears the session and redirects to /login when the user clicks Log out', async () => {
    tokenStorage.getToken.mockReturnValue('a-token')
    authService.getCurrentUser.mockResolvedValue(ACTIVE_USER)

    render(
      <MemoryRouter initialEntries={['/app']}>
        <TestApp />
      </MemoryRouter>
    )

    await waitFor(() => expect(screen.getByText('Protected Home')).toBeInTheDocument())

    await userEvent.click(screen.getByRole('button', { name: /log out/i }))

    await waitFor(() => expect(screen.getByRole('heading', { name: /sign in/i })).toBeInTheDocument())
    expect(tokenStorage.clearToken).toHaveBeenCalled()
    expect(screen.queryByText('Protected Home')).not.toBeInTheDocument()
  })
})
