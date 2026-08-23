import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { AuthProvider, useAuth } from './AuthContext'

vi.mock('../services/authService', () => ({
  login: vi.fn(),
  signup: vi.fn(),
  getCurrentUser: vi.fn(),
}))
vi.mock('../services/tokenStorage', () => ({
  getToken: vi.fn(),
  setToken: vi.fn(),
  clearToken: vi.fn(),
}))

import * as authService from '../services/authService'
import * as tokenStorage from '../services/tokenStorage'

function Consumer() {
  const { status, user, restoreError, login, logout, retryRestoreSession } = useAuth()
  return (
    <div>
      <span data-testid="status">{status}</span>
      <span data-testid="user">{user ? user.full_name : ''}</span>
      <span data-testid="restoreError">{restoreError ?? ''}</span>
      <button onClick={() => login('user@example.gov', 'password')}>login</button>
      <button onClick={logout}>logout</button>
      <button onClick={retryRestoreSession}>retry</button>
    </div>
  )
}

const ACTIVE_USER = {
  id: 'u1',
  full_name: 'Jane Admin',
  email: 'jane@example.gov',
  role: 'ADMIN',
  department_id: 'd1',
  status: 'ACTIVE',
}

describe('AuthProvider', () => {
  beforeEach(() => {
    vi.resetAllMocks()
  })

  it('starts unauthenticated when no token is stored, without calling /auth/me', async () => {
    tokenStorage.getToken.mockReturnValue(null)

    render(
      <AuthProvider>
        <Consumer />
      </AuthProvider>
    )

    await waitFor(() => expect(screen.getByTestId('status').textContent).toBe('unauthenticated'))
    expect(authService.getCurrentUser).not.toHaveBeenCalled()
  })

  it('restores an authenticated session when a stored token is still valid', async () => {
    tokenStorage.getToken.mockReturnValue('a-valid-token')
    authService.getCurrentUser.mockResolvedValue(ACTIVE_USER)

    render(
      <AuthProvider>
        <Consumer />
      </AuthProvider>
    )

    await waitFor(() => expect(screen.getByTestId('status').textContent).toBe('authenticated'))
    expect(screen.getByTestId('user').textContent).toBe('Jane Admin')
  })

  it('clears the session when the stored token is no longer valid', async () => {
    tokenStorage.getToken.mockReturnValue('a-stale-token')
    authService.getCurrentUser.mockRejectedValue({ status: 401, message: 'Could not validate credentials.' })

    render(
      <AuthProvider>
        <Consumer />
      </AuthProvider>
    )

    await waitFor(() => expect(screen.getByTestId('status').textContent).toBe('unauthenticated'))
    expect(tokenStorage.clearToken).toHaveBeenCalled()
  })

  it('transitions loading → unauthenticated → authenticated after a successful login', async () => {
    tokenStorage.getToken.mockReturnValue(null)
    authService.login.mockResolvedValue({ access_token: 'fresh-token', user: ACTIVE_USER })

    render(
      <AuthProvider>
        <Consumer />
      </AuthProvider>
    )

    await waitFor(() => expect(screen.getByTestId('status').textContent).toBe('unauthenticated'))

    await userEvent.click(screen.getByText('login'))

    await waitFor(() => expect(screen.getByTestId('status').textContent).toBe('authenticated'))
    expect(tokenStorage.setToken).toHaveBeenCalledWith('fresh-token')
    expect(screen.getByTestId('user').textContent).toBe('Jane Admin')
  })

  it('does not clear the stored token on a network failure during restoration, and reports a retryable error', async () => {
    tokenStorage.getToken.mockReturnValue('a-token')
    authService.getCurrentUser.mockRejectedValue({
      status: 0,
      message: 'Unable to reach the server. Check your connection and try again.',
      fieldErrors: null,
    })

    render(
      <AuthProvider>
        <Consumer />
      </AuthProvider>
    )

    await waitFor(() => expect(screen.getByTestId('status').textContent).toBe('unauthenticated'))
    expect(tokenStorage.clearToken).not.toHaveBeenCalled()
    expect(screen.getByTestId('restoreError').textContent).toMatch(/unable to verify your session/i)
  })

  it('retrying a failed restoration can succeed once the server is reachable again', async () => {
    tokenStorage.getToken.mockReturnValue('a-token')
    authService.getCurrentUser
      .mockRejectedValueOnce({ status: 0, message: 'Unable to reach the server.', fieldErrors: null })
      .mockResolvedValueOnce(ACTIVE_USER)

    render(
      <AuthProvider>
        <Consumer />
      </AuthProvider>
    )

    await waitFor(() => expect(screen.getByTestId('restoreError').textContent).not.toBe(''))

    await userEvent.click(screen.getByText('retry'))

    await waitFor(() => expect(screen.getByTestId('status').textContent).toBe('authenticated'))
    expect(screen.getByTestId('restoreError').textContent).toBe('')
  })

  it('clears the session on logout, with no server-side revocation call', async () => {
    tokenStorage.getToken.mockReturnValue('a-valid-token')
    authService.getCurrentUser.mockResolvedValue(ACTIVE_USER)

    render(
      <AuthProvider>
        <Consumer />
      </AuthProvider>
    )

    await waitFor(() => expect(screen.getByTestId('status').textContent).toBe('authenticated'))

    await userEvent.click(screen.getByText('logout'))

    await waitFor(() => expect(screen.getByTestId('status').textContent).toBe('unauthenticated'))
    expect(tokenStorage.clearToken).toHaveBeenCalled()
    expect(screen.getByTestId('user').textContent).toBe('')
  })
})
