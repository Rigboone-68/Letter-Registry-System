import styles from './StatusBadge.module.css'

const TONE_BY_VALUE = {
  ACTIVE: 'positive',
  ARCHIVED: 'neutral',
  INACTIVE: 'neutral',
}

/**
 * A small, generic status pill (docs/architecture/frontend.md §18 —
 * recommended so the project's several distinct status enums never
 * visually blend into each other). Renders the label as real text, not
 * color alone, so meaning survives without color perception (§27).
 */
export default function StatusBadge({ value, label }) {
  const tone = TONE_BY_VALUE[value] ?? 'neutral'
  return <span className={`${styles.root} ${styles[tone]}`}>{label ?? value}</span>
}
