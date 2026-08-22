# Registry Operations & Search — Architecture (Phase 4C, implemented)

**Status: implemented.** `GET /api/v1/letters` now supports pagination,
explicit whitelisted sorting, per-field search/filters, and inclusive
date-range filtering — on top of the department-isolation and classified-
access boundary Phase 4B established. The central finding from this
phase's earlier architecture review (a query-level authorization gap that
would have leaked classified-record counts through pagination) was fixed
**first**, before any new feature was added, exactly as planned.

## 0. How to read this document

* **IMPLEMENTED** — built, tested (automated + live `lrs_dev`
  verification), and described exactly as the code behaves.
* **PENDING BUSINESS CLARIFICATION** — genuinely open; not guessed into
  a constraint or a policy.
* **FUTURE** — a reasonable next step, deliberately not built this
  phase.

## 1. The fix that had to come first

**IMPLEMENTED.** Before pagination existed, `LetterService.list_letters`
fetched every department-scoped row and discarded the classified ones a
`USER` couldn't see *after* the fact, in Python. That is a genuine
count/pagination-leakage risk once `LIMIT`/`OFFSET`/`total` exist — a
non-recording `USER` could otherwise learn "there are more letters here
than I can see" purely from a paginated total.

The fix: `app/services/authorization.py:letter_visibility_filter(user)`
returns a SQLAlchemy boolean expression (the classified-access half of
`assert_letter_access`'s policy, re-expressed for a *query*, not an
already-loaded row) — `None` for `SYSTEM_ADMIN`/`ADMIN` (no restriction),
or `Letter.classification_id IS NULL OR Classification.restricts_access
= false OR Letter.recorded_by = :user_id` for `USER`.
`LetterRepository.list_letters` builds **one** `stmt` with every `WHERE`
clause (department, status, category, classification, text search, date
range, and — when non-`None` — the visibility filter) applied, then
derives *both* the `COUNT` query and the paginated `items` query from
that same `stmt` (`count_stmt = select(func.count()).select_from(stmt.subquery())`).
There is no second, independently-built query for the count that could
disagree with the items query about which rows are visible — verified
directly, not just by code inspection: see §7's regression tests and the
live `lrs_dev` check recorded in `docs/PROJECT_STATUS.md`.

`can_view_letter` (the old Python-side helper) still exists, for a
single already-loaded `Letter` (used nowhere in list/search code
anymore) — its docstring now explicitly says it must never be used for a
query result set.

## 2. Existing department isolation — unchanged

**IMPLEMENTED, unchanged from Phase 4B.** `department_id` remains
SYSTEM_ADMIN-only; a `USER`/`ADMIN`-supplied value is silently ignored,
never rejected, and never expands their own-department scope. No code
changed here — `app/services/letter_service.py:list_letters` computes
`recipient_department_id` from `user.department_id` for non-SYSTEM_ADMIN
callers exactly as it did before pagination/search existed.

## 3. Pagination

**IMPLEMENTED**: `page` (default `1`, minimum `1`) and `page_size`
(default `25`, minimum `1`, maximum `100`) — both validated by FastAPI
`Query(ge=..., le=...)` before the request ever reaches the service, so
an out-of-range value is a clean `422`, not a clamped or silently
corrected one. Response shape extends, not replaces, the original
`{"items": [...], "total": N}` envelope:

```json
{
  "items": [...],
  "total": 137,
  "page": 1,
  "page_size": 25,
  "total_pages": 6
}
```

`total`/`total_pages` are computed from the exact same authorized query
as `items` (§1) — an inaccessible letter cannot inflate either, at any
page. `total_pages = ceil(total / page_size)`, `0` when `total == 0`.

**Note on `items`' shape**: `items` now contains the lightweight
`LetterListItem` (§9), not the full `LetterResponse` — an intentional,
explicitly-instructed change (not an accidental break of the `items`/
`total` key names, which are unchanged).

## 4. Sorting

