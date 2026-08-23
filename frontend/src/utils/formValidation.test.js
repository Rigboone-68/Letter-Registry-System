import { describe, expect, it } from 'vitest'

import { validateLetterForm, validateLoginForm, validateSignupForm } from './formValidation'

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
