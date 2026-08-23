import { describe, expect, it } from 'vitest'

import {
  validateAdminAuthorizeForm,
  validateDepartmentForm,
  validateDocumentFile,
  validateLetterForm,
  validateLoginForm,
  validateSignupForm,
  validateUserAuthorizeForm,
} from './formValidation'

describe('validateLoginForm', () => {
  it('requires email and password', () => {
    const errors = validateLoginForm({ email: '', password: '' })
    expect(errors.email).toMatch(/required/i)
    expect(errors.password).toMatch(/required/i)
  })

  it('rejects an obviously malformed email', () => {
    const errors = validateLoginForm({ email: 'not-an-email', password: 'secret' })
    expect(errors.email).toMatch(/valid email/i)
  })

  it('passes for a well-formed submission', () => {
    const errors = validateLoginForm({ email: 'jane@example.gov', password: 'secret' })
    expect(errors).toEqual({})
  })
})

describe('validateSignupForm', () => {
  it('requires every field', () => {
    const errors = validateSignupForm({ full_name: '', email: '', password: '', password_confirm: '' })
    expect(errors.full_name).toMatch(/required/i)
    expect(errors.email).toMatch(/required/i)
    expect(errors.password).toMatch(/required/i)
    expect(errors.password_confirm).toMatch(/confirm/i)
  })

  it('flags a mismatched password confirmation', () => {
    const errors = validateSignupForm({
      full_name: 'Jane User',
      email: 'jane@example.gov',
      password: 'password123',
      password_confirm: 'different',
    })
    expect(errors.password_confirm).toMatch(/do not match/i)
  })

  it('passes for a well-formed submission', () => {
    const errors = validateSignupForm({
      full_name: 'Jane User',
      email: 'jane@example.gov',
      password: 'password123',
      password_confirm: 'password123',
    })
    expect(errors).toEqual({})
  })
})

describe('validateLetterForm', () => {
  const VALID = {
    reference_number: 'REF-001',
    subject: 'Budget approval',
    source_name: 'Ministry of Finance',
    sender_name: 'Jane Sender',
    sender_designation: 'Director',
    sender_department: 'Finance',
    received_at: '2026-01-01T09:00',
  }

  it('requires every mandatory field', () => {
    const errors = validateLetterForm({
      reference_number: '',
      subject: '',
      source_name: '',
      sender_name: '',
      sender_designation: '',
      sender_department: '',
      received_at: '',
    })
    expect(errors.reference_number).toMatch(/required/i)
    expect(errors.subject).toMatch(/required/i)
    expect(errors.source_name).toMatch(/required/i)
    expect(errors.sender_name).toMatch(/required/i)
    expect(errors.sender_designation).toMatch(/required/i)
    expect(errors.sender_department).toMatch(/required/i)
    expect(errors.received_at).toMatch(/required/i)
  })

  it('passes for a well-formed submission', () => {
    expect(validateLetterForm(VALID)).toEqual({})
  })

  it('does not require optional fields', () => {
    const errors = validateLetterForm(VALID)
    expect(errors.source_location).toBeUndefined()
    expect(errors.reason).toBeUndefined()
    expect(errors.category_id).toBeUndefined()
  })
})

describe('validateDepartmentForm', () => {
  it('requires name', () => {
    expect(validateDepartmentForm({ name: '' }).name).toMatch(/required/i)
  })

  it('does not require code', () => {
    const errors = validateDepartmentForm({ name: 'Finance' })
    expect(errors.code).toBeUndefined()
    expect(errors).toEqual({})
  })
})

describe('validateAdminAuthorizeForm', () => {
  it('requires email and department_id', () => {
    const errors = validateAdminAuthorizeForm({ email: '', department_id: '' })
    expect(errors.email).toMatch(/required/i)
    expect(errors.department_id).toMatch(/required/i)
  })

  it('rejects a malformed email', () => {
    const errors = validateAdminAuthorizeForm({ email: 'not-an-email', department_id: 'd1' })
    expect(errors.email).toMatch(/valid email/i)
  })

  it('passes for a well-formed submission', () => {
    expect(validateAdminAuthorizeForm({ email: 'jane@example.gov', department_id: 'd1' })).toEqual({})
  })
})

describe('validateUserAuthorizeForm', () => {
  it('requires email only', () => {
    const errors = validateUserAuthorizeForm({ email: '' })
    expect(errors.email).toMatch(/required/i)
    expect(errors.department_id).toBeUndefined()
  })

  it('passes for a well-formed submission', () => {
    expect(validateUserAuthorizeForm({ email: 'jane@example.gov' })).toEqual({})
  })
})

describe('validateDocumentFile', () => {
  const OPTIONS = { allowedExtensions: ['pdf', 'jpg', 'jpeg', 'png', 'txt'], maxSizeBytes: 10 * 1024 * 1024 }

  function makeFile({ name = 'letter.pdf', size = 1024 } = {}) {
    const file = new File([new Uint8Array(size)], name)
    return file
  }

  it('requires a file to be selected', () => {
    expect(validateDocumentFile(null, OPTIONS)).toMatch(/select a file/i)
  })

  it('rejects an unsupported extension', () => {
    expect(validateDocumentFile(makeFile({ name: 'archive.zip' }), OPTIONS)).toMatch(/unsupported file type/i)
  })

  it('rejects an oversized file', () => {
    expect(validateDocumentFile(makeFile({ size: OPTIONS.maxSizeBytes + 1 }), OPTIONS)).toMatch(
      /exceeds the maximum allowed size/i
    )
  })

  it('rejects an empty file', () => {
    expect(validateDocumentFile(makeFile({ size: 0 }), OPTIONS)).toMatch(/empty/i)
  })

  it('passes for a well-formed file', () => {
    expect(validateDocumentFile(makeFile(), OPTIONS)).toBeNull()
  })
})
