import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import LetterFormPage from './LetterFormPage'

const mockUseAuth = vi.fn()
vi.mock('../context/AuthContext', () => ({
  useAuth: () => mockUseAuth(),
}))

vi.mock('../services/letterService', async () => {
  const actual = await vi.importActual('../services/letterService')
  return { ...actual, get: vi.fn(), create: vi.fn(), update: vi.fn() }
})
vi.mock('../services/categoryService', () => ({ list: vi.fn() }))
vi.mock('../services/classificationService', () => ({ list: vi.fn() }))

import * as categoryService from '../services/categoryService'
import * as classificationService from '../services/classificationService'
import * as letterService from '../services/letterService'

const USER_ROLE = { id: 'u1', role: 'USER', department_id: 'd1' }
const SYSTEM_ADMIN_ROLE = { id: 'u2', role: 'SYSTEM_ADMIN', department_id: null }

const EDIT_LETTER = {
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
  reason: null,
  category_id: null,
  classification_id: null,
  received_at: '2026-01-05T09:00:00Z',
  recorded_by: 'u1',
  text_content: null,
  status: 'ACTIVE',
  created_at: '2026-01-05T09:00:00Z',
  updated_at: '2026-01-05T09:00:00Z',
}

function renderCreate() {
  return render(
    <MemoryRouter initialEntries={['/app/letters/new']}>
      <Routes>
        <Route path="/app/letters" element={<div>Registry List</div>} />
        <Route path="/app/letters/new" element={<LetterFormPage />} />
        <Route path="/app/letters/:id" element={<div>Detail Page</div>} />
      </Routes>
    </MemoryRouter>
  )
}

function renderEdit(id = 'l1') {
  return render(
    <MemoryRouter initialEntries={[`/app/letters/${id}/edit`]}>
      <Routes>
        <Route path="/app/letters/:id" element={<div>Detail Page</div>} />
        <Route path="/app/letters/:id/edit" element={<LetterFormPage />} />
      </Routes>
    </MemoryRouter>
  )
}

