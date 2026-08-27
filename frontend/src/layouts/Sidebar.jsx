import { useEffect, useRef, useState } from 'react'
import { NavLink, useLocation } from 'react-router-dom'

import { APP_NAME, APP_SHORT_NAME } from '../constants/app'
import { useAuth } from '../context/AuthContext'
import { getNavigationForRole } from '../navigation/navigationConfig'
import styles from './Sidebar.module.css'

/**
 * Navigation icons (Phase 5I.6A, docs/architecture/ui-design-system.md
 * §30) — replaces the 3-letter monogram glyph (`DAS`/`LET`/`DOC`/...)
 * the Phase 5I.2 Sidebar rework used as a placeholder, which manual
 * review confirmed read as text labels, not icons. Small inline SVGs
 * (no icon library, no external asset — every path/shape is written
 * directly here), 16×16 viewBox, `stroke="currentColor"` so each
 * icon's color is never its own independent state: it simply follows
 * `.linkGlyph`'s own `color`, which `.linkActive .linkGlyph` already
 * sets to `var(--color-primary)` — the exact same one active-state
 * mechanism the label/accent-bar/background already use, not a second
 * one. Every icon is purely decorative (`aria-hidden`, `focusable`
 * false); the adjacent `.linkLabel` text remains the link's real
 * accessible name, unaffected by any of this — keyed by label, not a
 * new field on `navigationConfig.js`, since this phase's own boundary
 * explicitly keeps that file untouched. An unmapped future label falls
 * back to a plain square outline rather than rendering nothing.
 */
const ICON_STROKE = {
  fill: 'none',
  stroke: 'currentColor',
  strokeWidth: '1.4',
  strokeLinecap: 'round',
  strokeLinejoin: 'round',
  'aria-hidden': 'true',
  focusable: 'false',
}

const NAV_ICONS = {
  Dashboard: (
    <svg viewBox="0 0 16 16" {...ICON_STROKE}>
      <rect x="1.5" y="1.5" width="5.5" height="5.5" rx="1" />
      <rect x="9" y="1.5" width="5.5" height="5.5" rx="1" />
      <rect x="1.5" y="9" width="5.5" height="5.5" rx="1" />
      <rect x="9" y="9" width="5.5" height="5.5" rx="1" />
    </svg>
  ),
  Letters: (
    <svg viewBox="0 0 16 16" {...ICON_STROKE}>
      <rect x="1.5" y="3" width="13" height="10" rx="1.2" />
      <path d="M2 4l6 5 6-5" />
    </svg>
  ),
  Documents: (
    <svg viewBox="0 0 16 16" {...ICON_STROKE}>
      <rect x="4" y="2" width="9" height="11" rx="1" />
      <path d="M2.5 5v8a1 1 0 0 0 1 1h7" />
    </svg>
  ),
  Notifications: (
    <svg viewBox="0 0 16 16" {...ICON_STROKE}>
      <path d="M4 11V7a4 4 0 0 1 8 0v4" />
      <path d="M2.5 11h11" />
      <path d="M6.5 13.2a1.6 1.6 0 0 0 3 0" />
    </svg>
  ),
  Departments: (
    <svg viewBox="0 0 16 16" {...ICON_STROKE}>
      <rect x="2.5" y="2" width="11" height="12" rx="0.5" />
      <path d="M2.5 6h11M6 2v12M10 2v12" />
    </svg>
  ),
  Administrators: (
    <svg viewBox="0 0 16 16" {...ICON_STROKE}>
      <path d="M8 1.5l5 2v4c0 4-2.5 6-5 7-2.5-1-5-3-5-7v-4l5-2z" />
    </svg>
  ),
  Users: (
    <svg viewBox="0 0 16 16" {...ICON_STROKE}>
      <circle cx="8" cy="5" r="2.5" />
      <path d="M2.8 14c.6-3 2.6-4.5 5.2-4.5s4.6 1.5 5.2 4.5" />
    </svg>
  ),
  Designations: (
    <svg viewBox="0 0 16 16" {...ICON_STROKE}>
      <rect x="3" y="4.5" width="10" height="9" rx="1.5" />
      <circle cx="8" cy="8" r="1.6" />
      <path d="M6 1.5h4v3H6z" />
    </svg>
  ),
  Categories: (
    <svg viewBox="0 0 16 16" {...ICON_STROKE}>
      <path d="M2 4.5a1 1 0 0 1 1-1h3l1.2 1.5H13a1 1 0 0 1 1 1V12a1 1 0 0 1-1 1H3a1 1 0 0 1-1-1V4.5z" />
    </svg>
  ),
  Classifications: (
    <svg viewBox="0 0 16 16" {...ICON_STROKE}>
      <path d="M8 2l6 3-6 3-6-3 6-3z" />
      <path d="M2 8.5l6 3 6-3" />
      <path d="M2 11.5l6 3 6-3" />
    </svg>
  ),
}

const DEFAULT_ICON = (
  <svg viewBox="0 0 16 16" {...ICON_STROKE}>
    <rect x="3" y="3" width="10" height="10" rx="1.5" />
  </svg>
)

