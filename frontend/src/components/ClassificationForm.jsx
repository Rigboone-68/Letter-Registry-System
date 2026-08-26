import styles from '../pages/AdminPages.module.css'

/**
 * Classification name/description/`restricts_access` fields only — no
 * `<form>` wrapper, no submit button (Phase 5H.1, mirroring
 * `CategoryForm.jsx`/`DepartmentForm.jsx`). Reused by
 * `ClassificationCreatePage` and `ClassificationDetailPage`'s inline
 * edit mode.
 *
 * `restricts_access` is a plain checkbox, forwarded to the backend
 * exactly as set — this component makes no decision about what the
 * flag *means* or who it affects; that is entirely
 * `assert_letter_access`'s job on the backend, unaffected by anything
 * here. No `status`/`id`/timestamp field exists here either — status
 * changes only ever go through the dedicated activate/deactivate
 * actions elsewhere.
 */
export default function ClassificationForm({ form, fieldErrors, onChange }) {
  return (
    <>
      <div className={styles.field}>
        <label htmlFor="classification-name">Name *</label>
        <input
          id="classification-name"
          name="name"
          type="text"
          required
          value={form.name}
          onChange={onChange}
          aria-invalid={Boolean(fieldErrors.name)}
          aria-describedby={fieldErrors.name ? 'classification-name-error' : undefined}
        />
        {fieldErrors.name && (
          <span id="classification-name-error" role="alert" className={styles.fieldError}>
            {fieldErrors.name}
          </span>
        )}
      </div>

      <div className={styles.field}>
        <label htmlFor="classification-description">Description</label>
        <textarea
          id="classification-description"
          name="description"
          rows={3}
          value={form.description}
          onChange={onChange}
          aria-invalid={Boolean(fieldErrors.description)}
          aria-describedby={
            fieldErrors.description ? 'classification-description-error' : undefined
          }
        />
        {fieldErrors.description && (
          <span id="classification-description-error" role="alert" className={styles.fieldError}>
            {fieldErrors.description}
          </span>
        )}
      </div>

      <div className={styles.field}>
        <label htmlFor="classification-restricts-access">
          <input
            id="classification-restricts-access"
            name="restricts_access"
            type="checkbox"
            checked={form.restricts_access}
            onChange={onChange}
          />
          {' '}Restricts access to classified Letters
        </label>
        <p className={styles.hint}>
          When checked, a Letter tagged with this classification is hidden from any USER
          who did not record it — enforced entirely by the backend
          (`assert_letter_access`). This form only sets the flag; it never decides who can
          see a classified Letter.
        </p>
      </div>
    </>
  )
}
