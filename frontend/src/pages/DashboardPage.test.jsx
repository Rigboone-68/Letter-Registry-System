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
  return { ...actual, list: vi.fn(), aggregate: vi.fn() }
})
vi.mock('../services/notificationService', () => ({ unreadCount: vi.fn() }))
vi.mock('../services/departmentService', () => ({ list: vi.fn() }))

import * as departmentService from '../services/departmentService'
import * as letterService from '../services/letterService'
import * as notificationService from '../services/notificationService'

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

function aggregateResponse(groupBy, buckets) {
  const total = buckets.reduce((sum, bucket) => sum + bucket.count, 0)
  return { group_by: groupBy, total, buckets }
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
      return Promise.resolve(letterListResponse(10))
    })
    letterService.aggregate.mockImplementation((params = {}) => {
      if (params.group_by === 'direction') {
        return Promise.resolve(
          aggregateResponse('direction', [
            { key: 'INCOMING', count: 7 },
            { key: 'OUTGOING', count: 3 },
          ])
        )
      }
      if (params.group_by === 'department') {
        return Promise.resolve(aggregateResponse('department', [{ key: 'dept-1', count: 6 }]))
      }
      if (params.group_by === 'dispatch_department') {
        return Promise.resolve(aggregateResponse('dispatch_department', [{ key: 'dept-2', count: 2 }]))
      }
      if (params.group_by === 'month' && params.direction === 'INCOMING') {
        return Promise.resolve(
          aggregateResponse('month', [{ key: '2026-01-01T00:00:00+00:00', count: 5 }])
        )
      }
      if (params.group_by === 'month' && params.direction === 'OUTGOING') {
        return Promise.resolve(
          aggregateResponse('month', [{ key: '2026-01-01T00:00:00+00:00', count: 1 }])
        )
      }
      throw new Error(`Unexpected aggregate call: ${JSON.stringify(params)}`)
    })
    notificationService.unreadCount.mockResolvedValue({ unread_count: 99 })
    departmentService.list.mockResolvedValue({
      items: [
        { id: 'dept-1', name: 'Finance' },
        { id: 'dept-2', name: 'S&IT' },
      ],
      total: 2,
    })
  })

  it('renders the two headline figures for every role', async () => {
    renderDashboard('USER')

    expect(await screen.findByText('10')).toBeInTheDocument() // Total Letters
    expect(await screen.findByText('99')).toBeInTheDocument() // Unread Notifications
    expect(screen.getByText('Total Letters')).toBeInTheDocument()
    expect(screen.getByText('Unread Notifications')).toBeInTheDocument()
  })

  it('no longer renders the retired administration KPI cards for any role', async () => {
    renderDashboard('SYSTEM_ADMIN')
    await screen.findByText('10')

    expect(screen.queryByText('Active Departments')).not.toBeInTheDocument()
    expect(screen.queryByText('Pending Admin Approvals')).not.toBeInTheDocument()
    expect(screen.queryByText('Active Users')).not.toBeInTheDocument()
    expect(screen.queryByText('Pending User Approvals')).not.toBeInTheDocument()
  })

  it('requests every chart from the aggregate endpoint, never the full Letter registry', async () => {
    renderDashboard('USER')
    await screen.findByText('10')

    await waitFor(() => expect(letterService.aggregate).toHaveBeenCalledWith({ group_by: 'direction' }))
    expect(letterService.aggregate).toHaveBeenCalledWith({ group_by: 'department' })
    expect(letterService.aggregate).toHaveBeenCalledWith({ group_by: 'dispatch_department' })
    expect(letterService.aggregate).toHaveBeenCalledWith({ group_by: 'month', direction: 'INCOMING' })
    expect(letterService.aggregate).toHaveBeenCalledWith({ group_by: 'month', direction: 'OUTGOING' })

    // Never a page-size/pagination parameter used to reconstruct analytics.
    for (const call of letterService.aggregate.mock.calls) {
      expect(call[0]).not.toHaveProperty('page_size')
    }
  })

  it('never sends a department id to any aggregate request — the backend derives scope itself', async () => {
    renderDashboard('SYSTEM_ADMIN')
    await screen.findByText('10')
    await waitFor(() => expect(letterService.aggregate).toHaveBeenCalled())

    for (const call of letterService.aggregate.mock.calls) {
      expect(call[0]).not.toHaveProperty('department_id')
    }
  })

  it('renders the Incoming vs. Outgoing chart with real labels and counts', async () => {
    renderDashboard('USER')

    // "Incoming / Diary"/"Outgoing / Dispatch" also label the trend
    // chart's own legend below — assert at least one match rather than
    // assuming uniqueness across the whole page.
    expect(await screen.findAllByText('Incoming / Diary')).not.toHaveLength(0)
    expect(screen.getAllByText('Outgoing / Dispatch')).not.toHaveLength(0)
    expect(screen.getByText('7')).toBeInTheDocument()
    expect(screen.getByText('3')).toBeInTheDocument()
  })

  it('resolves department ids to real names on the received/sent charts', async () => {
    renderDashboard('USER')

    expect(await screen.findByText('Finance')).toBeInTheDocument()
    expect(screen.getByText('S&IT')).toBeInTheDocument()
  })

  it('renders the correspondence trend chart legend', async () => {
    renderDashboard('USER')
    await screen.findByText('10')

    expect(await screen.findAllByText(/Incoming \/ Diary/)).not.toHaveLength(0)
    expect(await screen.findAllByText(/Outgoing \/ Dispatch/)).not.toHaveLength(0)
  })

  it('lets one failed chart render its own error without blanking the rest of the dashboard', async () => {
    letterService.aggregate.mockImplementation((params = {}) => {
      if (params.group_by === 'direction') {
        return Promise.reject({ status: 0, message: 'Unable to reach the server.', fieldErrors: null })
      }
      if (params.group_by === 'department') {
        return Promise.resolve(aggregateResponse('department', [{ key: 'dept-1', count: 6 }]))
      }
      if (params.group_by === 'dispatch_department') {
        return Promise.resolve(aggregateResponse('dispatch_department', []))
      }
      return Promise.resolve(aggregateResponse('month', []))
    })
    renderDashboard('USER')

    expect(await screen.findAllByRole('alert')).not.toHaveLength(0)
    expect(await screen.findByText('Finance')).toBeInTheDocument() // received chart still rendered
    expect(await screen.findByText('10')).toBeInTheDocument() // headline still rendered
  })

  it('shows an empty state, not a misleading zero-looking chart, when a chart has no buckets', async () => {
    letterService.aggregate.mockImplementation((params = {}) => {
      if (params.group_by === 'dispatch_department') {
        return Promise.resolve(aggregateResponse('dispatch_department', []))
      }
      if (params.group_by === 'direction') {
        return Promise.resolve(aggregateResponse('direction', []))
      }
      if (params.group_by === 'department') {
        return Promise.resolve(aggregateResponse('department', []))
      }
      return Promise.resolve(aggregateResponse('month', []))
    })
    renderDashboard('USER')

    expect(
      await screen.findByText('No outgoing correspondence has been dispatched yet.')
    ).toBeInTheDocument()
  })

  it('Recent Letters behavior is unchanged', async () => {
    renderDashboard('USER')
    const link = await screen.findByRole('link', { name: /ref-001/i })
    expect(link).toHaveAttribute('href', '/app/letters/l1')
  })

  it('Quick Actions behavior is unchanged, role-scoped', async () => {
    renderDashboard('SYSTEM_ADMIN')

    expect(await screen.findByRole('link', { name: 'Create Department' })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Authorize Admin' })).toBeInTheDocument()
  })

  it('never sends a recipient identifier to the notification endpoint', async () => {
    renderDashboard('USER')
    await waitFor(() => expect(notificationService.unreadCount).toHaveBeenCalled())
    expect(notificationService.unreadCount).toHaveBeenCalledWith()
  })

  it('has semantic headings for every chart and existing section', async () => {
    renderDashboard('USER')
    await screen.findByText('10')

    expect(screen.getByRole('heading', { level: 1, name: 'Dashboard' })).toBeInTheDocument()
    expect(
      screen.getByRole('heading', { level: 2, name: 'Incoming vs. Outgoing Correspondence' })
    ).toBeInTheDocument()
    expect(
      screen.getByRole('heading', { level: 2, name: 'Letters Received by Department' })
    ).toBeInTheDocument()
    expect(
      screen.getByRole('heading', { level: 2, name: 'Letters Sent by Department' })
    ).toBeInTheDocument()
    expect(
      screen.getByRole('heading', { level: 2, name: 'Correspondence Activity Over Time' })
    ).toBeInTheDocument()
    expect(screen.getByRole('heading', { level: 2, name: 'Recent Letters' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { level: 2, name: 'Quick Actions' })).toBeInTheDocument()
  })

  it('renders the header subtitle with no fabricated system-health or security claim', async () => {
    renderDashboard('USER')
    await screen.findByText('10')

    expect(screen.getByText('Registry Overview')).toBeInTheDocument()
    const forbidden = /system secure|all systems operational|encrypted|live monitoring/i
    expect(document.body.textContent).not.toMatch(forbidden)
  })
})
