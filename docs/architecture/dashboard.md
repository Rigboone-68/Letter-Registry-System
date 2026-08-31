# Dashboard & Operational Overview UI — Architecture & Requirements Review (Phase 5F)

**Status: REVIEW ONLY. No frontend or backend code, migration, or test
was written this phase.** Builds on Phase 5A (foundation), Phase 5B
(authentication/account UX), Phase 5C (core Letter registry UI), Phase
5D (administration/account-management UI), and Phase 5E (documents/
notifications UI) — all implemented, committed, and unchanged by this
review. Repository confirmed clean and at `edc6649` (Phase 5E) before
this review began.

## 0. How to read this document

Same taxonomy this project has used since Phase 4A:

* **CONFIRMED** — verified directly against current backend/frontend
  source code this session.
* **RECOMMENDED** — this document's own proposal, grounded in confirmed
  facts and the conventions Phase 5A-5E already established. Not
  implemented.
* **PROVISIONAL** — an explicit judgment call this document had to make
  one way or another, flagged so it is revisited deliberately.
* **PENDING BUSINESS CLARIFICATION** — genuinely open, not guessed.
* **PENDING BACKEND API** — the frontend capability described would
  require a backend endpoint/field that does not currently exist.
  Never worked around; always named explicitly.

Per the brief's own §5 taxonomy, every candidate dashboard metric is
also tagged with one of:

* **A — DIRECTLY AVAILABLE** — one existing endpoint call, cleanly.
* **B — DERIVABLE FROM EXISTING API** — possible today, but costs
  multiple requests or client-side aggregation.
* **C — REQUIRES BACKEND API** — cannot be obtained efficiently or
  correctly today.
* **D — REQUIRES BUSINESS CLARIFICATION** — the metric's own definition
  isn't confirmed yet.
* **E — NOT RECOMMENDED** — technically possible, architecturally wrong
  for V1.

## 0.1 Relationship to existing documents

This is not the first time a dashboard has been discussed. Two prior
documents already reached conclusions this review verifies and builds
on rather than re-deriving from nothing:

* `docs/architecture/audit-notifications.md` §23 (Phase 4E) —
  **RECOMMENDED**, not implemented: a future dashboard's *current-state*
  metrics should read from the operational tables via ordinary aggregate
  queries (a new backend capability, not something the frontend already
  has); *historical/change* metrics are what `AuditLog` exists to
  answer, once a read API is built; `Notification` is explicitly **not**
  a good dashboard data source (recipient-scoped, deliberately
  disposable); a dedicated reporting/warehouse table is **not
  recommended** until real dashboard query patterns are known.
* `docs/architecture/frontend.md` §27 — a "dedicated stats/aggregate
  endpoint" was already named as PENDING/FUTURE, not designed.

This review confirms both conclusions still hold against current
source, and does the concrete work neither prior document went into:
a full metric-by-metric inventory, exact role/department/classification
handling, and a proposed (not built) endpoint shape.

---

## 1. Current frontend dashboard state (CONFIRMED)

**No dashboard exists in any form.** Verified directly:

* `frontend/src/routes/index.jsx` — the `/app` index route is
  `<Navigate to="letters" replace />`; there is no `/app/dashboard`
  route, reserved or otherwise, anywhere in the route tree.
* `frontend/src/navigation/navigationConfig.js` — no "Dashboard" entry
  for any of the three roles (`SYSTEM_ADMIN`/`ADMIN`/`USER`).
* `frontend/src/pages/RootRedirect.jsx` — sends an authenticated caller
  straight to `/app` (→ `letters`), never a dashboard concept.
* No dashboard-named component, page, service, or test file exists
  anywhere under `frontend/src/`.
* `frontend/package.json` — dependencies are exactly `axios`,
  `react`, `react-dom`, `react-router-dom`; devDependencies are the
  Vite/Vitest/Testing-Library toolchain. **No charting library of any
  kind is installed** (no Chart.js, Recharts, D3, Victory, etc.).

This phase is a genuine blank slate — nothing to preserve, nothing to
migrate, no placeholder to replace.

## 2. Current backend data availability (CONFIRMED, re-read fresh)

Every business endpoint was re-read this session, not recalled from a
prior phase's report. Twelve resource routers are mounted
(`backend/app/api/v1/router.py`): `auth`, `departments`, `admins`,
`users`, `categories`, `classifications`, `letters`, `documents`
(nested under Letters), `notifications`, plus a dev-only verification
router (`dev_authz_test`) irrelevant to any real screen.

**No dashboard, summary, aggregate, stats, or reporting endpoint exists
anywhere.** No endpoint returns a count without also returning the
matching rows.

| Resource | List endpoint | Pagination | `total` computed how | Role |
|---|---|---|---|---|
| Letters | `GET /letters` | Real (`page`/`page_size`, max 100) | **SQL `COUNT`**, from the *same* filtered/visibility-scoped statement as the page itself (`app/repositories/letter_repository.py:list_letters`) | any authenticated user; department/classified-scoped |
| Departments | `GET /departments` | **None** — always returns every matching row | `len(list)` in Python, after the full result is materialized | SYSTEM_ADMIN only |
| Admins | `GET /admins` | **None** | `len(list)` | SYSTEM_ADMIN only |
| Users | `GET /users` | **None** | `len(list)` | ADMIN only, own department |
| User authorizations | `GET /users/authorizations` | **None** | `len(list)` | ADMIN only, own department |
| Categories | `GET /categories` | **None** | `len(list)` | SYSTEM_ADMIN only |
| Classifications | `GET /classifications` | **None** | `len(list)` | SYSTEM_ADMIN only |
| Documents | `GET /letters/{id}/documents` | **None** — per-Letter only, no cross-Letter list | `len(list)` | any user with access to the parent Letter |
| Notifications | `GET /notifications` | Real (`page`/`page_size`, max 100) | Real `COUNT`, recipient-scoped | own account only |
| Notifications (unread) | `GET /notifications/unread-count` | n/a | Real `COUNT` | own account only |

**This asymmetry matters directly for dashboard design** (§10, §11):
a Letters count is cheap and DB-accurate at any page size because it's
a real `COUNT` query; a Departments/Admins/Users/Categories/
Classifications "count" requires the backend to materialize and return
every matching row's full object today — there is no lighter-weight
path for those five resources, confirmed by reading the endpoint code
directly, not assumed from a schema alone.

**No audit read API exists.** `app/models/audit_log.py`,
`app/repositories/audit_log_repository.py`, and
`app/services/audit_service.py` all exist and are actively written to
(Phase 4E) — but grepping every endpoint file and `router.py` confirms
**zero** HTTP route exposes `AuditLog` in any form. Any dashboard metric
that would need audit data is `PENDING BACKEND API`, full stop — this
was already the conclusion of `audit-notifications.md` §9/§23, and nothing
has changed since.

### 2.1 The classified-access rule, precisely (CONFIRMED — directly relevant to every count below)

`app/services/authorization.py:letter_visibility_filter` — returns
`None` (no extra restriction) for `SYSTEM_ADMIN` and `ADMIN`; returns a
real SQL predicate for `USER` only, true when a letter's classification
doesn't restrict access, has no classification, or the USER themself
recorded it. This predicate is applied at the query level, joined into
both the `COUNT` and the paginated `SELECT` in the same statement — so
**`GET /letters`'s `total` already excludes every classified-and-
inaccessible record for a USER caller, at any filter combination,
without the frontend doing anything.** ADMIN and SYSTEM_ADMIN have no
classified-record narrowing at all within their own scope (department
for ADMIN, unrestricted for SYSTEM_ADMIN) — confirmed directly from the
predicate's own `None` return for those two roles.

---

## 3. Dashboard metric inventory

Every candidate the brief listed, verified against source, not
assumed. "Existing request" means the exact call that would produce it
today with zero backend change.