**IMPLEMENTED**: `sort_by` (`LetterSortField` enum — `received_at`,
`created_at`, `reference_number`, `subject`) and `sort_order`
(`SortOrder` enum — `asc`, `desc`), default `received_at`/`desc`. Both
are FastAPI-validated enums — a client value outside the whitelist is a
`422` before the endpoint function body ever runs; no raw client string
is ever used to build `ORDER BY`.
`app/repositories/letter_repository.py:SORTABLE_COLUMNS` is the single
mapping from the whitelisted key to an actual SQLAlchemy column (kept in
sync by hand with the `LetterSortField` enum — four fields, not expected
to change often enough to justify a shared source of truth between a
Pydantic enum and a repository dict).

**Stable pagination**: every query appends a deterministic secondary
sort by `Letter.id` after the requested column, so two letters with an
identical `received_at`/`subject`/etc. still produce a consistent order
across repeated requests — proven directly by
`test_stable_ordering_via_secondary_sort_key`
(`tests/integration/test_letter_search.py`), which issues the same query
twice and asserts identical item order, not just identical membership.

## 5. Search / filter parameters

**IMPLEMENTED — exact match** (unchanged from Phase 4B, extended with
three new filters): `category_id`, `classification_id`, `status`,
`department_id` (§2).

**IMPLEMENTED — case-insensitive contains** (`ILIKE '%term%'`, new this
phase): `reference_number`, `subject`, `sender_name`,
`sender_designation`, `sender_department`, `source_name`,
`source_location`. Search terms are escaped
(`app/repositories/letter_repository.py:_ilike_escape`) so a literal `%`
or `_` in a search term (e.g. a reference number fragment like
"50%-approved") matches literally rather than acting as a SQL wildcard.

**IMPLEMENTED — date range**: `received_from`/`received_to` against
`Letter.received_at`, both boundaries inclusive
(`received_at >= received_from AND received_at <= received_to`).
`recorded_from`/`recorded_to` against `created_at` were **not**
implemented — no confirmed requirement asks for it (unchanged assessment
from the architecture review). A `received_from` after `received_to` is
rejected with `422` (`InvalidDateRangeError`, raised in
`LetterService.list_letters`, translated to HTTP in the endpoint).

**IMPLEMENTED — multi-filter combination**: every supplied filter is
`AND`-combined (each additional filter narrows, never broadens, the
result). No OR-search exists or was requested.

**Reference number is not unique** (unchanged Phase 4B hardening
finding) — a `reference_number` search can and does match more than one
`Letter`; nothing in this phase reintroduced uniqueness or invented a
replacement scope (global/per-department/per-year all remain PENDING —
see §11).

## 6. Response design

**IMPLEMENTED**: `LetterListItem` (`app/schemas/letter.py`) — every
`Letter` field except `text_content` and `reason`, the two fields a
tabular registry view has no use for. `GET /api/v1/letters/{id}` is
unchanged — still returns the full `LetterResponse`.

## 7. Query architecture & performance

**IMPLEMENTED**: plain SQLAlchemy expression filters for exact-match
fields, `ILIKE` for contains-match fields, both composed with `.where()`
inside one `select()` — no full-text search, no `pg_trgm`, no second
query engine, exactly as the architecture review recommended and nothing
more.

**No N+1 queries**: `list_letters` does not eager-load `documents`,
`notifications`, or `classification` objects — the `LEFT JOIN` to
`classifications` (only added when `visibility_filter is not None`,
i.e. only for a `USER` caller) exists solely to make
`Classification.restricts_access` referenceable in the `WHERE` clause;
no `Classification` object is ever materialized or returned.
`LetterListItem` only exposes `category_id`/`classification_id` (not
names — "the UI can resolve names separately", carried over unchanged
from the architecture review), so there is no name-resolution query per
row to begin with.

## 8. Index

