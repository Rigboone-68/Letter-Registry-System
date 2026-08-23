import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { AuthProvider } from '../context/AuthContext'
import LoginPage from './LoginPage'

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

function renderLoginPage() {
  return render(
    <MemoryRouter initialEntries={['/login']}>
      <AuthProvider>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/app" element={<div>App Home</div>} />
        </Routes>
      </AuthProvider>
    </MemoryRouter>
  )
}

async function fillAndSubmit(email, password) {
  await userEvent.type(screen.getByLabelText(/email/i), email)
  await userEvent.type(screen.getByLabelText(/^password/i), password)
  await userEvent.click(screen.getByRole('button', { name: /sign in/i }))
}

describe('LoginPage', () => {
  beforeEach(() => {
    vi.resetAllMocks()
    tokenStorage.getToken.mockReturnValue(null)
  })

  it('requires email and password before calling the API', async () => {
    renderLoginPage()
    await waitFor(() => expect(screen.getByRole('button', { name: /sign in/i })).toBeInTheDocument())

    await userEvent.click(screen.getByRole('button', { name: /sign in/i }))

    expect(await screen.findByText(/email is required/i)).toBeInTheDocument()
    expect(screen.getByText(/password is required/i)).toBeInTheDocument()
    expect(authService.login).not.toHaveBeenCalled()
  })

  it('marks invalid fields with aria-invalid and associates the error text via aria-describedby', async () => {
    renderLoginPage()
    await userEvent.click(screen.getByRole('button', { name: /sign in/i }))

    const emailInput = await screen.findByLabelText(/email/i)
    await waitFor(() => expect(emailInput).toHaveAttribute('aria-invalid', 'true'))
    const describedBy = emailInput.getAttribute('aria-describedby')
    expect(describedBy).toBeTruthy()
    expect(document.getElementById(describedBy)).toHaveTextContent(/email is required/i)
  })

  it('logs in successfully and navigates into the protected app', async () => {
    authService.login.mockResolvedValue({ access_token: 'tok', user: ACTIVE_USER })
    renderLoginPage()

    await fillAndSubmit('jane@example.gov', 'correct-password')

    await waitFor(() => expect(screen.getByText('App Home')).toBeInTheDocument())
    expect(tokenStorage.setToken).toHaveBeenCalledWith('tok')
  })

  it('shows a generic error for invalid credentials, never distinguishing account existence', async () => {
    authService.login.mockRejectedValue({ status: 401, message: 'Incorrect email or password.', fieldErrors: null })
    renderLoginPage()

    await fillAndSubmit('jane@example.gov', 'wrong-password')

    expect(await screen.findByRole('alert')).toHaveTextContent('Incorrect email or password.')
  })

  it('shows the pending-approval notice instead of a generic error for a pending account', async () => {
    authService.login.mockRejectedValue({
      status: 403,
      message: 'Your account is awaiting administrator approval.',
      fieldErrors: null,
    })
    renderLoginPage()

    await fillAndSubmit('jane@example.gov', 'password123')

    expect(await screen.findByText(/pending approval/i)).toBeInTheDocument()
    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
  })

  it('shows the deactivated-account notice instead of a generic error for a deactivated account', async () => {
    authService.login.mockRejectedValue({
      status: 403,
      message: 'Your account has been deactivated.',
      fieldErrors: null,
    })
    renderLoginPage()

    await fillAndSubmit('jane@example.gov', 'password123')

    expect(await screen.findByText(/account deactivated/i)).toBeInTheDocument()
  })

  it('shows a network-failure message distinct from a credentials error', async () => {
    authService.login.mockRejectedValue({
      status: 0,
      message: 'Unable to reach the server. Check your connection and try again.',
      fieldErrors: null,
    })
    renderLoginPage()

    await fillAndSubmit('jane@example.gov', 'password123')

    expect(await screen.findByRole('alert')).toHaveTextContent(/reach the server/i)
  })

  it('disables the submit button and shows a loading label while the request is in flight', async () => {
    let resolveLogin
    authService.login.mockReturnValue(
      new Promise((resolve) => {
        resolveLogin = resolve
      })
    )
    renderLoginPage()

    await userEvent.type(screen.getByLabelText(/email/i), 'jane@example.gov')
    await userEvent.type(screen.getByLabelText(/^password/i), 'password123')
    await userEvent.click(screen.getByRole('button', { name: /sign in/i }))

    expect(screen.getByRole('button', { name: /signing in/i })).toBeDisabled()
    resolveLogin({ access_token: 'tok', user: ACTIVE_USER })
  })

  it('redirects an already-authenticated user straight into the app', async () => {
    tokenStorage.getToken.mockReturnValue('existing-token')
    authService.getCurrentUser.mockResolvedValue(ACTIVE_USER)
    renderLoginPage()

    await waitFor(() => expect(screen.getByText('App Home')).toBeInTheDocument())
  })

  it('clears a previous error once a new submission begins', async () => {
    authService.login
      .mockRejectedValueOnce({ status: 401, message: 'Incorrect email or password.', fieldErrors: null })
      .mockResolvedValueOnce({ access_token: 'tok', user: ACTIVE_USER })
    renderLoginPage()

    await fillAndSubmit('jane@example.gov', 'wrong')
    expect(await screen.findByRole('alert')).toBeInTheDocument()

    await userEvent.clear(screen.getByLabelText(/^password/i))
    await userEvent.type(screen.getByLabelText(/^password/i), 'correct-password')
    await userEvent.click(screen.getByRole('button', { name: /sign in/i }))

    await waitFor(() => expect(screen.queryByRole('alert')).not.toBeInTheDocument())
  })

  it('shows a retryable banner, not a fresh-login demand, when session restoration fails due to a network error', async () => {
    tokenStorage.getToken.mockReturnValue('existing-token')
    authService.getCurrentUser.mockRejectedValueOnce({
      status: 0,
      message: 'Unable to reach the server. Check your connection and try again.',
      fieldErrors: null,
    })
    renderLoginPage()

    expect(await screen.findByText(/unable to verify your session/i)).toBeInTheDocument()
    expect(tokenStorage.clearToken).not.toHaveBeenCalled()
    expect(screen.getByRole('button', { name: /sign in/i })).toBeInTheDocument()
  })
})
