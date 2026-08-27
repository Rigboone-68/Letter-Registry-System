import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import DashboardPage from './DashboardPage'

const mockUseAuth = vi.fn()
vi.mock('../context/AuthContext', () => ({
  useAuth: () => mockUseAuth(),
}))
vi.mock('../services/letterService', async () => {
  const actual = await vi.importActual('../services/letterService')
  return { ...actual, list: vi.fn() }
})
vi.mock('../services/notificationService', () => ({ unreadCount: vi.fn() }))
vi.mock('../services/departmentService', () => ({ list: vi.fn() }))
vi.mock('../services/adminService', () => ({ list: vi.fn() }))
vi.mock('../services/userService', () => ({ list: vi.fn() }))

import * as adminService from '../services/adminService'
import * as departmentService from '../services/departmentService'
import * as letterService from '../services/letterService'
import * as notificationService from '../services/notificationService'
import * as userService from '../services/userService'

const RECENT_LETTER = {
  id: 'l1',
  reference_number: 'REF-001',
  subject: 'Budget approval',
  status: 'ACTIVE',
  received_at: '2026-01-05T09:00:00Z',
}

function letterListResponse(total) {
  return { items: [], total, page: 1, page_size: 1, total_pages: 1 }
}

function renderDashboard(role = 'USER') {
  mockUseAuth.mockReturnValue({ user: { id: 'u1', role, department_id: 'd1', full_name: 'Jane' } })
  return render(
    <MemoryRouter>
      <DashboardPage />
    </MemoryRouter>
  )
}