**IMPLEMENTED**: `ix_letters_reference_number` (migration `9fa970ffa560`)
— a plain, non-unique B-tree index, re-added after
`uq_letters_reference_number` (and its implicit index) was removed
during the Phase 4B hardening pass. No index was added for `subject`/
`sender_name`/etc. — a B-tree index gives no benefit to `ILIKE
'%contains%'` matching, so adding one there would be pure write
overhead with no read benefit (unchanged assessment from the
architecture review; would become justified if `pg_trgm` is ever
adopted, which it was not this phase).

## 9. Security — verified, not just designed

Every threat the architecture review identified now has a concrete,
tested mitigation, not just a plan:

| Threat | Mitigation | Verified by |
|---|---|---|
| Classified-record count/pagination leakage | Query-level `visibility_filter`, same `stmt` for count and items (§1) | `test_classified_record_excluded_from_total_count`, `test_classified_record_excluded_across_all_pages` (automated) + live `lrs_dev` check (`docs/PROJECT_STATUS.md`) |
| Cross-department filter override | `department_id` silently ignored for non-SYSTEM_ADMIN (§2, unchanged) | `test_user_cannot_expand_scope_via_department_filter`, `test_admin_cannot_expand_scope_via_department_filter` |
| Sort-field / arbitrary ORDER BY injection | `LetterSortField` enum — FastAPI rejects anything else with `422` before the endpoint runs | `test_invalid_sort_field_rejected`, `test_invalid_sort_order_rejected` |
| Enumeration via search (probing for another department's/classified letters) | A search matching only inaccessible letters returns an empty, ordinary-looking result — same `200`/`{"items": [], "total": 0}` as a search matching nothing | `test_search_matching_only_inaccessible_letters_returns_safely_empty` |
| IDOR on `GET /api/v1/letters/{id}` | Unchanged from Phase 4B — `assert_letter_access` gates it identically | Pre-existing `test_letter_registry.py` coverage, unaffected by this phase |
| Oversized `page_size` | FastAPI `Query(le=100)` — `422` | `test_page_size_over_maximum_rejected` |

No client-supplied filter can override authorization — every
department/classified predicate is computed server-side from the
authenticated caller, never accepted as request input; text/exact
filters are always additional `AND` conditions on top of that, never a
substitute for it.

## 10. Test results

**43 new tests** (`tests/integration/test_letter_search.py`), covering
pagination (6), sorting (7), text search (9), exact filters (3), date
filters (4), multi-filter AND (1), department isolation (6), classified
records (5, including the two count/pagination-leakage regressions), and
enumeration safety (1) — plus the existing 344-test suite, unaffected.
**387 total, 0 failed, 0 skipped**, re-run 3 consecutive times.

## 11. Pending business clarifications (unchanged, not expanded)

1. **Reference number uniqueness scope** — global/per-department/
   per-source/per-year (`docs/architecture/letter-registry.md` §2.3/§14).
2. **The exact classification value list**
   (`docs/architecture/letter-registry.md` §2.5/§12).
3. **The exact classified-letter visibility matrix** beyond the current
   provisional `SYSTEM_ADMIN`/`ADMIN`/recorder rule
   (`app/services/authorization.py:assert_letter_access`/
   `letter_visibility_filter`).
4. **Exact reference-number search semantics beyond "contains"** — a
   product/UX question (prefix vs. contains was flagged in the review;
   contains was implemented as the more forgiving default, not
   necessarily the final answer).
5. **Whether a single free-text `search=` box (spanning multiple
   fields) is wanted** alongside the per-field parameters implemented
   this phase.

## 12. Future work (not this phase)

* `recorded_from`/`recorded_to` date filtering on `created_at`, if a
  real need for it emerges.
* A combined `search=` box (§11 item 5).
* `pg_trgm`/full-text search, if real usage shows plain `ILIKE` scans
  are too slow at production data volumes — no evidence of that exists
  yet.
* CSV/PDF/Excel export, contingent on this filter architecture (Phase
  4D/E territory, not scheduled).
* File upload/download for `LetterDocument` (unrelated to search;
  tracked separately since Phase 2/4A).
