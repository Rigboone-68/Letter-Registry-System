import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'

import Pagination from './Pagination'

describe('Pagination', () => {
  it('renders only a result count when there is a single page', () => {
    render(<Pagination page={1} totalPages={1} total={3} onPageChange={vi.fn()} />)
    expect(screen.getByText('3 results')).toBeInTheDocument()
    expect(screen.queryByRole('navigation')).not.toBeInTheDocument()
  })

  it('marks the current page with aria-current', () => {
    render(<Pagination page={2} totalPages={5} total={100} onPageChange={vi.fn()} />)
    expect(screen.getByRole('button', { name: '2' })).toHaveAttribute('aria-current', 'page')
    expect(screen.getByRole('button', { name: '3' })).not.toHaveAttribute('aria-current')
  })

  it('disables Previous on the first page and Next on the last page', () => {
    render(<Pagination page={1} totalPages={3} total={60} onPageChange={vi.fn()} />)
    expect(screen.getByRole('button', { name: /previous page/i })).toBeDisabled()
    expect(screen.getByRole('button', { name: /next page/i })).not.toBeDisabled()
  })

  it('calls onPageChange with the requested page', async () => {
    const onPageChange = vi.fn()
    render(<Pagination page={2} totalPages={5} total={100} onPageChange={onPageChange} />)
    await userEvent.click(screen.getByRole('button', { name: /next page/i }))
    expect(onPageChange).toHaveBeenCalledWith(3)
  })
})
