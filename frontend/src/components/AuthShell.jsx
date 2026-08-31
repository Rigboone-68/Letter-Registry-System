import { APP_NAME, APP_SHORT_NAME, AUTH_BACKGROUND_SRC, GOVT_LOGO_SRC, PRODUCTION_CREDIT } from '../constants/app'
import styles from './AuthShell.module.css'

/**
 * The shared entrance chrome for every Login/Signup state (form,
 * pending, deactivated) — originally Phase 5I.4E
 * (docs/architecture/ui-design-system.md §28), extracted from its two
 * near-identical per-page copies in Phase 6B once the shell grew a
 * genuine split-screen layout worth sharing properly rather than
 * maintaining twice.
 *
 * Split-screen layout, per the supervisor's explicit request: the
 * supplied `front_page.jpeg` fills a left "institutional presentation"
 * pane (`object-fit: cover`, decorative — `alt=""`, since it conveys
 * mood/context, not identity-bearing text); the right pane holds the
 * actual Government of Balochistan logo, the `APP_SHORT_NAME`/
 * `APP_NAME` brand text, whatever real content (`children`) this
 * screen needs, and the `PRODUCTION_CREDIT` line. The logo is also
 * `alt=""` — the adjacent visible brand text already fully names the
 * application's identity, so a second screen-reader announcement of
 * the same fact would be redundant (the one deliberate exception to
 * "give meaningful images real alt text": this logo's role here is
 * decorative reinforcement of an identity already stated in real
 * text, not the sole conveyor of it).
 *
 * Below the existing 768px breakpoint (the same one every other
 * responsive layout in this app already uses), the image pane
 * collapses to a short header band rather than disappearing — the
 * brief's own explicit "keep the identity visible, never squeeze the
 * form" instruction — and the two panes stack vertically.
 */
export default function AuthShell({ children }) {
  return (
    <div className={styles.root}>
      <div className={styles.imagePane}>
        <img src={AUTH_BACKGROUND_SRC} alt="" className={styles.image} />
      </div>
      <div className={styles.formPane}>
        <div className={styles.formPaneInner}>
          <div className={styles.brand}>
            <img src={GOVT_LOGO_SRC} alt="" className={styles.brandMark} />
            <div className={styles.brandCopy}>
              <p className={styles.brandEyebrow}>{APP_SHORT_NAME} Operational Registry</p>
              <p className={styles.brandName}>{APP_NAME}</p>
            </div>
          </div>
          {children}
          <p className={styles.credit}>{PRODUCTION_CREDIT}</p>
        </div>
      </div>
    </div>
  )
}
