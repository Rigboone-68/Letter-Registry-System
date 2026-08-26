import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import CategoryListPage from './CategoryListPage'

vi.mock('../services/categoryService', () => ({ list: vi.fn() }))

import * as categoryService from '../services/categoryService'

function makeCategory(overrides = {}) {
  return {
    id: 'c1',
    name: 'Administrative',
    description: 'General administrative correspondence',
    status: 'ACTIVE',
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
    ...overrides,
  }
}

function renderPage() {
  return render(
    <MemoryRouter initialEntries={['/app/system/categories']}>
      <Routes>
        <Route path="/app/system/categories" element={<CategoryListPage />} />
      </Routes>
    </MemoryRouter>
  )
}

describe('CategoryListPage', () => {
  beforeEach(() => vi.resetAllMocks())

  it('renders a successful list', async () => {
    categoryService.list.mockResolvedValue({ items: [makeCategory()], total: 1 })
    renderPage()
    expect(await screen.findByText('Administrative')).toBeInTheDocument()
    expect(screen.getByText('1 total')).toBeInTheDocument()
  })

  it('shows an empty state when there are no results', async () => {
    categoryService.list.mockResolvedValue({ items: [], total: 0 })
    renderPage()
    expect(await screen.findByText(/no categories match/i)).toBeInTheDocument()
  })

  it('shows an error state with a working retry', async () => {
    categoryService.list
      .mockRejectedValueOnce({ status: 0, message: 'Unable to reach the server.', fieldErrors: null })
      .mockResolvedValueOnce({ items: [makeCategory()], total: 1 })
    renderPage()
    expect(await screen.findByRole('alert')).toHaveTextContent(/reach the server/i)
    await userEvent.click(screen.getByRole('button', { name: /try again/i }))
    expect(await screen.findByText('Administrative')).toBeInTheDocument()
  })

  it('re-requests with the selected status filter', async () => {
    categoryService.list.mockResolvedValue({ items: [], total: 0 })
    renderPage()
    await waitFor(() => expect(categoryService.list).toHaveBeenCalledWith({}))

    await userEvent.selectOptions(screen.getByLabelText(/status/i), 'INACTIVE')

    await waitFor(() => expect(categoryService.list).toHaveBeenLastCalledWith({ status: 'INACTIVE' }))
  })

  it('links to the create-category page', async () => {
    categoryService.list.mockResolvedValue({ items: [], total: 0 })
    renderPage()
    expect(await screen.findByRole('link', { name: /create category/i })).toHaveAttribute(
      'href',
      '/app/system/categories/new'
    )
  })

  it('never renders a delete action', async () => {
    categoryService.list.mockResolvedValue({ items: [makeCategory()], total: 1 })
    renderPage()
    await screen.findByText('Administrative')
    expect(screen.queryByRole('button', { name: /delete/i })).not.toBeInTheDocument()
  })
})
