import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import LetterListPage from './LetterListPage'

const mockUseAuth = vi.fn()
vi.mock('../context/AuthContext', () => ({
  useAuth: () => mockUseAuth(),
}))

vi.mock('../services/letterService', async () => {
  const actual = await vi.importActual('../services/letterService')
  return { ...actual, list: vi.fn() }
})
vi.mock('../services/categoryService', () => ({ list: vi.fn() }))
vi.mock('../services/classificationService', () => ({ list: vi.fn() }))
vi.mock('../services/departmentService', () => ({ list: vi.fn() }))

import * as categoryService from '../services/categoryService'
import * as classificationService from '../services/classificationService'
import * as departmentService from '../services/departmentService'
import * as letterService from '../services/letterService'

const USER_ROLE = { id: 'u1', role: 'USER', department_id: 'd1' }
const SYSTEM_ADMIN_ROLE = { id: 'u2', role: 'SYSTEM_ADMIN', department_id: null }

function makeLetter(overrides = {}) {
  return {
    id: 'l1',
    reference_number: 'REF-001',
    recipient_department_id: 'd1',
    source_name: 'Ministry of Finance',
    source_department_id: null,
    source_location: null,
    sender_name: 'Jane Sender',
    sender_designation: 'Director',
    sender_department: 'Finance',
    sender_address: null,
    subject: 'Budget approval',
    category_id: null,
    classification_id: null,
    received_at: '2026-01-05T09:00:00Z',
    recorded_by: 'u1',
    status: 'ACTIVE',
    created_at: '2026-01-05T09:00:00Z',
    updated_at: '2026-01-05T09:00:00Z',
    ...overrides,
  }
}

function renderPage(initialEntries = ['/app/letters']) {
  return render(
    <MemoryRouter initialEntries={initialEntries}>
      <Routes>
        <Route path="/app/letters" element={<LetterListPage />} />
      </Routes>
    </MemoryRouter>
  )
}

