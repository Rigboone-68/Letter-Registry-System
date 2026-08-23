/**
 * Lightweight, dependency-free client-side validation for the auth forms
 * (docs/architecture/frontend.md — Phase 5B). This exists purely to give
 * immediate, accessible feedback for the obvious cases (an empty
 * required field, an obviously malformed email, a mismatched password
 * confirmation) before a request is even sent — it is never a
 * replacement for backend validation, which remains authoritative and
 * is re-checked on every submission regardless of what this reports.
 */

const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/

export function isBlank(value) {
  return !value || value.trim().length === 0
}

export function isValidEmailFormat(value) {
  return EMAIL_PATTERN.test(value)
}

export function validateLoginForm({ email, password }) {
  const errors = {}

  if (isBlank(email)) {
    errors.email = 'Email is required.'
  } else if (!isValidEmailFormat(email)) {
    errors.email = 'Enter a valid email address.'
  }

  if (isBlank(password)) {
    errors.password = 'Password is required.'
  }

  return errors
}

export function validateSignupForm({ full_name, email, password, password_confirm }) {
  const errors = {}

  if (isBlank(full_name)) {
    errors.full_name = 'Full name is required.'
  }

  if (isBlank(email)) {
    errors.email = 'Email is required.'
  } else if (!isValidEmailFormat(email)) {
    errors.email = 'Enter a valid email address.'
  }

  if (isBlank(password)) {
    errors.password = 'Password is required.'
  }

  if (isBlank(password_confirm)) {
    errors.password_confirm = 'Please confirm your password.'
  } else if (!isBlank(password) && password !== password_confirm) {
    errors.password_confirm = 'Passwords do not match.'
  }

  return errors
}

const LETTER_REQUIRED_FIELDS = [
  ['reference_number', 'Reference number is required.'],
  ['subject', 'Subject is required.'],
  ['source_name', 'Source is required.'],
  ['sender_name', 'Sender name is required.'],
  ['sender_designation', 'Sender designation is required.'],
  ['sender_department', "Sender's department is required."],
]

/**
 * Mirrors `LetterCreate`'s own required-field set
 * (backend/app/schemas/letter.py) — every field here is required at
 * creation per the finalized Phase 4B business decisions; everything
 * else on the schema is optional. `received_at` is validated separately
 * since it's a datetime, not a blank-checked string.
 */
export function validateLetterForm({ reference_number, subject, source_name, sender_name, sender_designation, sender_department, received_at }) {
  const values = { reference_number, subject, source_name, sender_name, sender_designation, sender_department }
  const errors = {}

  for (const [field, message] of LETTER_REQUIRED_FIELDS) {
    if (isBlank(values[field])) {
      errors[field] = message
    }
  }

  if (isBlank(received_at)) {
    errors.received_at = 'Received date is required.'
  }

  return errors
}
