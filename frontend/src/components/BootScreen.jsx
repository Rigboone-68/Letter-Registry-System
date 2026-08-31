import { APP_NAME, APP_SHORT_NAME, GOVT_LOGO_SRC, PRODUCTION_CREDIT } from '../constants/app'
import styles from './BootScreen.module.css'

/**
 * The application boot/loading identity (Phase 5I.5,
 * docs/architecture/ui-design-system.md §29). Rendered by `App.jsx`
 * for exactly as long as `AuthContext`'s own existing `status ===
 * 'loading'` window lasts — this component owns no timing, delay, or
 * progress state of its own; it simply gives that already-existing,
 * genuine initialization window a distinctive "Precision Ledger"
 * presentation instead of the bare `LoadingState` spinner every other
 * loading moment in the app already uses (deliberately left
 * unreplaced everywhere else — see §10 of the brief; this is an
 * *addition*, not a redesign of existing loading states).
 *
 * The "Registry Glyph" (`.glyph`, `aria-hidden`) is the one animated
 * element: a nested-square mark — the exact geometry
 * `layouts/Sidebar.module.css` and `pages/AuthPages.module.css`
 * already established — with four small registry ticks that
 * illuminate in sequence around it, evoking a registry being scanned
 * rather than a generic spinner. It is purely decorative; the real,
 * truthful loading indication is the separate `role="status"` text
 * below it, so a screen reader is never left with only the animation.
 *
 * Phase 6B adds the actual Government of Balochistan logo above the
 * glyph — modestly sized, `alt=""` (decorative): the adjacent visible
 * `APP_SHORT_NAME`/`APP_NAME` text already fully names the
 * application's identity, so a second screen-reader announcement of
 * the same fact would be redundant. The existing glyph/animation/
 * reduced-motion behavior is completely unchanged.
 */
export default function BootScreen({ label = `Loading ${APP_NAME}` }) {
  return (
    <div className={styles.root}>
      <img src={GOVT_LOGO_SRC} alt="" className={styles.logo} />
      <div className={styles.glyph} aria-hidden="true">
        <span className={styles.glyphOuter} />
        <span className={styles.glyphInner} />
        <span className={styles.glyphCenter} />
        <span className={`${styles.glyphTick} ${styles.glyphTickTop}`} />
        <span className={`${styles.glyphTick} ${styles.glyphTickRight}`} />
        <span className={`${styles.glyphTick} ${styles.glyphTickBottom}`} />
        <span className={`${styles.glyphTick} ${styles.glyphTickLeft}`} />
      </div>
      <p className={styles.eyebrow}>{APP_SHORT_NAME}</p>
      <p className={styles.name}>{APP_NAME}</p>
      <p className={styles.status} role="status" aria-live="polite">
        {label}
      </p>
      <p className={styles.credit}>{PRODUCTION_CREDIT}</p>
    </div>
  )
}
