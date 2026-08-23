import { forwardRef } from 'react'

/**
 * A reusable department `<select>` (Phase 5D,
 * docs/architecture/administration-ui.md §14.6) — used by the Admin
 * Authorize form, the Admin Transfer dialog, and the Administrators
 * list's department filter. Takes an already-loaded `departments` array
 * (from `services/departmentService.js`) rather than fetching anything
 * itself — data loading stays in the page that owns the request.
 *
 * `activeOnly` (default `true`) filters the option list to `ACTIVE`
 * departments — a UX nicety, not a security boundary: the backend
 * still rejects an `INACTIVE` selection with its own `409` regardless
 * of what this control offers (`DepartmentNotActiveError`, e.g.
 * `app/services/admin_service.py:authorize_admin`/
 * `change_admin_department`). Pass `activeOnly={false}` for a filter
 * context where seeing inactive departments is itself useful (e.g. the
 * Administrators list filter, so a SYSTEM_ADMIN can still find Admins
 * in a department that has since gone inactive).
 *
 * Wrapped in `forwardRef` only so `AdminTransferDialog` can manage
 * initial focus/Tab-trapping on the underlying `<select>` — every other
 * call site ignores the ref.
 *
 * A placeholder `<option value="">` is always rendered when
 * `includeAllOption` is false — including when `required` is true.
 * Omitting it for `required` selects was a real bug, not a valid
 * optimization: a controlled `<select value="">` with no matching
 * `<option value="">` silently desyncs from the DOM — the browser
 * falls back to visually selecting the first real option while React's
 * own tracked value (and the parent's form state) stays `''`, with no
 * `onChange` ever firing to reconcile the two. A caller who then clicks
 * the already-visually-selected option triggers no native `change`
 * event at all (the browser only fires one when the selection actually
 * changes), so the parent's state — and therefore validation — never
 * sees a selection the user can plainly see on screen. `required`-ness
 * is already enforced by the parent's own validation
 * (`utils/formValidation.js`'s `isBlank(department_id)` check), not by
 * withholding the placeholder option.
 */
const DepartmentSelector = forwardRef(function DepartmentSelector(
  { id, name, departments, value, onChange, activeOnly = true, includeAllOption = false, required, ...rest },
  ref
) {
  const options = activeOnly
    ? departments.filter((department) => department.status === 'ACTIVE')
    : departments

  return (
    <select
      id={id}
      name={name}
      ref={ref}
      value={value}
      onChange={onChange}
      required={required}
      {...rest}
    >
      {includeAllOption && <option value="">All departments</option>}
      {!includeAllOption && <option value="">Select a department</option>}
      {options.map((department) => (
        <option key={department.id} value={department.id}>
          {department.name}
          {department.status === 'INACTIVE' ? ' (inactive)' : ''}
        </option>
      ))}
    </select>
  )
})

export default DepartmentSelector
