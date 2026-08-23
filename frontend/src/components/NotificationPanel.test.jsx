import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import NotificationPanel from './NotificationPanel'

vi.mock('../services/notificationService', () => ({
  unreadCount: vi.fn(),
  list: vi.fn(),
  markRead: vi.fn(),
  markAllRead: vi.fn(),
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

function renderPanel(props = {}) {
  return render(
    <MemoryRouter>
      <NotificationPanel onClose={vi.fn()} onUnreadCountChange={vi.fn()} {...props} />
    </MemoryRouter>
  )
}

describe('NotificationPanel', () => {
  beforeEach(() => vi.resetAllMocks())

  it('shows a loading state, then the fetched notifications', async () => {
    notificationService.list.mockResolvedValue({ items: [makeNotification()], total: 1, page: 1, page_size: 10, total_pages: 1 })
    renderPanel()
    expect(await screen.findByText(/a new letter/i)).toBeInTheDocument()
    expect(notificationService.list).toHaveBeenCalledWith({ page: 1, page_size: 10 })
  })

  it('shows an empty state when there are no notifications', async () => {
    notificationService.list.mockResolvedValue({ items: [], total: 0, page: 1, page_size: 10, total_pages: 0 })
    renderPanel()
    expect(await screen.findByText(/no notifications yet/i)).toBeInTheDocument()
  })

  it('shows an error state on failure', async () => {
    notificationService.list.mockRejectedValue({ status: 0, message: 'Unable to reach the server.', fieldErrors: null })
    renderPanel()
    expect(await screen.findByRole('alert')).toHaveTextContent(/reach the server/i)
  })

  it('marks one notification read and refreshes the unread count', async () => {
    notificationService.list.mockResolvedValue({ items: [makeNotification()], total: 1, page: 1, page_size: 10, total_pages: 1 })
    notificationService.markRead.mockResolvedValue(makeNotification({ is_read: true, read_at: '2026-01-05T10:00:00Z' }))
    notificationService.unreadCount.mockResolvedValue({ unread_count: 0 })
    const onUnreadCountChange = vi.fn()
    renderPanel({ onUnreadCountChange })
    await screen.findByText(/a new letter/i)

    await userEvent.click(screen.getByRole('button', { name: /mark as read/i }))

    await waitFor(() => expect(notificationService.markRead).toHaveBeenCalledWith('n1'))
    await waitFor(() => expect(onUnreadCountChange).toHaveBeenCalledWith(0))
  })

  it('marks all read and clears the unread count', async () => {
    notificationService.list.mockResolvedValue({
      items: [
        makeNotification(),
        makeNotification({ id: 'n2', message: 'A new letter (reference: REF-002) has been registered in your department.' }),
      ],
      total: 2,
      page: 1,
      page_size: 10,
      total_pages: 1,
    })
    notificationService.markAllRead.mockResolvedValue({ marked_read: 2 })
    const onUnreadCountChange = vi.fn()
    renderPanel({ onUnreadCountChange })
    await screen.findAllByText(/a new letter/i)

    await userEvent.click(screen.getByRole('button', { name: /mark all read/i }))

    await waitFor(() => expect(notificationService.markAllRead).toHaveBeenCalled())
    expect(onUnreadCountChange).toHaveBeenCalledWith(0)
    expect(screen.queryAllByRole('button', { name: /mark as read/i })).toHaveLength(0)
  })

  it('does not show Mark all read when nothing is unread', async () => {
    notificationService.list.mockResolvedValue({
      items: [makeNotification({ is_read: true, read_at: '2026-01-05T10:00:00Z' })],
      total: 1,
      page: 1,
      page_size: 10,
      total_pages: 1,
    })
    renderPanel()
    await screen.findByText(/a new letter/i)
    expect(screen.queryByRole('button', { name: /mark all read/i })).not.toBeInTheDocument()
  })

  it('closes on Escape', async () => {
    notificationService.list.mockResolvedValue({ items: [], total: 0, page: 1, page_size: 10, total_pages: 0 })
    const onClose = vi.fn()
    renderPanel({ onClose })
    await screen.findByText(/no notifications yet/i)

    await userEvent.keyboard('{Escape}')
    expect(onClose).toHaveBeenCalled()
  })

  it('links to the full notifications page', async () => {
    notificationService.list.mockResolvedValue({ items: [], total: 0, page: 1, page_size: 10, total_pages: 0 })
    renderPanel()
    expect(await screen.findByRole('link', { name: /view all notifications/i })).toHaveAttribute(
      'href',
      '/app/notifications'
    )
  })

  it('never requests another user\'s notifications', async () => {
    notificationService.list.mockResolvedValue({ items: [], total: 0, page: 1, page_size: 10, total_pages: 0 })
    renderPanel()
    await waitFor(() => expect(notificationService.list).toHaveBeenCalled())
    const params = notificationService.list.mock.calls[0][0]
    expect(Object.keys(params).sort()).toEqual(['page', 'page_size'])
  })
})
