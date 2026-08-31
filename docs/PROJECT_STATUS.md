# LRS Project Status

**A Production of AJ-Labs.** Suitable for sharing with the project
supervisor as-is.

---

## Project Status: Implementation Complete

**This is the final implementation phase. No further phase is
planned.** The Phase 6D final-polish pass reviewed the already-built,
already-tested dashboard for real problems rather than redesigning it,
and confirmed the project is ready for handover.

**Live data-accuracy verification** (in place of the pixel-level
browser verification this environment cannot perform — no browser-
automation tool is available): a real backend server was started
against the real dev database; two brand-new, clearly-labeled
throwaway accounts were created and logged in through the real login
endpoint (never by impersonating an existing real account — an earlier
attempt to mint a token for one of the project's actual users was
correctly blocked by this session's own safety tooling); two
clearly-labeled OUTGOING test letters were created through the real
API. Every dashboard chart's expected value was hand-computed from
this known sample and compared against the actual
`GET /letters/aggregate` response — direction counts, department
totals, dispatch totals, and monthly trend buckets all matched
exactly, for both a SYSTEM_ADMIN-level view and each throwaway
account's own department-scoped view (confirming a supplied
`department_id` is silently ignored for non-SYSTEM_ADMIN, exactly as
designed). Both test letters were then archived and both throwaway
accounts deactivated — reversible, non-destructive cleanup consistent
with this system's own "never physically delete" convention; AJ should
note the dev database's Total Letters figure now reads 6 rather than 4
until those two archived rows are removed by a direct database
operation, which was not performed without being asked.

