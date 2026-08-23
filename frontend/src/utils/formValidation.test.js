import { describe, expect, it } from 'vitest'

import { validateLoginForm, validateSignupForm } from './formValidation'

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
