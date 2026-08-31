/**
 * Application-wide constants.
 *
 * Values that differ per environment come from Vite env variables so that
 * nothing environment-specific is hard-coded in components.
 *
 * Phase 6B renamed the visible application from "Letter Registry
 * System"/"LRS" to "Daak Management System"/"DMS" — this is the one
 * place that string lives; every consumer (`Sidebar`, `Topbar`,
 * `AuthShell`, `BootScreen`, `LetterFormPage`'s `title={APP_NAME}`,
 * etc.) already imported `APP_NAME`/`APP_SHORT_NAME` from here rather
 * than hardcoding it, so this one change propagates everywhere the
 * name is rendered. Two non-JS occurrences elsewhere still needed a
 * manual edit, since neither can reference a JS constant:
 * `frontend/index.html`'s `<title>` and `frontend/.env.example`'s
 * documented default. `Letter`/`Letter Registry`/`correspondence` —
 * the actual business-domain terminology — are unrelated to this
 * rename and untouched everywhere in the app.
 *
 * `GOVT_LOGO_SRC`/`AUTH_BACKGROUND_SRC` re-export the two supplied,
 * unmodified brand assets from `src/assets/` — imported once here so
 * every consumer (`Sidebar`, `AuthShell`, `BootScreen`) references the
 * same file, the same "one source" convention `APP_NAME` already
 * established. Vite resolves an imported `.webp`/`.jpeg` to a bundled,
 * hashed URL string at build time — neither file's bytes or format is
 * altered by this re-export.
 */

export const APP_NAME = import.meta.env.VITE_APP_NAME || 'Daak Management System'
export const APP_SHORT_NAME = 'DMS'
export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api/v1'

export { default as GOVT_LOGO_SRC } from '../assets/govt_bal.webp'
export { default as AUTH_BACKGROUND_SRC } from '../assets/front_page.jpeg'

// Approved wording (docs/architecture/ui-design-system.md §26). Not yet
// rendered anywhere — Phase 5I.1 only prepares this constant/text; the
// visible footer and its layout are deferred to the shell-redesign
// phase (§12 of the Phase 5I.1 brief: inserting it into AppShell now
// would modify the shell, out of this phase's scope).
export const PRODUCTION_CREDIT = 'A Project by AJ-OVA Labs'
