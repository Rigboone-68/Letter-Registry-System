import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it } from 'vitest'

import QuickActions from './QuickActions'

function renderWithRouter(role) {
  return render(
    <MemoryRouter>
      <QuickActions role={role} />
    </MemoryRouter>
  )
}

describe('QuickActions', () => {
  it('shows only SYSTEM_ADMIN actions for SYSTEM_ADMIN, pointing at existing routes', () => {
    renderWithRouter('SYSTEM_ADMIN')

    expect(screen.getByRole('link', { name: 'Create Department' })).toHaveAttribute(
      'href',
      '/app/system/departments/new'
    )
    expect(screen.getByRole('link', { name: 'Authorize Admin' })).toHaveAttribute(
      'href',
      '/app/system/admins/authorize'
    )
    expect(screen.queryByRole('link', { name: 'Authorize User' })).not.toBeInTheDocument()
    expect(screen.queryByRole('link', { name: 'Record a Letter' })).not.toBeInTheDocument()
  })

  it('shows only the ADMIN action for ADMIN', () => {
    renderWithRouter('ADMIN')

    expect(screen.getByRole('link', { name: 'Authorize User' })).toHaveAttribute(
      'href',
      '/app/admin/users/authorize'
    )
    expect(screen.queryByRole('link', { name: 'Create Department' })).not.toBeInTheDocument()
  })

  it('shows only the USER action for USER', () => {
    renderWithRouter('USER')

    expect(screen.getByRole('link', { name: 'Record a Letter' })).toHaveAttribute('href', '/app/letters/new')
    expect(screen.queryByRole('link', { name: 'Authorize User' })).not.toBeInTheDocument()
  })

  it('never renders an action for an operation the role cannot perform', () => {
    renderWithRouter('USER')
    expect(screen.queryByRole('link', { name: 'Create Department' })).not.toBeInTheDocument()
    expect(screen.queryByRole('link', { name: 'Authorize Admin' })).not.toBeInTheDocument()
    expect(screen.queryByRole('link', { name: 'Authorize User' })).not.toBeInTheDocument()
  })

  it('renders nothing for an unknown role rather than throwing', () => {
    const { container } = renderWithRouter(undefined)
    expect(container).toBeEmptyDOMElement()
  })
})
