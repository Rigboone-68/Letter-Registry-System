# Backend Dashboard Aggregation & Analytics API — Architecture & Requirements Review (Phase 5G)

**Status: REVIEW ONLY. No backend or frontend code, migration, index, or
test was written this phase.** Builds on Phase 5F (Dashboard &
Operational Overview UI, implemented and committed at `1e5c8de`) —
unchanged by this review. Repository confirmed clean before this
review began.

## 0. How to read this document

Same taxonomy this project has used since Phase 4A, extended with two
values this phase's own brief specifically requested:

* **CONFIRMED** — verified directly against current backend source
  this session.
* **RECOMMENDED** — this document's own proposal, grounded in confirmed
  facts. Not implemented.
* **PROVISIONAL** — an explicit judgment call, flagged so it is
  revisited deliberately.
* **PENDING BUSINESS CLARIFICATION** — genuinely open, not guessed.
* **PENDING BACKEND API** — depends on a backend capability that does
  not yet exist (most often: the `AuditLog` read API itself).
* **NOT RECOMMENDED** — considered and rejected, with a reason.
* **FUTURE** — plausible eventually, explicitly not now, not designed
  in detail.

Every candidate metric (§6) is also classified per the brief's own
scheme:

* **A — EXISTING API ALREADY SUFFICIENT.**
* **B — BACKEND AGGREGATE API JUSTIFIED.**
* **C — POSSIBLE BUT NOT RECOMMENDED.**
* **D — REQUIRES BUSINESS CLARIFICATION.**
* **E — OUT OF SCOPE.**

## 0.1 Relationship to existing documents

`docs/architecture/dashboard.md` (Phase 5F) already did the frontend-
facing half of this analysis and reached conclusions this review
verifies and extends rather than re-deriving: every current-operational
metric is available today from an existing request; every historical/
trend metric would need a new backend endpoint; `Notification` is not a
good analytics data source; no charting library exists; the V1
dashboard is deliberately operational-only. `docs/architecture/
audit-notifications.md` §23 (Phase 4E) already recommended that a
future dashboard's *historical* metrics come from `AuditLog` once a
read API exists, and that current-state metrics come from the
operational tables via ordinary aggregate queries — a new backend
capability, not something either the frontend or the backend currently
has. This review is the concrete backend-side design neither prior
document went into: exact query construction, exact authorization
reuse, exact response shapes, and — critically — whether any of it is
actually justified yet.

---

## 1. Current dashboard capabilities (CONFIRMED, re-read fresh)

`frontend/src/pages/DashboardPage.jsx` (Phase 5F, unchanged by this
review) obtains, from four independent client-side fetch groups, every
figure it shows — all from **existing, non-aggregate** endpoints:

| Card/widget | Source | Mechanism |
|---|---|---|
| Total / Active / Archived Letters | `GET /letters` × 3 | `page_size: 1`, reads `.total` (a real SQL `COUNT`) |
| Unread Notifications | `GET /notifications/unread-count` | one-time fetch, reuses the same endpoint `NotificationBell` polls |
| Active Departments, Pending Admin Approvals (SYSTEM_ADMIN) | `GET /departments`, `GET /admins` | full-list fetch, `.total` computed client-visible as `len()` |
| Active Users, Pending User Approvals (ADMIN) | `GET /users` × 2 | same mechanism |
| Recent Letters | `GET /letters` | `sort_by=received_at&sort_order=desc&page_size=5` |
| Quick Actions | none (static links) | — |

No chart, trend, breakdown, or filter control exists anywhere in the
current dashboard (confirmed by reading `DashboardPage.jsx`,
`SummaryCard.jsx`, `RecentLetters.jsx`, `QuickActions.jsx` directly —
none references a `group_by`, date-range, or breakdown concept of any
kind). This phase evaluates **only** what would require new backend
work beyond this — it does not redesign anything above.

## 2. Current backend architecture (CONFIRMED, re-read fresh)

Layering is strict and consistent everywhere: `endpoint` (FastAPI
route, thin — request parsing, dependency injection, exception→HTTP
mapping) → `service` (business rules, orchestrates one or more
repositories, owns the transaction) → `repository` (the only layer that
builds SQLAlchemy statements) → PostgreSQL. Every one of the twelve
mounted routers (`app/api/v1/router.py`) follows this without
exception; a Phase 5G endpoint must follow it too — no query-building
code in an endpoint function, no business logic in a repository.

**Two reusable authorization primitives already exist and are directly
relevant** (`app/services/authorization.py`, both unchanged since
Phase 4B/4C):

* `assert_department_access(user, department_id)` — SYSTEM_ADMIN always
  allowed; ADMIN/USER only if `department_id` equals their own AND
  their own department is `ACTIVE`. Framework-agnostic (no FastAPI
  import), callable from any service.
* `letter_visibility_filter(user)` — the SQL-expressible half of the
  classified-access rule: returns `None` for SYSTEM_ADMIN/ADMIN (no
  restriction), a real SQLAlchemy boolean expression for USER only
  (visible if unclassified, classification doesn't restrict access, or
  the USER recorded it themselves). Already used by
  `app/repositories/letter_repository.py:list_letters` to build the
  exact same `WHERE` clause `COUNT` and pagination both share.

