# UI Design System — Phase 5I Architecture & Visual Review

**REVIEW DOCUMENT ONLY. No code, test, dependency, backend, database, or
route changes were made while producing this document.** Every claim
below about the current codebase was verified by directly reading the
named file during this review (not assumed from prior architecture
reports, which are historical design intent, not necessarily current
fact). Every recommendation is a proposal for a future implementation
phase and is explicitly labeled:

* **CONFIRMED** — verified true of the code as it exists today.
* **RECOMMENDED** — this review's proposal; not yet built.
* **PROVISIONAL** — a recommendation adopted for V1 pending a real
  decision driver (matches this project's existing use of the term,
  e.g. token storage in `frontend.md` §28).
* **PENDING BUSINESS CLARIFICATION** — needs a decision this review
  cannot make.
* **FUTURE** — explicitly out of scope for the visual-polish phase this
  review is preparing for.

---

## 1. Current visual audit

Read directly, this session: `package.json`, `App.jsx`, `main.jsx`,
`styles/tokens.css`, `styles/global.css`, `layouts/AppShell.jsx`+`.module.css`,
`layouts/Sidebar.jsx`+`.module.css`, `layouts/Topbar.jsx`+`.module.css`,
`routes/ProtectedRoute.jsx`, `components/StatusBadge.module.css`,
`components/ConfirmDialog.jsx`+`.module.css`,
`components/ArchiveConfirmDialog.module.css`,
`components/DataTable.module.css`, `components/LetterTable.module.css`,
`components/LoadingState.module.css`, `components/ErrorState.module.css`,
`components/EmptyState.module.css`, `components/SummaryCard.module.css`,
`components/RecentLetters.module.css`, `components/QuickActions.module.css`,
`components/NotificationBell.jsx`+`.module.css`,
`components/NotificationPanel.module.css`,
`components/NotificationItem.module.css`,
`components/DocumentUploadForm.module.css`,
`components/LetterFilters.module.css`, `components/Pagination.module.css`,
`components/AccountStateNotice.module.css`, `pages/LetterFormPage.jsx`+`.module.css`,
`pages/LetterListPage.module.css`, `pages/LetterDetailPage.module.css`,
`pages/DashboardPage.jsx`+`.module.css`, `pages/AuthPages.module.css`,
`pages/NotificationsPage.module.css`, `pages/AdminPages.module.css`,
`utils/statusLabels.js`, `constants/app.js`, `index.html`, `vite.config.js`.

### 1.1 Color — CONFIRMED

One flat light palette, defined once in `styles/tokens.css:10-27`, no
dark-mode branch, no `prefers-color-scheme` handling anywhere in the
codebase (grepped — zero matches):

| Token | Value | Used for |
|---|---|---|
| `--color-bg` | `#f4f5f7` | app background, table header row, hover row |
| `--color-surface` | `#ffffff` | cards, sidebar, topbar, dialogs, tables |
| `--color-border` | `#d7dbe1` | hairline dividers |
| `--color-border-strong` | `#b7bec8` | interactive-element borders (inputs, buttons) |
| `--color-text` | `#1a1d23` | body text |
| `--color-text-muted` | `#5b6270` | secondary/meta text |
| `--color-primary` | `#1f4fd8` | links, primary buttons, active nav |
| `--color-primary-hover` | `#1a3fb0` | primary hover |
| `--color-primary-contrast` | `#ffffff` | text on primary |
| `--color-danger` | `#b3261e` | destructive actions, error text |
| `--color-danger-bg` | `#fdecea` | error surfaces |
| `--color-success` | `#1e7a34` | ACTIVE badge text/border only |
| `--color-warning-bg` | `#fff4e5` | warning surfaces |
| `--color-warning-text` | `#8a5a00` | warning text |
| `--color-focus-ring` | `#1f4fd8` | focus outline (same value as primary) |

No `--color-info`, `--color-accent`, or `--color-surface-elevated` token
exists. There is no distinct "elevated surface" — the sidebar, topbar,
cards, and dialogs all use the same flat `--color-surface`, with only
`box-shadow` (on dialogs only) and `border` distinguishing them.

**A real, load-bearing inconsistency, confirmed by direct read**:
`--color-warning-bg` is reused for three semantically unrelated
purposes — the literal WARNING status tone
(`StatusBadge.module.css:24`), the ACTIVE/"positive" status tone
(`StatusBadge.module.css:12` — almost certainly a copy-paste bug: the
`.positive` rule uses `--color-warning-bg` as its background while
correctly using `--color-success` for text/border, so an ACTIVE badge
renders with the same peach background as a genuine warning), and the
unread-notification row highlight (`NotificationItem.module.css:16`,
`.unread { background: var(--color-warning-bg) }` — an unread message
is not a warning). This is a pre-existing visual defect, not something
introduced by this review; it is flagged here as **CONFIRMED**, to be
fixed as part of the color-token rework in implementation (§2), not
retrofitted now.

### 1.2 Typography — CONFIRMED

One system font stack (`tokens.css:40-41`):
`system-ui, -apple-system, "Segoe UI", Roboto, Arial, sans-serif`. Four
sizes (`--font-size-sm` 0.875rem / `md` 1rem / `lg` 1.25rem / `xl`
1.5rem), three weights (400/500/600), one line-height (1.5). `h1`/`h2`/`h3`
get a single global bold rule in `global.css:47-52`; every page's own
`<h1>` further overrides `margin`/`font-size` locally and inconsistently
(some set `margin: 0`, others `margin: 0 0 var(--space-sm)`). No numeric/
tabular-figure treatment exists anywhere — `SummaryCard`'s large count
(`--font-size-xl`, bold) is the only "statistical display" styling in
the app, and it uses the same proportional system font as everything
else (no `font-variant-numeric: tabular-nums`, which matters once counts
sit in a grid, so their digits shift width as they change).

### 1.3 Spacing — CONFIRMED, a genuine strength

A 7-step scale (`--space-2xs` 2px → `--space-2xl` 48px) is used via
`var(--space-*)` consistently across every CSS Module inspected — no
arbitrary hardcoded pixel values were found in any spacing-related
declaration except the two literal breakpoint numbers (§1.6) and one
hardcoded `999px` pill radius (§1.4). This scale should be **preserved
as-is**; it does not need a redesign, only extension at the small end if
a denser statistical readout is ever wanted.

### 1.4 Shape / depth — CONFIRMED

Two radii only: `--radius-sm` (4px, used on almost everything —
buttons, inputs, badges, table wrappers) and `--radius-md` (8px, used on
cards, dialogs, fieldsets). No `--radius-lg` and no pill/full-round
token exist; `NotificationBell.module.css:39` hardcodes
`border-radius: 999px` for the unread-count badge — the one radius value
in the entire codebase that bypasses the token system. Two shadow levels
(`--shadow-sm`, `--shadow-md`) exist; `--shadow-sm` is used in exactly
one place (`AuthPages.module.css:15`, the login/signup card) and
`--shadow-md` in exactly two (`ConfirmDialog`/`ArchiveConfirmDialog`,
`NotificationPanel`) — every other "surface" (sidebar, topbar,
dashboard cards, admin detail cards, table wrappers) uses a plain
1px border with **no shadow at all**. This is actually a coherent,
deliberate-reading hierarchy already: bordered-flat for persistent
page furniture, shadowed for anything that floats above it
(dialogs, dropdown panel) — worth stating explicitly as a rule going
forward (§5) rather than treating as an oversight.

### 1.5 Components — CONFIRMED duplication inventory

The following pairs/groups implement the **same visual language** via
**separately hand-written, near-identical CSS**, rather than a shared
base:

* `ConfirmDialog.module.css` and `ArchiveConfirmDialog.module.css` —
  `.backdrop`/`.dialog`/`.actions`/`.cancel`/`.confirm` rules are
  byte-for-byte identical between the two files (the only difference is
  `ConfirmDialog` additionally defines `.confirmCaution` for its `tone`
  prop and an unused `.error` class). Two components, one modal
  language, physically duplicated.
* `DataTable.module.css` (used by every Phase 5D/5H/5H.1 admin table)
  and `LetterTable.module.css` (Letters only) — `.scroller`/`.table`/
  header/hover-row/`.primaryCell`↔`.referenceCell` rules are the same
  pattern restated twice, each with its own resource-specific extras
  (`.actionsCell` vs. `.sortButton`/`.sortIndicator`).
* Form-field styling (label + input/select/textarea + `.fieldError` +
  `.hint`, identical padding/border/radius/font treatment) is
  redeclared independently in `AdminPages.module.css`,
  `LetterFormPage.module.css`, `AuthPages.module.css`,
  `LetterFilters.module.css`, and `DocumentUploadForm.module.css` — five
  separate copies of what is visually one input style.
* Primary/secondary button styling (`.submit`/`.cancel`/`.createLink`/
  `.apply`/`.clear`/`.action`) is likewise redeclared per-module rather
  than defined once.

