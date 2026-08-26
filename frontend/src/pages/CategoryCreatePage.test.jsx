import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import CategoryCreatePage from './CategoryCreatePage'

vi.mock('../services/categoryService', () => ({ create: vi.fn() }))

import * as categoryService from '../services/categoryService'

function renderPage() {
  return render(
    <MemoryRouter initialEntries={['/app/system/categories/new']}>
      <Routes>
        <Route path="/app/system/categories" element={<div>Category List</div>} />
        <Route path="/app/system/categories/new" element={<CategoryCreatePage />} />
        <Route path="/app/system/categories/:id" element={<div>Category Detail</div>} />
      </Routes>
    </MemoryRouter>
  )
}

describe('CategoryCreatePage', () => {
  beforeEach(() => vi.resetAllMocks())

  it('requires a name before submitting', async () => {
    renderPage()
    await userEvent.click(screen.getByRole('button', { name: /create category/i }))
    expect(await screen.findByText(/name is required/i)).toBeInTheDocument()
    expect(categoryService.create).not.toHaveBeenCalled()
  })

  it('creates successfully and navigates to the new category', async () => {
    categoryService.create.mockResolvedValue({ id: 'c9', name: 'Legal', description: null, status: 'ACTIVE' })
    renderPage()
    await userEvent.type(screen.getByLabelText(/name/i), 'Legal')
    await userEvent.click(screen.getByRole('button', { name: /create category/i }))

    await waitFor(() => expect(screen.getByText('Category Detail')).toBeInTheDocument())
    expect(categoryService.create).toHaveBeenCalledWith({ name: 'Legal', description: null })
  })

  it('shows a duplicate-name conflict from the backend', async () => {
    categoryService.create.mockRejectedValue({
      status: 409,
      message: 'A category with this name already exists.',
      fieldErrors: null,
    })
    renderPage()
    await userEvent.type(screen.getByLabelText(/name/i), 'Administrative')
    await userEvent.click(screen.getByRole('button', { name: /create category/i }))
    expect(await screen.findByRole('alert')).toHaveTextContent(/already exists/i)
  })

  it('never sends id, status, or timestamps', async () => {
    categoryService.create.mockResolvedValue({ id: 'c9', name: 'Legal', description: null, status: 'ACTIVE' })
    renderPage()
    await userEvent.type(screen.getByLabelText(/name/i), 'Legal')
    await userEvent.click(screen.getByRole('button', { name: /create category/i }))

    await waitFor(() => expect(categoryService.create).toHaveBeenCalled())
    const payload = categoryService.create.mock.calls[0][0]
    expect(Object.keys(payload).sort()).toEqual(['description', 'name'])
  })

  it('cancels back to the category list', async () => {
    renderPage()
    await userEvent.click(screen.getByRole('button', { name: /cancel/i }))
    expect(await screen.findByText('Category List')).toBeInTheDocument()
  })
})
