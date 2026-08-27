import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import AppShell from './AppShell'
import { PRODUCTION_CREDIT } from '../constants/app'

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

function renderShell(initialEntry = '/app/dashboard') {
  mockUseAuth.mockReturnValue({
    user: { id: 'u1', full_name: 'Jane User', role: 'USER' },
    logout: vi.fn(),
  })
  notificationService.unreadCount.mockResolvedValue({ unread_count: 0 })

  return render(
    <MemoryRouter initialEntries={[initialEntry]}>
      <Routes>
        <Route element={<AppShell />}>
          <Route path="/app/dashboard" element={<div>Dashboard content</div>} />
          <Route path="/app/letters" element={<div>Letters content</div>} />
        </Route>
      </Routes>
    </MemoryRouter>
  )
}

describe('AppShell', () => {
  beforeEach(() => vi.resetAllMocks())

  it('renders the routed page content via Outlet', async () => {
    renderShell()
    expect(await screen.findByText('Dashboard content')).toBeInTheDocument()
  })

  it('renders the AJ-OVA Labs footer exactly once', async () => {
    renderShell()
    await screen.findByText('Dashboard content')
    expect(screen.getAllByText(PRODUCTION_CREDIT)).toHaveLength(1)
  })

  it('opens the mobile navigation drawer from the Topbar menu button', async () => {
    renderShell()
    await screen.findByText('Dashboard content')

    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()

    await userEvent.click(screen.getByRole('button', { name: /open navigation menu/i }))

    expect(screen.getByRole('dialog', { name: /navigation menu/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /close navigation menu/i })).toHaveAttribute(
      'aria-expanded',
      'true'
    )
  })

  it('closes the drawer via the backdrop', async () => {
    renderShell()
    await screen.findByText('Dashboard content')
    await userEvent.click(screen.getByRole('button', { name: /open navigation menu/i }))
    const dialog = screen.getByRole('dialog', { name: /navigation menu/i })

    await userEvent.click(dialog.previousSibling)

    await waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument())
  })

  it('closes the drawer via Escape', async () => {
    renderShell()
    await screen.findByText('Dashboard content')
    await userEvent.click(screen.getByRole('button', { name: /open navigation menu/i }))
    await screen.findByRole('dialog', { name: /navigation menu/i })

    await userEvent.keyboard('{Escape}')

    await waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument())
  })

  it('closes the drawer automatically after a navigation link is selected', async () => {
    renderShell()
    await screen.findByText('Dashboard content')
    await userEvent.click(screen.getByRole('button', { name: /open navigation menu/i }))
    const dialog = await screen.findByRole('dialog', { name: /navigation menu/i })

    await userEvent.click(within(dialog).getByRole('link', { name: /^letters/i }))

    await waitFor(() => expect(screen.getByText('Letters content')).toBeInTheDocument())
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
  })
})
