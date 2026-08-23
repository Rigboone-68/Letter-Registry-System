import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import NotificationsPage from './NotificationsPage'

vi.mock('../services/notificationService', () => ({
  list: vi.fn(),
  markRead: vi.fn(),
  markAllRead: vi.fn(),
  unreadCount: vi.fn(),
}))

import * as notificationService from '../services/notificationService'

function makeNotification(overrides = {}) {
  return {
    id: 'n1',
    letter_id: 'l1',
    notification_type: 'LETTER_REGISTERED',
    message: 'A new letter (reference: REF-001) has been registered in your department.',
    is_read: false,
    created_at: '2026-01-05T09:00:00Z',
    read_at: null,
    ...overrides,
  }
}

function renderPage() {
  return render(
    <MemoryRouter initialEntries={['/app/notifications']}>
      <Routes>
        <Route path="/app/notifications" element={<NotificationsPage />} />
        <Route path="/app/letters/:id" element={<div>Letter Detail</div>} />
      </Routes>
    </MemoryRouter>
  )
}

describe('NotificationsPage', () => {
  beforeEach(() => vi.resetAllMocks())

  it('renders a successful, paginated list', async () => {
    notificationService.list.mockResolvedValue({
      items: [makeNotification()],
      total: 1,
      page: 1,
      page_size: 25,
      total_pages: 1,
    })
    renderPage()
    expect(await screen.findByText(/a new letter/i)).toBeInTheDocument()
    expect(screen.getByText('1 total')).toBeInTheDocument()
    expect(notificationService.list).toHaveBeenCalledWith({ page: 1 })
  })

  it('shows an empty state', async () => {
    notificationService.list.mockResolvedValue({ items: [], total: 0, page: 1, page_size: 25, total_pages: 0 })
    renderPage()
    expect(await screen.findByText(/no notifications yet/i)).toBeInTheDocument()
  })

  it('shows a retryable error state', async () => {
    notificationService.list.mockRejectedValueOnce({ status: 0, message: 'Unable to reach the server.', fieldErrors: null })
    notificationService.list.mockResolvedValueOnce({ items: [], total: 0, page: 1, page_size: 25, total_pages: 0 })
    renderPage()
    expect(await screen.findByRole('alert')).toHaveTextContent(/reach the server/i)
    await userEvent.click(screen.getByRole('button', { name: /try again/i }))
    expect(await screen.findByText(/no notifications yet/i)).toBeInTheDocument()
  })

  it('paginates using the real backend page metadata', async () => {
    notificationService.list.mockResolvedValue({
      items: [makeNotification()],
      total: 30,
      page: 1,
      page_size: 25,
      total_pages: 2,
    })
    renderPage()
    await screen.findByText(/a new letter/i)

    await userEvent.click(screen.getByRole('button', { name: '2' }))

    await waitFor(() => expect(notificationService.list).toHaveBeenLastCalledWith({ page: 2 }))
  })

  it('never sends an is_read filter parameter', async () => {
    notificationService.list.mockResolvedValue({ items: [], total: 0, page: 1, page_size: 25, total_pages: 0 })
    renderPage()
    await waitFor(() => expect(notificationService.list).toHaveBeenCalled())
    const params = notificationService.list.mock.calls[0][0]
    expect(params).not.toHaveProperty('is_read')
  })

  it('navigates to the related Letter on click, and a subsequent 404 renders the existing generic not-found state', async () => {
    notificationService.list.mockResolvedValue({
      items: [makeNotification()],
      total: 1,
      page: 1,
      page_size: 25,
      total_pages: 1,
    })
    renderPage()
    await screen.findByText(/a new letter/i)

    await userEvent.click(screen.getByRole('link'))

    expect(await screen.findByText('Letter Detail')).toBeInTheDocument()
  })

  it('marks one notification read', async () => {
    notificationService.list.mockResolvedValue({
      items: [makeNotification()],
      total: 1,
      page: 1,
      page_size: 25,
      total_pages: 1,
    })
    notificationService.markRead.mockResolvedValue(makeNotification({ is_read: true, read_at: '2026-01-05T10:00:00Z' }))
    renderPage()
    await screen.findByText(/a new letter/i)

    await userEvent.click(screen.getByRole('button', { name: /mark as read/i }))

    await waitFor(() => expect(notificationService.markRead).toHaveBeenCalledWith('n1'))
    await waitFor(() => expect(screen.queryByRole('button', { name: /mark as read/i })).not.toBeInTheDocument())
  })

  it('marks all read', async () => {
    notificationService.list.mockResolvedValue({
      items: [
        makeNotification(),
        makeNotification({ id: 'n2', message: 'A new letter (reference: REF-002) has been registered in your department.' }),
      ],
      total: 2,
      page: 1,
      page_size: 25,
      total_pages: 1,
    })
    notificationService.markAllRead.mockResolvedValue({ marked_read: 2 })
    renderPage()
    await screen.findAllByText(/a new letter/i)

    await userEvent.click(screen.getByRole('button', { name: /mark all read/i }))

    await waitFor(() => expect(notificationService.markAllRead).toHaveBeenCalled())
    expect(screen.queryAllByRole('button', { name: /mark as read/i })).toHaveLength(0)
  })

  it('shows a normalized error, not a silent success, when marking read fails', async () => {
    notificationService.list.mockResolvedValue({
      items: [makeNotification()],
      total: 1,
      page: 1,
      page_size: 25,
      total_pages: 1,
    })
    notificationService.markRead.mockRejectedValue({ status: 404, message: 'Notification not found.', fieldErrors: null })
    renderPage()
    await screen.findByText(/a new letter/i)

    await userEvent.click(screen.getByRole('button', { name: /mark as read/i }))

    expect(await screen.findByRole('alert')).toHaveTextContent('Notification not found.')
    expect(screen.getByRole('button', { name: /mark as read/i })).toBeInTheDocument()
  })
})
