import { useCallback, useEffect, useState } from 'react'
import { useLocation, useNavigate, useParams } from 'react-router-dom'

import DepartmentSelector from '../components/DepartmentSelector'
import ErrorState from '../components/ErrorState'
import LoadingState from '../components/LoadingState'
import { useAuth } from '../context/AuthContext'
import * as categoryService from '../services/categoryService'
import * as classificationService from '../services/classificationService'
import * as departmentService from '../services/departmentService'
import * as designationService from '../services/designationService'
import * as letterService from '../services/letterService'
import { LETTER_DIRECTION_OPTIONS } from '../services/letterService'
import { validateLetterForm } from '../utils/formValidation'
import styles from './LetterFormPage.module.css'

const EMPTY_FORM = {
  reference_number: '',
  subject: '',
  source_department_id: '',
  source_name: '',
  source_location: '',
  sender_name: '',
  designation_id: '',
  sender_designation: '',
  sender_department: '',
  sender_address: '',
  reason: '',
  received_at: '',
  text_content: '',
  category_id: '',
  classification_id: '',
  // Phase 6A — write-once at creation, never sent/shown on edit.
  direction: 'INCOMING',
  dispatch_department_id: '',
  continuation_of_letter_id: '',
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
 * Phase 5C; Source Department + Designation, Phase 5H) — one component
 * for both `/app/letters/new` (create, `POST /api/v1/letters`) and
 * `/app/letters/:id/edit` (edit, `PATCH /api/v1/letters/:id`), the same
 * reuse pattern `docs/architecture/frontend.md` §31 recommends.
 *
 * **Source Department** (Phase 5H) replaces the old free-text "Source
 * name" input with a `DepartmentSelector` bound to
 * `source_department_id` — the field already existed on every Letter
 * schema (`source_department_id`, optional) but had no frontend control
 * until now, per docs/architecture/source-designation.md §1/§4.
 * Selecting a department auto-fills `source_name` (still the backend's
 * own required text field, unchanged) with that department's name —
 * the user never types it. `GET /api/v1/departments` is now readable by
 * every authenticated role (§5 of that document), not SYSTEM_ADMIN
 * only, specifically so this works for USER/ADMIN.
 *
 * **Designation** (Phase 5H) replaces the old free-text "Sender
 * designation" input with a `<select>` bound to the new `designation_id`
 * field. Selecting one auto-fills `sender_designation` (still required
 * text, unchanged) with that designation's name; the backend itself is
 * still authoritative and overrides this value server-side regardless
 * (docs/architecture/source-designation.md §9) — the client-side
 * mirroring here is only so the required text field is never sent
 * blank. `GET /api/v1/designations` is readable by every authenticated
 * role by design (§11 of that document) — the one thing this new
 * resource exists to support.
 *
 * Both selectors load only `ACTIVE` options on **create** (§5/§11 —
 * "only active/appropriate" options should ever be offered for a new
 * assignment); on **edit**, both load the *complete* list (active and
 * inactive) so a Letter's already-assigned, possibly-now-inactive
 * department/designation still renders and remains selectable as
 * "unchanged" — mirroring the existing Category/Classification
 * inactive-injection pattern below. Both are required at this form's
 * own validation layer only on **create** — an existing Letter
 * predating Phase 5H legitimately has neither set, and editing an
 * unrelated field must not retroactively demand one
 * (`utils/formValidation.js`'s own `isEdit` parameter).
 *
 * `category_id`/`classification_id` remain a CONFIRMED backend-contract
 * gap, unchanged by this phase: `GET /api/v1/categories` and
 * `/classifications` are still both `require_system_admin`-only
 * (`app/api/v1/endpoints/{categories,classifications}.py`), but
 * `POST /api/v1/letters` is USER/ADMIN-only
 * (`require_user_or_admin` — SYSTEM_ADMIN has no department to
 * record a letter against). No caller of the create form can ever
 * legitimately load that option list, so these two fields never
 * appear on create. On edit, they appear only for a SYSTEM_ADMIN
 * caller (the only role that can both load the options and, per
 * `assert_letter_access`'s SYSTEM_ADMIN bypass, edit any letter) —
 * a USER/ADMIN editing a letter simply never touches these two
 * fields, and the backend's own "omitted field means unchanged"
 * `LetterUpdate` semantics leave whatever value was already there
 * untouched.
 *
 * `id`/`recipient_department_id`/`recorded_by`/`status`/`created_at`/
 * `updated_at` have no field in `EMPTY_FORM` at all — there is nothing
 * here for a client value to bind to even accidentally.
 *
 * Phase 5I.4B (docs/architecture/ui-design-system.md §8/§9) adds a
 * header (eyebrow/accent line) and restyles the existing fieldset/
 * legend/button treatment — every field, name, id, validation rule, and
 * payload above is unchanged; the four fieldsets' own grouping and
 * legend text are untouched.
 *
 * Phase 6A (docs/architecture/correspondence.md §9) adds one new
 * fieldset, **create only**: a Correspondence Direction control
 * (Incoming/Diary vs Outgoing/Dispatch), and — only when Outgoing is
 * selected — a "Dispatch to Department" selector reusing the same
 * `DepartmentSelector` component Source Department already uses. Both
 * are write-once: `direction`/`dispatch_department_id` have no field on
 * `LetterUpdate` at all, so neither is rendered, validated, or sent on
 * edit — the same "create-only" pattern Source Department/Designation
 * already established. Reaching this page via a Letter Detail page's
 * "Create response" link (`navigate(..., { state: { continuationOfLetterId,
 * continuationOfReference } })`) pre-selects Outgoing and silently
 * carries `continuation_of_letter_id` through to the payload — it is
 * never a field the user edits directly, only ever set by that one
 * navigation path.
 */
export default function LetterFormPage() {
  const { id } = useParams()
  const isEdit = Boolean(id)
  const navigate = useNavigate()
  const location = useLocation()
  const { user } = useAuth()
  const isSystemAdmin = user?.role === 'SYSTEM_ADMIN'
  const continuationOfLetterId = !isEdit ? location.state?.continuationOfLetterId : undefined
  const continuationOfReference = !isEdit ? location.state?.continuationOfReference : undefined

  const [form, setForm] = useState(() =>
    continuationOfLetterId
      ? { ...EMPTY_FORM, direction: 'OUTGOING', continuation_of_letter_id: continuationOfLetterId }
      : EMPTY_FORM
  )
  const [fieldErrors, setFieldErrors] = useState({})
  const [formError, setFormError] = useState(null)
  const [submitting, setSubmitting] = useState(false)
  const [initialLoading, setInitialLoading] = useState(isEdit)
  const [notFound, setNotFound] = useState(false)
  const [loadError, setLoadError] = useState(null)
  const [referenceOptions, setReferenceOptions] = useState({ categories: null, classifications: null })

  // Source Department / Designation (Phase 5H) — required for every
  // role that can reach this form (USER/ADMIN), unlike
  // categories/classifications above, so this loads unconditionally,
  // not gated by isSystemAdmin. ACTIVE-only on create; the complete
  // list on edit, so an already-assigned, now-inactive value still
  // renders and stays selectable as "unchanged" — see this file's own
  // module docstring.
  const [departments, setDepartments] = useState(null)
  const [designations, setDesignations] = useState(null)
  const [referenceDataError, setReferenceDataError] = useState(null)

  useEffect(() => {
    if (!isEdit) return
    letterService
      .get(id)
      .then((letter) => {
        setForm({
          reference_number: letter.reference_number,
          subject: letter.subject ?? '',
          source_department_id: letter.source_department_id ?? '',
          source_name: letter.source_name,
          source_location: letter.source_location ?? '',
          sender_name: letter.sender_name,
          designation_id: letter.designation_id ?? '',
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

  useEffect(() => {
    const filter = isEdit ? {} : { status: 'ACTIVE' }
    Promise.all([departmentService.list(filter), designationService.list(filter)])
      .then(([departmentResponse, designationResponse]) => {
        setDepartments(departmentResponse.items)
        setDesignations(designationResponse.items)
      })
      .catch((normalizedError) => setReferenceDataError(normalizedError))
  }, [isEdit])

  const handleChange = useCallback((event) => {
    const { name, value } = event.target
    setForm((previous) => ({ ...previous, [name]: value }))
  }, [])

  // Selecting a Source Department auto-fills source_name (still the
  // backend's own required text field) with that department's name —
  // the user never types it (docs/architecture/source-designation.md
  // §4/§13). Clearing the selection clears source_name too, rather than
  // leaving a stale name attached to no department.
  const handleSourceDepartmentChange = useCallback(
    (event) => {
      const departmentId = event.target.value
      const selected = departments?.find((department) => department.id === departmentId)
      setForm((previous) => ({
        ...previous,
        source_department_id: departmentId,
        source_name: selected ? selected.name : '',
      }))
    },
    [departments]
  )

  // Mirrors handleSourceDepartmentChange for Designation — the backend
  // is still authoritative and overrides sender_designation server-side
  // regardless (§9), but the field remains required text on
  // LetterCreate/LetterUpdate, so it must never be sent blank.
  const handleDesignationChange = useCallback(
    (event) => {
      const designationId = event.target.value
      const selected = designations?.find((designation) => designation.id === designationId)
      setForm((previous) => ({
        ...previous,
        designation_id: designationId,
        sender_designation: selected ? selected.name : '',
      }))
    },
    [designations]
  )

  function buildPayload() {
    const payload = {
      reference_number: form.reference_number,
      subject: form.subject,
      source_department_id: form.source_department_id || null,
      source_name: form.source_name,
      source_location: form.source_location || null,
      sender_name: form.sender_name,
      designation_id: form.designation_id || null,
      sender_designation: form.sender_designation,
      sender_department: form.sender_department,
      sender_address: form.sender_address || null,
      reason: form.reason || null,
      received_at: fromDatetimeLocalValue(form.received_at),
      text_content: form.text_content || null,
    }
    if (!isEdit) {
      // Write-once fields — never sent on edit (see this file's own
      // module docstring); `LetterUpdate` has no field for any of them.
      payload.direction = form.direction
      if (form.direction === 'OUTGOING') {
        payload.dispatch_department_id = form.dispatch_department_id || null
      }
      if (form.continuation_of_letter_id) {
        payload.continuation_of_letter_id = form.continuation_of_letter_id
      }
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

    const errors = validateLetterForm(form, { isEdit })
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
  if (referenceDataError) return <ErrorState message={referenceDataError.message} />
  if (!departments || !designations) return <LoadingState label="Loading form options..." />

  return (
    <section className={styles.root}>
      <header className={styles.header}>
        <p className={styles.eyebrow}>{isEdit ? 'Registry Entry · Edit' : 'Registry Entry'}</p>
        <div className={styles.titleRow}>
          <h1>{isEdit ? 'Edit Letter' : 'Record New Letter'}</h1>
          <span className={styles.headerMark} aria-hidden="true" />
        </div>
      </header>

      <form onSubmit={handleSubmit} noValidate className={styles.form}>
        {formError && <ErrorState message={formError} />}

        {continuationOfLetterId && (
          <p className={styles.hint}>
            Responding to {continuationOfReference ? `letter ${continuationOfReference}` : 'the original letter'}.
            This will be recorded as a new, separate letter linked to it.
          </p>
        )}

        {!isEdit && (
          <fieldset className={styles.fieldset}>
            <legend>Correspondence direction</legend>
            <div className={styles.field}>
              <label htmlFor="direction">Direction *</label>
              <select
                id="direction"
                name="direction"
                value={form.direction}
                onChange={handleChange}
                required
              >
                {LETTER_DIRECTION_OPTIONS.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
            </div>
            {form.direction === 'OUTGOING' && (
              <div className={styles.field}>
                <label htmlFor="dispatch_department_id">Dispatch to Department *</label>
                <DepartmentSelector
                  id="dispatch_department_id"
                  name="dispatch_department_id"
                  departments={departments.filter((department) => department.id !== user?.department_id)}
                  value={form.dispatch_department_id}
                  onChange={handleChange}
                  activeOnly={false}
                  required
                  aria-invalid={Boolean(fieldErrors.dispatch_department_id)}
                  aria-describedby={
                    fieldErrors.dispatch_department_id ? 'dispatch_department_id-error' : undefined
                  }
                />
                <p className={styles.hint}>
                  The department this correspondence is being sent to. They will be notified and can
                  record it as their own incoming correspondence.
                </p>
                <FieldError name="dispatch_department_id" fieldErrors={fieldErrors} />
              </div>
            )}
          </fieldset>
        )}

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
            <label htmlFor="source_department_id">Source Department{!isEdit && ' *'}</label>
            <DepartmentSelector
              id="source_department_id"
              name="source_department_id"
              departments={departments}
              value={form.source_department_id}
              onChange={handleSourceDepartmentChange}
              activeOnly={false}
              required={!isEdit}
              aria-invalid={Boolean(fieldErrors.source_department_id)}
              aria-describedby={
                fieldErrors.source_department_id ? 'source_department_id-error' : undefined
              }
            />
            <p className={styles.hint}>
              The department this letter originated from — distinct from "Recipient
              Department" (your own department, which registers the letter) and "Sender's
              Department" below (the individual sender's own department, free text).
            </p>
            <FieldError name="source_department_id" fieldErrors={fieldErrors} />
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
            <label htmlFor="designation_id">Designation{!isEdit && ' *'}</label>
            <select
              id="designation_id"
              name="designation_id"
              value={form.designation_id}
              onChange={handleDesignationChange}
              required={!isEdit}
              aria-invalid={Boolean(fieldErrors.designation_id)}
              aria-describedby={fieldErrors.designation_id ? 'designation_id-error' : undefined}
            >
              <option value="">Select a designation</option>
              {designations.map((designation) => (
                <option key={designation.id} value={designation.id}>
                  {designation.name}
                  {designation.status === 'INACTIVE' ? ' (inactive)' : ''}
                </option>
              ))}
            </select>
            {designations.length === 0 && (
              <p className={styles.hint}>
                No designations are available yet. A System Administrator must add at
                least one before a letter can be recorded.
              </p>
            )}
            <FieldError name="designation_id" fieldErrors={fieldErrors} />
          </div>
          <div className={styles.field}>
            <label htmlFor="sender_department">Sender's department *</label>
            <input type="text" required {...fieldProps('sender_department', form, fieldErrors, handleChange)} />
            <p className={styles.hint}>
              Free text describing the sender's own department — distinct from
              "Source Department," which may or may not be the same organization.
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
