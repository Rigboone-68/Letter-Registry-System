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
  ['sender_name', 'Sender name is required.'],
  ['sender_department', "Sender's department is required."],
]

/**
 * Mirrors `LetterCreate`'s own required-field set
 * (backend/app/schemas/letter.py) — every field here is required at
 * creation per the finalized Phase 4B business decisions; everything
 * else on the schema is optional. `received_at` is validated separately
 * since it's a datetime, not a blank-checked string.
 *
 * `source_department_id`/`designation_id` (Phase 5H) are validated here
 * instead of `source_name`/`sender_designation` — the backend schema
 * itself still requires the latter two as text, but this V1 form no
 * longer offers a manual text box for either (`LetterFormPage.jsx`
 * derives both from the selected Department/Designation and sends them
 * alongside the id) — see docs/architecture/source-designation.md
 * §12/§13. This is a frontend UX decision, not a backend contract
 * change: `source_department_id`/`designation_id` remain optional on
 * `LetterCreate`/`LetterUpdate` themselves.
 *
 * **Required only when creating** (`isEdit: false`, the default) — a
 * Letter recorded before Phase 5H legitimately has neither field set,
 * and editing an unrelated field (e.g. fixing a typo in Subject) must
 * not be blocked into retroactively demanding a Source Department or
 * Designation it never had. This mirrors the backend's own "an
 * omitted/unchanged field is never re-validated" convention
 * (docs/architecture/source-designation.md §9) at the frontend layer.
 */
export function validateLetterForm(
  {
    reference_number,
    subject,
    source_department_id,
    sender_name,
    designation_id,
    sender_department,
    received_at,
    direction,
    dispatch_department_id,
  },
  { isEdit = false } = {}
) {
  const values = { reference_number, subject, sender_name, sender_department }
  const errors = {}

  for (const [field, message] of LETTER_REQUIRED_FIELDS) {
    if (isBlank(values[field])) {
      errors[field] = message
    }
  }

  if (!isEdit) {
    if (isBlank(source_department_id)) {
      errors.source_department_id = 'Source Department is required.'
    }
    if (isBlank(designation_id)) {
      errors.designation_id = 'Designation is required.'
    }
    // Correspondence direction (Phase 6A) is write-once at creation —
    // there is no field for it on `LetterUpdate` at all, so this rule
    // never applies on edit, mirroring Source Department/Designation
    // above exactly.
    if (direction === 'OUTGOING' && isBlank(dispatch_department_id)) {
      errors.dispatch_department_id = 'Dispatch Department is required for outgoing correspondence.'
    }
  }

  if (isBlank(received_at)) {
    errors.received_at = 'Received date is required.'
  }

  return errors
}

/**
 * Mirrors `DepartmentCreate`/`DepartmentUpdate`'s own required-ness
 * (backend/app/schemas/department.py): `name` is always required at
 * creation; `code` is always optional. `DepartmentUpdate`'s own
 * "at least one of name or code" rule is a server-side edit-mode
 * concern (nothing to validate client-side for a create form, which
 * always supplies a name), so it is not duplicated here.
 */
export function validateDepartmentForm({ name }) {
  const errors = {}

  if (isBlank(name)) {
    errors.name = 'Name is required.'
  }

  return errors
}

/**
 * Mirrors `validateDepartmentForm` — `DesignationCreate`
 * (backend/app/schemas/designation.py) has exactly one field, `name`,
 * always required. Case-insensitive/duplicate handling is entirely the
 * backend's own job (`uq_designations_name_lower`); this form only
 * catches the trivial empty-string case before a request is even sent.
 */
export function validateDesignationForm({ name }) {
  const errors = {}

  if (isBlank(name)) {
    errors.name = 'Name is required.'
  }

  return errors
}

/**
 * Mirrors `validateDepartmentForm` — `CategoryCreate`
 * (backend/app/schemas/category.py) requires `name`; `description` is
 * always optional. Duplicate-name handling is entirely the backend's
 * own job (`uq_categories_name`).
 */
export function validateCategoryForm({ name }) {
  const errors = {}

  if (isBlank(name)) {
    errors.name = 'Name is required.'
  }

  return errors
}

/**
 * Mirrors `validateCategoryForm` — `ClassificationCreate`
 * (backend/app/schemas/classification.py) requires `name`;
 * `description`/`restricts_access` are always optional (the latter
 * defaults `false` server-side if omitted). This form never validates
 * `restricts_access` itself — it's a plain boolean checkbox, nothing to
 * validate.
 */
export function validateClassificationForm({ name }) {
  const errors = {}

  if (isBlank(name)) {
    errors.name = 'Name is required.'
  }

  return errors
}

/**
 * Mirrors `AdminAuthorizationCreate` (backend/app/schemas/admin.py):
 * `email` and `department_id` are both required — a System Admin
 * genuinely chooses a destination department, unlike User
 * authorization below.
 */
export function validateAdminAuthorizeForm({ email, department_id }) {
  const errors = {}

  if (isBlank(email)) {
    errors.email = 'Email is required.'
  } else if (!isValidEmailFormat(email)) {
    errors.email = 'Enter a valid email address.'
  }

  if (isBlank(department_id)) {
    errors.department_id = 'Department is required.'
  }

  return errors
}

/**
 * Mirrors `UserAuthorizationCreate` (backend/app/schemas/user.py):
 * `email` only — there is no `department_id` field on this schema at
 * all, since it is always derived from the calling Admin's own
 * department server-side.
 */
export function validateUserAuthorizeForm({ email }) {
  const errors = {}

  if (isBlank(email)) {
    errors.email = 'Email is required.'
  } else if (!isValidEmailFormat(email)) {
    errors.email = 'Enter a valid email address.'
  }

  return errors
}

/**
 * A UX-nicety pre-check only, mirroring the backend's own confirmed
 * pipeline (backend/app/services/document_validation.py) as closely as
 * a filename/size check can — the backend's magic-byte content-
 * signature sniff remains the sole authority; a file that passes this
 * check can still be rejected by the backend with a `422` if its actual
 * bytes don't match its extension, and this function never claims
 * otherwise (docs/architecture/document-notification-ui.md §3.4).
 * Returns a single error string, or `null` if the file passes every
 * client-side check.
 */
export function validateDocumentFile(file, { allowedExtensions, maxSizeBytes }) {
  if (!file) {
    return 'Select a file to upload.'
  }

  const extension = file.name.includes('.') ? file.name.split('.').pop().toLowerCase() : ''
  if (!allowedExtensions.includes(extension)) {
    return `Unsupported file type. Accepted types: ${allowedExtensions.join(', ')}.`
  }

  if (file.size === 0) {
    return 'Selected file is empty.'
  }

  if (file.size > maxSizeBytes) {
    const maxMb = (maxSizeBytes / (1024 * 1024)).toFixed(0)
    return `File exceeds the maximum allowed size of ${maxMb} MB.`
  }

  return null
}
