import { render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

/**
 * Exercises the Phase 5I.5 boot gate in `App.jsx` itself, not the real
 * route tree — `routes/index.jsx` and every page it imports are
 * already covered by each page's own tests and by
 * `routes/routing.test.jsx`; duplicating that here would only make
 * this test heavier and more fragile. `../routes`'s real
 * `createBrowserRouter` export is replaced with a tiny
 * `createMemoryRouter` stand-in so this test never touches the actual
 * browser history, while `AuthContext`'s real timing (via the same
 * `authService`/`tokenStorage` mocks every other auth test uses)
 * drives the one thing this file actually needs to prove: the boot
 * screen appears only for the genuine `status === 'loading'` window
 * and never reappears afterward.
 */
vi.mock('./services/authService', () => ({
  login: vi.fn(),
  signup: vi.fn(),
  getCurrentUser: vi.fn(),
}))
vi.mock('./services/tokenStorage', () => ({
  getToken: vi.fn(),
  setToken: vi.fn(),
  clearToken: vi.fn(),
}))
vi.mock('./routes', async () => {
  const { createMemoryRouter } = await import('react-router-dom')
  return {
    router: createMemoryRouter([{ path: '*', element: <div>Routed Application</div> }], {
      initialEntries: ['/'],
    }),
  }
})

import App from './App'
import * as authService from './services/authService'
import * as tokenStorage from './services/tokenStorage'

const ACTIVE_USER = {
  id: 'u1',
  full_name: 'Jane User',
  email: 'jane@example.gov',
  role: 'USER',
  department_id: 'd1',
  status: 'ACTIVE',
}

describe('App boot lifecycle', () => {
  beforeEach(() => {
    vi.resetAllMocks()
  })

  it('shows the boot screen only while the session is genuinely being restored, then renders the application', async () => {
    tokenStorage.getToken.mockReturnValue('a-token')
    let resolveUser
    authService.getCurrentUser.mockReturnValue(
      new Promise((resolve) => {
        resolveUser = resolve
      })
    )

    render(<App />)

    expect(screen.getByRole('status')).toHaveTextContent('Loading Letter Registry System')
    expect(screen.queryByText('Routed Application')).not.toBeInTheDocument()

    resolveUser(ACTIVE_USER)

    await waitFor(() => expect(screen.getByText('Routed Application')).toBeInTheDocument())
    expect(screen.queryByText('Loading Letter Registry System')).not.toBeInTheDocument()
  })

  it('renders the application once an unauthenticated session resolves, with no artificial delay', async () => {
    tokenStorage.getToken.mockReturnValue(null)

    render(<App />)

    await waitFor(() => expect(screen.getByText('Routed Application')).toBeInTheDocument())
    expect(authService.getCurrentUser).not.toHaveBeenCalled()
  })

  it('never shows the boot screen again once initialization has completed', async () => {
    tokenStorage.getToken.mockReturnValue(null)

    render(<App />)

    await waitFor(() => expect(screen.getByText('Routed Application')).toBeInTheDocument())
    expect(screen.queryByRole('status')).not.toBeInTheDocument()
  })
})
