import { describe, expect, it } from 'vitest'

import { normalizeApiError } from './errorNormalization'

describe('normalizeApiError', () => {
  it('normalizes a plain-string detail (a raised HTTPException)', () => {
    const error = {
      response: { status: 403, data: { detail: 'Your account has been deactivated.' } },
    }

    expect(normalizeApiError(error)).toEqual({
      status: 403,
      message: 'Your account has been deactivated.',
      fieldErrors: null,
    })
  })

  it('normalizes an array-shaped detail (a Pydantic validation failure) into fieldErrors', () => {
    const error = {
      response: {
        status: 422,
        data: {
          detail: [
            { loc: ['body', 'password_confirm'], msg: 'field required', type: 'missing' },
            { loc: ['body', 'email'], msg: 'value is not a valid email address', type: 'value_error' },
          ],
        },
      },
    }

    const result = normalizeApiError(error)

    expect(result.status).toBe(422)
    expect(result.fieldErrors).toEqual({
      password_confirm: 'field required',
      email: 'value is not a valid email address',
    })
  })

  it('normalizes a network failure (no response at all)', () => {
    const result = normalizeApiError({ response: undefined })

    expect(result.status).toBe(0)
    expect(result.message).toMatch(/reach the server/i)
    expect(result.fieldErrors).toBeNull()
  })

  it('falls back to a generic message for an unexpected body shape', () => {
    const error = { response: { status: 500, data: {} } }

    const result = normalizeApiError(error)

    expect(result.status).toBe(500)
    expect(result.message).toMatch(/unexpected/i)
    expect(result.fieldErrors).toBeNull()
  })
})
