import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import NotificationBell from './NotificationBell'

vi.mock('../services/notificationService', () => ({
  unreadCount: vi.fn(),
  list: vi.fn(),
  markRead: vi.fn(),
  markAllRead: vi.fn(),
}))

import * as notificationService from '../services/notificationService'

function renderBell() {
  return render(
    <MemoryRouter>
      <NotificationBell />
    </MemoryRouter>
  )
}

describe('NotificationBell', () => {
  beforeEach(() => {
    vi.resetAllMocks()
    notificationService.unreadCount.mockResolvedValue({ unread_count: 0 })
    notificationService.list.mockResolvedValue({ items: [], total: 0, page: 1, page_size: 10, total_pages: 0 })
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('renders an accessible bell button and fetches the unread count on mount', async () => {
    notificationService.unreadCount.mockResolvedValue({ unread_count: 3 })
    renderBell()
    await waitFor(() => expect(notificationService.unreadCount).toHaveBeenCalled())
    expect(await screen.findByRole('button', { name: 'Notifications, 3 unread' })).toBeInTheDocument()
  })

  it('uses a plain accessible name when there are no unread notifications', async () => {
    renderBell()
    expect(await screen.findByRole('button', { name: 'Notifications' })).toBeInTheDocument()
  })

  it('caps the displayed badge at 99+', async () => {
    notificationService.unreadCount.mockResolvedValue({ unread_count: 150 })
    renderBell()
    expect(await screen.findByText('99+')).toBeInTheDocument()
  })

  it('opens the panel on click, with aria-expanded reflecting state', async () => {
    renderBell()
    const button = await screen.findByRole('button', { name: 'Notifications' })
    expect(button).toHaveAttribute('aria-expanded', 'false')

    await userEvent.click(button)

    expect(button).toHaveAttribute('aria-expanded', 'true')
    expect(await screen.findByRole('region', { name: /notifications/i })).toBeInTheDocument()
  })

  it('is keyboard operable', async () => {
    renderBell()
    const button = await screen.findByRole('button', { name: 'Notifications' })
    button.focus()
    await userEvent.keyboard('{Enter}')
    expect(await screen.findByRole('region', { name: /notifications/i })).toBeInTheDocument()
  })

  it('closes on Escape and returns focus to the bell', async () => {
    renderBell()
    const button = await screen.findByRole('button', { name: 'Notifications' })
    await userEvent.click(button)
    await screen.findByRole('region', { name: /notifications/i })

    await userEvent.keyboard('{Escape}')

    await waitFor(() => expect(screen.queryByRole('region', { name: /notifications/i })).not.toBeInTheDocument())
    expect(button).toHaveFocus()
  })

  it('polls unread-count on an interval, never the full list', async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true })
    renderBell()
    await vi.waitFor(() => expect(notificationService.unreadCount).toHaveBeenCalledTimes(1))

    await vi.advanceTimersByTimeAsync(60000)
    expect(notificationService.unreadCount).toHaveBeenCalledTimes(2)
    expect(notificationService.list).not.toHaveBeenCalled()
  })

  it('pauses polling while the tab is hidden and resumes on visibility', async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true })
    renderBell()
    await vi.waitFor(() => expect(notificationService.unreadCount).toHaveBeenCalledTimes(1))

    Object.defineProperty(document, 'visibilityState', { value: 'hidden', configurable: true })
    document.dispatchEvent(new Event('visibilitychange'))

    await vi.advanceTimersByTimeAsync(120000)
    expect(notificationService.unreadCount).toHaveBeenCalledTimes(1)

    Object.defineProperty(document, 'visibilityState', { value: 'visible', configurable: true })
    document.dispatchEvent(new Event('visibilitychange'))

    await vi.waitFor(() => expect(notificationService.unreadCount).toHaveBeenCalledTimes(2))
  })

  it('stops polling on unmount', async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true })
    const { unmount } = renderBell()
    await vi.waitFor(() => expect(notificationService.unreadCount).toHaveBeenCalledTimes(1))

    unmount()
    await vi.advanceTimersByTimeAsync(120000)
    expect(notificationService.unreadCount).toHaveBeenCalledTimes(1)
  })
})
