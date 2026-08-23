import { render, screen } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { describe, expect, it, vi } from 'vitest'

import ProtectedRoute from './ProtectedRoute'

const mockUseAuth = vi.fn()
vi.mock('../context/AuthContext', () => ({
  useAuth: () => mockUseAuth(),
}))

function renderProtected(initialPath = '/app') {
  return render(
    <MemoryRouter initialEntries={[initialPath]}>
      <Routes>
        <Route path="/login" element={<div>Login Page</div>} />
        <Route element={<ProtectedRoute />}>
          <Route path="/app" element={<div>App Content</div>} />
        </Route>
      </Routes>
    </MemoryRouter>
  )
}

describe('ProtectedRoute', () => {
  it('renders a loading state while the session is being restored, never the protected content', () => {
    mockUseAuth.mockReturnValue({ status: 'loading' })

    renderProtected()

    expect(screen.getByRole('status')).toBeInTheDocument()
    expect(screen.queryByText('App Content')).not.toBeInTheDocument()
  })

  it('redirects to /login when unauthenticated', () => {
    mockUseAuth.mockReturnValue({ status: 'unauthenticated' })

    renderProtected()

    expect(screen.getByText('Login Page')).toBeInTheDocument()
    expect(screen.queryByText('App Content')).not.toBeInTheDocument()
  })

  it('renders the protected content once authenticated', () => {
    mockUseAuth.mockReturnValue({ status: 'authenticated' })

    renderProtected()

    expect(screen.getByText('App Content')).toBeInTheDocument()
  })
})