| Metric | Class | Existing request (if any) | Notes |
|---|---|---|---|
| Total letters (role-scoped) | **A** | `GET /letters?page_size=1` → `.total` | One request, real `COUNT`, already department/classified-scoped |
| Active letters | **A** | `GET /letters?status=ACTIVE&page_size=1` → `.total` | Same mechanism |
| Archived letters | **A** | `GET /letters?status=ARCHIVED&page_size=1` → `.total` | Same mechanism |
| Letters by category | **B** | One `GET /letters?category_id={id}&page_size=1` per category | No group-by exists; cost = number of categories (currently 3, per the seeded V1 set — cheap today, but the *pattern* doesn't scale if categories grow) |
| Letters by classification | **B** | Same pattern, per classification | Same caveat |
| Letters by department (SYSTEM_ADMIN only) | **B** | One `GET /letters?department_id={id}&page_size=1` per department | Cost scales with department count; `ADMIN`/`USER` have no cross-department view to build this from at all |
| Letters received today/this week/this month | **B** | `GET /letters?received_from=X&received_to=Y&page_size=1` → `.total` | The backend supports an inclusive date range on `received_at` (confirmed, `letters.py`); one request per bucket, not a single "trend" call |
| Recent letters (a short list) | **A** | `GET /letters?sort_by=received_at&sort_order=desc&page_size=N` | Exactly what `LetterListPage` already does — direct reuse of `letterService.list` |
| Unread notifications | **A** | `GET /notifications/unread-count` | Already built (Phase 5E), reused as-is |
| Recent notifications | **A** | `GET /notifications?page=1&page_size=N` | Already built (Phase 5E) |
| Documents attached (per Letter) | **A**, contextual only | `GET /letters/{id}/documents` | Correct only inside a Letter's own detail page (Phase 5E); no cross-Letter document count/list endpoint exists — see §9 |
| Active departments | **B** | `GET /departments?status=ACTIVE` → `.total` (or `len(items)`) | Costs a full-object fetch of every active department (§2 table); SYSTEM_ADMIN only |
| Inactive departments | **B** | Same, `status=INACTIVE` | Same cost/role note |
| Active admins | **B** | `GET /admins?status=ACTIVE` → `.total` | Same cost note; SYSTEM_ADMIN only |
| Active users (own department) | **B** | `GET /users?status=ACTIVE` → `.total` | Same cost note; ADMIN only, own department |
| Pending Admin approvals | **B** | `GET /admins?status=PENDING_APPROVAL` → `.total` | Same cost note; SYSTEM_ADMIN only |
| Pending User approvals | **B** | `GET /users?status=PENDING_APPROVAL` → `.total` | Same cost note; ADMIN only, own department |
| Active User-authorization count | **B** | `GET /users/authorizations?status=ACTIVE` → `.total` | ADMIN only, own department |
| Letter trends over time (weekly/monthly series) | **C** | none | Would need a date-bucketed aggregate query; no endpoint groups by time bucket today |
| Department trends / comparisons | **C** | none | No cross-department aggregate exists; SYSTEM_ADMIN's only tool is per-department `total`, one request each, no time dimension |
| Classification trends | **C** | none | Same reasoning as department trends |
| Category trends | **C** | none | Same reasoning |
| Audit activity (any form) | **C** | none | No audit read API exists at all (§2) |
| Registration activity (accounts created over time) | **C** | none | Would require either an audit read API or a new date-bucketed User/Admin aggregate; neither exists |
| Average processing time (received → archived, or similar) | **D** | none | The concept itself is undefined — no business definition of what "processing" means for a Letter has ever been confirmed by any prior phase |
| Response time | **D** | none | Not a modeled concept anywhere in the schema; undefined |
| Workload (per user/department) | **D** | none | Undefined — "workload" could mean letters recorded, letters pending some action, or something else; no confirmed definition |
| Monthly comparisons (this month vs. last) | **C** | none | Same date-bucketing gap as trends above |
| Historical volumes | **C** | none | Same gap |

**Loading the entire Letter registry into the browser merely to compute
these client-side is explicitly `E — NOT RECOMMENDED`** for every
multi-bucket/trend metric above — see §10 for the cost analysis.

---

## 4. Current vs. historical metrics

**Current operational state** — CONFIRMED available today, class A or B
above: total/active/archived letter counts, unread notifications,
active departments/admins/users, pending Admin/User approvals, active
User-authorizations. These describe *right now*, need no time
dimension, and (mostly) cost one request each.

**Historical/analytical data** — trends, monthly comparisons, "letters
this month vs. last," processing time, workload, audit-derived activity
— every one of these is class C or D above. None is available from a
single existing request; several (processing time, workload, response
time) aren't even defined as business concepts yet, independent of
whether an endpoint exists.

**Do not use `AuditLog` for dashboard analytics merely because the
table exists** (the brief's own explicit instruction, and consistent
with `audit-notifications.md` §23's own conclusion): the table has no
read path from the API today. Everything downstream of it is `PENDING
BACKEND API`, not a frontend design decision.

---

## 5. Role-specific dashboard requirements

Per the brief's own instruction, the three illustrative lists in §7
(SYSTEM_ADMIN/ADMIN/USER "may potentially need...") were **not**
accepted as requirements — each was checked against what the backend
actually supports and against confirmed department/role isolation.

### 5.1 SYSTEM_ADMIN

Verified capable of, today: system-wide Letter counts (unrestricted —
`letter_visibility_filter` returns `None` for this role, and
`department_id` is optionally selectable), Department/Admin counts
(SYSTEM_ADMIN-only endpoints), pending Admin approvals, its own unread
notifications. **Not capable of, today, without a new endpoint**:
per-department breakdowns without N requests (§3), any trend/historical
view, any User-level metric (User endpoints are `require_admin`, not
reachable by SYSTEM_ADMIN at all — confirmed from `users.py`'s own
dependency).

### 5.2 ADMIN

Verified capable of, today: own-department Letter counts (scoped
automatically — `ADMIN` supplies no `department_id`, the service always
uses `user.department_id`), own-department active/pending User counts,
own-department User-authorization counts, its own unread notifications.
**Not capable of**: any other department's data (structurally — every
ADMIN-facing endpoint scopes to `user.department_id` server-side, with
no parameter to override it, confirmed from `list_users`/
`list_authorizations`), Department/Admin-level metrics (SYSTEM_ADMIN-
only endpoints, 403 for ADMIN).

### 5.3 USER

Verified capable of, today: own-department, classified-access-narrowed
Letter counts and a recent-Letters list (identical mechanism to
`LetterListPage`, already built), its own unread notifications.
**Not capable of, and should not attempt**: any Department/Admin/User
management metric (every relevant endpoint is `require_system_admin` or
`require_admin`, 403 for USER); any cross-department figure.

### 5.4 What remains genuinely open

Whether **any** dashboard should exist for USER at all, whether ADMIN's
dashboard should show anything beyond Letters+Users, and whether
SYSTEM_ADMIN's should default to a global or per-department view — none
of this is answered by the backend; all three are `PENDING BUSINESS
CLARIFICATION` (see §24).

---

## 6. Department isolation (CRITICAL)

**The dashboard must consume, never re-derive, isolation.** Every
metric proposed in §3 that is class A or B already comes from an
endpoint whose department scoping is enforced server-side and cannot be
overridden by a client-supplied parameter for ADMIN/USER — confirmed
directly, not assumed, for `letters.py` (`recipient_department_id`
derived from `user.department_id` unless `SYSTEM_ADMIN`),
`users.py`/`users.py` authorizations (`admin=current_user`, no override
parameter exists), and `admins.py`'s `department_id` filter (present,
but the endpoint itself is SYSTEM_ADMIN-only — an ADMIN cannot reach it
regardless).

