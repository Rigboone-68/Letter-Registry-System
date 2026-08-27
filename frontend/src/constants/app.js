/**
 * Application-wide constants.
 *
 * Values that differ per environment come from Vite env variables so that
 * nothing environment-specific is hard-coded in components.
 */

export const APP_NAME = import.meta.env.VITE_APP_NAME || 'Letter Registry System'
export const APP_SHORT_NAME = 'LRS'
export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api/v1'

// Approved wording (docs/architecture/ui-design-system.md §26). Not yet
// rendered anywhere — Phase 5I.1 only prepares this constant/text; the
// visible footer and its layout are deferred to the shell-redesign
// phase (§12 of the Phase 5I.1 brief: inserting it into AppShell now
// would modify the shell, out of this phase's scope).
export const PRODUCTION_CREDIT = 'A Project by AJ-OVA Labs'
