import styles from './StatusBadge.module.css'

// Keyed by raw enum value across every status domain this app renders
// (LetterStatus, ActiveStatus, UserStatus, AuthorizationStatus,
// docs/architecture/administration-ui.md §19) — one consistent visual
// system rather than a different badge look per domain; the value's
// meaning is disambiguated by its surrounding context (a table's own
// "Status" column already scoped to one resource), and by `domain`
// below for assistive technology specifically.
const TONE_BY_VALUE = {
  ACTIVE: 'positive',
  ARCHIVED: 'neutral',
  INACTIVE: 'neutral',
  PENDING_APPROVAL: 'warning',
  DEACTIVATED: 'neutral',
  USED: 'neutral',
  REVOKED: 'negative',
}

/**
 * A small, generic status pill (docs/architecture/frontend.md §18 —
 * recommended so the project's several distinct status enums never
 * visually blend into each other). Renders the label as real text, not
 * color alone, so meaning survives without color perception (§27).
 *
 * `domain` is optional, purely an accessible-name prefix (e.g. "User
 * status: Active" rather than a bare, ambiguous "Active") for a screen
 * reader — it never changes the visual tone (Phase 5D, see
 * docs/architecture/administration-ui.md §14.4/§19 for why one visual
 * system, not three, is deliberate).
 *
 * `.indicator` (Phase 5I.3, docs/architecture/ui-design-system.md
 * §12/§13/§20) adds a small, `aria-hidden` shape before the text — a
 * circle/diamond/square per tone, drawn in CSS with `currentColor`, no
 * icon library and no emoji — so status is never communicated by color
 * alone. The visible text remains the real, always-present signal;
 * removing the shape would still leave a fully meaningful badge.
 */
export default function StatusBadge({ value, label, domain }) {
  const tone = TONE_BY_VALUE[value] ?? 'neutral'
  const text = label ?? value
  return (
    <span className={`${styles.root} ${styles[tone]}`}>
      <span className={styles.indicator} aria-hidden="true" />
      {domain && <span className="sr-only">{domain} status: </span>}
      {text}
    </span>
  )
}
