import styles from '../pages/AdminPages.module.css'

/**
 * Department name/code fields only — no `<form>` wrapper, no submit
 * button (Phase 5D, docs/architecture/administration-ui.md §4.1/§14).
 * Reused by `DepartmentCreatePage` and `DepartmentDetailPage`'s inline
 * edit mode, which each own their own `<form>`/submit/cancel affordance
 * since create and edit have different surrounding chrome.
 *
 * No `status`/`id`/timestamp field exists here — `DepartmentCreate`/
 * `DepartmentUpdate` (backend) have none either; status changes only
 * ever go through the dedicated activate/deactivate actions elsewhere.
 */
export default function DepartmentForm({ form, fieldErrors, onChange }) {
  return (
    <>
      <div className={styles.field}>
        <label htmlFor="department-name">Name *</label>
        <input
          id="department-name"
          name="name"
          type="text"
          required
          value={form.name}
          onChange={onChange}
          aria-invalid={Boolean(fieldErrors.name)}
          aria-describedby={fieldErrors.name ? 'department-name-error' : undefined}
        />
        {fieldErrors.name && (
          <span id="department-name-error" role="alert" className={styles.fieldError}>
            {fieldErrors.name}
          </span>
        )}
      </div>

      <div className={styles.field}>
        <label htmlFor="department-code">Code</label>
        <input
          id="department-code"
          name="code"
          type="text"
          value={form.code}
          onChange={onChange}
          aria-invalid={Boolean(fieldErrors.code)}
          aria-describedby={fieldErrors.code ? 'department-code-error' : undefined}
        />
        {fieldErrors.code && (
          <span id="department-code-error" role="alert" className={styles.fieldError}>
            {fieldErrors.code}
          </span>
        )}
      </div>
    </>
  )
}
