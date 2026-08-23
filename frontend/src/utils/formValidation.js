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
