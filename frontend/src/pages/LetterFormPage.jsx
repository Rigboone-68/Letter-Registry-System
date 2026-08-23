import { useCallback, useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'

import ErrorState from '../components/ErrorState'
import LoadingState from '../components/LoadingState'
import { useAuth } from '../context/AuthContext'
import * as categoryService from '../services/categoryService'
import * as classificationService from '../services/classificationService'
import * as letterService from '../services/letterService'
import { validateLetterForm } from '../utils/formValidation'
import styles from './LetterFormPage.module.css'

const EMPTY_FORM = {
  reference_number: '',
  subject: '',
  source_name: '',
  source_location: '',
  sender_name: '',
  sender_designation: '',
  sender_department: '',
  sender_address: '',
  reason: '',
  received_at: '',
  text_content: '',
  category_id: '',
  classification_id: '',
}

function toDatetimeLocalValue(isoString) {
  if (!isoString) return ''
  const date = new Date(isoString)
  const pad = (n) => String(n).padStart(2, '0')
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`
}

function fromDatetimeLocalValue(value) {
  if (!value) return null
  return new Date(value).toISOString()
}

function fieldProps(name, form, fieldErrors, onChange) {
  return {
    id: name,
    name,
    value: form[name],
    onChange,
    'aria-invalid': Boolean(fieldErrors[name]),
    'aria-describedby': fieldErrors[name] ? `${name}-error` : undefined,
  }
}

function FieldError({ name, fieldErrors }) {
  if (!fieldErrors[name]) return null
  return (
    <span id={`${name}-error`} role="alert" className={styles.fieldError}>
      {fieldErrors[name]}
    </span>
  )
}

/**
 * Letter create/edit form (docs/architecture/frontend.md §9/§10,
 * Phase 5C) — one component for both `/app/letters/new` (create,
 * `POST /api/v1/letters`) and `/app/letters/:id/edit` (edit,
 * `PATCH /api/v1/letters/:id`), the same reuse pattern
 * `docs/architecture/frontend.md` §31 recommends.
 *
 * Fields shown are exactly `LetterCreate`'s field set
 * (backend/app/schemas/letter.py, `extra="forbid"`) minus two
 * deliberately omitted, documented exceptions:
 *
 *   - `source_department_id` — an optional structured cross-reference to
 *     an LRS department; omitted from this V1 form because resolving it
 *     to a selectable name requires `GET /api/v1/departments`
 *     (SYSTEM_ADMIN-only) and `source_name` (always required, always
 *     shown) already conveys the source in human-readable form. A
 *     scope simplification, not a backend blocker.
 *   - `category_id`/`classification_id` — a CONFIRMED backend-contract
 *     gap, not a simplification: `GET /api/v1/categories` and
 *     `/classifications` are both `require_system_admin`-only
 *     (`app/api/v1/endpoints/{categories,classifications}.py`), but
 *     `POST /api/v1/letters` is USER/ADMIN-only
 *     (`require_user_or_admin` — SYSTEM_ADMIN has no department to
 *     record a letter against). No caller of the create form can ever
 *     legitimately load the option list, so these two fields never
 *     appear on create. On edit, they appear only for a SYSTEM_ADMIN
 *     caller (the only role that can both load the options and, per
 *     `assert_letter_access`'s SYSTEM_ADMIN bypass, edit any letter) —
 *     a USER/ADMIN editing a letter simply never touches these two
 *     fields, and the backend's own "omitted field means unchanged"
 *     `LetterUpdate` semantics leave whatever value was already there
 *     untouched.
 *
 * `id`/`recipient_department_id`/`recorded_by`/`status`/`created_at`/
 * `updated_at` have no field in `EMPTY_FORM` at all — there is nothing
 * here for a client value to bind to even accidentally.
 */
export default function LetterFormPage() {
  const { id } = useParams()
  const isEdit = Boolean(id)
  const navigate = useNavigate()
  const { user } = useAuth()
  const isSystemAdmin = user?.role === 'SYSTEM_ADMIN'

  const [form, setForm] = useState(EMPTY_FORM)
  const [fieldErrors, setFieldErrors] = useState({})
  const [formError, setFormError] = useState(null)
  const [submitting, setSubmitting] = useState(false)
  const [initialLoading, setInitialLoading] = useState(isEdit)
  const [notFound, setNotFound] = useState(false)
  const [loadError, setLoadError] = useState(null)
  const [referenceOptions, setReferenceOptions] = useState({ categories: null, classifications: null })

  useEffect(() => {
    if (!isEdit) return
    letterService
      .get(id)
      .then((letter) => {
        setForm({
          reference_number: letter.reference_number,
          subject: letter.subject ?? '',
          source_name: letter.source_name,
          source_location: letter.source_location ?? '',
          sender_name: letter.sender_name,
          sender_designation: letter.sender_designation,
          sender_department: letter.sender_department,
          sender_address: letter.sender_address ?? '',
          reason: letter.reason ?? '',
          received_at: toDatetimeLocalValue(letter.received_at),
          text_content: letter.text_content ?? '',
          category_id: letter.category_id ?? '',
          classification_id: letter.classification_id ?? '',
        })
      })
      .catch((normalizedError) => {
        if (normalizedError.status === 404) {
          setNotFound(true)
        } else {
          setLoadError(normalizedError)
        }
      })
      .finally(() => setInitialLoading(false))
  }, [id, isEdit])

  useEffect(() => {
    if (!isSystemAdmin || !isEdit) return
    Promise.all([categoryService.list(), classificationService.list()])
      .then(([categories, classifications]) => {
        setReferenceOptions({ categories: categories.items, classifications: classifications.items })
      })
      .catch(() => {
        // Reference-data loading is a convenience for SYSTEM_ADMIN edits
        // only — a failure here degrades to no category/classification
        // selector rather than blocking the rest of the form.
      })
  }, [isSystemAdmin, isEdit])

  const handleChange = useCallback((event) => {
    const { name, value } = event.target
    setForm((previous) => ({ ...previous, [name]: value }))
  }, [])

  function buildPayload() {
    const payload = {
      reference_number: form.reference_number,
      subject: form.subject,
      source_name: form.source_name,
      source_location: form.source_location || null,
      sender_name: form.sender_name,
      sender_designation: form.sender_designation,
      sender_department: form.sender_department,
      sender_address: form.sender_address || null,
      reason: form.reason || null,
      received_at: fromDatetimeLocalValue(form.received_at),
      text_content: form.text_content || null,
    }
    if (isSystemAdmin && isEdit) {
      // Only ever sent when a value is actually chosen — the backend's
      // "omitted means unchanged" LetterUpdate semantics mean sending
      // an explicit null would silently no-op rather than clear an
      // existing value (a known, pre-existing backend limitation; see
      // docs/architecture/frontend.md §10), so this form never attempts
      // that and never implies it worked.
      if (form.category_id) payload.category_id = form.category_id
      if (form.classification_id) payload.classification_id = form.classification_id
    }
    return payload
  }

  async function handleSubmit(event) {
    event.preventDefault()
    setFormError(null)

    const errors = validateLetterForm(form)
    setFieldErrors(errors)
    if (Object.keys(errors).length > 0) return

    setSubmitting(true)
    try {
      const payload = buildPayload()
      const result = isEdit ? await letterService.update(id, payload) : await letterService.create(payload)
      navigate(`/app/letters/${result.id}`, { replace: true })
    } catch (normalizedError) {
      if (normalizedError.fieldErrors) {
        setFieldErrors(normalizedError.fieldErrors)
      } else {
        setFormError(normalizedError.message ?? 'Unable to save this letter.')
      }
    } finally {
      setSubmitting(false)
    }
  }

  function handleCancel() {
    navigate(isEdit ? `/app/letters/${id}` : '/app/letters')
  }

  if (initialLoading) return <LoadingState label="Loading letter..." />
  if (notFound) return <ErrorState message="Letter not found." />
  if (loadError) return <ErrorState message={loadError.message} />

  return (
    <section className={styles.root}>
      <h1>{isEdit ? 'Edit Letter' : 'Record New Letter'}</h1>

      <form onSubmit={handleSubmit} noValidate className={styles.form}>
        {formError && <ErrorState message={formError} />}

        <fieldset className={styles.fieldset}>
          <legend>Reference &amp; subject</legend>
          <div className={styles.field}>
            <label htmlFor="reference_number">Reference number *</label>
            <input type="text" required {...fieldProps('reference_number', form, fieldErrors, handleChange)} />
            <FieldError name="reference_number" fieldErrors={fieldErrors} />
          </div>
          <div className={styles.field}>
            <label htmlFor="subject">Subject *</label>
            <input type="text" required {...fieldProps('subject', form, fieldErrors, handleChange)} />
            <FieldError name="subject" fieldErrors={fieldErrors} />
          </div>
          <div className={styles.field}>
            <label htmlFor="received_at">Received date/time *</label>
            <input type="datetime-local" required {...fieldProps('received_at', form, fieldErrors, handleChange)} />
            <FieldError name="received_at" fieldErrors={fieldErrors} />
          </div>
        </fieldset>

        <fieldset className={styles.fieldset}>
          <legend>Source</legend>
          <div className={styles.field}>
            <label htmlFor="source_name">Source name *</label>
            <input type="text" required {...fieldProps('source_name', form, fieldErrors, handleChange)} />
            <FieldError name="source_name" fieldErrors={fieldErrors} />
          </div>
          <div className={styles.field}>
            <label htmlFor="source_location">Source location</label>
            <input type="text" {...fieldProps('source_location', form, fieldErrors, handleChange)} />
          </div>
        </fieldset>

        <fieldset className={styles.fieldset}>
          <legend>Sender</legend>
          <div className={styles.field}>
            <label htmlFor="sender_name">Sender name *</label>
            <input type="text" required {...fieldProps('sender_name', form, fieldErrors, handleChange)} />
            <FieldError name="sender_name" fieldErrors={fieldErrors} />
          </div>
          <div className={styles.field}>
            <label htmlFor="sender_designation">Sender designation *</label>
            <input type="text" required {...fieldProps('sender_designation', form, fieldErrors, handleChange)} />
            <FieldError name="sender_designation" fieldErrors={fieldErrors} />
          </div>
          <div className={styles.field}>
            <label htmlFor="sender_department">Sender's department *</label>
            <input type="text" required {...fieldProps('sender_department', form, fieldErrors, handleChange)} />
            <p className={styles.hint}>
              Free text describing the sender's own department — distinct from
              "Source," which may or may not be the same organization.
            </p>
            <FieldError name="sender_department" fieldErrors={fieldErrors} />
          </div>
          <div className={styles.field}>
            <label htmlFor="sender_address">Sender address</label>
            <textarea rows={2} {...fieldProps('sender_address', form, fieldErrors, handleChange)} />
          </div>
        </fieldset>

        <fieldset className={styles.fieldset}>
          <legend>Additional details</legend>
          <div className={styles.field}>
            <label htmlFor="reason">Reason</label>
            <textarea rows={2} {...fieldProps('reason', form, fieldErrors, handleChange)} />
          </div>
          <div className={styles.field}>
            <label htmlFor="text_content">Content</label>
            <textarea rows={5} {...fieldProps('text_content', form, fieldErrors, handleChange)} />
          </div>

          {isSystemAdmin && isEdit && (
            <>
              <p className={styles.hint}>
                Category and Classification are only editable here as
                SYSTEM_ADMIN. Once set, choosing "Unassigned" has no effect —
                the backend currently has no way to clear either field back to
                unassigned through this endpoint.
              </p>
              <div className={styles.field}>
                <label htmlFor="category_id">Category</label>
                <select {...fieldProps('category_id', form, fieldErrors, handleChange)}>
                  <option value="">Unassigned</option>
                  {referenceOptions.categories?.map((option) => (
                    <option key={option.id} value={option.id}>
                      {option.name}
                      {option.status === 'INACTIVE' ? ' (inactive)' : ''}
                    </option>
                  ))}
                </select>
              </div>
              <div className={styles.field}>
                <label htmlFor="classification_id">Classification</label>
                <select {...fieldProps('classification_id', form, fieldErrors, handleChange)}>
                  <option value="">Unassigned</option>
                  {referenceOptions.classifications?.map((option) => (
                    <option key={option.id} value={option.id}>
                      {option.name}
                      {option.status === 'INACTIVE' ? ' (inactive)' : ''}
                    </option>
                  ))}
                </select>
              </div>
            </>
          )}
        </fieldset>

        <div className={styles.actions}>
          <button type="submit" className={styles.submit} disabled={submitting}>
            {submitting ? 'Saving…' : isEdit ? 'Save changes' : 'Record Letter'}
          </button>
          <button type="button" onClick={handleCancel} className={styles.cancel}>
            Cancel
          </button>
        </div>
      </form>
    </section>
  )
}