**No metric in this review requires the frontend to fetch cross-
department data and filter it client-side to simulate isolation** — and
none should ever be built that way. Where a system-wide, department-
broken-out figure is wanted for SYSTEM_ADMIN (e.g., "letters per
department, all departments, one screen"), the *only* mechanisms
available today are either (a) one request per department against the
existing `GET /letters?department_id=X` (class B, bounded by how many
departments actually exist, acceptable at this project's expected
scale — a handful of departments, not hundreds) or (b) a new backend
aggregate endpoint (`PENDING BACKEND API`, §11). Option (a) is
**RECOMMENDED for V1 if a per-department breakdown is confirmed wanted
at all** (§24); it is bounded, uses only existing, already-isolated
endpoints, and requires no backend change.

---

## 7. Classified Letters (CRITICAL)

Confirmed directly (§2.1): `GET /letters`'s `total` already excludes
every classified-and-inaccessible-to-this-USER record, at the database
level, for every filter combination — there is nothing left for the
dashboard to additionally filter, hide, or adjust. This means:

* **A USER's Letter counts on a dashboard are already correct as-is**
  — reusing the exact same `letterService.list` call `LetterListPage`
  already makes, with `page_size=1`, produces an accurate, already-
  narrowed total. No frontend classification check is needed or should
  ever be added (the same discipline every prior phase has held to).
* **The dashboard must never present two counts whose difference would
  reveal a hidden record's existence** — for example, never show a
  SYSTEM_ADMIN-visible department total next to a USER's own narrower
  total on the same screen in a way that implies "N records are hidden
  from you." Each role's dashboard shows only its own role-scoped
  figures; the review found no legitimate V1 reason to juxtapose them.
* **A system-wide aggregate for SYSTEM_ADMIN is not subject to this
  problem at all** — `letter_visibility_filter` returns `None` for
  SYSTEM_ADMIN, meaning there is no classified narrowing to leak in the
  first place at that role.
* **If a future backend aggregate endpoint is ever built** (§11), it
  must apply the identical `letter_visibility_filter` logic the
  existing list endpoint already uses — never a separate, independently
  maintained count path that could silently drift out of sync with it.

---

## 8. Letter API assessment — pagination cost

`GET /letters` supports real pagination (`page`/`page_size`, `page_size`
capped at 100 server-side), whitelisted sorting, and per-field filters
including an inclusive `received_at` date range. This is more than
enough to safely produce **single-number, single-filter-combination
counts** (§3's class-A/B items) — one request each.

**It is explicitly not a safe basis for computing a full multi-
dimensional breakdown by paging through everything.** At `page_size=100`
(the maximum), a registry of even a few thousand Letters would require
dozens of round trips merely to enumerate every row once, before any
client-side aggregation could even begin — and that cost would need to
be paid again for every additional breakdown dimension (by category,
by classification, by department, by month), since there is no combined
group-by response. **RECOMMENDED**: this is architecturally the wrong
tool for anything beyond a handful of single-filter totals; a genuine
breakdown/trend widget should wait for a backend aggregate endpoint
(§11), never be built by exhaustively paging the registry client-side.
This is "technically possible" (the pagination exists) but **not
architecturally recommended** — exactly the distinction the brief asked
this section to draw.

---

## 9. Administration data assessment

Departments/Admins/Users/User-authorizations/Categories/Classifications
all share the same shape today: no pagination, a `total` that is really
just `len()` of the complete matching-row list (§2's table). This means
every count in §3 drawn from these five resources technically works
with a single request — but that request always returns full objects
for every matching row, not a lean count. At this project's current,
expected scale (a handful of departments, a modest number of Admins/
Users per department — the same scale Phase 5D's own review already
established has no pagination need yet) this is acceptable for V1
dashboard cards; **RECOMMENDED**: revisit if Phase 5D's own "does this
need pagination at real V1 volumes" question (`administration-ui.md`
§11/§22, still `PENDING BUSINESS CLARIFICATION`) is ever answered "yes"
— at that point, a dashboard depending on full-list fetches for a count
would need a lighter path too, and the two problems should be solved
together, not separately.

---

## 10. Notification integration

Phase 5E already built `NotificationBell` (unread count, polled every
60 seconds, paused when the tab is hidden), `NotificationPanel` (a
dropdown of recent notifications), and a full `/app/notifications`
page. **RECOMMENDED: the dashboard needs, at most, a thin summary —
reuse `notificationService.unreadCount()` for a card, and optionally
`notificationService.list({page: 1, page_size: N})` for a short "recent
notifications" list — never a second, independent notification-fetching
or polling mechanism.** No new polling interval should be introduced; a
dashboard widget should either read the same unread count
`NotificationBell` already displays (no additional request) or fetch
once on dashboard mount, matching every other widget's own load
behavior (§17). Duplicating `NotificationPanel`'s full interaction
surface (mark-read, mark-all-read) on the dashboard is **not
recommended** — the existing Topbar/`/app/notifications` experience
already covers that; a dashboard notification card should be read-only
and link to `/app/notifications` for anything beyond a glance, the same
pattern `NotificationPanel` itself already uses for its own "View all"
link.

**Recipient isolation must not be duplicated or re-implemented** — the
existing `notificationService.list`/`unreadCount` already send no
recipient identifier of any kind (Phase 5E, confirmed unchanged this
session); a dashboard widget reusing them inherits that guarantee for
free and must never add one.

---

## 11. Document integration

**RECOMMENDED: Documents do not belong on the dashboard as a metric.**
Confirmed directly: `LetterResponse` has no document-count field, and
no endpoint lists documents across Letters — `GET /letters/{id}/
documents` is inherently per-Letter (Phase 4D/5E). Producing "total
documents uploaded" or similar would require either paging through
every Letter and issuing one documents-list request per Letter (grossly
expensive, `E — NOT RECOMMENDED`) or a new backend aggregate (`PENDING
BACKEND API`, not proposed here absent a confirmed business need).
Documents remain, as Phase 5E's own review already concluded,
contextual to a Letter's own detail page — nothing found this phase
changes that conclusion.

---

## 12. Dashboard API gap analysis — what would justify new backend work

For every class-C item in §3, a real backend gap, not a frontend
limitation:

1. **Letter trend/breakdown aggregation** (by time bucket, category,
   classification, or department, singly or combined) — **why
   insufficient today**: no group-by/aggregate query exists; a client-
   side equivalent would cost one request per bucket at best, and full
   registry pagination at worst. **What's needed**: a backend endpoint
   that runs the aggregation in the database, applying the identical
   department/classified-visibility rules `list_letters` already
   enforces. **Minimum response**: counts grouped by the requested
   dimension only (e.g., `[{bucket: "2026-08", count: 41}, ...]`) —
   never full `Letter` rows. **Roles**: same visibility rules as
   `GET /letters` — SYSTEM_ADMIN unrestricted (optionally
   department-filtered), ADMIN/USER own-department (USER further
   classified-narrowed). **Isolation**: must reuse
   `letter_visibility_filter`/department-scoping exactly, not a
   parallel implementation.
2. **Audit-derived activity of any kind** — **why insufficient**: no
   read endpoint exists for `AuditLog` at all (§2). **What's needed**: a
   read API for `AuditLog` first (already `PENDING BACKEND API` per
   `audit-notifications.md` §9, unchanged by this review) — a dashboard
   consumer would be a downstream concern once that exists, not before.
3. **Cross-resource summary in one round trip** (e.g., "give me letter
   counts + pending approvals + unread notifications in one response")
   — **why insufficient today**: each figure requires its own request
   against its own resource's endpoint; nothing combines them.
   **What's needed**: *optional* — see §12.1 below for whether this is
   actually worth building for V1.
4. **Department/registration-activity-over-time** — **why
   insufficient**: same date-bucketing gap as trends above; no endpoint
   groups Admin/User creation by time. **What's needed**: either an
   audit read API (once built) or a purpose-built aggregate; not
   proposed here absent a confirmed need.

None of these are implemented, proposed as urgent, or assumed
necessary for V1 — see §23 for the actual V1 recommendation.

### 12.1 Is a combined `/dashboard/summary` endpoint actually the right shape?

The brief explicitly asked this question rather than assuming the
answer. **RECOMMENDED, if and when backend work is authorized**:
*separate*, narrow endpoints per concern rather than one combined
summary — e.g., a Letter-aggregate endpoint distinct from any future
audit-activity endpoint — because they have genuinely different
performance characteristics (one is a fast `COUNT`/`GROUP BY` against
`Letter`, the other would eventually read `AuditLog`), different
freshness requirements, and different role/department scoping rules
that are easier to reason about and test independently than inside one
combined handler. A single combined summary endpoint is not proposed;
this is a design opinion for a future implementation phase, not a
decision made here.

---

## 13. Dashboard layout (conceptual, RECOMMENDED)

```
Dashboard
├── Summary cards (role-scoped counts, §14)
├── Recent Letters (reuses letterService.list, sorted/limited)
├── Notifications (thin, reuses notificationService, links out to /app/notifications)
└── Quick actions (role-scoped shortcuts, §16)
```

No chart/visualization block appears in this recommended V1 layout —
see §15 for why. This is a starting shape, not a final design; exact
widget placement, card count, and responsive stacking are frontend
implementation-phase decisions, not architecture ones.

---

## 14. Summary cards

| Card | Class | Role scope | Refresh strategy | Backend aggregation needed? |
|---|---|---|---|---|
| Total letters | A | all (role-scoped automatically) | load on mount | No |
| Active letters | A | all | load on mount | No |
| Archived letters | A | all | load on mount | No |
| Unread notifications | A | all | reuse `NotificationBell`'s existing polled value | No |
| Pending Admin approvals | B | SYSTEM_ADMIN | load on mount | No (full-list cost, §9) |
| Pending User approvals | B | ADMIN | load on mount | No (full-list cost, §9) |
| Active departments | B | SYSTEM_ADMIN | load on mount | No (full-list cost, §9) |
| Active users (own department) | B | ADMIN | load on mount | No (full-list cost, §9) |

Every card above is `RECOMMENDED`, not `CONFIRMED` as a requirement —
whether the business actually wants each one is §24's own open
question. What *is* confirmed is that none of them requires new backend
work to display accurately and safely.

---

## 15. Charts/visualizations

**RECOMMENDED: no chart ships in V1.** Three independent reasons,
verified rather than assumed:

1. **No charting library is installed** (`package.json`, §1) — adding
   one is explicitly out of this phase's scope (§34) and, per §16 of
   the brief, should never be done "merely because a chart is visually
   appealing."
2. **Every chart-worthy metric in §3 (trends, breakdowns, historical
   volumes) is class C** — none is available from an existing request;
   building a chart today would mean either an expensive client-side
   aggregation (E, not recommended) or waiting on backend work that
   isn't authorized this phase.
3. **No business requirement for any specific chart has been confirmed**
   — §24 lists this as explicitly open.

If a future phase confirms both a specific chart requirement *and*
backend aggregate support for it, **RECOMMENDED**: prefer the smallest
dependency that satisfies the confirmed need over a general-purpose
charting framework, and confirm the choice against `frontend.md` §26's
existing "no UI framework without justification" discipline, which
applies equally to a charting library.

---

## 16. Recent activity

Three genuinely different sources exist; the brief's own instruction
not to conflate them is followed:

* **Recent Letters** — class A, available today (`letterService.list`
  sorted by `received_at`/`created_at` descending, limited). This alone
  is `RECOMMENDED` as sufficient for a V1 "recent activity" widget.
* **Recent notifications** — class A, already built (Phase 5E);
  distinct from "activity" in the sense of *system* events — these are
  personal, recipient-scoped alerts, not a log of what happened.
* **Recent audit events** — class C, `PENDING BACKEND API` (§2, §12) —
  no read path exists. If "recent activity" is ever meant to include
  things like approvals, deactivations, or department changes rather
  than just new Letters, that meaning requires the audit read API
  first, not a workaround.

**RECOMMENDED for V1**: "recent activity" means recent Letters only,
stated explicitly as such in the UI copy (not a generic unlabeled
"Activity" heading that implies more than it delivers) — a smaller,
honest scope rather than a name that overpromises.

---

## 17. Quick actions

Role-scoped shortcuts only, never a duplicate of the full navigation
system, and never an action the role cannot actually perform:

* **SYSTEM_ADMIN** — "Create Department" (`/app/system/departments/new`,
  a real existing route), "Authorize Admin"
  (`/app/system/admins/authorize`, existing). "View Letters" is already
  one Sidebar click away (`/app/system/letters`) — a quick action for it
  adds little; **PROVISIONAL**, include only if the dashboard is meant
  to be a genuine landing page rather than an overview screen reached
  from elsewhere.
* **ADMIN** — "Authorize User" (`/app/admin/users/authorize`, existing).
* **USER** — no create/authorize action exists for this role anywhere
  in the backend; "Record a Letter" (`/app/letters/new`, existing,
  `require_user_or_admin`) is the only legitimate shortcut.

Every action listed links to an **already-built** route — this section
proposes no new page, form, or endpoint. Whether quick actions belong
on the dashboard at all, versus relying on the existing Sidebar, is
`PENDING BUSINESS CLARIFICATION` (§24).

---

## 18. Filtering & date range

| Filter | Classification | Reasoning |
|---|---|---|
| Date range (on Letter-derived cards) | RECOMMENDED, narrow | The backend already supports `received_from`/`received_to`; a small set of fixed presets (today/this week/this month) is enough for V1 counts (§3) — a free-form range selector adds UI complexity for a V1 that doesn't yet have a confirmed use for arbitrary ranges |
| Department filter (SYSTEM_ADMIN dashboard only) | RECOMMENDED | Already supported by `GET /letters?department_id=` for SYSTEM_ADMIN; not meaningful for ADMIN/USER, who have no department parameter to begin with |
| Category filter | PROVISIONAL | Technically available (§3, class B) but adds N requests per rendered breakdown; only worth it if a category breakdown widget is confirmed wanted (§24) |
| Classification filter | PROVISIONAL | Same reasoning as category |
| Status filter (Active/Archived) | RECOMMENDED | Directly maps to the two summary cards already proposed (§14) |

No filter proposed here requires new backend support — every one is
class A/B against the existing Letter API. A filter that would require
backend aggregate support (e.g., an arbitrary custom date-bucketed
trend) is out of scope for V1 per §15's own conclusion.

---

## 19. Refresh strategy

**RECOMMENDED**: load once on dashboard mount, no automatic polling of
any kind for Letter/administration counts — these are operational
snapshots, not the kind of near-real-time data that justifies a
recurring request (the same reasoning `document-notification-ui.md`
§11.2 already applied to notification polling, restated here rather
than re-derived). **Reuse, don't duplicate, `NotificationBell`'s
existing 60-second poll** for any unread-count figure shown on the
dashboard — a second, independent interval polling the same endpoint
would double the request volume for no benefit and risks the two values
drifting visibly out of sync on screen. A manual "Refresh" affordance
on the dashboard itself is **PROVISIONAL** — reasonable, not required;
whether it's worth the added UI surface is a judgment call for the
implementation phase, not this review. Refresh-after-mutation (e.g., a
count updating right after a Quick Action succeeds) is **RECOMMENDED**
where the mutation happened *on* the dashboard itself (a Quick Action);
not recommended as a cross-page concern (a Letter created on
`LetterFormPage` need not push a live update back to a dashboard that
isn't currently mounted).

---

## 20. Error handling

**RECOMMENDED: independent widget failure, not a single dashboard-wide
error.** If a summary-card request fails, that card alone shows
`ErrorState` (reused as-is) with retry; the rest of the dashboard
renders normally. This is a design position for the *next* phase's
implementation, consistent with how every existing multi-section page
in this project already isolates its own async state (e.g.,
`LetterDetailPage`'s Documents section failing independently of the
Letter metadata around it, Phase 5E). Every existing status-code
semantic is preserved unchanged, reusing `errorNormalization.js` as-is:
a `401` triggers the existing centralized session-clear/redirect; a
`403` (e.g., an ADMIN's own department going inactive mid-session)
renders the existing generic permission message, never a dashboard-
specific variant; a `404`/`409`/`422`/`500`/network failure (`status: 0`)
all render via the existing `ErrorState` message, verbatim from the
backend where the backend supplies one. **No status code is ever
remapped** (403→404 or the reverse) — the same discipline every prior
phase has held to, restated here because the dashboard aggregates
several independent requests where that temptation could otherwise
arise.

---

## 21. Accessibility

**RECOMMENDED**, extending the existing Phase 5A-5E baseline, no new
pattern: summary cards need an accessible name and value (not color
alone to convey e.g. "pending approvals" urgency); any future chart
(none in V1, §15) would need a textual data-table alternative, not a
canvas/SVG-only representation; date-range presets need to be real,
labeled, keyboard-operable controls (buttons or a `<select>`, not
click-only chips); Quick Actions are just links/buttons — no new
accessibility pattern beyond what `Sidebar`'s existing `NavLink`s
already establish. Loading/error/empty states reuse
`LoadingState`/`ErrorState`/`EmptyState` verbatim, inheriting their
existing `role="status"`/`role="alert"` wiring — no new component
needed to satisfy this.

---

## 22. Responsive design

**RECOMMENDED**: CSS Modules + `styles/tokens.css` only, no new
dependency, matching every prior phase. Summary cards should be a
CSS Grid/flex-wrap layout that reflows from a multi-column row (desktop)
down to a single column (mobile) — the same responsive discipline
`DataTable.module.css`/`AppShell.module.css` already establish
elsewhere in this codebase. Since no chart ships in V1 (§15), the "can
charts shrink indefinitely" question the brief raised does not need an
answer this phase — deferred to whichever future phase actually adds
one, with an explicit accessible-alternative requirement already
established above (§21) for whenever that happens.

---

## 23. Performance

Assessed request cost for the §14 summary-card set, all loaded on
mount, no polling beyond the existing notification-bell interval:
roughly 4-8 requests total for a full SYSTEM_ADMIN dashboard (letters ×
2-3, departments, admins-pending, own unread-count reused from
`NotificationBell`), fewer for ADMIN/USER (no Department/Admin-level
cards apply to them at all). This is comparable to what
`AdminListPage`/`DepartmentListPage` already cost individually today —
**RECOMMENDED as acceptable for V1**, no batching/combining endpoint
needed to justify it (§12.1). **What must not happen, and is called out
explicitly because the brief asked for it**: the dashboard mounting
inside `AppShell` must not cause `NotificationBell`'s existing poll to
fire twice, or start a second independent poll for the same data — the
dashboard should read `NotificationBell`'s value (e.g., via a small
prop/context it already owns) or make its own single one-time fetch on
mount, never both an independent interval and the existing one running
concurrently. No React Query/Redux/Zustand or other state-management
library is introduced or needed to satisfy this — the existing
`useState`/`useEffect` convention every page in this project already
uses is sufficient, per the brief's own explicit instruction.

---

## 24. Security threat review

| # | Threat | Backend mitigation | Frontend responsibility | Remaining risk |
|---|---|---|---|---|
| 1 | Cross-department metric leakage | Every relevant endpoint scopes to `user.department_id` server-side with no client override (§6) | Never construct a request that guesses another department's id | None found — structurally enforced, matches Phase 5D's own conclusion for the same endpoints |
| 2 | Classified-record count leakage | `letter_visibility_filter` applied at the query level (§2.1, §7) | Never juxtapose a role-broader count against a role-narrower one on the same screen in a way that implies a hidden delta (§7) | Low — the one genuinely frontend-owned discipline this review adds; must be honored during implementation |
| 3 | Role-based metric leakage | Every admin-resource endpoint is `require_system_admin`/`require_admin` (403 otherwise) | Dashboard must render only cards the current role's endpoints can actually answer — never call, and silently swallow the failure of, an endpoint the role can't reach | Low, if widget visibility is derived from role, matching `Sidebar`'s existing convention |
| 4 | IDOR through dashboard filters | Every filter parameter this review proposes (department_id, category_id, classification_id, date range) is passed straight through to endpoints that already enforce their own scoping (§6) | Never invent a filter parameter the backend doesn't already validate/scope | None found — no new parameter is proposed that the backend doesn't already own |
| 5 | Client-side authorization | N/A — none proposed | No dashboard widget decides visibility independently; every figure is backend-scoped already (§6, §7) | None, provided implementation follows this review |
| 6 | Over-fetching | Letters use a real `COUNT` (§2); Departments/Admins/Users do not (§9) | Never request `page_size` larger than needed for a count-only card; never fetch a list merely to display a number if a smaller request would do | Low-Medium — inherent to the five non-`COUNT` resources until/unless a lighter backend path exists (§9); not a new risk this phase introduces, an existing one this review surfaces |
| 7 | Sensitive data exposure | `LetterResponse`/`DepartmentResponse`/etc. already omit sensitive fields (e.g. no `password_hash`, confirmed unchanged) | Dashboard cards should render counts/short lists only — never dump a full object list onto a summary screen | None found |
| 8 | Notification leakage | Recipient isolation is structural — no `recipient_user_id` parameter exists anywhere (Phase 5E, unchanged) | Reuse the existing service functions unmodified (§10); never add a recipient parameter | None, provided §10 is followed |
| 9 | Hidden resource inference | Same mechanism as #2 | Same discipline as #2 — a 404 or an absent card must not itself become a signal that something exists | Low |
| 10 | Stale role/department state | `AuthContext` is the single source of role/department/status, re-derived from `GET /auth/me` on session restore (unchanged since Phase 5A) | Dashboard must read role from `useAuth()`, never cache or hardcode it independently | None — same guarantee every existing role-gated screen already relies on |

---

## 25. Test plan (design only, not implemented)

Per the brief's explicit list, scoped to what this review actually
proposes (no chart, no trend widget, no new backend endpoint):

* Dashboard route renders only for an authenticated session (reuses
  `ProtectedRoute`, no new guard logic).
* Role-specific card set: SYSTEM_ADMIN sees Department/Admin cards,
  ADMIN sees User cards, USER sees neither — three role-driven render
  tests, matching the existing `Topbar.test.jsx`/`Sidebar` role-test
  pattern.
* Loading/empty/error states per widget, using the existing
  `LoadingState`/`EmptyState`/`ErrorState` primitives — no new
  assertions beyond what every other page's test file already checks.
* **Independent partial-widget failure** — one card's request rejects
  while the others succeed; assert the rest of the dashboard still
  renders (§20).
* Recent-Letters widget reuses `letterService.list` — assert the exact
  params sent (sort/limit), matching `LetterListPage.test.jsx`'s own
  parameter-shape assertions.
* Notification widget — assert it reads/reuses the existing service,
  sends no recipient parameter (mirroring
  `NotificationPanel.test.jsx`'s existing "never requests another
  user's notifications" test).
* Quick actions — assert only role-appropriate actions render, and each
  link points at an already-existing route.
* Classified/department-isolation behavior — assert no widget ever
  requests another department's id or exposes a hidden-record signal
  (§24 #2/#9).
* Session expiry (401) mid-dashboard-load — assert the existing
  centralized redirect fires, matching every other page's existing
  test.
* Responsive structure — a smoke-level test that summary cards render
  inside the existing grid container class, not a full visual-
  regression suite (this project has never had one).

Not designed here (no confirmed requirement to design a test plan
for): any chart, any trend widget, any audit-derived data — none of
these are being built.

---

## 26. Backend/API gap summary

Restating §12 as a compact list, each `PENDING BACKEND API` unless
noted:

* Letter aggregation/breakdown by time bucket, category, classification,
  or department in a single response.
* Any audit-derived dashboard data (blocked on the audit read API
  itself not existing — `PENDING BACKEND API`, inherited unchanged from
  `audit-notifications.md` §9).
* A lighter-weight, count-only path for Departments/Admins/Users/
  Categories/Classifications (today: full-object list only) — not
  urgent at current scale (§9), `PENDING BUSINESS CLARIFICATION` on
  whether/when it becomes worth building, tied to the same open
  pagination question Phase 5D's own review already raised.
* Any cross-Letter document metric (§11) — not proposed absent a
  confirmed need.
* Processing time / response time / workload — **not a backend gap at
  all yet**; the concepts themselves are undefined (`PENDING BUSINESS
  CLARIFICATION`, §3) — building an endpoint for an undefined metric
  would be building the wrong thing.

None of these is implemented, and none should be, before this review's
own open business questions (§24 below, brief's numbering; called §27
in this document since §24 above is the security review) are answered.

---

## 27. Business clarifications (genuinely open, not manufactured)

* What does management actually want to see on the dashboard? No
  specification exists anywhere in this project's history.
* Is the dashboard meant to be primarily operational (current counts)
  or analytical (trends/history)? §28 gives this review's own
  recommendation, but the underlying want is not confirmed.
* Should SYSTEM_ADMIN's dashboard default to a system-wide view or a
  per-department drill-down? Both are technically buildable (§6); which
  is wanted first is not confirmed.
* What time range should any date-scoped card default to (today/this
  week/this month)? Not confirmed.
* Are historical trends actually required for V1, or a later phase?
  Given every trend metric is class C (§3), this materially changes
  scope and is worth confirming explicitly before any backend work is
  requested.
* Which charts, if any, are actually useful? Not confirmed — and, per
  §15, moot until both a specific chart and its backing aggregate are
  both confirmed.
* Should pending approvals appear on SYSTEM_ADMIN's/ADMIN's dashboard,
  or is the existing `AdminListPage`/`UserListPage` status filter
  (`status=PENDING_APPROVAL`) sufficient on its own? Not confirmed.
* Should active users/admins/departments appear as dashboard cards, or
  is that administration-screen-only information? Not confirmed.
* Should the dashboard refresh automatically at all, beyond reusing the
  existing notification poll (§19)? Not confirmed.
* Should USER have a dashboard at all, given how little role-specific
  data is available to it beyond what `LetterListPage` already shows
  (§5.3)? Genuinely open — a USER dashboard could easily be redundant
  with the existing Letters screen.
* Is "recent activity" meant to mean Letters or audit-style events
  (§16)? This review recommends "Letters only" for V1 but the
  underlying want is not confirmed.
* Are exports required later? Not confirmed, and explicitly out of this
  phase's scope regardless (§34's own non-scope list).

---

## 28. V1 recommendation — assessed, not assumed

The brief's own proposed principle: *"Dashboard V1 should prioritize
operational visibility over analytics."* This review finds the
principle **supported by the evidence gathered this phase**, not merely
asserted: every current-state metric in §3 is class A or B (available
today, cheaply, with correct isolation already enforced); every
analytical/historical metric is class C or D (requires new backend
work, or isn't even defined as a business concept yet). Building
analytics into V1 would mean either (a) implementing new backend
aggregate endpoints with no confirmed business requirement driving
their exact shape (§27), or (b) computing them unsafely client-side via
full-registry pagination (§8, `E — NOT RECOMMENDED`). Neither is
justified by anything found this phase.

**RECOMMENDED, not confirmed as a business requirement**: V1 should be
operational-only — the §14 summary cards, §16's recent-Letters widget,
and the §10 notification reuse, nothing chart- or trend-shaped. This
recommendation is explicitly not silently promoted to a confirmed
requirement — §27's open questions, especially "is the dashboard
primarily operational or analytical," remain the business's decision
to make.

---

## 29. Implementation sequence (RECOMMENDED, not started)

1. **5F.1 — Business clarification pass.** Resolve, or explicitly defer,
   the §27 questions before writing frontend code — in particular
   "operational vs. analytical" and "does USER get a dashboard,"
   because both materially change scope.
2. **5F.2 — Dashboard frontend foundation.** Route (`/app/dashboard` or
   similar), navigation entry per role, `dashboardService.js` composing
   calls to the *existing* `letterService`/`notificationService`/
   `adminService`/`userService`/`departmentService` — no new backend
   endpoint needed for this slice.
3. **5F.3 — Operational widgets.** Summary cards (§14), recent Letters
   (§16), notification reuse (§10), quick actions (§17) — everything
   class A/B from §3.
4. **5F.4 — Optional analytics widgets.** Only if §27's "operational vs.
   analytical" question resolves toward wanting them, and only after
   the backend aggregate endpoint(s) they'd depend on (§12) are
   designed and built as their own, separate, reviewed phase — not
   bundled into this one.
5. **5F.5 — Tests.** Per §25, alongside each slice, matching every
   prior phase's own established practice rather than deferred to the
   end.
6. **5F.6 — Manual verification.** Against a real running backend, once
   implemented — not part of this review.
7. **5F.7 — Documentation.** This file's own future implementation-
   record section (matching `document-notification-ui.md` §27's
   pattern), plus the project documentation files listed in §30.
8. **5F.8 — Commit checkpoint.**

---

## 30. Documentation (this phase's own footprint)

Created: `docs/architecture/dashboard.md` (this file). Updated:
`README.md`, `docs/README.md`, `docs/PROJECT_STATUS.md`,
`docs/architecture/frontend.md`, `docs/architecture/overview.md` — all
recording that this review exists and what it covers, matching the
exact documentation-only footprint every prior review-only phase (4A,
4D's review, 4E's review, Phase 5's review, Phase 5D's review, Phase
5E's review) has left.

---

## 31. Explicit scope confirmation

This phase produced documentation only. It did **not** produce or
modify: any file under `frontend/src/`, any file under `backend/app/`
or `backend/alembic/`, any test file, any migration, any database
change, any configuration change, any package dependency change (no
charting library was installed). It did not implement a dashboard
React page, dashboard components, a backend dashboard API, an
analytics warehouse, reporting tables, an audit API, an audit UI,
exports, scheduled reports, email reports, background workers,
WebSockets, a new state-management library, or a charting library.
`git status` before and after this session is identical except for
this new documentation file and the five project documentation updates
listed in §30. Phase 5F implementation begins only when explicitly
instructed, per this project's standing rule that phases are reviewed
before the next begins.

---

## 32. Implementation record — IMPLEMENTED

Built directly on §1-31's own design — no new architecture decisions,
only the ones already recommended, built. Every item below is
IMPLEMENTED unless marked otherwise (PROVISIONAL/PENDING). Source was
re-verified fresh against current backend code before implementation
(§3 of the implementation brief) and found unchanged from this review's
own findings — no discrepancy to document.

### Routing and navigation (§4) — IMPLEMENTED

`routes/index.jsx` adds `{ path: 'dashboard', element: <DashboardPage /> }`
as a plain child route inside the existing `AppShell`/`ProtectedRoute`
tree — no new authentication or authorization mechanism, no
`RoleGuard` (the page itself renders role-appropriate content rather
than needing route-level restriction, since every role is meant to see
some version of it). **The existing `RootRedirect`/index-route
behavior is unchanged** — `/app`'s index route still redirects to
`letters`, exactly as the brief instructed; `/app/dashboard` is
additive, not a new default landing page. `navigationConfig.js` adds a
`Dashboard` entry as the first item for all three roles. No department
id is hardcoded anywhere in either file (verified by grep, §21 below).

### One dashboard, role-aware content (§5) — IMPLEMENTED

A single `DashboardPage` component, not three separate implementations.
Every Letter-derived and Notification request is **identical
regardless of role** — the same `letterService.list`/
`notificationService.unreadCount` calls `LetterListPage`/
`NotificationBell` already make, relying entirely on the backend's own
department/classified-access scoping (§6/§7 of the review); the
component never inspects or sends `user.department_id`. Only the
Administration summary and Quick Actions are role-conditional, and
only render/fetch for the role that can actually use them — a USER
triggers zero Department/Admin/User requests (verified by test).

### Metrics actually implemented (§7, §8, §9, §14 of the review) — IMPLEMENTED

Exactly the eight cards §14's own table named, no more:

* **Total / Active / Archived Letters** (all roles) — three
  `letterService.list({ ..., page_size: 1 })` calls, reading `.total`
  only — the real SQL `COUNT`, already department/classified-scoped
  server-side (§2.1/§7 of the review). No pagination through the
  registry; no multi-dimensional breakdown (by category, classification,
  department, or time) was built — every one of those remained class C
  in the review and was left out entirely, per the brief's own "if a
  metric requires an endpoint that doesn't exist, leave it out" rule.
* **Unread Notifications** (all roles) — one `notificationService.unreadCount()`
  call on mount. **Not a second polling mechanism** — `NotificationBell`
  (Phase 5E) keeps its own independent 60-second poll for the Topbar
  badge, entirely untouched; this is a single, one-time read of the
  same cheap endpoint, not an interval.
* **Active Departments / Pending Admin Approvals** (SYSTEM_ADMIN only)
  — `departmentService.list({status: 'ACTIVE'})` /
  `adminService.list({status: 'PENDING_APPROVAL'})`, reading `.total`.
* **Active Users / Pending User Approvals** (ADMIN only, own department
  — server-derived, no parameter sent) —
  `userService.list({status: 'ACTIVE'})` /
  `userService.list({status: 'PENDING_APPROVAL'})`.

**Not implemented, matching the review's own conclusions exactly**: any
chart, any trend, any historical/monthly figure, any department/
category/classification breakdown, any audit-derived metric, any
document count. No filter controls (date range, category,
classification) were added — the review marked these PROVISIONAL/not
confirmed as wanted, and the implementation brief's own approved scope
never asked for filter UI, so none was built.

### Recent Letters (§8, §16) — IMPLEMENTED

`RecentLetters` renders up to 5 Letters from one
`letterService.list({ sort_by: 'received_at', sort_order: 'desc', page_size: 5 })`
call — the same request shape `LetterListPage` already makes, not the
full registry. A Letter rendered is exactly what the backend returned;
nothing is inferred about Letters not returned. Clicking through uses
the existing `<Link to="/app/letters/:id">` route; a subsequent 404 is
handled entirely by `LetterDetailPage`'s existing, unmodified generic
not-found behavior — no explanation of *why* is ever attempted, matching
§8's own instruction.

### Quick Actions (§12, §17) — IMPLEMENTED, exactly the approved set

SYSTEM_ADMIN: Create Department, Authorize Admin. ADMIN: Authorize
User. USER: Record a Letter. **"View Letters" was deliberately left out
for every role** — the review marked it PROVISIONAL ("include only if
the dashboard is meant to be a genuine landing page"), and since the
index redirect still goes to `letters` directly (§4 above), the
Sidebar's own existing link is already the more natural path — adding
a duplicate here would be clutter without new capability. Every action
links to an already-existing route; none was invented.

### Notification integration (§10) — IMPLEMENTED, no duplication

Reuses `notificationService.unreadCount()` only — no second interval,
no duplicated `NotificationPanel` UI, no recipient parameter sent
(verified by test: the call takes no arguments at all). A full,
interactive notification list remains exactly where Phase 5E put it
(`NotificationBell`'s dropdown and `/app/notifications`); the dashboard
shows only the count.

### Document integration (§11) — NOT IMPLEMENTED, per the review

No document metric of any kind appears on the dashboard — the review
found no cross-Letter document endpoint exists and recommended against
building one speculatively. Nothing here changes that.

### Component architecture (§13) — IMPLEMENTED, minimal set

`SummaryCard` (reused 4-8 times depending on role), `RecentLetters`,
`QuickActions`, and `DashboardPage` itself. No `DashboardSummary`
wrapper component was created — the summary-cards grid is a plain
`<section>` inside `DashboardPage`, since nothing else would reuse a
separate wrapper. `RecentLetters` deliberately does not reuse the full
`LetterTable` — a dashboard widget has no sorting/filtering
interaction to justify that component's extra surface; a small list of
links is enough. Every loading/error/empty state reuses
`LoadingState`/`ErrorState`/`EmptyState` unchanged; `StatusBadge` is
reused for each Recent-Letters row's status. No UI framework, no
charting library.

### Data fetching (§14) — IMPLEMENTED, no new abstraction

**No `dashboardService.js` was created.** `DashboardPage` calls
`letterService`/`notificationService`/`departmentService`/
`adminService`/`userService` directly — each metric is already exactly
one call to an existing service function; wrapping them in a combined
service would have added a layer with nothing of its own to do. Four
independent fetch groups (Letters summary, Administration summary,
Notifications, Recent Letters), each with its own `loading`/`error`
state, matching `LetterListPage`'s own established
`useCallback`+`useEffect` convention exactly.

### Loading / error / partial failure (§15) — IMPLEMENTED, verified by test

A failed widget never blocks or hides the others — verified directly:
a rejected Letters-summary request still lets Recent Letters and the
Notifications count render normally. A failed `SummaryCard` shows
"Unavailable" (`role="alert"`), never a fabricated `0` — verified by
test that a real `0` and the failure text are never both mistaken for
each other.

### HTTP error semantics (§16) — IMPLEMENTED, unchanged

No status code is remapped anywhere in the new code (verified by
reading every `.catch` — each stores the normalized error object
as-is). A `401` continues through the existing centralized
`apiClient`/`AuthContext` redirect, unmodified; no dashboard-specific
authentication handling was added.

### Accessibility (§17) — IMPLEMENTED

Semantic `h1`/`h2` headings for the page and each section; `SummaryCard`
values are real text, not color-only; `RecentLetters`/`QuickActions`
use ordinary `<Link>`s (keyboard-focusable, visible focus inherited
from the existing global focus-ring styles); loading/error states
reuse `LoadingState`/`ErrorState`'s existing `role="status"`/
`role="alert"` wiring. No chart was added, so no chart-accessibility
question arises this phase.

### Responsive design (§18) — IMPLEMENTED

`DashboardPage.module.css` uses `grid-template-columns:
repeat(auto-fit, minmax(180px, 1fr))` for the summary cards, narrowing
to two, then one, column at the existing tablet/mobile breakpoints —
CSS Modules + `tokens.css` only, no new dependency.

### Visual design (§19) — IMPLEMENTED

Plain cards, a list, and link-styled buttons — no gradients, no
decorative animation, no invented KPI, no percentage without a
confirmed meaning. Every number on the page traces to one real backend
`.total`.

### Tests (§20) — IMPLEMENTED

33 new tests across 5 files (`components/SummaryCard.test.jsx` — 3,
`components/RecentLetters.test.jsx` — 5, `components/QuickActions.test.jsx`
— 5, `pages/DashboardPage.test.jsx` — 11, plus 3 updated assertions in
`navigation/navigationConfig.test.js`, unchanged in count but updated
for the new `Dashboard` entry). Covers: role-specific rendering (three
roles, asserting both what renders and what does **not**), summary
cards, loading/error/empty states, independent partial-widget failure,
Recent Letters navigation, exact request-parameter shape (proving no
`department_id`/oversized `page_size` is ever sent), notification
reuse with zero arguments, and accessible heading structure. Backend
tests were not modified.

### Security review (§21 of the brief) — verified this phase, not merely designed

Grepped every new/changed frontend file for `jwt`/`decode`/
`localStorage`/`department_id`-as-authorization/`recipient_user_id`/
`dangerouslySetInnerHTML`/hardcoded classification logic. The only
matches are: a doc comment stating `department_id` is deliberately
never sent, and four `role === '...'` branches — all four are
presentation-only (which cards/actions to show), never a data-access
decision; every request the component makes remains subject to the
backend's own role/department checks regardless of what these branches
decide, the same "role-aware presentation is fine, frontend
authorization is not" principle every prior phase has already followed.

### Build / regression — IMPLEMENTED, verified

`npm run build` succeeds (184 modules, no errors). `npm run test` —
**249 passed**, 0 failed, run 3 consecutive times against the final
code. Backend regression: `pytest tests/` — **458 passed**, unaffected,
confirming zero backend impact. `git status` confirms no file under
`backend/app/`, `backend/alembic/`, or `backend/tests/` was touched, and
no dependency was added.

**One test-infrastructure issue found and fixed, not a logic defect**:
`LetterFormPage.test.jsx`'s character-by-character `userEvent.type`
interaction tests began intermittently missing Vitest's 5000ms default
per-test timeout once the full suite grew past ~30 files, purely from
worker-thread contention under full-suite load (confirmed
non-deterministic — the same tests failed, then passed, then failed
again across consecutive identical runs with no code change, and always
passed reliably in isolation). Fixed by raising `testTimeout` to
10000ms in `vite.config.js` — headroom, not a weakened assertion;
re-confirmed 3 consecutive clean full-suite runs afterward.

### Manual verification (§23 of the brief) — NOT PERFORMED

No backend or dev environment was running at any point in this
session. Reported honestly rather than claimed, per the brief's own
instruction.

### Known limitations (post-implementation, restating this review's own findings — none newly discovered)

* **No breakdown/trend/chart of any kind** — every such metric
  remained class C in the review; none was built. `PENDING BACKEND
  API`.
* **No filter controls** (date range, category, classification,
  department) — the review left these PROVISIONAL/unconfirmed as
  wanted; none was built pending that confirmation. `PENDING BUSINESS
  CLARIFICATION`.
* **Administration counts cost a full-object list fetch** (no database
  `COUNT`, no pagination on Departments/Admins/Users) — unchanged
  backend limitation, acceptable at current scale per §9 of the review.
* **No manual QA against a running backend** — automated verification
  only, this session.

---

## 33. Phase 5G — Backend Dashboard Aggregation & Analytics API (cross-reference)

A dedicated follow-up review,
[`dashboard-analytics-api.md`](dashboard-analytics-api.md), assessed
whether the backend should provide additional aggregate/analytics
endpoints beyond what this document's own §14/§26 already flagged as
`PENDING BACKEND API`/`PENDING/FUTURE`. **Finding: no metric it
inventoried both needs a new backend endpoint and has confirmed
business value** — the operational dashboard this document describes
already covers everything the evidence supports building, restated and
now doubly confirmed from the backend side. That review documents a
complete, ready-to-build `GET /api/v1/letters/aggregate` design
(reusing this project's existing `letter_visibility_filter`/
department-derivation authorization logic directly, no new predicate)
for if and when a specific breakdown or trend is ever confirmed
wanted — nothing was implemented. See that document's own §27-§28 for
the exact open business questions and its V1 recommendation.

**Update, Phase 6C**: a confirmed supervisor requirement (this
document's own KPI-card interpretability gap, §27's first open
question) resolved the "not yet confirmed" status above. Phase 6C
implemented `GET /api/v1/letters/aggregate` exactly as this section's
design described, reassessed against Phase 6A's new correspondence
fields in the interim — see [`dashboard-analytics-api.md`](dashboard-analytics-api.md)'s
own "Phase 6C" section for the implementation record. This document's
own `DashboardPage.jsx` and its widgets remain **unmodified** — no
chart consumes the new endpoint yet; that is explicitly a later,
separate phase's work.

---

## 34. Phase 6D — Dashboard Operational Graphs (implementation record)

**Trigger**: the supervisor explicitly requested the KPI-card
presentation itself be replaced with graphs — not merely that new data
become available (§33's Phase 6C update), but that the numeric-card
format be retired because non-technical staff found it hard to
interpret. This phase is frontend-only; the backend `GET
/letters/aggregate` contract (Phase 6C) was consumed exactly as
published, with no backend change required or made.

### 34.1 Chart library decision

`package.json` was inspected first, per this phase's own instruction.
No chart library of any kind is installed (`axios`, `react`,
`react-dom`, `react-router-dom` are the only runtime dependencies).
**Decision: no dependency was installed.** Every required
visualization — two horizontal bar comparisons and one time-series
trend — is achievable with plain CSS (`<div>`-based proportional-width
bars) and a small hand-written SVG polyline plot, both trivial in
scope next to a general-purpose charting library. This also fits the
existing "Precision Ledger" design language better than a generic
library's own default styling would (§15 of this phase's brief:
"avoid...decoration"), and keeps the bundle size and dependency surface
unchanged. This was a genuine evaluation, not an assumption — had the
required visualizations needed real geographic maps, complex
statistical plots, or heavy interactivity, this section would instead
report that finding and stop, per the brief's own instruction. They did
not.

### 34.2 What was built

Two new reusable chart components (`frontend/src/components/`):

* **`HorizontalBarChart.jsx`** — a plain CSS bar-track component reused
  for all three bar-shaped graphs (Incoming vs. Outgoing, Received by
  Department, Sent by Department). Deliberately not three bespoke
  components, since none differs in shape, only in which bars and
  labels it carries — the same reuse discipline `SummaryCard` already
  established for the old KPI cards. Every label and count is real,
  always-visible HTML text directly beside its bar — the visual *is*
  the accessible text, not a separate representation bolted on
  afterward. A horizontal layout means a long department name grows the
  row's height, never the page's width — no truncation, no overflow.
* **`CorrespondenceTrendChart.jsx`** — a two-series SVG line plot
  (Incoming solid, Outgoing dashed — distinguished by line style as
  well as color) with a real, visible text legend and a keyboard-
  accessible `<details>` disclosure containing the exact monthly counts
  as an actual `<table>`. The SVG itself is `aria-hidden` — it is a
  redundant visualization of information the legend and table already
  state as real text, never the sole source of a value.
* **`utils/aggregateChartHelpers.js`** — pure functions
  (`directionBars`, `departmentBars`, `formatMonthLabel`,
  `mergeTrendSeries`) turning a raw `{ key, count }` bucket list into
  chart-ready shapes. No React, no Axios — fully unit-testable in
  isolation, matching this project's existing `utils/` convention
  (`formValidation.js`, `statusLabels.js`).
* **`services/letterService.js`** — one new `aggregate(params)`
  function (`GET /letters/aggregate`), added directly to the existing,
  already-consolidated Letter service module rather than a new
  `dashboardAnalyticsService.js` — the brief's own instruction to only
  introduce a dedicated service module if it "genuinely improves
  reuse/testability" was evaluated and declined: this is a Letter-
  resource endpoint, exactly like `list`/`get`/`create` above it in the
  same file, and a second module would only fragment one resource's API
  surface across two files for no benefit.
* **`pages/DashboardPage.jsx`/`.module.css`** — rewritten (see §34.3).

### 34.3 KPI removal

The eight role-dependent `SummaryCard`s are gone. Two small headline
figures remain — **Total Letters** and **Unread Notifications** —
genuinely orienting numbers a reader wants before the charts below
break the total down further, not a shrunk-down copy of the removed
card wall. The Active/Archived Letters split (previously two more
cards) was dropped: the new Incoming/Outgoing direction chart and the
department charts now carry that kind of breakdown responsibility, and
keeping a redundant Active/Archived pair alongside four new charts
would reintroduce the "chart/number overload" this phase's brief
explicitly warned against.

The four SYSTEM_ADMIN/ADMIN-only administration cards (Active
Departments, Pending Admin Approvals, Active Users, Pending User
Approvals) were **not** reintroduced in any form — as cards or as
charts. They answer an administration question (how many departments/
users exist or are pending), not the confirmed correspondence-volume
question this phase's brief named (direction, department flow, time
trend); the Departments/Administrators/Users screens (Phase 5D) already
show this exact data. Per the brief's own §10 instruction ("do not
reintroduce...unless actually useful to the supervisor's operational
requirement"), no confirmed need was found, so they were left out —
`departmentService.list()`/`adminService.list()`/`userService.list()`
calls for administration-summary purposes are gone from this page
entirely (the department-name lookup that remains is for a completely
different purpose — resolving department-id chart labels, §34.4 — and
calls the same endpoint for a different reason).

### 34.4 The four graphs

1. **Incoming vs. Outgoing** (`group_by=direction`) —
   `HorizontalBarChart` with two bars in a fixed order (Incoming always
   first), each direction's own label serving as the primary means of
   distinguishing them — color is reinforced by, never a substitute
   for, the adjacent text.
2. **Letters Received by Department** (`group_by=department`) —
   `HorizontalBarChart`, department-id keys resolved to names via one
   shared `GET /departments` request (already readable by any role
   since Phase 5H), reused by graph 3 too rather than fetched twice.
   Backend ordering (count descending, key ascending) is preserved
   exactly — never re-sorted client-side. No top-N truncation — every
   department returned appears as its own row.
3. **Letters Sent by Department** (`group_by=dispatch_department`) —
   same component, the real Phase 6A dispatch-target dimension, **not**
   `source_department_id` (which carries no authorization meaning and
   answers "who claims to have sent this," not "which department is
   this system's own confirmed dispatch destination" — see
   `dashboard-analytics-api.md` §6).
4. **Correspondence Activity Over Time** (`group_by=month`, filtered by
   `direction`) — `CorrespondenceTrendChart`. `month` was chosen over
   `day`/`week` per the brief's own steer ("prefer month if it provides
   a meaningful overview without excessive noise") — this project has
   no confirmed high-volume correspondence pattern that would need
   finer daily granularity, and `month` keeps the plot legible even
   after a year of data. Comparing Incoming vs. Outgoing over time uses
   **two** bounded, direction-filtered requests
   (`group_by=month&direction=INCOMING` /
   `...&direction=OUTGOING`), merged client-side by date key only
   (`mergeTrendSeries`) — never by re-counting Letters, never one
   request per bucket. This is the deliberate, bounded workaround the
   brief's own §7 anticipated for the Phase 6C API's lack of a
   two-dimensional `group_by`, not a fabricated one.

### 34.5 Department × Direction — DEFERRED

Explicitly evaluated and left out, per the brief's own §8. A
department/direction cross-tabulation (e.g. "which department sent the
most Outgoing correspondence" broken out per department) would need
either a two-dimensional backend aggregate (which Phase 6C's own design
deliberately does not provide — `dashboard-analytics-api.md` §32.9) or
one request per department (explicitly forbidden by this phase's own
§7/§20 performance instructions). **DEFERRED — requires a
two-dimensional aggregate endpoint.** No placeholder, "coming soon"
panel, or client-side pseudo-aggregation was added to the UI for this;
it is simply absent.

### 34.6 Date range / filters

Kept minimal, per the brief's own §11 instruction ("if date filtering
was not previously established as a dashboard requirement, keep it
minimal"): `dashboard.md`'s own history confirms no date-range concept
has ever existed on this dashboard. No preset control (This month/Last
month/Last 3 months/This year) was added this phase — every chart
requests its full available history with no `received_from`/
`received_to` filter. This is a genuine, disclosed limitation, not an
oversight: a future phase can add a shared date-range control across
all four charts once a specific default/preset is confirmed wanted
(the same open question `dashboard-analytics-api.md` §27 already
named, still unresolved).

### 34.7 Refresh

No new polling loop of any kind. `NotificationBell`'s own existing
unread-count poll (Topbar) is completely untouched. Every chart fetches
once on `DashboardPage` mount, via the same `useEffect`/`useCallback`
pattern every other widget on this page already used before this
phase — no explicit "Refresh" button was added, since no confirmed
requirement named one and the existing lifecycle (navigate away, then
back) already re-fetches everything.

### 34.8 Data fetching discipline

Nine requests fire on a full dashboard load: Total Letters (1),
Unread Notifications (1), Recent Letters (1, unchanged from Phase 5F),
`group_by=direction` (1), `group_by=department` (1),
`group_by=dispatch_department` (1), `group_by=month` × 2 directions
(2), and one shared `GET /departments` call for name resolution (1).
Bounded and predictable regardless of how many departments or Letters
exist — never one request per department, never a full-registry fetch,
never client-side counting. Every chart's loading/error state is
tracked independently (mirroring the existing per-widget `{ loading,
error, data }` state shape `RecentLetters`/the old `SummaryCard`s
already used) — the received/sent department charts additionally
depend on the shared department-name lookup succeeding, so a failure
of that one shared request affects those two charts together without
affecting the direction chart, the trend chart, the headline figures,
Recent Letters, or Quick Actions.

### 34.9 Accessibility

No chart's information exists only as a rendered graphic. The bar
charts' labels and counts are real HTML text next to each bar; the
trend chart's SVG is `aria-hidden` and duplicated by a real text legend
plus a keyboard-operable `<details>`/`<table>` disclosure — never a
hover-only tooltip. Direction is distinguished primarily by its own
text label; the trend chart's two series are distinguished by line
style (solid vs. dashed) and marker shape (circle vs. square) in
addition to color, named in the legend's own text. Every chart section
has a real `<h2>` (the existing `sectionHeader`/`h2` pattern this page
already used) plus a one-line description paragraph. **No WCAG
compliance is claimed** — this is a reasoned accessibility design, not
an audit.

### 34.10 Visual design

No new dependency, no gradient, no glow, no 3D effect, no pie chart, no
decorative animation. Bar fills use the existing `--color-primary`
token; the trend chart's two lines use the existing `--color-primary`/
`--color-accent` pair. Chart sections reuse the exact same
`.section`-style surface (`--color-surface`/`--color-border`/
`--radius-md`/`--space-md`) every other Dashboard section already
uses — no new surface treatment was invented.

### 34.11 Responsive design

The bar chart's row grid narrows its label/track column widths at the
768px and 480px breakpoints (the existing documented breakpoints,
`tokens.css`) rather than introducing a new one; a bar row stacks
vertically below 480px so a long department name never causes
horizontal overflow. The trend chart's SVG uses a `viewBox` with
`preserveAspectRatio="none"`, so it scales fluidly to its container's
width at any viewport; its fixed height is reduced at the 768px
breakpoint. The chart section stack (`.charts`) is a single column at
every width — it was never a multi-column grid, so nothing needs to
collapse.

### 34.12 Security boundary

No file under `src/context/`, `src/routes/`, `services/tokenStorage.js`,
or `services/apiClient.js` was touched (confirmed via `git status`
before and after this phase). No role-based chart hiding was added —
every chart renders for every role, exactly as §10 of the brief
required, with the aggregate API itself remaining the sole
authorization boundary. `letterService.aggregate()` forwards its
`params` object as-is (a read-only query-string, never a write
payload) — the same pattern `list()` already used.

### 34.13 Testing

23 new tests for the two chart components and the helper module
(`HorizontalBarChart.test.jsx` — 8, `CorrespondenceTrendChart.test.jsx`
— 7, `aggregateChartHelpers.test.js` — 8), covering loading/error/empty
states, real-text label/count rendering, ordering preservation, long-
label non-truncation, and the accessible table/legend content. The
existing `DashboardPage.test.jsx` (16 tests, all asserting the removed
KPI cards) was rewritten — not weakened — into 14 tests covering the
new headline figures, confirmation that the retired administration
cards render for no role, that every chart requests the aggregate
endpoint (never `/letters` pagination, never a `department_id`
parameter), department-name resolution, independent per-chart failure,
the empty-state distinction from a misleading zero-looking chart, and
that Recent Letters/Quick Actions/notification behavior is unchanged.
Full frontend suite: 409 tests (54 files), run 3 consecutive times with
identical results.

### 34.14 Manual verification

**Partially performed, honestly limited.** The Vite dev server was
started and confirmed to boot and serve `200 OK` with zero build/
runtime console errors, and a clean `npm run build` was confirmed to
include the new chart components' actual rendered strings in the
production bundle (not merely compile without erroring). **Full manual
browser verification — visually inspecting rendered charts, testing
at real desktop/tablet/mobile widths, comparing chart values against a
known set of manually-created Letters across SYSTEM_ADMIN/ADMIN/USER —
was not performed**, consistent with every prior phase in this
project: no browser-automation tool is available in this environment.
Every functional claim in this section is backed by the automated test
suite in §34.13, not by observing the running application in a real
browser.

### 34.15 Explicit scope confirmation

Modified: `frontend/src/pages/DashboardPage.jsx`,
`frontend/src/pages/DashboardPage.module.css`,
`frontend/src/pages/DashboardPage.test.jsx`,
`frontend/src/services/letterService.js`. Created:
`frontend/src/components/HorizontalBarChart.jsx`/`.module.css`/`.test.jsx`,
`frontend/src/components/CorrespondenceTrendChart.jsx`/`.module.css`/`.test.jsx`,
`frontend/src/utils/aggregateChartHelpers.js`/`.test.js`, this section.
**Not** touched: any backend file (no genuine API deficiency was
found — the Phase 6C contract was sufficient as published), `AuthContext`,
`RoleGuard`, `ProtectedRoute`, `tokenStorage.js`, `apiClient.js`,
`NotificationBell`, any Letter/Document/Notification/correspondence
lifecycle file, `package.json` (no dependency added or removed). Not
committed, not pushed, per this phase's own explicit instruction.

---

## 35. Phase 6D — Final Polish & Handover Verification

This is the project's **final implementation phase** — no Phase 6E
follows. The goal was not a redesign: inspect the already-implemented
and already-tested Phase 6D dashboard for real problems, fix only what
manual verification actually found, and confirm the project is ready
for handover.

### 35.1 Manual browser verification — honestly limited, substituted with a stronger check where possible

No browser-automation or screenshot tool is available in this
environment (confirmed again this phase — `WebFetch` converts HTML to
markdown via a model and does not execute JavaScript, so it cannot
render this single-page application; there is no Playwright/Puppeteer/
screenshot capability). **Pixel-level visual verification — exact
spacing, font rendering, hover states — was not performed and cannot
be honestly claimed.**

In its place, a genuine, stronger-than-usual verification was run
against the real dev environment instead of relying on source
inspection alone:

* The Vite dev server was confirmed to boot cleanly (`200 OK`, zero
  console errors) and a clean production build was confirmed to
  contain the actual new component output (not merely compile).
* **A full backend server was started** (`uvicorn`, port 8123) against
  the real dev PostgreSQL database — the same database this project's
  own backend test suite uses.
* **Two brand-new, clearly-labeled throwaway accounts** were created
  (`phase6d.verify.finance@example.com` in the real Finance
  department, `phase6d.verify.pd@example.com` in the real P&D
  department) and logged in through the real `/api/v1/auth/login`
  endpoint — never by minting a token for an existing real person's
  account. An earlier attempt to do the latter (mint tokens for the
  project's actual existing user accounts to save a step) was correctly
  blocked by this session's own safety tooling as account
  impersonation; creating fresh accounts of its own instead was the
  correct, non-impersonating alternative, confirmed with AJ before
  writing anything to the real dev database.
* **Two clearly-labeled OUTGOING letters** (`PHASE6D-VERIFY-OUT-1`,
  `PHASE6D-VERIFY-OUT-2`) were created through the real
  `POST /api/v1/letters` endpoint — Finance dispatching to P&D, and
  P&D dispatching to Finance — a small, known sample, not fabricated
  bulk data.
* **Every value the four dashboard charts would render was computed by
  hand from this known sample and compared against the real
  `GET /letters/aggregate` response** — not simulated, not mocked:

  | Dimension | Hand-computed expectation | Actual API response |
  |---|---|---|
  | `direction` | INCOMING 4, OUTGOING 2 | INCOMING 4, OUTGOING 2 ✓ |
  | `department` | Finance 5, P&D 1 | Finance 5, P&D 1 ✓ |
  | `dispatch_department` | P&D 1, Finance 1 | P&D 1, Finance 1 ✓ |
  | `month` (all) | Jul 1, Aug 5 | Jul 1, Aug 5 ✓ |
  | `month`, `direction=INCOMING` | Aug 4 | Aug 4 ✓ |
  | `month`, `direction=OUTGOING` | Jul 1, Aug 1 | Jul 1, Aug 1 ✓ |

  Every figure matched exactly. This directly exercises the same query
  path, the same repository/service code, and the same response shape
  the frontend's `directionBars`/`departmentBars`/`mergeTrendSeries`
  helpers consume — a real end-to-end confirmation of "dashboard
  aggregate → actual registry," per this phase's own §6 instruction.
* **Role scoping was verified live**, not just asserted from tests: the
  Finance throwaway account's own aggregate calls returned only its 5
  own letters (never P&D's), a `department_id` parameter it supplied
  pointing at P&D was silently ignored exactly as designed, and the
  P&D account saw only its own 1 letter. This is the same guarantee
  the automated test suite already covers, re-confirmed against a live
  server rather than only a test client.
* **Cleanup**: both test letters were archived (`DELETE
  /letters/{id}` — status → `ARCHIVED`, never a physical delete,
  matching this system's own established convention) and all three
  throwaway accounts were set to `DEACTIVATED`. Neither action is a
  hard delete — this system has no such capability by design — so
  these rows remain in the dev database as inert, clearly-labeled,
  archived/deactivated history. **AJ should be aware**: the dev
  database's real "Total Letters" figure now reads 6, not 4, until/
  unless these two archived rows are removed by a direct database
  operation, which was not performed without being explicitly asked to
  do so (a genuinely destructive action outside this project's own
  established API surface).

### 35.2 Genuine refinement made

**`CorrespondenceTrendChart`'s x-axis previously labeled only the
first and last month.** With the real dev data at the time of Phase
6D's own implementation (and still, at the time this final phase
began) there were only ever 1-2 distinct months of correspondence, so
this happened to label every month that existed — the gap was latent,
not yet visible. Re-reading the component fresh for this phase (per
its own §1 instruction not to rely on prior reports) surfaced it as a
real defect against this phase's own explicit verification criterion,
"month labels are readable": a third month would have gone completely
unlabeled on the graphic, with no way to know which point on the line
it corresponded to without opening the "View exact monthly counts"
disclosure. Fixed via `selectAxisTicks()` — every point gets a label
when there are 6 or fewer, and a thinned, evenly-spaced subset
(always including the first and last) for longer series, so labels
never overlap into an unreadable smear regardless of how much history
accumulates after handover. Two new regression tests cover this
exactly: a 3-month series correctly labels the middle month, and a
12-month series thins to fewer than 12 labels while always keeping the
first and last.

This was the **only** code change made this phase — the rest of the
implementation was inspected and confirmed correct, not altered.

### 35.3 Reviewed and confirmed correct — not changed

Matching this project's own established practice (Phase 5I.6) of
documenting what was *deliberately left alone* after genuine
consideration, not just what was changed:

* **Chart data scaling** (§3.A/§12 of this phase's brief) — each bar
  chart's width is `count / max(count in this chart)`, confirmed
  correct and non-misleading by the live data-accuracy check above (a
  2-vs-4 count produced a visually-proportional 50%-width bar,
  verified by the underlying math, not assumed).
* **Dispatch semantics** (§3.C) — confirmed via live verification that
  `group_by=dispatch_department` reflects the real Phase 6A dispatch
  target and never `source_department_id`; re-read `DashboardPage.jsx`
  fresh and confirmed no such substitution exists anywhere in the code.
* **KPI prominence** (§5) — the two remaining headline figures
  (`.headline`, `max-width: 480px`, two cards) were re-assessed against
  "do they visually compete with the charts." Given they occupy a
  fraction of the width the old eight-card wall did, and sit above a
  clear visual break (`.header`'s existing border) before the charts
  begin, no genuine competition was found — left unchanged rather than
  shrunk further without a concrete, observed problem to fix.
* **Department × Direction deferral** (§8 of this phase's own
  brief, restating §32.9/§34.5) — re-confirmed still correctly absent;
  no placeholder or client-side pseudo-aggregation was ever added.
* **Filters / date range** (§8 of the brief) — Phase 6D never
  implemented date controls (§34.6), so this phase's own §8 verification
  ("if Phase 6D implemented date controls, verify they work") does not
  apply; re-confirmed no such control exists, and none was added this
  phase (no "complicated filter controls during this final phase," per
  the brief's own instruction).
* **Accessibility** (§10) — re-read every chart component fresh:
  headings are real `<h2>`s, every value is real text, the trend
  chart's data table is a genuine `<table>` with `<th scope>`, decorative
  SVGs carry `aria-hidden="true"`, and no information depends on color
  alone (direction is distinguished primarily by its own text label;
  the trend's two series by line style and marker shape). No formal
  WCAG audit is claimed.
* **Performance** (§12) — re-confirmed nine bounded requests on load,
  no per-department request, no polling loop, no client-side
  aggregation, no new dependency, no large asset.
* **Security boundary** (§13) — re-confirmed via `git status` that no
  file under `context/`, `routes/`, `tokenStorage.js`, or
  `apiClient.js` was touched this phase, and no frontend authorization
  logic exists anywhere in the dashboard code.

### 35.4 Manual verification steps for AJ to run locally

Since pixel-level rendering could not be verified in this environment,
here is the exact procedure to confirm the dashboard visually:

1. `cd frontend && npm run dev`, then `cd backend && uvicorn
   app.main:app --reload` (or the project's usual startup command).
2. Log in as a USER or ADMIN in a department with some correspondence
   recorded (e.g. Finance), and navigate to `/app/dashboard`.
3. Confirm: two small headline numbers at the top; below them, four
   chart sections in order (Incoming vs. Outgoing, Received by
   Department, Sent by Department, Activity Over Time); Recent Letters
   and Quick Actions below that, unchanged from before.
4. Resize the browser to a phone width (~375px) and a tablet width
   (~800px) — confirm no horizontal scrollbar appears anywhere, and
   that department names in the bar charts wrap onto a second line
   rather than being cut off.
5. Open the trend chart's "View exact monthly counts" disclosure and
   confirm it expands/collapses via mouse and via keyboard (Tab to
   focus, Enter/Space to toggle).
6. Log in as SYSTEM_ADMIN and confirm the department charts show every
   department's data; log in as a USER in a different department and
   confirm the same charts show only that department's own rows.
7. Optional: temporarily disconnect the backend (stop `uvicorn`) and
   reload the dashboard — confirm each chart shows its own error
   message rather than a blank page.

### 35.5 Final regression results

Frontend: 411 tests (54 files, +2 from this phase's own regression
tests), run 3 consecutive times with identical results. A clean
production build (`rm -rf dist node_modules/.vite && npm run build`)
succeeded with the new axis-label code confirmed present in the
output. Backend: 525 tests, run once this phase (no backend code was
touched) — confirmed unaffected by this phase's live dev-database
verification activity, which used only real API calls and ordinary
archive/deactivate operations, never a schema or fixture change.

### 35.6 Project handover status

This closes the Phase 6D arc and, per this phase's own explicit
instruction, **the project's implementation work**. No further phase
is planned. Outstanding items are exactly the ones named as deferred
throughout Phases 6C/6D and never disguised as done: a Department ×
Direction cross-tabulation (needs a two-dimensional aggregate endpoint,
not built), a dashboard date-range control (no default/preset ever
confirmed wanted), an audit read API and its own analytics (Phase 5G
§20, still `FUTURE`), and a Designation edit/detail page. None of these
were treated as blockers for handover — each was evaluated in its own
phase and found to require either a business decision this project was
never given, or backend work explicitly out of a frontend-only phase's
scope. Nothing was committed or pushed this phase, per its own explicit
instruction — commit/push remains a separate, explicit action for AJ
to request.