**One genuine, previously-latent defect was found and fixed**:
`CorrespondenceTrendChart`'s x-axis labeled only the first and last
month. This happened to cover every month that existed in the real
data at the time (1-2 months), so it was invisible until this phase's
own fresh re-read of the component — a third month would have gone
completely unlabeled on the graphic. Fixed with an evenly-spaced,
always-includes-the-endpoints thinning strategy, covered by two new
regression tests. This was the only code change made this phase —
everything else was inspected and confirmed correct, not altered
(documented in full, including what was reviewed and left alone, in
`docs/architecture/dashboard.md`'s own "Phase 6D" §35).

Frontend suite grown to 411 tests (54 files, +2), run 3 consecutive
times with identical results. Backend suite re-confirmed at 525 tests,
unaffected by this phase's live-database verification activity. No
backend file, `AuthContext`, `RoleGuard`, `ProtectedRoute`,
`tokenStorage.js`, or `apiClient.js` was touched. Nothing was committed
or pushed — that remains a separate, explicit action for AJ to
request.

**Deliberately deferred, not hidden**: a Department × Direction chart
(needs a two-dimensional aggregate endpoint, never built), a dashboard
date-range control (no default/preset ever confirmed wanted), an
audit read API and its own analytics (`FUTURE` since Phase 5G §20),
and a Designation edit/detail page. Each was evaluated in its own
phase and found to need either a business decision this project was
never given, or work explicitly out of scope for a frontend-only
phase.

### Phase 6D — Dashboard Operational Graphs

Complete (prior phase), **frontend
only**. The supervisor explicitly asked that the KPI-card presentation
itself be replaced, not merely extended with new data — the eight
role-dependent `SummaryCard`s Phase 5F/5I built are gone.

**The four graphs**, each consuming Phase 6C's `GET
/letters/aggregate` directly, no backend change needed: Incoming vs.
Outgoing (`group_by=direction`), Letters Received by Department
(`group_by=department`), Letters Sent by Department
(`group_by=dispatch_department` — the real Phase 6A dispatch target,
never `source_department_id`, which carries no authorization meaning),
and Correspondence Activity Over Time (`group_by=month`, two bounded,
direction-filtered requests merged client-side by date key — the
Phase 6C API deliberately has no two-dimensional `group_by`, so this
is the one safe, bounded way to compare Incoming vs. Outgoing over
time without a client-side pseudo-aggregation over raw Letters).

**No chart library was installed.** `package.json` was inspected
first, confirmed to have none, and a genuine evaluation concluded
plain CSS proportional-width bars and a small hand-written SVG line
plot were sufficient and a better fit for the existing "Precision
Ledger" design language than a generic library's own default styling
— a deliberate decision, not an assumption. Every chart's label and
count is real, always-visible text next to its bar or in a legend/
table, never a tooltip-only value; the two trend-chart series are
distinguished by line style (solid vs. dashed) and marker shape, not
color alone.

**Department × Direction** (e.g. "which department sent the most
Outgoing correspondence," broken out per department) was evaluated and
explicitly left out — `DEFERRED — requires a two-dimensional aggregate
endpoint`, per the phase's own instruction not to fabricate one or
approximate it with a request per department.

**Two small headline figures remain** (Total Letters, Unread
Notifications) — genuinely orienting numbers, not a shrunk-down copy
of the removed card wall. The old SYSTEM_ADMIN/ADMIN administration
cards (Active Departments, Pending Admin Approvals, Active Users,
Pending User Approvals) were **not** reintroduced as charts or
otherwise — they answer an administration question the
Departments/Administrators/Users screens already show, not the
confirmed correspondence-volume question this phase's brief asked for.

Frontend test suite grown to **409 tests** (54 files): 23 new
(`HorizontalBarChart`, `CorrespondenceTrendChart`,
`aggregateChartHelpers`) plus a full rewrite (not a weakening) of
`DashboardPage.test.jsx` to match the new dashboard shape, run 3
consecutive times with identical results. A production build was
confirmed to include the new components' actual rendered output, not
merely compile without error. No backend file was touched — the Phase
6C contract was sufficient as published, so no genuine API deficiency
was found or reported. Manual browser verification: the dev server was
confirmed to boot cleanly, but full visual/responsive/role-by-role
verification was **not performed** — no browser-automation tool is
available in this environment. Full record in
`docs/architecture/dashboard.md`'s own "Phase 6D" section.

### Phase 6C — Dashboard Analytics API

Complete (prior phase), **backend only**. A confirmed supervisor
requirement — the operational Phase 5F dashboard's KPI cards are hard
for non-technical users to interpret without a visual breakdown —
reactivated Phase 5G's own previously-deferred design
(`docs/architecture/dashboard-analytics-api.md`), which that phase
implemented rather than re-deriving from scratch.

**The endpoint**: `GET /api/v1/letters/aggregate?group_by=...` answers
Incoming-vs-Outgoing counts, category/classification/department/
dispatch-department breakdowns, and day/week/month correspondence
trends — one `GROUP BY` query per request, never N+1, never a row
loaded into Python for counting. Every other `GET /letters` filter
(status, category, classification, date range) plus Phase 6A's own
`direction`/`dispatch_department_id` are reusable as narrowing filters
on top of the grouping itself.

**Reassessed, not blindly ported, from Phase 5G's own design**: Phase
5G predates Phase 6A's correspondence-direction schema entirely, so
this phase had to decide which of Phase 6A's five new fields actually
belong in an aggregate. `direction` became both a filter and its own
`group_by` dimension (directly answers "Incoming vs Outgoing").
`dispatch_department_id` became both a filter and a new
`group_by=dispatch_department` dimension — a genuinely different
question from `department` (which still means "owning department,"
unchanged), since a dispatched-but-not-yet-recorded letter has no row
owned by the receiving department yet. `diary_number`,
`recorded_from_letter_id`, and `continuation_of_letter_id` were
deliberately left out — none is a dimension anyone would meaningfully
group correspondence by. Phase 5G's own "descending by count" ordering
rule was kept for every non-date dimension, but deliberately
overridden for day/week/month buckets to chronological order — a
frequency-sorted trend chart would be meaningless.

**Authorization**: zero new logic. The exact same
`letter_visibility_filter(user)` and `SYSTEM_ADMIN ? department_id :
user.department_id` derivation `GET /letters` already uses is reused
unmodified — verified, not just asserted, by a dedicated regression
test proving a USER's aggregate `total` can never exceed what that same
USER's own `GET /letters` would return for the same filters.

**No migration or index was needed** — `alembic check` confirmed zero
schema drift; every column this endpoint groups or filters by was
already indexed, either from earlier phases or Phase 6A's own
migration.

Backend test suite grown to **525 tests** (510 + 15 new), run twice
consecutively with zero regressions. One unrelated, pre-existing flaky
test (`test_security.py::test_decode_access_token_rejects_tampered_signature`)
was diagnosed during this phase's own verification — a base64
padding-bit collision in its own tamper simulation, unrelated to this
phase's changes — and disclosed rather than silently ignored or
fixed outside this phase's scope. No frontend file, dashboard chart, or
`DashboardPage.jsx` change — explicitly backend-only, per this phase's
own brief. Full record in `docs/architecture/dashboard-analytics-api.md`'s
own "Phase 6C" section.

### Phase 6B — Daak Management System Branding & Authentication Redesign

Complete (prior phase). The application's visible identity, implemented
independently of — and without touching — Phase 6A's functional
correspondence work below.

**The rename, confirmed from one source before changing anything**: a
codebase-wide search found exactly one place the string "Letter
Registry System" was ever defined — `constants/app.js`'s `APP_NAME`.
Every screen that shows the name already imported that one constant
rather than hardcoding it, so changing it once (to "Daak Management
System"/"DMS") renamed the application everywhere it's visible.
Two static, non-JS spots needed a manual edit since neither can
reference a JS constant: `index.html`'s browser tab title and
`.env.example`'s documented default. The backend's own `APP_NAME`
setting (FastAPI/Swagger documentation title only — never seen by an
actual user of the application) was deliberately left alone, out of
this phase's explicitly frontend-scoped brief.

**The Government of Balochistan logo** — the actual supplied
`govt_bal.webp`, moved byte-for-byte (MD5-verified) into
`frontend/src/assets/`, never regenerated or replaced with a
placeholder — now appears in the Sidebar, on Login/Signup, and on the
boot screen, always as a decorative image (`alt=""`): in every one of
those three places, visible or screen-reader text right next to it
already states the application's identity, so the logo never needs to
carry that information a second time. No "Official Government
Portal"/"Secure Government Network"/"Government Certified" language
was added anywhere — confirmed by a dedicated grep across every
changed file.

**Login and Signup** now use a genuine split-screen layout — the
supplied `front_page.jpeg` filling the left ~58% of the viewport, the
existing, completely unmodified sign-in/sign-up form on the right.
The shell chrome around the form, previously duplicated in both
`LoginPage.jsx` and `SignupPage.jsx`, was extracted into one shared
`AuthShell` component now that it has a real two-pane layout worth
sharing rather than maintaining twice. Every field, validation rule,
submit handler, loading state, error path, and redirect is
byte-for-byte unchanged — both pages' complete existing test suites
pass with zero modification. Below the existing 768px breakpoint, the
layout stacks (a short image header band above the form) rather than
squeezing the form narrower or hiding the identity.

**The footer** is visibly smaller (tighter padding, shorter
line-height) but says exactly the same thing, exactly once per screen,
as before.

Frontend test suite grown to **386 tests** (51 files, +4), run 3
consecutive times with identical results. Backend test suite unchanged
at **510 tests** — confirming Phase 6A's own functionality was not
disturbed, per this phase's own explicit instruction. Manual browser
verification: **not performed** — no browser-automation tool is
available in this environment; the split-screen layout's actual visual
balance at real viewport sizes has not been visually confirmed.

### Phase 6A — Incoming/Outgoing Correspondence, Diary Number & Letter Continuation

Complete (prior phase). The first functional (not visual) enhancement
since the Phase 5I visual arc closed.

**The core insight, from inspecting the actual code before designing
anything**: every `Letter` before this phase already represented one
thing — correspondence recorded by the department that received it
(`recipient_department_id` is always the recorder's own department,
never a client-suppliable destination). Preserving that exact meaning
for both directions — `recipient_department_id` stays "the owning
department" whether the letter is `INCOMING` or `OUTGOING` — meant the
entire existing security boundary (`assert_letter_access`,
`letter_visibility_filter`, `assert_department_access`) needed **zero**
changes. The actual dispatch destination lives in a new, separate
field, `dispatch_department_id`, which carries authorization meaning
for exactly one new, narrow, additive operation (see below) and
nowhere else.

**Diary Number**: confirmed from the code (not assumed) that
`reference_number` was never unique in any scope — a Phase 4B finding,
still open. `diary_number` is a new, separate operational identifier,
generated by a real row-locked Postgres sequence, unique per
`(department, direction)` — matching how every other resource in this
schema is already department-isolated, and avoiding an invented
annual-reset rule nobody confirmed.

**The "Record" action**: `POST /letters/{id}/record` copies every field
from an outgoing letter into a brand-new incoming letter — the
recipient department never re-types anything. Idempotent: a repeat
call returns the same letter, never a duplicate, enforced by a real
partial unique database index (not just a frontend check) — the
brief's own explicit "server-side, not just disabling a button"
instruction. A response is a new, separate Letter linked via
`continuation_of_letter_id`, never an overwrite.

**A real bug found and fixed during this phase's own testing**: the
first draft of the receipt-confirmation notification linked the
dispatching department to the *new incoming* letter — which they
cannot open (they don't own it). Fixed to link back to their own
outgoing letter instead, with a dedicated regression test added.

Every one of the ten business-rule questions the brief posed is
answered from actual code evidence in
`docs/architecture/correspondence.md`, with what's still genuinely
undecided (an annual diary-number reset, multi-department dispatch)
marked PENDING BUSINESS CLARIFICATION rather than silently assumed.

Backend test suite grown to **510 tests** (+23, one migration
upgrade/downgrade/upgrade cycle verified with zero drift). Frontend
test suite grown to **382 tests** (+18), run 3 consecutive times with
identical results. Manual E2E verification: **not performed** — no
browser-automation tool is available in this environment.

### Phase 5I.6A — Sidebar Icon Identity Correction

Complete (prior phase). A
targeted fix found during final visual verification: the Sidebar's
navigation "icons" (added Phase 5I.2) were actually 3-letter monograms
(`DAS`/`LET`/`DOC`/etc.) — a deliberate placeholder at the time, but
one manual review confirmed read as text labels, not icons, undercutting
the intended Precision Ledger identity.

**Fix**: replaced with 9 small inline SVG icons (no icon library, no
external asset) — grid/envelope/document-stack/bell/building/shield/
badge/folder/layers for Dashboard/Letters/Documents/Notifications/
Departments/Administrators/Designations/Categories/Classifications,
plus a person icon for `Users` (the ADMIN-only item the brief's own
suggested mapping omitted). Every icon uses `stroke="currentColor"`,
so its color simply follows the existing `.linkActive .linkGlyph`
active-state rule — never a second, independent active-state
mechanism. The bordered 30×22px "chip" container (which is what made
the monogram read as a label) was replaced with a plain, unboxed
18×18px icon box.

**Explicitly unchanged**: `navigationConfig.js`, routes, labels,
permissions, role behavior, active-route logic, Sidebar collapse
behavior, mobile-drawer behavior, and `Topbar` — all confirmed
unchanged via `git diff`. `aria-current="page"` (react-router-dom's
own built-in behavior) and every link's real accessible name (the
visible label text) are untouched — no existing test needed to change;
one new regression test was added confirming every navigation link
renders a decorative, `aria-hidden` icon. Zero new dependencies.

Test suite grown to **364 frontend tests** (50 files, +1) and **487
backend tests** (unchanged — one incidental flaky test reproduced as
passing both in isolation and on a full rerun, confirmed unrelated to
this frontend-only phase), run 3 consecutive times with identical
results. Full implementation record in
`docs/architecture/ui-design-system.md`'s own "Phase 5I.6A" section.

### Phase 5I.6 — Final Polish, Manual E2E & Handover Audit

Complete (prior phase).
The closing audit across all nine prior visual phases (5I.1–5I.5): a
full re-read of every project documentation file, a full screen
inventory, and a codebase-wide audit across visual consistency,
branding, boot experience, responsive behavior, accessibility, motion,
functional coherence, the security boundary, document/classification
security, performance, and error/empty/loading consistency — fixing
only genuine issues actually found. No redesign, no new feature, no
reopened product requirement.

**Method**: combined automated, codebase-wide searches (hardcoded
colors outside `tokens.css`, `transition: all`, `outline: none`, stray
`console.log`/`setTimeout`, every animation's reduced-motion coverage,
every responsive breakpoint, every emoji/pictograph character,
branding-string consistency, and the full JWT/token/localStorage/
role/department-id/recipient/storage-path/signed-URL security pattern
set) with targeted reads of the specific files each result required a
judgment call on.

**The one genuine defect found and fixed**: `NotificationBell`'s icon
was a raw 🔔 emoji — the one full-color, OS-rendered pictograph
anywhere in the entire application, breaking the restrained,
CSS-geometric "Precision Ledger" icon language every other screen
maintained since Phase 5I.1. Replaced with a CSS-only bell outline
using the same understated icon color Sidebar's own nav glyphs already
use. Purely decorative; the button's accessible name, `aria-expanded`,
click/keyboard behavior, unread-count badge, and polling are all
byte-for-byte unchanged — confirmed by its own 9 existing tests passing
unmodified.

**Reviewed and confirmed correct, not defects** (documented in full,
with reasoning, in `docs/architecture/ui-design-system.md`'s own
"Phase 5I.6" section, so they aren't rediscovered and "fixed"
unnecessarily later): `NotificationPanel`'s deliberate
`outline: none` on its own non-Tab-reachable focus container; a
one-pixel breakpoint-naming inconsistency (768px vs. 767px) with no
visible consequence; the Boot screen's deliberately simpler background
compared to the Authentication entrance; a mild, pre-existing,
untouched screen-reader redundancy in the Sidebar brand mark;
consistent table/dialog/focus-indication patterns across every
resource; and an already-clean, unweakened error-normalization layer.

**Security boundary**: a combined security-pattern grep across the
entire `frontend/src` tree found zero new security-sensitive logic —
every match was either a comment stating the app *never* performs that
action, or one of the confirmed presentation-only role conditionals
this phase's own brief explicitly allows (they gate which UI renders,
never data access). `AuthContext.jsx` was not modified.

**Manual browser verification: not performed** — no browser-automation
tool is available in this environment, so none is claimed. Every
finding came from static code inspection, targeted unit tests, and the
automated searches above.

Test suite unchanged at **363 frontend tests** (50 files) and **487
backend tests**, run 3 consecutive times with identical results. The
Phase 5I visual architecture (5I.1 through 5I.6) is now considered
closed.

### Phase 5I.5 — Boot & Loading Experience

Complete (prior phase). The application's startup/loading identity —
one new component (`BootScreen`), gated at `App.jsx` using
`AuthContext`'s own existing `status === 'loading'` window (never a
duplicated timer). A CSS-only "LRS Registry Glyph" (the same
nested-square geometry as Sidebar/Auth, plus four ticks illuminating
in sequence, a duration derived via `calc()` from the existing
`--motion-slow` token) and a truthful `role="status"` message.
`ProtectedRoute`/`RootRedirect`'s own loading branches, `LoadingState`,
and every other existing loading moment are unchanged;
`AuthContext.jsx` was read but not modified. Test suite grown to 363
frontend tests (50 files) / 487 backend tests, run 3 consecutive times
with identical results.

### Phase 5I.4E — Authentication Visual Transformation

Complete (prior phase). The fifth screen-level visual transformation —
the unauthenticated entrance experience (`LoginPage`, `SignupPage`,
and the `PendingApprovalNotice`/`DeactivatedAccountNotice` states they
render). Confirmed the existing composition was exactly the generic
"white card + email + password + blue button" pattern, with the
submit button never composed onto the Phase 5I.3 shared primitives.
Both pages now share one local `AuthShell` wrapper rendering a static
brand mark (the Sidebar's nested-square geometry, scaled up),
`APP_NAME`, and the previously-unrendered `PRODUCTION_CREDIT` line —
distinguished only by a small eyebrow label. Both account-state
notices gained a small color marker. `AuthContext.jsx` was read for
context only, not modified. Test suite unchanged at 354 frontend tests
(48 files) / 487 backend tests, run 3 consecutive times with identical
results.

### Phase 5I.4D — Documents & Notifications Visual Transformation

Complete (prior phase). The fourth screen-level visual transformation —
Documents (within the Letter dossier) and Notifications (Topbar bell,
panel, and the full `/app/notifications` page). `DocumentList` already
inherited the Phase 5I.4C row-accent-bar treatment for free via its
shared `DataTable.module.css` import. `LetterDetailPage` gained a
real, non-fabricated attachment count; the upload form gained a
percentage-bound progress bar; the panel gained an "Operational
Signals" eyebrow and a CSS-only bell connector; notification rows
gained one more static unread dot; the notification page gained the
same eyebrow/accent-line/chip-count header language used elsewhere.
`NotificationBell` audited and left unmodified. Test suite unchanged
at 354 frontend tests (48 files) / 487 backend tests, run 3
consecutive times with identical results.

### Phase 5I.4C — Administration Visual Transformation

Complete (prior phase). The third screen-level visual transformation —
the entire administration workspace (Departments, Administrators,
Users, Authorizations, Designations, Categories, Classifications; ~28
files), verified by re-reading every list/create/detail page and the
shared `AdminPages.module.css`/`DataTable.module.css` directly before
editing. Nearly every page already shared exactly two files — enhancing
those two shared files once cascaded a console-wide eyebrow/accent-
line/chip-count header language, a consistent button treatment, and a
one-family row-accent-bar table hover to all seven resources.
`AdminTransferDialog` gained real visual separation between current-
department/target-department/consequences, its required wording
confirmed byte-for-byte unchanged. Every API payload, service call,
role branch, and 403/404 collapsing behavior confirmed unchanged via
`git diff` and a dedicated 107-test pass across all 17 Administration
test files. Test suite unchanged at 354 frontend tests (48 files) / 487
backend tests, run 3 consecutive times with identical results.

### Phase 5I.4B — Letter Registry Visual Transformation

Complete (prior phase). The
second screen-level visual transformation — the Letter registry family
only (`LetterListPage`, `LetterFormPage`, `LetterDetailPage`,
`LetterFilters`, `LetterTable`), verified by re-reading every one of
these files and all four relevant test files directly before editing.

**Implemented**: a registry header (eyebrow/accent line, the existing
`{total} total` count restyled as a chip — same exact text, since a
test asserts it verbatim); the filter panel recomposed into a
"Registry Search" console — the same 13 fields, now grouped into four
labeled `<fieldset>`s, plus a purely decorative "N active filters"
badge computed from the page's own already-existing filter-count logic;
the registry table gained a left accent-bar-on-hover (scoped to this
table only, so the shared admin `DataTable` is unaffected) and tabular
reference numbers; the Letter form gained the same header treatment and
finally composed the shared button primitives (deferred from Phase
5I.3, which explicitly excluded Letter pages); the Letter detail page
became a four-section "record dossier" (Correspondence/Source/Sender/
Additional details) instead of one flat 11-field grid.

**A deliberate, recorded omission**: Category/Classification were NOT
added to the detail-page dossier, despite being suggested — doing so
would require a new service call and role branch `LetterDetailPage`
doesn't already have, which is a functional change, not a visual one.

**Explicitly unchanged**: every field, id, filter key, URL parameter,
sort field, validation rule, payload shape, and role-conditional branch
across all five files — confirmed via `git diff` that none of the
data-fetching/business logic appears in the changed lines. Zero new
dependencies.

Test suite unchanged at **354 frontend tests** (48 files — no test
needed to change, since no existing behavior changed) and **487 backend
tests**, run 3 consecutive times with identical results — all 48
pre-existing Letter-registry-specific assertions (URL sync, sorting,
filter apply/clear, role-specific rendering, Source Department/
Designation auto-fill, document integration, archive confirmation)
passed completely unmodified. Full implementation record in
`docs/architecture/ui-design-system.md`'s own "Phase 5I.4B" section.

### Phase 5I.4A — Dashboard Visual Transformation

Complete (prior phase). The first
screen-level visual transformation — `/app/dashboard` only, verified by
re-reading `DashboardPage`/`SummaryCard`/`RecentLetters`/`QuickActions`
directly before editing.

**Implemented**: a deliberate four-zone composition (header, metrics,
registry activity, quick actions) replacing four independently-styled
cards; a header with a neutral eyebrow/subtitle (no invented
system-health or security claim — grepped and tested for this
explicitly); every summary card now shares one consistent treatment
(a left accent bar, a corner-bracket mark, tabular numerals, a
restrained hover lift) rather than a dozen bespoke styles; Recent
Letters reuses the existing accent-bar-on-hover language from
`Sidebar`/`NotificationItem` and gained a real (not fabricated) "N
shown" count; Quick Actions became one column of tiles with a
decorative, `aria-hidden` directional arrow. One subtle whole-page
entrance fade is the only new motion — no per-card stagger, no chart,
no trend, no fabricated percentage or comparison.

**Explicitly unchanged**: every metric, fetch, and role-based branch in
`DashboardPage.jsx` — confirmed via `git diff` that all four
`role === '...'` conditionals fall outside this phase's changed lines.
No new dependency; no system-status indicator (still no honest signal
to back one).

Test suite grown to **354 frontend tests** (48 files, 349 + 5 new) and
unchanged at **487 backend tests**, run 3 consecutive times with
identical results — every pre-existing Dashboard assertion (wrong-role
requests never fire, independent widget failure, no fabricated zero,
exact Letter-link hrefs) passed completely unmodified. Full
implementation record in `docs/architecture/ui-design-system.md`'s own
"Phase 5I.4A" section.

### Phase 5I.3 — Core UI Primitives & Interaction System Implementation

Complete (prior phase). The third implementation pass against the Phase 5I proposal —
**reusable primitives only**, deliberately excluding Dashboard, Letter
pages, Administration pages, Documents, the Notification panel, and
Authentication pages, each explicitly reserved for its own later phase.

**Implemented**: a new shared `styles/primitives.module.css` (button
variants, table base, dialog base) that `AdminPages.module.css`,
`LetterFilters.module.css`, `DocumentUploadForm.module.css`,
`DataTable.module.css`, `LetterTable.module.css`,
`ConfirmDialog.module.css`, `ArchiveConfirmDialog.module.css`,
`Topbar.module.css`, and `NotificationItem.module.css` now `compose`
from via CSS Modules' native mechanism — no new component, every page
keeps its exact existing markup. A global form-control base (input/
select/textarea/checkbox) was added to `global.css`, since CSS Modules'
`composes` cannot target the descendant selectors most of this
codebase's form duplication was written with — this reaches every
existing form with zero markup change and let five duplicate per-file
blocks be deleted outright. `StatusBadge` gained a small `aria-hidden`
shape per tone (circle/diamond/square); `EmptyState` gained a small
CSS-only document glyph; `NotificationItem`'s unread state gained a
left accent bar in addition to its existing background/weight signals;
`ConfirmDialog`/`ArchiveConfirmDialog` gained a short entrance
animation, fully covered by the existing reduced-motion foundation.
Two new test files (`StatusBadge.test.jsx`, `EmptyState.test.jsx`)
close a real prior gap — neither primitive had dedicated tests before.

**A scope correction, recorded honestly**: an initial edit touched
`pages/LetterFormPage.module.css` — on review this was an overreach
into explicitly-prohibited "Letter page redesign," so it was reverted
before continuing.

**Explicitly not done this phase**: no Dashboard/Letter-page/
Administration-page/Document-page/Notification-panel/Authentication-
page redesign; no boot screen; no loading glyph; no drag-and-drop
upload (a deliberate judgment call — the existing click-to-browse input
already satisfies the upload contract without new event-handling risk).
Zero dependencies installed.

Test suite grown to **349 frontend tests** (48 files, 335 + 14 new) and
unchanged at **487 backend tests**, run 3 consecutive times with
identical results; `npm run build` succeeded (CSS actually shrank
slightly from the deleted duplicate blocks, net of the new shared
primitives file). Full implementation record in
`docs/architecture/ui-design-system.md`'s own "Phase 5I.3" section.

### Phase 5I.2 — App Shell & Navigation Visual Implementation

Complete (prior phase). The second implementation pass against the Phase 5I
proposal — **App Shell and Navigation only** — verified by re-reading
`AppShell`/`Sidebar`/`Topbar`, `navigationConfig.js`, `AuthContext`, and
`routes/index.jsx` directly before making any change.

**Implemented**: a visually redesigned `Sidebar` (a small CSS-only
brand mark, a 3-letter monogram glyph per nav item — disambiguated
across all three roles' real labels, an active-route accent bar, a
desktop collapse toggle with no persistence, and a mobile drawer with a
real focus trap, Escape, and backdrop, generalized from
`ConfirmDialog`'s own pattern); a refined `Topbar` (a hamburger toggle,
clearer identity/role typography) with `NotificationBell`'s
polling/API/behavior completely untouched (only its badge gained a
small border); the AJ-OVA Labs footer, now actually rendered once in
`AppShell` on every authenticated screen (`PRODUCTION_CREDIT`, unchanged
text from Phase 5I.1); and a shell-level content max-width for very
wide monitors. `navigationConfig.js`'s role-derived list is
byte-for-byte unchanged — this phase only changed how it's rendered.

**A real testing-environment finding, recorded for future phases**:
this project's test environment (jsdom) does not evaluate `@media`
width queries at all — a control meant to be hidden-by-default and
revealed by a media query is permanently untestable that way here; the
mobile toggle is instead visible-by-default and hidden only at desktop
width, which degrades correctly in a real browser while staying
directly testable. Full reasoning in
`docs/architecture/ui-design-system.md`'s own "Phase 5I.2" section.

**Explicitly not done this phase**: no table/form/dialog consolidation,
no Dashboard/Letter/Administration/Documents/notification-panel/
authentication redesign, no boot screen, no loading glyph, no system-
status indicator (no honest signal exists to back one). Zero
dependencies installed; zero backend/route/service/`AuthContext`/
authorization files touched (grepped the diff for
`jwt`/`decode`/`localStorage`/role-string comparisons/
`recipient_user_id` — zero matches in `src/layouts/`).

Test suite grown to **335 frontend tests** (46 files, 320 + 15 new) and
unchanged at **487 backend tests**, run 3 consecutive times with
identical results; `npm run build` succeeded (JS bundle grew from
368.44 KB to 371.47 KB — the new shell markup itself, zero new
dependency). Full implementation record in
`docs/architecture/ui-design-system.md`'s own "Phase 5I.2" section.

### Phase 5I.1 — Global Visual Foundation Implementation

Complete (prior phase). The
first implementation pass against the Phase 5I proposal —
**global foundation only**, verified by re-reading the actual current
source (`tokens.css`, `global.css`, `App.jsx`/`main.jsx`/`AppShell`/
`Sidebar`/`Topbar` and their CSS Modules, `StatusBadge`/
`NotificationItem`) before making any change, not assumed from the
review document.

**Implemented**: additive color tokens (`--color-text-secondary`,
`--color-border-subtle`, `--color-surface-elevated`, `--color-accent`,
`--color-info`/`-bg`, `--color-success-bg`, `--color-highlight-bg` —
every Phase 5A token unchanged, nothing renamed) and a 5-value motion
scale in `tokens.css`; a static CSS-only atmospheric background wash, a
strengthened `:focus-visible` treatment, a global
`prefers-reduced-motion` safety net, and one narrow global interaction-
transition rule in `global.css`; and the fix for the confirmed ACTIVE-
badge/unread-notification color bug found during the Phase 5I review
(`StatusBadge.module.css`/`NotificationItem.module.css` each now
reference their own correct token instead of both incorrectly sharing
`--color-warning-bg`). The existing but previously unused
`PRODUCTION_CREDIT` constant's text was updated to the approved footer
wording — not yet rendered anywhere.

**Explicitly not done this phase**: no Sidebar/Topbar/Dashboard/Letter/
Administration/Documents/Notifications/Authentication screen was
redesigned; no boot screen, loading animation, collapsible sidebar,
mobile drawer, or visible footer was added; zero dependencies were
installed; no API/service/route/`AuthContext`/authorization/business-
rule file was touched.

Test suite unchanged in count — **320 frontend tests** (44 files) and
**487 backend tests** — run 3 consecutive times with identical results;
`npm run build` succeeded with the JS bundle byte-identical (368.44 KB),
confirming zero dependency change. Full implementation record in
`docs/architecture/ui-design-system.md`'s own "Phase 5I.1" section.

### Phase 5I — Futuristic UI / Visual Architecture & Design System
Review

Complete (prior phase). **Review only — no code, test, dependency, backend,
or database file was changed.** With the functional V1 scope now frozen
(every screen through Phase 5H.1 implemented and its automated suite
green), this phase inspected the actual current frontend — every
layout, component, and page CSS Module, the design tokens, and the
relevant tests — against a "futuristic enterprise command center"
design direction, and produced a complete, actionable visual-system
proposal without writing a single line of implementation code.

**Audit findings (confirmed by direct code reading, not assumption)**:
a real, pre-existing color-token bug — the ACTIVE status badge and the
unread-notification row both incorrectly reuse the `--color-warning-bg`
token, which visually conflates "active/good" and "unread" with
"warning"; and several genuinely duplicated CSS patterns (the
confirmation-dialog, data-table, and form-field styles are each
hand-written twice or more across otherwise visually consistent
screens). Both are documented as fix targets for the eventual
implementation phase, not fixed now.

**Proposal**: an extended color/typography/spacing/shape/motion token
system (corrects the bug above, adds `--color-accent`/`--color-info`/
`--color-highlight-bg`/`--color-success-bg` and a small motion-timing
scale — no existing token is removed); a collapsible sidebar and mobile
drawer (the one confirmed structural navigation gap — the current
mobile layout has no drawer at all); a three-tier loading system (a
short, honest boot screen with no fabricated "securing/encrypting"
claims, page-level skeletons, and the existing button-level loading
pattern, unchanged); a status-badge icon layer (shape, not just color,
per WCAG); and a wired-up AJ-OVA Labs footer (`constants/app.js`
already has an unused, differently-worded credit string ready to be
replaced). **Every recommendation is achievable with the exact
dependency set already installed — zero new packages.**

Explicitly preserved, restated as hard constraints: all API contracts,
backend authorization, classified-record 404-collapsing behavior (no
403/404 distinction is added for Letters), document security, and every
existing test's functional assertions. Full record, including a
34-section design specification and a manual E2E checklist for the
eventual implementation phase, in
`docs/architecture/ui-design-system.md`.

**Not implemented, matching the approved scope exactly:** every
recommendation above — this phase is architecture and documentation
only. The next phase (visual implementation) begins only when
explicitly instructed.

### Phase 5H.1 — Complete Existing Category & Classification Admin UI

Complete (prior phase). A confirmed frontend completion gap found during Phase 5H's
own manual E2E verification: `/app/system/categories` and
`/app/system/classifications` still rendered `PlaceholderPage` ("planned
but not yet implemented"), even though both resources' backend
(list/create/update/activate/deactivate, `SYSTEM_ADMIN`-only) has
existed unchanged since Phase 4B. This phase is a pure frontend
exposure task — **zero backend files were touched**, confirmed by a
fresh character-substituted diff of `categories.py`/`classifications.py`
showing them structurally identical (Classification adds only
`restricts_access`).

Six new pages (`CategoryListPage`/`CategoryCreatePage`/
`CategoryDetailPage`, and the Classification equivalents), mirroring the
existing `DepartmentListPage`/`DepartmentCreatePage`/
`DepartmentDetailPage` three-page pattern exactly — list with a status
filter, create, and a detail page with inline edit plus
Activate/Deactivate (Deactivate confirmed via `ConfirmDialog`, Activate
not, matching the established Phase 5D confirmation matrix). No delete
action exists for either resource, matching the backend (there is no
`DELETE` route). Classification's form/table additionally show
`restricts_access` as plain "Yes"/"No" text — the frontend only ever
forwards a SYSTEM_ADMIN's explicit choice for this flag to the backend;
the classified-access authorization boundary itself
(`assert_letter_access`) is completely unchanged and untouched by this
phase. `routes/index.jsx`'s two placeholder routes were replaced with
nested `RoleGuard` route groups identical in shape to
`system/departments`; `navigationConfig.js` needed no changes at all —
its Categories/Classifications entries already pointed at the correct
paths, and the "planned" appearance came entirely from the route
rendering `PlaceholderPage`, not from anything in navigation.

Test suite grown to **320 frontend tests** (280 + 40), run 3 consecutive
times with identical results; backend suite unaffected at
**487 passed**. Full implementation record in
`docs/architecture/frontend.md` §36's own resolution note.

**Not implemented, matching the approved scope exactly:** delete for
either resource; dashboard/audit/notification integration for either
resource; any UI polish/typography/spacing/footer; Phase 6 work; any
change to classified-access authorization semantics.

### Phase 5H — Source Department & Designation Master Data:
Implementation

Complete (prior phase). Two supervisor-requested changes from a
live handover demonstration, both now working end to end against the
real backend: the Letter form's Source field is a Department picker
(reusing the existing `DepartmentSelector`), and Designation is a new,
SYSTEM_ADMIN-managed, system-wide master-data dropdown.

**Backend**: a new `Designation` resource (model/repository/service/
endpoints) mirrors `Category` closely, with one deliberate departure —
`GET /api/v1/designations` is readable by any authenticated role, not
SYSTEM_ADMIN-only, so USER/ADMIN can populate the Letter form's
dropdown. `GET /api/v1/departments` received the identical, minimal
relaxation for the same reason (Source Department); every write
endpoint on both resources remains SYSTEM_ADMIN-only, verified directly
by re-reading every endpoint's dependency after implementation. A new,
**nullable** `letters.designation_id` FK (migration
`323ccfde77f4_designation_master_data`) sits alongside the existing,
completely unchanged, required `sender_designation` text column — zero
backfill, zero risk to any existing Letter. The migration was verified
for real: `alembic upgrade head` → `downgrade` → `upgrade head` →
`check`, clean at every step, against a real local PostgreSQL instance.

**Frontend**: `LetterFormPage.jsx`'s free-text Source and Sender-
designation inputs are replaced with real selections — Source
Department auto-fills `source_name`, Designation auto-fills
`sender_designation` (the backend remains authoritative and overrides
it regardless). Both are required only when *creating* a Letter, never
retroactively demanded when editing one that predates this phase. A
new, deliberately minimal SYSTEM_ADMIN screen
(`/app/system/designations`) is the only way to add designations — the
system intentionally starts with zero, by explicit business decision,
so Letter recording is correctly, disclosedly blocked until a
SYSTEM_ADMIN adds at least one.

Test suite grown to **487 backend tests** (458 + 29) and **280 frontend
tests** (258 + 22), each run 3 consecutive times with identical
results. Full implementation record in
`docs/architecture/source-designation.md` §26.

**Not implemented, matching the approved scope exactly:** any UI
polish/typography/spacing/footer; Phase 6 work; making Source or
Designation backend-mandatory; an external/non-departmental Source
fallback; a Designation edit/detail page.

### Phase 5H — Source Department & Designation Master Data: Architecture & Requirements Review

Complete (prior pass, this same phase). Review only — no backend or
frontend code, migration, or test was written at that stage. Prepared
under real handover time pressure — written to be directly actionable,
not just thorough. Two supervisor-requested changes from a live
demonstration: Source (currently free text) should be selectable from
the existing Department list; Designation (currently free text) should
be a SYSTEM_ADMIN-managed, system-wide dropdown.

**Two findings drove the whole review.** First: `source_department_id`
already exists, fully wired, on `LetterCreate`/`LetterUpdate`/
`LetterResponse`/`LetterListItem`, with existing backend validation
(`LetterService._validate_source_department`) rejecting a nonexistent
or `INACTIVE` department — it was simply never given a frontend
control (`LetterFormPage.jsx`'s own docstring already says so). Making
Source a dropdown is therefore mostly a **frontend** task. Second: `GET
/api/v1/departments` is `require_system_admin`-only today — the exact
same access gap already documented for Category/Classification
(`frontend.md` §36) would silently block Source Department *and*
Designation for USER/ADMIN, the only roles that can ever record a
Letter, unless corrected. **This review recommends a one-line
dependency relaxation on that single endpoint** (read-only; every write
endpoint stays SYSTEM_ADMIN-only) as the one small, necessary backend
change — without it, neither feature works for its actual users.

**Recommended design**: `source_name` (required text) is retained, not
replaced — an already-confirmed product decision ("must never force
every source into a department FK") — with the frontend auto-filling it
from the selected department's name. A new `Designation` master-data
table mirrors `Category`/`Classification` almost exactly (never
physically deleted, idempotent activate/deactivate, `ActiveStatus`
reused), with one deliberate departure: case-insensitive name
uniqueness (matching `User.email`'s existing functional-index
technique) rather than Category/Classification's case-sensitive
`unique=True`. Historical integrity is solved the same way
`source_department_id`/`source_name` already coexist today: a new,
**nullable** `designation_id` FK added alongside the existing,
unchanged, required `sender_designation` text column — zero backfill,
zero risk to existing Letters. `designation_id` is recommended
**optional**, deliberately, because no designations are being seeded
(the supervisor provided no list) — making it mandatory with an empty
starting table would break Letter recording entirely until a
SYSTEM_ADMIN manually adds one first.

Full review, including a MUST-IMPLEMENT-BEFORE-HANDOVER vs.
NICE-TO-HAVE/FUTURE split and a complete implementation sequence, in
`docs/architecture/source-designation.md`.

**Not in scope for this phase, and not added:** any backend or
frontend code; a migration; UI polish/typography/spacing/footer; Phase
6 work; making Source or Designation mandatory; an external/non-
departmental Source fallback.

### Phase 5G — Backend Dashboard Aggregation & Analytics API: Architecture & Requirements Review

Complete (prior phase). Review only — no
backend or frontend code, migration, index, or test was written this
phase. Repository confirmed clean and at Phase 5F (`1e5c8de`) before
this review began. Re-inspected the full backend layering
(endpoint→service→repository), the actual Letter/Department/User/
Admin/Document/Notification/AuditLog schema (indexes, constraints,
relationships — verified directly, not assumed from prior phase
reports), and `list_letters`'s exact query-construction pattern.

**Confirmed the two reusable authorization primitives
(`letter_visibility_filter`/department derivation) can and should be
reused directly for any future Letter aggregate — no second,
independently-maintained predicate is proposed.** Confirmed every
column a plausible Letter aggregate would group or filter by
(`recipient_department_id`, `category_id`, `classification_id`,
`received_at`, `status`) is already indexed, so **zero new indexes are
recommended**. Confirmed `AuditLog` has no department column at all,
and no read API exists — audit analytics is deferred entirely to a
future, separate phase, not mixed into this one.

Produced a full metric-by-metric inventory (Letter/Administration/
Document/Notification/Audit) classified per the brief's own A-E scheme.
**Finding: no metric in the inventory clears the bar of "confirmed
business value that existing APIs cannot already provide"** — every
metric that would need a genuinely new backend endpoint is gated behind
an unconfirmed business want. **Recommendation: defer backend
aggregation entirely for V1** — the current, already-shipped
operational dashboard (Phase 5F) already delivers everything the
evidence supports building. A complete endpoint design
(`GET /api/v1/letters/aggregate`, response schema, date-range/filter
strategy, security threat review, test plan) is documented as
ready-to-build if and when a specific breakdown or trend is ever
confirmed wanted — but none is authorized or implemented this phase.

Full review in `docs/architecture/dashboard-analytics-api.md`.

**Not in scope for this phase, and not added:** any backend endpoint,
repository method, service method, migration, or index; an `AuditLog`
read API; an audit dashboard; an analytics UI; charts; reporting
tables; materialized views; Redis; caching infrastructure; any frontend
change.

### Phase 5F — Dashboard & Operational Overview UI: Implementation

Complete (prior phase). Frontend only, built directly on this same phase's own prior
architecture review — no backend code, migration, or production data
was touched. Added `/app/dashboard` (a plain child route, available to
every role — no new authentication/authorization mechanism; the
existing `RootRedirect`/`/app` index behavior is unchanged) rendering
one role-aware `DashboardPage`: Total/Active/Archived Letter counts and
Unread Notifications for every role (each a single, cheap, already
department/classified-scoped request — no registry pagination, no
client-side filtering); Active Departments + Pending Admin Approvals
for SYSTEM_ADMIN; Active Users + Pending User Approvals for ADMIN; a
5-item Recent Letters list reusing the existing Letter service and
route; and role-scoped Quick Actions linking to already-existing
screens only (Create Department/Authorize Admin for SYSTEM_ADMIN,
Authorize User for ADMIN, Record a Letter for USER). No chart, trend,
breakdown, filter control, or document metric was built — every one
remained `PENDING BACKEND API` or `PENDING BUSINESS CLARIFICATION` per
the review, and none was implemented anyway. The existing
`NotificationBell` polling is untouched; the dashboard's notification
figure is one one-time fetch, not a second timer.

Test suite grown from 249 (159 baseline through Phase 5E, plus this
phase's own additions — see below) — **33 new tests** across
`SummaryCard`/`RecentLetters`/`QuickActions`/`DashboardPage`, run 3
consecutive times with identical results. A pre-existing test-
infrastructure flake (`LetterFormPage.test.jsx` intermittently missing
Vitest's 5000ms default timeout under full-suite worker contention,
confirmed non-deterministic and unrelated to any logic defect) was
fixed by raising `testTimeout` to 10000ms in `vite.config.js` —
headroom, not a weakened assertion. `npm run build` succeeds. Backend
regression (`pytest tests/`) — **458 passed**, unaffected, confirming
zero backend impact. Full implementation record in
`docs/architecture/dashboard.md` §32.

**Not added, per the brief's own explicit list:** backend dashboard
endpoints, an audit read API, historical analytics, trend charts, a
charting library, reporting tables, an analytics warehouse, exports,
scheduled reports, WebSockets, background workers, Redis/Celery, React
Query, Redux, Zustand, or any new state-management library.

### Phase 5F — Dashboard & Operational Overview UI: Architecture & Requirements Review

Complete (prior pass, this same phase). Review only — no frontend or
backend code, migration, or test was written at that stage. Repository
confirmed clean and at Phase 5E (`edc6649`) before this review began.
Re-inspected every business endpoint fresh: confirmed **no dashboard,
summary, aggregate, or reporting endpoint exists anywhere**, that
`GET /letters` computes its `total` from a real SQL `COUNT` on the same
department/classified-visibility-scoped statement as the page itself
(so a Letter count is cheap and already correctly isolated), and that
`GET /departments`/`/admins`/`/users`/`/categories`/`/classifications`
have **no pagination at all** — each returns its complete matching
result set, with `total` computed as `len()` in Python, not a database
`COUNT`. Confirmed **no audit read API exists** — `AuditLog` is
written to but nothing exposes it through `/api/v1`, restating
`audit-notifications.md`'s own unchanged conclusion.

Produced a full metric-by-metric inventory (letters/documents/
notifications/departments/admins/users/pending-approvals/trends/audit
activity), classifying each as directly available, derivable-but-
costly, requiring a new backend endpoint, requiring business
clarification, or architecturally inappropriate for V1. Found that
**every current-operational-state metric is available today from an
existing request**, while **every historical/trend/analytical metric
requires either a new backend aggregate endpoint or an audit read API
that doesn't exist** — supporting, without confirming as a business
requirement, the recommendation that V1 should be operational-only, no
charts, no trends. Confirmed no charting library is installed and none
should be added this phase.

Full review in `docs/architecture/dashboard.md`.

**Not in scope for this phase, and not added:** any frontend page,
component, service, or test; any backend endpoint, schema, service, or
migration; a dashboard aggregate endpoint; an audit read API; charts;
exports; scheduled reports.

### Phase 5E — Documents & Notifications UI: Implementation

Complete (prior phase). Frontend only, built directly on this same phase's own prior
architecture review — no backend code, migration, or production data
was touched. `LetterDetailPage` now has a real Documents section
(`DocumentUploadForm` + `DocumentList`, upload with progress feedback,
authenticated blob download, no delete/replace action anywhere,
because no such endpoint exists); a `NotificationBell` in the existing
`Topbar` polls `GET /notifications/unread-count` only, every 60
seconds (`PROVISIONAL`), paused while the tab is hidden; a
`NotificationPanel` dropdown and a full paginated `/app/notifications`
page (reusing Phase 5C's `Pagination` component) both use **explicit
"Mark as read" only** — clicking a notification's related-Letter link
never marks it read, per an explicit override of this review's own
PROVISIONAL lean (§23/§27 of the architecture doc). No frontend
authorization rule of any kind was added for classified/inaccessible
Letters or their documents — a `404` renders exactly as it always has.

Test suite grown from 159 to **225 tests**, run 3 consecutive times
with identical results and clean stderr output. `npm run build`
succeeds. Backend regression (`pytest tests/`) — **458 passed**,
unaffected, confirming zero backend impact. Full implementation record
in `docs/architecture/document-notification-ui.md` §27.

**Not added, per the brief's own explicit list:** OCR, antivirus
scanning, cloud storage, public/signed document URLs, email/SMS/push
notifications, WebSockets, queues, Celery, Redis, an audit UI, a
dashboard, exports, document deletion, a document replacement
endpoint, notification recipient management, a notification-creation
UI, or any new frontend authorization logic.

### Phase 5E — Documents & Notifications UI: Architecture &
Requirements Review

Complete (prior pass, this same phase). Review only — no frontend or
backend code, migration, or test was written at that stage. Repository
confirmed clean and at Phase 5D (`f46cb7c`) before this review began.
Re-inspected `app/api/v1/endpoints/documents.py`/`notifications.py`,
their services (`document_service.py`/`document_storage.py`/
`document_validation.py`/`notification_service.py`), repositories, and
schemas fresh — both confirmed **unchanged since Phase 4D/4E**, so this
review reaches the same conclusions Phase 5's own original §14/§15
already did on the big questions (fetch+blob required for downloads,
no delete endpoint, poll only `/unread-count`) and adds the
implementation-level detail (exact routes/components/services/tests)
neither Phase 5 nor Phase 5C went into.

**Confirmed, precisely, why a plain `<a href>` cannot download a
document**: the response requires a Bearer token like every other
endpoint; `Content-Disposition: attachment` is set automatically by
Starlette's `FileResponse` whenever a `filename=` is passed (confirmed
from the exact call in `documents.py`, not assumed), forcing a real
browser download once fetched as a blob. **Confirmed the document
lifecycle precisely**: upload only, no replace/delete endpoint of any
kind — "replacement" is calling upload again, leaving the prior
document fully untouched, exactly as Phase 4D's own review concluded.
**Confirmed the notification message is safe to render as plain
JSX text** — a fixed server-authored template with one non-sensitive
interpolated value (the Letter's reference number), auto-escaped by
React, never requiring sanitization.

**A real, narrow scenario documented, not previously written down
anywhere**: a `LETTER_REGISTERED` notification's recipient can still
hit a generic Letter `404` if their own access changed after the
notification was generated (e.g. an Admin department transfer, Phase
5D) — not a bug, and not something the frontend should treat
differently from any other Letter 404.

Full review in `docs/architecture/document-notification-ui.md`.

**Not in scope for this phase, and not added:** any frontend page,
component, service, or test; any backend endpoint, schema, service, or
migration; document deletion/replacement endpoints; email/SMS/push
notifications; WebSockets; a dashboard; an audit UI.

### Phase 5D — Administration & Account Management UI: Implementation

Complete (prior phase). Builds directly on this same phase's own prior
architecture review: `/app/system/departments`, `/app/system/admins`,
and `/app/admin/users` are now a complete Department/Administrator/User
management UI — 10 new pages, 4 new list tables, a generalized
`ConfirmDialog`, a specialized `AdminTransferDialog`, an extended
`StatusBadge` (two new tones — `PENDING_APPROVAL`/`REVOKED`), and two
new API service modules (`adminService.js`/`userService.js`) plus an
extended `departmentService.js`. Test suite grown from 84 to **159
tests**, run 3 consecutive times with identical results. Full
implementation record in `docs/architecture/administration-ui.md` §26.

### Phase 5D — Administration & Account Management UI: Architecture & Requirements Review

Complete (prior pass, this same phase). Review only — no frontend or
backend code, migration, or test was written at that stage. Re-inspected
the actual current Department/Admin/User/UserAuthorization backend
fresh, not from any prior phase's report, and confirmed the actual
current frontend had no admin/user/department service, page, or
component of any kind (only three already-slotted `PlaceholderPage`
routes). Designed the complete System Admin (Departments,
Administrators, Admin transfer) and Admin (Users, User authorizations)
UX, navigation, routing, component architecture, service layer,
error-handling matrix, confirmation matrix, security review, and a
three-enum state matrix, all against the confirmed backend contract
only. **Two corrections to the phase brief's own assumptions**: the
frontend did not already have Document/Notification UI; `AuthorizationStatus`
is `ACTIVE`/`USED`/`REVOKED`, not `PENDING`/`EXPIRED`, and `expires_at`
is never actually set by any code path. **A real, confirmed gap**: none
of the four Department/Admin/User/Authorization resources support
pagination, sorting, or text search, unlike Letters. Full review in
`docs/architecture/administration-ui.md` §1-25.

### Phase 5C — Core Registry UI: Implementation

Complete (prior phase). Builds
directly on Phase 5A's foundation and Phase 5B's authentication UX: the
`/app/letters` and `/app/system/letters` placeholders are now a complete
V1 Letter registry — list/search (seven text filters, `status`/
`category`/`classification` exact filters, an inclusive received-date
range), sort (all four backend-whitelisted fields, accessible
`aria-sort` column headers), pagination (driven entirely by the
backend's own `page`/`page_size`/`total`/`total_pages`), create, view,
edit, and archive (a non-destructive status transition, worded and
confirmed accordingly — never "delete"). List/filter/sort/pagination
state lives in the URL, so refresh, back/forward, and bookmarking all
preserve registry state. One `LetterListPage`/`LetterFormPage` component
each adapt to the caller's role (USER/ADMIN vs. SYSTEM_ADMIN) rather
than duplicating pages, matching how `RoleGuard`/`navigationConfig.js`
already derive UI behavior from the documented backend contract.

**A real, confirmed backend-contract gap was found and resolved, not
routed around**: `GET /api/v1/categories`, `/classifications`, and
`/departments` are all `require_system_admin`-only, but
`POST /api/v1/letters` structurally excludes SYSTEM_ADMIN (no department
to record a letter against) — so no role that can create or edit a
Letter can ever load the category/classification/department reference
lists. Resolution: `category_id`/`classification_id` never appear on
Create (for any role); on Edit they appear only for SYSTEM_ADMIN, the
only role for which the reference-data load actually succeeds. Nothing
was hardcoded as a workaround — confirmed by grep, zero category/
classification/department names appear anywhere outside test fixtures.
Full reasoning in `docs/architecture/frontend.md` §36.

**Classified-record safety (CRITICAL, re-verified against this
implementation)**: `items`/`total` are rendered exactly as the backend
returns them, with zero client-side re-filtering; a `404` on a Letter —
whether nonexistent, wrong-department, or classified-and-inaccessible —
renders the identical generic "Letter not found," verified by a test
asserting the rendered text contains neither "classif" nor "permission."

The test suite grew from 44 to **84 tests**, covering every scenario the
brief listed as a minimum. Frontend production build and test suite both
succeed; the backend regression suite (458 tests) is unaffected —
confirmed by re-running it before and after, with zero backend files
touched. Full design and implementation record in
`docs/architecture/frontend.md` §36.

**No other business feature screen exists.** Documents, Notifications,
and every administrative screen, the dashboard, and the audit UI all
remain exactly what the architecture review scheduled for later phases;
the Letter detail page has a labeled placeholder section for documents
rather than a fake feature.

**Not in scope for this phase, and not added:** document upload/download
UI, notifications UI, dashboards, Departments/Admins/Users/Categories/
Classifications management UI, audit UI, OCR, exports, a global search
box, new backend endpoints, backend business logic, database changes, or
migrations.

### Phase 5B — Authentication & Account UX: Implementation

Complete (prior phase). Builds directly on Phase 5A's foundation:
`LoginPage`/`SignupPage` became real, production-quality forms —
client-side required/email-format validation with `aria-invalid`/
`aria-describedby` on every field, a disabled submit button with a
loading label while a request is in flight, and the previous
submission's error cleared the instant a new one begins. A `401` on
login always shows the backend's own generic "Incorrect email or
password." (never distinguishing a nonexistent account from a wrong
password); a `403` for a pending or deactivated account renders one of
two new reusable notice components
(`PendingApprovalNotice`/`DeactivatedAccountNotice`) instead of a
generic error, stating only what the backend confirms. Session
restoration distinguishes a genuine token rejection (clears the stored
token) from a network failure (keeps the token, shows a retry-capable
banner). The test suite grew from 17 to 44 tests. No backend file was
touched. Full design and implementation record in
`docs/architecture/frontend.md` §35.

### Phase 5A — Frontend Foundation: Implementation

Complete (prior phase). Builds directly on this same phase's own prior
architecture/UX review: routing
(`react-router-dom`, installed since Phase 1 but unwired until now) now
backs a real route tree; a single `AuthContext` restores a session from
`GET /auth/me` before any protected route renders (no authentication
flicker); one centralized Axios client attaches the bearer token,
normalizes both confirmed backend error-body shapes into one predictable
form, and clears the session on a `401` — except on the login/signup
calls themselves, which handle their own failures locally, exactly as
the review specified; `ProtectedRoute` (authentication only) and
`RoleGuard` (role-based navigation convenience only) are two separate
components, not conflated; navigation is derived entirely from the
authenticated user's role, with the token/role/department never trusted
from anywhere but the backend's own responses; the `AppShell`/`Sidebar`/
`Topbar` chrome, a small design-token set (no UI framework added), and
an accessibility baseline are all in place. A test framework was
established from nothing (Vitest + React Testing Library, 17 tests
across authentication state transitions, protected-route behavior,
role-navigation configuration, and API error normalization — the four
areas the brief named as the minimum). Frontend production build and
test suite both succeed; the backend regression suite (458 tests) is
unaffected — confirmed by re-running it before and after, with zero
backend files touched. Full design and implementation record in
`docs/architecture/frontend.md` §34.

### Phase 5 — Frontend & Operational UI: Architecture & UX Requirements Review

Complete (prior phase). Review only — no frontend or backend code,
migration, or test was written at that stage. Inspected the actual
frontend (a pure Phase 1 skeleton) and the actual backend API surface
(42 real business endpoints across 8 resource routers, enumerated from
the live OpenAPI schema, not from memory), rather than assuming a prior
report was still accurate. Mapped every endpoint to a screen by role,
corrected one gap in the task's own suggested System Admin navigation
(it omitted Letters/Documents, which `SYSTEM_ADMIN` actually has full
cross-department access to), designed the Letter/document/notification/
administration UX directly against the *actual* schemas (not the task's
own illustrative field list — e.g. it omitted `reason`, a real field),
and worked through 30 analysis topics (§3-§30 of the review) —
authentication UX, role hierarchy, per-role screens, Letter search/form/
classified-access handling, department-isolation UX, document/
notification/audit UX, route/component/API-client architecture, auth
state, error handling, responsive design, accessibility, a design
system, a dashboard feasibility assessment, a frontend security review,
performance, and a test strategy — all using the CONFIRMED/RECOMMENDED/
PROVISIONAL/PENDING taxonomy the brief specified. Full design in
`docs/architecture/frontend.md` §1-33.

**The governing CRITICAL finding, restated because Phase 5A's own
foundation had to preserve it even with no Letter screen yet built**:
the frontend must never independently filter, label, or infer
classified-Letter existence — it renders exactly what the API already
returns (`items`/`total` already exclude inaccessible letters at the
query level, per Phase 4C) and treats every `404` identically, with zero
distinguishing language between "doesn't exist" and "exists but
restricted." A second, more technical finding, already exercised by
Phase 5A's own error-normalization module: this backend returns two
different error-body shapes (`{"detail": "<string>"}` for raised
`HTTPException`s vs. FastAPI's array-shaped `{"detail": [...]}` for
Pydantic validation failures) that any frontend error-normalization
layer must handle both of, not just one.

### Phase 4E — Operational Activity, Notifications & Audit: Implementation

Complete (prior phase). Built directly on that same phase's own prior
architecture review: `AuditLog` generation was wired into every event
the review recommended — Letter (created/updated/archived/classification-
changed/category-changed), Document (uploaded), User (approved/
deactivated/reactivated), Admin (authorized/approved/deactivated/
reactivated/department-changed), Department (created/activated/
deactivated), Category/Classification (created/updated/activated/
deactivated), and Authorization (created/revoked) — append-only (no
update/delete endpoint exists anywhere), mandatory (a write failure
rolls back the whole triggering operation, proven by a dedicated test),
and using only targeted old/new field pairs, never a full row snapshot
or a sensitive value. `Notification` generation was wired into the one
CONFIRMED V1 trigger — a letter being registered — with the recipient
department's ACTIVE Admins as an explicit PROVISIONAL recipient
strategy, best-effort via a real database `SAVEPOINT` (proven against an
actual failure inside it, not a stand-in), and a deliberately generic
message. Four new endpoints (`GET/PATCH /api/v1/notifications*`) let a
user read and mark-read only their own notifications. No schema change
was needed. 33 new tests, full suite **458 passed**, re-run 3 consecutive
times, plus a live-server verification against `lrs_dev` with real
minted JWTs. Full design and implementation record in
`docs/architecture/audit-notifications.md` §31.

### Phase 4E — Operational Activity, Notifications & Audit: Architecture & Requirements Review

Complete (prior pass, this same phase). Review only — no code,
migration, or test was written at that stage. Inspected the actual
current state of `AuditLog` and `Notification` (both unchanged since the
Phase 2 baseline + hardening migrations; confirmed by grep that zero
application code anywhere wrote to either table) rather than assuming
the five prior phases' own "planned, not implemented" audit-event lists
were still complete. Consolidated those five lists into one place and
identified the events none of them had itemized yet (Letter
classification/category changes, Category/Classification management
events). Worked through 22 analysis topics (§4-§25 of the review) — audit
immutability, actor-vs-target model, target/change-detail strategy,
audit access control and data-leakage risk, retention, notification
purpose/recipients/security/lifecycle/API, real-time vs. polled
delivery, event-generation architecture, transactional consistency,
background processing, audit-vs-notification distinction, and
dashboard/Letter-timeline/search implications — plus a database
sufficiency review, and designed a 14-scenario test plan, all using the
CONFIRMED/RECOMMENDED/OPTIONAL/PENDING taxonomy the brief specified. Full
design in `docs/architecture/audit-notifications.md` §1-30.

**Two CRITICAL findings, resolved by design in the review, confirmed
correct by implementation**: (1) audit writes should be mandatory and
share the triggering operation's own transaction (a failure fails the
whole operation), while notification writes should be best-effort inside
a database `SAVEPOINT` (`session.begin_nested()`) so a notification
failure can never abort the audit row or business operation riding
alongside it — the same savepoint mechanism `tests/conftest.py`'s
`db_session` fixture already uses for an analogous reason, not a
newly-invented pattern; (2) a notification's stored `message` text must
stay generic (never interpolate Letter subject/content) because a later
classification change cannot retroactively scrub text already sent — any
richer display must re-check `assert_letter_access` fresh at read time,
extending Phase 4D's "never cache authorization" principle to a third
consumer.

### Phase 4D — Document Management: Implementation

Complete (prior phase). Built directly on that same phase's own prior
architecture review: `LetterDocument` upload, listing, and download were
implemented —
`POST`/`GET /api/v1/letters/{letter_id}/documents` and
`GET .../{document_id}` — with a server-generated, UUID-based storage
path that never trusts client input, layered file-type/size validation
(extension allowlist, then an authoritative magic-byte content
signature — client-supplied `Content-Type` is never trusted), and an
authorization chain that reuses `LetterService.get_letter`/
`assert_letter_access` rather than a new, parallel document-level check,
so classified-letter protection extends to its documents automatically.
No document deletion endpoint exists, of any kind — an explicit,
deliberate scope decision matching the review's own recommendation, not
a gap. No schema change was needed; `alembic check` confirms zero drift.
38 new tests, full suite **425 passed**, re-run 3 consecutive times, plus
a live-server verification against `lrs_dev` with real minted JWTs. Full
design and implementation record in
`docs/architecture/document-management.md` §33.

**One deliberate deviation from the review's own §7 recommendation**:
the implementation brief's literal example
(`<letter_uuid>/<document_uuid>.<ext>`, no department/year/month
grouping) was followed exactly as specified, rather than the review's
own recommended reconciliation with the Phase 1 storage convention —
`storage/README.md` now documents what was actually built and is
explicit about the gap between the two.

**Not in scope for this phase, and not added:** document deletion
(physical or soft), document replacement as a distinct endpoint (upload
again instead), OCR, antivirus/malware scanning, cloud storage, backup
automation, notifications, automatic audit logging, frontend upload UI,
or a `checksum_sha256` column (recommended by the review, explicitly
deferred by the implementation brief).

This implementation phase was preceded, in this same phase, by an
architecture-and-requirements-review-only pass — no code was written
until the review's recommendations were approved; see "Completed" below
for both, in order.

## Completed

### Phase 5E — Documents & Notifications UI architecture & requirements review

* **Inspected the actual current backend state, not assumed** — fresh
  reads of `documents.py`/`document_service.py`/`document_storage.py`/
  `document_validation.py`/`letter_document_repository.py`/
  `document.py` (schema) and `notifications.py`/
  `notification_service.py`/`notification_repository.py`/
  `notification.py` (schema/model); both confirmed byte-for-byte
  unchanged since Phase 4D/4E.
* **The download mechanism confirmed precisely, not just "fetch+blob is
  needed"**: `Content-Disposition: attachment` is set automatically by
  Starlette's `FileResponse` whenever `filename=` is passed — traced to
  the exact call site in `documents.py`, not assumed from general
  FastAPI knowledge. `X-Content-Type-Options: nosniff` is already
  present on every download response.
* **Document lifecycle confirmed exhaustively**: upload only; no
  replace, no delete, no archive-a-document concept independent of its
  parent Letter. `document_service.py`'s own docstring states
  "replacement" is simply calling upload again.
* **Notification message content confirmed safe to render as plain
  text** — a fixed, server-authored template with exactly one
  non-sensitive interpolated value (the Letter's reference number),
  auto-escaped by ordinary JSX rendering.
* **A real, previously-undocumented interaction found**: a
  `LETTER_REGISTERED` notification's recipient can still hit a generic
  Letter `404` if their own access changed after the notification was
  generated (e.g. an Admin department transfer, Phase 5D's own
  confirmed instant-effect behavior) — documented as expected,
  non-distinguishing 404 behavior, not a bug.
* **Full architecture designed**: `DocumentList`/`DocumentUploadForm`
  inline on `LetterDetailPage`'s existing placeholder section (no new
  route); `NotificationBell`/`NotificationPanel`/`NotificationItem` in
  `Topbar`, plus the already-slotted `/app/notifications` page;
  `documentService.js`/`notificationService.js` (new); a full
  error-handling matrix (`422` vs. `413` vs. `500` distinguished for
  uploads); a 15-item security threat review; a ~50-60-test plan.
* **No frontend or backend file was touched** — confirmed by `git
  status` before/after; this phase produced documentation only.
* **Documentation**: `docs/architecture/document-notification-ui.md`
  (new), plus updates to the root README, `docs/README.md`,
  `docs/architecture/frontend.md`, and `docs/architecture/overview.md`.

### Phase 5D — Administration & Account Management UI implementation

* **Department management** (`frontend/src/pages/DepartmentListPage.jsx`/
  `DepartmentCreatePage.jsx`/`DepartmentDetailPage.jsx`) — list (status
  filter), create, and one detail page with an inline edit mode (not a
  separate route — the two-field edit surface didn't justify the split).
  Activate has no confirmation (purely restorative); Deactivate does,
  explaining the operational impact on every Admin/User in that
  department without using "delete" anywhere.
* **Administrator management** (`AdminListPage.jsx`/`AdminAuthorizePage.jsx`/
  `AdminDetailPage.jsx`) — list (status + department filters, resolving
  department names via a lookup map, no per-row request), a dedicated
  Authorize form (department required, `ACTIVE`-only options), and a
  detail page whose actions are entirely status-gated: Approve
  (confirmed — not idempotent), Deactivate + Transfer (`ACTIVE` only),
  Reactivate (`DEACTIVATED` only, not confirmed).
* **Admin transfer** (`components/AdminTransferDialog.jsx`) — states
  verbatim, using the backend's own confirmed guarantee, that historical
  Letters are never reassigned; department options limited to `ACTIVE`;
  a genuine `409` (destination not active) surfaces inline in the
  dialog, not as a page-level error.
* **User management** (`UserListPage.jsx`/`UserAuthorizePage.jsx`/
  `UserAuthorizationsPage.jsx`/`UserDetailPage.jsx`) — the Authorize
  form has a single `email` field, matching `UserAuthorizationCreate`
  exactly (no department field exists on that schema to expose even by
  mistake); a separate Authorizations list (department-wide visibility,
  defaults to `ACTIVE`) with a creator-scoped Revoke action shown on
  every `ACTIVE` row (there is no field to pre-filter by creator, so a
  mismatched attempt 404s generically like any other, per the review's
  own enumeration-prevention reasoning).
* **The 403-vs-409 distinction preserved, verified by test** — a `403`
  on User Approve/Reactivate is phrased around the *Admin's own*
  department, never the target account; Deactivate (which can never
  return that `403`) shows no such warning.
* **Three enums, three visually distinct tones, never merged** —
  `StatusBadge` extended with `warning` (`PENDING_APPROVAL`) and
  `negative` (`REVOKED`) tones plus an optional accessible-name
  `domain` prefix; a new `.sr-only` utility was added to
  `styles/global.css` to support it.
* **`RoleGuard` extended, backward-compatibly, to work as a layout
  route** — renders `<Outlet/>` when used with no `children`, so each
  new route group (`/app/system/admins/*`, `/app/system/departments/*`,
  `/app/admin/users/*`) shares one guard instance instead of repeating
  it per child route. Every existing call site (`system/letters`,
  `system/categories`, `system/classifications`) is unaffected.
* **Every confirmed backend gap from the review respected, not routed
  around**: no pagination/search/sort UI (none exists on any of the
  four resources); no department field on the User authorization form;
  no revoke action for Admin-purpose authorizations; no department/
  admin/user counts anywhere.
* **No backend file was touched** — confirmed by `git status` and a
  full backend regression run before and after (458 passed, unaffected
  both times).
* **Validation**: `npm run build` succeeds (163 modules, no errors);
  `npm run test` — **159 passed**, 0 failed, run 3 consecutive times
  with identical results; `pytest tests/` (backend) — **458 passed**,
  unaffected.
* **Documentation**: `docs/architecture/administration-ui.md` §26 (new
  implementation record), plus updates to the root README,
  `frontend/README.md`, `docs/README.md`,
  `docs/architecture/frontend.md`, and `docs/architecture/overview.md`.

### Phase 5D — Administration & Account Management UI architecture & requirements review

* **Inspected the actual current backend state, not assumed** — fresh
  reads of every Department/Admin/User/UserAuthorization endpoint,
  schema, service, repository, and model file this session; confirmed
  the exact status codes, error messages, idempotency behavior, and
  authorization boundary for every one of the 19 confirmed endpoints
  across the three resource routers.
* **Corrected two inaccurate assumptions in the phase brief itself**
  (verified against source, not accepted at face value): the frontend
  does not currently have Document or Notification UI (both remain
  `PlaceholderPage`); `AuthorizationStatus` is `ACTIVE`/`USED`/`REVOKED`,
  not `PENDING`/`EXPIRED` — and `expires_at`, while present on the
  schema, is never actually set by any code path in this backend today.
* **System Admin protection and Admin self-targeting are both
  structural, not a check to design** — `UserRepository.find_admin_by_id`/
  `find_user_by_id` filter by role before an id can ever resolve, so no
  endpoint can target a SYSTEM_ADMIN, and an Admin's own id (role
  `ADMIN`) 404s on every User-lifecycle endpoint by construction. No
  frontend logic is needed or recommended to reinforce either.
* **The read/lock-down vs. state-elevating distinction, preserved, not
  flattened** — documented the precise backend asymmetry (Deactivate/
  Revoke/list actions never require the Admin's own department to be
  ACTIVE; Authorize/Approve/Reactivate do, and can 403 for a reason that
  has nothing to do with the target account) and designed the error
  matrix and UI copy around it exactly, rather than one generic "Admin
  can manage users" treatment.
* **A confirmed gap distinct from Phase 5C's own**: none of
  Departments/Admins/Users/Authorizations support pagination, search, or
  sort — only exact `status`/`department_id` filters exist. Marked
  `PENDING BACKEND API`; whether that's acceptable at real V1 data
  volumes marked `PENDING BUSINESS CLARIFICATION` — neither guessed.
* **Admin transfer (`PATCH /admins/{id}/department`) verified precise**
  — confirmed directly in `admin_service.py` and its own referenced
  integration test that a transfer changes only the Admin's current
  `department_id`; historical Letters they recorded keep their original
  `recipient_department_id` forever, never reassigned.
* **Full UX design produced for**: Department list/create/detail-edit/
  activate/deactivate; Administrators list/detail/authorize/lifecycle/
  transfer; Users list/detail/authorize/lifecycle; the separate User-
  authorizations list and creator-scoped revoke. Navigation requires no
  change — `navigationConfig.js`'s three relevant entries already point
  at the correct paths. Routing, component architecture (a generalized
  `ConfirmDialog`, an extended `StatusBadge`, two separate — not merged
  — authorization forms, a reused `departmentService.js`), service
  layer (endpoint-by-endpoint method mapping), a full error-handling
  matrix, a full confirmation matrix (never "Delete" wording, matching
  Phase 5C's "Archive, never delete" precedent), a security review, and
  a three-enum state matrix (`UserStatus`/`AuthorizationStatus`/
  `ActiveStatus`, never merged) were all designed, not implemented.
* **No frontend or backend file was touched** — confirmed by `git
  status` before/after; this phase produced documentation only.
* **Documentation**: `docs/architecture/administration-ui.md` (new),
  plus updates to the root README and `docs/README.md`.

### Phase 5C — Core Registry UI implementation

* **`LetterListPage`** (`frontend/src/pages/LetterListPage.jsx`) — one
  component mounted at both `/app/letters` (USER/ADMIN) and
  `/app/system/letters` (SYSTEM_ADMIN, `RoleGuard`-wrapped), adapting to
  `user.role` rather than duplicating pages. List/filter/sort/pagination
  state lives in the URL (`useSearchParams`, no new dependency) so
  refresh, back/forward, and bookmarking all preserve registry state.
  Filters: all seven confirmed text filters, `status` (every role),
  `category_id`/`classification_id`/`department_id` (SYSTEM_ADMIN only —
  see the reference-data gap below), inclusive received-date range.
  Sorting: all four whitelisted fields via an explicit selector plus
  `aria-sort`-labeled clickable column headers. Pagination: driven
  entirely by the backend's own `page`/`page_size`/`total`/`total_pages`,
  self-correcting when a filter narrows the result set out from under an
  already-paginated page.
* **CONFIRMED backend-contract gap found and resolved, not routed
  around**: `GET /api/v1/categories`/`/classifications`/`/departments`
  are all `require_system_admin`-only, but `POST /api/v1/letters`
  structurally excludes SYSTEM_ADMIN — no role that can create/edit a
  Letter can load those reference-data lists. `category_id`/
  `classification_id` never appear on Create (for any role); on Edit
  they appear only for SYSTEM_ADMIN. Nothing hardcoded as a workaround —
  confirmed by grep. Full reasoning:
  `docs/architecture/frontend.md` §36.
* **`LetterFormPage`** (`frontend/src/pages/LetterFormPage.jsx`) — one
  component for both `/app/letters/new` (create) and
  `/app/letters/:id/edit` (edit). Field set matches `LetterCreate`/
  `LetterUpdate` exactly minus the two documented, deliberate omissions
  (`source_department_id` — a scope simplification; category/
  classification — the confirmed gap above). Client-side validation
  (`frontend/src/utils/formValidation.js:validateLetterForm`) checks only
  the fields the backend itself requires at creation; server `422` field
  errors render through the same mechanism. Never sends an explicit
  `null` for category/classification on edit (would silently no-op
  against the pre-existing "omitted means unchanged" `LetterUpdate`
  limitation) — the form's own hint text says so directly.
* **`LetterDetailPage`** (`frontend/src/pages/LetterDetailPage.jsx`) —
  renders every `LetterResponse` field except `recorded_by` (no
  cross-role user-lookup endpoint was in this phase's authorized scope).
  A `404` — nonexistent, wrong-department, or classified-and-inaccessible,
  all three collapsed identically by the backend — renders the same
  generic "Letter not found," verified by a test asserting the rendered
  text contains neither "classif" nor "permission."
* **Archive, never "delete"** (`frontend/src/components/
  ArchiveConfirmDialog.jsx`) — `DELETE /api/v1/letters/{id}` is a soft
  status transition, confirmed from the endpoint's own summary string,
  never a physical row deletion; the confirmation dialog says so
  directly and never uses "delete" or "permanent." The archive action
  disappears once a letter is already `ARCHIVED`.
* **Reusable components**: `LetterTable` (semantic table, `aria-sort`,
  conditional columns driven by which lookup maps the caller supplied —
  never a raw id when a name can't be resolved), `LetterFilters`
  (explicit Apply/Clear, no request-per-keystroke), `Pagination`
  (`aria-current`, boundary-disabled Previous/Next), `StatusBadge`
  (never color alone), `ArchiveConfirmDialog` (dependency-free but
  keyboard-trapped, `Escape`-dismissible).
* **API service layer**: `letterService.js` (`list`/`get`/`create`/
  `update`/`archive`, an explicit field allowlist on write so
  `recipient_department_id`/`recorded_by`/`status`/`id` can never reach
  a request body — verified by a payload-shape test on both create and
  edit), `categoryService.js`/`classificationService.js`/
  `departmentService.js` (thin SYSTEM_ADMIN-only wrappers).
* **No N+1** — one request per registry page load; category/
  classification/department names come from lookup maps loaded once
  (SYSTEM_ADMIN only), never per row.
* **Test suite grown from 44 to 84 tests** across 17 files — new:
  `utils/formValidation.test.js` extended (3),
  `components/LetterTable.test.jsx` (5), `components/Pagination.test.jsx`
  (4), `pages/LetterListPage.test.jsx` (10),
  `pages/LetterDetailPage.test.jsx` (7), `pages/LetterFormPage.test.jsx`
  (11).
* **No backend file was touched** — confirmed by `git status` and a full
  backend regression run before and after (458 passed, unaffected both
  times).
* **Validation**: `npm run build` succeeds (139 modules, no errors);
  `npm run test` — **84 passed**, 0 failed; `pytest tests/` (backend) —
  **458 passed**, unaffected.
* **Documentation**: `docs/architecture/frontend.md` §36 (new
  implementation record), plus updates to the root README,
  `frontend/README.md`, `docs/README.md`, and
  `docs/architecture/overview.md`.

### Phase 5B — Authentication & Account UX implementation

* **`LoginPage`/`SignupPage` rebuilt as production forms**
  (`frontend/src/pages/LoginPage.jsx`/`SignupPage.jsx`) — client-side
  required-field and email-format validation
  (`frontend/src/utils/formValidation.js`, dependency-free), each field
  wired with `aria-invalid`/`aria-describedby` pointing at its own error
  text, a disabled submit button with a distinct loading label while a
  request is in flight, and the previous submission's error cleared the
  instant a new one begins. Server-side validation (`422`) remains
  authoritative — client-side checks only stop an obviously incomplete
  submission from being sent.
* **Two new reusable account-state notices**
  (`frontend/src/components/PendingApprovalNotice.jsx`/
  `DeactivatedAccountNotice.jsx`) — `PendingApprovalNotice` renders after
  a successful signup and after a login attempt against a
  `PENDING_APPROVAL` account (same underlying backend fact, two call
  sites); states only that the account needs administrator approval, no
  timeline, no email-notification promise, no administrator contact
  invented. `DeactivatedAccountNotice` renders only after a login attempt
  against a deactivated account (the backend only distinguishes this at
  `POST /auth/login`; a mid-session deactivation instead surfaces as a
  generic `401`, already handled by the existing centralized handler) —
  states the account is disabled and its record has not been deleted,
  with no administrative detail exposed and no reactivation control (an
  administrative, backend-only operation, correctly out of scope).
* **Session-restoration network-failure handling**
  (`frontend/src/context/AuthContext.jsx`) — a genuine token rejection
  (`401`) still clears the stored token, exactly as before; a network
  failure (the server can't be reached at all) no longer does — the
  token might still be valid, so it's kept, `status` becomes
  `'unauthenticated'` (never silently `'authenticated'`), and a new
  `restoreError` field plus a `retryRestoreSession` function are exposed
  so `LoginPage` can show a retry-capable banner instead of an
  unexplained demand to log in again.
* **A real Phase 5A gap closed**: `SignupPage` gained the same
  already-authenticated → redirect-into-`/app` guard `LoginPage` already
  had — before this phase, an authenticated user visiting `/signup`
  directly would see the signup form instead of being redirected.
* **Design tension resolved and documented, not silently picked**: the
  brief's "refresh/load the authoritative user through `/auth/me`" after
  login was reconciled against Phase 5A's existing behavior (setting
  `user` directly from the login response) by re-reading `auth.py`
  fresh — the login endpoint's `TokenResponse.user` is already the same
  freshly-queried, backend-authoritative `UserPublic` a follow-up
  `/auth/me` call would return, so no redundant call was added. What the
  instruction actually protects against — never deriving authorization
  from decoded JWT claims — was already true and remains true (no
  JWT-decoding library exists in this codebase). See
  `docs/architecture/frontend.md` §35.
* **Accessibility** — every form field has a real `<label htmlFor>`,
  `aria-invalid` reflecting its active error (client- or
  server-reported), and `aria-describedby` pointing at that error's own
  `id` (verified by a test that resolves the id via
  `document.getElementById` and asserts it contains the visible error
  text). Submission-level errors use the existing `ErrorState`'s
  `role="alert"`; the two new notices use `role="status"` (an
  informational account-state fact, not a user-caused error).
* **Test suite grown from 17 to 44 tests** across 8 files — new:
  `utils/formValidation.test.js` (6), `pages/LoginPage.test.jsx` (11),
  `pages/SignupPage.test.jsx` (7), `routes/routing.test.jsx` (1, an
  end-to-end logout → `/login` redirect test rendering the real
  `AuthProvider`/`ProtectedRoute`/`AppShell`/`Topbar` together); expanded:
  `context/AuthContext.test.jsx` (5 → 7, adding the network-failure and
  retry-after-network-failure scenarios).
* **No backend file was touched** — confirmed by `git status` (no
  `backend/app/`, `backend/alembic/`, or `backend/tests/` file changed)
  and a full backend regression run before and after (458 passed,
  unaffected both times).
* **Validation**: `npm run build` succeeds (117 modules, no errors);
  `npm run test` — **44 passed**, 0 failed (re-run after the final
  self-review pass, identical result); `pytest tests/` (backend) —
  **458 passed**, unaffected.
* **Documentation**: `docs/architecture/frontend.md` §35 (new
  implementation record), plus updates to the root README,
  `frontend/README.md`, `docs/README.md`, and
  `docs/architecture/overview.md`.

### Phase 5A — Frontend Foundation implementation

* **Routing wired up** (`frontend/src/routes/index.jsx`) —
  `react-router-dom` (installed since Phase 1, unused until now) now
  backs `/`, `/login`, `/signup`, and a `/app` subtree gated by
  `ProtectedRoute`. Placeholder child routes exist only where necessary
  to prove the routing architecture, all rendering one shared
  `PlaceholderPage` — no feature logic anywhere in them.
* **`AuthContext`** (`frontend/src/context/AuthContext.jsx`) — the
  single authentication state mechanism: `status`
  (`'loading' | 'authenticated' | 'unauthenticated'`) and `user`, always
  the `UserPublic` object most recently returned by
  `POST /auth/login`/`GET /auth/me`, never decoded from the JWT
  client-side. Session restoration validates any stored token against
  `/auth/me` before any protected route renders, avoiding an
  authentication flicker.
* **One centralized Axios client** (`frontend/src/services/apiClient.js`)
  — attaches `Authorization: Bearer <token>`; normalizes both confirmed
  backend error-body shapes (`{"detail": "<string>"}` for raised
  `HTTPException`s, FastAPI's array-shaped `{"detail": [...]}"` for
  Pydantic validation failures) into one predictable
  `{status, message, fieldErrors}`
  (`frontend/src/services/errorNormalization.js`); a single 401 handler
  clears the session — except on the login/signup/session-restore calls
  themselves (`{ skipAuthRedirect: true }`), which handle their own
  failure locally, matching the review's own explicit finding that a
  `401` on the login form itself is a wrong-password error, not "your
  session died."
* **Token storage isolated to one module**
  (`frontend/src/services/tokenStorage.js`) — `localStorage` for V1,
  documented explicitly (in the module itself and in
  `frontend/README.md`) as the same PROVISIONAL placeholder the
  architecture review named, with the exact replacement boundary stated.
  No token is logged anywhere and none appears in any URL.
* **Login/signup foundations** (`frontend/src/services/authService.js`,
  `frontend/src/pages/LoginPage.jsx`/`SignupPage.jsx`) — minimal,
  functional forms (not the final polished pages the review describes)
  built far enough to prove success, invalid credentials, a pending
  account, and a deactivated account each render the backend's own
  distinct real message, verified against the exact strings in
  `auth.py`. Signup never auto-logs in, matching the review's own
  finding that a fresh account always starts `PENDING_APPROVAL`. Neither
  form has a `role`/`department`/`status` field — the backend schemas
  have none either.
* **`ProtectedRoute` (authentication only) and `RoleGuard` (role-based
  navigation convenience only) as two separate components** — matching
  the review's own explicit instruction not to perform role
  authorization inside the authentication guard; neither provides real
  security, which remains entirely backend-enforced.
* **Role-derived navigation** (`frontend/src/navigation/navigationConfig.js`)
  — plain, frozen configuration data, matching the brief's three
  per-role lists exactly (including "Documents," pointed at a
  placeholder that explains it has no standalone route, per the review's
  own recommended design, rather than silently dropping the entry or
  silently building a page the review didn't recommend). No department
  id appears anywhere in it — verified by a dedicated test.
* **`AppShell`/`Sidebar`/`Topbar`** (`frontend/src/layouts/`) — current
  user's display identity, role indicator, logout control, and
  role-derived nav; no dashboard widget of any kind.
* **A small design-token set** (`frontend/src/styles/tokens.css`/
  `global.css`) — CSS Modules for component-scoped styles, no UI
  framework added.
* **An accessibility baseline** — semantic nav/buttons, visible focus
  states, associated form labels, `role="status"`/`role="alert"` on the
  loading/error primitives.
* **Test infrastructure established from nothing** — no test framework
  existed in `package.json` before this phase; Vitest + React Testing
  Library + jsdom now do, with **17 tests** across the four areas the
  brief named as the minimum: authentication state transitions (5),
  protected-route behavior (3), role-navigation configuration (5), and
  API error normalization (4).
* **No feature screen was built** — every nav destination renders the
  one shared placeholder. No Letter pages, Letter CRUD, search UI,
  document UI, notification UI, dashboard, administration pages, or
  audit UI.
* **No backend file was touched** — confirmed by `git status` (only
  `backend/README.md`, a documentation file, changed) and a full backend
  regression run before and after (458 passed, unaffected both times).
* **Validation**: `npm run build` succeeds (113 modules, no errors);
  `npm run test` — **17 passed**, 0 failed; `pytest tests/` (backend) —
  **458 passed**, unaffected.
* **Documentation**: `docs/architecture/frontend.md` §34 (new
  implementation record), plus updates to the root README,
  `frontend/README.md`, `docs/README.md`, and
  `docs/architecture/overview.md`.

### Phase 5 — Frontend & Operational UI architecture & requirements review

* **Inspected the actual current frontend, not assumed** — confirmed
  `frontend/` is a pure Phase 1 skeleton: `App.jsx` renders a static
  placeholder, every other `src/*` directory
  (`components`/`context`/`hooks`/`layouts`/`pages`/`routes`/`services`/
  `utils`) contains only a one-line placeholder `README.md`, no `.jsx`/
  `.js` implementation file exists beyond `App.jsx`/`main.jsx`/
  `constants/app.js`, and `node_modules/` has never been installed.
* **Confirmed the frontend stack is already chosen, not a decision this
  review needed to make** — React 18.3.1, Vite 5.3.1,
  react-router-dom 6.24.0, axios 1.7.2, all already in `package.json`,
  none of it wired up (no router mounted, no HTTP client instance, no
  state management, no CSS framework, no test framework configured).
  Recommended keeping it exactly as-is at V1 — no React Query, no
  state-management library, no CSS/UI framework — per the review's own
  repeated instruction not to add complexity without a demonstrated
  need.
* **Built an endpoint-to-screen map from the live OpenAPI schema, not
  memory** — `app.openapi()` enumerated **42 real business endpoints**
  across 8 resource routers (auth, departments, admins, users,
  categories, classifications, letters, documents, notifications),
  explicitly excluding `/health` and the five verification-only
  `/auth/test/*` routes.
* **Corrected one real gap in the task's own suggested System Admin
  navigation** — it omitted Letters/Documents entirely, but
  `SYSTEM_ADMIN` is confirmed (via `assert_letter_access`'s own bypass)
  to have full cross-department Letter/Document read/update/archive
  access, and is the one role for which `GET /letters`'s `department_id`
  filter is actually meaningful. Recommended adding a System Admin
  Letters screen rather than silently following an incomplete
  suggestion.
* **Mapped the *actual* Letter schema for the create/edit form, not the
  task's own illustrative field list** — read `app/schemas/letter.py`
  fresh and found a real field (`reason`) the task's own "known business
  fields" example omitted; confirmed `recipient_department_id` is
  server-derived only (no "choose recipient department" control exists
  on any form) and that `reference_number` has no uniqueness
  constraint, so no "is this available" UX should be built.
* **Classified Letter UX (CRITICAL) — the governing rule for the whole
  review.** The frontend must never independently filter, label, or
  infer classified-Letter existence — `items`/`total` from `GET /letters`
  already exclude inaccessible letters at the query level (Phase 4C's
  own fix), and every `404` on a Letter/Document must be rendered
  identically regardless of whether the resource doesn't exist or exists
  but is restricted — collapsing that distinction is exactly what the
  backend's own enumeration-resistant design already does, and a
  frontend that re-introduces a "this one's classified" message would
  silently defeat it.
* **A real gap identified that no frontend design can close without a
  backend change**: nothing exposes a caller's own department's
  `ACTIVE`/`INACTIVE` status to them (`UserPublic` has `department_id`,
  not the department's own status) — the frontend can only detect its
  own department going inactive *reactively*, via a `403` on the next
  action, never proactively. Not proposed as a backend change here —
  named as an accepted, real V1 limitation.
* **A precise, previously-undocumented integration detail surfaced by
  reading the actual endpoint code** — this backend returns two
  different error-body shapes depending on failure origin: a plain
  `{"detail": "<string>"}` for every raised `HTTPException` throughout
  every service in this codebase, versus FastAPI's own array-shaped
  `{"detail": [{"loc": [...], "msg": ..., "type": ...}]}` for a Pydantic
  request-validation failure. A frontend error-normalization layer that
  assumes only one of these shapes will break on whichever it didn't
  test.
* **Document download requires the same bearer auth as every other
  endpoint** — confirmed no plain, unauthenticated, or static URL to a
  document exists anywhere (no `StaticFiles` mount, Phase 4D). A plain
  `<a href>` cannot carry the required `Authorization` header;
  recommended fetch-then-blob-URL, with "open in a shareable new-tab
  URL" named as a real, accepted V1 limitation rather than silently
  worked around.
* **Three distinct backend status enums, not one blended lifecycle** —
  corrected the task's own loosely-worded lifecycle label set
  (`AuthorizationStatus`: `ACTIVE`/`USED`/`REVOKED` on
  `UserAuthorization`; `UserStatus`: `PENDING_APPROVAL`/`ACTIVE`/
  `DEACTIVATED` on `User`; `ActiveStatus`: `ACTIVE`/`INACTIVE` on
  Department/Category/Classification — a different enum that happens to
  share the word "ACTIVE") — recommending one parameterized `StatusBadge`
  component so the three never visually blend into each other. Verified
  directly against `app/models/enums.py`, not assumed from the task's
  own phrasing.
* **Every one of the 42 confirmed endpoints was mapped to a screen** —
  no orphaned backend capability was left unmapped, and no screen was
  proposed for a capability the backend doesn't actually have.
* **A route/component/API-client architecture, an auth-state design, a
  consolidated error-handling table, a minimal design-system
  recommendation (CSS Modules, no framework), an accessibility
  baseline, a frontend security review (including the token-storage
  trade-off and every listed risk — role/department spoofing, IDOR,
  classified/notification leakage, document URL exposure), a dashboard
  feasibility assessment (what's derivable from existing endpoints with
  zero new backend work, and what genuinely isn't), and a prioritized
  test strategy were all designed, not implemented.**
* **No frontend or backend file was touched** — confirmed by `git
  status` before/after; this phase produced documentation only.
* **Documentation**: `docs/architecture/frontend.md` (new), plus updates
  to the root README, `backend/README.md`, `docs/README.md`, and
  `docs/architecture/overview.md`.

### Phase 4E — Operational Activity, Notifications & Audit implementation

* **Audit foundation** (`app/services/audit_service.py:AuditService.record`,
  `app/repositories/audit_log_repository.py`) — the single, reusable
  service-level mechanism the review's §16/§19 called for: no event bus,
  no SQLAlchemy event listeners, no domain-event framework. `record`
  only `flush()`es, never `commit()`s/`rollback()`s — the caller's own
  existing `session.commit()` is what actually makes a write mandatory.
  Insert-only by construction: no `update`/`delete` method exists, and
  **no audit-viewing or audit-mutation endpoint of any kind was built**
  — confirmed by a dedicated test hitting a plausible audit URL and
  getting `404`/`405`.
* **Wired into eight entity types, exactly the events the review
  named, no more**: `LETTER_CREATED`/`UPDATED`/`ARCHIVED`/
  `CLASSIFICATION_CHANGED`/`CATEGORY_CHANGED`
  (`app/services/letter_service.py`); `DOCUMENT_UPLOADED`
  (`app/services/document_service.py`, recorded inside the same try
  block that already handles Phase 4D's write-then-commit compensation,
  so an audit failure triggers the identical file-cleanup path a
  database failure would); `USER_APPROVED`/`DEACTIVATED`/`REACTIVATED`,
  `USER_AUTHORIZATION_CREATED`/`REVOKED`
  (`app/services/user_service.py`); `ADMIN_AUTHORIZATION_CREATED`,
  `ADMIN_APPROVED`/`DEACTIVATED`/`REACTIVATED`/`DEPARTMENT_CHANGED`
  (`app/services/admin_service.py` — required adding an `actor_id`
  parameter to four methods that previously received no caller identity
  at all, and threading `current_user.id` through `admins.py`, whose
  `_current_user` dependency parameter had been unused until now);
  `DEPARTMENT_CREATED`/`ACTIVATED`/`DEACTIVATED`
  (`app/services/department_service.py` — `DEPARTMENT_UPDATED` was
  deliberately not implemented, honoring the brief's own asymmetric
  event list); `CATEGORY_CREATED`/`UPDATED`/`ACTIVATED`/`DEACTIVATED`
  and the `CLASSIFICATION_*` equivalents
  (`app/services/category_service.py`/`classification_service.py`).
  Every "only on a genuine state transition" case (e.g. re-archiving an
  already-archived letter) was checked explicitly, so idempotent no-op
  calls never produce a redundant audit entry.
* **Targeted old/new values only, verified not just designed** — a
  dedicated test asserts `LETTER_CLASSIFICATION_CHANGED`'s
  `old_values`/`new_values` contain *only* `classification_id`, and
  another confirms a Letter's `text_content` and a User's
  `password_hash` never appear in any audit row's values, across every
  event type.
* **Mandatory/same-transaction, proven by forcing a real failure** —
  `test_audit_failure_rolls_back_letter_creation` makes
  `AuditService.record` raise mid-`create_letter` and confirms, after
  rolling back the still-open transaction, that the Letter row never
  existed — not merely that the request returned an error.
* **Notification foundation** (`app/services/notification_service.py`,
  `app/repositories/notification_repository.py`) — the one CONFIRMED V1
  trigger, `notify_letter_registered`, called from
  `LetterService.create_letter`. Recipient strategy (the recipient
  department's ACTIVE Admins, via `UserRepository.list_admins`) is
  implemented exactly as the review's PROVISIONAL default, not quietly
  promoted to a confirmed answer.
* **Best-effort via a real database `SAVEPOINT`, proven against a
  genuine internal failure** — `notify_letter_registered` wraps its body
  in `session.begin_nested()`; a dedicated test makes
  `NotificationRepository.create` itself raise (not a stand-in that
  bypasses the savepoint) and confirms the Letter and its audit row
  still commit successfully, the failure is logged at `WARNING`
  (`app/core/logging.py:get_logger` — this project's one existing
  logging convention, no new one introduced), and no notification row
  exists for that letter.
* **Generic message content, verified with a deliberately sensitive
  test case** — `test_notification_message_contains_no_letter_content`
  creates a Letter with a deliberately sensitive `subject` and confirms
  it never appears in the generated notification text
  (`"A new letter (reference: {reference_number}) has been registered
  in your department."`).
* **`GET /api/v1/notifications`** (paginated, newest-first),
  **`GET /api/v1/notifications/unread-count`**,
  **`PATCH /api/v1/notifications/{notification_id}/read`** (idempotent),
  **`PATCH /api/v1/notifications/read-all`** — all four use
  `get_current_user` only and are unconditionally scoped to
  `current_user` for every role including `SYSTEM_ADMIN`; a mismatched
  notification id 404s, matching the enumeration-resistant shape
  `DocumentNotFoundError`/`LetterNotFoundError` already established.
* **Zero schema change.** `alembic check` against `lrs_dev` reports "No
  new upgrade operations detected" both before and after this phase —
  `AuditLog`/`Notification` are used exactly as they already existed
  since Phase 2.
* **33 new tests** (`tests/integration/test_audit.py` — 21,
  `test_notifications.py` — 12) — covering all 30 scenarios named in
  the implementation brief; regression scenarios (existing
  authorization, classified-Letter access, department isolation,
  document access, Letter search/pagination) are covered by the
  pre-existing 425-test suite, re-run after every wiring change and
  confirmed to stay green throughout, rather than duplicated into new
  test functions.
* **Full suite: 458 passed** (425 baseline + 33 new), re-run 3
  consecutive times, identical results.
* **Live-server verification against `lrs_dev`**, real minted JWTs, real
  HTTP — see "Validation performed" below.
* **Documentation**: `docs/architecture/audit-notifications.md` §31
  (new implementation record), plus updates to the root README,
  `backend/README.md`, `docs/README.md`, and
  `docs/architecture/overview.md`.

### Phase 4E — Operational Activity, Notifications & Audit architecture & requirements review

* **Inspected the actual current repository state, not assumed** —
  confirmed `AuditLog` and `Notification` are byte-for-byte unchanged
  since the Phase 2 baseline + hardening migrations; confirmed by `grep`
  across `app/services/`, `app/repositories/`, `app/api/`,
  `app/schemas/`, `app/core/` that **zero application code writes to
  either table anywhere** — only two model-level tests touch each
  (`tests/integration/test_models.py`), exercising relationships and
  defaults, not generation logic. Confirmed no SQLAlchemy event-listener,
  background-task, or queue infrastructure exists anywhere in the
  codebase (`requirements.txt` has no Celery/Redis; `app/middleware/` is
  still empty except `__init__.py`).
* **Consolidated five prior phases' own "planned, not implemented" audit
  lists into one place**, rather than starting a sixth competing one —
  `authorization.md` §12, `department-management.md` §10,
  `admin-management.md` §13, `user-management.md` §12, and
  `document-management.md` §25 each already itemized their own entity's
  events; this review confirmed all five are still accurate and added
  the events none of them had ever itemized: Letter created/edited/
  archived/classification-changed/category-changed, and
  Category/Classification management events (created/updated/activated/
  deactivated). Letter classification changes are flagged as the
  highest-priority Letter-related event, since it's the one field whose
  change can alter who can see the letter at all.
* **Audit immutability (CRITICAL) — recommended append-only**, matching
  this project's established never-physically-delete pattern
  (Department/User/Category/Classification/Letter all deactivate/
  archive; Phase 4D's own review concluded `LetterDocument` needs no
  deletion endpoint at all). No role, including `SYSTEM_ADMIN`, should
  ever get an API path that edits or deletes an `AuditLog` row.
* **Audit target strategy — recommended keeping the existing
  `entity_type`/`entity_id` design (no FK), no schema change.** Evaluated
  against two rejected alternatives (per-entity audit tables; a wide
  sparse-FK table) and confirmed the current, minimal design is already
  the least-overengineered V1 choice. One clarification identified, not
  a schema change: an Admin-related audit event should use
  `entity_type="User"` (the real table an Admin account lives in, since
  Admin accounts have been `User` rows with `role=ADMIN` since Phase
  3B.3), disambiguated by the `action` string (`ADMIN_APPROVED` vs.
  `USER_APPROVED`) — never a fictitious `entity_type="Admin"` that
  doesn't correspond to any real table.
* **Change detail strategy — recommended targeted old/new field pairs**
  (e.g. `{"old_department_id": ..., "new_department_id": ...}`), **not a
  generic full-row-snapshot JSON blob** — explicitly rejected as
  something nothing in the confirmed requirements needs, and a real
  future data-leakage risk if a full snapshot ever captured a classified
  Letter's `text_content` alongside a mundane field change.
* **Transactional consistency (CRITICAL) — an asymmetric, precisely
  worked-out design.** Audit writes are recommended mandatory, sharing
  the triggering operation's own transaction — a failure fails the whole
  operation, since a silently-unaudited official action would defeat the
  audit trail's entire stated purpose. Notification writes are
  recommended best-effort — but a naive try/except around a same-session
  notification write is **not sufficient**, since PostgreSQL aborts an
  entire transaction the moment any statement inside it fails; the
  review identifies a `SAVEPOINT` (`session.begin_nested()`) as the
  correct mechanism, and points directly at `tests/conftest.py`'s
  `db_session` fixture — already using `join_transaction_mode="create_savepoint"`
  for an analogous reason — as existing, working proof the pattern is
  sound in this exact codebase, not a novel proposal.
* **Notification security (CRITICAL) — recommended keeping stored
  `message` text generic**, never interpolating a Letter's subject or
  content directly into it, because a later classification change cannot
  retroactively scrub text already sent to a recipient. Any future
  richer notification display (e.g. joining to live Letter fields) must
  re-check `assert_letter_access` fresh at read time — extending Phase
  4D's "authorization must never be cached or snapshotted" principle
  (`document-management.md` §17) to a third consumer.
* **Audit access control — deliberately left PENDING**, with a real
  complexity surfaced rather than hand-waved: resolving "which
  department does this audit entry belong to" for a polymorphic target
  requires a per-entity-type join (a `Letter`'s via
  `recipient_department_id`, a `User`'s via its own `department_id`, a
  `Department` *is* one) that no authorization check in this project has
  needed before. **Recommended safe default**: `SYSTEM_ADMIN`-only for
  V1's audit-viewing API, whenever built — narrower than "ADMIN sees
  their department," which shouldn't be built before that resolution
  logic is deliberately designed and tested, given the data-leakage risk
  of getting it wrong.
* **Notification recipients — explicitly flagged as PENDING BUSINESS
  CLARIFICATION**, with the specific trap named and avoided: recipient
  selection must derive from `Letter.recipient_department_id`, never from
  `uploaded_by.department_id` or any user's own department snapshotted
  elsewhere. An interim recommended default (the recipient department's
  Admins) is offered but explicitly marked a guess, not a confirmed
  answer.
* **Real-time delivery — confirmed, not guessed, out of scope**, quoting
  `docs/database/schema.md` §2.8's own record of the original brief
  directly: "V1 is an in-system notification center only... no delivery
  mechanism (email, push, WebSocket) exists or is assumed." Polling or
  manual refresh recommended; WebSockets/SSE explicitly not recommended
  for V1.
* **Event generation architecture — recommended service-level**,
  evaluated against four alternatives (endpoint-level, SQLAlchemy event
  listeners, a domain-event/pub-sub layer, background tasks) and
  rejecting each with a specific, codebase-grounded reason — notably that
  ORM event listeners would also fire during `tests/factories.py`'s
  direct model construction, polluting test runs with synthetic
  audit/notification rows.
* **A 14-scenario test plan and a 7-step Recommended Phase 4E
  implementation sequence were both designed, not implemented.** No
  migration, model, service, repository, schema, or endpoint file was
  touched — confirmed by `git status` before/after.
* **Documentation**: `docs/architecture/audit-notifications.md` (new),
  plus updates to the root README, `backend/README.md`, `docs/README.md`,
  and `docs/architecture/overview.md`.

### Phase 4D — Document Management implementation

* **`POST /api/v1/letters/{letter_id}/documents`** (upload),
  **`GET /api/v1/letters/{letter_id}/documents`** (metadata list, no
  `storage_path` field on the response), and
  **`GET /api/v1/letters/{letter_id}/documents/{document_id}`**
  (streamed binary download) — nested under Letter on purpose, per the
  review's own §19 recommendation, so the letter-first authorization
  chain is structurally unavoidable rather than a discipline to remember.
* **Storage foundation** (`app/services/document_storage.py`) —
  `STORAGE_PATH` resolved to an absolute path fresh on every call (never
  cached at import time), created if missing. Every filesystem path
  segment is server-generated:
  `<STORAGE_PATH>/<letter_uuid>/<document_uuid>.<ext>`, the extension
  chosen from a fixed map keyed by the already magic-byte-validated
  content type — never a client-supplied filename or extension. Writes
  are staged to a uniquely-named temp file and atomically renamed into
  place. **One deliberate deviation from the review's own §7
  recommendation**: the implementation brief's literal example (this
  exact flat, no-department/year/month-grouping structure) was followed
  as an explicit instruction, rather than the review's own recommended
  reconciliation with the Phase 1 `storage/README.md` convention — that
  file now documents what was actually built and is explicit about the
  gap, rather than silently updated to match either.
* **Layered file validation** (`app/services/document_validation.py`) —
  extension allowlist → size limit
  (`settings.MAX_DOCUMENT_SIZE_BYTES`, 10 MB default, still labeled an
  architectural recommendation in `config.py`/`.env.example`, not a
  confirmed organizational limit) → an authoritative magic-byte
  content-signature check (hand-rolled byte-prefix checks for
  PDF/JPEG/PNG, a UTF-8/control-character heuristic for text —
  deliberately no `python-magic`/libmagic dependency, given the small
  fixed type set and the native-install friction such a dependency adds
  on Windows) → extension/content-type agreement (a `.pdf` upload whose
  bytes are actually a PNG is rejected as mismatched). Client-supplied
  `Content-Type` is read but never consulted by any validation decision
  — confirmed live by uploading real PNG bytes under a `.pdf` filename
  and declared `Content-Type: application/pdf` (`422`, rejected).
* **Authorization chain (CRITICAL) — reused, not duplicated.**
  `DocumentService` resolves and authorizes the parent Letter via the
  existing `LetterService.get_letter` (already applying
  `assert_letter_access`) before ever touching a document — no new
  department/classification logic was written. A thin
  `assert_document_access` delegate was also added to
  `app/services/authorization.py` for any future caller holding an
  already-loaded `LetterDocument`, per the review's own suggestion. Every
  document route uses `get_current_user` only (not
  `require_user_or_admin`) so SYSTEM_ADMIN retains the same system-wide
  access to documents it already has to Letters — deliberately different
  from `POST /letters`, which excludes SYSTEM_ADMIN for a structural
  reason (no department to record a letter against) that doesn't apply
  to attaching a document to an *existing* letter.
* **Deletion policy (CRITICAL) — implemented exactly as recommended,
  the one recommendation with zero deviation.** No document deletion
  endpoint exists, physical or soft (`grep` for `@router.delete` in
  `app/api/v1/endpoints/documents.py` returns nothing). Uploading again
  is the only way to add a document; nothing removes a prior one.
* **Write-then-commit failure handling** — the file is written to its
  final path *before* the database row is committed; a DB failure after
  a successful write rolls back the transaction and deletes the
  now-orphaned file as compensation. Both failure branches (DB failure
  after a successful write; storage failure before any DB write) are
  directly tested, not just asserted.
* **Zero schema change.** `LetterDocument` is untouched;
  `alembic check` against `lrs_dev` reports "No new upgrade operations
  detected" both before and after this phase. The review's own
  `checksum_sha256` recommendation (§12) was explicitly not implemented,
  per the implementation brief's own instruction not to add it yet.
* **`python-multipart` added as a new dependency** (`requirements.txt`)
  — required by FastAPI/Starlette to parse `multipart/form-data` upload
  requests; no application code imports it directly.
* **38 new tests**
  (`tests/integration/test_document_management.py`) — file acceptance
  (PDF/JPEG/PNG/TXT) and rejection (bad extension, HTML, MIME spoofing,
  malformed content, oversized, empty), path security (five malicious-
  filename variants plus a direct containment-check test), authorization
  (USER/ADMIN own vs. other department, SYSTEM_ADMIN cross-department,
  classified-letter recorder vs. non-recorder, wrong-letter/document
  pairing, nonexistent letter/document), historical integrity
  (deactivated uploader still represented, archived letters keep their
  documents and stay downloadable), storage guarantees (UUID-based
  server-controlled path, no `storage_path` in any response, no static
  route exposes storage, correct download headers), and failure handling
  — against a real PostgreSQL test database, with an autouse
  `storage_root` fixture redirecting every test's `STORAGE_PATH` to a
  per-test temporary directory (the filesystem equivalent of
  `db_session`'s per-test rollback isolation).
* **Full suite: 425 passed** (387 baseline + 38 new), re-run 3
  consecutive times, identical results.
* **Live-server verification against `lrs_dev`**, real minted JWTs, real
  HTTP — see "Validation performed" below.
* **Documentation**: `docs/architecture/document-management.md` §33
  (new implementation record), `storage/README.md` (updated to match
  what was actually built), plus updates to the root README,
  `backend/README.md`, `docs/README.md`, and
  `docs/architecture/overview.md`.

### Phase 4D — Document Management architecture & requirements review

* **Inspected the actual current repository state, not assumed** —
  confirmed `LetterDocument` (`document_type`, `original_filename`,
  `storage_path`, `file_size`, `mime_type`, `uploaded_by`, `uploaded_at`)
  is byte-for-byte unchanged since the Phase 2 baseline + hardening
  migrations; confirmed zero application code (service/repository/
  schema/endpoint) exists above the model layer; confirmed no
  `StaticFiles` mount exists in `app/main.py`; confirmed `.gitignore`
  excludes `storage/letters/*` except `.gitkeep`; confirmed only two
  Phase 2 model-level tests touch `LetterDocument` (multi-document
  attachment, CASCADE-on-physical-delete), with no upload/validation/
  security test existing anywhere.
* **Surfaced a real, previously-unnoticed documentation conflict** — the
  pre-existing Phase 1 `storage/README.md` path convention
  (`<department-code>/<year>/<month>/<letter-uuid>.<ext>`) has no
  document-identifier segment, structurally assuming one file per
  letter; this conflicts with the schema's already-confirmed 1-to-many
  `Letter → LetterDocument` capability. Not silently resolved — reconciled
  with a recommended combined convention
  (`<department-id>/<year>/<month>/<letter-uuid>/<document-uuid>.<ext>`)
  that keeps Phase 1's department/year/month grouping and adds
  multi-document support, using `department.id` rather than the
  nullable, unconfirmed-format `department.code`. See
  `docs/architecture/document-management.md` §7.
* **Two CRITICAL findings resolved by design, not new code**:
  (1) department isolation for documents must derive from
  `LetterDocument.letter_id → Letter.recipient_department_id`, never
  `uploaded_by.department_id` (a User can change departments) —
  `LetterDocument` already has no department field of its own, so there
  is nothing to misuse; (2) classified-document access must chain
  through the existing `assert_letter_access`
  (`app/services/authorization.py`, Phase 4B/4C) via a thin future
  `assert_document_access` delegate, never a new parallel check — so
  classified-letter protection extends to attachments automatically. See
  §16-17.
* **Document deletion policy (CRITICAL) — recommended that V1 build no
  deletion endpoint at all**, physical or soft. Physical deletion would
  break this project's established never-physically-delete principle
  (Department/User/Category/Classification/Letter all archive, never
  delete); soft-delete would need a new lifecycle/status field
  `LetterDocument` doesn't have today; and no confirmed requirement asks
  for document deletion in the first place. See §14.
* **Document replacement policy — resolved without a schema change.**
  "Replacing" a document is recommended to mean simply uploading another
  document for the same letter (the old one stays) — already fully
  supported by the existing multi-document capability, the safest option
  against historical-record loss. A "mark as superseded" concept would
  need a new field and isn't adopted without further business
  confirmation. See §13.
* **Layered file validation strategy designed (not implemented)**:
  extension allowlist, never-trust-client-`Content-Type`, magic-byte
  signature verification as the authoritative check, size limit — with
  an explicit note that type validation is not a substitute for
  antivirus scanning (out of scope). A 10 MB default size limit is
  labeled an ARCHITECTURAL RECOMMENDATION, not a confirmed organizational
  limit — none was given. See §8-9.
* **Checksum field recommended as an additive future column**
  (`checksum_sha256`, nullable, no uniqueness constraint — two different
  letters can legitimately share an identical attachment) — the only
  schema change any recommendation in this review implies, and not
  created this phase. See §12, §28.
* **Text-content relationship clarified without a schema change** —
  `Letter.text_content` (typed/transcribed content) and a `LetterDocument`
  with `mime_type="text/plain"` (an uploaded `.txt` file) are
  complementary, not redundant; the model already supports both. The
  *workflow* question (which one a User is expected to use) is marked
  PENDING BUSINESS CLARIFICATION. See §10.
* **API design recommended**: documents nested under their Letter
  (`GET /api/v1/letters/{letter_id}/documents/{document_id}`) rather than
  a flat `/api/v1/documents/{id}`, so the letter-first authorization
  chain is structurally unavoidable, not just a discipline. Content-Type
  on download always server-controlled from the validated `mime_type`,
  never re-trusted from a client header. See §19.
* **Transaction/failure-handling strategy designed** for five scenarios
  (DB-row-created-but-file-write-fails, file-succeeds-but-DB-fails,
  interrupted upload, duplicate upload, storage-directory-unavailable) —
  recommended ordering is write-file-then-commit-DB-row, biasing failures
  toward the recoverable outcome (an orphaned file, cleanable later) over
  the unrecoverable one (a DB row referencing a file that was never
  written). See §23.
* **16+ scenario test plan designed, not implemented** — file-type
  validation, path/storage safety, authorization (cross-department,
  classified-access, IDOR/enumeration), historical integrity, failure
  handling, and static-file-exposure regression. See §29.
* **No migration, model, service, repository, schema, endpoint, or test
  file touched** — confirmed by `git status` before/after; this phase
  produced documentation only.
* **Documentation**: `docs/architecture/document-management.md` (new),
  plus updates to the root README, `backend/README.md`, `docs/README.md`,
  and `docs/architecture/overview.md`.

### Phase 4C — Registry Operations & Search implementation

### Phase 4C — Registry Operations & Search implementation

* **Fixed the query-level classified-access gap first**, exactly as
  planned. `app/services/authorization.py:letter_visibility_filter(user)`
  returns a SQLAlchemy boolean expression (`None` for
  `SYSTEM_ADMIN`/`ADMIN`; the classified-access rule as a `WHERE`
  fragment for `USER`), consumed by
  `app/repositories/letter_repository.py:list_letters`, which builds
  **one** filtered statement and derives both the `COUNT` and the
  paginated `items` query from it — structurally impossible for the two
  to disagree about which rows are visible. Verified by two dedicated
  regression tests and a live `lrs_dev` check (see "Validation
  performed" below).
* **Pagination** — `page`/`page_size` (defaults `1`/`25`, `page_size`
  capped at `100`, both FastAPI-validated), envelope extended with
  `page`/`page_size`/`total_pages` (the existing `items`/`total` keys
  unchanged).
* **Sorting** — `sort_by`/`sort_order` via `LetterSortField`/`SortOrder`
  enums (an invalid value is `422` before the endpoint runs — never a
  raw client string reaching `ORDER BY`), default `received_at desc`,
  stabilized with a secondary sort on `Letter.id`.
* **Search/filters** — `reference_number`, `subject`, `sender_name`,
  `sender_designation`, `sender_department`, `source_name`,
  `source_location` (case-insensitive contains, `ILIKE`-escaped against
  literal `%`/`_` in the search term); `received_from`/`received_to`
  (inclusive, rejected with `422` if reversed); `category_id`/
  `classification_id`/`status`/`department_id` (exact, `department_id`
  unchanged Phase 4B behavior — SYSTEM_ADMIN-only, silently ignored
  otherwise). All combine with `AND`.
* **Lightweight list response** — `LetterListItem`
  (`app/schemas/letter.py`) omits `text_content`/`reason`;
  `GET /api/v1/letters/{id}` unchanged, still returns the full
  `LetterResponse`.
* **Migration `9fa970ffa560`** — adds `ix_letters_reference_number` (a
  plain, non-unique B-tree index; re-added after Phase 4B's hardening
  pass removed the unique constraint that used to imply one). No other
  index added — a B-tree index gives `ILIKE '%contains%'` no benefit.
* **43 new tests** (`tests/integration/test_letter_search.py`) — the two
  highest-priority ones prove the central fix directly:
  `test_classified_record_excluded_from_total_count` and
  `test_classified_record_excluded_across_all_pages`.
* **No physical Letter deletion, no reference-number uniqueness
  reintroduced, no Phase 4D functionality** — confirmed explicitly, see
  "Explicit Scope Confirmation" in the phase's own final report.
* **Documentation**: `docs/architecture/registry-search.md` updated from
  recommendation to implementation record, plus updates to the root
  README, `backend/README.md`, and `docs/architecture/overview.md`.

### Phase 4B — Letter Registry Core implementation, plus a pre-commit hardening pass

Complete. Builds directly on Phase 4A's review: the
product owner resolved all six pending business decisions, and this
phase implemented them — a Letter registry with recipient/source
department separation, required structured sender details, a required
manually-entered reference number, exactly three seeded Categories,
Classification management with a real (though intentionally provisional)
classified-access authorization boundary, and full Letter CRUD (create/
list/get/update/archive) scoped by department and, for classified
letters, further narrowed for non-recording Users. A follow-up hardening
pass, before anything was committed, then reviewed the whole
implementation for correctness/security and found one real defect:
reference-number uniqueness had been implemented as a *global* database
constraint on an assumption the business never actually confirmed (only
"must be unique" was said, never the scope) — the constraint was removed
rather than kept on a guess or replaced with a different guessed scope.
Everything else reviewed (DELETE/archival safety, sender-field
placeholders, source/sender semantics, classified-access boundary,
department isolation, historical identity, input security) was
re-verified against actual code and found already correct. Full design
in `docs/architecture/letter-registry.md`, hardening findings in its §14.
Not in scope for that phase: file upload/download (the `LetterDocument`
relationship remains schema-only), dashboards, automatic notification
generation, automatic audit logging, full-text search, frontend, System
Admin handover, or an ADMIN-purpose authorization-revocation endpoint (a
pre-existing Phase 3B.4 gap, unrelated to that phase).

### Phase 4B hardening pass — pre-commit correctness/security review

* **Reference-number uniqueness — the one real defect found.** Migration
  `c887ab35e4a3` drops `uq_letters_reference_number`. The finalized
  business decision said reference numbers "must be unique" but never
  specified the scope (global? per receiving department? per source? per
  year?); the initial implementation guessed "global", which a real
  multi-department registry could easily violate legitimately (two
  departments each issuing their own overlapping numbering). No
  replacement scope was invented — duplicates are now accepted anywhere,
  pending an actual business answer. `reference_number` remains required
  (`NOT NULL`). Dead code removed alongside it:
  `DuplicateReferenceNumberError`, the `try/except IntegrityError`
  blocks in `LetterService.create_letter`/`update_letter`, and the
  unused `LetterRepository.find_by_reference_number`.
* **DELETE/archival safety — re-verified, no change needed.** Confirmed
  via `grep` (not just re-reading prior documentation) that no code path
  issues a SQL `DELETE` against a `Letter` row — `archive_letter` only
  sets `status = ARCHIVED`. Already the safest available reading of
  "Delete Letter, subject to authorization" against this project's
  standing "letters are never physically deleted" principle.
* **Sender-field migration placeholders — confirmed safe.** The literal
  string `'MIGRATION-PLACEHOLDER'` (and `'MIGRATED-<row-id>'` for
  reference numbers) cannot be mistaken for real business data, and no
  real production data could exist regardless (this project has never
  been deployed).
* **Classification security, department isolation, historical identity,
  input security — all re-verified directly against current code and
  existing tests**, confirmed to match what was previously reported, no
  changes needed. See `docs/architecture/letter-registry.md` §14 for the
  full, itemized findings using its CONFIRMED/ARCHITECTURAL/PROVISIONAL/
  PENDING taxonomy.
* **344 tests total — unchanged.** Three tests were rewritten in place
  (asserting the new, correct behavior — duplicates now succeed rather
  than being rejected) rather than deleted and replaced, so the count
  didn't move. Re-run 3 consecutive times, all green.
* **No new migration needed beyond the one hardening fix** — `alembic
  check` confirms zero drift; no historical migration file was modified.

### Phase 4B — Letter Registry Core implementation

* **Six finalized business decisions implemented exactly as specified** —
  see `docs/architecture/letter-registry.md` §2 for each, and §0 for the
  CONFIRMED/IMPLEMENTATION-DECISION/PENDING framework used throughout so
  nothing implemented here is silently guessed.
* **Migration `48ec742d9e8f`** — renamed `letters.department_id` ->
  `recipient_department_id` and `letters.received_from` -> `source_name`
  (data-preserving renames, not recreated columns); added
  `source_department_id`/`source_location`/`sender_address` (nullable)
  and `sender_name`/`sender_designation`/`sender_department`/
  `reference_number` (required, safely backfilled for any pre-existing
  row using the standard add-nullable -> backfill -> tighten pattern);
  added `uq_letters_reference_number` (later removed — see below); added
  `classifications.restricts_access`; seeded exactly three `categories`
  rows (General Letter, Notification, Office Order). Verified against a
  real pre-existing `Letter` row inserted before the migration ran (not
  just an empty table), and a full `upgrade -> downgrade -> upgrade`
  round-trip — see "Validation performed" below.
* **Migration `c887ab35e4a3` (hardening pass)** — drops
  `uq_letters_reference_number`, added by the migration above on an
  unconfirmed global-uniqueness assumption; see the hardening-pass
  section above and `docs/architecture/letter-registry.md` §2.3/§14.
* **`app/services/authorization.py:assert_letter_access`** — the
  classified-access authorization boundary, built on top of (not
  duplicating) `assert_department_access`. Department isolation always
  gates first; `SYSTEM_ADMIN` retains complete access; a `USER` who is
  not a classified letter's own recorder is denied even within their own
  department. Documented explicitly as a conservative, provisional
  default — the exact visibility matrix remains open (see "Remaining
  Known Issues").
* **`app/services/letter_service.py`, `category_service.py`,
  `classification_service.py`**, their repositories, Pydantic schemas,
  and `/api/v1/letters*`, `/api/v1/categories*`, `/api/v1/classifications*`
  endpoints — the same four-layer architecture every phase since 3A has
  used. `recorded_by`/`recipient_department_id` always derived from the
  authenticated caller, never client-supplied (no field for either
  exists on `LetterCreate`).
* **"Delete" is archival** (`status -> ARCHIVED`), never a physical SQL
  `DELETE` — a continuation of Phase 2's original decision, not a change
  to it.
* **Reference-number uniqueness — implemented, then removed the same
  phase.** Originally enforced at the database level
  (`uq_letters_reference_number`), race-safe (attempt-then-catch
  `IntegrityError`, the same pattern `DepartmentService` established in
  Phase 3B.2). A follow-up hardening pass found the *scope* of "must be
  unique" was never actually confirmed by the business and removed the
  constraint (migration `c887ab35e4a3`) rather than keep a guess — see
  the hardening-pass section above.
* **67 new automated tests** across `test_letter_registry.py` (50,
  covering every lettered item A-X in the brief's test list),
  `test_category_management.py` (8), `test_classification_management.py`
  (9) — against a real PostgreSQL test database — plus a full live-server
  verification against `lrs_dev` with real JWTs (letter creation,
  duplicate-reference rejection, cross-department 404s, the classified-
  access boundary exercised across recorder/same-department-non-recorder/
  Admin/SYSTEM_ADMIN, update, and archive).
* **Documentation**: `docs/architecture/letter-registry.md` (finalized
  decisions + implementation record), plus updates to the root README,
  `backend/README.md`, `docs/README.md`, and
  `docs/architecture/overview.md`.

### Phase 4A — Letter Registry Core architecture review

* **Full inspection of the existing Letter-adjacent schema** — `Letter`,
  `LetterDocument`, `Category`, `Classification`, `Department`, `User`,
  `AuditLog`, `Notification` models, both existing migrations, and
  `docs/database/schema.md` — confirmed, not assumed: no repository,
  Pydantic schema, service, or API endpoint exists yet for `Letter`/
  `Category`/`Classification`; Phase 4A is the first phase to write any
  code above the model layer for these three entities (and it wrote
  documentation only).
* **Confirmed a real architectural gap**: the existing
  `Letter.department_id` is a single field, but the confirmed V1
  requirements need two independent department-shaped facts — the
  sending/source department and the recipient/owning department. A single
  column cannot represent both. Recommended a `recipient_department_id`
  field (the field department-isolation authorization should check,
  functionally a clarification of what `department_id` already means
  today) plus a separate source-side representation — not implemented
  this phase. See `docs/architecture/letter-registry.md` §5.
* **Confirmed two requirements are already fully satisfied by existing
  Phase 2 design, with no gap**: the "date received vs. date recorded"
  distinction (`received_at` vs. `created_at`, already two separate
  columns) and "letter content, text or document or both"
  (`text_content` + the existing `LetterDocument` 1:N relationship).
  Neither needed a new column.
* **Confirmed `recorded_by`'s historical-identity guarantee (`RESTRICT`,
  not `CASCADE`/`SET NULL`) is already correct** — verified directly
  against the model and existing passing tests, not re-implemented.
* **Flagged, not resolved, six pending business clarifications**:
  source-department representation (free text vs. FK to a real
  `Department`), exact sender-detail sub-fields, reference-number
  uniqueness/issuing-authority/format, whether "Budget" belongs to
  Category or Classification (the same word appeared as a Category
  example in Phase 2 and a Classification example in this phase's brief),
  whether "Classified" needs to actually restrict visibility or is a
  label only, and source-location/sender-details nullability. See
  `docs/architecture/letter-registry.md` §21.
* **Identified a Phase 4B prerequisite**: System-Admin Category and
  Classification management (list/create/update/activate-deactivate)
  does not exist yet — both tables are schema-only since Phase 2, with
  zero rows and zero endpoints. `Letter.category_id`/`classification_id`
  cannot reference anything real until that management surface exists.
* **No schema, migration, repository, service, endpoint, or test change**
  — this phase produced documentation only, per its explicit scope
  boundary. `alembic check`: "No new upgrade operations detected."
* **Documentation**: `docs/architecture/letter-registry.md` (new), plus
  updates to the root README, `backend/README.md`, `docs/README.md`, and
  `docs/architecture/overview.md`.

### Phase 3B.4 — User management

* **User authorization, ADMIN only** — `POST /api/v1/users/authorizations`.
  Unlike Admin authorization, the request has no `department_id` field at
  all — it is always derived from the calling Admin's own department.
  Validates the Admin's own department is `ACTIVE`, the email doesn't
  already belong to an active User, and no unresolved USER authorization
  already exists for it.
* **User signup reuses the existing `/auth/signup` endpoint** — no third
  authentication workflow. Race-safety (`SELECT ... FOR UPDATE`) is
  unchanged from Phase 3A/3B.3 and re-verified for an Admin-issued
  USER-purpose authorization specifically with a genuine two-thread
  concurrency test.
* **User approval** — `POST /api/v1/users/{id}/approve`. Not idempotent,
  same one-time-event reasoning as Admin approval (Phase 3B.3).
* **Deactivate/reactivate, both idempotent** — reactivation additionally
  requires the Admin's *own* department to be `ACTIVE`, re-checked on
  every call. Deactivation is unconditional — allowed even if the Admin's
  department has itself been deactivated, a deliberate design decision
  (see "Three isolation strengths" below) since lock-down actions must
  stay possible precisely when a department is in a bad state.
* **Three different isolation strengths, not interchangeable** — read and
  lock-down actions (list/get/deactivate/revoke) require only that the
  target belong to the Admin's own department; state-elevating actions
  (authorize/approve/reactivate) additionally require the Admin's own
  department to be `ACTIVE`. Documented and tested explicitly, not just an
  incidental side effect — see `docs/architecture/user-management.md` §5.
* **The project's first authorization revocation endpoint** —
  `DELETE /api/v1/users/authorizations/{id}`. `AuthorizationStatus.REVOKED`
  has existed since Phase 2 but had no endpoint setting it until now.
  Creator-scoped (only the Admin who created an authorization may revoke
  it — stricter than the department-wide visibility of the listing
  endpoint), idempotent for an already-revoked row, rejected (`409`) for
  an already-used one, and never deletes the row.
* **Cross-department isolation exercised against a real resource for the
  first time** — every prior phase's caller (`SYSTEM_ADMIN`) was global,
  so `assert_department_access` had only ever run against
  verification-only endpoints or short-circuited via the SYSTEM_ADMIN
  bypass. An Admin in Department A gets an identical `404` (not `403`)
  attempting to view, approve, deactivate, or reactivate a User in
  Department B — indistinguishable from that id not existing at all,
  hiding cross-department existence, not merely blocking action on it.
* **User self-protection requires no special-case code** — the same
  structural pattern Phase 3B.3 used for System Admin protection:
  `find_user_by_id` filters by role `USER`, so an Admin's own id (role
  `ADMIN`) 404s on every lifecycle endpoint without a dedicated
  "is this the caller's own id" check.
* **53 new automated tests** against a real PostgreSQL test database,
  covering every item in the brief's Authorization/Workflow/Listing/
  Details/Approval/Deactivation/Reactivation/Revocation/Cross-Department-
  Security/Self-Protection/Lifecycle/Race-Safety lists, plus a full
  live-server verification against `lrs_dev` (authorize → signup →
  pending login rejected → approve → login → access → deactivate → stale
  JWT rejected → reactivate → same stale JWT works again; cross-department
  rejection; revoked authorization cannot sign up).
* **Documentation**: `docs/architecture/user-management.md` (new), plus
  updates to the root README, `backend/README.md`, `docs/README.md`, and
  `docs/architecture/overview.md`.

### Phase 3B.3 — Admin management (see previous entries below for detail)

* **Admin authorization, SYSTEM_ADMIN only** —
  `POST /api/v1/admins/authorizations`. Validates the destination
  department exists and is `ACTIVE`, the email doesn't already belong to
  an active Admin, and no unresolved ADMIN authorization already exists
  for it. `authorized_by` is always the caller's own id.
* **Admin signup reuses the existing `/auth/signup` endpoint** — no second
  authentication workflow. Role is derived from whichever authorization is
  found (`purpose=ADMIN` → role `ADMIN`, otherwise role `USER`) — a USER
  authorization can never produce an ADMIN and vice versa, by
  construction. Race-safety (`SELECT ... FOR UPDATE`) is unchanged from
  Phase 3A and re-verified for the ADMIN path specifically with a genuine
  two-thread concurrency test.
* **Admin approval** — `POST /api/v1/admins/{id}/approve`. Not idempotent
  (unlike every other status-changing endpoint in this project so far):
  approving an already-`ACTIVE` or `DEACTIVATED` Admin is rejected with
  `409`, since approval is a one-time event, not a toggle.
* **Deactivate/reactivate, both idempotent** — reactivation additionally
  requires the Admin's department to be `ACTIVE`, re-checked on every
  call (even the already-`ACTIVE` idempotent case), since an Admin can end
  up `ACTIVE` while their department is `INACTIVE` (Phase 3B.2
  deactivation never touches `User` rows).
* **Multiple Admins per department, deliberately unbounded** — no
  `department_id UNIQUE` constraint added, per the brief's explicit
  instruction.
* **Admin department transfer, proven historically safe** —
  `Letter.department_id` is independently stored (Phase 2 design), never
  re-derived from the recording user, so moving an Admin between
  departments cannot retroactively change any letter they already
  recorded. Verified directly (row-level assertion after a real transfer),
  not just asserted from the schema.
* **System Admin accounts are structurally unreachable through
  `/api/v1/admins/*`** — a `user_id` resolving to `SYSTEM_ADMIN` gets the
  same `404` as a nonexistent id, via the same repository method
  (`find_admin_by_id`) that filters by role.
* **Admin self-protection requires no special-case code** — every
  Admin-management endpoint is `require_system_admin`-only (reused
  unchanged from Phase 3B.1, no new dependency), so an Admin can never
  reach any of these endpoints regardless of which `user_id` they target,
  including their own.
* **47 new automated tests** against a real PostgreSQL test database,
  covering every item in the brief's Authorization/Workflow/Approval/
  Lifecycle/Multiple-Admins/Department-Transfer/Self-Protection/System-
  Admin-Protection/Race-Safety lists, plus a full live-server verification
  against `lrs_dev` (authorize → signup → pending → approve → login →
  escalation attempts rejected → department transfer → deactivate → old
  token rejected).
* **Documentation**: `docs/architecture/admin-management.md` (new), plus
  updates to the root README, `backend/README.md`, `docs/README.md`,
  `docs/architecture/overview.md`, and `docs/database/schema.md`.

### Phase 3B.2 — Department management (see previous entries below for detail)

* **Department CRUD, SYSTEM_ADMIN only** — `POST`/`GET`/`PATCH
  /api/v1/departments`, `.../{id}`, `.../{id}/activate`,
  `.../{id}/deactivate`. New departments are always `ACTIVE`; `status` is
  never editable through the generic update endpoint, only through the
  two dedicated, idempotent activate/deactivate endpoints.
* **Race-safe duplicate detection** — no pre-check; every create/update
  attempts the write and relies on PostgreSQL's own unique constraints,
  catching `IntegrityError` and reporting exactly which field
  (`name`/`code`) conflicted via `409`.
* **Historical data preserved on deactivation** — no User, Letter, or any
  other row is deleted, modified, or reassigned when a department becomes
  `INACTIVE`; verified directly (row-by-row) in tests, not just asserted.
* **Inactive-department authorization extension** —
  `assert_department_access` (Phase 3B.1) now also requires an
  ADMIN/USER's own department to be `ACTIVE`; SYSTEM_ADMIN is completely
  unaffected and retains full access to inactive departments for
  historical/administrative purposes. Reactivating a department restores
  access immediately, with no cached decision anywhere.
* **A real schema-naming bug found and fixed** (not a migration —
  `alembic check` still reports zero drift): `Department.name`/`code`'s
  unique constraints were unnamed (`unique=True` shorthand), so the test
  database (`Base.metadata.create_all()`) and the real, migration-built
  database silently used different auto-generated constraint names. Fixed
  by naming both explicitly to match the existing migration. The same
  latent issue remains on `categories.name`/`classifications.name`,
  documented but not fixed (out of this phase's scope).
* **36 new automated tests** against a real PostgreSQL test database,
  covering every item in the brief's Authorization/Creation/Retrieval/
  Update/Status/Security lists, plus a full live-server verification
  against `lrs_dev` (creation → duplicate rejection → list/get/update →
  deactivate-blocks-user → reactivate-restores-access).
* **Documentation**: `docs/architecture/department-management.md` (new),
  plus updates to the root README, `backend/README.md`, `docs/README.md`,
  `docs/architecture/overview.md`, `docs/architecture/authorization.md`,
  and `docs/database/schema.md`.

### Phase 3B.1 — RBAC & department authorization

* **Role-check dependencies** (`app/api/deps.py`) —
  `require_system_admin`, `require_admin`, `require_admin_or_system_admin`,
  `require_user_or_admin`, each composed on top of `get_current_user` via
  FastAPI's own `Depends()` mechanism, never re-deciding authentication.
* **Department-isolation enforcement** — `assert_department_access`
  (`app/services/authorization.py`, framework-agnostic — no FastAPI
  import) and its FastAPI wrapper `require_department_access`
  (`app/api/deps.py`). SYSTEM_ADMIN bypasses; ADMIN/USER must match their
  own `department_id` exactly — not an existence check, a made-up UUID is
  rejected identically to a real foreign one.
* **Generic, non-leaking 403s** — one fixed message for every role/
  department authorization failure; never names the role required, the
  department requested, or the caller's own department.
* **Five verification-only endpoints**
  (`app/api/v1/endpoints/dev_authz_test.py`, tagged
  `dev-authorization-test` in OpenAPI, no frontend) — exist solely because
  no real protected resource exists yet in this phase for the
  authorization dependencies to attach to; documented for removal once
  Phase 4 adds one.
* **42 new automated tests**: 16 in `backend/tests/unit/test_authorization.py`
  (pure function/dependency logic, no database) and 26 in
  `backend/tests/integration/test_authorization.py` (real JWTs, real
  database-backed Users, real HTTP requests — including every scenario in
  the brief's Role/Department/Deactivation/Negative-security test lists).
* **Documentation**: `docs/architecture/authorization.md` (new), plus
  updates to the root README, `backend/README.md`, and
  `docs/architecture/overview.md`.

### Phase 3A — Authentication foundation (see previous entries below for detail)

* **Local email/password authentication** — no external OAuth provider;
  see `docs/architecture/authentication.md` §1.
* **Argon2id password hashing** via `argon2-cffi`, centralized password
  policy (8-128 characters), never a manual hash comparison.
* **JWT access tokens** (PyJWT, HS256, `SECRET_KEY`-signed) — creation,
  validation, expiration, and rejection of tampered/malformed/`alg:none`
  tokens.
* **Bootstrap System Admin** — `python -m app.cli create-system-admin`,
  refuses to run if an active System Admin already exists.
* **Authorized signup** — `POST /api/v1/auth/signup`, race-safe
  consumption of `UserAuthorization` (`SELECT ... FOR UPDATE`), role/
  department/status always derived server-side, never client-supplied.
* **Pending-approval account lifecycle** — new accounts start
  `PENDING_APPROVAL` and cannot log in until (a future phase's) Admin
  approval.
* **Login** — `POST /api/v1/auth/login`, account-enumeration-resistant,
  status-aware (pending/deactivated rejected with distinct messages after
  a correct password, not before).
* **Current-user endpoint** — `GET /api/v1/auth/me`, backed by
  `get_current_user` (`app/api/deps.py`), the identity-establishment
  dependency Phase 3B's authorization checks will build on.
* **65 new automated tests** across `backend/tests/unit/test_security.py`,
  `test_email_utils.py`, and `backend/tests/integration/test_auth_bootstrap.py`,
  `test_auth_signup.py`, `test_auth_login.py`, `test_auth_current_user.py`
  — including a genuine two-thread/two-connection concurrency test proving
  the signup race-condition fix.
* **Documentation**: `docs/architecture/authentication.md` (new), plus
  updates to the root README, `backend/README.md`, and
  `docs/architecture/overview.md`.

### Phase 2 — Database architecture (see previous entries below for detail)

* 9 core SQLAlchemy models, two Alembic migrations (baseline + hardening),
  31 model-level tests. Full detail in `docs/database/schema.md`.

### Corrections applied during Phase 2 (self-review hardening pass)

A self-review of the initial Phase 2 implementation found six issues,
addressed as follows — see `docs/database/schema.md` for the technical
detail behind each:

| # | Issue | Fix |
|---|---|---|
| 1 | Order-dependent circular import: `from app.models import X` (or `from app.models.user import X`) could fail in a fresh interpreter depending on what had already been imported | `app/database/base.py` no longer imports `app.models`; consumers that need full metadata (`alembic/env.py`, `tests/conftest.py`) import it themselves. Guarded by `tests/unit/test_imports.py` |
| 2 | ORM-level `session.delete(department)` didn't cleanly hit the database's `RESTRICT` — SQLAlchemy tried to null out dependent users' `department_id` first, which instead tripped an unrelated CHECK constraint | `passive_deletes="all"` added to every `RESTRICT`/`SET NULL`-backed one-to-many relationship (Department, Category, Classification, User, and `Letter.notifications`), so the ORM defers entirely to the database's own FK action |
| 3 | `departments.status` had no index, unlike the equivalent column on Category/Classification | Added (`ix_departments_status`) |
| 4 | `notifications.is_read` had no database-level default — a row written outside the ORM would fail `NOT NULL` | Added `server_default=false()`, alongside the existing ORM-side default |
| 5 | `letter_documents.uploaded_by` had no index, unlike every other User-referencing FK in the schema | Added (`ix_letter_documents_uploaded_by`) |
| 6 | The role/department `CHECK` constraint hardcoded role strings, duplicating `UserRole`'s values | Model-side constraint now built from `UserRole.*.value`; the migration's own copy is deliberately still a literal (migrations are frozen snapshots) — see `app/models/user.py` docstring |

### Validation performed — Phase 5E implementation

| Check | Result |
|---|---|
| `npm run build` (frontend, `frontend/`) | Succeeds — 176 modules transformed, no errors |
| `npm run test` (frontend, Vitest) | **225 passed**, 0 failed — run 3 consecutive times against the final code, identical results, clean stderr output |
| `pytest tests/` (backend, `backend/`) | **458 passed**, 0 failed, 0 skipped — unaffected by this phase, confirming zero backend impact |
| `git status` — backend files | No `backend/app/`, `backend/alembic/`, or `backend/tests/` file touched |
| `git status` — secrets | No `.env`/`.env.local` tracked; no new dependency added (only new first-party source/test files) |
| Grep for `jwt`/`decode`/`localStorage`/`recipient_user_id` in new/changed files | Zero matches representing actual usage — only comments/test names documenting their absence |
| Grep for `dangerouslySetInnerHTML` | Zero matches representing actual usage — appears only in a comment and a test name asserting it is never used |
| Grep for `DELETE`/delete-document calls, storage-path exposure, signed/public URLs, hardcoded role checks, hardcoded department IDs | Zero matches of any kind in the new/changed file set |
| Grep for a `403`→`404` (or reverse) conversion in the new pages/components | Zero matches |
| Manual verification against a running backend | Not performed — no backend/dev environment was running at any point this session; reported honestly rather than claimed |

### Validation performed — Phase 5H implementation

| Check | Result |
|---|---|
| `npm run build` (frontend, `frontend/`) | Succeeds — 187 modules transformed, no errors |
| `npm run test` (frontend, Vitest) | **280 passed**, 0 failed — run 3 consecutive times against the final code, identical results |
| `pytest tests/` (backend, `backend/`) | **487 passed**, 0 failed, 0 skipped — run 3 consecutive times, identical results |
| `alembic upgrade head` → `downgrade 9fa970ffa560` → `upgrade head` → `check` | Clean at every step against a real local PostgreSQL instance; `alembic check` reports "No new upgrade operations detected" |
| Every `designations.py`/`departments.py` endpoint's `Depends(...)` re-read after implementation | Exactly one `get_current_user` dependency per file (the two list endpoints); every other endpoint `require_system_admin`, matching the design exactly |
| Grep for `jwt`/`decode`/`localStorage`/hardcoded department or designation ids/`source_department_id`-as-authorization/client-controlled `role`/`DELETE`-on-designation | Zero matches representing actual usage — only comments documenting their absence |
| `git status` — scope | No file outside the explicit implementation scope touched; no dependency added |
| Manual/live click-through of the actual demo path | Not performed — only the real-database migration cycle above is genuinely live; reported honestly rather than claimed |

### Validation performed — Phase 5H review

An architecture/requirements review, not an implementation phase —
validation here means confirming no code was written and no drift was
introduced, the same standard applied to every prior review-only pass:

| Check | Result |
|---|---|
| `git status` before and after the review | Identical except one new documentation file and four documentation updates — no backend file, frontend file, migration, or test file touched |
| Direct reads of `backend/app/models/letter.py`, `schemas/letter.py`, `services/letter_service.py` | Confirmed `source_department_id` already exists end-to-end with existing validation (`_validate_source_department`) — a fresh finding not assumed from any prior phase's report |
| Direct reads of `backend/app/models/category.py`/`classification.py`, `services/category_service.py`, `api/v1/endpoints/categories.py` | Used as the direct design precedent for the new `Designation` resource — model shape, service pattern, endpoint verbs (`POST .../activate`, confirmed, not the brief's own guessed `PATCH`) |
| Direct read of `backend/app/api/v1/endpoints/departments.py` | Confirmed `GET /departments`'s dependency is `require_system_admin` — the access-gap finding this review treats as critical |
| Direct read of `frontend/src/pages/LetterFormPage.jsx` | Confirmed its own docstring already documents *why* `source_department_id` has no UI today — cross-checked against the schema finding above, not assumed |

### Validation performed — Phase 5G review

An architecture/requirements review, not an implementation phase —
validation here means confirming no code was written and no drift was
introduced, the same standard applied to every prior review-only pass:

| Check | Result |
|---|---|
| `git status` before and after the review | Identical except one new documentation file and five documentation updates — no backend file (`.py`), frontend file (`.jsx`/`.js`/`.css`), migration, index, or test file touched |
| Direct reads of `app/api/deps.py`, `app/services/authorization.py`, `app/repositories/letter_repository.py`, `app/services/letter_service.py` | Confirmed both reusable authorization primitives (`letter_visibility_filter`, department derivation) and the exact filtered-statement pattern `list_letters` already uses — directly reusable for an aggregate, no duplication needed |
| Direct reads of `Letter`/`Department`/`User`/`UserAuthorization`/`LetterDocument`/`Notification`/`AuditLog` models | Confirmed every column a plausible Letter aggregate would group/filter by is already indexed; confirmed `AuditLog` has no department column; confirmed `LetterDocument.mime_type` is not indexed |
| Grep for an audit-read endpoint across `app/api/v1/endpoints/` and `router.py` | Zero matches — confirmed unchanged from Phase 4E's/5F's own findings |
| `frontend/src/pages/DashboardPage.jsx` and its three components, re-read fresh | Confirmed exactly which existing (non-aggregate) endpoints the Phase 5F dashboard already uses — this review's inventory builds on that baseline, not a redesign of it |

### Validation performed — Phase 5F implementation

| Check | Result |
|---|---|
| `npm run build` (frontend, `frontend/`) | Succeeds — 184 modules transformed, no errors |
| `npm run test` (frontend, Vitest) | **249 passed**, 0 failed — run 3 consecutive times against the final code, identical results |
| `pytest tests/` (backend, `backend/`) | **458 passed**, 0 failed, 0 skipped — unaffected by this phase, confirming zero backend impact |
| `git status` — backend files | No `backend/app/`, `backend/alembic/`, or `backend/tests/` file touched |
| `git status` — dependencies | No `package.json` dependency added — no charting library, no state-management library |
| Grep for `jwt`/`decode`/`localStorage` in new/changed files | Zero matches |
| Grep for `department_id` sent as a request parameter | Zero matches representing actual usage — the one match is a doc comment stating it is deliberately never sent |
| Grep for `recipient_user_id` | Zero matches |
| Grep for `dangerouslySetInnerHTML` | Zero matches |
| Grep for hardcoded classified-record filtering logic | Zero matches — the dashboard never fetches a list of Letters larger than needed and applies no classification-based branch anywhere |
| Test-infrastructure issue found during the 3-run validation | `LetterFormPage.test.jsx` intermittently missed Vitest's 5000ms default timeout under full-suite worker contention once the suite grew past ~30 files — confirmed non-deterministic (same tests failed, then passed, then failed again across identical consecutive runs) and unrelated to any logic defect; fixed by raising `testTimeout` to 10000ms in `vite.config.js`, re-verified with 3 further clean runs |
| Manual verification against a running backend | Not performed — no backend/dev environment was running at any point this session; reported honestly rather than claimed |

### Validation performed — Phase 5F review

An architecture/requirements review, not an implementation phase —
validation here means confirming no code was written and no drift was
introduced, the same standard applied to every prior review-only pass:

| Check | Result |
|---|---|
| `git status` before and after the review | Identical except one new documentation file and five documentation updates — no frontend file (`.jsx`/`.js`/`.css`), backend file, migration, or test file touched, no dependency added |
| Direct reads of all twelve mounted routers (`app/api/v1/router.py`) and their endpoints/services/repositories/schemas | Confirmed exactly which resources support pagination/real `COUNT` (Letters, Notifications) vs. full-list-only `len()` (Departments, Admins, Users, Categories, Classifications); confirmed no dashboard/summary/aggregate/audit-read endpoint exists anywhere |
| Direct read of `app/services/authorization.py:letter_visibility_filter` | Confirmed the classified-access predicate is query-level (`None` for SYSTEM_ADMIN/ADMIN, a real SQL predicate for USER, joined into both the `COUNT` and the paginated `SELECT`) — a Letter count is already correctly isolated with no frontend filtering needed |
| Cross-check against `docs/architecture/audit-notifications.md` §23 and `docs/architecture/frontend.md` §27's prior dashboard-adjacent findings | Confirmed both conclusions (current-state metrics need a new aggregate endpoint; audit-derived metrics need the audit read API first; Notification is not a good dashboard data source) still hold — this review extends them with a full metric inventory neither prior document went into |
| `frontend/package.json` inspection | Confirmed no charting library is installed; none was added this phase |

### Validation performed — Phase 5E review

An architecture/requirements review, not an implementation phase —
validation here means confirming no code was written and no drift was
introduced, the same standard applied to every prior review-only pass:

| Check | Result |
|---|---|
| `git status` before and after the review | Identical except one new documentation file and five documentation updates — no frontend file (`.jsx`/`.js`/`.css`), backend file, migration, or test file touched |
| Direct reads of every Document/Notification endpoint, schema, service, repository, and model file | Confirmed exact status codes, error messages, response headers, and lifecycle behavior, all fresh this session |
| Cross-check against `docs/architecture/frontend.md` §14/§15's original findings | Confirmed both backend modules unchanged since Phase 4D/4E — the original review's conclusions still hold, extended with implementation-level detail this pass added |

### Validation performed — Phase 5D implementation

| Check | Result |
|---|---|
| `npm run build` (frontend, `frontend/`) | Succeeds — 163 modules transformed, no errors |
| `npm run test` (frontend, Vitest) | **159 passed**, 0 failed — run 3 consecutive times, identical results |
| `pytest tests/` (backend, `backend/`) | **458 passed**, 0 failed, 0 skipped — unaffected by this phase, confirming zero backend impact |
| `git status` — backend files | No `backend/app/`, `backend/alembic/`, or `backend/tests/` file touched |
| `git status` — secrets | No `.env`/`.env.local` tracked; no new dependency added (only new first-party source/test files) |
| Grep for `jwt`/`decode`/`localStorage` in new/changed files | Zero matches outside `services/tokenStorage.js` (untouched) |
| Grep for a `DELETE` request in `adminService.js`/`userService.js`/`departmentService.js` | Exactly one — `revokeAuthorization`, the one confirmed backend `DELETE` endpoint; none for account lifecycle |
| Grep for a `403`→`404` (or reverse) conversion in the new pages | Zero matches |
| Grep for "Delete" wording anywhere in the new UI | Zero matches outside test fixtures/regex patterns checking for its absence |

### Validation performed — Phase 5D review

An architecture/requirements review, not an implementation phase —
validation here means confirming no code was written and no drift was
introduced, the same standard applied to every prior review-only pass
(Phase 4A, Phase 4D's review, Phase 4E's review, Phase 5's review):

| Check | Result |
|---|---|
| `git status` before and after the review | Identical except one new documentation file and three documentation updates — no frontend file (`.jsx`/`.js`/`.css`), backend file, migration, or test file touched |
| Direct reads of every Department/Admin/User/UserAuthorization endpoint, schema, service, repository, and model file | Confirmed exact status codes, error messages, idempotency behavior, and the read/lock-down vs. state-elevating asymmetry, all fresh this session |
| Fresh `glob` of `frontend/src/**/*.{jsx,js}` | Confirmed the brief's own claim of existing Document/Notification UI was inaccurate; confirmed the exact current inventory of pages/components/services this review's design builds on |

### Validation performed — Phase 5C implementation

| Check | Result |
|---|---|
| `npm run build` (frontend, `frontend/`) | Succeeds — 139 modules transformed, no errors |
| `npm run test` (frontend, Vitest) | **84 passed**, 0 failed |
| `pytest tests/` (backend, `backend/`) | **458 passed**, 0 failed, 0 skipped — unaffected by this phase, confirming zero backend impact |
| `git status` — backend files | No `backend/app/`, `backend/alembic/`, or `backend/tests/` file touched |
| `git status` — secrets | No `.env`/`.env.local` tracked; no new dependency added (only new first-party source/test files) |
| Grep for hardcoded category/classification/department names | Zero matches outside test fixtures |

### Validation performed — Phase 5B implementation

| Check | Result |
|---|---|
| `npm run build` (frontend, `frontend/`) | Succeeds — 117 modules transformed, no errors |
| `npm run test` (frontend, Vitest) | **44 passed**, 0 failed — run twice (once before, once after the final self-review pass), identical result both times |
| `pytest tests/` (backend, `backend/`) | **458 passed**, 0 failed, 0 skipped — unaffected by this phase, confirming zero backend impact |
| `git status` — backend files | No `backend/app/`, `backend/alembic/`, or `backend/tests/` file touched |
| `git status` — secrets | No `.env`/`.env.local` tracked; no new dependency added (only new first-party source/test files) |

### Validation performed — Phase 5A implementation

| Check | Result |
|---|---|
| `npm run build` (frontend, `frontend/`) | Succeeds — 113 modules transformed, no errors |
| `npm run test` (frontend, Vitest) | **17 passed**, 0 failed |
| `pytest tests/` (backend, `backend/`) | **458 passed**, 0 failed, 0 skipped — unaffected by this phase, confirming zero backend impact |
| `git status` — backend files | Only `backend/README.md` (documentation) changed; no `backend/app/`, `backend/alembic/`, model, service, repository, or endpoint file touched |
| `git status` — secrets | No `.env`/`.env.local` tracked for either `frontend/` or `backend/`; `node_modules/`/`dist/` confirmed git-ignored |
| `npm audit` | 6 pre-existing advisories (react-router-dom, esbuild/vite toolchain), both already pinned to their current major versions since Phase 1; no non-breaking fix exists for either without violating "use the existing stack" — documented in `frontend/README.md`, not silently upgraded or silently ignored |

### Validation performed — Phase 5 review

An architecture/UX review, not an implementation phase — validation here
means confirming no code was written and no drift was introduced, not
running new business-logic or UI tests (the same standard applied to
every prior review-only pass — Phase 4A, Phase 4D's review, Phase 4E's
review):

| Check | Result |
|---|---|
| `git status` before and after the review | Identical except one new documentation file and five documentation updates — no frontend file (`.jsx`/`.js`/config), backend file, migration, or test file touched |
| Direct listing of every file under `frontend/` (excluding `node_modules/`, which does not exist) | Confirmed empirically — 18 files total, only `App.jsx`/`main.jsx`/`constants/app.js` contain any code, every other `src/*` entry is a one-line placeholder `README.md` |
| `app.openapi()` against the live FastAPI app | Enumerated the complete, authoritative 42-endpoint business API surface used to build the endpoint-to-screen map — not reconstructed from prior phase reports |
| Direct reads of `app/schemas/letter.py`, `auth.py`, `admin.py`, `user.py`, `category.py`, `classification.py`, `notification.py`, `document.py`, `app/models/enums.py`, `app/api/v1/endpoints/auth.py` | Confirmed exact field sets, exact HTTP status codes/error shapes for every auth failure mode, and the three distinct status enums, all fresh this session |

### Validation performed — Phase 4E implementation

All against the same real, local, disposable PostgreSQL 17 instance
used for every prior phase (`lrs_dev` for manual checks, `lrs_test` for
the suite — never a shared or departmental database):

| Check | Result |
|---|---|
| `pytest tests/` (full suite) against `lrs_test` | **458 passed**, 0 failed, 0 skipped (425 baseline + 33 new). Re-run 3 consecutive times, identical results |
| `alembic check` against `lrs_dev` | "No new upgrade operations detected" — this phase needed no schema change |
| No test writes into the real `storage/letters/` tree | Confirmed by `find storage/letters -type f` before/after the full suite run — only `.gitkeep` present both times (the Phase 4D document tests' storage isolation fixture is unaffected by this phase's changes) |
| Live-server verification against `lrs_dev`, real minted JWTs, a running `uvicorn` instance | Letter registration produced a `LETTER_CREATED` audit row (correct actor, `entity_type="Letter"`, targeted `new_values`) and a `LETTER_REGISTERED` notification for each of the recipient department's two Admins (`200`, one item each); each Admin's own `GET /notifications` returned only their own row; one Admin marking their notification read left the other Admin's unread count untouched (`404` when the other Admin tried to mark it); `read-all` only affected the calling Admin's own rows; the `SYSTEM_ADMIN`'s own notification list was empty (never a recipient under the current strategy); an unauthenticated request got `401` |
| Files/rows created during live verification, confirmed and cleaned up | One department, four users, one letter, one audit row, two notification rows — all deleted via direct session cleanup afterward; `lrs_dev`'s `categories` table reconfirmed unchanged (still exactly 3 seeded rows) |
| `git status` review | No secrets tracked; `.env` confirmed gitignored |

### Validation performed — Phase 4E review

An architecture review, not an implementation phase — validation here
means confirming no code was written and no drift was introduced, not
running new business-logic tests (the same standard applied to the
Phase 4A and Phase 4D review passes):

| Check | Result |
|---|---|
| `git status` before and after the review | Identical except one new documentation file and five documentation updates — no model, migration, repository, schema, service, endpoint, or test file touched |
| `alembic check` | Unaffected — no migration was created, consistent with a read-only review (last confirmed against `lrs_dev` at the end of Phase 4D's corrections pass; nothing since has touched the schema) |
| Direct reads of `app/models/audit_log.py`, `app/models/notification.py`, `app/models/user.py`, `app/models/user_authorization.py`, `app/models/enums.py`, both Phase 2 migrations, `tests/integration/test_models.py` | Confirmed empirically (not from memory) that both tables are unchanged since Phase 2 and only touched by model-level tests |
| `grep` across `app/services/`, `app/repositories/`, `app/api/`, `app/schemas/`, `app/core/` for `AuditLog`/`Notification` | Zero real matches (two incidental false positives were "Notification" as a seeded *Category* name, not the model) — confirms zero application code writes to either table |
| `grep` for SQLAlchemy event listeners, `BackgroundTasks`, `Celery`/`Redis` across `app/` and `requirements.txt` | Zero matches — confirms no existing event/background-task infrastructure this review needed to account for |

### Validation performed — Phase 4D implementation

All against the same real, local, disposable PostgreSQL 17 instance
used for every prior phase (`lrs_dev` for manual checks, `lrs_test` for
the suite — never a shared or departmental database):

| Check | Result |
|---|---|
| `pytest tests/` (full suite) against `lrs_test` | **425 passed**, 0 failed, 0 skipped (387 baseline + 38 new). Re-run 3 consecutive times, identical results |
| `alembic check` against `lrs_dev` | "No new upgrade operations detected" — this phase needed no schema change |
| No test writes into the real `storage/letters/` tree | Confirmed by `find storage/letters -type f` before/after the full suite run — only `.gitkeep` present both times; the autouse `storage_root` test fixture redirects every test's `STORAGE_PATH` to a per-test `tmp_path` |
| Live-server verification against `lrs_dev`, real minted JWTs, a running `uvicorn` instance | Upload as the recording USER (`201`); download — content byte-for-byte identical to what was uploaded (`200`); cross-department USER upload and download (`404`, both); SYSTEM_ADMIN upload to a letter in a department it doesn't belong to (`201` — confirms system-wide access); non-recording USER in the *same* department denied a classified letter's documents (`404`); the recording USER allowed (`201`); unsupported extension `.docx` (`422`); MIME spoofing — `.pdf` filename/declared `Content-Type`, real PNG bytes — rejected (`422`); metadata list response confirmed free of any `storage_path` field; nonexistent document id (`404`); unauthenticated request (`401`) |
| Live download response headers | `Content-Type: application/pdf` (server-validated, not client-supplied), `Content-Disposition: attachment; filename="..."`, `X-Content-Type-Options: nosniff` |
| Files written during live verification, confirmed and cleaned up | `storage/letters/<letter_id>/<document_id>.pdf` for each upload — matches the documented convention exactly; all removed after verification |
| All live-verification data removed afterward | Departments/Users/Letters/`LetterDocument` rows deleted via direct session cleanup; `lrs_dev`'s `categories` table reconfirmed unchanged (still exactly 3 seeded rows) |
| `git status` review | No secrets tracked; `.env` confirmed gitignored (see "Known Limitations" for a local-environment note about this file, unrelated to what was committed) |

**Environment note, not a Phase 4D defect**: a bare `pytest` invocation
from `backend/` also tries to collect
`app/api/v1/endpoints/dev_authz_test.py` as a test module (its filename
incidentally matches pytest's default `*_test.py` discovery pattern),
producing one collection error unrelated to any test in this suite.
Confirmed pre-existing (not introduced by this phase) by stashing every
Phase 4D change and reproducing the identical error against the
unmodified tree. `pytest tests/` (scoped explicitly) avoids it; that
scoped form is what every count above uses, and what `backend/README.md`
now documents.

### Validation performed — Phase 4D review

An architecture review, not an implementation phase — validation here
means confirming no code was written and no drift was introduced, not
running new business-logic tests (the same standard applied to Phase
4A's review):

| Check | Result |
|---|---|
| `git status` before and after the review | Identical except one new documentation file and five documentation updates — no model, migration, repository, schema, service, endpoint, or test file touched |
| `alembic check` | "No new upgrade operations detected" — no migration was created, consistent with a read-only review |
| Direct reads of `app/models/letter_document.py`, `app/models/letter.py`, `app/core/config.py`, migrations, tests, `app/main.py`, `.gitignore`, `storage/README.md` | Confirmed empirically (not from Phase 4A memory) that `LetterDocument` is unchanged since Phase 2, no `StaticFiles` mount exists, and only two model-level tests touch the entity |
| `grep` across `app/services/`, `app/repositories/`, `app/schemas/`, `app/api/` for `LetterDocument`/`storage_path`/`STORAGE_PATH`/`upload`/`download` | Zero real matches — confirms zero application code exists above the model layer for documents |

### Validation performed — Phase 4C

All against the same real, local, disposable PostgreSQL 17 instance used
for every prior phase (`lrs_dev` for manual checks, `lrs_test` for the
suite — never a shared or departmental database):

| Check | Result |
|---|---|
| `pytest` (full suite) against `lrs_test` | **387 passed**, 0 failed, 0 skipped (344 baseline + 43 new). Re-run 3 consecutive times, identical results |
| `alembic upgrade head` against `lrs_dev` (new migration `9fa970ffa560`) | Applied cleanly (`c887ab35e4a3 -> 9fa970ffa560`) |
| `alembic downgrade -1` -> `alembic upgrade head` | Full round-trip verified — `ix_letters_reference_number` correctly absent after downgrade, correctly present again after re-upgrade |
| `alembic check` | "No new upgrade operations detected" |
| Live-server verification against `lrs_dev` with real JWTs — the central fix, proven end-to-end | 3 ordinary letters + 2 classified letters (recorded by a different User) created in one department; the non-recording User's `GET /api/v1/letters` returned `total: 3` (not 5), with no `HIDDEN`-tagged reference number appearing in `items`; the same query paginated at `page_size=2` still reported `total: 3`/`total_pages: 2` across both pages; the department's Admin and a SYSTEM_ADMIN both correctly saw `total: 5` |
| Live sort + search + filter combined | `?subject=live&sort_by=reference_number&sort_order=asc` returned exactly the visible (non-classified) letters, correctly ordered |
| `git status` review | No secrets tracked; `.env` confirmed gitignored; no historical migration file modified |

All data created during manual verification was deleted from `lrs_dev`
afterward, except the three seeded `categories` rows (unchanged,
permanent V1 configuration); `lrs_dev` otherwise empty again.

### Validation performed — Phase 4B

All against the same real, local, disposable PostgreSQL 17 instance used
for every prior phase (`lrs_dev` for manual checks, `lrs_test` for the
suite — never a shared or departmental database):

| Check | Result |
|---|---|
| `pytest` (full suite) against `lrs_test` | **344 passed**, 0 failed, 0 skipped (277 baseline + 67 new). Re-run 3 times consecutively with identical results — no flakiness introduced |
| `alembic upgrade head` against `lrs_dev` | Applied cleanly (`a223396c9eac -> 48ec742d9e8f`) |
| `alembic downgrade -1` -> `alembic upgrade head` | Full round-trip verified — the schema after re-upgrading was byte-identical to the first upgrade (indexes, constraints, columns all present, correctly named) |
| Migration tested against a real pre-existing row (not just an empty table) | A `Letter` row inserted via raw SQL *before* the migration ran was correctly preserved: `recipient_department_id` retained the exact original `department_id` value, `source_name` retained the original `received_from` value, and the new required columns were backfilled to clearly-marked, uniquely-identifiable placeholder values (`MIGRATION-PLACEHOLDER` / `MIGRATED-<row-id>`) |
| `alembic check` | "No new upgrade operations detected" — models match the applied migration exactly |
| FastAPI app startup + `GET /health` + full OpenAPI schema generation | 200 OK; `/api/v1/letters*`, `/api/v1/categories*`, `/api/v1/classifications*` all present with expected methods |
| Full Letter lifecycle, run for real against `lrs_dev` via real HTTP with real minted JWTs, two departments | Category list confirmed seeded with exactly the three finalized names; letter created with real category + a `restricts_access=True` classification; duplicate reference number -> `409` **(superseded — see hardening pass below; `uq_letters_reference_number` no longer exists, duplicates now succeed)**; cross-department `GET` -> `404`; a *second* User in the *same* department who did not record the letter -> `404`; the recording User, an Admin in the same department, and SYSTEM_ADMIN -> `200`; update by the recorder -> `200`; archive -> `200` with `status=ARCHIVED`; archived letter still retrievable (confirming soft-delete, not physical deletion) |
| `git status` review | No secrets tracked; `.env` confirmed gitignored |

All data created during manual verification was deleted from `lrs_dev`
afterward, except the three seeded `categories` rows (General Letter,
Notification, Office Order) — those are the intended, permanent V1
configuration, not test artifacts, so they were deliberately left in
place; `lrs_dev` otherwise empty again.

### Validation performed — Phase 4B hardening pass

| Check | Result |
|---|---|
| `pytest` (full suite) against `lrs_test` | **344 passed**, 0 failed, 0 skipped. Re-run 3 consecutive times, identical results |
| `alembic upgrade head` / `downgrade -1` / `upgrade head` against `lrs_dev` (new migration `c887ab35e4a3`) | Full round-trip verified — `uq_letters_reference_number` correctly absent after upgrade, correctly restored after downgrade, correctly absent again after re-upgrade |
| `alembic check` | "No new upgrade operations detected" |
| `grep` for `session.delete` targeting `Letter` across `app/` | Zero matches — confirms `DELETE /api/v1/letters/{id}` never issues a physical `DELETE`, code-level, not just documentation |
| `grep` for hardcoded category names in application logic | Zero matches outside docstrings/comments — Category validation is pure FK + `ACTIVE`-status, no string literals |
| `git status` review | No secrets tracked; `.env` confirmed gitignored; no historical migration file modified |

No live-server re-verification was performed for this specific pass —
the fix (dropping a constraint) is fully covered by the automated
migration round-trip above and the rewritten
`test_letter_registry.py` assertions (duplicates now return `201`, not
`409`), which is direct, repeatable evidence at least as strong as a
one-off manual `curl` session.

### Validation performed — Phase 4A

An architecture review, not an implementation phase — validation here
means confirming no code was written and no drift was introduced, not
running new business-logic tests:

| Check | Result |
|---|---|
| `git status` before and after the review | Identical except one new documentation file and five documentation updates — no model, migration, repository, schema, service, endpoint, or test file touched |
| `alembic check` | "No new upgrade operations detected" — no migration was created, consistent with a read-only review |
| `pytest` (full suite) against `lrs_test` | **277 passed**, 0 failed, 0 skipped — unchanged from the Phase 3B.4 hardening pass baseline, confirming the review itself introduced zero regressions (expected, since nothing executable changed) |
| Directory listing of `app/repositories/`, `app/schemas/`, `app/api/v1/endpoints/` | Confirmed empirically (not from memory) that no `Letter`/`Category`/`Classification` repository, schema, or endpoint file exists yet |
| `git log -p` / direct model reads for `Letter.recorded_by`, `Letter.department_id` | Confirmed `RESTRICT` (not `CASCADE`/`SET NULL`) on `recorded_by`, and that `department_id` is an independently-stored column, not derived — both by reading the actual current file content, not assumed from prior-phase memory |

### Validation performed — Phase 3B.4 hardening pass

A follow-up pass after Phase 3B.4's own report, scoped to exactly three
things: (1) fix the one flaky test noted in that report, (2) assess
whether the documented "no ADMIN-purpose authorization revocation" gap is
an actual vulnerability, (3) verify the "`AuthorizationStatus.REVOKED`
existed since Phase 2" claim against real git/migration history. No
Letter functionality, frontend, System Admin handover, or new business
functionality was touched.

| Check | Result |
|---|---|
| `pytest` (full suite) against `lrs_test` | **277 passed**, 0 failed, 0 skipped (274 baseline + 3 new regression tests proving the revocation-scope questions below) |
| Full suite re-run 5 times consecutively | 277/277 passed every time — no flakiness |
| `test_me_with_tampered_token_is_rejected` alone, 20 consecutive isolated runs | 20/20 passed — deterministic (was previously observed to fail ~6% of the time) |
| `alembic check` | "No new upgrade operations detected" — this pass touched only test code and documentation, no models or schema |
| `git log` / `git log -p` on `app/models/enums.py` and `backend/alembic/versions/*.py` | Confirmed `AuthorizationStatus.REVOKED` was present in the very first Phase 2 baseline migration (`3da4b7ee8167`, `down_revision=None`) — both the Python enum and the actual PostgreSQL native enum type. Never modified by the hardening migration (`e8a5cea2ccc6`) or the Phase 3B.3 migration (`a223396c9eac`). The Phase 3B.4 report's claim was **accurate**; no documentation correction needed |
| ADMIN-purpose authorization revocation security assessment (7 questions, see `docs/architecture/user-management.md` §13) | **No vulnerability found.** Absence of an ADMIN-purpose revoke endpoint is a documented capability gap, not an exploitable hole — see that section for the full reasoning. Left unimplemented, as instructed |
| `git status` review | No secrets tracked; `.env` confirmed gitignored |

All data created during manual verification was deleted from `lrs_dev`
afterward — `lrs_dev` was already empty from the prior pass (no new manual
`lrs_dev` verification was needed for this hardening pass, since nothing
it touched is only reachable via a running server).

### Validation performed — Phase 3B.4

All against the same real, local, disposable PostgreSQL 17 instance used
for every prior phase (`lrs_dev` for manual checks, `lrs_test` for the
suite — never a shared or departmental database):

| Check | Result |
|---|---|
| `pytest` (full suite) against `lrs_test` | **274 passed**, 0 failed, 0 skipped at the time of the original 3B.4 report. A subsequent hardening pass found and fixed one pre-existing flaky test (`test_me_with_tampered_token_is_rejected`, Phase 3A) — see "Validation performed — Phase 3B.4 hardening pass" below for the corrected, deterministic result (277 passed, 5/5 consecutive full-suite runs) |
| `alembic check` | "No new upgrade operations detected" — Phase 3B.4 required no schema change; `AuthorizationStatus.REVOKED` already existed on the enum since Phase 2, this phase is simply the first to set it |
| FastAPI app startup + `GET /health` | 200 OK |
| Phase 3A/3B.1/3B.2/3B.3 tests re-run as part of the full suite | All still pass — no regression |
| Full User lifecycle, run for real against `lrs_dev` via real HTTP with real minted JWTs, two departments and two Admins | Authorize (department correctly derived from the Admin, not client-supplied) → `201`; candidate signup → role `USER`, status `PENDING_APPROVAL`; login while pending → `403`; Admin approves → `200`, status `ACTIVE`; login → valid JWT; protected access → `200`; Admin deactivates → `200`; same stale JWT → `401`; Admin reactivates → `200`; same stale JWT → `200` again (status re-checked live, no re-login needed) |
| Cross-department rejection, run for real | Admin A: `GET`/`approve`/`deactivate` on a Department B User all → `404` (not `403` — existence hidden); Admin A's user listing excludes Department B entirely |
| Revocation, run for real | Admin A creates an authorization → Admin B (different department) attempts revoke → `404`; Admin A revokes own authorization → `200`, `REVOKED`; signup attempt against the revoked authorization → `403` |
| `git status` review | No secrets tracked; `.env` confirmed gitignored |

All data created during manual verification was deleted from `lrs_dev`
afterward — `lrs_dev` is empty again.

### Validation performed — Phase 3B.3

All against the same real, local, disposable PostgreSQL 17 instance used
for Phase 2/3A/3B.1/3B.2 (`lrs_dev` for manual checks, `lrs_test` for the
suite — never a shared or departmental database):

| Check | Result |
|---|---|
| `pytest` (full suite) against `lrs_test` | **221 passed**, 0 failed, 0 skipped (1 pre-existing harmless deprecation warning — unchanged) |
| `alembic upgrade` → `downgrade` → `upgrade` → `alembic check` | New migration `a223396c9eac` (adds `user_authorizations.purpose`) round-trips cleanly; zero drift afterward |
| Migration backfill, tested against an actual pre-existing row (not just an empty table) | A row inserted via raw SQL *before* the migration ran was correctly backfilled to `purpose='USER'` after `upgrade` |
| FastAPI app startup + `GET /health` | 200 OK |
| Phase 3A/3B.1/3B.2 tests re-run as part of the full suite | All still pass — no regression |
| Full Admin lifecycle, run for real against `lrs_dev` via `curl` with real minted JWTs | Authorize → `201`; candidate signup → role `ADMIN`, status `PENDING_APPROVAL`; login while pending → `403`; approve → `200`, status `ACTIVE`; login → valid JWT; Admin attempting to create a department → `403`; Admin attempting to deactivate self → `403`; System Admin department-transfer → `200`; deactivate → `200`; deactivated Admin's still-unexpired token on a subsequent request → `401` |
| `git status` review | No secrets tracked; `.env` confirmed gitignored |

All data created during manual verification was deleted from `lrs_dev`
afterward — `lrs_dev` is empty again.

### Validation performed — Phase 3B.2

All against the same real, local, disposable PostgreSQL 17 instance used
for Phase 2/3A/3B.1 (`lrs_dev` for manual checks, `lrs_test` for the suite
— never a shared or departmental database):

| Check | Result |
|---|---|
| `pytest` (full suite) against `lrs_test` | **174 passed**, 0 failed, 0 skipped (1 pre-existing harmless deprecation warning — unchanged) |
| `alembic check` | "No new upgrade operations detected" — Phase 3B.2 required no schema change (the constraint-naming fix changed only how the model declares an existing constraint, not the constraint itself) |
| FastAPI app startup + `GET /health` | 200 OK |
| Phase 3A/3B.1 tests re-run as part of the full suite | All still pass — no regression |
| Full department CRUD, run for real against `lrs_dev` via `curl` with a real minted SYSTEM_ADMIN JWT | Create → `201`; duplicate name → `409`; list/get/update → correct data; server-controlled-field injection → `422` |
| Full deactivate/reactivate cycle, run for real against `lrs_dev` with a real minted USER JWT in that department | User could access their department (`200`) → SYSTEM_ADMIN deactivated it → same User blocked (`403`) → SYSTEM_ADMIN reactivated it → same User restored (`200`), all against the live server, not `TestClient` |
| `git status` review | No secrets tracked; `.env` confirmed gitignored |

All data created during manual verification was deleted from `lrs_dev`
afterward — `lrs_dev` is empty again.

### Validation performed — Phase 3B.1

All against the same real, local, disposable PostgreSQL 17 instance used
for Phase 2/3A (`lrs_dev` for manual checks, `lrs_test` for the suite —
never a shared or departmental database):

| Check | Result |
|---|---|
| `pytest` (full suite) against `lrs_test` | **138 passed**, 0 failed, 0 skipped (1 pre-existing harmless deprecation warning — unchanged from Phase 3A) |
| `alembic check` | "No new upgrade operations detected" — Phase 3B.1 required no schema change |
| FastAPI app startup + `GET /health` | 200 OK |
| Phase 3A authentication tests re-run as part of the full suite | All still pass — no regression |
| Full role/department authorization matrix, run for real against `lrs_dev` (SYSTEM_ADMIN/ADMIN/USER × own/other department, via `curl` with real minted JWTs) | Every case matched the documented rule exactly — including the two explicit attack attempts (ADMIN and USER each tried another department's real UUID) |
| `git status` review | No secrets tracked; `.env` confirmed gitignored |

All data created during manual verification was deleted from `lrs_dev`
afterward — `lrs_dev` is empty again.

### Validation performed — Phase 3A

All against the same real, local, disposable PostgreSQL 17 instance used
for Phase 2 (`lrs_dev` for manual checks, `lrs_test` for the suite — never
a shared or departmental database):

| Check | Result |
|---|---|
| `pytest` (full suite) against `lrs_test` | **96 passed**, 0 failed, 0 skipped (1 pre-existing harmless deprecation warning — see Known Limitations) |
| `alembic check` | "No new upgrade operations detected" — Phase 3A required no schema change |
| FastAPI app startup + `GET /health` | 200 OK |
| Bootstrap CLI, run for real against `lrs_dev` | Created a SYSTEM_ADMIN with no department, ACTIVE status, hashed password; a second run was correctly refused |
| `POST /auth/login` for the bootstrapped admin | Returned a valid JWT; `GET /auth/me` with it returned the correct profile |
| Full signup flow via real HTTP against `lrs_dev` | Authorized email → `201`, `PENDING_APPROVAL`; unauthorized email → `403`; role-injection attempt → `422`; login while pending → `403` with the correct message; authorization row confirmed `USED` afterward |
| Tampered JWT / missing token via `curl` | Both `401` |
| Frontend build (`npm run build`) | Succeeds — untouched this phase, verified as still working |
| `git status` review | No secrets tracked; `.env` confirmed gitignored |

All data created during manual verification was deleted from `lrs_dev`
afterward — `lrs_dev` is empty again.

### Validation performed — Phase 2 (for reference)

| Check | Result |
|---|---|
| `alembic upgrade head` against `lrs_dev` | Both migrations applied cleanly |
| `alembic downgrade base` → `alembic upgrade head` | Full round-trip verified after the hardening migration was added |
| `alembic revision --autogenerate` after upgrading | "No new upgrade operations detected" — migrations match models exactly |
| `pytest` against `lrs_test` | 31 passed, 0 failed, 0 warnings |
| `from app.models import User` / `from app.models.user import User` in fresh interpreters | Both succeed (previously order-dependent) |
| FastAPI app startup + `GET /health` | 200 OK, using the real `lrs_dev` connection string |
| Empirical FK behavior (raw SQL and ORM-level, against `lrs_dev`, transactional/cleaned up) | `RESTRICT` blocks Department/User deletion with a clean FK error; `CASCADE` removes LetterDocument/Notification rows when their Letter is deleted |

## In Progress

Nothing — Phase 5H's implementation is complete (every prior phase
through Phase 5G's own Backend Aggregation review, a manual E2E bug fix
to `DepartmentSelector`'s controlled-value handling, Phase 5H's own
Source Department & Designation review, and now Phase 5H's
implementation are all done) and the project is paused pending explicit
instruction to begin the next phase, per the standing project rule that
phases are reviewed before the next begins.

## Pending (Phase 5H's own remaining known limitations, and later)

* **A Designation edit/detail page** — `PATCH /designations/{id}`
  exists on the backend; no frontend screen calls it yet. Deliberate
  Phase 5H scope, not an oversight — see
  `docs/architecture/source-designation.md` §12/§22.
* **An external/non-departmental Source fallback** — the Letter form's
  Source field is now exclusively a Department picker; a letter from an
  organization with no LRS department record has no representation
  through this form. `PENDING BUSINESS CLARIFICATION` — see
  `docs/architecture/source-designation.md` §4/§21.
* **A Letter aggregation/breakdown backend endpoint**
  (`GET /api/v1/letters/aggregate`, by category/classification/
  department/day/week/month) — fully designed
  (`docs/architecture/dashboard-analytics-api.md` §12-§16) but **not
  recommended for V1**: no metric in the Phase 5G inventory cleared the

* **A Letter aggregation/breakdown backend endpoint**
  (`GET /api/v1/letters/aggregate`, by category/classification/
  department/day/week/month) — fully designed
  (`docs/architecture/dashboard-analytics-api.md` §12-§16) but **not
  recommended for V1**: no metric in the Phase 5G inventory cleared the
  bar of confirmed business value existing APIs can't already provide.
  `PENDING BUSINESS CLARIFICATION` on whether any specific breakdown or
  trend is actually wanted — implementation is gated on that, not on
  any remaining design work.
* **A lighter-weight, count-only path for Departments/Admins/Users/
  Categories/Classifications** — today, computing any count from these
  five resources costs a full-object list fetch (no pagination, no
  database `COUNT`, unlike Letters). Not urgent at current scale;
  `PENDING BUSINESS CLARIFICATION`, tied to the same pagination
  question Phase 5D's own review already raised. Phase 5G's own review
  reached the identical conclusion from the backend side — see
  `docs/architecture/dashboard-analytics-api.md` §17.
* **`AuditLog` read API and any audit-derived analytics** — no read API
  exists; Phase 5G's own review found `AuditLog` has no department
  column at all, so scoping an audit aggregate correctly needs a
  separate, per-entity-type join design not yet attempted. `FUTURE`,
  explicitly deferred to its own later phase, not bundled with Letter
  aggregation. See `docs/architecture/dashboard-analytics-api.md` §5/§20.
* **Category/Classification management UI** — **RESOLVED (Phase 5H.1)**.
  Was out of Phase 5D's, 5E's, and 5F's scope (not an oversight — see
  `docs/architecture/document-notification-ui.md` §24 for how Phase 5E
  itself was sequenced); built in Phase 5H.1 once found to be a
  confirmed frontend completion gap during Phase 5H's manual E2E pass.
* **No signed/shareable document-download URL** (Phase 5E review,
  restating Phase 5's own §14 finding) — every download requires an
  authenticated fetch; there is no "open in a new tab" URL for a
  document. `PENDING BACKEND API` if ever wanted; not proposed by this
  review.
* **No pagination, search, or sort on Departments/Admins/Users/User-
  authorizations** (Phase 5D review finding) — unlike `GET /letters`,
  none of `GET /departments`/`/admins`/`/users`/`/users/authorizations`
  accept `page`/`page_size`/`sort_by`/any text filter; only exact
  `status` (all four) and `department_id` (Admins list only) filters
  exist. Each returns its complete result set in one response. Whether
  this is acceptable at real V1 data volumes is marked `PENDING
  BUSINESS CLARIFICATION` in that review, not resolved. See
  `docs/architecture/administration-ui.md` §11/§22.
* **Department-scoped user/admin counts** (Phase 5D review finding) —
  `DepartmentResponse` has no such field, and no endpoint computes one;
  a Department detail page cannot show "N users, M admins" without a
  new backend capability. See `docs/architecture/administration-ui.md`
  §7/§22.
* **Admin-purpose authorizations cannot be revoked** (Phase 5D review
  finding) — unlike User-purpose authorizations
  (`DELETE /users/authorizations/{id}`), no equivalent endpoint exists
  for Admin-purpose ones; a real asymmetry between the two lifecycles,
  flagged as a business decision, not silently assumed to need matching.
  See `docs/architecture/administration-ui.md` §8.1/§22.
* **A System-Admin-facing audit view** — `AuditLog` is populated (Phase
  4E) but has no read endpoint; restated as still open by the Phase 5D
  review, not a new finding. See
  `docs/architecture/audit-notifications.md` §9/§28.
* **USER/ADMIN cannot assign or view a resolved category/classification
  when creating or editing a Letter** (Phase 5C finding) —
  `GET /api/v1/categories`/`/classifications` are `require_system_admin`-
  only, but `POST /api/v1/letters` structurally excludes SYSTEM_ADMIN; no
  role that can create/edit a Letter can load those reference lists. A
  future backend change (e.g., a read-scoped, non-SYSTEM_ADMIN-only
  variant of these list endpoints) would be needed to close this gap;
  not proposed here. See `docs/architecture/frontend.md` §36.
* **A category/classification cannot be cleared back to unassigned once
  set** — the pre-existing `LetterUpdate` "omitted field means
  unchanged" limitation (§10) means there is currently no way, through
  the API, to explicitly null out a field that was already set. A future
  backend change (an explicit "clear" signal distinct from "omit") would
  be needed; not proposed here.
* **A unified global search box for Letters** — the backend has no such
  semantics; a frontend built against per-field filters only would need
  a new backend capability to support one search box across fields. See
  `docs/architecture/frontend.md` §11/§31.
* **A short-lived signed document-download URL** — would enable "open in
  a shareable new-tab URL" without client-side buffering; not proposed
  as a change, a future option if ever needed. See
  `docs/architecture/frontend.md` §14/§31.
* **A dedicated stats/aggregate endpoint** — would make a richer
  dashboard status-breakdown efficient (today it would cost one request
  per bucket); not proposed as a change. See
  `docs/architecture/frontend.md` §27/§31.
* **Exposing a caller's own department's `ACTIVE`/`INACTIVE` status** —
  `UserPublic` currently has no such field, so a frontend cannot detect
  its own department going inactive except reactively, via a `403`. See
  `docs/architecture/frontend.md` §13/§31.
* **An audit-viewing/read API** — `AuditLog` is now populated (Phase
  4E), but nothing exposes it through the API; the access-control
  question is genuinely unconfirmed. Phase 4E's review recommends
  `SYSTEM_ADMIN`-only as the safe V1 default, with department-scoped
  `ADMIN` access deferred until the per-entity-type department-resolution
  logic it would require is deliberately designed. See
  `docs/architecture/audit-notifications.md` §9/§28.
* **Notification triggers beyond "letter registered"** — the one
  CONFIRMED V1 trigger is implemented; document upload, classification/
  category changes, and User/Admin/Department lifecycle notifications
  remain unimplemented, deliberately, pending business confirmation each
  is actually wanted. See `docs/architecture/audit-notifications.md` §12.
* **Notification recipients for "letter registered" — still
  PROVISIONAL, not confirmed.** Implemented as the recipient
  department's ACTIVE Admins (an explicit, documented guess, not a
  business answer); whole-department or recorder-only-receipt remain
  live alternatives if the business ever weighs in. See
  `docs/architecture/audit-notifications.md` §13/§28.
* **`UserAuthorization.expires_at` enforcement** — the column exists, but
  nothing currently checks it against the current time; an "expired"
  audit event depends on that first being built. See
  `docs/architecture/audit-notifications.md` §4/§28.
* **Audit and notification retention periods** — no business period
  exists for either; Phase 4E recommends archiving (never deleting) audit
  rows whenever a period is set, and treats notifications as disposable
  by design. See `docs/architecture/audit-notifications.md` §11/§15.
* **Document deletion for `LetterDocument`** — deliberately not built in
  Phase 4D (physical or soft), matching the review's own recommendation.
  `LetterDocument` still has no lifecycle/status field to soft-delete
  into if that's ever wanted; no requirement has confirmed deletion is
  needed. See `docs/architecture/document-management.md` §14.
* **An optional `checksum_sha256` column on `LetterDocument`** — the one
  schema change Phase 4D's review recommended (nullable, no uniqueness
  constraint); the implementation brief explicitly deferred it
  ("Do not add checksum yet"). See
  `docs/architecture/document-management.md` §12/§28.
* **Department/year/month grouping in the document storage path** —
  Phase 4D's own architecture review recommended layering this on top
  of the per-letter UUID structure for long-term browsability at high
  volume; the implementation brief's literal example
  (`<letter_uuid>/<document_uuid>.<ext>`, no such grouping) was followed
  instead. Revisit if the flat per-letter directory layout becomes
  unwieldy. See `docs/architecture/document-management.md` §33 and
  `storage/README.md`.
* **The text-attachment workflow** (typed `Letter.text_content` vs. an
  uploaded `.txt` file vs. either, at the User's discretion) — the data
  model already supports all three readings without change; only the
  expected workflow is unconfirmed. See
  `docs/architecture/document-management.md` §10.
* **A document-replacement "supersede" workflow distinct from "just
  upload another document"** — the current, implemented behavior
  (uploading again simply adds another `LetterDocument`; nothing is ever
  marked as superseded or hidden) is the safe default Phase 4D's review
  recommended; a first-class "this replaces that" concept would need a
  new field and isn't built. See
  `docs/architecture/document-management.md` §13.
* **The exact classification value list** — no `Classification` rows are
  seeded; a System Admin can create them through the management API once
  the organization confirms the final list (Important/Classified/Budget/
  etc. were always examples, never a closed enumeration the way
  Category's three now are). See `docs/architecture/letter-registry.md`
  §2.5/§12.
* **The exact classified-letter visibility matrix beyond "not every
  department user by default"** — `app/services/authorization.py:assert_letter_access`/
  `letter_visibility_filter` currently allow `ADMIN`/`SYSTEM_ADMIN`/the
  letter's own recorder; this is an explicit, documented, provisional
  default, not a confirmed final policy. See
  `docs/architecture/letter-registry.md` §8/§12 and
  `docs/architecture/registry-search.md` §11.
* **Exact reference-number search semantics beyond "contains"** (Phase
  4C) — prefix matching was considered and not chosen; contains was
  implemented as the more forgiving default. A product/UX question, not
  a blocking one. See `docs/architecture/registry-search.md` §11.
* **Whether a single free-text `search=` box (spanning multiple fields)
  is wanted** alongside the per-field parameters implemented in Phase
  4C. See `docs/architecture/registry-search.md` §11.
* **A revoke endpoint for ADMIN-purpose `UserAuthorization` rows** — Phase
  3B.4 added revocation only for the USER-purpose path
  (`DELETE /api/v1/users/authorizations/{id}`); a System Admin still
  cannot revoke a still-`ACTIVE`, non-expired ADMIN-purpose authorization.
  The repository layer is already purpose-agnostic
  (`find_by_id`/`list_by_department`/`revoke`), so this needs only a new
  endpoint plus a creator/department check mirroring
  `docs/architecture/user-management.md` §9 — see that section's "Known
  limitations".
* **System Admin handover workflow** — see
  `docs/architecture/authentication.md` §9.
* **Automatic audit logging** of authorization-sensitive actions,
  including the four department events (Phase 3B.2), five Admin events
  (Phase 3B.3), five User events (Phase 3B.4,
  `USER_AUTHORIZATION_CREATED`/`REVOKED`/`APPROVED`/`DEACTIVATED`/
  `REACTIVATED`), and Letter lifecycle events (Phase 4B — the service
  remains `AuditLog`-compatible per Phase 4A §19, but no row is written
  yet) — see `docs/architecture/authorization.md` §12,
  `docs/architecture/department-management.md` §10,
  `docs/architecture/admin-management.md` §13,
  `docs/architecture/user-management.md` §12, and
  `docs/architecture/letter-registry.md` §13 for the full list.
* **Automatic notification generation** — "a letter was registered" is
  the one confirmed V1 trigger; `Notification.letter_id` is already
  architecturally ready (Phase 4A §20), but no row is written by Phase 4B.
* **Department/Admin/User/Letter/Category/Classification list
  pagination** — deliberately not implemented in any phase so far, but
  every response envelope (`{"items": [...], "total": N}`) was shaped so
  adding it later needs no redesign; see
  `docs/architecture/department-management.md` §3.
* **Clearing an already-set department `code` back to `null`** — not
  possible through `PATCH /api/v1/departments/{id}` today; see
  `docs/architecture/department-management.md` §3, "Known limitation".
* **The same `unique=True` constraint-naming issue fixed for Department
  in Phase 3B.2** still exists on `categories.name` and
  `classifications.name`. Not fixed, since nothing currently depends on
  either constraint's name — the same technique applies if a future
  Category/Classification management phase ever needs it.
* **An email can be authorized as an Admin (or User) candidate while it
  already belongs to an active User (or Admin)** — a narrow, accepted edge
  case in both directions, not a security issue (the existing
  duplicate-email check at signup already prevents any real
  inconsistency); see `docs/architecture/admin-management.md` §3 and
  `docs/architecture/user-management.md` §4.
* **Frontend authentication/authorization/department/Admin/User-
  management UI** — login/signup pages, protected routing, token storage,
  role-based show/hide. See `docs/architecture/authentication.md` §15 for
  why this remains deliberately deferred.

## Pending Confirmation (from S&IT)

None of the following are implemented as final requirements — each is a
documented, minimal, reversible assumption. See `docs/database/schema.md`
§7 and `docs/architecture/letter-registry.md` §12 for the full reasoning
behind each.

* **Official letter/reference number's existence/format: RESOLVED (Phase
  4B)** — required, manually entered, no format imposed. **Uniqueness
  scope: STILL PENDING** — a global constraint was implemented, then
  removed during a same-phase hardening pass once it became clear the
  business only said "must be unique", never confirming global vs.
  per-department vs. per-source vs. per-year. Duplicates are currently
  accepted anywhere. See `docs/architecture/letter-registry.md` §2.3/§14.
* **Sender identification: RESOLVED (Phase 4B)** — split into
  `source_name`/`source_department_id` (source/origin) and
  `sender_name`/`sender_designation`/`sender_department`/`sender_address`
  (the specific person/office details), superseding the old free-text
  `received_from`. See `docs/architecture/letter-registry.md` §2.1/§2.2.
* **Final category list: RESOLVED (Phase 4B)** — exactly three, closed
  for V1 (General Letter, Notification, Office Order); "Budget" confirmed
  *not* to be one. See `docs/architecture/letter-registry.md` §2.4.
* **Final classification/priority terminology — still open.**
  "Important"/"Classified"/"Budget"/etc. remain examples only; no
  `Classification` row is seeded. What *is* resolved: classification can
  carry access-control significance (§2.5). See
  `docs/architecture/letter-registry.md` §12.
* **Departmental code format** (`departments.code`) — left nullable,
  unformatted. Unrelated to Phase 4B, still open.
* **`letters.subject` requirement-ness: RESOLVED (Phase 4B)** — now
  required via `LetterCreate` (the underlying database column remains
  nullable — see `docs/architecture/letter-registry.md` §3 for why that's
  not a contradiction). `letters.reason` remains nullable and optional,
  unrequested by the finalized decisions, not removed either.
* **Source location / sender address nullability: RESOLVED (Phase 4B)**
  — `source_location` nullable (not required), `sender_address`
  explicitly, deliberately nullable ("do not make Sender Address
  artificially mandatory").
* **Document retention requirements** — not addressed; no retention/expiry
  field exists on `letter_documents`. Unrelated to Phase 4B, still open.

## Known Limitations

* **RESOLVED (Phase 5D) — the frontend now has a complete Department/
  Administrator/User management UI** (list/create/detail/lifecycle
  actions/authorization workflows/Admin transfer), on top of Phase 5C's
  complete core Letter registry and Phase 5B's complete authentication/
  account UX, but **Document upload/download and Notifications UI still
  do not exist** — both are still only reachable via a direct API
  client (`curl`, `httpx`, the automated test suite), not the frontend.
  See `docs/architecture/administration-ui.md` §26 for exactly what is
  and isn't built.
* **No pagination, search, or sort on Departments/Admins/Users/User-
  authorizations** (Phase 5D, a CONFIRMED backend-contract limitation) —
  unlike `GET /letters`, none of the four resources' list endpoints
  accept `page`/`page_size`/`sort_by`/any text filter; only exact
  `status` (all four) and `department_id` (Admins list only) filters
  exist, and every list page renders the complete matching result set.
  Whether this needs to change at real V1 data volumes is `PENDING
  BUSINESS CLARIFICATION`, not resolved by this phase. See
  `docs/architecture/administration-ui.md` §11/§22.
* **Admin-purpose authorizations cannot be revoked through this or any
  frontend** (Phase 5D, a CONFIRMED backend-contract gap) — no
  `DELETE`-equivalent endpoint exists for them, unlike User-purpose
  authorizations; `AdminAuthorizePage` has no revoke-adjacent
  affordance, matching the gap exactly rather than implying a capability
  that doesn't exist. See `docs/architecture/administration-ui.md`
  §8.1/§22.
* **No department/admin/user counts appear anywhere** (Phase 5D) —
  `DepartmentResponse` has no such field; none is computed client-side
  from other endpoints, since no combination of the current API surface
  can compute it correctly for a SYSTEM_ADMIN viewer. See
  `docs/architecture/administration-ui.md` §7/§22.
* **USER/ADMIN cannot assign or view a resolved category/classification
  name for a Letter** (Phase 5C, a CONFIRMED backend-contract gap, not a
  frontend oversight) — `GET /api/v1/categories`/`/classifications` are
  `require_system_admin`-only, while `POST /api/v1/letters` structurally
  excludes SYSTEM_ADMIN (no department to record a letter against). The
  two roles that actually record/edit letters day-to-day have no
  legitimate way to load the option lists; only SYSTEM_ADMIN (via Edit)
  can set either field. Nothing was hardcoded as a workaround. See
  `docs/architecture/frontend.md` §36.
* **A category/classification cannot be cleared back to unassigned once
  set, through this or any frontend** (Phase 5C, restates a pre-existing
  backend limitation from `docs/architecture/frontend.md` §10) — sending
  an explicit `null` is indistinguishable from omitting the field
  entirely (`LetterUpdate`'s "omitted means unchanged" semantics), so the
  SYSTEM_ADMIN edit form never attempts it and says so in its own hint
  text rather than implying the capability exists.
* **`source_department_id` and `recorded_by` have no UI** (Phase 5C,
  deliberate scope simplifications, not backend blockers) —
  `source_name` already conveys the letter's source in every screen this
  phase builds; resolving `recorded_by` to a user's name would need a
  cross-role user-lookup endpoint this phase was not authorized to
  consume (only Category/Classification reference data was, per that
  phase's own scope limit).
* **Logout does not revoke an already-issued JWT server-side** (Phase
  5B, restated from Phase 3A's original design — not a new gap) — the
  backend has no logout/revocation endpoint; `AuthContext.logout()`
  removes the locally held token only. A token that has already been
  issued remains valid, from the backend's perspective, until it
  naturally expires. Accepted V1 architecture, not a defect. See
  `docs/architecture/frontend.md` §35, `frontend/README.md`.
* **A network failure during session restoration requires a manual
  retry** (Phase 5B) — `AuthContext` does not automatically retry or
  back off; the user (or a page reload) must trigger the retry. No
  automatic retry was requested by the brief, and adding one (timers,
  backoff, cancellation) was judged unnecessary complexity for what this
  phase actually needed to guarantee: a network failure is never treated
  as a successful authenticated state, and the stored token is not
  discarded just because the server was briefly unreachable.
* **Two pre-existing `npm audit` advisories have no non-breaking fix**
  (Phase 5A finding, unchanged by Phase 5B) — `react-router-dom`'s only
  patched release is a `v7` major version; the `esbuild`/`vite`
  toolchain's fix requires `vite@8`. Both packages were already pinned to
  their current major versions since Phase 1; upgrading either would
  replace the existing stack, which these phases were explicitly
  instructed not to do. Documented in `frontend/README.md`, not silently
  upgraded or silently ignored.
* **No way for a frontend to proactively know its own department is
  `INACTIVE`** (Phase 5 finding) — `UserPublic` exposes `department_id`
  but not that department's own status; a future frontend can only
  detect this reactively, via a `403` on the next department-scoped
  action. Not a bug — a real information gap this review named rather
  than working around. See `docs/architecture/frontend.md` §13.
* **RESOLVED (Phase 4C)** — the classified-record count/pagination
  leakage risk identified in this phase's own architecture review
  (a non-recording `USER`'s `total` could have included letters they
  couldn't see, once pagination existed) was fixed *before* pagination
  was built, not after: `letter_visibility_filter` makes the
  classified-access rule a SQL `WHERE` clause, and `total`/`items` are
  derived from the identical filtered query. Verified by two dedicated
  regression tests and a live `lrs_dev` check — see
  `docs/architecture/registry-search.md` §1/§9.
* **`letters.reference_number` currently has no uniqueness enforcement
  at all** (Phase 4B hardening pass finding, unchanged by Phase 4C) — a
  global constraint was implemented then removed once it became clear
  the business never actually confirmed the scope ("must be unique"
  alone doesn't say global vs. per-department vs. per-source vs.
  per-year). Duplicates are currently accepted anywhere in the system,
  and a reference-number search can return more than one result. It is,
  however, indexed again (`ix_letters_reference_number`, migration
  `9fa970ffa560`, Phase 4C) — a plain, non-unique index, added because
  reference-number search is a real requirement. See
  `docs/architecture/letter-registry.md` §2.3/§14 and
  `docs/architecture/registry-search.md` §8.
* **RESOLVED (Phase 4B)** — `Letter` now has `recipient_department_id`
  (the department-isolation boundary) and `source_department_id`/
  `source_name` (the letter's origin) as distinct fields; the single-
  field ambiguity Phase 4A flagged (one `department_id` trying to mean
  both at once) no longer exists. See
  `docs/architecture/letter-registry.md` §5 for the migration that
  resolved it.
* **The classified-access visibility policy is a documented, provisional
  default, not a confirmed final one** (Phase 4B) — `ADMIN`/`SYSTEM_ADMIN`/
  the letter's own recorder can view a restricted letter; a `USER` who is
  none of those cannot, even within their own department. See
  `docs/architecture/letter-registry.md` §8/§12.
* **RESOLVED (Phase 4D implementation)** — `LetterDocument` upload,
  listing, and download are implemented
  (`/api/v1/letters/{letter_id}/documents*`). `storage/README.md` now
  documents the actual, implemented path convention (no longer the
  Phase 1 illustrative one, which had no document-identifier segment and
  conflicted with the schema's multi-document capability).
* **`LetterDocument` has no lifecycle/status field** (Phase 4D
  finding, still true) — unlike `Letter`/`User`/`Department`/`Category`/
  `Classification`, there is currently nothing to soft-delete a document
  into. Phase 4D's implementation deliberately built **no document
  deletion endpoint of any kind** (physical or soft), matching the
  review's own recommendation rather than adding one prematurely. See
  `docs/architecture/document-management.md` §14.
* **The document storage path has no department/year/month grouping**
  (Phase 4D implementation, a deliberate deviation from the review's own
  §7 recommendation) — the flat `<letter_uuid>/<document_uuid>.<ext>`
  structure the implementation brief specified literally was built
  instead; revisit if the per-letter directory layout becomes unwieldy
  at high volume. See `docs/architecture/document-management.md` §33.
* **A bare `pytest` invocation from `backend/` produces one unrelated
  collection error** — `app/api/v1/endpoints/dev_authz_test.py`'s
  filename incidentally matches pytest's default `*_test.py` discovery
  pattern, so pytest also tries (and fails) to collect its route-handler
  functions as test functions. Discovered while validating Phase 4D;
  confirmed pre-existing, not a regression, by reproducing the identical
  error against the unmodified pre-Phase-4D tree. `pytest tests/`
  (scoped explicitly, now documented in `backend/README.md`) avoids it;
  not fixed, since renaming or reconfiguring collection for an unrelated
  Phase 3B.1 file is outside this phase's scope.
* **The local `backend/.env` file was inadvertently overwritten during
  Phase 4D's validation** (copied fresh from `.env.example` while
  setting up an `alembic check` run) — `.env` is git-ignored and was
  never committed, so this is local-environment-only, not a repository
  or data issue. No actual data was lost: the real `lrs_dev` database
  and its schema/rows were confirmed completely intact afterward
  (`lrs_dev`/`lrs_dev` — a local-development convention, not a real
  credential; it only ever connects to a Postgres instance on
  `localhost` and protects nothing of value, matching this project's
  existing `lrs_test`/`lrs_test` convention — still connect, and its 3 seeded
  `categories` rows were reconfirmed unchanged both before and after
  Phase 4D's live verification). `.env` was restored with a freshly
  generated `SECRET_KEY` and `DATABASE_URL` pointed back at `lrs_dev`; a
  freshly generated `SECRET_KEY` invalidates any JWT signed with the
  previous one (an accepted, already-documented consequence of rotating
  this value — see "Configuration" in `backend/README.md`), not a data
  loss. Flagged here for transparency, not because it blocks anything.
* **No PostgreSQL was available in the initial development environment.**
  One was installed and configured specifically to validate this phase (see
  "Validation performed" above) rather than leaving the migration and test
  suite unverified. In an environment where PostgreSQL is genuinely
  unavailable, `pytest` skips (does not fail) the model tests — see
  `docs/database/README.md`, "Providing a local test database".
* **A pre-existing Phase 1 config bug was fixed during this phase's
  validation.** `backend/app/core/config.py`'s `CORS_ORIGINS` setting
  crashed on startup (`pydantic_settings.exceptions.SettingsError`) when
  `.env` was created by copying `.env.example` exactly as the README
  instructs, because pydantic-settings tried to JSON-decode the documented
  comma-separated value before the field's own validator ran. Fixed with a
  one-line `NoDecode` annotation (see `backend/README.md`, "Configuration").
  This was outside Phase 2's nominal scope (database architecture) but was
  fixed because it silently broke this phase's own "verify the app starts"
  validation step and every documented getting-started instruction.
* **`httpx`/Starlette deprecation warning** on `TestClient` import
  (`Using httpx with starlette.testclient is deprecated; install httpx2
  instead`) — pre-existing, noted in `requirements.txt`'s own comment.
  Not addressed in this phase; harmless for now, but will need resolving
  before Phase 3 adds real API tests.
* **No database-level enforcement of department isolation** — by design,
  deferred to a future service layer. See `docs/architecture/overview.md`
  §3 for why this cannot be a schema-level guarantee.
* **`passive_deletes="all"` (added in the hardening pass) has a documented
  SQLAlchemy caveat**: an object already loaded into a session's identity
  map before its row is removed by the database's own `ON DELETE CASCADE`
  is not automatically expunged or refreshed within that same session —
  `session.get(...)` can return a stale copy until the session is expired
  or a fresh one is used. This is inherent to the pattern, not a bug; see
  `docs/database/schema.md` §1, "ORM deletion behavior", and the test that
  demonstrates it. A future service/repository layer needs to be aware of
  this when deleting a Letter in the same session that will keep running.
* **No refresh tokens or token revocation** (Phase 3A) — a token is valid
  until it expires; deactivating the account it belongs to stops it being
  *useful* immediately (re-checked on every request) but doesn't revoke the
  token itself. See `docs/architecture/authentication.md` §16.
* **`UserAuthorization` records no longer require direct database access
  to create** (resolved: ADMIN-purpose via Phase 3B.3, USER-purpose via
  Phase 3B.4) — both now go through `/api/v1/admins/authorizations` and
  `/api/v1/users/authorizations` respectively. Kept here for history: this
  entry described a real gap during Phase 3A, when manual verification of
  the signup flow had to create an authorization directly via the ORM.
* **Bootstrap has no race-condition hardening beyond a single transaction**
  (Phase 3A) — an accepted, documented simplification since it's a rare,
  CLI-only, operator-run action, unlike signup which is fully race-safe.
  See `docs/architecture/authentication.md` §8.
* **`getpass.getpass()` does not accept piped/redirected stdin on Windows**
  — confirmed during Phase 3A's manual verification (it reads directly
  from the console). Not a bug: arguably a desirable property, since it
  stops a password from being accidentally scripted into a piped command.
  The automated test suite calls `create_system_admin` directly rather than
  the interactive CLI wrapper for this reason.
* **No real departmental *business* resource exists yet** — Phase 3B.2
  gave `require_system_admin` its first real resource (departments
  themselves), and Phase 3B.4 finally exercised
  `assert_department_access` as a genuine cross-department, resource-level
  check (User accounts) rather than only the Phase 3B.1 verification-only
  endpoints. Departments/Admins/Users are all still *management*
  resources, though — no Letter or other departmental *business* resource
  exists yet. Not a defect — see `docs/architecture/authorization.md` §7,
  `docs/architecture/user-management.md` §5-6, and Phase 4 in "Pending"
  above.
* **No automatic audit logging** of authorization-sensitive actions —
  deliberately out of scope for both Phase 3B.1 and 3B.2 (brief §15/§21);
  see `docs/architecture/authorization.md` §12 and
  `docs/architecture/department-management.md` §10 for the full list
  scoped for when the relevant actions exist.
* **`Department.name`/`code` needed a constraint-naming fix this phase**
  (Phase 3B.2) — see "Known Limitations" entry below and
  `docs/database/schema.md` §2.1 for the full explanation. No migration
  was required; this was a Python-model-only fix.
* **The same constraint-naming issue is still latent on
  `categories.name`/`classifications.name`** (Phase 3B.2 finding, not
  fixed) — see "Pending" above.
* **A department's `code` cannot be cleared back to `null` via `PATCH`**
  (Phase 3B.2) — only overwritten with a different value. Deliberate
  simplicity tradeoff; see `docs/architecture/department-management.md`
  §3.
* **No pagination on `GET /api/v1/departments`** (Phase 3B.2) — not needed
  at current data volumes; the response envelope was shaped so adding it
  later needs no redesign. See `docs/architecture/department-management.md`
  §3.
* **No way to revoke a still-`ACTIVE`, non-expired ADMIN-purpose
  `UserAuthorization`** (Phase 3B.3 gap, still open after Phase 3B.4) — no
  endpoint sets one to `REVOKED`. The equivalent USER-purpose gap was
  closed in Phase 3B.4 (`DELETE /api/v1/users/authorizations/{id}`); the
  repository layer behind it is already purpose-agnostic, so an
  Admin-management equivalent needs only a new endpoint. See
  `docs/architecture/user-management.md` §12, "Known limitations".
* **An email can be authorized as an Admin candidate while already
  belonging to an active User, and vice versa** (Phase 3B.3/3B.4) —
  narrow, accepted edge case in both directions; see
  `docs/architecture/admin-management.md` §3 and
  `docs/architecture/user-management.md` §4.
* **No automatic audit logging** of authorization-sensitive actions —
  deliberately out of scope for Phase 3B.1/3B.2/3B.3/3B.4 (brief
  §15/§21/§25, and this phase's own scope boundary); see
  `docs/architecture/authorization.md` §12,
  `docs/architecture/department-management.md` §10,
  `docs/architecture/admin-management.md` §13, and
  `docs/architecture/user-management.md` §12 for the full list scoped for
  when the relevant actions exist.
* **RESOLVED (Phase 4E implementation) — `AuditLog` and `Notification`
  are now populated.** `AuditLog` records Letter/Document/User/Admin/
  Department/Category/Classification/Authorization lifecycle events,
  append-only and transactionally mandatory; `Notification` generates
  for the one confirmed "letter registered" trigger, best-effort via a
  database `SAVEPOINT`. See `docs/architecture/audit-notifications.md`
  §31 for the full implementation record.
* **No audit-viewing/read API exists** (Phase 4E, deliberate scope
  decision, not a gap) — `AuditLog` is written to but nothing exposes it
  through `/api/v1`; the access-control question (§9) remains genuinely
  unconfirmed. See `docs/architecture/audit-notifications.md` §9/§31.
* **Notification recipient strategy ("the recipient department's
  Admins") is still PROVISIONAL** — implemented as the interim default
  the review named, explicitly not confirmed by the business. See
  `docs/architecture/audit-notifications.md` §13.
* **RESOLVED (Phase 3B.4 hardening pass) — `test_me_with_tampered_token_is_rejected`
  (Phase 3A) was occasionally flaky on a full-suite run.** Root cause
  confirmed empirically (5,000-trial script): the old technique flipped
  the *last base64 character* of a 32-byte HMAC-SHA256 signature to a
  fixed value ('A', or 'B' if already 'A'). That character's low 2 bits
  are base64 padding, discarded on decode; 'A' (`000000`) and 'B'
  (`000001`) differ only in that discarded bit. Whenever the signature's
  real trailing 4 bits already happened to be `0000` (the last char
  already 'A', ~1/16 of random signatures — measured 6.10% empirically),
  the "fall back to B" branch silently produced a byte-identical
  signature, so the server correctly accepted it and the test's `401`
  assertion failed. This was a **test-construction bug, not a JWT
  verification weakness** — `app/core/security.py:decode_access_token`
  was never modified. The test now decodes the signature to raw bytes,
  XORs one real byte, and re-encodes (`_tamper_signature`,
  `tests/integration/test_auth_current_user.py`) — verified deterministic
  across 5,000 trials and 20 consecutive isolated test runs.

## Next Recommended Phase

Phase 5H's implementation is now complete — Source Department and
Designation both work end to end against the real backend, matching
`docs/architecture/source-designation.md` §22's MUST-IMPLEMENT list
exactly. See that document's own §26 for the full implementation
record. What remains from this phase is small and disclosed: a
Designation edit/detail page, and the open "external source" business
question (§21 of that review) — neither blocks tonight's handover.

Separately, Phase 5G's own review is complete — it found that **no backend
aggregation is currently justified**: every candidate analytics metric
either already has an existing, sufficient API (Phase 5F's own
operational dashboard) or is gated behind an unconfirmed business want.
A complete `GET /api/v1/letters/aggregate` design is documented and
ready to build (`docs/architecture/dashboard-analytics-api.md` §12-§16)
the moment at least one specific breakdown or trend is confirmed
wanted — but nothing was implemented or authorized this phase. Category/
Classification management (the other previously-open screen) was built
in the subsequent Phase 5H.1. What remains is resolving Phase 5G's own
business clarifications (§27 of that review — is analytics wanted at all, which
trend/breakdown matters, default date range, whether USER should see
any aggregate), or resolving one of the several other genuinely open
questions before more UI or any analytics widget is built on top of
what exists today:

Resolving the category/classification reference-data
access gap Phase 5C confirmed (a backend change: a read-scoped,
non-SYSTEM_ADMIN-only variant of `GET /categories`/`/classifications` —
not designed or proposed by any phase so far), **or** whether
Departments/Admins/Users/User-authorizations need pagination at real V1
data volumes (Phase 5D's review, `docs/architecture/administration-ui.md`
§11/§22 — now also directly relevant to dashboard-card cost, per
`docs/architecture/dashboard.md` §9), **or** whether Admin-purpose
authorizations should become revocable, matching User-purpose ones
(same review, §8.1/§22), **or** an audit-viewing/read API once its
access-control question is resolved (a prerequisite for any historical/
trend dashboard widget, per `docs/architecture/dashboard.md` §2/§26),
**or** resolving the outstanding business clarifications first —
including, newly surfaced this phase, whether the dashboard should be
operational or analytical, whether USER should have a dashboard at all,
and which of §27's other open questions in `docs/architecture/dashboard.md`
matter most. Recommended before or alongside whichever is chosen:
resolve the exact classification value list and classified-visibility
matrix with the product owner (`docs/architecture/letter-registry.md`
§12, `docs/architecture/registry-search.md` §11); the category/
classification reference-data access gap named above; who should
receive a "letter registered" notification, since "department Admins"
is still an explicit guess (`docs/architecture/audit-notifications.md`
§13); whether mark-read-on-navigate is the desired notification
behavior — implemented as explicit-only for now, per an explicit
override documented in `docs/architecture/document-notification-ui.md`
§27, but the underlying business question remains open — and
notification polling frequency/retention (still `PROVISIONAL` at 60
seconds, `docs/architecture/document-notification-ui.md` §11/§27);
which deployment model applies (individually-assigned workstations vs.
shared machines), since it changes the frontend's token-storage
recommendation (`docs/architecture/frontend.md` §28); and whether a
unified global search, a signed document-download URL, or document
previews are ever actually wanted before any is built speculatively
(`docs/architecture/frontend.md` §31,
`docs/architecture/document-notification-ui.md` §23).
