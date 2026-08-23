import { render, screen } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { describe, expect, it, vi } from 'vitest'

import RoleGuard from './RoleGuard'

const mockUseAuth = vi.fn()
vi.mock('../context/AuthContext', () => ({
  useAuth: () => mockUseAuth(),
}))

describe('RoleGuard', () => {
  it('renders children directly when the role matches', () => {
    mockUseAuth.mockReturnValue({ user: { role: 'SYSTEM_ADMIN' } })
    render(
      <MemoryRouter initialEntries={['/app/departments']}>
        <Routes>
          <Route
            path="/app/departments"
            element={
              <RoleGuard allowedRoles={['SYSTEM_ADMIN']}>
                <div>Departments</div>
              </RoleGuard>
            }
          />
        </Routes>
      </MemoryRouter>
    )
    expect(screen.getByText('Departments')).toBeInTheDocument()
  })

  it('redirects to /app when the role does not match (children mode)', () => {
    mockUseAuth.mockReturnValue({ user: { role: 'USER' } })
    render(
      <MemoryRouter initialEntries={['/app/departments']}>
        <Routes>
          <Route path="/app" element={<div>App Home</div>} />
          <Route
            path="/app/departments"
            element={
              <RoleGuard allowedRoles={['SYSTEM_ADMIN']}>
                <div>Departments</div>
              </RoleGuard>
            }
          />
        </Routes>
      </MemoryRouter>
    )
    expect(screen.getByText('App Home')).toBeInTheDocument()
    expect(screen.queryByText('Departments')).not.toBeInTheDocument()
  })

  it('renders nested child routes via Outlet when used as a layout route (no children prop)', () => {
    mockUseAuth.mockReturnValue({ user: { role: 'SYSTEM_ADMIN' } })
    render(
      <MemoryRouter initialEntries={['/app/system/admins/authorize']}>
        <Routes>
          <Route path="/app/system/admins" element={<RoleGuard allowedRoles={['SYSTEM_ADMIN']} />}>
            <Route index element={<div>Admin List</div>} />
            <Route path="authorize" element={<div>Authorize Admin</div>} />
          </Route>
        </Routes>
      </MemoryRouter>
    )
    expect(screen.getByText('Authorize Admin')).toBeInTheDocument()
    expect(screen.queryByText('Admin List')).not.toBeInTheDocument()
  })

  it('redirects to /app for a mismatched role before any nested route renders', () => {
    mockUseAuth.mockReturnValue({ user: { role: 'ADMIN' } })
    render(
      <MemoryRouter initialEntries={['/app/system/admins/authorize']}>
        <Routes>
          <Route path="/app" element={<div>App Home</div>} />
          <Route path="/app/system/admins" element={<RoleGuard allowedRoles={['SYSTEM_ADMIN']} />}>
            <Route index element={<div>Admin List</div>} />
            <Route path="authorize" element={<div>Authorize Admin</div>} />
          </Route>
        </Routes>
      </MemoryRouter>
    )
    expect(screen.getByText('App Home')).toBeInTheDocument()
    expect(screen.queryByText('Authorize Admin')).not.toBeInTheDocument()
  })

  it('redirects when there is no authenticated user at all', () => {
    mockUseAuth.mockReturnValue({ user: null })
    render(
      <MemoryRouter initialEntries={['/app/departments']}>
        <Routes>
          <Route path="/app" element={<div>App Home</div>} />
          <Route
            path="/app/departments"
            element={
              <RoleGuard allowedRoles={['SYSTEM_ADMIN']}>
                <div>Departments</div>
              </RoleGuard>
            }
          />
        </Routes>
      </MemoryRouter>
    )
    expect(screen.getByText('App Home')).toBeInTheDocument()
  })
})