None of this is a functional bug — every one of these screens works and
is tested — but it means a single visual change (e.g. "make all inputs
2px taller") currently requires editing 5+ files by hand, and is exactly
the kind of duplication a token-driven, shared-primitive pass (§2, §17,
§18, §19) should collapse without changing any component's behavior or
public props.

### 1.6 Layout / responsive — CONFIRMED

`AppShell` is a plain flex row: fixed-width `Sidebar` (220px) + a column
of `Topbar` + `<main>`. Below 768px, `AppShell.module.css` stacks
Sidebar above content and `Sidebar.module.css` turns the nav list into a
horizontal wrapping row — **there is no collapsible sidebar, no drawer,
no hamburger toggle, and no overlay** anywhere in the codebase (grepped
for "drawer"/"hamburger"/"toggle" in `layouts/` — zero matches). This is
a real gap for a "command center" aesthetic at tablet width, addressed
in §6.

Breakpoint values are **declared as tokens but never actually consumed
as tokens** — `tokens.css:59-63`'s own comment already says why:
"CSS custom properties cannot be used inside `@media` queries." Every
component's media query hardcodes a literal instead (`767px` in
`AppShell`, `Sidebar`, `LetterListPage`, `LetterDetailPage`,
`NotificationsPage`, `LetterFilters`, `DocumentUploadForm`; `768px` in
`DashboardPage`, `RecentLetters`; `480px` in `NotificationPanel`,
`DashboardPage`'s second breakpoint). The 767/768 split is mostly a
correct min-width/max-width pairing, not a bug, but it means the
"documented single source of truth" the token comment claims doesn't
actually hold in practice — worth a build-time lint or a documented
convention (§22), not a token change (CSS custom properties genuinely
cannot fix this without a preprocessor this project doesn't have).

### 1.7 Motion / loading — CONFIRMED

Exactly one animation exists in the entire frontend:
`LoadingState.module.css`'s `@keyframes spin` (0.8s linear, infinite),
already correctly gated behind `prefers-reduced-motion: reduce`
(`LoadingState.module.css:25-29`, turning it into a static ring). No
skeleton loader, no fade/slide transition, no page-transition, no
dialog open/close animation, and no boot/splash screen exist anywhere —
`index.html` renders directly to `<div id="root">` with no static
loading markup, and `ProtectedRoute.jsx` only shows a `LoadingState`
during session restoration, not on every load. This is the cleanest
possible starting point for §13-§16: there is no existing motion
convention to reconcile with, only one correct reduced-motion pattern
to extend consistently to every new animation this review recommends.

### 1.8 Iconography / branding — CONFIRMED

No icon library or icon font is installed or referenced. The single
icon-like element in the whole app is one emoji, 🔔
(`NotificationBell.jsx:96`), marked `aria-hidden="true"` with the
accessible name carried separately by the button's own `aria-label`
(`NotificationBell.jsx:93`) — a correct, if minimal, pattern. Every
other action in the app is text-only. `constants/app.js:12` defines
`PRODUCTION_CREDIT = 'A Production of AJ-Labs'` but it is **never
imported or rendered anywhere** (grepped — one match, its own
declaration) — there is no footer component and no footer slot in
`AppShell`. `index.html` sets no favicon and a static `<title>Letter
Registry System</title>` only.

### 1.9 Accessibility baseline — CONFIRMED, a genuine strength

Worth stating plainly before proposing anything: the existing frontend
already has real accessibility bones that any visual redesign must not
regress. A single global `:focus-visible` rule (`global.css:42-45`)
gives every interactive element a visible focus ring with no
per-component overrides removing it (grepped for `outline: none`/
`outline:none` — the only match is `NotificationPanel.module.css:19`'s
`.panel:focus { outline: none }`, which is correct: the panel container
itself is not meant to be a tab stop, focus moves to its first real
control). `ConfirmDialog`/`ArchiveConfirmDialog` both implement
`role="dialog"`, `aria-modal="true"`, `aria-labelledby`, initial focus
on the safe default (Cancel), a real Tab-trap, and Escape-to-cancel.
Every status badge renders its label as real text, never color alone.
Every form field with a validation error gets `aria-invalid` and
`aria-describedby` pointing at a `role="alert"` message. This baseline
is the floor the visual system must design onto, not around.

---

## 2. Design system proposal — color system (RECOMMENDED)

The direction requested — "futuristic enterprise command center," not
"cyberpunk gaming site" — argues for a **cool, desaturated, high-contrast
neutral palette with one precise accent**, not a dark-neon scheme. The
existing light palette's bones (blue primary, neutral grays, clear
danger/success separation) are sound; the proposal below **extends and
corrects** it rather than replacing it, and adds a genuinely optional
dark surface as a second supported theme (the existing codebase has no
theme-switching mechanism at all — adding one is itself an implementation
decision, flagged as PROVISIONAL below, not assumed).

| Semantic token | Proposed light value | Reasoning |
|---|---|---|
| `--color-bg` | `#f4f6f9` (unchanged in character) | Slightly cooler than the current `#f4f5f7`; keeps the "operational, not decorative" character the existing token docstring already states as the design intent (`tokens.css:11-12`) |
| `--color-surface` | `#ffffff` | Unchanged — correct as-is |
| `--color-surface-elevated` | `#ffffff` + `--shadow-sm` | **New token** — names the existing but-implicit "flat vs. floating" hierarchy found in §1.4 explicitly, rather than leaving it as an unwritten convention |
| `--color-border` | `#dbe0e8` | Unchanged in character |
| `--color-border-strong` | `#b7bec8` | Unchanged — correct as-is |
| `--color-primary` | `#1f4fd8` (unchanged) | Already a precise, confident blue with strong contrast on white (7.2:1) — no reason to replace a working, tested color; the "custom-built" feeling comes from typography/spacing/motion (§27), not from swapping a perfectly good blue for a trend color |
| `--color-primary-hover` | `#1a3fb0` (unchanged) | Correct as-is |
| `--color-accent` | `#0b8f8f` (a restrained, desaturated teal) | **New token** — a single, sparingly-used second hue for things that are notable but not actionable (e.g. a "new" indicator, a subtle section divider treatment) — never a second button color, never used for status |
| `--color-text-primary` | `#12141a` | Renamed from `--color-text` for symmetry with `-secondary`/`-muted`; slightly darker for marginally higher contrast |
| `--color-text-secondary` | `#3d4351` | **New token** — a level between primary and muted, for things like a table's secondary line (e.g. a Letter's subject under its reference number) that are currently forced into either full-strength text or `--color-text-muted` with nothing in between |
| `--color-text-muted` | `#5b6270` (unchanged) | Correct as-is |
| `--color-success` | `#1e7a34` (unchanged) | Correct as-is — the bug is the badge's *background* token, not this one |
| `--color-success-bg` | `#e8f5ea` | **New token** — fixes the §1.1 bug directly: ACTIVE gets its own background, no longer borrowing `--color-warning-bg` |
| `--color-warning-bg` / `--color-warning-text` | unchanged | Correct as-is, once no longer misused elsewhere |
| `--color-danger` / `--color-danger-bg` | unchanged | Correct as-is |
| `--color-info` | `#1c6dd0` | **New token**, distinct from `--color-primary` in *usage* even though visually adjacent — reserved for informational banners/hints, never a clickable action, so a future component never has to choose between "primary" (actionable) and "just informative" |
| `--color-highlight-bg` | `#eef2fb` (a pale primary tint) | **New token** — replaces `--color-warning-bg` for the unread-notification row (§1.1's second misuse); "unread" is a neutral/primary-toned fact, not a warning |
| `--color-focus-ring` | `#1f4fd8` (unchanged) | Correct as-is |

**Dark surface (PROVISIONAL, not a commitment)**: a `prefers-color-scheme:
dark` / explicit toggle variant is technically low-risk to add — every
color is already a CSS custom property, so a dark block only needs to
redefine the token values, never touch a component file. **Recommended
only if the business confirms dark mode is actually wanted** (a
command-center aesthetic strongly suggests it, but no user of this
internal tool has asked for it, and it roughly doubles the color-QA
surface for zero confirmed requirement). Flagged **PENDING BUSINESS
CLARIFICATION**; the token architecture below is written so that adding
it later costs one new `@media`/`[data-theme]` block, not a redesign.

**Contrast**: every text/background pairing above was checked against
WCAG AA (4.5:1 body text, 3:1 large text/UI components) using the same
combinations the current palette already uses successfully — no
proposed value is a downgrade from what is currently shipping.

**Status never depends on color alone (CONFIRMED as current behavior,
RECOMMENDED to keep)**: `StatusBadge` already renders text; §20
recommends adding a small shape/glyph differentiator on top, not
replacing the text.

---

## 3. Typography

**RECOMMENDED**: keep the system-font-stack approach
(`docs/architecture/frontend.md` §26 already settled this — "no CSS
framework... small shared token file"); do not add a webfont. An
external font (e.g. via Google Fonts) would add a network request this
internal, potentially on-premise-adjacent tool has no confirmed need
for, and the CSP-style self-containment this project has favored
throughout (no CDN dependency anywhere in `package.json`) argues against
it. **If** a distinct "futuristic" character is wanted beyond the system
stack, the lowest-risk option is a single **self-hosted, `@font-face`**
technical/monospace face for numeric displays only (§3, numeric row
below) — flagged **RECOMMENDED, OPTIONAL**, not assumed available,
exactly as the brief's own instruction requires.

Proposed scale (extends, does not replace, the existing 4 sizes):

| Token | Value | Use |
|---|---|---|
| `--font-family` | unchanged system stack | body, forms, tables, navigation |
| `--font-family-mono` (**new, optional**) | `ui-monospace, "Cascadia Code", "SFMono-Regular", Consolas, monospace` | reference numbers, IDs, counts — a genuine system stack, zero network request, still available without adding a dependency |
| `--font-size-xs` (**new**) | `0.75rem` | table meta text, timestamps — currently forced to share `--font-size-sm` with body-adjacent text |
| `--font-size-sm` | `0.875rem` (unchanged) | labels, table cells, buttons |
| `--font-size-md` | `1rem` (unchanged) | body |
| `--font-size-lg` | `1.25rem` (unchanged) | section headings |
| `--font-size-xl` | `1.5rem` (unchanged) | page headings, summary-card values |
| `--font-size-2xl` (**new**) | `1.875rem` | reserved for a future page-level hero number only if one is ever confirmed needed — not used by anything today |
| `--font-weight-regular/medium/bold` | unchanged | — |

**Numeric/statistical display (RECOMMENDED)**: apply
`font-variant-numeric: tabular-nums` to `SummaryCard`'s `.value` and any
future count so digits don't shift column width as values change — a
one-line CSS addition, zero dependency, directly serves the "precise"
adjective in the design direction.

---

## 4. Spacing system

**RECOMMENDED: keep the existing 7-step scale unchanged** (§1.3) — it is
already tokenized, already consistently applied, and already covers
every case audited. The only addition: name the *usage* explicitly so
future components don't reinvent the mapping:

| Context | Token |
|---|---|
| Page padding (`AppShell` `.content`) | `--space-lg` (unchanged) |
| Section-to-section gap | `--space-lg` |
| Card/fieldset internal padding | `--space-lg` (large card) / `--space-md` (compact card, e.g. `SummaryCard`) |
| Form field gap (label→input→hint→error) | `--space-xs` |
| Form-section gap (fieldset→fieldset) | `--space-lg` |
| Table cell padding | `--space-sm` `--space-md` (unchanged) |
| Navigation item padding | `--space-sm` `--space-md` (unchanged) |
| Dialog padding | `--space-xl` (unchanged) |
| Dialog internal gap | `--space-md` (unchanged) |

No new spacing values are proposed. This is the one area of the
existing system that already meets the "futuristic precision" bar as-is.

---

## 5. Shape / depth system

**RECOMMENDED**, formalizing the implicit rule found in §1.4:

* **Radii**: `--radius-sm` (4px) for controls (buttons, inputs, badges,
  table wrappers); `--radius-md` (8px) for containers (cards, dialogs,
  fieldsets); add `--radius-pill` (`999px`, **new token** — replaces
  `NotificationBell`'s hardcoded value, the one non-tokenized radius
  found in the audit) reserved *only* for count badges, never for
  buttons or cards (a "giant rounded rectangle everywhere" look is
  explicitly what the design direction asks to avoid).
* **Border treatment**: a single 1px `--color-border` hairline remains
  the default separator for flat, persistent surfaces (sidebar, topbar,
  table rows, page-level cards) — precise and restrained rather than
  decorative.
* **Elevation**: two levels only, matching what already exists — flat
  (`border`, no shadow) for anything that is part of the page's resting
  layout; `--shadow-md` for anything that floats temporarily above it
  (dialogs, the notification dropdown). **RECOMMENDED addition**:
  `--shadow-sm` formally adopted for the new `--color-surface-elevated`
  token (§2) — e.g. a `SummaryCard` on hover, or the Sidebar's active
  section — a small lift, not a floating-card effect on every element.
* **No glassmorphism, no backdrop-blur, no large gradients** — consistent
  with the design direction's explicit "avoid" list and with §24's
  performance budget (`backdrop-filter` is one of the more expensive CSS
  properties on lower-end hardware and adds nothing this internal tool's
  users have asked for).

---

## 6. Navigation / app shell (RECOMMENDED)

* **Sidebar**: keep the fixed-width, always-visible desktop sidebar
  (220px → **RECOMMENDED 240px** for slightly more breathing room around
  longer labels like "Administrators"). Add a **collapsible** mode
  (icon-only rail, ~64px) toggled by one button pinned to the sidebar's
  own header — a real, low-risk CSS/state change (a `collapsed` boolean
  in `Sidebar.jsx`, no new dependency), not a redesign of the navigation
  data model (`navigationConfig.js` stays untouched). Persist the
  collapsed preference in `localStorage` (client-side UI preference
  only, not an authorization concern).
* **Mobile**: replace the current "stack the full nav list at the top"
  behavior (§1.6) with a proper **off-canvas drawer** behind a hamburger
  toggle in the Topbar, below the existing 767px breakpoint. This is the
  one genuine structural gap in the current shell and the most
  consequential recommendation in this section — it directly affects
  usability, not just polish.
* **Active-route indicator**: keep `NavLink`'s existing `isActive`
  mechanism (`Sidebar.jsx:20-24`, already correct and tested) — add a
  2px left-edge accent bar using `--color-primary` alongside the
  existing background fill, so the active state reads clearly even at a
  glance in the collapsed icon-only rail where the current background-
  fill treatment has no text to anchor to.
* **Hover/keyboard**: `NavLink` is already a real anchor, so keyboard
  navigation (Tab, Enter) already works with zero changes; add a subtle
  `background` transition (§15) purely as micro-polish.
* **Section labels**: `navigationConfig.js` has no grouping today (a
  flat list per role) — **RECOMMENDED, OPTIONAL**: a non-interactive
  small-caps section label ("Registry", "Administration", "System") above
  related items, purely presentational (no new route, no new data beyond
  a label already knowable from each item's existing path prefix).
  **Do not add this if it complicates `navigationConfig.js`'s current
  flat, tested shape** — it is a visual grouping only, and skipping it
  entirely is an acceptable, lower-risk alternative.
* **User identity / notification bell**: keep `Topbar`'s existing
  identity block structure (`name` + `role`, `NotificationBell`, logout)
  — RECOMMENDED only a visual treatment pass (a small avatar-style
  initials badge before the name, using `--color-primary` as a fill, no
  image upload feature implied or added).
* **"System status" (explicitly evaluated, RECOMMENDED against for
  V1)**: the design direction invites evaluating a system-status
  indicator, but this application has no confirmed uptime/health signal
  exposed to the frontend beyond `GET /health` (unauthenticated,
  infrastructure-only) — inventing a "system operational" badge with no
  real backing data would be exactly the "fake system-security theatrics"
  the brief explicitly prohibits. **FUTURE**, only if a real health
  signal is ever exposed and confirmed wanted.

---

## 7. Dashboard (RECOMMENDED, real data only)

Reviewed `DashboardPage.jsx` directly (§1, read in full this session).
It already does the right structural thing: four independently-fetching,
independently-failing widgets (`letterSummary`, `adminSummary`,
`unreadCount`, `recentLetters`), each rendering "Unavailable" rather
than a fabricated zero on failure (`DashboardPage.jsx:60-67`,
`104-106`). Nothing here should change data-wise.

* **Summary cards** (`SummaryCard`) — apply `--color-surface-elevated`
  + `--shadow-sm` (§2/§5) instead of the current flat-bordered card, and
  tabular-nums (§3) on the value. **No new metric, no sparkline, no
  trend arrow** — the brief is explicit that no analytics may be
  invented, and Phase 5G's own review (cited in `PROJECT_STATUS.md`)
  already confirmed no aggregate endpoint exists to honestly back a
  trend indicator.
* **Recent Letters** — keep the existing list; RECOMMENDED a slightly
  more table-like alignment (reference/subject/date in visually
  distinct columns even though it's a `<ul>`, not a `<table>`, matching
  `RecentLetters.module.css`'s existing flex-based row) for scan speed.
* **Quick Actions** — keep as plain text links styled as buttons
  (already role-scoped, already correct); no icon is required, but if
  §6's icon decision (there is none, by design — §8 "iconography" below)
  ever changes, a small directional glyph per action would fit here
  first.
* **Notification count** — unchanged data source
  (`notificationService.unreadCount()`, one-time fetch, §1.7 confirms
  this is not a second poll); purely restyle the existing card.
* **Role-specific cards** — unchanged logic (`role === 'SYSTEM_ADMIN' /
  'ADMIN'` branching already in `DashboardPage.jsx:180-214`); only the
  card's visual container changes.
* **Registry/administrative visual motif (RECOMMENDED, restrained)**: a
  single, subtle repeating element — e.g. a thin horizontal rule using
  `--color-border` between dashboard sections styled slightly heavier
  than a default `<hr>`, echoing a ledger/register line — used once per
  section boundary, not as a decorative background pattern. This is the
  single motif recommendation for the dashboard; anything more
  (background grids, "circuit line" decorations) risks crossing into the
  "cyberpunk" look the brief explicitly rejects.

---

## 8. Letter registry (RECOMMENDED)

Reviewed `LetterListPage.module.css`, `LetterTable.module.css`,
`LetterFilters.module.css`, `Pagination.module.css` directly.

* **Filters**: keep the existing grid-based filter form
  (`LetterFilters.module.css:11-15`, already responsive, already
  collapses to one column under 767px) — apply the shared input styling
  from §17 instead of its own copy, and visually separate "Apply"
  (`--color-primary`) from "Clear" (already secondary-styled) more
  clearly via spacing, not new colors.
* **Table**: keep `LetterTable`'s existing sortable-header pattern
  (`.sortButton`/`.sortIndicator`, already keyboard-accessible since
  it's a real `<button>`) — RECOMMENDED tightening row height slightly
  and right-aligning any numeric/date column for scan speed, without
  reducing the existing `--space-sm`/`--space-md` cell padding below
  accessible touch-target size on any actionable cell.
* **Status badges**: apply the corrected color tokens (§2) and the
  shape/icon differentiation (§20) — no change to which statuses exist
  or what triggers them.
* **Pagination**: keep the existing numbered-button pattern
  (`Pagination.module.css`, already has a clear `.current` state and
  disabled-state handling) — purely restyle to the new token set.
* **Create/edit forms, detail view, archive confirmation**: covered in
  §9/§19 respectively — no separate treatment needed here beyond what
  those sections already specify.
* **Information density**: the existing `min-width: 640px` horizontal-
  scroll table (`LetterTable.module.css:12`) is the correct pattern for
  this data shape at narrow widths — **RECOMMENDED to keep**, not
  replace with a card-per-row mobile layout, since a card layout would
  actually reduce scan density for the registry's core use case
  (comparing many letters at once), which the brief's own "information
  density without visual clutter" instruction for this specific screen
  supports.

---

## 9. Letter form (RECOMMENDED)

Reviewed `LetterFormPage.jsx` in full this session (476 lines).

**Confirmed existing strength to preserve exactly**: the form is
already grouped into four semantic `<fieldset>`/`<legend>` sections —
"Reference & subject," "Source," "Sender," "Additional details"
(`LetterFormPage.jsx:320-463`) — this is precisely the "field
grouping/section hierarchy" §9 of the brief asks for; it already exists
and should not be restructured, only visually reinforced (a slightly
heavier `<legend>` treatment using `--font-weight-medium` +
`--color-text-secondary`, §2/§3, and a touch more `--space-lg` gap
between fieldsets than within one).

* **Required-field indicators**: already present as a literal `*` in
  each label (`Reference number *`, conditionally `Source
  Department{!isEdit && ' *'}`, etc.) — RECOMMENDED: keep the `*`
  convention (already correct, already understood by screen readers via
  the `required` attribute + visible text, not a color-only asterisk),
  add a small `--color-danger`-toned rendering for the asterisk itself
  purely for visual scannability, not a new indication method.
* **Focus states**: inherit `:focus-visible` globally already (§1.9) —
  no change needed beyond ensuring the new input styling (§17) never
  overrides it.
* **Select styling**: `DepartmentSelector` and the plain `<select>`
  elements for Designation/Category/Classification currently render as
  the browser's default select box wrapped in the shared field styling
  — RECOMMENDED a consistent custom chevron treatment (CSS-only,
  `appearance: none` + a background-image chevron using `currentColor`,
  no icon-font dependency) applied once via the shared `.field select`
  rule (§17), not per-page.
* **Validation states**: unchanged — `aria-invalid` + `aria-describedby`
  + `role="alert"` already correct (§1.9); only the visual treatment of
  the red border (§2's `--color-danger`) is restyled.
* **Submit behavior / loading state**: `submitting` already disables the
  button and swaps its label to "Saving…"/"Record Letter" appropriately
  (`LetterFormPage.jsx:466-468`) — RECOMMENDED an inline spinner (reusing
  `LoadingState`'s existing spinner visual, §13.C) inside the button
  next to the label, not a page-level overlay.
* **Success feedback**: currently an immediate `navigate()` to the new/
  updated Letter's detail page (`LetterFormPage.jsx:291`) with no
  separate toast/banner — **RECOMMENDED to keep this pattern exactly**;
  landing on the saved record *is* the confirmation, and adding a toast
  on top would be a redundant, motion-for-its-own-sake addition the
  brief's "meaningful motion" principle argues against.
* **Recipient Department / Source Department / Source Location /
  Designation / Classification / Category / Sender information —
  visual distinction (RECOMMENDED)**: these already live in visually
  separate fieldsets (Source vs. Sender vs. Additional details) with
  explanatory `<p className={styles.hint}>` text already distinguishing
  "Source Department" from "Recipient Department" and "Sender's
  Department" in prose (`LetterFormPage.jsx:356-360`,
  `406-409`) — RECOMMENDED reinforcing this with a small left-border
  accent per fieldset type (e.g. neutral for Reference, `--color-info`
  for Source, `--color-text-secondary` for Sender) so the grouping is
  visible at a glance, not only on reading the legend text. Category/
  Classification (SYSTEM_ADMIN-edit-only, §36 of `frontend.md`,
  unchanged by this review) should visually read as "advanced/
  restricted" fields — RECOMMENDED a subtle `--color-border-strong`
  boxed treatment distinct from the always-visible fields above them,
  communicating "not everyone sees this" without adding any new
  client-side authorization logic (the fields are already
  conditionally rendered server-role-based, §25 confirms this must
  stay exactly as-is).

---

## 10. Administration (RECOMMENDED)

Departments, Administrators, Users, Authorizations, Categories,
Classifications, Designations already share one visual language by
construction — every one of these screens was deliberately built by
mirroring `DepartmentListPage`/`DepartmentCreatePage`/
`DepartmentDetailPage` (confirmed directly across Phase 5D and Phase
5H.1's own implementation, and structurally verified again this
session for Category/Classification). The CSS achieving that shared
look is currently split across `AdminPages.module.css` + `DataTable.module.css`
(§1.5's duplication finding) rather than genuinely centralized — the
**recommendation for this section is consolidation, not redesign**:

* Fold `AdminPages.module.css`'s form/detail/list rules and
  `DataTable.module.css`'s table rules into the shared primitives
  proposed in §17/§18, so any of these seven resources changes its look
  by editing one shared stylesheet, never per-resource files.
* Keep the existing Activate-not-confirmed / Deactivate-confirmed
  pattern exactly as-is (§19 covers the dialog visual treatment; the
  underlying confirmation semantics are explicitly out of scope for
  this review, per the brief).
* Status badges, action buttons, and confirmation dialogs across all
  seven resources should visually converge on the same instances (§18,
  §19, §20) rather than each resource's table/dialog looking
  independently "close enough."
* **No resource gets a bespoke visual language** — e.g. Classification's
  `restricts_access` "Yes"/"No" column (Phase 5H.1) should use the same
  text-forward, non-color-only treatment as every status badge, not a
  unique lock-icon-and-glow treatment that would single it out
  stylistically from Category sitting right next to it in navigation.

---

## 11. Documents (RECOMMENDED, security model untouched)

Reviewed `DocumentUploadForm.module.css` and the Phase 5E implementation
record in `PROJECT_STATUS.md`/`frontend/README.md` (no document
endpoint or service file was re-read line-by-line this session, since
its authorization/storage-path handling is explicitly out of this
review's scope and was already deeply verified in Phase 4D/5E).

* **Upload control**: the current form (`DocumentUploadForm.module.css`,
  a plain bordered block with a file input, no drag-and-drop) —
  RECOMMENDED adding a **visual** dropzone affordance (a dashed-border
  region matching `EmptyState`'s existing dashed-border visual language,
  §21, with a click-to-browse `<input type="file">` still doing the
  actual work) and, **RECOMMENDED, OPTIONAL**, native HTML5 drag-and-drop
  event handlers (`onDrop`/`onDragOver`) purely to populate the same
  `<input>`'s file — zero new dependency, zero change to what gets
  validated or how (`validateDocumentFile` in `formValidation.js`
  remains the same pre-check, the backend's magic-byte sniff remains
  authoritative, unchanged).
* **File metadata / upload progress**: keep the existing
  `onUploadProgress`-driven percentage text (already implemented,
  `frontend/README.md`'s Documents section confirms this) — RECOMMENDED
  a slim linear progress bar visual on top of the existing text, not a
  replacement for it (text remains for screen readers via
  `aria-live`, unchanged).
* **Download action / loading / empty / error states**: unchanged
  mechanism (authenticated blob fetch through `apiClient`, synthetic
  anchor click, `URL.revokeObjectURL` — `frontend/README.md` confirms
  this is why a plain `<a href>` cannot be used) — only the button's
  visual treatment changes (§17).
* **Explicit non-negotiables, restated from the brief and already true
  today**: no public URL is ever constructed, no storage path is ever
  rendered or logged to the DOM, and no deletion action exists or is
  added — this review does not touch `documentService.js` and does not
  recommend any change to it.

---

## 12. Notifications (RECOMMENDED, behavior untouched)

`NotificationBell`/`NotificationPanel`/`NotificationItem` reviewed
directly this session.

* **Unread indicator**: fix the color misuse found in §1.1 —
  `.unread`'s background moves from `--color-warning-bg` to the new
  `--color-highlight-bg` (§2); the count badge keeps `--color-danger`
  (correct as an attention color for "you have unread items," unchanged).
* **Bell micro-motion (RECOMMENDED, restrained)**: a brief (150-200ms)
  scale/opacity pulse on the badge *only when the unread count
  increases* (not on every poll tick, not looping) — a single
  micro-interaction that communicates "something changed" without a
  persistent animation competing for attention during normal use. Gated
  behind `prefers-reduced-motion` (§16) — becomes an instant, non-
  animated appearance.
* **Mark-read interaction**: unchanged (explicit-button-only, per Phase
  5E's own deliberate override, `frontend/README.md` confirms) — only
  the button's visual treatment changes (§17), never its behavior or
  when it fires.
* **Letter navigation**: unchanged — clicking a notification's Letter
  link still never marks it read (Phase 5E's own confirmed behavior);
  this review does not touch that logic.

---

## 13. Loading experience (RECOMMENDED)

### A. Application boot

**RECOMMENDED, short and honest**: a boot sequence only for the single
moment that already has real, unavoidable latency — session
restoration (`ProtectedRoute.jsx:21-23`, `status === 'loading'`, which
already exists and already waits on a real `GET /auth/me` call, not a
fabricated delay). Replace the current plain `LoadingState` text
("Restoring your session...") shown at that exact moment with a
branded, centered mark:

```
AJ-OVA LABS
LETTER REGISTRY SYSTEM
```

plus the existing spinner visual (§13.C) — no invented copy like
"Encrypting..." or "Securing..." (the brief's own explicit prohibition,
and correctly so: this app does no client-side encryption or security
handshake beyond the one real network call already happening). The
screen must disappear the instant `GET /auth/me` resolves (success or
failure) — it must never have its own minimum-display timer, which
would be an artificial delay the brief explicitly warns against
("must not unnecessarily delay the application"). On a fast, already-
authenticated reload this may be visible for well under 100ms, which is
correct, not a bug to "fix" by padding it out.

### B. Page / section loading

**RECOMMENDED**: introduce a small number of **skeleton primitives**
(a shimmering rectangle matching the shape of a table row / card /
form field) for the handful of screens where a visible layout shift
currently happens between "loading" and "loaded" — primarily
`LetterListPage`/admin list pages (a table skeleton) and
`DashboardPage` (a card skeleton). **Do not build a skeleton for every
screen** — `LetterDetailPage`/admin detail pages, whose current plain
`LoadingState` text-plus-spinner is brief and layout-stable, do not
need one; adding skeletons everywhere for consistency's own sake would
be motion without purpose, which §15's own principle argues against.

### C. Action loading

**RECOMMENDED, no change to the existing pattern, only its visual
polish**: the codebase already does this correctly everywhere audited
— a submit/action button disables itself and swaps its label to a
present-progressive verb ("Saving…", "Creating…", "Deactivating…",
`submitting`/`saving`/`actionPending` state booleans throughout every
form and detail page). Add the small inline spinner from §9 to these
existing disabled-button states; do not introduce a second, competing
loading pattern (e.g. a page-level overlay) for the same moment.

---

## 14. Loading animation design (SPECIFICATION ONLY — not implemented)

One custom visual identity element, used in exactly the two places
named above (boot screen, and as the shared spinner glyph everywhere
`LoadingState` already appears):

* **Form**: a **geometric registry glyph** — a simple square/rectangle
  outline (evoking a letter/document, not an abstract logo mark) with
  one corner-tracing stroke that animates around its perimeter,
  suggesting "processing," not "decoding" or "scanning" (avoiding any
  connotation of the fake-security theatrics the brief prohibits). This
  is deliberately **not** an orbiting-particles or circuit-line motif —
  those read as the "cyberpunk" aesthetic the brief explicitly rejects.
* **Duration**: 1.2s per full perimeter trace, linear easing (matching
  the existing spinner's own `linear` timing function,
  `LoadingState.module.css:16`, for consistency of "character" between
  old and new motion).
* **Repetition**: infinite while loading is genuinely in progress; never
  a fixed number of loops that could finish before the real operation
  does (which would misrepresent system state — the brief's own §16
  principle: "animations must never be required to understand system
  state," which cuts both ways — an animation must also never *falsely*
  claim state is resolved).
* **Reduced motion**: collapses to a static outline of the same glyph
  (no stroke animation) — mirrors the existing spinner's own
  `prefers-reduced-motion` handling (§1.7) exactly, just applied to the
  new glyph instead of a circular spinner.
* **Where it appears**: the application-boot screen (§13.A, larger
  scale) and as a **direct visual replacement** for `LoadingState`'s
  existing circular spinner everywhere that component is already used
  (§13.B/C) — one glyph, reused everywhere, not a boot-only special
  case and a separate everyday spinner.
* **Not implemented in this phase** — this is a specification for a
  future implementation step (§29) to build as one small, shared
  component (`LoadingGlyph` or an extension of the existing
  `LoadingState`), pure CSS/SVG, zero new dependency.

---

## 15. Micro-interaction system (RECOMMENDED)

A small, closed set of timing tokens — **RECOMMENDED as new CSS custom
properties** in `tokens.css`, not ad hoc per-component durations:

| Token | Value | Used for |
|---|---|---|
| `--motion-instant` | 100ms | hover background/border changes, focus ring |
| `--motion-fast` | 150ms | dropdown/panel open, notification badge pulse |
| `--motion-base` | 200ms | dialog open/close, page-section reveal |
| `--motion-slow` | 350ms | the loading-glyph boot entrance only |
| `--motion-ease` | `cubic-bezier(0.2, 0, 0, 1)` | the one easing curve for every non-linear transition above (a "settle," not a bounce — matches "restrained," not "cinematic-bouncy") |

**Explicitly not recommended**: a page-transition animation between
routes. React Router's navigation here is instant content-swap by
design (no route-level suspense/transition exists today), and adding
one purely for visual flourish risks making every navigation feel
*slower*, directly against the brief's "animations that slow the user
down" prohibition — the safer, faster choice is no page-transition at
all, which is also the current, tested behavior.

Success/error feedback (form submission, action buttons) already
communicate via text-state changes (§13.C) — **RECOMMENDED**: pair
those with the `--motion-fast` background-color transition already
implicit in most `:hover`/state-change rules, not a new toast/snackbar
system (none exists today, and introducing one changes where feedback
appears on-screen — a bigger behavior change than this visual-only
phase should make without explicit confirmation it's wanted).

---

## 16. Reduced motion (REQUIRED, RECOMMENDED implementation)

`prefers-reduced-motion: reduce` must disable or replace, never merely
shorten:

| Animation | Reduced-motion behavior |
|---|---|
| Boot glyph (§13.A/§14) | Static outline, no perimeter trace — screen still appears/disappears at the same real moments (session-restore start/end), only the glyph itself stops animating |
| Loading spinner/glyph everywhere else (§13.B/C) | Same static-outline treatment — matches the existing, already-correct `LoadingState` pattern (§1.7) exactly |
| Sidebar collapse/expand (§6) | Instant width change, no transition |
| Mobile drawer open/close (§6) | Instant show/hide, no slide transition |
| Dialog open/close (§19) | Instant appearance/removal, no fade/scale |
| Notification badge pulse (§12) | The badge still appears/updates instantly — only the pulse animation is skipped |
| Any future page-section reveal | Instant, no fade-in |

No page-transition exists to gate (§15). **Principle, restated from the
brief and already true of the one animation that exists today**:
nothing about *understanding* system state (loading vs. loaded, unread
vs. read, active vs. inactive route) may depend on an animation having
played — every one of the above already has, or will have, a
non-animated equivalent state that conveys the same information
(a static glyph is still visibly "the loading indicator"; an unread
badge is still visibly present without its pulse).

Implementation mechanism: a single `@media (prefers-reduced-motion:
reduce)` block per component (matching the existing, proven
`LoadingState.module.css:25-29` pattern) — **RECOMMENDED against** a
single global "kill all animations" rule, since a global rule cannot
distinguish "this transition is decorative" from "this transition is
the only way a dialog visibly enters" (both need to keep working, just
without motion).

---

## 17. Forms — unified visual language (RECOMMENDED)

Consolidate the five duplicated field-style declarations found in §1.5
into one shared primitive (a `forms.module.css` or equivalent
imported/composed by every page, exact mechanism left to
implementation — CSS Modules support `composes:`, which fits this
without any new tooling):

* **Labels**: `--font-size-sm`, `--font-weight-medium`, unchanged from
  today.
* **Required fields**: the existing literal `*` convention (§9),
  unchanged, restyled only in color emphasis (§2).
* **Inputs/selects/textareas**: unchanged padding/border/radius
  (`--space-sm` / `--color-border-strong` / `--radius-sm`) — add a
  `--motion-instant` (§15) border-color transition on `:focus` for a
  slightly more responsive feel, layered on top of the existing,
  unchanged `:focus-visible` outline (never replacing it).
* **Checkboxes** (Classification's `restricts_access`, Phase 5H.1): keep
  the native `<input type="checkbox">` (already correct, already
  keyboard/screen-reader-native) — RECOMMENDED only a slightly larger
  hit target (`--space-md` square minimum, touch-target-friendly, §23)
  via padding on its label, not a custom-drawn checkbox graphic (a
  custom checkbox risks losing native OS accessibility behavior for a
  purely cosmetic gain).
* **Errors**: unchanged mechanism (`aria-invalid` + `role="alert"` +
  red border) — visual color from §2's corrected `--color-danger`.
* **Helper text** (`.hint`): unchanged — `--color-text-muted`,
  `--font-size-sm`.
* **Disabled state**: unchanged `opacity: 0.6` + `cursor: not-allowed`
  convention, already applied consistently everywhere audited — keep
  exactly as-is.
* **Loading state**: covered by §13.C (button-level only, no separate
  form-wide loading treatment needed beyond what already exists).
* **Success state (RECOMMENDED, new)**: no existing field-level success
  indicator exists anywhere today (only page-level "navigate to the
  saved record," §9) — **RECOMMENDED not to add one**; a per-field green
  checkmark on a form that immediately navigates away on success would
  appear for a few hundred milliseconds at most, which is motion
  without a chance to be perceived, let alone useful.

---

## 18. Tables — unified visual language (RECOMMENDED)

Consolidate `DataTable.module.css` and `LetterTable.module.css` (§1.5)
into one shared base, with resource-specific extras (`.actionsCell`,
`.sortButton`) layered on top via `composes:` or a second, small
resource-specific stylesheet — never re-declaring the shared rules.

* **Header**: unchanged (`--color-bg` background, muted medium-weight
  text) — this is already a clean, restrained treatment.
* **Rows / hover**: unchanged `--color-bg` hover — RECOMMENDED adding
  the `--motion-instant` background transition (§15) so hover feels
  responsive rather than an instant snap.
* **Selected state**: **does not exist today** — no table in this
  application supports row selection (no bulk actions exist anywhere in
  the confirmed backend contract) — **explicitly not recommended to
  add**; a selected-row style with nothing to select for would be a
  purely decorative addition.
* **Sorting**: unchanged — `LetterTable`'s existing `.sortButton`/
  `.sortIndicator` pattern (real `<button>`, already keyboard-
  accessible, already has an `aria-sort`-capable structure per
  `frontend/README.md`'s own description) is the correct pattern;
  extend its exact visual treatment, never its mechanism, to any future
  sortable table (none of the current admin resources support backend
  sorting, so none should visually imply they do, per §1.5's own
  scoping note in `DataTable.module.css`'s docstring).
* **Pagination**: unchanged (§8) — visually restyled only.
* **Status**: §20.
* **Actions**: unchanged `.actionsCell` button-row pattern — restyled
  via §17's shared button treatment.
* **Empty state**: §21.
* **Loading skeleton**: §13.B — a table-row skeleton shape, used only on
  the list pages named there.
* **Responsive behavior**: unchanged horizontal-scroll-within-
  `.scroller` pattern (§8's rationale for the registry applies equally
  to every admin table) — RECOMMENDED against converting to stacked
  cards on mobile for the same information-density reasoning.

---

## 19. Dialogs (RECOMMENDED, confirmation semantics untouched)

`ConfirmDialog` and `ArchiveConfirmDialog` (§1.5's confirmed near-
duplicate) should be visually and structurally unified into one shared
modal language — **RECOMMENDED**: retire `ArchiveConfirmDialog`'s
separate CSS file in favor of `ConfirmDialog.module.css` (a pure CSS
consolidation; whether `ArchiveConfirmDialog` becomes a thin wrapper
around `ConfirmDialog` or stays a separate component using the same
class names is an implementation-time decision, not a visual-design
one, and either way **no confirmation wording, `tone` behavior, or
Escape/focus-trap logic changes**).

* **Backdrop**: unchanged `rgba(0,0,0,0.45)` scrim — correct, restrained
  contrast against the dialog without a blur effect (§5's anti-
  glassmorphism stance).
| **Panel**: unchanged `--radius-md` + `--shadow-md` (§5) — the one
  place in the app a shadow is fully justified (a genuinely floating
  element).
* **Title/body**: unchanged structure (`<h2 id=...>` + `<p>`) — apply
  §3's typography tokens only.
* **Actions**: unchanged right-aligned Cancel/Confirm button row.
* **Destructive-action emphasis**: already exists and is correct —
  `tone="caution"` renders the confirm button in `--color-danger`
  (`ConfirmDialog.jsx:80`, `.confirmCaution`) — **RECOMMENDED**: keep
  this exact mechanism, apply corrected token values only.
* **Escape / focus trap**: unchanged — already fully implemented and
  tested (§1.9); this review adds no behavior here, only confirms it
  must not regress.
* **Mobile layout**: unchanged `padding: var(--space-lg)` around the
  backdrop already prevents the dialog from touching the viewport edge
  on small screens (`ConfirmDialog.module.css:8`) — RECOMMENDED no
  further change; the existing `max-width: 420px` with `width: 100%`
  already degrades correctly.
* **Open/close motion (RECOMMENDED, new)**: a `--motion-base` (§15)
  fade + slight scale-in on open, matching reverse on close — the one
  place in this review where a dialog "opening" benefits from being
  perceptible rather than an instant swap, since it's a significant,
  attention-demanding state change; gated by §16's reduced-motion rule
  exactly like everything else.

---

## 20. Status system (RECOMMENDED, no new statuses)

`StatusBadge`/`statusLabels.js` reviewed directly. The seven real
enum values (`ACTIVE`/`INACTIVE`/`ARCHIVED`/`PENDING_APPROVAL`/
`DEACTIVATED`/`USED`/`REVOKED`) map to four visual tones today
(positive/neutral/warning/negative) — **RECOMMENDED to keep this exact
4-tone mapping** (it is already a sound simplification: `ARCHIVED`,
`INACTIVE`, `DEACTIVATED`, and `USED` are all "neutral, no longer the
default state" and do not need four different colors to communicate
that).

* **Text**: already always present (`StatusBadge.jsx`, `label ?? value`
  — never color-only) — unchanged, this is correct today.
* **Color**: corrected per §2 (ACTIVE gets its own `--color-success-bg`,
  no longer sharing `--color-warning-bg`).
* **Icon (RECOMMENDED, new, restrained)**: a small (12px) geometric
  glyph per tone — a filled dot for positive, an outlined dot for
  neutral, a triangle for warning, an outlined "x" or bar for negative
  — placed before the text, `aria-hidden="true"` (the text remains the
  accessible name, exactly as today). This gives a *shape* differentiator
  on top of color and text, directly serving the brief's "use text,
  icon where appropriate, shape, contrast" instruction, without
  introducing an icon font/library — four small inline SVGs (or one
  SVG sprite) cover the entire set, zero new dependency.
* **Shape**: unchanged pill/rounded-rectangle badge shape (§5) — already
  visually distinct from a plain text label.
* **Contrast**: re-verified against §2's corrected tokens — all four
  tones meet WCAG AA for their text-on-background pairing.
* **No new statuses are proposed or implied** — this section is a
  rendering-layer change only.

---

## 21. Empty / error states (RECOMMENDED, backend semantics untouched)

`EmptyState`/`ErrorState` are already applied uniformly (§1.9) — this
section proposes visual refinement only, explicitly preserving the
existing 403/404/network distinctions:

* **No records** (`EmptyState`, unchanged dashed-border box) —
  RECOMMENDED: keep the exact structure, add one small, restrained
  glyph (an outlined document/tray icon, matching §14's "registry
  glyph" character so empty states feel like a deliberate design
  language, not a missing-content placeholder) above the existing
  message text.
* **No notifications / no documents / no designations** — same
  `EmptyState` component, resource-specific message text unchanged
  (already correct per-page today).
* **Network error** (`ErrorState` with `onRetry`) — unchanged mechanism
  (already the correct pattern: a visible retry button, never a
  silent/auto-retry) — restyle only.
* **Authorization error (403) vs. Not found (404)** — **CONFIRMED
  current behavior, must not change**: this application's backend
  deliberately collapses "classified and inaccessible," "wrong
  department," and "genuinely nonexistent" into one generic 404
  (`frontend/README.md`'s "Classified-record safety" section, §1.9's
  a11y review, and every prior phase's own explicit instruction confirm
  this). **This review does not add a distinct 403 visual treatment for
  Letters** — doing so would let the frontend leak exactly the
  information ("this exists but you can't see it" vs. "this doesn't
  exist") the backend's 404 design deliberately withholds, directly
  violating §21 and §25's own explicit instruction not to convert
  403↔404. Genuine 403s that *do* exist today and are already
  distinguished (e.g. `UserDetailPage`'s "your own department is
  inactive" 403 phrasing, Phase 5D) keep their existing distinct
  message text — only the visual container (`ErrorState`) is restyled,
  never the message logic.
* **Validation error** — unchanged (§17) — inline, `role="alert"`,
  never a separate error page.

---

## 22. Responsive design (RECOMMENDED)

* **Breakpoints**: formalize the two literal values already in
  consistent use (§1.6) as a documented convention — `768px` (tablet)
  and `1024px` (desktop) — **RECOMMENDED**: since CSS custom properties
  cannot be read inside `@media` (confirmed limitation, §1.6), keep
  literal values but standardize on exactly `max-width: 767.98px` /
  `min-width: 768px` pairing project-wide (resolving the current
  767/768/480-mixed literals into one documented pair, plus the
  existing 480px-only breakpoint for the notification panel's own
  small-screen fixed-position behavior, which is a correct exception,
  not an inconsistency, since no other component needs a third
  breakpoint).
* **Sidebar**: collapses to icon rail at `<1024px` (RECOMMENDED,
  automatic, in addition to the manual toggle from §6), becomes the new
  off-canvas drawer at `<768px` (§6).
* **Tables**: unchanged horizontal-scroll pattern (§8/§18) at every
  breakpoint — the correct choice for this data shape, restated.
* **Forms**: unchanged single-column stacking below 768px (already
  correct in every form module audited) — no change proposed.
* **Dashboard cards**: unchanged existing 3-tier grid (`auto-fit
  minmax(180px,1fr)` → 2-column at 768px → 1-column at 480px,
  `DashboardPage.module.css:13-40`) — already well-tuned, no change
  proposed.
* **Dialogs**: unchanged (§19) — already correctly responsive via
  `max-width` + viewport padding.
* **Notification panel**: unchanged existing `position: fixed`
  full-width treatment under 480px (`NotificationPanel.module.css:66-74`)
  — already correct.
* **Document upload**: unchanged existing full-width submit button under
  767px (`DocumentUploadForm.module.css:55-59`) — already correct.

---

## 23. Accessibility (AUDIT against WCAG, RECOMMENDED fixes)

| Area | Current state | Recommendation |
|---|---|---|
| Contrast | Already AA-compliant across the audited palette (§1.1); the one bug (§1.1) doesn't fail contrast, it fails *meaning* | §2's corrected tokens fix the meaning issue; re-verify contrast on any new token (`--color-accent`, `--color-info`, `--color-highlight-bg`) before implementation |
| Focus visibility | CONFIRMED strong baseline (§1.9), global `:focus-visible`, never removed | Preserve exactly; any new interactive element (collapsible sidebar toggle, drawer, dropzone) must inherit it, never define a competing focus style |
| Keyboard navigation | CONFIRMED: dialogs already Tab-trapped, nav already real anchors, sort buttons already real buttons | New elements (drawer toggle, collapsible-sidebar toggle, dropzone) must be real `<button>`s, keyboard-operable with no new custom key handling beyond what `ConfirmDialog` already proves works |
| Reduced motion | CONFIRMED: one correct existing pattern (§1.7) | Extend identically to every new animation (§16) — no exceptions |
| Labels | CONFIRMED: every form field already has an associated `<label htmlFor>` | No change; new fields (if any future phase adds them) must follow the same pattern |
| Status communication | CONFIRMED: text-first already (§1.9, §20) | Icon addition (§20) is `aria-hidden`, additive only, never the sole signal |
| Error communication | CONFIRMED: `role="alert"` + `aria-describedby` already correct | No change to mechanism; only visual restyling |
| Touch target size | Not fully audited previously — checkboxes (§17) and the notification bell (`2.25rem` square, `NotificationBell.module.css:10-11`, already meets the 44px-equivalent guideline) are fine; **RECOMMENDED check during implementation**: the collapsible-sidebar toggle and mobile hamburger (new elements, §6) must each be at least 44×44px |

**No aesthetic decision in this review is allowed to reduce any of the
"CONFIRMED strong baseline" rows above** — this is a hard constraint
carried into §29's implementation sequence (accessibility pass, step
19, but continuously re-verified at every step, not deferred to the end).

---

## 24. Performance (RECOMMENDED budget)

* **CSS vs. JS animation**: every animation proposed in this review
  (§14, §15, §19) is a pure CSS `transition`/`@keyframes` — **no JS
  animation library is needed or recommended** (§31 confirms this
  explicitly as policy).
* **Layout thrashing**: the collapsible sidebar (§6) should animate
  `width` via a CSS transition on a fixed-width flex child, which is a
  compositor-cheap property change at this scale (220px↔64px, a small
  element, not a full-page reflow trigger) — RECOMMENDED verifying with
  the browser's own paint-flashing tool during implementation, not
  assumed safe without a check.
* **Expensive shadows / blur**: the entire proposal uses exactly two
  shadow levels (§5), both already proven in production use today
  (dialogs, notification panel) — no new expensive shadow is introduced;
  `backdrop-filter`/blur is explicitly not recommended anywhere (§5).
* **Large gradients**: none proposed anywhere in this document — the
  entire color system (§2) is flat fills, consistent with the "avoid
  excessive gradients" instruction.
* **Unnecessary re-renders**: out of scope for a visual-only review (no
  component logic changes are proposed) — flagged as a **FUTURE**
  concern only if a future phase touches component internals, which
  this one does not.
* **Bundle size**: zero new dependencies (§31) means the current 368KB/
  110KB-gzip production bundle (confirmed by the most recent `npm run
  build` output, Phase 5H.1) should not measurably grow — a handful of
  new CSS Module files and a few small inline SVGs (§20's status icons)
  add low-single-digit KB at most.
* **No animation should noticeably slow normal interactions** — every
  duration proposed in §15 is under 350ms, well within the ~100-400ms
  range generally accepted as "responsive, not sluggish"; nothing
  in this review adds a required wait before an action can proceed
  (every animation is decorative-on-top, never blocking).

---

## 25. Security boundary (CONFIRMED, hard constraint)

Restated as a hard constraint on the entire visual proposal above, not
merely a checklist:

* **No JWT decoding, no token inspection** — nothing in this review
  reads or needs to read the token; every role-conditional visual (§6,
  §9, §10) already comes from `AuthContext`'s existing `user` object,
  itself sourced only from backend responses (`frontend.md` §22,
  unchanged).
* **No new role inference** — the SYSTEM_ADMIN-only visual treatment
  proposed for Category/Classification fields (§9) uses the exact same
  `isSystemAdmin` boolean `LetterFormPage.jsx` already computes from
  `user.role` — no new client-side role logic is introduced.
* **No Letter authorization or classified-visibility logic** — §21
  explicitly rejects distinguishing 403-shaped from 404-shaped
  "not found" for Letters, precisely to avoid the frontend inferring
  anything about classified-access the backend hasn't already decided.
* **No storage paths, no document URLs, no `recipient_user_id`
  exposure, no public links** — none of §11's document recommendations
  touch `documentService.js`, the authenticated-blob-fetch download
  mechanism, or any response field; this review adds visual treatment
  around an unchanged data flow only.
* **No backend error bypass** — §21's error-state visual refinement
  renders the same `error.message`/`error.status` values already
  normalized by `errorNormalization.js` (untouched); no new client-side
  interpretation of an error code is added.
* **Everything in this document is presentation-only** — every
  recommendation is expressed as a CSS Module change, a new CSS custom
  property, a new small presentational component (loading glyph, status
  icon), or a client-side-only UI preference (sidebar-collapsed state
  in `localStorage`, §6) — none reads, writes, or infers anything about
  authorization, classification, or document security.

---

## 26. AJ-OVA Labs branding (RECOMMENDED, not implemented)

* **Wording**: "A Project by AJ-OVA Labs" — exactly as specified.
  (Note for the implementer: `constants/app.js:12` already defines a
  *different*, currently-unused string, `PRODUCTION_CREDIT = 'A
  Production of AJ-Labs'` — §1.8 confirms this exists but is dead code.
  **RECOMMENDED**: update that constant's value to the new wording
  rather than adding a second, competing constant, and finally wire it
  into the shell.)
* **Placement**: a slim footer row inside `AppShell.module.css`'s
  `.main` column, below `<main>`, always visible (not scroll-dependent,
  not a floating element) — RECOMMENDED height under 32px, `--font-
  size-xs` (§3), `--color-text-muted`, centered or right-aligned, never
  competing visually with the page content above it.
* **Consistency**: rendered once, in `AppShell.jsx`, so it appears
  identically on every authenticated screen — **RECOMMENDED, PENDING
  BUSINESS CLARIFICATION**: whether it should also appear on
  `LoginPage`/`SignupPage` (currently outside `AppShell`, rendered via
  `AuthPages.module.css`'s own centered card layout) — a reasonable
  default is yes, for consistent branding pre- and post-login, but this
  review does not assume that decision.
* **Restraint**: one line, muted color, no logo mark proposed (none
  exists today, and inventing one is a branding decision outside a UI
  architecture review's scope) — explicitly must not dominate or
  distract from the application's own content, matching the brief's own
  instruction.

---

## 27. Futuristic visual identity (RECOMMENDED synthesis)

Bringing together §2-§20 into one coherent identity statement, per the
brief's explicit request not to just say "dark mode + neon":

* **Visual metaphor**: the *ledger/registry* — a system whose job is
  precise, auditable record-keeping. Every motif in this review (the
  registry glyph, §14; the dashboard section rule, §7; the fieldset
  left-border accents, §9) traces back to "a line, precisely drawn,"
  not "a glow, generously applied." This is what makes "futuristic"
  read as *precision* rather than *decoration* — the emotional target
  the brief names ("this looks like a serious system built for the
  future," not a game).
* **Accent strategy**: one primary hue (existing blue, §2, deliberately
  kept), one narrow-use secondary accent (`--color-accent` teal, §2)
  reserved for "notable, not actionable," and status colors that never
  double as decoration — three roles for color, never more, so nothing
  competes with the primary action color for attention.
* **Geometric language**: rectangles and hairlines, not circles/blobs —
  the registry glyph (§14) is literally a rectangle with a traced
  border; badges (§20) are the only rounded/pill shapes in the system,
  and only because a status pill is a genuinely established UI
  convention users already recognize, not a stylistic flourish.
* **Surface language**: flat-bordered for structure, one subtle shadow
  step for anything temporarily elevated (§5) — depth communicates
  *state* (resting vs. floating), never decoration for its own sake.
* **Typography character**: a plain, confident system sans for
  everything humans read at length, an optional monospace only for
  numbers/IDs (§3) — "precise" over "stylized," matching the brief's
  explicit adjective list.
* **Motion character**: short, purposeful, always meaning-bearing (§15) —
  "restrained" and "meaningful," never ambient/looping decoration except
  the two loading indicators (§13/§14), which are the one place
  continuous motion is honestly justified (a real, unresolved wait).
* **Iconography**: minimal by design — four status glyphs (§20), one
  loading glyph (§14), one empty-state glyph (§21), and nothing else;
  no icon library, no icon-per-nav-item unless a future phase confirms
  it's wanted (§6 leaves this optional). A system that uses fewer,
  more deliberate glyphs reads as more custom-built than one that
  reaches for a generic 1,000-icon set.
* **Data visualization language (FUTURE, specification only)**: no
  chart exists or is proposed (§7's explicit constraint) — **if** a
  future, separately-authorized phase ever adds one (gated on Phase
  5G's own unresolved "is analytics wanted at all" business question,
  `PROJECT_STATUS.md`), it should use the same restrained palette (§2),
  the same tabular-numeral treatment (§3), and flat fills with hairline
  gridlines — no gradient fills, no 3D effects, no neon glow on data
  series, keeping visual continuity with the rest of the system rather
  than importing a different, more "dashboard-trendy" visual language
  just because charts conventionally invite one.
* **Branding treatment**: restrained, textual, footer-only (§26) — the
  "premium" feeling this system should project comes from the
  consistency and precision of the system itself, not from a prominent
  logo or splash of brand color.

---

## 28. Explicit non-changes

The following remain completely untouched by any recommendation in
this document, and by the implementation phase(s) that follow it:

* **API contracts** — no request/response shape, query parameter, or
  status code changes.
* **Backend authorization** — `require_system_admin`, `require_user_or_
  admin`, `assert_letter_access`, `assert_department_access`, and every
  other backend-side check remain byte-for-byte unchanged.
* **Database / migrations** — no model, schema, or Alembic file is
  touched; no migration is created.
* **Business rules** — Letter/Category/Classification/Department/Admin/
  User/Designation lifecycle rules, validation requirements, and
  uniqueness constraints are unchanged.
* **Notification behavior** — trigger conditions, recipient strategy,
  polling target, and explicit-mark-read semantics are unchanged (only
  the unread-row color token and a badge micro-pulse change, §12).
* **Classification enforcement** — `restricts_access`'s effect on Letter
  visibility remains entirely `assert_letter_access`'s decision, never
  computed or duplicated client-side (§9, §25).
* **Document security** — upload validation, storage-path generation,
  and the authenticated-blob-download mechanism are unchanged (§11).
* **Role hierarchy** — SYSTEM_ADMIN/ADMIN/USER capabilities and
  boundaries are unchanged; every role-conditional visual is driven by
  the same `user.role` value already in use today.
* **Existing validation semantics** — every `validate*Form` function in
  `formValidation.js`, and every backend-side Pydantic validator, is
  unchanged; error *messages* are unchanged, only their container's
  visual treatment (§17, §21).
* **Existing test behavior** — no functional assertion in any of the
  320 current frontend tests is expected to need a behavior change (see
  §30 for what *does* need new coverage).

---

## 29. Implementation sequence (RECOMMENDED)

The brief's own suggested order is sound and matches this review's own
dependency analysis — adopted with one adjustment (status system moved
earlier, since tables/dashboard/registry all consume it, so fixing its
color-token bug before touching any screen that displays a badge avoids
re-touching those screens twice):

1. Global design tokens (§2, §3, §4, §5, §15) — color, typography,
   spacing (unchanged), shape/depth, motion timing tokens, all in
   `tokens.css`.
2. Status system (§20) — fixes the confirmed color-token bug (§1.1)
   before any screen displaying a badge is next touched.
3. Global typography/background (§3) applied via `global.css`.
4. Core controls — shared form/button/table primitives (§17, §18)
   consolidated out of the five/two duplicated stylesheets (§1.5).
5. App shell — Sidebar/Topbar structure updates for collapse + drawer
   (§6).
6. Dialogs (§19) — consolidate `ConfirmDialog`/`ArchiveConfirmDialog`.
7. Tables (§18) applied to Letters + every admin resource (§8, §10).
8. Forms (§17) applied to Letter form (§9) and every admin form (§10).
9. Dashboard (§7).
10. Documents (§11).
11. Notifications (§12).
12. Authentication pages (`AuthPages.module.css` gets the same token/
    button/input treatment as everything else, plus §26's branding
    footer if the pending business question resolves yes).
13. Loading system (§13, §14) — boot screen, skeletons, the shared
    loading glyph — sequenced late deliberately, since it depends on
    the final token/motion system from steps 1-2 being settled first.
14. Empty/error states (§21).
15. Responsive refinement pass (§22) across every screen touched above.
16. Accessibility pass (§23) — re-verification, not a first pass (every
    step above must already preserve the §1.9 baseline continuously).
17. Footer/branding (§26) — deliberately last among visual features, so
    it's added once, onto a finished shell, not repeatedly adjusted as
    the shell itself changes shape (sidebar collapse, drawer).
18. Full regression — functional suite (unchanged expectations, §28) +
    the new visual/behavioral tests from §30.

---

## 30. Test strategy (RECOMMENDED)

**All 320 existing frontend tests and 487 backend tests must continue
to pass unmodified in their assertions** — this review recommends
*additive* tests only, never replacing a functional assertion with a
snapshot.

New coverage recommended once implementation happens:

* **Reduced-motion behavior** — for each new animated element (loading
  glyph, dialog open/close, notification badge pulse, sidebar collapse),
  a test that mocks `window.matchMedia('(prefers-reduced-motion:
  reduce)')` to return `true` and asserts the relevant class/attribute
  reflects the non-animated state — mirroring the pattern already
  possible today (though not currently tested) for `LoadingState`'s
  existing spinner.
* **Keyboard interaction** — a test that the new sidebar-collapse
  toggle and mobile-drawer toggle are real, focusable, Enter/Space-
  activatable buttons (matching the existing `ConfirmDialog`/`RoleGuard`
  test style already in the suite).
* **Dialog behavior** — re-run existing `ConfirmDialog.test.jsx`
  assertions unchanged (Escape, Tab-trap, backdrop click) once its CSS
  is consolidated with `ArchiveConfirmDialog`'s (§19) — if the two
  components are ever merged into one, `ArchiveConfirmDialog.test.jsx`'s
  own assertions must still all pass against whatever the merged
  component is called.
* **Responsive-critical behavior** — a test asserting the mobile drawer
  is closed by default and opens only via its toggle (jsdom doesn't
  evaluate real media queries, so this is really a state/behavior test
  of the toggle component, not a true viewport test — consistent with
  how this suite already handles responsive logic, i.e. it doesn't
  attempt real breakpoint testing anywhere today).
* **Loading states** — a test per skeleton-bearing page (§13.B)
  asserting the skeleton renders while `loading` is true and is replaced
  by real content once data resolves, mirroring every existing
  `LoadingState`-based test already in the suite.
* **Footer presence** — one test on `AppShell.test.jsx` (a new file, if
  one doesn't already exist for AppShell — confirmed not to exist today,
  grepped) asserting the footer text renders exactly once, consistently,
  regardless of role.
* **Navigation** — existing `Sidebar`/`navigationConfig` tests extended
  to cover the collapsed-state toggle without needing to duplicate the
  entire existing role-based nav-item assertion set.
* **Role-specific rendering** — no new test category needed beyond what
  already exists (§25 confirms no new role logic is introduced); any
  visual change to a role-gated element should be verified against the
  same existing role-based test pattern used throughout Phase 5D/5H/5H.1.

**Explicitly not recommended**: broad visual/snapshot regression testing
across every page (the brief's own instruction: "do not replace
functional tests with snapshot-heavy tests") — this project's existing
test culture (assert specific behavior, specific text, specific ARIA
attributes) should extend to new visual behavior the same way, not pivot
to a different testing philosophy for this one phase.

---

## 31. Dependency policy (CONFIRMED feasible at zero new dependencies)

`package.json` reviewed directly this session (§1): the current
dependency set is already minimal — `react`, `react-dom`,
`react-router-dom`, `axios` (runtime); `vite`, `@vitejs/plugin-react`,
`vitest`, `@testing-library/*`, `jsdom` (dev/test). **Every
recommendation in this document is achievable with this exact set**:

* Colors/typography/spacing/shape/motion tokens — plain CSS custom
  properties, zero dependency.
* Loading glyph, status icons, empty-state glyph — inline SVG or pure
  CSS shapes, zero dependency (no icon font/library needed).
* Collapsible sidebar, mobile drawer — React state + CSS transition,
  zero dependency.
* Skeleton loaders — CSS `@keyframes` shimmer on plain `<div>`s, zero
  dependency.
* Tabular numerals — a CSS property (`font-variant-numeric`), zero
  dependency.
* Optional monospace font (§3) — a system font stack, zero dependency,
  zero network request.
* Dialog open/close motion — CSS transition on an existing component,
  zero dependency.

**No UI framework, no animation library, no icon library is
recommended.** The one intentionally-flagged **optional, not
recommended-by-default** item is a self-hosted `@font-face` (§3) — even
that requires no new *package*, only an asset file, and is explicitly
gated as optional rather than assumed.

---

## 32. Manual E2E plan (for the eventual implementation phase)

To be executed once visual implementation lands — not performed as part
of this review (no code was changed). All three roles
(SYSTEM_ADMIN/ADMIN/USER) where relevant:

1. **Login** (all three roles) — boot/session-restore visual (§13.A),
   form validation states (§17), successful redirect into `/app`.
2. **Signup** — pending-approval notice visual (§21's empty/notice
   styling), field validation states.
3. **Logout** — from Topbar, all three roles, confirms redirect to
   `/login` and no residual authenticated visual state.
4. **Dashboard** (all three roles) — correct role-scoped cards render
   with real data, "Unavailable" renders correctly if a widget is
   forced to fail (e.g. via DevTools network throttling/blocking one
   endpoint), skeleton (§13.B) visible briefly on a throttled
   connection.
5. **Letters** — list/filter/sort/paginate visual, create (all
   fieldsets, §9), edit, archive confirmation dialog (§19), classified-
   Letter 404 still renders generically (§21 — explicitly verify this
   has NOT changed).
6. **Source Department** — selector renders, auto-fill still works,
   required-on-create-only behavior unchanged.
7. **Designation** — same as above; zero-designations empty message
   still renders correctly (§21).
8. **Documents** — upload (new dropzone visual, §11), progress display,
   download, empty state, a forced upload error.
9. **Notifications** — bell badge (new pulse micro-interaction, §12),
   panel open/close, mark-read (behavior unchanged), full page.
10. **Departments** (SYSTEM_ADMIN) — list/create/detail/activate/
    deactivate, confirmation dialog visual.
11. **Administrators** (SYSTEM_ADMIN) — list/authorize/detail/approve/
    deactivate/reactivate, transfer dialog.
12. **Users** (ADMIN) — list/authorize/detail/approve/deactivate/
    reactivate/authorizations list/revoke.
13. **Authorizations** — creator-scoped revoke visual, confirm dialog.
14. **Categories** (SYSTEM_ADMIN) — list/create/edit/activate/
    deactivate, confirm dialog against new-permission-consolidated CSS
    (§10, §19).
15. **Classifications** (SYSTEM_ADMIN) — same, plus `restricts_access`
    checkbox/"Yes"/"No" visual (§10).
16. **Responsive navigation** (all three roles, resize to <768px and
    <1024px) — collapsible sidebar (§6), mobile drawer open/close,
    keyboard operability of both toggles (§23).
17. **Dialogs** (any resource) — Escape closes, Tab traps between
    Cancel/Confirm, backdrop click cancels, mobile viewport layout.
18. **Loading states** — boot screen on a fresh session restore,
    skeletons on list/dashboard pages under network throttling,
    button-level loading on every submit action.
19. **Footer** — visible on every authenticated page and (pending §26's
    open business question) the login/signup pages, correct wording,
    never obscuring content.
20. **Reduced motion** (OS-level setting enabled) — repeat steps 4, 9,
    16, 17, 18 and confirm every animation named in §16 is absent while
    all information is still fully conveyed.

---

## 33. Documentation

**Created** (this document): `docs/architecture/ui-design-system.md` —
review document only, as required.

**To be updated** (lightweight pointers, not rewrites, matching this
project's own established documentation-update style from prior
phases):

* `README.md` — add a Phase 5I row to the phase table ("Futuristic UI /
  Visual Architecture & Design System Review — Complete (review only)"),
  update the "Current status" banner line.
* `docs/README.md` — add `ui-design-system.md` to the `architecture/`
  directory's own row in its documentation index.
* `docs/PROJECT_STATUS.md` — a new "Current Phase" entry describing this
  review (review-only, no code), demoting Phase 5H.1 to a prior-phase
  entry, exactly matching the pattern already used for every previous
  phase transition in that file.
* `docs/architecture/frontend.md` — a short cross-reference note near
  §26 ("Design system") pointing to this new document as the detailed
  visual-system follow-up, without duplicating its content there.
* `docs/architecture/overview.md` — a one-line mention that a visual/UI
  design review (Phase 5I) exists and is documented separately, since
  this file's own per-role capability descriptions are unaffected by a
  presentation-only review.

**Not created**: no second large architecture document — this single
file is the complete review artifact, per the brief's own instruction
that this document is the deliverable.

---

## 34. Scope confirmation

* **No code was modified.** Every file this review touched was opened
  with the `Read`/`Grep`/`Glob` tools only.
* **No test was modified or added.**
* **No dependency was added, removed, or upgraded** — `package.json`
  was read, not edited.
* **No backend file was modified.**
* **No database file was modified.**
* **No migration was created.**
* **No frontend functionality changed** — no component, route, or
  service file was edited.
* **Nothing was committed.**
* **Nothing was pushed.**

This document, and the five documentation files named in §33 (to be
updated as a documentation-only follow-up to this same review), are the
only artifacts of Phase 5I.

---

## Phase 5I.1 — Global Visual Foundation: Implementation Record

The first implementation pass against this review. **Global foundation
only** — no page, layout, or feature component was redesigned; every
item below is a token, a global CSS rule, or the two named bug fixes
explicitly authorized for this phase. Verified by direct file read
before editing (`frontend/package.json`, `tokens.css`, `global.css`,
`App.jsx`, `main.jsx`, `AppShell`/`Sidebar`/`Topbar` and their CSS
Modules, `StatusBadge`/`NotificationItem`, and the relevant test files)
— nothing below was assumed from this review document without
re-checking the current source first.

**IMPLEMENTED**:

* **Color tokens** (`tokens.css`) — additive only, every Phase 5A token
  unchanged: `--color-text-primary` (alias for the existing
  `--color-text`, not a rename — no component file was touched to adopt
  it), `--color-text-secondary`, `--color-border-subtle`,
  `--color-surface-elevated`, `--color-accent`, `--color-info`,
  `--color-info-bg`, `--color-success-bg`, `--color-highlight-bg`.
* **Motion tokens** (`tokens.css`) — `--motion-instant` (100ms),
  `--motion-fast` (150ms), `--motion-normal` (200ms), `--motion-slow`
  (350ms), `--motion-ease` (`cubic-bezier(0.2, 0, 0, 1)`), exactly the
  values §9/§15 above specify.
* **ACTIVE badge / unread-notification bug (§1.1/§6 above), fixed** —
  `StatusBadge.module.css`'s `.positive` background changed from
  `var(--color-warning-bg)` to the new `var(--color-success-bg)`;
  `NotificationItem.module.css`'s `.unread` background changed from
  `var(--color-warning-bg)` to the new `var(--color-highlight-bg)`. No
  class name, label, or status value changed; no `.test.jsx` asserts on
  either rule's color (verified by reading `NotificationItem.test.jsx`
  and confirming no `StatusBadge.test.jsx` exists), so no test needed
  updating for this fix.
* **Global background** (`global.css`, `body`) — a static, single
  radial-gradient wash (`rgba(31, 79, 216, 0.05)` fading to transparent,
  anchored top-left, `background-attachment: fixed`) layered under the
  existing flat `--color-bg`. No animation, no JavaScript; every real
  surface (cards, tables, dialogs, sidebar, topbar) remains fully opaque
  on top of it, so no content's contrast is affected.
* **Global focus system** (`global.css`, `:focus-visible`) —
  strengthened, not replaced: the existing 2px solid outline is
  unchanged and remains the primary, always-present signal; a low-
  opacity (`rgba(31, 79, 216, 0.16)`) `box-shadow` halo was added purely
  as visual reinforcement.
* **Reduced-motion foundation** (`global.css`, new
  `@media (prefers-reduced-motion: reduce)` block) — a global safety net
  collapsing every animation/transition duration to `0.01ms` and
  disabling smooth scrolling, so any animation a later phase adds is
  automatically covered without a per-component override being written
  or forgotten. `LoadingState`'s existing, more specific
  `prefers-reduced-motion` rule is unchanged and continues to apply
  unaffected (the two rules do not conflict — the more specific one
  simply also matches).
* **Global transitions** (`global.css`) — one rule targeting
  `a, button, input, select, textarea` for `color`,
  `background-color`, `border-color`, `opacity`, `box-shadow` only, at
  `--motion-instant` — explicitly never `transition: all` and never a
  layout-triggering property. Applies to every existing hover/focus/
  disabled state across every current page/component with zero edits to
  any component's own CSS Module.
* **Footer constant text** (`constants/app.js`) — `PRODUCTION_CREDIT`'s
  value updated to the approved wording, "A Project by AJ-OVA Labs." Not
  yet rendered anywhere.

**DEFERRED** (explicitly out of this phase's scope, per its own brief):

* Visible footer rendering/placement inside `AppShell` — requires
  touching the shell, reserved for the shell-redesign phase.
* Sidebar/Topbar collapse, mobile drawer, active-route accent bar (§6
  above).
* The boot screen and the loading-glyph visual identity (§13/§14 above)
  — no new animation was added this phase, only the reduced-motion
  foundation it will rely on.
* Dashboard/Letter/Administration/Documents/Notifications/Authentication
  page-level visual treatment (§7-§12 above).
* Status-badge icon layer (§20 above) — only the one color-token bug was
  fixed; no new glyph was added.
* Table/form/dialog consolidation (§17-§19 above) — the duplicated CSS
  identified in §1.5 is unchanged; this phase did not edit
  `AdminPages.module.css`, `LetterFormPage.module.css`,
  `DataTable.module.css`, `LetterTable.module.css`,
  `ConfirmDialog.module.css`, or `ArchiveConfirmDialog.module.css`.
* Text-selection and scrollbar styling — **not implemented**, because
  this review never recommended either (§11 above proposes them only
  conditionally, "if the architecture review recommends these"; it did
  not for this codebase), and the Phase 5I.1 brief says to leave them
  unchanged absent that recommendation.
* `--radius-pill` / any new radius or shadow level — not introduced;
  the existing two-radius/two-shadow hierarchy was used as-is, per the
  Phase 5I.1 brief's own instruction to prefer the existing hierarchy
  "where appropriate," and no global-foundation rule needed a third
  level.

**NOT IN SCOPE** (restated from the Phase 5I.1 brief, unaffected by this
implementation): API services, API calls, routes, `AuthContext`,
authorization behavior, Letter/classification/document/notification
behavior, dashboard metrics, form validation, business rules, backend/
database code. Confirmed unmodified — see the verification results
below.

**Verification**: frontend suite run 3 consecutive times — **320/320
tests passed, 44/44 files, identical results each run**; `npm run
build` succeeded (JS bundle unchanged at 368.44 KB, confirming zero
dependency change; CSS grew from 30.74 KB to 31.73 KB minified, ~0.37 KB
gzipped, entirely from the new tokens/rules); backend `pytest tests/` —
**487 passed, unaffected**. `git status`/`git diff --stat` confirmed the
changed-file set matches exactly: `tokens.css`, `global.css`,
`StatusBadge.module.css`, `NotificationItem.module.css`,
`constants/app.js`, plus this documentation file and the five files
named in the brief's own documentation section — no route, service,
test, or backend file appears in the diff. No manual browser
verification was performed (no dev server was started this session);
this is stated explicitly rather than implied.

---

## Phase 5I.2 — App Shell & Navigation: Implementation Record

The second implementation pass — **App Shell and Navigation only**.
Verified by re-reading the actual current source before editing
(`AppShell.jsx`/`.module.css`, `Sidebar.jsx`/`.module.css`,
`Topbar.jsx`/`.module.css`, `navigationConfig.js`/`.test.js`,
`AuthContext.jsx`, `routes/index.jsx`, the current `tokens.css`/
`global.css` from Phase 5I.1) — not assumed from this review document.

**Sidebar** — visually rewritten (`layouts/Sidebar.jsx`/`.module.css`):
a small CSS-only "registry" brand mark (nested squares, no image
asset) next to the existing `APP_SHORT_NAME` constant; each nav item
gets a small monogram glyph derived from its own label (a 3-letter
abbreviation, not a single initial — a single initial collides for
this app's real nav set, e.g. Categories/Classifications both start
with "C," Departments/Designations both start with "De"; 3 letters
disambiguate every label across all three roles); an active-route
accent (a 3px left border revealed via `border-color`, so it never
shifts layout) plus `--color-highlight-bg`; a desktop collapse toggle
(icon-rail mode, `aria-expanded`, labels remain in the DOM — visually
clipped, not `display:none`, so they stay in the accessible tree and
as native `title` tooltips) with **no persistence** (deliberately —
this codebase's `localStorage` usage is scoped to auth tokens only, and
the brief explicitly said not to introduce it for a UI preference); and
a mobile-drawer mode (`role="dialog"`, `aria-modal`, a backdrop, a
generalized Tab-trap extending `ConfirmDialog`'s own 2-element trap
to however many nav links exist, Escape-to-close, closes automatically
on route change). **`navigationConfig.js` and `getNavigationForRole`
were not touched** — the same role-derived list, unchanged.

**Topbar** — a hamburger toggle added (visible by default, hidden only
at desktop width via a `min-width: 768px` query — see the jsdom finding
below for why it's phrased as the inverse of the usual pattern),
refined identity typography (name/role stacked, role rendered in
uppercase with letter-spacing using the new `--color-text-secondary`
token), and a hairline divider using `--color-border-subtle`. Identity/
role text is still exactly `user.full_name`/`user.role` from
`AuthContext` — nothing invented, nothing decoded from a token.
`NotificationBell`'s polling, API calls, and unread-count logic are
completely untouched; only its badge gained a 1.5px `--color-surface`
border (a "notched" look) — no JS, no behavior change.

**Footer** — implemented now (not deferred, per this phase's explicit
instruction that it's safe once the shell itself is being touched):
`AppShell.jsx` renders the existing `PRODUCTION_CREDIT` constant in a
`<footer>` once, below `<main>`, so it appears on every authenticated
screen regardless of role. No second copy of the text exists anywhere.

**Layout geometry**: sidebar 220px → 240px (expanded) / 64px
(collapsed); Topbar padding increased slightly (`--space-sm` →
`--space-md` vertical) for a touch more presence; `.content` gained a
`contentInner` wrapper with `max-width: 1600px` for very wide monitors
— no individual page's own layout/CSS was touched.

**A real jsdom finding, worth recording**: this project's test
environment does not evaluate `@media` width queries at all — a
`display: none` **base** rule with a `max-width` override to reveal it
never reveals it in jsdom, regardless of `window.innerWidth` (confirmed
empirically, not assumed). The mobile-only hamburger toggle is
therefore styled the other way around — visible by default, hidden via
a `min-width: 768px` query — so it degrades correctly in a real browser
(which does evaluate the query) while remaining directly testable
without any test-side viewport simulation or `hidden: true` query
workarounds. Documented here so a future phase doesn't reintroduce the
untestable pattern elsewhere in the shell.

**Motion**: sidebar-collapse animates `width`; the mobile drawer
animates `transform` (slide) with a `visibility` flip delayed only on
close (so its links leave the Tab order the instant it's fully hidden,
not before); the backdrop has no separate fade (a plain
`rgba(0,0,0,0.45)` scrim, matching `ConfirmDialog`'s own existing,
unanimated backdrop) — all using the Phase 5I.1 motion tokens
(`--motion-normal`, `--motion-ease`), never a new duration invented for
this phase. The Phase 5I.1 reduced-motion foundation was extended by
one line (`transition-delay: 0s !important`) — needed once this phase
introduced this codebase's first delay-based transition (the drawer's
close-delayed `visibility`), otherwise a delayed property could still
lag behind an instantly-completed transition under reduced motion.

**Accessibility**: `aria-current="page"` on the active nav link comes
for free from React Router's own `NavLink` (default behavior, not
custom code); the collapse toggle exposes `aria-expanded`; the mobile
toggle exposes `aria-expanded` and a state-appropriate `aria-label`;
the drawer is a labelled `role="dialog"` with a real focus trap and
Escape handling, generalized from `ConfirmDialog`'s own proven pattern;
background content is never reachable from the keyboard while the
drawer is open (the trap prevents Tab from leaving it) and the backdrop
intercepts pointer clicks — **not independently re-verified with a
screen reader or a real browser** this session; this is a code-level,
tested implementation of the pattern, not a claimed WCAG audit.

**System status**: not added — restated from the Phase 5I review's own
recommendation against it; no honest, backend-confirmed signal exists
for this frontend to render as a "system status," and inventing one
would be exactly the fake-security theatrics the brief prohibits.

**Not done this phase** (deferred, per the brief's own closing list):
core UI primitive redesign (tables/forms/dialogs consolidation), the
dashboard, Letter pages, administration pages, documents, the
notification panel itself, authentication pages, the boot screen, and
the loading glyph.

**Verification**: 46 test files / 335 tests (320 + 15 new — 9 in
`Sidebar.test.jsx`, 6 in `AppShell.test.jsx`), run 3 consecutive times
with identical results; `npm run build` succeeded (JS bundle grew from
368.44 KB to 371.47 KB — the new shell JSX itself, zero new
dependency); backend `pytest tests/` — 487 passed, unaffected. Grepped
the entire diff for `jwt`/`decode`/`localStorage`/role-string
comparisons/department-id comparisons/`recipient_user_id`/storage-path
patterns inside `src/layouts/` — zero matches.

---

## Phase 5I.3 — Core UI Primitives & Interaction System: Implementation Record

The third implementation pass — **reusable interaction primitives
only**, deliberately excluding every page-category the brief reserves
for its own later phase (Dashboard, Letter pages, Administration
pages, Documents, the Notification panel itself, Authentication).
Verified by re-reading `tokens.css`/`global.css` and every primitive
named in the brief (`LoadingState`, `ErrorState`, `EmptyState`,
`StatusBadge`, `Pagination`, `ConfirmDialog`, `AdminTransferDialog`,
`DepartmentSelector`, plus every form/table CSS Module) directly before
editing — not assumed from this document.

**A scope correction made mid-phase, recorded honestly**: an initial
edit touched `pages/LetterFormPage.module.css`'s button/input classes.
On review this was a genuine overreach — that file is unambiguously a
Letter-page file, and "Letter page redesign" is explicitly out of scope
for this phase — so it was reverted (`git checkout --`) before any
other work continued. The line actually drawn: files in `src/components/`
(and `pages/AdminPages.module.css`, which already serves seven
different resources and was already this codebase's own "shared
admin-page" file before this phase) were in scope; single-purpose page
files named in the brief's closing prohibition list
(`LetterFormPage`/`LetterListPage`/`LetterDetailPage`, `AuthPages`,
`DashboardPage`, `NotificationsPage`) were not touched.

**New file**: `styles/primitives.module.css` — shared `.btn`/
`.btnPrimary`/`.btnSecondary`/`.btnGhost`/`.btnDanger`, `.tableScroller`/
`.table`/`.tablePrimaryCell`/`.tableActionsCell`, and `.dialogBackdrop`/
`.dialogPanel`/`.dialogActions` (with entrance-motion keyframes). Every
consuming file reaches these via CSS Modules' native `composes:`
mechanism — no new component, no new prop-driven abstraction; every
page keeps its exact existing `<button>`/`<table>`/`<div role="dialog">`
markup.

**A real CSS Modules constraint, worth recording**: `composes` can only
target a simple class already applied directly to an element — it
cannot reach a descendant selector like `.field input` or
`.actionsCell button`. Since most of this codebase's form-control
duplication is written exactly that way, the genuinely global fix
(reaching every existing form with zero markup change anywhere) is a
**global element-type rule in `global.css`** instead — `input`/
`select`/`textarea` now share one base treatment there, and the
per-file duplicate blocks in `AdminPages.module.css` were deleted
outright (not left as harmless dead CSS). Descendant-selector button
cases that couldn't be composed (`DataTable.module.css`'s
`.actionsCell button, .actionsCell a`; `Pagination.module.css`'s
`.controls button`) were left as small, manually-matched CSS rather
than restructuring table/pagination JSX to add new classes — a bounded,
documented exception, not an oversight.

**Buttons**: one shared system (primary/secondary/ghost/danger),
consistent 2.25rem height, radius, typography, hover, a small
`translateY(1px)` press feedback on `:active`, and disabled state —
composed into `AdminPages.module.css` (`.submit`/`.cancel`/
`.createLink`), `LetterFilters.module.css` (`.apply`/`.clear`),
`DocumentUploadForm.module.css` (`.submit`), `ConfirmDialog.module.css`/
`ArchiveConfirmDialog.module.css` (`.cancel`/`.confirm`/
`.confirmCaution`), `Topbar.module.css` (`.logout`), and
`NotificationItem.module.css` (`.markRead`). `AdminTransferDialog`
inherits automatically — it already imports `ConfirmDialog.module.css`
directly, so it needed no edit of its own. No `transition: all`
anywhere; every transition lists explicit properties.

**Form controls**: consolidated in `global.css` (see the constraint
above) — one shared input/select/textarea treatment (border, radius,
background, disabled, `aria-invalid`) across every existing form with
zero markup changes; native `accent-color: var(--color-primary)` themes
every checkbox/radio (Classification's `restricts_access` included)
without replacing the native control — it stays fully keyboard-operable
and its checked state is drawn by the browser itself, never
color-only. `DepartmentSelector` needed no change at all — it has no
CSS module of its own and inherits this automatically through whichever
page renders it.

**Validation states**: unchanged mechanism everywhere — `aria-invalid`/
`aria-describedby`/`role="alert"` are exactly as before; only the
`aria-invalid='true']` border-color rule moved from five duplicate
per-file declarations to the one global rule.

**Select/dropdown UX**: no custom JS dropdown was introduced anywhere —
every `<select>` (Department/Category/Classification/Designation/
status filters) is still a plain native element, now visually
consistent purely because they all inherit the same global base rule.

**Tables**: `DataTable.module.css` (Departments/Admins/Users/
Authorizations/Categories/Classifications/Designations) and
`LetterTable.module.css` both now compose `tableScroller`/`table`/
`tablePrimaryCell` from the shared primitives — the header now reads
as uppercase, letter-spaced metadata text (`--color-text-secondary`),
distinct from the strong primary-cell text and quiet action buttons
below it. No column, sort, filter, or pagination logic changed.

**StatusBadge**: a small `aria-hidden` shape (`.indicator`) added
before the text — a circle for positive/neutral, a rotated-square
diamond for warning, a plain square for negative — drawn with
`currentColor`, so it always matches each tone's existing text color.
The visible text remains the real signal; the shape is purely
supplementary. No status value, label, or tone mapping changed — the
existing `TONE_BY_VALUE` map in `StatusBadge.jsx` is untouched. New
test file `StatusBadge.test.jsx` (11 tests, none existed before) covers
every mapped status value rendering its label as real text, the
fallback-to-raw-value case, the unknown-value case, and that the
indicator is `aria-hidden` and never the accessible content.

**Pagination**: spacing/state polish only (consistent button height,
an explicit transition list, unchanged disabled/current-page styling)
— page-number math, query parameters, and the API request shape are
completely untouched.

**Dialogs**: `ConfirmDialog`/`ArchiveConfirmDialog` now compose the
same backdrop/panel/action-row classes instead of duplicating them —
confirmed as the one genuine remaining dialog duplication from the
Phase 5I review (`AdminTransferDialog` was already sharing
`ConfirmDialog.module.css` directly, not a separate copy, corrected
understanding from this session's own fresh read). A short opacity +
translate/scale entrance animation was added to both the backdrop and
panel — automatic on mount (a CSS `animation`, not a `transition`,
since there is no prior DOM state to transition from) — fully covered
by the existing global `prefers-reduced-motion` safety net with no
per-dialog override needed. Focus trap, Escape, and backdrop-click
behavior are byte-for-byte unchanged; `ConfirmDialog.test.jsx`'s
existing `container.firstChild` backdrop-click assertion still passes
unmodified, since the DOM structure (backdrop wrapping panel) never
changed — only the CSS class contents did.

**Loading/Empty/Error states**: `LoadingState` was audited and left
unchanged — it was already token-driven, already the one universal
spinner+text pattern used everywhere, and already correctly
`prefers-reduced-motion`-gated; no genuine improvement was identified
that wouldn't be decoration for its own sake. `EmptyState` gained a
small, `aria-hidden`, CSS-only "document with lines" glyph (a
restrained registry motif, not an illustration) — new test file
`EmptyState.test.jsx` (3 tests) confirms the message text and the
default fallback still render, and that the glyph is decorative only.
`ErrorState`'s retry button now composes the shared `.btn` base while
keeping its own danger-outline coloring; the 401/403/404/409/422/500/
network distinctions it renders are entirely message-text it receives
as a prop — nothing here remaps or reinterprets a status code.

**Notification row states**: `NotificationItem`'s unread state now
carries a left accent bar (`--color-primary`) in addition to its
existing background tint and bolder message weight — three
independent signals, never color alone. A plain hover/focus-within
background was added for read rows (there was none before). Polling,
mark-read behavior, and API calls are completely untouched — confirmed
by `NotificationItem.test.jsx`'s and `NotificationBell.test.jsx`'s
unmodified passing assertions.

**Document upload UI**: comment-only clarification plus the shared
button class on `.submit`; **no drag-and-drop was added** — a
deliberate judgment call, not an oversight, since it would require new
`onDrop`/`onDragOver` event wiring and the existing click-to-browse
`<input>` already satisfies the accepted-types/size/upload contract
without introducing any behavior risk this phase didn't need to take.

**Filter/search controls**: `LetterFilters.module.css`'s Apply/Clear
buttons now compose the shared primitives; its `.field input`/
`.field select` duplicate block was deleted in favor of the same global
form-control base — deliberately without adding `width: 100%`, since
its existing CSS-grid layout never opted into one and already renders
correctly without it. No new search capability, no global search box,
no change to the URL-synced filter state.

**Futuristic visual language**: the accent-bar technique introduced for
Sidebar's active route (Phase 5I.2) is now reused for
`NotificationItem`'s unread indicator — the same "precision line"
language in a second place, not a new motif; the uppercase
letter-spaced table header continues the same typographic character
`Topbar`'s role text already established; the badge's shape layer and
`EmptyState`'s glyph are the only new CSS-drawn geometric elements — no
gradient, blur, or glow was added anywhere.

**Motion**: dialog entrance uses `--motion-fast` (backdrop) /
`--motion-normal` (panel); button press uses `--motion-instant`; table
row hover and notification-item hover/unread transitions use
`--motion-instant`. No new duration value was invented — every motion
in this phase reuses the Phase 5I.1 token scale exactly.

**Reduced motion**: every new animation/transition in this phase is
either a `transition-property` (already covered by the existing global
`transition-duration: 0.01ms !important` rule) or a CSS `animation`
(already covered by the existing global `animation-duration: 0.01ms
!important` rule) — zero new `prefers-reduced-motion` overrides were
needed anywhere, confirming the Phase 5I.1 foundation does exactly what
it was built for.

**Accessibility**: no ARIA attribute, label, landmark, or keyboard
behavior was removed anywhere; every shape/glyph addition is
`aria-hidden`; native form controls (`<select>`, `<input
type="checkbox">`) were never replaced with a custom widget — not
independently re-verified with a screen reader or a formal audit tool
this session.

**Verification**: 48 test files / 349 tests (335 + 14 new —
`StatusBadge.test.jsx` and `EmptyState.test.jsx`, neither of which
existed before this phase), run 3 consecutive times with identical
results; `npm run build` succeeded (JS grew 371.47 KB → 372.51 KB from
the two new presentational spans; CSS actually *shrank*, 35.57 KB →
34.61 KB minified, from the deleted duplicate blocks net of the new
shared primitives file); backend `pytest tests/` — 487 passed,
unaffected. Grepped the entire diff's touched files for
`jwt`/`decode`/`localStorage`/role-string comparisons/department-id
comparisons/`recipient_user_id`/storage-path/signed-URL patterns — the
only two matches were pre-existing, untouched comments in
`DocumentList.jsx`/`.test.jsx` explicitly documenting that a storage
path is *never* exposed.

**Not done this phase** (deferred, per the brief's own closing list):
Dashboard, Letter-page, Administration-page, Document-page,
Notification-panel, and Authentication-page redesign; the boot screen;
the registry loading glyph; final visual polish. `LoadingState` and
`DepartmentSelector` were audited and deliberately left unchanged
(already correct, or already inheriting every improvement with zero
edits of their own).

---

## Phase 5I.4A — Dashboard Visual Transformation: Implementation Record

The first screen-level visual transformation — `/app/dashboard` only.
Verified by re-reading `DashboardPage.jsx`/`.module.css`,
`SummaryCard.jsx`/`.module.css`, `RecentLetters.jsx`/`.module.css`,
`QuickActions.jsx`/`.module.css`, and all four relevant test files
directly before editing.

**Recomposition**: the page is now four visual zones — a header
(eyebrow + `h1` + a thin accent line + a subtitle), the metric grid, and
a two-column zone (Recent Letters 2fr / Quick Actions 1fr at desktop,
stacking to one column at the existing 1024px breakpoint) — not a
restyle of four independent cards. Every existing `useState`/
`useCallback`/`useEffect`/service call and every `role === '...'`
conditional in `DashboardPage.jsx` is byte-for-byte unchanged; only the
JSX returned at the bottom of the component changed (confirmed by
reading the diff directly — the fetch logic and role branches appear
nowhere in it).

**Header**: an eyebrow ("Registry Overview"), the unchanged `<h1>Dashboard</h1>`,
a small `aria-hidden` 24×3px accent line, and a subtitle ("Current
registry activity and quick actions for your role.") — every word here
describes real, existing page content; nothing claims security,
encryption, monitoring, or uptime. Grepped the new/changed Dashboard
files for `secure|encrypt|live monitoring|all systems|operational\b` —
the only two matches are pre-existing Phase 5F *code comments*
("Dashboard & Operational Overview," "operational-count card," both
naming the feature, not user-visible), confirmed via `git diff` to be
unrelated to this phase's changes. A new test asserts the rendered page
text never matches `/system secure|all systems operational|encrypted|
live monitoring/i`.

**Summary cards**: unchanged metrics, unchanged `label`/`value` props,
unchanged role-based card set — every card now gets one consistent
treatment (never a dozen bespoke styles): a `--color-primary` left
accent bar, an `aria-hidden` corner-bracket mark, uppercase
letter-spaced label text, `font-variant-numeric: tabular-nums` on the
value, and a restrained hover/focus lift (`--shadow-sm` +
`translateY(-1px)`, `--motion-fast`) using the existing
`--color-surface-elevated` token from Phase 5I.1 for the first time.
No chart, percentage, delta, or historical comparison was added — a
number without historical data is still just a number.

**Recent Letters**: reuses the exact accent-bar-on-hover language
`Sidebar`/`NotificationItem` already established (not a third variant),
bolder tabular-numeral reference numbers, and a real (not fabricated)
"`N` shown" count next to the heading — computed from
`recentLetters.items.length`, rendered only once loading/error have
resolved (never a misleading "0 shown" mid-fetch). The Letter link's
`to`/`href` and the underlying `letterService.list` request are
unchanged.

**Quick Actions**: the same three role-scoped actions, same routes,
now laid out as one column of full-width tiles (fitting the narrower
action column) with a decorative `aria-hidden` arrow that shifts on
hover/focus — the arrow is excluded from each link's accessible name by
construction, verified by a new test asserting
`toHaveAccessibleName('Record a Letter')`. The redundant local
`:focus-visible` override (from Phase 5F, before the global one
existed) was removed in favor of the existing global focus treatment —
one less duplicate rule, identical visible outcome.

**Motion**: one subtle, single entrance fade+translateY on the whole
page (`.root`, `--motion-normal`) — not a per-card stagger, keeping the
page reading as one composition rather than "a bunch of effects."
Card/row/tile hover transitions all reuse `--motion-instant`/
`--motion-fast` — no new duration was invented. Fully covered by the
existing global `prefers-reduced-motion` safety net (an `animation`
and several `transition`s, both already zeroed there) — no per-component
override was needed.

**Accessibility**: `<h1>Dashboard</h1>` and both `<h2>` headings keep
their exact original text (verified by the existing, unmodified
`getByRole('heading', ...)` test); every new decorative element
(corner bracket, header accent line, quick-action arrow) is
`aria-hidden`; no color-only status meaning was introduced (StatusBadge's
Phase 5I.3 shape layer already covers Letter status here). Not
independently re-verified with a screen reader or a formal audit tool.

**Security boundary**: grepped the diff for `jwt`/`decode`/
`localStorage`/`recipient_user_id`/storage-path/signed-URL patterns —
zero matches. The four `role === '...'` conditionals that do exist in
`DashboardPage.jsx` are all pre-existing (confirmed via `git diff` —
none appears in this phase's changed lines); this phase added no new
role branch, and every role's card/action set renders exactly as
before.

**Verification**: 48 test files / 354 tests (349 + 5 new — 2 in
`SummaryCard.test.jsx`, 1 in `QuickActions.test.jsx`, 3 in
`DashboardPage.test.jsx`), run 3 consecutive times with identical
results, including all pre-existing assertions (wrong-role requests
never fire, one widget's failure never blocks another, "Unavailable"
never a fabricated zero, exact Letter-link hrefs) passing completely
unmodified; `npm run build` succeeded (JS 372.51 KB → 373.65 KB, CSS
34.61 KB → 37.18 KB — new decorative CSS only, zero new dependency);
backend `pytest tests/` — 487 passed, unaffected.

**Not done this phase**: no chart, trend, percentage, or historical
comparison of any kind; no new metric, action, or route; no system-status
indicator (still no honest signal to back one — restated from Phase 5I's
own recommendation); Letter pages, Administration pages, Documents, the
Notification panel, Authentication pages, the boot screen, and the
loading glyph all remain untouched, reserved for their own later
phases.

---

## Phase 5I.4B — Letter Registry Visual Transformation: Implementation Record

The second screen-level visual transformation — the Letter registry
family only (`LetterListPage`, `LetterFormPage`, `LetterDetailPage`,
`LetterFilters`, `LetterTable`). Verified by re-reading every one of
these files, their `.module.css`, and all four relevant test files
(`LetterListPage.test.jsx`, `LetterFormPage.test.jsx`,
`LetterDetailPage.test.jsx`, `LetterTable.test.jsx`) directly before
editing.

**Registry header** (`LetterListPage`): an eyebrow ("Letter Registry")
+ the unchanged conditional title (`Letters` / `Letters — all
departments`) + an `aria-hidden` accent line, and the existing
`{data.total} total` count restyled as a bordered chip (**the exact
same text, unchanged** — a test asserts `getByText('1 total')`
verbatim, so the count was restyled via CSS only, never reformatted
into a "leading-zero" or "N RECORDS" display, which would have altered
the string and broken that test). "Record New Letter" still only
renders for `canCreate` roles — unchanged.

**Filter area** (`LetterFilters`): recomposed into a "Registry Search"
console — the same 13 fields (all present, same `name`/`id`/label
text), now grouped into four `<fieldset>`s (Correspondence; Sender &
source; Classification, rendered only when reference data exists,
matching the original conditional exactly; Received date range) with
uppercase technical legends. One new, purely decorative prop,
`activeCount` — computed by `LetterListPage` from the exact same
`activeFilters` object it already builds (`Object.keys(activeFilters).length`),
rendered as an "N active filters" badge; not a new filter, not a second
source of truth. Apply/Clear/draft-state logic is byte-for-byte
unchanged (confirmed via `git diff` — `handleChange`/`handleSubmit`/
`handleClear` appear nowhere in the diff).

**Registry table** (`LetterTable`): reuses the Phase 5I.3 shared table
primitives; this phase adds one row-level left accent bar on hover
(the same technique `RecentLetters`/`NotificationItem` already use),
scoped to this file only so the shared `DataTable`-based admin tables
are unaffected, plus `font-variant-numeric: tabular-nums` on the
reference-number cell. No column, sort, filter, link, or
classified-record behavior changed.

**Create/Edit Letter** (`LetterFormPage`): the same header treatment
(eyebrow + accent line) added above the form; the four existing
fieldsets (Reference & subject / Source / Sender / Additional details)
keep their exact grouping and legend text, now styled as uppercase
technical labels; `.submit`/`.cancel` now compose the shared button
primitives (deferred from Phase 5I.3, which explicitly excluded Letter
pages — now correctly in scope for this dedicated phase); the
now-redundant `.field input`/`.field select`/`.field textarea` block
was deleted in favor of the Phase 5I.3 global form-control base. Every
field, id, validation rule, and payload is unchanged — the existing
Source Department/Designation dropdowns, their auto-fill behavior, and
the SYSTEM_ADMIN-only Category/Classification selectors on edit all
work exactly as before (confirmed by all 20 `LetterFormPage.test.jsx`
tests passing unmodified).

**Letter detail — record dossier** (`LetterDetailPage`): the flat
11-field grid is now four labeled sections (Correspondence; Source;
Sender; Additional details), each a bordered card with an
accent-barred, uppercase section heading — the same fields, same
`Field` helper, same "—" placeholder convention for an empty value,
same `<dl>`/`<dt>`/`<dd>` semantics throughout. **Category/Classification
were deliberately NOT added to this dossier**, despite the brief's own
§10 suggestion — `LetterDetailPage` has no existing category/
classification service call (unlike `LetterListPage`/`LetterFormPage`,
which already conditionally load these for SYSTEM_ADMIN); adding one
here would be a new fetch and a new role branch, not a visual change,
and so falls outside this phase's "presentation only" boundary. This is
a recorded, deliberate omission, not an oversight. The header, Edit/
Archive actions (now composing the shared button primitives), the
Documents section, and the 404/error/archive-confirmation behavior are
completely unchanged.

**A jsdom scope note, not a real regression**: the very first test run
this phase reported `document is not defined`/`mockResolvedValue is
not a function` across all four Letter test files — a working-directory
mistake (`npx vitest` was invoked from the repo root, not `frontend/`),
not a code defect; re-running from the correct directory passed all 48
tests immediately, with zero code changes in between.

**Motion**: the same accent-bar-on-hover technique already established
in Phase 5I.4A, applied here to `LetterTable` rows — `--motion-instant`,
no new duration. No dialog/panel-entrance motion was added (Archive's
`ConfirmDialog`-based dialog already animates via the Phase 5I.3
`dialogPanelIn` keyframes). Fully covered by the existing global
reduced-motion safety net.

**Accessibility**: every `Field`/`fieldset`/`legend`/`label` pairing,
`aria-invalid`/`aria-describedby`, and the archive dialog's focus trap/
Escape handling are unchanged; the new dossier `<h2>`s and filter-group
`<legend>`s are real, meaningful headings (not decorative); every new
accent bar/eyebrow-line is `aria-hidden`. Not independently re-verified
with a screen reader or a formal audit tool.

**Security boundary**: grepped every changed file for
`jwt`/`decode`/`localStorage`/department-id-comparison/
`recipient_user_id`/storage-path/signed-URL patterns — zero matches.
Department isolation, classified-record 404-collapsing, and the
SYSTEM_ADMIN-only reference-data gating in `LetterListPage`/
`LetterFormPage` are all unchanged (confirmed via `git diff` — none of
the role-conditional branches appear in the diff).

**Verification**: 48 test files / 354 tests (unchanged from Phase
5I.4A — no test needed to change, since no existing behavior changed),
run 3 consecutive times with identical results, including all 48
pre-existing Letter-registry-specific assertions (URL sync, sort
toggling, filter apply/clear, role-specific rendering, Source
Department/Designation auto-fill, 422/409/403 handling, document
integration, archive confirmation wording) passing completely
unmodified; `npm run build` succeeded (JS 373.65 KB → 376.80 KB, CSS
37.18 KB → 38.44 KB — decorative CSS/JSX only, zero new dependency);
backend `pytest tests/` — 487 passed, unaffected.

**Not done this phase**: Category/Classification display on the detail
page (deliberately deferred, above); Administration pages, Documents,
the Notification panel, Authentication pages, the boot screen, and the
loading glyph all remain untouched, reserved for their own later
phases.

---

## Phase 5I.4C — Administration Visual Transformation: Implementation Record

The third screen-level visual transformation — the entire
administration workspace: Departments, Administrators, Users,
Authorizations, and Master Data (Designations/Categories/
Classifications), ~28 files total. Verified by re-reading every list/
create/detail page, `DepartmentTable`/`AdminTable`/`UserTable`/
`AuthorizationTable`/`DesignationTable`, `DepartmentForm`,
`AdminTransferDialog`, and the shared `AdminPages.module.css`/
`DataTable.module.css` directly before editing.

**A key structural finding, exploited deliberately**: nearly every one
of these ~28 pages already shares exactly two files —
`pages/AdminPages.module.css` (list/create/detail layout, used by all
seven resources) and `components/DataTable.module.css` (every table
except `LetterTable`). This meant the console-wide visual language
could be established almost entirely in **two shared files**, cascading
to all seven resources automatically, rather than needing per-resource
CSS work.

**Shared header language** (`AdminPages.module.css`): the same eyebrow/
accent-line/chip-count pattern already established for the Dashboard
and Letter registry, added once to the shared file. Each of the 17
list/create/detail pages then got a small, mechanical JSX insertion —
a resource-specific eyebrow string (e.g. "Department Administration,"
"Administrator Management," "Classification Master Data") plus the
existing heading wrapped in `.titleRow` with an `aria-hidden` accent
mark. The existing `{data.total} total` counts keep their exact text
(restyled as a chip via CSS only). `.headerActions button`/
`.actionsPanel button`/`.actionsPanel .primary` were upgraded to match
the shared button system's height/typography/transition values as
plain CSS (not `composes` — these are descendant selectors on bare
`<button>` elements with no class of their own, the same bounded
exception already established for `Pagination`/`DataTable` in Phase
5I.3) — zero JSX changes needed for any Activate/Deactivate/Approve/
Reactivate/Transfer/Refresh button anywhere.

**One-family tables** (`DataTable.module.css`): one row-level left
accent bar on hover, added once to the file every admin table (Department/
Admin/User/Authorization/Designation/Category/Classification) already
composes from — all seven now share the exact same row-hover language
in a single edit, deliberately distinct from `LetterTable.module.css`'s
own separately-scoped treatment (the registry's flagship table, kept
visually distinct on purpose since Phase 5I.4B).

**Admin Transfer — the one genuine restructuring**: `AdminTransferDialog`
gained real visual separation between "current department" (a bordered
info block), the department field, and the consequences paragraph
(reordered after the field, restyled quieter/muted). **The consequences
text is byte-for-byte unchanged** — `AdminDetailPage.test.jsx` asserts
the exact phrase "does not move or reassign any historical record"
verbatim, and this session confirmed that assertion still passes
unmodified. No wording, business semantics, or confirmation behavior
changed — only which visual container each paragraph sits in and their
order.

**Master data** (Designations/Categories/Classifications): inherited
the same header/table treatment as Departments/Admins/Users with zero
additional resource-specific work, exactly demonstrating the brief's
own "distinct from user/account administration while still sharing the
same system identity" goal — the identity comes from the shared files,
the distinction comes from each resource's own eyebrow text and
content. `restricts_access`, no-delete, and Designation's
list+create+lifecycle-combined-page pattern are all completely
unchanged.

**Status visualization**: unchanged — every table/detail page still
uses the Phase 5I.3 `StatusBadge` shape-per-tone system as-is; no new
status value was introduced anywhere across all seven resources.

**Forms**: `DepartmentForm`, the inline Admin/User authorize forms, and
`CategoryForm`/`ClassificationForm` were **not restructured** — each is
already 1-2 fields, small enough that fieldset grouping (used for the
Letter form and filters, which have far more fields) would be
ceremony, not clarity, for a form this size. This is a deliberate,
proportionate choice, not an oversight.

**Confirmation dialogs**: `ConfirmDialog`/`ArchiveConfirmDialog`'s
Phase 5I.3 consolidation and entrance motion already cover every
Deactivate/Approve/Revoke dialog across all seven resources — this
phase added no new dialog mechanics, only `AdminTransferDialog`'s
internal visual grouping (above).

**Empty/Error/Loading states**: unchanged mechanism, messages, retry
behavior, and 404 collapsing (e.g. Admin-detail's System-Admin
protection, User-detail's four-cases-collapsed-to-one 404) — untouched.

**Motion**: the accent-bar-on-hover technique now covers every admin
table via one shared-file edit; dialog entrance motion already existed
from Phase 5I.3. No new duration was invented.

**Accessibility**: every label/heading/`aria-invalid`/
`aria-describedby`/dialog focus-trap/Escape/table-semantics is
unchanged; every new eyebrow/accent-mark is either real text (eyebrows)
or `aria-hidden` (accent marks) — never color-only meaning.

**Security boundary**: grepped every changed file — zero matches for
`jwt`/`decode`/`localStorage`/role or department-id comparisons/
`recipient_user_id`/storage-path/signed-URL patterns anywhere across
the 17 pages, `AdminTransferDialog`, and the two shared CSS files.

**Verification**: 48 test files / 354 tests (unchanged — no test needed
to change), run 3 consecutive times with identical results; a
dedicated pass of all 17 Administration test files (107 tests) also
run and confirmed green, including the Admin Transfer flow's exact
consequences-text assertion, System-Admin-protection 404 phrasing, the
403-department-inactive test, and every activate/deactivate/approve/
revoke confirmation test; `npm run build` succeeded (JS 376.80 KB →
380.11 KB, CSS 38.44 KB → 40.53 KB — decorative CSS/JSX only, zero new
dependency); backend `pytest tests/` — 487 passed, unaffected.

**Not done this phase**: Documents, the Notification panel,
Authentication pages, the boot screen, and the loading glyph remain
untouched, reserved for their own later phases.

## Phase 5I.4D — Documents & Notifications Visual Transformation: Implementation Record

The fourth screen-level visual transformation — Documents (within the
Letter dossier) and Notifications (Topbar bell, panel, and the full
`/app/notifications` page), 5 component/page files plus their CSS
Modules. Verified by re-reading `DocumentList.jsx`/`.test.jsx`,
`DocumentUploadForm.jsx`/`.module.css`/`.test.jsx`,
`LetterDetailPage.jsx`/`.module.css`, `NotificationBell.jsx`/
`.module.css`, `NotificationPanel.jsx`/`.module.css`/`.test.jsx`,
`NotificationItem.jsx`/`.module.css`, and
`NotificationsPage.jsx`/`.module.css`/`.test.jsx` directly before
editing.

**A key structural finding, exploited deliberately**: `DocumentList.jsx`
already imports `styles` from the shared `DataTable.module.css`
directly (it has no CSS Module of its own) — meaning it already
inherited the Phase 5I.4C "one family" row-hover accent bar for free.
No `DocumentList`-specific CSS was needed to make the document table
match the rest of the registry's table language.

**Documents — a real, non-fabricated attachment count**:
`LetterDetailPage`'s "Documents" heading gained a small chip-style
count (`{documents.length} attachment(s)`) computed from the already-
loaded `documents` array, never a separate API call or invented
metric — added via a new `.sectionHeaderRow`/`.docCount` pair in
`LetterDetailPage.module.css`. The heading text itself, the table, and
`DocumentList`'s row content (`filename`, size, MIME type, Download
button) are byte-for-byte unchanged — `DocumentList.test.jsx`'s
`getByRole('button', { name: 'Download scan.pdf' })` and file-size/
type assertions pass unmodified.

**Upload experience**: `DocumentUploadForm`'s label gained a small
`aria-hidden` "document" glyph (a CSS-only folded-corner rectangle)
before the existing "Upload document" text — the accessible name is
unaffected since the glyph contributes no text node, confirmed against
`getByLabelText(/upload document/i)`. The in-flight progress message
(unchanged text: `Uploading… ${progress}%` / `'Uploading…'`) now sits
above a thin fill bar, but **only when a real percentage is already
known** — the indeterminate case stays text-only, exactly as before.
The fill width is driven directly by the existing `progress` state on
every render; there is no independent timer, fake progress, or CSS
animation standing in for network state. A drag/drop affordance was
considered and deliberately **not** added — the existing file input is
already a single click target with clear validation feedback, and a
drop zone would add a second interaction path without removing any
friction the brief identified.

**Notification Bell**: audited and found already at the target bar
from Phase 5I.2/5I.3 (2.25rem square button, contrasting badge
border) — **left completely unmodified** this phase, an honest
no-change finding rather than an oversight.

**Notification Panel — "Operational Signals"**: gained an eyebrow
label ("Operational Signals") above the unchanged "Notifications"
heading, and a small CSS-only triangle (`::before`, `aria-hidden`)
visually connecting the panel to the Topbar bell it opened from. The
panel keeps its Phase 5E "lighter disclosure" design exactly — no
backdrop, no Tab-trap, `Escape` still returns focus via the existing
`onClose` — and its entrance is a short opacity/translate fade using
`--motion-fast`/`--motion-ease`, already covered by the global
`prefers-reduced-motion` safety net with no per-component override.
`notificationService.list` is still called with exactly
`{ page: 1, page_size: 10 }`; mark-read stays explicit-button-only.

**Notification rows — a fourth, still-static signal**: `NotificationItem`
gained one more unread indicator — a small filled dot (`aria-hidden`,
non-animated) — alongside the existing Phase 5I.3 accent bar,
highlight background, and bolder message weight. It is never the sole
signal: the existing `sr-only` "Unread notification:" / "Read
notification:" prefix still carries the state as text first. No
blinking, pulsing, or continuous animation was added, per the brief's
explicit prohibition.

**Notification Page**: `/app/notifications` gained the same eyebrow/
accent-line/chip-count header language used everywhere else in the
application ("Operational Signals" eyebrow, `.titleRow` with an
`aria-hidden` accent mark, the existing `{data.total} total` text
restyled as a chip) plus `Refresh`/`Mark all read` restyled onto the
shared `btn`/`btnSecondary` primitives. No unread filter, search,
category, or bulk control was added — none of those exist in the
backend contract. `notificationService.list` is still called with
exactly `{ page: 1 }` (no `is_read` param, confirmed via
`NotificationsPage.test.jsx`); pagination, Letter navigation, and the
generic 404 behavior are all unchanged.

**Empty/Error states**: unchanged mechanism and messages throughout —
`EmptyState`'s "No notifications yet." and Document's generic
"Document not found." (no classification/permission text) both
untouched.

**Motion**: reused `--motion-instant`/`--motion-fast`/`--motion-ease`
exactly (upload progress-fill transition, panel entrance fade,
`viewAll` hover) — no new duration invented; the global
`prefers-reduced-motion` rule covers every new transition/animation
automatically.

**Accessibility**: every label/button/link/ARIA role is unchanged or
additive-only (`aria-hidden` on all new decorative glyphs — the
upload-form icon, the progress track, the panel connector triangle,
the unread dot, the header accent marks); unread state is still
communicated via text (`sr-only` prefix) first, never color/shape
alone.

**Security boundary**: grepped every changed file
(`LetterDetailPage.jsx`/`.module.css`, `DocumentUploadForm.jsx`/
`.module.css`, `NotificationsPage.jsx`/`.module.css`,
`NotificationPanel.jsx`/`.module.css`, `NotificationItem.jsx`/
`.module.css`) for `jwt`/`decode(`/`localStorage`/role or
department-id comparisons/`recipient_user_id`/storage-path/signed-
or public-URL patterns — zero matches. Document downloads still use
the existing authenticated blob-fetch flow; no storage path or signed
URL is exposed anywhere in the row markup.

**Verification**: the 7 directly-relevant test files (63 tests —
`LetterDetailPage`, `DocumentList`, `DocumentUploadForm`,
`NotificationBell`, `NotificationPanel`, `NotificationItem`,
`NotificationsPage`) confirmed green first; then the full suite (48
files / 354 tests, unchanged — no test needed to change) run 3
consecutive times with identical results; `npm run build` succeeded
(197 modules, JS 381.92 KB, CSS 42.86 KB — decorative CSS/JSX only,
zero new dependency); backend `pytest tests/` — 487 passed,
unaffected. Manual browser verification was **not performed** — no dev
server was started this phase.

**Not done this phase**: Authentication pages, the boot screen, and the
loading glyph remain untouched, reserved for their own later phases. A
per-row document-type geometric marker (one of the brief's own
"possible ideas") was considered and deliberately omitted — the
existing bold filename, explicit MIME-type column, and clear Download
button already give each row sufficient hierarchy without it.

## Phase 5I.4E — Authentication Visual Transformation: Implementation Record

The fifth screen-level visual transformation — the unauthenticated
entrance experience (`LoginPage`, `SignupPage`, and the two account-
state notices they render), 6 files total. Verified by re-reading
`LoginPage.jsx`/`.test.jsx`, `SignupPage.jsx`/`.test.jsx`,
`AuthPages.module.css`, `PendingApprovalNotice.jsx`/
`DeactivatedAccountNotice.jsx`/`AccountStateNotice.module.css`,
`AuthContext.jsx`, `authService.js`, `RootRedirect.jsx`,
`routes/index.jsx`, `Sidebar.jsx`/`.module.css`, `tokens.css`,
`global.css`, and `constants/app.js` directly before editing. Search
of `routes/index.jsx` confirmed exactly two unauthenticated routes
exist — `/login` and `/signup` — with `RootRedirect`/`ProtectedRoute`
only ever deciding *between* them and `/app`, never rendering
authentication UI of their own.

**A key structural finding, exploited deliberately**: the existing
`LoginPage.jsx`/`SignupPage.jsx` composition was confirmed to be
exactly the generic "white card + email + password + blue button" the
brief calls out — a single shared `AuthPages.module.css` with no brand
identity, and a hand-styled submit button never composed from the
Phase 5I.3 shared primitives (Authentication pages were explicitly
named as deferred in that phase's own scope note). This phase closes
that gap without touching either page's actual form logic.

**Authentication identity**: a static brand mark — the exact
nested-square geometry (a bordered rectangle with an inset accent-
colored border) `layouts/Sidebar.module.css` established in Phase
5I.2, scaled up — paired with the existing `APP_NAME`/`APP_SHORT_NAME`
constants and the existing (previously unrendered on any screen)
`PRODUCTION_CREDIT` string, now shown beneath the card on every auth
screen. No new organizational claim, security claim, or certification
language was introduced — a forbidden-language grep (`secure`,
`encrypt`, `live monitoring`, `all systems`, `threat monitor`,
`security alert`, `government-certified`, `military-grade`,
`protected infrastructure`) across every changed file returned zero
matches.

**Login and Signup — one design system, not two**: both pages now
share one local, non-exported `AuthShell` wrapper (defined once per
file rather than a new shared component, to keep each page's existing
self-contained scope) rendering the brand header, the page's own
content, and the credit line. They are told apart only by a small
technical eyebrow above each heading — "Account Access" (Login) vs.
"New Account Request" (Signup) — new, concise category labels in the
same vein as every prior phase's eyebrow text (e.g. "Operational
Signals," "Registry Search"), not existing copy and not a claim.
Every field, label, `autoComplete` value, validation rule, submit
handler, and redirect is byte-for-byte unchanged; both pages' existing
heading text ("Sign in" / "Create account") and accessible names are
unchanged, confirmed by `routing.test.jsx`'s
`getByRole('heading', { name: /sign in/i })` assertion passing
unmodified.

**Authentication states**: `PendingApprovalNotice` and
`DeactivatedAccountNotice` (shown from both Login and Signup) each
gained one small `aria-hidden` color-coded square marker before their
existing heading text — an info-tone marker for pending, a danger-tone
marker for deactivated — supplementing, never replacing, the text that
already states the condition. Their `.action` "Back to sign in" button
now composes the shared `btn` base from Phase 5I.3. No wording, no new
state, and no backend detail was added or exposed — both components'
existing deliberate omissions (no approval timeline, no deactivation
reason) are untouched.

**Form design**: `.field input`'s own border/padding/`[aria-invalid]`
overrides were removed from `AuthPages.module.css` — `global.css`'s
Phase 5I.3 form-control base and its own `input[aria-invalid='true']`
rule already cover both identically, so this was a real duplicate
removal, not a behavior change; every label, `aria-invalid`,
`aria-describedby`, and native input type is unchanged.

**Password field**: inspected — no visibility toggle exists today, and
none was added, per the brief's own explicit instruction not to
introduce functionality merely for visual polish.

**Auth buttons**: `.submit` now composes `btn btnPrimary` from
`styles/primitives.module.css` (full-width, a taller 2.75rem for a
stronger primary action), completing the one consolidation Phase 5I.3
explicitly deferred for this file. Disabled state, the "Signing in…" /
"Creating account…" submitting label, and click/keyboard behavior are
all unchanged.

**Brand mark / registry glyph**: the brand mark is static — no
animation, no boot sequence. The animated registry glyph remains
reserved for "Phase 5I.5 — Boot & Loading Experience," per the brief's
own explicit instruction.

**Background**: a static, `pointer-events: none`, radially-masked
precision grid layered behind the shell — no particle system, video,
heavy blur, glassmorphism, or neon effect; the existing Phase 5I.1
atmospheric wash in `global.css` is untouched underneath it.

**Motion**: one entrance fade/translate on the shell using
`--motion-normal`/`--motion-ease` (no new duration invented); no
continuous animation, no animated background, no boot or loading-glyph
animation. The global `prefers-reduced-motion` safety net covers it
automatically.

**Responsive**: a narrow-mobile breakpoint reduces card padding and
brand-name size; the grid background, brand mark, and credit line all
remain visible at every width with no horizontal overflow.

**Accessibility**: every existing label/`aria-invalid`/
`aria-describedby`/`autoComplete`/keyboard path/focus-visible/ARIA
attribute is unchanged; every new decorative element (brand mark, grid
background, account-state markers) is `aria-hidden` or a non-focusable
pseudo-element.

**Security boundary**: `AuthContext.jsx` was read for context only and
not modified. Grepped every changed file for `jwt`/`decode(`/
`localStorage`/role or department-id comparisons/`recipient_user_id`/
storage-path/signed- or public-URL patterns — the one match found
(`LoginPage.jsx`'s own pre-existing comment stating the page *never*
decodes the JWT) predates this phase and is not new usage; otherwise
zero matches.

**Verification**: the 4 directly-relevant test files (26 tests —
`LoginPage`, `SignupPage`, `AuthContext`, `routing`) confirmed green
first; then the full suite (48 files / 354 tests, unchanged — no test
needed to change) run 3 consecutive times with identical results;
`npm run build` succeeded (197 modules, JS 383.47 KB, CSS 44.65 KB —
decorative CSS/JSX only, zero new dependency); backend `pytest tests/`
— 487 passed, unaffected. Manual browser verification was **not
performed** — no dev server was started this phase.

**Not done this phase**: the boot screen and the animated loading
glyph remain untouched, reserved for "Phase 5I.5." A password
visibility toggle was considered and deliberately not added — no such
control exists today, and the brief explicitly prohibited adding one
without a confirmed product requirement.

## Phase 5I.5 — Boot & Loading Experience: Implementation Record

The application's startup/loading identity — one new component
(`BootScreen`), one new App-level CSS module, and a small gate added
to `App.jsx` itself; 2 files created as tests. Verified by re-reading
`App.jsx`, `main.jsx`, `routes/index.jsx`, `AuthContext.jsx`,
`AppShell.jsx`, `LoadingState.jsx`/`.module.css`,
`LoginPage.jsx`/`SignupPage.jsx`, `ProtectedRoute.jsx`,
`RootRedirect.jsx`, `tokens.css`, `global.css`, `constants/app.js`, and
the nested-square brand geometry in `Sidebar.module.css`/
`AuthPages.module.css` directly before writing any code.

**The safest existing lifecycle point, determined by inspection, not
assumed**: `AuthContext` already exposes a genuine `status ===
'loading'` window — true for exactly as long as the very first session
-restoration check (`GET /auth/me`, or an immediate settle if no token
is stored) takes. `ProtectedRoute` and `RootRedirect` already render
`LoadingState` during that window, but neither covers `/login`/
`/signup` directly, so a user opening the app cold could briefly see
the login form (or nothing distinctive) flash before that first
`status` settles. `App.jsx` sits above all of them, so gating there —
using this *existing* status value, never a duplicated timer or second
loading flag — covers every entry route uniformly. This is precisely
the "inside AuthContext's existing loading state" option the brief
itself offered in §8, and the one that required touching
`AuthContext.jsx` not at all.

**Implementation**: `App.jsx` now renders a small internal `AppGate`
component (inside `AuthProvider`, since only there can `useAuth()` be
called) that renders `<BootScreen />` while `status === 'loading'`,
and `<RouterProvider>` (wrapped in one small `.appEnter` transition
div) once `status` resolves either way. `ProtectedRoute.jsx` and
`RootRedirect.jsx` are untouched — their own `status === 'loading'`
branches are still exercised directly by their own existing, isolated
tests and remain valid defensive fallbacks; in production, by the time
either could render, `App.jsx` has already resolved `status` past
`'loading'`, so they simply never see that branch again for the rest
of the session (logout/login never revert `status` back to
`'loading'`).

**LRS Registry Glyph**: a CSS-only nested-square mark reusing the
exact geometry `Sidebar.module.css`/`AuthPages.module.css` already
established (an outer bordered square, an inset accent-bordered inner
square, a small center marker), with four small ticks at each edge
that illuminate in sequence — a "registry scan," deliberately not a
spinner, a hacker-terminal aesthetic, or a game loading bar. The
sequence's duration is derived via `calc()` from the existing
`--motion-slow` token (`calc(var(--motion-slow) * 4)`, with delays at
0/1×/2×/3× that same token) — a deliberate choice to compose the one
new repeating animation in this codebase from an existing token rather
than inventing a new raw duration, documented here as that judgment
call. The glyph is entirely `aria-hidden`; no SVG, image, canvas, or
video asset was added, and no icon/animation library was installed.

**Accessible loading message**: a separate, real `role="status"
aria-live="polite"` text — `Loading Letter Registry System` — is the
one actual loading indication a screen reader receives; the decorative
glyph contributes no text of its own (verified by
`BootScreen.test.jsx`). No unverified claim (`Securing system`,
`Encrypting records`, `Authenticating infrastructure`, `Establishing
secure channel`, `System operational`, `All systems secure`) was
introduced — a forbidden-language grep across every new/changed file
found only the test's own regex asserting their absence, not real
usage.

**Boot lifecycle**: no artificial delay, `setTimeout`, fake percentage,
or fake initialization step was added anywhere — the boot screen is
visible for exactly as long as the real `status === 'loading'` window
already was, confirmed by `App.test.jsx` resolving a controlled
`getCurrentUser` promise and asserting the boot screen disappears and
the router content appears only once that promise settles, with no
`waitFor` relying on a fixed timeout or animation duration.

**Transition into the application**: one short opacity/translate
settle (`App.module.css`'s `.appEnter`, `--motion-normal`/
`--motion-ease`) runs once when the router first mounts; the existing
global `prefers-reduced-motion` safety net in `global.css` already
collapses it to instant, so no local override was needed.

**Loading-state consistency**: `LoadingState` itself, and every one of
its existing call sites (`ProtectedRoute`, `RootRedirect`, and every
page-level fetch), are unchanged — this phase adds one new, additional
identity moment at the very top of the app, and deliberately does not
redesign or replace any other existing loading state, per the brief's
own explicit instruction.

**Reduced motion**: under `prefers-reduced-motion: reduce`, the four
registry ticks stop animating and render fully lit (a complete, static
mark) rather than disappearing — the loading indication is preserved
either way, and the accessible status text is unaffected in both
cases.

**Responsive**: the boot screen uses the same centered flex-column
layout as the authentication entrance (Phase 5I.4E) — glyph, identity
text, and status remain centered and legible from desktop down to very
narrow mobile widths with no horizontal overflow; no separate mobile
layout was needed.

**Performance**: CSS-only glyph (no image, SVG asset, canvas, or
video); no new dependency; `npm run build` grew by exactly the 3 new
source files (197 → 200 modules), with no measurable bundle-size
concern (JS 383.47 KB → 384.93 KB, CSS 44.65 KB → 46.86 KB).

**Accessibility**: the glyph is `aria-hidden="true"`; the real status
text remains in the normal document flow and is announced via
`aria-live="polite"`; no focus trap was added (the boot screen replaces
the entire app tree for a moment, so there is nothing else to trap
focus away from); no formal WCAG compliance is claimed.

**Security boundary**: `AuthContext.jsx` was read but not modified.
Grepped every new/changed file (`App.jsx`, `App.module.css`,
`App.test.jsx`, `BootScreen.jsx`, `BootScreen.module.css`,
`BootScreen.test.jsx`) for `jwt`/`decode(`/`localStorage`/role or
department-id comparisons/`recipient_user_id`/storage-path/signed- or
public-URL patterns — zero matches. No JWT decoding, token parsing, or
auth-token access of any kind was added.

**Tests**: 2 new test files. `BootScreen.test.jsx` (6 tests) covers the
truthful accessible status text, a custom-label case, the absence of
any unverified security/monitoring claim, the rendered LRS identity
text, the glyph's decorative/textless nature, and that the status text
exists independently of (not nested inside) the decorative glyph.
`App.test.jsx` (3 tests) covers the boot-lifecycle gate itself against
a lightweight `createMemoryRouter` stand-in for the real route tree
(the real `routes/index.jsx` and every page it imports are already
covered by their own tests and by `routes/routing.test.jsx` —
duplicating that here would only add weight and fragility): the boot
screen appears only during a genuinely pending `getCurrentUser` call
and disappears once that promise resolves, the application renders
immediately for an unauthenticated session with no artificial delay,
and the boot screen never reappears once initialization has completed.
No test depends on a fixed timeout or an animation duration.

**Verification**: the 2 new test files (9 tests) confirmed green
first; then the full suite (50 files / 363 tests — 48/354 plus the 2
new files) run 3 consecutive times with identical results; `npm run
build` succeeded; backend `pytest tests/` — 487 passed, unaffected
(no backend file touched). Manual browser verification was **not
performed** — no dev server was started this phase.

**Not done this phase**: Phase 5I.6 (final polish/E2E) remains
reserved, as the brief itself describes. No existing page's own
loading state was redesigned.

## Phase 5I.6 — Final Polish, Manual E2E & Handover Audit: Implementation Record

The closing audit across all nine prior visual phases (5I.1 through
5I.5) — a full documentation re-read, a full screen inventory, and a
targeted code audit across visual consistency, branding, boot
experience, responsive behavior, accessibility, motion, functional
coherence, the security boundary, document/classification security,
performance, and error/empty/loading consistency — fixing only the one
genuine defect the audit actually found. No redesign, no new feature,
no reopened product requirement.

**Method**: rather than re-reading every one of the ~90 component/page
files a ninth time, the audit combined automated, codebase-wide
searches (hardcoded colors outside `tokens.css`, `transition: all`,
`outline: none`, stray `console.log`/`setTimeout`, every `@keyframes`
and its reduced-motion coverage, every `@media` breakpoint, every
emoji/pictograph character, `PRODUCTION_CREDIT`/`APP_NAME` usage, and
the full JWT/token/localStorage/role/department-id/recipient/
storage-path/signed-URL security-pattern set) with targeted reads of
the specific files each search's result required judgment on.

**The one genuine defect found and fixed — `NotificationBell`'s icon**:
a codebase-wide emoji search found exactly two pictograph characters
in the entire frontend: the Sidebar/Topbar mobile-drawer toggle's
`☰`/`✕` (plain, monochrome Unicode symbols that already inherit
`currentColor`, consistent with the restrained icon language
everywhere else) and `NotificationBell`'s `🔔` — a full-color,
OS-rendered emoji glyph, the one place in the entire application that
broke the "restrained blue accent, no glow" Precision Ledger identity
every other screen maintained since Phase 5I.1. Replaced with a
CSS-only bell outline (`::before`/`::after` on a 13×13px `.icon` span,
using `--color-text-secondary` — the same understated icon color
Sidebar's own nav glyphs already use). Purely decorative
(`aria-hidden`, unchanged); the button's accessible name
(`aria-label`), `aria-expanded`, click/keyboard behavior, unread-count
badge, and 60-second visibility-aware polling are all byte-for-byte
unchanged — confirmed by `NotificationBell.test.jsx`'s existing 9 tests
passing unmodified (none of them ever asserted on the emoji itself).

**Reviewed and confirmed correct, not a defect** (documented here so a
future reader doesn't rediscover and "fix" these unnecessarily):

- `NotificationPanel.module.css`'s `.panel:focus { outline: none; }` —
  the panel container (`role="region"`, `tabIndex={-1}`) is focused
  only programmatically on open, to move a keyboard/AT user into the
  region; it can never be reached by Tab, so a persistent outline
  around a non-interactive landmark it can never visually associate
  with by keyboard navigation would be pure noise. Every real
  interactive control inside the panel (buttons, links) keeps its own
  `:focus-visible` treatment untouched. `ConfirmDialog` doesn't need
  the same override because it focuses a real button (Cancel), not its
  own container, so the global focus-visible ring already lands
  somewhere meaningful there.
- The 768px/767px breakpoint pairing is not byte-identical everywhere
  (`RecentLetters.module.css`/`DashboardPage.module.css` use
  `max-width: 768px`; `Sidebar`/`Topbar`/most other components pair
  `min-width: 768px` with `max-width: 767px`). At exactly 768px both
  rules can apply simultaneously, but neither conflicts with the
  other's own properties, and the resulting layout (a persistent
  desktop sidebar alongside 2-column dashboard cards) is coherent, not
  broken. Left unchanged — a one-pixel definitional nitpick with no
  visible consequence is not a "genuine defect" under this phase's own
  fix policy.
- `AuthPages.module.css`'s decorative precision-grid background (Phase
  5I.4E) has no equivalent in `BootScreen.module.css` (Phase 5I.5).
  Confirmed intentional: the boot screen is deliberately the simplest
  of the three "entrance" surfaces (per that phase's own "keep it
  recognizable and simple" instruction for the glyph), visible only
  briefly, while the authentication screens are static and can support
  slightly more decorative depth without becoming visual noise.
- The Sidebar brand mark's `sr-only` full `APP_NAME` alongside its
  visible `APP_SHORT_NAME` label and a native `title` tooltip (Phase
  5I.2, pre-existing, not touched by any later visual phase) is mildly
  redundant for a screen reader user but not incorrect ARIA, and
  changing it now would be outside this audit's own "fix only what
  this visual work introduced" boundary.
- Every table (Letter/Department/Admin/User/Authorization/Designation/
  Category/Classification/Document) already uses `scope="col"`
  consistently; only `LetterTable` needs `aria-sort` (the one
  sortable table, per the confirmed backend contract) — consistent,
  not a gap.
- `NavLink`'s active-route indication relies on react-router-dom's own
  built-in `aria-current="page"` (set automatically by the library
  whenever a `NavLink` is active, independent of the `className`
  function this codebase supplies) — already correct, needing no
  addition.
- `ArchiveConfirmDialog`/`AdminTransferDialog` already implement the
  same `role="dialog"`/`aria-modal`/Escape/focus-trap mechanics
  `ConfirmDialog` established — consistent, not duplicated ad hoc.
- `ErrorState`/`errorNormalization.js` (pre-existing, untouched by any
  visual phase) already collapse every backend failure shape into one
  `{ status, message, fieldErrors }` form, never expose a raw backend
  body, and `ErrorState` refuses to render a bare status code —
  confirmed still true, no visual phase weakened this.
- Every `@keyframes` animation in the codebase (`dashboardEnter`,
  `shellIn`, `panelIn`, `dialogBackdropIn`/`dialogPanelIn`,
  `appEnterIn`, `glyphScan`, `spin`) is a one-shot or intentionally
  looping effect already covered by `global.css`'s blanket
  `prefers-reduced-motion` rule, with a local, more specific override
  only where a component needs one (`LoadingState` explicitly stopping
  its spinner, `BootScreen` explicitly holding its ticks fully lit) —
  correct and consistent, not a gap.
- No hardcoded hex color exists in any `.module.css` file outside
  `tokens.css` itself; no `transition: all` exists anywhere in real
  code (only in a comment explaining why not to use it); the one
  `setTimeout` in the entire frontend (`DocumentList.jsx`'s delayed
  `URL.revokeObjectURL`) is a legitimate blob-cleanup delay from Phase
  5E, not a fake loading delay — none of these needed a fix.

**Presentation-only role conditionals** (`DashboardPage.jsx`'s
widget-selection branches, `LetterFormPage.jsx`/`LetterListPage.jsx`'s
pre-existing `isSystemAdmin`/`canCreate` visibility checks) control
only which UI is shown, never data access — each still calls its own
backend-authorized endpoint regardless of what the frontend renders,
exactly the exception this phase's own brief called acceptable.

**Security boundary**: a combined `jwt|decode(|localStorage|
sessionStorage|role ===|department_id ===|recipient_user_id|
storage_path|signed_url|public_url` grep across the entire `frontend/
src` tree found only pre-existing, legitimate matches (the JWT-related
hits are comments stating the app *never* decodes one;
`AuthContext.jsx` is unmodified; the `role ===`/`department_id`
conditionals are the presentation-only cases above) — zero new
security-sensitive logic anywhere. No document storage path, signed
URL, or public URL is exposed; no Delete/Replace document action
exists; no notification-recipient control was added; no
classification-based UI authorization exists anywhere.

**Manual browser verification**: **not performed** — this environment
has no browser-automation tool available to genuinely open the
application and visually walk through it, so none is claimed. Every
finding in this record comes from static code inspection, targeted
unit tests, and the automated searches described above, not from
observing the running application.

**Tests**: no test file needed a change beyond the fix itself, which
needed none (`NotificationBell.test.jsx`'s existing 9 tests never
asserted on the icon's content). The full suite (50 files / 363 tests,
unchanged from Phase 5I.5) was run 3 consecutive times with identical
results; `npm run build` succeeded (200 modules, JS 384.92 KB, CSS
47.29 KB — the +0.43 KB CSS growth is entirely the new bell-outline
rules); backend `pytest tests/` — 487 passed, unaffected (no backend
file touched, consistent with every phase in this arc). Manual
verification remains as stated above: not performed.

**Scope confirmation**: exactly 2 files changed this phase
(`NotificationBell.jsx`, `NotificationBell.module.css`) plus
documentation — confirmed via `git status`. No backend, database,
dependency, route, service, `AuthContext.jsx`, or business-logic file
was touched anywhere in this phase.

**Handover status**: with this audit complete and its one finding
fixed, the Phase 5I visual architecture (5I.1 through 5I.6) is
considered closed. Nothing else surfaced as "visibly broken,
inconsistent, confusing, unfinished, or unnecessarily rough enough
that it should be fixed before handover" — everything else audited
above is either already consistent or a documented, reasoned,
intentional difference.

## Phase 5I.6A — Sidebar Icon Identity Correction: Implementation Record

A targeted correction found during final visual verification: the
Sidebar's navigation "icons" (added Phase 5I.2) were actually 3-letter
monograms (`DAS`/`LET`/`DOC`/`NOT`/`DEP`/`ADM`/`DES`/`CAT`/`CLA`) — a
deliberate placeholder at the time (§20/§27 of this document explicitly
deferred "a real icon system"), but one that read visually as text
labels, not icons, undercutting the "polished/futuristic Precision
Ledger" identity everywhere else. This phase replaces them with a
small, coherent set of actual geometric icons. Visual correction only
— `navigationConfig.js`, routes, labels, permissions, role behavior,
active-route logic, collapse/mobile-drawer behavior, and `Topbar` are
all untouched.

**Approach**: inline SVG, not CSS-drawn shapes and not an icon library
— the brief's own suggested mapping ("grid/dashboard," "shield/person,"
"layered/document-classification") reads as literal line-icon
concepts, more naturally expressed as SVG paths than as CSS
border-box tricks, and inline SVG adds no external asset or
dependency. Nine icons, one per real navigation label (`Dashboard`,
`Letters`, `Documents`, `Notifications`, `Departments`,
`Administrators`, `Designations`, `Categories`, `Classifications`),
plus a tenth for `Users` (the ADMIN-only nav item the brief's own
mapping list omitted but which still needed an icon), plus a plain
square-outline fallback for any future unmapped label — all defined
in `Sidebar.jsx` as a lookup keyed by label, deliberately not a new
field on `navigationConfig.js`, honoring this phase's own boundary.

**One active-state mechanism, not two**: every icon uses
`stroke="currentColor"`, `fill="none"`, a shared 1.4 stroke width, and
round caps/joins — so an icon's color is never independent state, it
simply follows `.linkGlyph`'s own `color`, which `.linkActive
.linkGlyph` already set to `var(--color-primary)` before this phase
and still does. No second active-state mechanism was introduced.

**Container redesign**: `.linkGlyph` was a bordered 30×22px rectangle
holding text (a "chip," which is exactly what made the monogram read
as a label rather than an icon) — changed to a plain, unboxed 18×18px
flex container with no border or background, matching how professional
line-icon sidebars (and this application's own restrained aesthetic)
present navigation icons. Spacing (`.link`'s existing `gap`), the
collapsed-rail centering (`justify-content: center`), and the label's
existing clip-based visual hiding are all unchanged and unaffected by
the smaller, unboxed glyph.

**Icon set** (each 16×16 viewBox, 2-3 primitives): Dashboard — a 2×2
grid of small squares. Letters — an envelope (rectangle + flap
chevron). Documents — a document with a peeking second sheet behind
it. Notifications — a bell silhouette (dome, base line, small clapper
arc), deliberately echoing the same bell concept
`NotificationBell.module.css` established in Phase 5I.6, so the
Sidebar's own "Notifications" icon and the Topbar bell read as the
same mark. Departments — a building facade (rectangle with grid
division lines). Administrators — a shield outline. Users — a person
(head circle + shoulder arc). Designations — an ID badge (card body,
photo circle, clip tab). Categories — a folder silhouette.
Classifications — three stacked, offset rhombus outlines ("layers"),
deliberately distinct from Documents' two-sheet stack.

**Accessibility**: every icon is `aria-hidden="true"` and
`focusable="false"`; the adjacent `.linkLabel` text remains each
link's real accessible name — unaffected by any of this, confirmed by
every existing `getByRole('link', { name: ... })` assertion passing
unmodified. `aria-current="page"` (react-router-dom's own built-in
`NavLink` behavior, confirmed in Phase 5I.6) is untouched. Collapsed
sidebar: labels remain in the DOM, the native `title` tooltip is
unchanged, keyboard navigation and the mobile-drawer focus trap are
untouched.

**Security/functional boundary**: grepped `Sidebar.jsx`/
`Sidebar.module.css` for `jwt`/`decode(`/`localStorage`/role or
department-id comparisons/`recipient_user_id`/storage-path/signed- or
public-URL patterns — zero matches. `navigationConfig.js` confirmed
byte-for-byte unchanged via `git status`; no route, service, API,
backend, or dependency file touched.

**Tests**: no existing test needed to change — none of
`Sidebar.test.jsx`'s 9 existing assertions ever queried the glyph's own
content, only each link's accessible name (computed from the visible
label, unaffected by an `aria-hidden` sibling). One new regression test
added, confirming every rendered navigation link contains a
decorative, `aria-hidden` `<svg>` icon.

**Verification**: `Sidebar.test.jsx` (10 tests, +1) and
`navigationConfig.test.js` (5 tests, unchanged) confirmed green first;
then the full suite (50 files / 364 tests, +1) run 3 consecutive times
with identical results; `npm run build` succeeded (200 modules, JS
384.92 KB → 387.00 KB, CSS 47.29 KB → 47.16 KB — decorative CSS/JSX
only, zero new dependency); backend `pytest tests/` — one incidental
failure (`test_decode_access_token_rejects_tampered_signature`, a
randomized-tamper test) appeared on the first run, reproduced as
passing both in isolation and on a full-suite rerun (487 passed) —
confirmed a pre-existing flake unrelated to this phase, which touched
no backend file. Manual browser verification was **not performed** —
no browser-automation tool is available in this environment.

**Not done this phase**: no other Sidebar behavior, Topbar icon
(`☰`/`✕`, already confirmed monochrome and consistent in Phase 5I.6),
or navigation data changed.

## Phase 6B — Daak Management System Branding & Authentication Redesign: Implementation Record

The application's visible name and identity, plus a split-screen
Login/Signup redesign — implemented after, and independent of, Phase
6A's functional correspondence work, which this phase does not touch.

**Application name — one source, confirmed before changing anything**:
a codebase-wide search found exactly one place the literal string
"Letter Registry System" was defined — `constants/app.js`'s `APP_NAME`
— every consumer (`Sidebar`, `Topbar` via `APP_NAME`, `AuthShell`,
`BootScreen`, `LetterFormPage`'s `title={APP_NAME}`) already imported
it rather than hardcoding it, so changing the one constant (now
"Daak Management System", `APP_SHORT_NAME` now "DMS") propagated
everywhere the name is rendered. Two non-JS occurrences needed a
manual edit, since neither can reference a JS constant:
`frontend/index.html`'s `<title>` and `frontend/.env.example`'s
documented default. Two test files hardcoded the literal old string in
their own assertions (`App.test.jsx`, `BootScreen.test.jsx`) and were
updated to match — not weakened, still asserting the exact rendered
text. The backend's own `APP_NAME` setting (FastAPI/Swagger `title=`
only, never seen by an end user of the application) was deliberately
left untouched — out of this phase's explicitly frontend-scoped
brief. `Letter`/`Letter Registry`/`correspondence` — the actual
business-domain terminology — appear nowhere near this rename and are
completely unaffected.

**Assets — used exactly as supplied, never regenerated**: `govt_bal.webp`
(400×340, the official Government of Balochistan emblem) and
`front_page.jpeg` (736×1104, the supplied institutional photograph)
were located at the repository root, moved byte-for-byte (MD5-verified
before and after) into `frontend/src/assets/` — the project's own
documented location for "static images... bundled by Vite" — and
re-exported once from `constants/app.js` (`GOVT_LOGO_SRC`/
`AUTH_BACKGROUND_SRC`), the same "one source" convention `APP_NAME`
already established. The root-level duplicates were removed once the
copies were verified identical. Neither file's bytes, dimensions, or
format were altered — confirmed by the production build re-emitting
them at their original sizes (22.24 KB / 108.61 KB) under new,
content-hashed filenames.

**The government logo — real, everywhere the brand identity appears,
always decorative**: replaces the old CSS-drawn nested-square
placeholder mark in the Sidebar header, the authentication shell, and
(newly) the boot screen. Every placement uses `alt=""` — in each
location, the adjacent visible or `sr-only` `APP_NAME`/`APP_SHORT_NAME`
text already fully names the application's identity, so a second
screen-reader announcement of the same fact would be redundant (the
brief's own explicit guidance, applied identically in all three
places). `object-fit: contain` (never `cover`) everywhere the logo
appears, so the crest itself is never cropped; sized modestly (22–40px
tall depending on context) rather than enormous. No "Official
Government Portal"/"Secure Government Network"/"Government
Certified"/"Encrypted Government System" language was added anywhere
— a forbidden-language grep across every changed file confirms zero
matches; the logo itself is the identity, per the brief's own framing.

**Login/Signup — a real split-screen layout, not a floating card**: the
previously-duplicated, per-page `AuthShell` (Phase 5I.4E) is now
extracted into `components/AuthShell.jsx` — once its layout grew a
genuine two-pane structure worth sharing properly, duplicating it
across two files stopped being the smaller change. Left pane: the
supplied photograph, `object-fit: cover`, `flex: 0 0 58%` (within the
requested 55–60% range), `object-position: center` — the pane's own
aspect ratio crops the image's left/right edges before its top/bottom
at typical desktop proportions, keeping the photograph's own visual
center always in frame without distortion. Right pane: the real
government logo, brand text, the existing form card (`AuthPages.
module.css`, now holding only the card's own internals since the
surrounding chrome moved out), and the unchanged `PRODUCTION_CREDIT`
line. Every field, validation rule, submit handler, loading state,
error path, and redirect in `LoginPage.jsx`/`SignupPage.jsx` is
byte-for-byte unchanged — confirmed by both pages' full existing test
suites passing with zero modification. No password-visibility toggle
was added (none existed before).

**Responsive — the existing 768px breakpoint, not a new one**: below
768px (the same breakpoint `Sidebar`/`Topbar` already use), the split
collapses to a stacked layout — a 160px image header band above the
form, never disappearing, never squeezing the form narrower than the
viewport allows. No new breakpoint was introduced beyond the existing
420px rule (kept, for the form card's own narrow-width padding).

**Footer — smaller, same wording, same one instance**: `AppShell`'s
footer padding reduced from `--space-sm` to `--space-2xs` vertically
with a tighter line-height — visibly less dominant, still exactly the
unchanged `PRODUCTION_CREDIT` text ("A Project by AJ-OVA Labs"), still
rendered exactly once per authenticated screen (`AppShell.test.jsx`'s
existing "exactly once" assertion passes unmodified). Login/Signup
already render the same credit line via `AuthShell` — not a second,
independent footer, the same single constant either way.

**Security boundary**: no authentication logic, `AuthContext`
behavior, validation rule, or redirect changed anywhere — grepped
every changed file for JWT/token/localStorage patterns and for the
five forbidden security-claim phrases above; the one JWT-related match
is `LoginPage.jsx`'s own pre-existing comment stating the page *never*
decodes one.

**Tests**: `App.test.jsx`/`BootScreen.test.jsx` updated (2 hardcoded
literal-string assertions, not weakened); a new `AuthShell.test.jsx`
(4 tests) covers both images being decorative (`alt=""`), the brand
identity text, the single credit line, and children rendering. Every
other existing test file — `LoginPage`, `SignupPage`, `Sidebar`,
`AppShell`, `routing` — passes with zero modification. Full suite: 51
files / 386 tests (+1 file, +4 tests), run 3 consecutive times with
identical results; `npm run build` succeeded (204 modules — the two
new bundled asset files); backend `pytest tests/` — 510 passed,
completely unaffected (no backend file touched, confirming Phase 6A's
own functionality is untouched, per this phase's own explicit
instruction).

**Manual browser verification**: **not performed** — no
browser-automation tool is available in this environment. The
split-screen layout's actual visual balance (image crop framing,
right-pane proportions at real viewport sizes) has not been visually
confirmed in a running browser; every claim above is backed by
automated tests and direct code/CSS inspection, not observation.
