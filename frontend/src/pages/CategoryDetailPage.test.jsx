import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import CategoryDetailPage from './CategoryDetailPage'

vi.mock('../services/categoryService', () => ({
  get: vi.fn(),
  update: vi.fn(),
  activate: vi.fn(),
  deactivate: vi.fn(),
}))

import * as categoryService from '../services/categoryService'

const CATEGORY = {
  id: 'c1',
  name: 'Administrative',
  description: 'General administrative correspondence',
  status: 'ACTIVE',
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-01T00:00:00Z',
}

function renderPage(id = 'c1') {
  return render(
    <MemoryRouter initialEntries={[`/app/system/categories/${id}`]}>
      <Routes>
        <Route path="/app/system/categories" element={<div>Category List</div>} />
        <Route path="/app/system/categories/:id" element={<CategoryDetailPage />} />
      </Routes>
    </MemoryRouter>
  )
}

describe('CategoryDetailPage', () => {
  beforeEach(() => vi.resetAllMocks())

  it('renders category fields', async () => {
    categoryService.get.mockResolvedValue(CATEGORY)
    renderPage()
    expect(await screen.findByRole('heading', { name: 'Administrative' })).toBeInTheDocument()
    expect(screen.getByText('General administrative correspondence')).toBeInTheDocument()
  })

  it('renders a generic not-found state for a 404', async () => {
    categoryService.get.mockRejectedValue({ status: 404, message: 'Category not found.', fieldErrors: null })
    renderPage()
    expect(await screen.findByRole('alert')).toHaveTextContent('Category not found.')
  })

  it('edits name/description and saves', async () => {
    categoryService.get.mockResolvedValue(CATEGORY)
    categoryService.update.mockResolvedValue({ ...CATEGORY, name: 'Administrative & Legal' })
    renderPage()
    await screen.findByRole('heading', { name: 'Administrative' })

    await userEvent.click(screen.getByRole('button', { name: /^edit$/i }))
    const nameInput = screen.getByLabelText(/name/i)
    await userEvent.clear(nameInput)
    await userEvent.type(nameInput, 'Administrative & Legal')
    await userEvent.click(screen.getByRole('button', { name: /save changes/i }))

    expect(await screen.findByRole('heading', { name: 'Administrative & Legal' })).toBeInTheDocument()
  })

  it('activates without a confirmation dialog', async () => {
    categoryService.get.mockResolvedValue({ ...CATEGORY, status: 'INACTIVE' })
    categoryService.activate.mockResolvedValue({ ...CATEGORY, status: 'ACTIVE' })
    renderPage()
    await screen.findByRole('heading', { name: 'Administrative' })

    await userEvent.click(screen.getByRole('button', { name: /^activate$/i }))

    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
    await waitFor(() => expect(categoryService.activate).toHaveBeenCalledWith('c1'))
  })

  it('requires confirmation before deactivating, using non-permanent wording', async () => {
    categoryService.get.mockResolvedValue(CATEGORY)
    categoryService.deactivate.mockResolvedValue({ ...CATEGORY, status: 'INACTIVE' })
    renderPage()
    await screen.findByRole('heading', { name: 'Administrative' })

    await userEvent.click(screen.getByRole('button', { name: /^deactivate$/i }))
    const dialog = await screen.findByRole('dialog')
    expect(dialog.textContent.toLowerCase()).not.toMatch(/delete/)

    await userEvent.click(within(dialog).getByRole('button', { name: /deactivate category/i }))

    await waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument())
    expect(categoryService.deactivate).toHaveBeenCalledWith('c1')
  })

  it('never renders a delete action', async () => {
    categoryService.get.mockResolvedValue(CATEGORY)
    renderPage()
    await screen.findByRole('heading', { name: 'Administrative' })
    expect(screen.queryByRole('button', { name: /^delete$/i })).not.toBeInTheDocument()
  })
})