describe('LetterListPage', () => {
  beforeEach(() => {
    vi.resetAllMocks()
    mockUseAuth.mockReturnValue({ user: USER_ROLE })
  })

  it('renders a successful list of letters', async () => {
    letterService.list.mockResolvedValue({
      items: [makeLetter()],
      total: 1,
      page: 1,
      page_size: 25,
      total_pages: 1,
    })

    renderPage()

    expect(await screen.findByText('REF-001')).toBeInTheDocument()
    expect(screen.getByText('1 total')).toBeInTheDocument()
  })

  it('shows an empty state when there are no results', async () => {
    letterService.list.mockResolvedValue({ items: [], total: 0, page: 1, page_size: 25, total_pages: 0 })

    renderPage()

    expect(await screen.findByText(/no letters have been recorded yet/i)).toBeInTheDocument()
  })

  it('shows an error state on API failure, with a working retry', async () => {
    letterService.list
      .mockRejectedValueOnce({ status: 0, message: 'Unable to reach the server.', fieldErrors: null })
      .mockResolvedValueOnce({ items: [makeLetter()], total: 1, page: 1, page_size: 25, total_pages: 1 })

    renderPage()

    expect(await screen.findByRole('alert')).toHaveTextContent(/reach the server/i)

    await userEvent.click(screen.getByRole('button', { name: /try again/i }))

    expect(await screen.findByText('REF-001')).toBeInTheDocument()
  })

  it('requests the page/sort/filter values encoded in the URL', async () => {
    letterService.list.mockResolvedValue({ items: [], total: 0, page: 2, page_size: 25, total_pages: 3 })

    renderPage(['/app/letters?page=2&sort_by=subject&sort_order=asc&subject=budget'])

    await waitFor(() => expect(letterService.list).toHaveBeenCalled())
    const params = letterService.list.mock.calls[0][0]
    expect(params).toMatchObject({ page: 2, sort_by: 'subject', sort_order: 'asc', subject: 'budget' })
  })

  it('resets to page 1 when a filter is applied', async () => {
    letterService.list.mockResolvedValue({
      items: [makeLetter()],
      total: 1,
      page: 1,
      page_size: 25,
      total_pages: 1,
    })

    renderPage(['/app/letters?page=3'])
    await screen.findByText('REF-001')

    await userEvent.type(screen.getByLabelText(/^subject$/i), 'budget')
    await userEvent.click(screen.getByRole('button', { name: /apply filters/i }))

    await waitFor(() => {
      const lastCall = letterService.list.mock.calls.at(-1)[0]
      expect(lastCall).toMatchObject({ page: 1, subject: 'budget' })
    })
  })

  it('clears filters and resets to page 1 and default sort', async () => {
    letterService.list.mockResolvedValue({
      items: [makeLetter()],
      total: 1,
      page: 1,
      page_size: 25,
      total_pages: 1,
    })

    renderPage(['/app/letters?page=2&subject=budget&sort_by=subject&sort_order=asc'])
    await screen.findByText('REF-001')

    await userEvent.click(screen.getByRole('button', { name: /clear filters/i }))

    await waitFor(() => {
      const lastCall = letterService.list.mock.calls.at(-1)[0]
      expect(lastCall).toMatchObject({ page: 1, sort_by: 'received_at', sort_order: 'desc' })
      expect(lastCall.subject).toBeUndefined()
    })
  })

  it('toggles sort order when the same column header is clicked twice', async () => {
    letterService.list.mockResolvedValue({
      items: [makeLetter()],
      total: 1,
      page: 1,
      page_size: 25,
      total_pages: 1,
    })

    renderPage()
    await screen.findByText('REF-001')

    await userEvent.click(screen.getByRole('button', { name: /subject/i }))
    await waitFor(() => {
      expect(letterService.list.mock.calls.at(-1)[0]).toMatchObject({ sort_by: 'subject', sort_order: 'asc' })
    })

    await userEvent.click(screen.getByRole('button', { name: /subject/i }))
    await waitFor(() => {
      expect(letterService.list.mock.calls.at(-1)[0]).toMatchObject({ sort_by: 'subject', sort_order: 'desc' })
    })
  })

  it('shows a Record New Letter link for USER but not SYSTEM_ADMIN', async () => {
    letterService.list.mockResolvedValue({ items: [], total: 0, page: 1, page_size: 25, total_pages: 0 })
    renderPage()
    expect(await screen.findByRole('link', { name: /record new letter/i })).toBeInTheDocument()
  })

  it('does not show a Record New Letter link, and shows a department column, for SYSTEM_ADMIN', async () => {
    mockUseAuth.mockReturnValue({ user: SYSTEM_ADMIN_ROLE })
    categoryService.list.mockResolvedValue({ items: [], total: 0 })
    classificationService.list.mockResolvedValue({ items: [], total: 0 })
    departmentService.list.mockResolvedValue({
      items: [{ id: 'd1', name: 'Finance Department', status: 'ACTIVE' }],
      total: 1,
    })
    letterService.list.mockResolvedValue({
      items: [makeLetter()],
      total: 1,
      page: 1,
      page_size: 25,
      total_pages: 1,
    })

    renderPage()

    await screen.findByText('REF-001')
    expect(screen.queryByRole('link', { name: /record new letter/i })).not.toBeInTheDocument()
    const table = screen.getByRole('table')
    expect(await within(table).findByText('Finance Department')).toBeInTheDocument()
  })

  it('never issues a request for category/classification/department reference data as a non-SYSTEM_ADMIN', async () => {
    letterService.list.mockResolvedValue({ items: [], total: 0, page: 1, page_size: 25, total_pages: 0 })
    renderPage()
    await waitFor(() => expect(letterService.list).toHaveBeenCalled())
    expect(categoryService.list).not.toHaveBeenCalled()
    expect(classificationService.list).not.toHaveBeenCalled()
    expect(departmentService.list).not.toHaveBeenCalled()
  })
})