No caching infrastructure exists (`app/core/config.py` has no Redis/
cache setting of any kind) and none is proposed by this review (§19).

## 3. Database schema findings (CONFIRMED, re-read fresh)

| Table | Relevant indexed columns | Notes |
|---|---|---|
| `letters` | `recipient_department_id`, `source_department_id`, `category_id`, `classification_id`, `received_at`, `status`, `reference_number`, `subject`, `recorded_by` — **every one individually indexed**; plus a composite `ix_letters_recipient_department_received_at` | Every dimension a Letter aggregate could plausibly group or filter by is already indexed. No `archived_at`/status-transition timestamp exists — `updated_at` is bumped by *any* field edit, not specifically archival, so it cannot answer "when was this archived." |
| `departments` | `status` | |
| `users` | `role`, `department_id`, `status`, case-insensitive unique `email` | |
| `user_authorizations` | four indexed columns (status, department-derived fields via join) | |
| `letter_documents` | one index (foreign key), **`mime_type` is NOT indexed** | Relevant to §23 |
| `notifications` | composite `(recipient_user_id, is_read)` | No department column at all — recipient-scoped only |
| `audit_logs` | `user_id`, `entity_type`, `created_at`, composite `(entity_type, entity_id)` | No department column — see §5 |

**Finding**: because every dimension a plausible Letter aggregate would
group or filter by is already indexed, **no new index is required for
any Letter-based aggregate this review recommends** (§21/§28) — a
`GROUP BY` on an already-indexed column, combined with an
already-indexed `WHERE` predicate, is exactly the query shape
PostgreSQL's existing B-tree indexes already support well at this
project's expected data volume.

## 4. Letter API assessment — reuse potential (CONFIRMED)

`app/repositories/letter_repository.py:list_letters` builds one
`stmt = select(Letter)`, conditionally adds the `visibility_filter`
join/`WHERE`, conditionally adds every other filter
(department/status/category/classification/text-search/date-range),
then derives **both** `count_stmt` (via `select(func.count()).select_from(stmt.subquery())`)
**and** the paginated `items_stmt` from that *same* filtered statement.
This is exactly the reusable shape an aggregate query needs — the only
difference for a `GROUP BY` aggregate is replacing the final
`count_stmt`/`items_stmt`/`ORDER BY`/`LIMIT`/`OFFSET` step with a
`GROUP BY <dimension>` + `func.count()` step, built from the identical
filtered `stmt`. **RECOMMENDED**: extract the current filter-building
logic (department/status/category/classification/date-range/
visibility) into a small shared function both `list_letters` and any
future aggregate query call, rather than duplicating those `if`
statements a second time — a real, concrete refactor this review names
but does not perform. **Do not duplicate `letter_visibility_filter`
itself** — it is already framework-agnostic and reusable as-is (§10/§21
below).

## 5. AuditLog review (CONFIRMED, re-read fresh)

`AuditLog` is written to on every Letter/Document/Admin/Category/
Classification/Department/User lifecycle event (`app/services/
audit_service.py`, called from seven service modules), append-only,
same-transaction/mandatory (a write failure here fails the whole
operation). Columns: `user_id` (actor, nullable), `action`,
`entity_type`, `entity_id` (a bare UUID, no FK — `entity_type` names
which table it points into), `old_values`/`new_values` (JSONB, targeted
field pairs, never a full snapshot), `created_at`.

**No read API exists** — grepped every endpoint file and
`router.py` fresh this session; confirmed identical to Phase 4E's own
review and Phase 5F's own confirmation. Nothing has changed.

**A real design problem worth naming, not previously written down this
precisely**: `AuditLog` has **no department column of any kind** —
`entity_id` is heterogeneous (a `Letter` id one row, a `User` id the
next, a `Department` id the next), so there is no single, uniform way
to apply department-scoped or classified-access filtering to it the
way `letter_visibility_filter` does for `Letter` directly. Scoping an
audit-derived aggregate correctly would require a **different join
strategy per `entity_type`** (join to `letters` for Letter events, to
`users` for User events, etc.) — a materially more complex
authorization design than anything `letter_visibility_filter` already
solves, and one this review does not attempt to design, because no
audit read API exists yet to build the aggregate on top of in the first
place.