async function fillRequiredFields() {
  await userEvent.type(screen.getByLabelText(/reference number/i), 'REF-002')
  await userEvent.type(screen.getByLabelText(/^subject/i), 'New subject')
  await userEvent.type(screen.getByLabelText(/received date/i), '2026-02-01T10:00')
  await userEvent.type(screen.getByLabelText(/source name/i), 'Ministry of Health')
  await userEvent.type(screen.getByLabelText(/sender name/i), 'John Sender')
  await userEvent.type(screen.getByLabelText(/sender designation/i), 'Officer')
  await userEvent.type(screen.getByLabelText(/sender's department/i), 'Health')
}

describe('LetterFormPage — create', () => {
  beforeEach(() => {
    vi.resetAllMocks()
    mockUseAuth.mockReturnValue({ user: USER_ROLE })
  })

  it('requires the mandatory fields before submitting', async () => {
    renderCreate()
    await userEvent.click(screen.getByRole('button', { name: /record letter/i }))

    expect(await screen.findByText(/reference number is required/i)).toBeInTheDocument()
    expect(letterService.create).not.toHaveBeenCalled()
  })

  it('creates successfully and navigates to the new letter', async () => {
    letterService.create.mockResolvedValue({ ...EDIT_LETTER, id: 'new-id', reference_number: 'REF-002' })
    renderCreate()

    await fillRequiredFields()
    await userEvent.click(screen.getByRole('button', { name: /record letter/i }))

    await waitFor(() => expect(screen.getByText('Detail Page')).toBeInTheDocument())
  })

  it('displays field errors from a 422 response', async () => {
    letterService.create.mockRejectedValue({
      status: 422,
      message: 'Please correct the highlighted fields.',
      fieldErrors: { reference_number: 'must not be blank.' },
    })
    renderCreate()
    await fillRequiredFields()
    await userEvent.click(screen.getByRole('button', { name: /record letter/i }))

    expect(await screen.findByText('must not be blank.')).toBeInTheDocument()
  })

  it('shows a generic forbidden message for a 403', async () => {
    letterService.create.mockRejectedValue({
      status: 403,
      message: 'You do not have permission to perform this action.',
      fieldErrors: null,
    })
    renderCreate()
    await fillRequiredFields()
    await userEvent.click(screen.getByRole('button', { name: /record letter/i }))

    expect(await screen.findByRole('alert')).toHaveTextContent(/do not have permission/i)
  })

  it('never sends recipient_department_id, recorded_by, status, or category/classification', async () => {
    letterService.create.mockResolvedValue({ ...EDIT_LETTER, id: 'new-id' })
    renderCreate()
    await fillRequiredFields()
    await userEvent.click(screen.getByRole('button', { name: /record letter/i }))

    await waitFor(() => expect(letterService.create).toHaveBeenCalled())
    const payload = letterService.create.mock.calls[0][0]
    expect(payload).not.toHaveProperty('recipient_department_id')
    expect(payload).not.toHaveProperty('recorded_by')
    expect(payload).not.toHaveProperty('status')
    expect(payload).not.toHaveProperty('id')
    expect(payload).not.toHaveProperty('category_id')
    expect(payload).not.toHaveProperty('classification_id')
  })

  it('does not render a category/classification selector on create for any role', () => {
    mockUseAuth.mockReturnValue({ user: SYSTEM_ADMIN_ROLE })
    renderCreate()
    expect(screen.queryByLabelText(/^category$/i)).not.toBeInTheDocument()
    expect(screen.queryByLabelText(/^classification$/i)).not.toBeInTheDocument()
  })
})

describe('LetterFormPage — edit', () => {
  beforeEach(() => {
    vi.resetAllMocks()
    mockUseAuth.mockReturnValue({ user: USER_ROLE })
  })

  it('loads the existing letter and pre-fills the form', async () => {
    letterService.get.mockResolvedValue(EDIT_LETTER)
    renderEdit()

    expect(await screen.findByDisplayValue('REF-001')).toBeInTheDocument()
    expect(screen.getByDisplayValue('Budget approval')).toBeInTheDocument()
  })

  it('renders a generic not-found state for a 404 on load', async () => {
    letterService.get.mockRejectedValue({ status: 404, message: 'Letter not found.', fieldErrors: null })
    renderEdit()

    expect(await screen.findByRole('alert')).toHaveTextContent('Letter not found.')
  })

  it('submits only the fields the backend allows and navigates to the detail page on success', async () => {
    letterService.get.mockResolvedValue(EDIT_LETTER)
    letterService.update.mockResolvedValue({ ...EDIT_LETTER, subject: 'Updated subject' })
    renderEdit()
    await screen.findByDisplayValue('REF-001')

    const subjectInput = screen.getByLabelText(/^subject/i)
    await userEvent.clear(subjectInput)
    await userEvent.type(subjectInput, 'Updated subject')
    await userEvent.click(screen.getByRole('button', { name: /save changes/i }))

    await waitFor(() => expect(screen.getByText('Detail Page')).toBeInTheDocument())
    const payload = letterService.update.mock.calls[0][1]
    expect(payload).not.toHaveProperty('recipient_department_id')
    expect(payload).not.toHaveProperty('recorded_by')
    expect(payload).not.toHaveProperty('status')
  })

  it('does not show a category/classification selector for USER', async () => {
    letterService.get.mockResolvedValue(EDIT_LETTER)
    renderEdit()
    await screen.findByDisplayValue('REF-001')

    expect(screen.queryByLabelText(/^category$/i)).not.toBeInTheDocument()
    expect(categoryService.list).not.toHaveBeenCalled()
  })

  it('shows a category/classification selector loaded from the API for SYSTEM_ADMIN', async () => {
    mockUseAuth.mockReturnValue({ user: SYSTEM_ADMIN_ROLE })
    letterService.get.mockResolvedValue(EDIT_LETTER)
    categoryService.list.mockResolvedValue({
      items: [{ id: 'c1', name: 'General Letter', status: 'ACTIVE' }],
      total: 1,
    })
    classificationService.list.mockResolvedValue({ items: [], total: 0 })
    renderEdit()
    await screen.findByDisplayValue('REF-001')

    expect(await screen.findByLabelText(/^category$/i)).toBeInTheDocument()
    expect(await screen.findByText('General Letter')).toBeInTheDocument()
  })
})