describe('DashboardPage', () => {
  beforeEach(() => {
    vi.resetAllMocks()
    letterService.list.mockImplementation((params = {}) => {
      if (params.sort_by) return Promise.resolve({ ...letterListResponse(1), items: [RECENT_LETTER] })
      if (params.status === 'ACTIVE') return Promise.resolve(letterListResponse(7))
      if (params.status === 'ARCHIVED') return Promise.resolve(letterListResponse(3))
      return Promise.resolve(letterListResponse(10))
    })
    notificationService.unreadCount.mockResolvedValue({ unread_count: 2 })
    departmentService.list.mockResolvedValue({ items: [], total: 4 })
    adminService.list.mockResolvedValue({ items: [], total: 1 })
    userService.list.mockResolvedValue({ items: [], total: 5 })
  })

  it('renders universal Letter and Notification cards for every role', async () => {
    renderDashboard('USER')

    expect(await screen.findByText('10')).toBeInTheDocument() // Total Letters
    expect(screen.getByText('7')).toBeInTheDocument() // Active Letters
    expect(screen.getByText('3')).toBeInTheDocument() // Archived Letters
    expect(await screen.findByText('2')).toBeInTheDocument() // Unread Notifications
  })

  it('renders SYSTEM_ADMIN-only cards and quick actions, and fetches no ADMIN/USER-only data', async () => {
    renderDashboard('SYSTEM_ADMIN')

    expect(await screen.findByText('Active Departments')).toBeInTheDocument()
    expect(screen.getByText('Pending Admin Approvals')).toBeInTheDocument()
    expect(screen.queryByText('Active Users')).not.toBeInTheDocument()
    expect(screen.queryByText('Pending User Approvals')).not.toBeInTheDocument()

    expect(screen.getByRole('link', { name: 'Create Department' })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Authorize Admin' })).toBeInTheDocument()

    await waitFor(() => expect(departmentService.list).toHaveBeenCalledWith({ status: 'ACTIVE' }))
    expect(adminService.list).toHaveBeenCalledWith({ status: 'PENDING_APPROVAL' })
    expect(userService.list).not.toHaveBeenCalled()
  })

  it('renders ADMIN-only cards and quick actions, and fetches no SYSTEM_ADMIN-only data', async () => {
    renderDashboard('ADMIN')

    expect(await screen.findByText('Active Users')).toBeInTheDocument()
    expect(screen.getByText('Pending User Approvals')).toBeInTheDocument()
    expect(screen.queryByText('Active Departments')).not.toBeInTheDocument()

    expect(screen.getByRole('link', { name: 'Authorize User' })).toBeInTheDocument()
    expect(screen.queryByRole('link', { name: 'Create Department' })).not.toBeInTheDocument()

    await waitFor(() => expect(userService.list).toHaveBeenCalledWith({ status: 'ACTIVE' }))
    expect(userService.list).toHaveBeenCalledWith({ status: 'PENDING_APPROVAL' })
    expect(departmentService.list).not.toHaveBeenCalled()
    expect(adminService.list).not.toHaveBeenCalled()
  })

  it('renders no administration cards or quick actions for USER', async () => {
    renderDashboard('USER')
    await screen.findByText('10')

    expect(screen.queryByText('Active Departments')).not.toBeInTheDocument()
    expect(screen.queryByText('Active Users')).not.toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Record a Letter' })).toBeInTheDocument()
    expect(departmentService.list).not.toHaveBeenCalled()
    expect(adminService.list).not.toHaveBeenCalled()
    expect(userService.list).not.toHaveBeenCalled()
  })

  it('requests only the smallest reasonable Letter counts, never the full registry', async () => {
    renderDashboard('USER')
    await screen.findByText('10')

    expect(letterService.list).toHaveBeenCalledWith({ page_size: 1 })
    expect(letterService.list).toHaveBeenCalledWith({ status: 'ACTIVE', page_size: 1 })
    expect(letterService.list).toHaveBeenCalledWith({ status: 'ARCHIVED', page_size: 1 })
    expect(letterService.list).toHaveBeenCalledWith({
      sort_by: 'received_at',
      sort_order: 'desc',
      page_size: 5,
    })
  })

  it('renders Recent Letters as a link to the existing Letter detail route', async () => {
    renderDashboard('USER')
    const link = await screen.findByRole('link', { name: /ref-001/i })
    expect(link).toHaveAttribute('href', '/app/letters/l1')
  })

  it('never sends a recipient identifier to the notification endpoint', async () => {
    renderDashboard('USER')
    await waitFor(() => expect(notificationService.unreadCount).toHaveBeenCalled())
    expect(notificationService.unreadCount).toHaveBeenCalledWith()
  })

  it('never sends a department id anywhere — department scoping is entirely server-derived', async () => {
    renderDashboard('SYSTEM_ADMIN')
    await waitFor(() => expect(departmentService.list).toHaveBeenCalled())

    for (const call of letterService.list.mock.calls) {
      expect(call[0]).not.toHaveProperty('department_id')
    }
    for (const call of departmentService.list.mock.calls.concat(adminService.list.mock.calls)) {
      expect(call[0]).not.toHaveProperty('department_id')
    }
  })

  it('lets one widget fail independently — a failed Letter summary never blocks Recent Letters or Notifications', async () => {
    letterService.list.mockImplementation((params = {}) => {
      if (params.sort_by) return Promise.resolve({ ...letterListResponse(1), items: [RECENT_LETTER] })
      return Promise.reject({ status: 0, message: 'Unable to reach the server.', fieldErrors: null })
    })
    renderDashboard('USER')

    expect(await screen.findAllByRole('alert')).not.toHaveLength(0)
    expect(await screen.findByText('2')).toBeInTheDocument() // Notifications still loaded
    expect(await screen.findByRole('link', { name: /ref-001/i })).toBeInTheDocument() // Recent Letters still loaded
  })

  it('shows "Unavailable" for a failed card, never a fabricated zero', async () => {
    letterService.list.mockImplementation((params = {}) => {
      if (params.sort_by) return Promise.resolve({ ...letterListResponse(1), items: [] })
      return Promise.reject({ status: 0, message: 'Unable to reach the server.', fieldErrors: null })
    })
    renderDashboard('USER')

    expect(await screen.findAllByText(/unavailable/i)).not.toHaveLength(0)
    expect(screen.queryByText('0')).not.toBeInTheDocument()
  })

  it('has semantic headings for every section', async () => {
    renderDashboard('USER')
    await screen.findByText('10')

    expect(screen.getByRole('heading', { level: 1, name: 'Dashboard' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { level: 2, name: 'Recent Letters' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { level: 2, name: 'Quick Actions' })).toBeInTheDocument()
  })

  it('renders the new header subtitle with no fabricated system-health or security claim (Phase 5I.4A)', async () => {
    renderDashboard('USER')
    await screen.findByText('10')

    expect(screen.getByText('Registry Overview')).toBeInTheDocument()
    expect(
      screen.getByText('Current registry activity and quick actions for your role.')
    ).toBeInTheDocument()

    const forbidden = /system secure|all systems operational|encrypted|live monitoring/i
    expect(document.body.textContent).not.toMatch(forbidden)
  })

  it('shows how many recent letters are shown only once loaded, never during loading or on error', async () => {
    renderDashboard('USER')

    expect(await screen.findByText('1 shown')).toBeInTheDocument()
  })

  it('keeps Quick Actions links named exactly by their label, even with a decorative arrow', async () => {
    renderDashboard('SYSTEM_ADMIN')

    const link = await screen.findByRole('link', { name: 'Create Department' })
    expect(link).toHaveAttribute('href', '/app/system/departments/new')
  })
})