**RECOMMENDED**: audit analytics of any kind should be **FUTURE**,
contingent on (a) an audit read API being designed and built first (its
own, separate, undesigned phase — `PENDING BACKEND API`, unchanged from
every prior phase's own conclusion), and (b) that future phase
separately designing the per-entity-type department-scoping problem
above, which is materially different work from this review's own
Letter-focused design. **Audit analytics is explicitly not part of
5G's scope** — mixing operational Letter aggregation with audit-derived
analytics in one phase would conflate two different authorization
models (§25 of the brief's own instruction).

---

## 6. Metric inventory

### Letter metrics

| Metric | Class | Reasoning |
|---|---|---|
| Total / Active / Archived Letters | **A** | Already implemented (Phase 5F), three cheap `COUNT` requests |
| Letters received by day/week/month (trend) | **D** → **B** if confirmed | No confirmed business requirement that a trend is wanted at all (§27); if confirmed, cheaply built via `GROUP BY DATE_TRUNC('day'/'week'/'month', received_at)` on an already-indexed column |
| Letters by category | **D** → **B** if confirmed | Only 3 categories exist today (seeded, Phase 4B) — cheap either way; the open question is whether the *breakdown itself* has confirmed value, not query cost |
| Letters by classification | **D** → **B** if confirmed | Same reasoning |
| Letters by department (SYSTEM_ADMIN only) | **D** → **B** if confirmed | Meaningless for ADMIN/USER (exactly one department each); cheap via the already-indexed `recipient_department_id` |
| Letters by source department | **E** | `source_department_id` carries **no authorization meaning** (`assert_letter_access`'s own docstring — an external sender has no LRS account); no phase has ever proposed this has operational value; risks confusion with the authorization-relevant `recipient_department_id` |
| Letters by sender department | **E** | `sender_department` is free text, not a normalized FK — `GROUP BY` on free text is fragile (case/whitespace variance) and no confirmed value exists |
| Letters by status | **A** | Already two cheap calls (Phase 5F); a single `group_by=status` call would save one round trip but isn't solving a real performance problem at current scale (§11 below) |
| Letters by date range (a single range's total) | **A** | `received_from`/`received_to` already exist on `GET /letters`; already used by nothing today, but available |

### Administration metrics

| Metric | Class | Reasoning |
|---|---|---|
| Active/Inactive Departments | **A** | `GET /departments?status=` already returns this (as a full-object list, Phase 5D/5F) |
| Active/Inactive Admins | **A** | `GET /admins?status=` — same mechanism |
| Active/Inactive Users | **A** | `GET /users?status=` — same mechanism |
| Pending User/Admin Approvals | **A** | Already implemented (Phase 5F) |
| Authorization counts (Active/Used/Revoked) | **A** | `GET /users/authorizations?status=` — same mechanism |

Every administration metric is **A** — a dedicated `COUNT`-only
endpoint would reduce per-request payload size (avoiding a full-object
fetch just to read a count) but no phase has found this to be an actual
performance problem at current data volumes, and Phase 5D's own review
already flagged the underlying "does this need pagination/a lighter
path at real V1 volumes" question as `PENDING BUSINESS CLARIFICATION`
— unchanged by this review. **NOT RECOMMENDED to build a dedicated
administration-aggregate endpoint for 5G** — tie any future work here
to that same still-open pagination question rather than solving it in
isolation for the dashboard's benefit alone.

### Document metrics

| Metric | Class | Reasoning |
|---|---|---|
| Documents per Letter | **A**, contextual only | Already directly available (`GET /letters/{id}/documents`, `len(items)`) exactly where it's meaningful — inside a Letter's own detail page; not a dashboard-level concept |
| Total documents (system/department-wide) | **E** | No cross-Letter document list endpoint exists; would need either N+1 (one request per Letter — explicitly the anti-pattern the Phase 5F review already rejected) or a new aggregate; **no confirmed business value has ever been named** for this number |
| Documents by extension/type | **E** | `mime_type` is **not indexed** (§3); would need a new index with no confirmed query pattern to justify it; no confirmed business value |

### Notification metrics

| Metric | Class | Reasoning |
|---|---|---|
| Unread count | **A** | Already implemented |
| Read/unread distribution (system-wide) | **C** | Notifications are recipient-scoped by design (no department column at all, §3); a system-wide distribution would either aggregate across every user's private notifications (no confirmed administrative purpose) or be per-user (already fully available via the existing list + `is_read` field, no aggregate needed) |
| Notifications over time | **E** | Restates `audit-notifications.md` §23's own explicit conclusion: `Notification` is deliberately disposable, "never designed to be a system of record for anything" — not a good analytics source regardless of how the query would be built |

### Audit metrics

| Metric | Class | Reasoning |
|---|---|---|
| Actions over time, Letters created/updated/archived, classification/category changes, admin actions | **E**, all — `PENDING BACKEND API` (the audit read API itself), then **FUTURE** | See §5 in full — no read API exists, and the per-entity-type department-scoping problem is undesigned. Explicitly out of 5G's scope per the brief's own §25 instruction. |

---

## 7. Current vs. historical metrics

**Current operational** (available from the operational tables' *present
state*, no time dimension): every Letter/Department/Admin/User/
Notification count in §6 classified A. All already implemented.

**Historical/analytical** (require either a time dimension over
existing tables, or `AuditLog`): Letter trends by day/week/month,
Letter breakdowns by category/classification/department (these are
"current-state breakdowns," not time-series, but share the same "not
yet confirmed as wanted" status as trends), and every audit-derived
metric. The Letter-table-derived historical metrics (trends,
breakdowns) are **technically cheap** — no `AuditLog` needed, since
`Letter.received_at`/`category_id`/`classification_id`/
`recipient_department_id` are all present-tense, current-state columns
on the operational table itself, just grouped differently. **Do not
conflate "requires a `GROUP BY`" with "requires `AuditLog`"** — only
metrics about *change over time to a specific record* (letters
archived on a given day, a classification changed from X to Y) require
`AuditLog`; metrics about the *current distribution* of an
already-queryable column do not, regardless of whether they're framed
as "historical."

---

## 8. Department isolation (CRITICAL)

Every aggregate this review's design (§12-§16) proposes reuses
`letter_service.py`'s own existing derivation, unchanged:
`recipient_department_id = department_id if user.role == SYSTEM_ADMIN
else user.department_id` — a SYSTEM_ADMIN caller may optionally filter
to one department or see all; an ADMIN/USER caller's own department is
always substituted server-side, with no request parameter capable of
overriding it (the exact mechanism `GET /letters` already enforces,
confirmed unchanged in `app/services/letter_service.py:list_letters`
and `app/api/v1/endpoints/letters.py:list_letters`). **No new
department-isolation mechanism is proposed or needed** — this is a
direct reuse, not a new design.

An inactive department does not change this: `assert_department_access`
already rejects an ADMIN/USER whose own department has gone `INACTIVE`
(a `403`, unrelated to the aggregate's own logic) before any aggregate
query would even run, via the same dependency chain every other
Letter-scoped endpoint already goes through.

## 9. Classified-record security (CRITICAL)

For a USER caller, every proposed aggregate **must** apply
`letter_visibility_filter(user)` as a `WHERE` predicate on the exact
same query that computes the aggregate — never fetch an unfiltered row
set and discard/re-count in Python (the identical discipline
`docs/architecture/registry-search.md` §8 already established for
pagination, restated here for aggregation). Applied this way, a
classified-and-inaccessible-to-this-USER Letter is excluded from every
bucket, every total, and every trend point identically to how it is
already excluded from `GET /letters`'s own `total` today — **there is
nothing new to invent**; the same predicate, applied the same way, at
the same point in query construction, produces a correctly-narrowed
aggregate automatically. ADMIN and SYSTEM_ADMIN are unaffected — the
predicate is `None` for both, matching current, confirmed behavior
exactly. **No new classification matrix is proposed** — this review
preserves the current, provisional policy (see
`docs/architecture/letter-registry.md` §12 — the exact classification
value list and classified-visibility matrix remain
`PENDING BUSINESS CLARIFICATION`, unchanged by this review) as-is.

---

## 10. Query-level authorization reuse (CRITICAL ARCHITECTURAL QUESTION — direct answer)

**Yes, both `letter_visibility_filter()` and the department-derivation
logic can and must be reused directly, unmodified, for any Letter
aggregate.** No aggregate-specific authorization predicate is needed or
proposed — the existing predicate was already designed to be
SQL-expressible and join-composable specifically so it could be reused
in exactly this kind of query, not only in `list_letters` (confirmed by
re-reading its own docstring, §2 above, unchanged since Phase 4C).
`assert_department_access`/`assert_letter_access` (the single-resource,
Python-side checks) are **not** what an aggregate query would call —
those remain for single-row authorization (`GET /letters/{id}` and
similar); the aggregate path reuses `letter_visibility_filter` exactly
as `list_letters` already does, for the same reason: a `GROUP BY`/
`COUNT` needs a `WHERE`-clause-shaped predicate, not a raise-or-return
check against an already-loaded row. **There is exactly one
authoritative authorization expression for Letter visibility in this
system, and this review's design adds no second one.**

---

## 11. Aggregate query design

**RECOMMENDED approach**: one SQLAlchemy statement per request, built
by extending the same filter-construction pattern `list_letters` already
uses (§4), replacing pagination with `GROUP BY <dimension>` and
`func.count()`. For PostgreSQL-specific grouping needs:

* **Category/classification/department breakdown**: `GROUP BY
  Letter.category_id` (etc.), `func.count()` per group — a plain
  `GROUP BY` on an already-indexed column.
* **Day/week/month trend**: `func.date_trunc('day'|'week'|'month',
  Letter.received_at)`, `GROUP BY` on that expression — PostgreSQL's
  native, efficient bucketing function; no application-side date-math
  needed.
* **Multiple simultaneous counts in one round trip** (e.g. the
  existing Active/Archived split, currently two separate requests) —
  PostgreSQL's `FILTER` clause via SQLAlchemy's
  `func.count().filter(Letter.status == 'ACTIVE')` computes several
  conditional counts in a single query and a single round trip, without
  a `GROUP BY` or multiple statements at all. This is the one
  candidate this review found that improves on something already
  shipped (Phase 5F's 3-request Letters summary) without requiring any
  *new* business confirmation — see §28.

**Explicitly avoided, per the brief's own instruction and this
project's own established discipline**: no row is ever loaded into
Python and aggregated there; no Pandas; no N+1 (one query per bucket)
— every breakdown is one `GROUP BY` query, not one query per group
value; no browser-side aggregation (unchanged from Phase 5F's own
conclusion). **One query can safely serve one metric-family per
request** (e.g., one call answers "letters by category," a separate
call answers "letters by month") — this review does not recommend
trying to cram every possible breakdown into a single mega-query, since
that would produce a large, awkward response shape for whichever
dimension the caller didn't actually want (§13/§14).

---

## 12. Endpoint design

Comparing the brief's own three options directly:

* **Option A, `GET /api/v1/dashboard/summary`**: rejected. A
  `/dashboard` namespace is page-shaped, not resource-shaped — it would
  be the first router in this entire codebase organized around a
  frontend screen rather than a backend resource (confirmed by reading
  `router.py`: every one of the twelve existing routers is a business
  resource — `letters`, `departments`, `admins`, etc., never a UI
  concept). This violates the project's own established layering
  convention (§2) and §26's explicit "keep naming consistent with
  letters/departments/users/admins/notifications" instruction.
* **Option B, `GET /api/v1/dashboard/analytics`**: rejected for the
  same reason, and additionally implies a broader analytics surface
  (multi-resource) than anything this review actually found justified
  — only Letters have a genuinely B-classified aggregate candidate
  (§6); Departments/Admins/Users/Documents/Notifications do not.
* **Option C, multiple focused endpoints**: **RECOMMENDED, narrowed
  further than "multiple"** — exactly **one** new endpoint,
  Letter-scoped, nested under the existing `/letters` resource, the
  same way `/letters/{id}/documents` already nests Documents under
  Letters rather than inventing a top-level `/documents` resource
  (Phase 4D's own precedent, still followed).

**RECOMMENDED, if and when built**: `GET /api/v1/letters/aggregate` —
one endpoint, a `group_by` query parameter selects the dimension
(`status` | `category` | `classification` | `department` | `day` |
`week` | `month`), reusing every other `GET /letters` filter
(department_id — SYSTEM_ADMIN only, status, category_id,
classification_id, received_from/received_to) as an optional narrowing
predicate on top of the grouping itself. One endpoint, one query per
request, no per-dimension endpoint proliferation — satisfying "avoid
over-engineering" directly. This is a **design**, not an authorization
to build it — see §28.

---

## 13. Response design

```
GET /api/v1/letters/aggregate?group_by=category

{
  "group_by": "category",
  "total": 41,
  "buckets": [
    { "key": "3f2b...-category-uuid", "count": 27 },
    { "key": "9a1c...-category-uuid", "count": 10 },
    { "key": null, "count": 4 }
  ]
}
```

| Field | Meaning | Source | Nullable | Ordering |
|---|---|---|---|---|
| `group_by` | Echoes the effective grouping dimension | request parameter | No | — |
| `total` | Sum of every bucket's `count` — the same figure `GET /letters`'s own `total` would return for the identical filter set, restated for convenience | `SELECT COUNT(*)` on the same filtered statement, or `SUM(bucket counts)` | No | — |
| `buckets[].key` | The raw grouping value — a `category_id`/`classification_id`/`department_id` (UUID), a `status` string, or an ISO date-bucket string (`day`/`week`/`month`) | the `GROUP BY` expression's own value | **Yes**, when `group_by` is `category`/`classification` and the Letter has no category/classification assigned (both remain nullable FKs, §3) | Descending by `count`, ties broken by `key` ascending — deterministic, matching `list_letters`'s own "always add a deterministic secondary sort" discipline |
| `buckets[].count` | Rows in this bucket, already department/classified-visibility-scoped | `func.count()` | No | — |

**Never returns a full `Letter`/`Department`/`Admin`/`User` object** —
`key` is a bare id or label, exactly the brief's own §14 instruction.
**No resolved name is included** for `category`/`classification`/
`department` keys — resolving a `category_id` to a display name is
already the frontend's own job today (`LetterListPage`'s existing
reference-data pattern, SYSTEM_ADMIN-only, Phase 5C) and this endpoint
does not duplicate that lookup.

---

## 14. Date range strategy

`received_at` — **RECOMMENDED**, not `created_at`. `received_at` is
the operationally meaningful timestamp throughout this system already
(it is what `GET /letters`'s own `received_from`/`received_to` filters
use today, what the existing composite index
`ix_letters_recipient_department_received_at` is built on, and what
Phase 5F's Recent Letters widget sorts by) — `created_at` reflects when
the *database row* was inserted, which can differ from when the letter
was actually received (e.g. backlogged data entry) and has never been
used as the business-meaningful date anywhere in this project.
Reusing `received_at` is a direct continuation of existing behavior,
not a new decision.

* **Default range**: `PENDING BUSINESS CLARIFICATION` — no confirmed
  default exists anywhere in this project's history (restating
  `dashboard.md` §27's own open question); `RECOMMENDED` if forced to
  pick one today: no default range at all (return every matching row,
  identical to how `GET /letters` behaves with no date filter supplied)
  rather than silently guessing "this month" or "this year."
* **Maximum range**: **RECOMMENDED**: none imposed — the existing
  `GET /letters` endpoint imposes no maximum range either, and a
  `GROUP BY` aggregate over an indexed date column does not become
  unsafe at any range this project's expected data volume would ever
  produce (§18).
* **Boundary behavior**: **RECOMMENDED**: inclusive on both ends,
  matching `GET /letters`'s own confirmed `received_from >=` / `
  received_to <=` behavior exactly — no new convention.
* **Invalid ranges** (`received_from` after `received_to`):
  **RECOMMENDED**: reuse the existing `InvalidDateRangeError` → `422`
  exactly, not a new validation path.
* **Future dates**: **CONFIRMED, unchanged**: no restriction exists
  anywhere in this system today (`LetterCreate`/`LetterUpdate` have no
  future-date validator); an aggregate endpoint should not invent one
  either — a future-dated Letter (if one exists) is counted exactly
  like any other.
* **Timezone**: **CONFIRMED, unchanged**: `received_at` is
  `DateTime(timezone=True)` (§3); `date_trunc` bucketing is
  PostgreSQL-timezone-aware using the session's configured timezone —
  this project has never confirmed an organizational timezone
  requirement beyond what the database session already uses, and this
  review does not introduce one.

---

## 15. Filter strategy

| Filter | Useful? | Who | Security note | Index needed? |
|---|---|---|---|---|
| `status` | Yes | all | Already public-facing on `GET /letters`; no risk | Already indexed |
| `category_id` | Yes | all | Same | Already indexed |
| `classification_id` | Yes | all | Same — filtering by a specific classification never reveals *which* records are classified beyond what the caller could already see via `GET /letters?classification_id=` today | Already indexed |
| `department_id` | Yes, **SYSTEM_ADMIN only** | SYSTEM_ADMIN | **Must never let ADMIN/USER expand scope** — reuse the exact `list_letters` behavior: silently ignored (not rejected) for ADMIN/USER, since their own department is always substituted server-side regardless of what's supplied | Already indexed |
| `received_from`/`received_to` | Yes | all | No risk beyond what date-range filtering on `GET /letters` already exposes | Already indexed |
| `source_department_id` | **No** | — | Carries no authorization meaning (§6); exposing it as an aggregate filter invites confusion with `department_id`'s actual isolation role | N/A — not proposed |
| `sender_department` (free text) | **No** | — | Free-text `GROUP BY`/filter on an unnormalized field; no confirmed value | N/A — not proposed |

**Not every database field becomes a filter** — only the ones already
exposed by `GET /letters` today are reused; nothing new is invented.

---

## 16. Role-specific API access

Reuses the existing `get_current_user` dependency only — **no new
dependency function is proposed**. Role-based *scope* (not endpoint
access) is derived inside the service layer exactly as `list_letters`
already does: SYSTEM_ADMIN unrestricted (optionally department-
filtered), ADMIN/USER server-derived to their own department, USER
additionally narrowed by `letter_visibility_filter`. **All three roles
can call the same endpoint** — there is no role this endpoint should be
closed to, since every role that can call `GET /letters` today would
get a correctly-scoped, non-empty answer from its aggregate equivalent
too (a USER's own aggregate is simply narrower, not forbidden). This
mirrors `GET /letters`'s own `get_current_user`-only dependency
exactly — **do not gate this endpoint behind `require_admin`/
`require_system_admin`**, which would incorrectly exclude USER from an
aggregate over data they can already list individually.

---

## 17. Administration aggregates — assessed, not recommended for 5G

See §6's own table. Every Department/Admin/User count is already class
**A** — `NOT RECOMMENDED` to add a dedicated `COUNT`-only endpoint for
5G specifically to serve the dashboard; tie any future work here to
Phase 5D's still-open pagination question (`docs/architecture/
administration-ui.md` §11/§22) instead of solving it in isolation.

## 18. Document aggregates — assessed, not recommended

See §6. **NOT RECOMMENDED** — no confirmed business value for any
cross-Letter document statistic, and `mime_type` (the one column a
"document type breakdown" would need) isn't indexed, meaning even a
cheap-sounding breakdown would require a new index with no query
pattern to justify it yet (§21).

## 19. Notification aggregates — assessed, not recommended

See §6. Unread count (already implemented) remains the only justified
notification figure. **NOT RECOMMENDED** to expose any system-wide
notification statistic to ADMIN/USER — `Notification` has no department
column at all, so a "department's unread count" concept does not even
exist structurally, and a truly system-wide count has no confirmed
administrative purpose. A per-user breakdown needs no aggregate — the
existing list endpoint already carries `is_read` per row.

## 20. Audit analytics — deferred entirely

See §5 in full. **FUTURE**, contingent on the audit read API itself
being designed first (a separate, undesigned phase), and on that future
phase separately solving `AuditLog`'s per-entity-type department-
scoping problem. **Not part of 5G.**

---

## 21. Performance

At this project's expected data volume (an internal departmental
correspondence registry, not a high-throughput consumer system — the
same scale assumption every prior phase's own performance review has
made), a `GROUP BY` on an already-indexed column with an already-
indexed `WHERE` predicate is inexpensive — PostgreSQL can satisfy this
class of query via an index scan plus an in-memory hash/sort
aggregate, the same query shape `list_letters`'s own `COUNT` already
executes today for every page load. **No index is speculative here**
— every column this review's design would `GROUP BY` or filter on is
already indexed (§3); this review recommends **zero new indexes**
(§28). Repeated dashboard refreshes and concurrent users are bounded
by the same connection-pool/query-cost profile every other endpoint in
this system already operates under — nothing about an aggregate query
changes that profile qualitatively, since it is still one indexed
query per request, not a table scan.

**No materialized view is justified** — the brief's own instruction to
require "a demonstrated query justification" applies doubly to a
materialized view, which adds real operational complexity (refresh
scheduling, staleness). Nothing in this review's findings demonstrates
current `GROUP BY` performance is inadequate; a materialized view
would be solving a problem that has not been observed.

## 22. Caching

**RECOMMENDED for V1, if any of this is ever built: no caching layer of
any kind** — no Redis, no application-level cache, no materialized
view. The brief's own instruction ("assume no additional infrastructure
unless evidence proves it necessary") is directly supported here: §21
found no performance problem to solve, so there is nothing for a cache
to fix. Revisit only if a future phase's own real measurement (not a
speculative one) shows otherwise.

---

## 23. Security threat review

| # | Threat | Backend mitigation | Remaining risk |
|---|---|---|---|
| 1 | Cross-department aggregate leakage | Identical department-derivation `list_letters` already uses (§8) — ADMIN/USER can never supply a `department_id` that overrides their own | None found, provided the design in §8/§16 is followed exactly |
| 2 | Classified-record count leakage | `letter_visibility_filter` applied at the query level for USER (§9) — a classified-inaccessible record is excluded from every bucket the same way it's excluded from `GET /letters`'s own `total` today | None found |
| 3 | Role escalation | No new role-gating dependency is introduced (§16); the endpoint is `get_current_user`-only, matching `GET /letters` exactly — no path by which a lower role reaches a higher role's scope | None found |
| 4 | IDOR via `department_id` | Same mechanism as #1 — the parameter is silently ignored (not trusted) for ADMIN/USER | None found |
| 5 | Hidden resource inference | A classified-inaccessible Letter is excluded from bucket counts identically to how it's excluded from list `total` today — no new inference surface beyond what already exists in `GET /letters` | None found |
| 6 | Over-broad aggregate queries | No filter is required — an unfiltered `group_by=status` call is exactly as expensive as the two existing `GET /letters?status=` calls Phase 5F already makes, not a new cost category | Low — bounded by §21's own analysis |
| 7 | Date-range abuse | No maximum range imposed (§14), matching `GET /letters`'s own existing behavior; an indexed `date_trunc` aggregate over an unusually large range is still one indexed scan, not a runaway cost | Low |
| 8 | Expensive query abuse | One `GROUP BY` per request, on indexed columns only, no N+1, no unbounded joins (§11) | Low, same profile as every other list endpoint in this system |
| 9 | Sensitive user/admin statistics | No administration aggregate is recommended for 5G (§17) — nothing new to assess here | N/A this phase |
| 10 | `AuditLog` leakage | No audit aggregate is proposed (§20) — nothing new to assess here | N/A this phase |
| 11 | Notification statistics leakage | No system-wide notification aggregate is recommended (§19); unread-count remains per-recipient, unchanged | None found |
| 12 | Document statistics leakage | No document aggregate is recommended (§18) | N/A this phase |

---

## 24. Test plan (design only, not implemented)

If and when this endpoint is built, at minimum: SYSTEM_ADMIN receives
a system-wide (or department-filtered) aggregate; ADMIN's aggregate
never includes another department's rows even if `department_id` is
supplied; USER's aggregate additionally excludes classified-
inaccessible rows, verified by comparing against a fixture containing
both accessible and inaccessible classified Letters; a cross-department
`department_id` supplied by ADMIN/USER is silently ignored, not
honored (a dedicated regression test, mirroring the exact assertion
style Phase 5F's own `DashboardPage.test.jsx` already used for
"never sends a department id"); each `group_by` dimension (status,
category, classification, department, day, week, month) produces
correctly-bucketed counts against a known fixture; an empty result set
returns `{"total": 0, "buckets": []}`, not an error; an invalid date
range returns the existing `422`; **a security-specific regression
proving a narrower (USER-scoped) total can never be used to infer a
broader (department-wide or system-wide) count** — e.g. assert a USER's
`total` for `group_by=status` never exceeds what that USER's own
`GET /letters` would return for the same filters, across a fixture
with intentionally-hidden classified rows; a query-count assertion
(mocking/inspecting the SQLAlchemy session) proving exactly one query
executes per request, never N+1, and that no `Letter` row is
individually loaded into Python for aggregation. Pagination is
correctly **not** applicable to this response shape — no test should
assert a `page`/`page_size` parameter exists on it.

## 25. Migration / index review

**No migration or index is recommended for 5G.** Every column this
review's design would `GROUP BY` or filter on is already indexed (§3/
§21) — `recipient_department_id`, `category_id`, `classification_id`,
`received_at`, `status` are all individually indexed today, and the
existing composite `ix_letters_recipient_department_received_at`
already supports the single most likely real query shape ("this
department's letters, over time"). **If document-type breakdown is
ever separately confirmed as wanted** (§18, currently `E`), a new index
on `letter_documents.mime_type` would need its own justification at
that time — not proposed here, since no query pattern exists to justify
it yet. No historical migration is modified or proposed to be modified.

---

## 26. API versioning / naming

`GET /api/v1/letters/aggregate` — stays under the existing
`/api/v1` prefix (`app/core/config.py:API_V1_PREFIX`, unchanged), no
new API version. Nested under `/letters`, matching the existing
resource-oriented convention (`/letters/{id}/documents`) rather than
introducing a page-shaped `/dashboard` or a separate `/analytics`
namespace (§12).

---

## 27. Business clarifications (genuinely open, not manufactured)

* Is analytics actually required for V1, or is the operational-only
  Phase 5F dashboard sufficient indefinitely? Not confirmed anywhere.
* Which trend, if any, actually matters — daily, weekly, or monthly
  Letter volume? Not confirmed.
* What default date range should any trend/breakdown use? Not
  confirmed (§14).
* Should ADMIN see category/classification breakdowns for their own
  department, or is that a SYSTEM_ADMIN-only concern? Not confirmed.
* Should USER see any aggregate count beyond what `GET /letters`
  already answers? Not confirmed — arguably redundant with existing
  list/search.
* Should SYSTEM_ADMIN see system-wide statistics by default, or
  per-department on request? Not confirmed.
* Should source department or sender department ever be included in an
  aggregate, despite this review's own `E` classification? Would need
  an explicit, deliberate business reason to override §6's finding.
* Should document metrics exist at all? Not confirmed; no value has
  ever been named.
* Should notification metrics exist beyond unread count? Not
  confirmed; `audit-notifications.md` §23 already leans no.
* Should audit analytics exist, and if so, in this phase or a later,
  separate one? This review recommends a later, separate one (§20),
  but the underlying want is not confirmed.
* Are exports required later? Not confirmed, and out of scope
  regardless (§33 of the brief).
* What refresh frequency would any analytics widget need? Not
  confirmed — moot until a widget itself is confirmed wanted.

---

## 28. V1 recommendation

The brief's own principle: *"Do not build an analytics API unless the
metric provides meaningful operational or management value that cannot
be obtained efficiently from existing APIs."* **This review finds the
principle fully supported by the evidence gathered**: of every metric
in the inventory (§6), the only ones classified `A` (already
sufficient) are the ones Phase 5F already shipped; every metric that
would need a *new* endpoint is gated behind an unconfirmed business
want (`D`) or explicitly `E`/deferred. **No metric in this review
clears the bar of "confirmed value that existing APIs cannot already
provide."**

**RECOMMENDED**: defer backend aggregation entirely for now — build
nothing this phase or the next, until at least one specific breakdown
or trend is confirmed wanted by the business. The one narrow exception
worth naming, **not urgent, not blocking**: consolidating the existing
Active/Archived Letters split (currently two requests, already shipped
and already confirmed valuable) into one `FILTER`-based query (§11)
is the single lowest-risk candidate if any 5G backend work is ever
prioritized at all — it requires no new business confirmation, since
the metric itself is already approved; only its request-count
efficiency would change. Even this is explicitly **not** implemented
or authorized by this review — named only as the most-ready candidate
if the team chooses to
proceed with any 5G work.

This directly supports "operational visibility over analytics" (Phase
5F §31's own principle, restated and now doubly confirmed from the
backend side): the current dashboard already delivers everything the
evidence supports building, and nothing found this phase changes that
conclusion.

---

## 29. Implementation sequence (RECOMMENDED, contingent on §27, not started)

1. **5G.1 — Business/API contract confirmation.** Resolve at least one
   of §27's open questions — in particular, whether *any* trend/
   breakdown is actually wanted — before writing backend code. Without
   this, there is nothing to build.
2. **5G.2 — Aggregate authorization design.** Already done by this
   review (§8-§10) — reuse `letter_visibility_filter`/department
   derivation exactly as designed; no further design work needed at
   this step.
3. **5G.3 — Query/repository implementation.** Extract the shared
   filter-building logic from `list_letters` (§4); add the `GROUP BY`/
   `date_trunc` aggregate method to `LetterRepository`.
4. **5G.4 — Service/API layer.** `LetterService`/`app/api/v1/
   endpoints/letters.py` — `GET /letters/aggregate`, per §12/§13.
5. **5G.5 — Security/performance tests.** Per §24, before frontend
   integration, matching every prior phase's own established practice.
6. **5G.6 — Frontend integration.** Only after 5G.1-5G.5 — a new
   Dashboard widget consuming the new endpoint, its own small,
   reviewed slice of frontend work, not bundled into this backend
   phase.
7. **5G.7 — Manual verification.** Against a real running backend —
   not part of this review.
8. **5G.8 — Commit/push checkpoint.**

---

## 30. Documentation (this phase's own footprint)

Created: `docs/architecture/dashboard-analytics-api.md` (this file).
Updated: `README.md`, `docs/README.md`, `docs/PROJECT_STATUS.md`,
`docs/architecture/dashboard.md`, `docs/architecture/overview.md` —
all recording that this review exists and what it found, matching the
exact documentation-only footprint every prior review-only phase has
left.

## 31. Explicit scope confirmation

This phase produced documentation only. It did **not** produce or
modify: any file under `backend/app/` or `backend/alembic/`, any file
under `frontend/src/`, any test file, any migration, any index, any
database change, any configuration change, any package dependency
change. It did not implement a dashboard API, an aggregate repository
method, an aggregate service method, a new endpoint, an `AuditLog` API,
an audit dashboard, an analytics UI, a chart, a reporting table, a
materialized view, Redis, caching infrastructure, background workers,
exports, or scheduled reports. `git status` before and after this
session is identical except for this new documentation file and the
five project documentation updates listed in §30. Phase 5G
implementation begins only when explicitly instructed and only after
at least one of §27's open business questions is resolved.
