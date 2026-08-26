import styles from '../pages/AdminPages.module.css'

/**
 * Category name/description fields only — no `<form>` wrapper, no
 * submit button (Phase 5H.1, mirroring `DepartmentForm.jsx` exactly).
 * Reused by `CategoryCreatePage` and `CategoryDetailPage`'s inline edit
 * mode, which each own their own `<form>`/submit/cancel affordance.
 *
 * No `status`/`id`/timestamp field exists here — `CategoryCreate`/
 * `CategoryUpdate` (backend) have none either; status changes only
 * ever go through the dedicated activate/deactivate actions elsewhere.
 */
export default function CategoryForm({ form, fieldErrors, onChange }) {
  return (
    <>
      <div className={styles.field}>
        <label htmlFor="category-name">Name *</label>
        <input
          id="category-name"
          name="name"
          type="text"
          required
          value={form.name}
          onChange={onChange}
          aria-invalid={Boolean(fieldErrors.name)}
          aria-describedby={fieldErrors.name ? 'category-name-error' : undefined}
        />
        {fieldErrors.name && (
          <span id="category-name-error" role="alert" className={styles.fieldError}>
            {fieldErrors.name}
          </span>
        )}
      </div>

      <div className={styles.field}>
        <label htmlFor="category-description">Description</label>
        <textarea
          id="category-description"
          name="description"
          rows={3}
          value={form.description}
          onChange={onChange}
          aria-invalid={Boolean(fieldErrors.description)}
          aria-describedby={fieldErrors.description ? 'category-description-error' : undefined}
        />
        {fieldErrors.description && (
          <span id="category-description-error" role="alert" className={styles.fieldError}>
            {fieldErrors.description}
          </span>
        )}
      </div>
    </>
  )
}
