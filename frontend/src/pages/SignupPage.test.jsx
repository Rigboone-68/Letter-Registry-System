import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { AuthProvider } from '../context/AuthContext'
import SignupPage from './SignupPage'

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

function renderSignupPage() {
  return render(
    <MemoryRouter initialEntries={['/signup']}>
      <AuthProvider>
        <Routes>
          <Route path="/signup" element={<SignupPage />} />
          <Route path="/login" element={<div>Login Page</div>} />
          <Route path="/app" element={<div>App Home</div>} />
        </Routes>
      </AuthProvider>
    </MemoryRouter>
  )
}

async function fillForm({ full_name = 'Jane User', email = 'jane@example.gov', password = 'password123', password_confirm = 'password123' } = {}) {
  await userEvent.type(screen.getByLabelText(/full name/i), full_name)
  await userEvent.type(screen.getByLabelText(/^email/i), email)
  await userEvent.type(screen.getByLabelText(/^password$/i), password)
  await userEvent.type(screen.getByLabelText(/confirm password/i), password_confirm)
}

describe('SignupPage', () => {
  beforeEach(() => {
    vi.resetAllMocks()
    tokenStorage.getToken.mockReturnValue(null)
  })

  it('requires every field before calling the API', async () => {
    renderSignupPage()
    await waitFor(() => expect(screen.getByRole('button', { name: /create account/i })).toBeInTheDocument())

    await userEvent.click(screen.getByRole('button', { name: /create account/i }))

    expect(await screen.findByText(/full name is required/i)).toBeInTheDocument()
    expect(screen.getByText(/email is required/i)).toBeInTheDocument()
    expect(screen.getByText(/password is required/i)).toBeInTheDocument()
    expect(authService.signup).not.toHaveBeenCalled()
  })

  it('requires the password confirmation to match', async () => {
    renderSignupPage()
    await fillForm({ password: 'password123', password_confirm: 'different' })
    await userEvent.click(screen.getByRole('button', { name: /create account/i }))

    expect(await screen.findByText(/do not match/i)).toBeInTheDocument()
    expect(authService.signup).not.toHaveBeenCalled()
  })

  it('shows the pending-approval notice after a successful signup, never auto-authenticating', async () => {
    authService.signup.mockResolvedValue({
      id: 'u1',
      full_name: 'Jane User',
      email: 'jane@example.gov',
      role: 'USER',
      department_id: null,
      status: 'PENDING_APPROVAL',
    })
    renderSignupPage()
    await fillForm()
    await userEvent.click(screen.getByRole('button', { name: /create account/i }))

    expect(await screen.findByText(/pending approval/i)).toBeInTheDocument()
    expect(tokenStorage.setToken).not.toHaveBeenCalled()
  })

  it('shows the backend duplicate-account error', async () => {
    authService.signup.mockRejectedValue({
      status: 409,
      message: 'An account with this email already exists.',
      fieldErrors: null,
    })
    renderSignupPage()
    await fillForm()
    await userEvent.click(screen.getByRole('button', { name: /create account/i }))

    expect(await screen.findByRole('alert')).toHaveTextContent(/already exists/i)
  })

  it('shows the backend not-authorized-to-sign-up error', async () => {
    authService.signup.mockRejectedValue({
      status: 403,
      message: 'This email is not authorized to sign up.',
      fieldErrors: null,
    })
    renderSignupPage()
    await fillForm()
    await userEvent.click(screen.getByRole('button', { name: /create account/i }))

    expect(await screen.findByRole('alert')).toHaveTextContent(/not authorized/i)
  })

  it('never sends a role, department, or status field to the backend', async () => {
    authService.signup.mockResolvedValue({
      id: 'u1',
      full_name: 'Jane User',
      email: 'jane@example.gov',
      role: 'USER',
      department_id: null,
      status: 'PENDING_APPROVAL',
    })
    renderSignupPage()
    await fillForm()
    await userEvent.click(screen.getByRole('button', { name: /create account/i }))

    await waitFor(() => expect(authService.signup).toHaveBeenCalled())
    const payload = authService.signup.mock.calls[0][0]
    expect(Object.keys(payload).sort()).toEqual(['email', 'full_name', 'password', 'password_confirm'])
    expect(payload).not.toHaveProperty('role')
    expect(payload).not.toHaveProperty('department_id')
    expect(payload).not.toHaveProperty('status')
  })

  it('redirects an already-authenticated user straight into the app', async () => {
    tokenStorage.getToken.mockReturnValue('existing-token')
    authService.getCurrentUser.mockResolvedValue({
      id: 'u1',
      full_name: 'Jane User',
      email: 'jane@example.gov',
      role: 'USER',
      department_id: 'd1',
      status: 'ACTIVE',
    })
    renderSignupPage()

    await waitFor(() => expect(screen.getByText('App Home')).toBeInTheDocument())
  })
})
