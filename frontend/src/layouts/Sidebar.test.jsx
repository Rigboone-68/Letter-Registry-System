import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { describe, expect, it, vi } from 'vitest'

import Sidebar from './Sidebar'

const mockUseAuth = vi.fn()
vi.mock('../context/AuthContext', () => ({
  useAuth: () => mockUseAuth(),
}))

function renderSidebar({ role = 'USER', initialEntry = '/app/dashboard', ...props } = {}) {
  mockUseAuth.mockReturnValue({ user: { role } })
  return render(
    <MemoryRouter initialEntries={[initialEntry]}>
      <Routes>
        <Route
          path="*"
          element={
            <>
              <Sidebar {...props} />
              <div>Page content</div>
            </>
          }
        />
      </Routes>
    </MemoryRouter>
  )
}

describe('Sidebar', () => {
  it('renders the full role-derived navigation set for SYSTEM_ADMIN', () => {
    renderSidebar({ role: 'SYSTEM_ADMIN' })
    for (const label of ['Dashboard', 'Letters', 'Departments', 'Administrators', 'Categories', 'Classifications']) {
      expect(screen.getByRole('link', { name: new RegExp(label) })).toBeInTheDocument()
    }
  })

  it('excludes administrative items for USER', () => {
    renderSidebar({ role: 'USER' })
    expect(screen.getByRole('link', { name: /dashboard/i })).toBeInTheDocument()
    expect(screen.queryByRole('link', { name: /departments/i })).not.toBeInTheDocument()
    expect(screen.queryByRole('link', { name: /administrators/i })).not.toBeInTheDocument()
  })

  it('marks the active route with aria-current, and only the active route', () => {
    renderSidebar({ role: 'USER', initialEntry: '/app/dashboard' })
    expect(screen.getByRole('link', { name: /dashboard/i })).toHaveAttribute('aria-current', 'page')
    expect(screen.getByRole('link', { name: /^letters/i })).not.toHaveAttribute('aria-current')
  })

  it('toggles collapsed state and flips aria-expanded on the collapse control', async () => {
    renderSidebar()
    const toggle = screen.getByRole('button', { name: /collapse navigation/i })
    expect(toggle).toHaveAttribute('aria-expanded', 'true')

    await userEvent.click(toggle)

    expect(screen.getByRole('button', { name: /expand navigation/i })).toHaveAttribute('aria-expanded', 'false')
  })

  it('keeps every navigation link with its full accessible name while collapsed', async () => {
    renderSidebar()
    await userEvent.click(screen.getByRole('button', { name: /collapse navigation/i }))

    expect(screen.getByRole('link', { name: /dashboard/i })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /notifications/i })).toBeInTheDocument()
  })

  it('renders as an accessible dialog only when acting as the mobile drawer', () => {
    renderSidebar({ mobileOpen: false })
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
  })

  it('renders a dialog with a backdrop when mobileOpen is true, and Escape closes it', async () => {
    const onCloseMobile = vi.fn()
    renderSidebar({ mobileOpen: true, onCloseMobile })

    expect(screen.getByRole('dialog', { name: /navigation menu/i })).toBeInTheDocument()

    await userEvent.keyboard('{Escape}')
    expect(onCloseMobile).toHaveBeenCalled()
  })

  it('closes when the backdrop is clicked', async () => {
    const onCloseMobile = vi.fn()
    renderSidebar({ mobileOpen: true, onCloseMobile })

    const dialog = screen.getByRole('dialog', { name: /navigation menu/i })
    // The backdrop is the dialog's own preceding sibling in the DOM,
    // rendered by the same component — locate it via its aria-hidden
    // marker rather than a CSS class, matching how ConfirmDialog's own
    // test suite locates its backdrop.
    const backdrop = dialog.previousSibling
    await userEvent.click(backdrop)

    expect(onCloseMobile).toHaveBeenCalled()
  })

  it('moves focus to the first navigation link when the drawer opens', async () => {
    renderSidebar({ mobileOpen: true })
    await waitFor(() => expect(screen.getByRole('link', { name: /dashboard/i })).toHaveFocus())
  })

  it('renders a decorative icon for every navigation item, never affecting the link name', () => {
    renderSidebar({ role: 'SYSTEM_ADMIN' })
    const links = screen.getAllByRole('link')
    expect(links.length).toBeGreaterThan(0)

    for (const link of links) {
      const icon = link.querySelector('svg')
      expect(icon).toBeInTheDocument()
      expect(icon).toHaveAttribute('aria-hidden', 'true')
    }
  })
})