function iconFor(label) {
  return NAV_ICONS[label] ?? DEFAULT_ICON
}

/**
 * Application navigation (docs/architecture/frontend.md §13/§19),
 * visually redesigned Phase 5I.2 per
 * docs/architecture/ui-design-system.md §6/§27 ("Precision Ledger").
 * Navigation is still derived entirely from the authenticated user's
 * role via `getNavigationForRole` — this component makes no routing or
 * permission decision of its own, and hiding/showing an entry here
 * remains a convenience only, never a security boundary. Nothing here
 * changed since Phase 5A/5I.1 in terms of *which* items a role receives.
 *
 * Two independent visual states, owned here, neither of which changes
 * what `navigationConfig.js` returns:
 *
 *  - **Desktop collapse** (`collapsed`) — an icon-rail mode for a
 *    narrower persistent sidebar. Entirely self-contained; `AppShell`
 *    does not need to know about it, since the sidebar's own width
 *    change reflows the adjacent flex column automatically.
 *  - **Mobile drawer** (`mobileOpen`/`onCloseMobile` props, owned by
 *    `AppShell`, triggered from `Topbar`'s hamburger button) — the same
 *    `<nav>` becomes an accessible modal below the existing 768px
 *    breakpoint (docs/architecture/ui-design-system.md §22): a
 *    backdrop, Escape-to-close, a Tab focus trap generalized from
 *    `components/ConfirmDialog.jsx`'s own 2-element trap to however
 *    many nav links exist, and it closes itself the moment a route is
 *    actually selected.
 */
export default function Sidebar({ mobileOpen = false, onCloseMobile = () => {} }) {
  const { user } = useAuth()
  const items = getNavigationForRole(user?.role)
  const location = useLocation()

  const [collapsed, setCollapsed] = useState(false)
  const navRef = useRef(null)
  const firstLinkRef = useRef(null)

  // Mobile drawer accessibility: Escape closes it; Tab is trapped
  // inside it while open (background content stays reachable only by
  // pointer, and the backdrop below intercepts pointer clicks, so it
  // is never accidentally interactive from the keyboard either).
  useEffect(() => {
    if (!mobileOpen) return

    firstLinkRef.current?.focus()

    function handleKeyDown(event) {
      if (event.key === 'Escape') {
        onCloseMobile()
        return
      }
      if (event.key !== 'Tab' || !navRef.current) return
      const focusable = navRef.current.querySelectorAll('a[href], button:not([disabled])')
      if (focusable.length === 0) return
      const first = focusable[0]
      const last = focusable[focusable.length - 1]
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault()
        last.focus()
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault()
        first.focus()
      }
    }

    document.addEventListener('keydown', handleKeyDown)
    return () => document.removeEventListener('keydown', handleKeyDown)
  }, [mobileOpen, onCloseMobile])

  // Selecting a route closes the mobile drawer automatically. Reacts
  // only to an actual path change, not to `mobileOpen` toggling itself
  // (opening the drawer must never immediately close it) — the freshest
  // `mobileOpen`/`onCloseMobile` are still read correctly since a new
  // effect closure is created every render regardless of this
  // dependency array, matching the existing mount-only-effect
  // convention already used in `context/AuthContext.jsx`.
  useEffect(() => {
    if (mobileOpen) onCloseMobile()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [location.pathname])

  const navClassName = [styles.root, collapsed ? styles.collapsed : '', mobileOpen ? styles.mobileOpen : '']
    .filter(Boolean)
    .join(' ')

  return (
    <>
      {mobileOpen && <div className={styles.backdrop} onClick={onCloseMobile} aria-hidden="true" />}
      <nav
        ref={navRef}
        className={navClassName}
        aria-label="Main navigation"
        {...(mobileOpen ? { role: 'dialog', 'aria-modal': 'true', 'aria-label': 'Navigation menu' } : {})}
      >
        <div className={styles.header}>
          <span className={styles.brand} title={APP_NAME}>
            <span className={styles.brandMark} aria-hidden="true" />
            <span className={styles.brandLabel}>{APP_SHORT_NAME}</span>
            <span className="sr-only">{APP_NAME}</span>
          </span>
          <button
            type="button"
            className={styles.collapseToggle}
            onClick={() => setCollapsed((previous) => !previous)}
            aria-expanded={!collapsed}
            aria-controls="sidebar-nav-list"
          >
            <span aria-hidden="true">{collapsed ? '›' : '‹'}</span>
            <span className="sr-only">{collapsed ? 'Expand navigation' : 'Collapse navigation'}</span>
          </button>
        </div>
        <ul className={styles.list} id="sidebar-nav-list">
          {items.map((item, index) => (
            <li key={item.path}>
              <NavLink
                ref={index === 0 ? firstLinkRef : undefined}
                to={item.path}
                title={item.label}
                className={({ isActive }) =>
                  isActive ? `${styles.link} ${styles.linkActive}` : styles.link
                }
              >
                <span className={styles.linkGlyph} aria-hidden="true">
                  {iconFor(item.label)}
                </span>
                <span className={styles.linkLabel}>{item.label}</span>
              </NavLink>
            </li>
          ))}
        </ul>
      </nav>
    </>
  )
}
