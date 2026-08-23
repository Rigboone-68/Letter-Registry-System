import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it, vi } from 'vitest'

import NotificationItem from './NotificationItem'

const UNREAD = {
  id: 'n1',
  letter_id: 'l1',
  notification_type: 'LETTER_REGISTERED',
  message: 'A new letter (reference: REF-001) has been registered in your department.',
  is_read: false,
  created_at: '2026-01-05T09:00:00Z',
  read_at: null,
}

function renderItem(props = {}) {
  return render(
    <MemoryRouter>
      <ul>
        <NotificationItem notification={UNREAD} onMarkRead={vi.fn()} marking={false} {...props} />
      </ul>
    </MemoryRouter>
  )
}

describe('NotificationItem', () => {
  it('renders the message as plain text, never via dangerouslySetInnerHTML', () => {
    renderItem()
    expect(screen.getByText(/a new letter \(reference: ref-001\)/i)).toBeInTheDocument()
  })

  it('links to the related Letter when letter_id is present', () => {
    renderItem()
    expect(screen.getByRole('link')).toHaveAttribute('href', '/app/letters/l1')
  })

  it('renders non-interactively when letter_id is null', () => {
    renderItem({ notification: { ...UNREAD, letter_id: null } })
    expect(screen.queryByRole('link')).not.toBeInTheDocument()
    expect(screen.getByText(UNREAD.message)).toBeInTheDocument()
  })

  it('shows a Mark as read action only for unread notifications', () => {
    renderItem()
    expect(screen.getByRole('button', { name: /mark as read/i })).toBeInTheDocument()
  })

  it('does not show a Mark as read action for an already-read notification', () => {
    renderItem({ notification: { ...UNREAD, is_read: true, read_at: '2026-01-05T10:00:00Z' } })
    expect(screen.queryByRole('button', { name: /mark as read/i })).not.toBeInTheDocument()
  })

  it('calls onMarkRead only from the explicit action, never from clicking the Letter link', async () => {
    const onMarkRead = vi.fn()
    renderItem({ onMarkRead })

    await userEvent.click(screen.getByRole('link'))
    expect(onMarkRead).not.toHaveBeenCalled()

    await userEvent.click(screen.getByRole('button', { name: /mark as read/i }))
    expect(onMarkRead).toHaveBeenCalledWith(UNREAD)
  })

  it('is keyboard accessible', async () => {
    renderItem()
    await userEvent.tab()
    expect(screen.getByRole('link')).toHaveFocus()
    await userEvent.tab()
    expect(screen.getByRole('button', { name: /mark as read/i })).toHaveFocus()
  })
})
