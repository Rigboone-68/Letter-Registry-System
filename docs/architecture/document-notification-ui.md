# Documents & Notifications UI — Architecture Review (Phase 5E)

**Status: REVIEW ONLY. No frontend or backend code was written this
phase.** Builds on Phase 5A (foundation), Phase 5B (authentication/
account UX), Phase 5C (core Letter registry UI), and Phase 5D
(administration/account-management UI) — all implemented, committed,
and unchanged by this review. Repository confirmed clean and at
`f46cb7c` (Phase 5D) before this review began.

## 0. How to read this document

Same taxonomy this project has used since Phase 4A:

* **CONFIRMED** — verified directly against current backend/frontend
  source code this session (endpoints, schemas, services, repositories,
  models, and the current frontend's own integration points — all
  re-read fresh, not recalled from `docs/architecture/frontend.md`'s
  Phase 5 review, though that review's own §14/§15 findings are
  cross-checked and, where still accurate, cited rather than
  re-derived).
* **RECOMMENDED** — this document's own proposal, grounded in confirmed
  facts and the conventions Phase 5A-5D already established. Not
  implemented.
* **PROVISIONAL** — an explicit judgment call this document had to make
  one way or another, flagged so it is revisited deliberately.
* **PENDING BUSINESS CLARIFICATION** — genuinely open, not guessed.
* **PENDING BACKEND API** — the frontend capability described would
  require a backend endpoint/field that does not currently exist.
  Never worked around; always named explicitly.

## 0.1 Relationship to the existing Phase 5 review

`docs/architecture/frontend.md` §14 (Document management UX) and §15
(Notifications UX) already reviewed this ground once, during the
original Phase 5 pass, and both `documents.py`/`document_service.py`/
`document_storage.py`/`document_validation.py` and
`notifications.py`/`notification_service.py`/
`notification_repository.py` are **confirmed unchanged** since then
(Phase 4D/4E implementation, untouched by Phases 5A-5D) — a fresh read
this session reached the identical conclusions on every point §14/§15
already made: fetch+blob is required for downloads (not a plain
`<a href>`), no delete endpoint exists, polling should hit
`/unread-count` only. This document does not re-derive those from
scratch; it cites them, adds the implementation-level detail (exact
component/route/service/test architecture) neither Phase 5 nor Phase 5C
went into, and resolves the handful of details §14/§15 left open.

---

## 1. Current Document API findings (CONFIRMED, re-read fresh)

### 1.1 Endpoints — `app/api/v1/endpoints/documents.py`, all `get_current_user` only

| Method & path | Request | Response | Status codes |
|---|---|---|---|
| `POST /letters/{letter_id}/documents` | `multipart/form-data`, one `file` field — **no JSON body schema exists** (`DocumentResponse` has no matching `Create` schema; upload is a raw file field plus the `letter_id` URL segment) | `DocumentResponse` | `201`; `404` (`"Letter not found."` — collapses nonexistent/wrong-department/classified-inaccessible identically); `422` (`"Uploaded file is empty."` / `"Unsupported, unrecognized, or mismatched file type."`); `413` (`"File exceeds the maximum allowed size of {N} bytes."`); `500` (`"Failed to store the uploaded document."`) |
| `GET /letters/{letter_id}/documents` | — | `DocumentListResponse {items, total}` | `200`; `404` (same collapsed Letter-access failure) — **no pagination, no sort, no filter of any kind** |
| `GET /letters/{letter_id}/documents/{document_id}` | — | Raw file bytes (`FileResponse`, **not JSON**) | `200`; `404` (`"Letter not found."` for the parent, or `"Document not found."` if the letter is accessible but the document id doesn't match it — see §4 for why these are two different messages and what that means); `500` (`"Document content is unavailable."` — a DB row survives but the file is missing on disk; also `"Failed to store the uploaded document."`-shaped `500`s for a storage-path resolution failure) |

### 1.2 `DocumentResponse` (CONFIRMED, `app/schemas/document.py`)

```
id: uuid
letter_id: uuid
original_filename: str
mime_type: str
file_size: int
uploaded_by: uuid
uploaded_at: datetime
```

**No `storage_path` field** — never serialized, the same guarantee
`UserPublic` gives `password_hash` (§1.6). **No `document_type`
field either**, despite the `LetterDocument` model having one — it
exists on the table but is never set by `upload_document` (always
`None` in practice, confirmed by `DocumentService.upload_document`'s
`create(...)` call, which passes no `document_type` argument) and is
not exposed on the response schema at all. **No `uploaded_by` name
resolution** — the field is a bare `uuid`, and there is no
cross-role user-lookup endpoint for the frontend to resolve it against
(the same gap Phase 5C's `LetterDetailPage` already found and
documented for `recorded_by`).

### 1.3 Upload validation, exact pipeline (CONFIRMED, `document_validation.py`)

1. **Extension allowlist**: `pdf`, `jpg`, `jpeg`, `png`, `txt` — a fast,
   weak first filter, "easily spoofed" by the module's own docstring.
2. **Size**: `0 < len(content) <= settings.MAX_DOCUMENT_SIZE_BYTES`
   (`10 * 1024 * 1024` = 10 MB, `backend/app/core/config.py` — an
   ARCHITECTURAL RECOMMENDATION per Phase 4D's own review, not a
   confirmed organizational limit).
3. **Magic-byte content-signature sniff** — the authoritative check:
   `%PDF-` for PDF, `\xff\xd8\xff` for JPEG, `\x89PNG\r\n\x1a\n` for
   PNG, a UTF-8-decodability + no-control-character heuristic for
   `text/plain`. **The client-supplied `Content-Type` header is never
   read for validation purposes anywhere in this pipeline** — confirmed
   directly in `document_validation.py`'s own docstring and code.
4. **Extension/content agreement** — a `.pdf` file whose bytes are
   actually a PNG is rejected as mismatched (`FileContentMismatchError`
   → `422`), not silently accepted under either type.

The endpoint reads **exactly** `MAX_DOCUMENT_SIZE_BYTES + 1` bytes from
the upload stream before validation runs (`documents.py`'s own
`upload_document`) — bounding memory use so an oversized upload is
caught without buffering an unbounded amount of data first.

### 1.4 Download response headers (CONFIRMED — precise, not assumed)

`FileResponse(resolved_path, media_type=document.mime_type,
filename=_safe_download_filename(document.original_filename),
headers={"X-Content-Type-Options": "nosniff"})`. Passing `filename=` to
Starlette's `FileResponse` sets `Content-Disposition: attachment;
filename="..."` by default (its `content_disposition_type` parameter
defaults to `"attachment"`) — **this forces a browser download, it does
not render inline**, confirmed from the FastAPI/Starlette contract this
code invokes, not merely assumed. `_safe_download_filename` strips
control characters (`\r`, `\n`, and other C0/DEL bytes) from the
original filename before it reaches the header — defense in depth
against header injection, on top of what HTTP header parsing already
disallows. `Content-Type` is always the server-validated `mime_type`
from step 3 above — **never** the client's original upload-time
`Content-Type` claim, which was never trusted or stored in the first
place.

### 1.5 Storage path reconstruction on download (CONFIRMED — a real, deliberate design choice)

`download_document` does **not** trust the `storage_path` column
stored on the row — it re-derives the expected path from
`build_storage_path(letter_id, document_id, document.mime_type)` (three
already-authorized/validated primitives) and re-verifies containment
under the storage root before ever opening a file handle
(`document_storage.py` §1.6 below). This means a hypothetically
corrupted or tampered `storage_path` column value has zero effect on
what gets served — entirely irrelevant to the frontend, but confirms
there is no path-traversal surface the frontend needs to defend
against on its side either.

### 1.6 Storage (CONFIRMED, `document_storage.py`)

Path shape: `<STORAGE_PATH>/<letter_id>/<document_id>.<extension>` —
both UUIDs server-generated, extension server-derived from the
validated MIME type (`EXTENSION_BY_MIME_TYPE`), **never** from the
client's original filename or extension. Writes are staged to a unique
temp file and atomically `os.replace`d into place. `storage/README.md`
(Phase 4D) documents the same convention; unchanged since. **No route
serves this directory statically** — confirmed by `app/main.py`, which
mounts only `api_router` and a `/health` liveness probe, no
`StaticFiles`.

### 1.7 Authorization chain (CONFIRMED — the letter-first pattern, extended, not duplicated)

Every document operation resolves and authorizes the **parent Letter
first**, via `LetterService.get_letter` (which applies
`assert_letter_access` — department isolation, then the classified-
access narrowing for a non-recording `USER`) — `DocumentService` has no
department/classification logic of its own. `assert_document_access`
(`app/services/authorization.py`, built in Phase 4D) exists as a thin
delegate for a future caller already holding a loaded `LetterDocument`,
but the actual endpoints in `documents.py` don't use it — they call
`LetterService.get_letter` directly, which is the more common
call-shape here (§7 confirms this is intentional, not an oversight).
`SYSTEM_ADMIN` retains full cross-department document access, matching
its Letter access exactly — no separate document-level permission tier
exists (`documents.py`'s own module docstring: "Do not create a
separate document permission hierarchy").

### 1.8 Document lifecycle (CONFIRMED)

**Upload only.** No `PATCH`, no `DELETE`, no replace-in-place endpoint
exists anywhere in `documents.py`, and `document_service.py`'s own
docstring states this is deliberate, not a gap: **"replacement" means
calling `upload_document` again — the prior document row and file are
both left completely untouched.** A Letter can accumulate any number of
`LetterDocument` rows over time; none is ever superseded, hidden, or
removed by a later upload. `delete_document_file` exists in
`document_storage.py` but is **only** failure-path compensation (an
orphaned file after a database commit fails) — never reachable from any
user action.

---

## 2. Current Notification API findings (CONFIRMED, re-read fresh)

### 2.1 Endpoints — `app/api/v1/endpoints/notifications.py`, all `get_current_user` only, unconditionally scoped to `current_user`

| Method & path | Request | Response | Status codes |
|---|---|---|---|
| `GET /notifications` | `page` (default 1), `page_size` (default 25, max 100) — **no other query parameter exists: no `is_read` filter, no `notification_type` filter, no date filter, no sort override** | `NotificationListResponse {items, total, page, page_size, total_pages}` | `200` |
| `GET /notifications/unread-count` | — | `UnreadCountResponse {unread_count: int}` | `200` |
| `PATCH /notifications/{notification_id}/read` | — | `NotificationResponse` | `200`; `404` (`"Notification not found."` — collapses "doesn't exist" and "belongs to a different recipient" identically) |
| `PATCH /notifications/read-all` | — | **A raw `dict`, `{"marked_read": <int>}`** — no `response_model` is declared on this route, unlike every other endpoint in this codebase | `200` |

### 2.2 `NotificationResponse` (CONFIRMED, `app/schemas/notification.py`)

```
id: uuid
letter_id: uuid | null
notification_type: str
message: str
is_read: bool
created_at: datetime
read_at: datetime | null
```

`notification_type` is a **plain string, not an enum** on either the
schema or the model — confirmed in `app/models/notification.py`'s own
docstring reasoning (parallel to `LetterDocument.document_type`). In
practice, **exactly one value is ever generated**:
`"LETTER_REGISTERED"` (`notification_service.py:notify_letter_registered`,
the only call site anywhere that creates a `Notification` row). The
frontend must not assume this is a closed, exhaustive set — a future
trigger could introduce a new string value with no schema change and
no frontend contract to update against, so any type-specific rendering
logic (§10) must degrade to the raw `message` text for an unrecognized
`notification_type`, never crash or render blank.

### 2.3 Message content (CONFIRMED, safe to render as-is)

The one generated message is a fixed template: `"A new letter
(reference: {reference_number}) has been registered in your
department."` — **never** the Letter's subject, sender, content, or
classification. This is deliberate (`notification_service.py`'s own
docstring, §14/§15 of `docs/architecture/audit-notifications.md`): a
later classification change on the referenced Letter cannot
retroactively scrub text already delivered to a recipient, so nothing
sensitive is ever interpolated into it in the first place. **CONFIRMED
safe to render as plain text** — it is a fixed, server-authored
template with exactly one interpolated value (`reference_number`, which
is itself never classified/restricted data — Letters' own reference
number carries no confidentiality marking anywhere in this schema).
React's default JSX text rendering already HTML-escapes it, so no
`dangerouslySetInnerHTML` or similar is ever needed or should be used
(§9/§24's XSS question, resolved here).

### 2.4 Ordering, pagination, recipient isolation (CONFIRMED)

Newest-first (`created_at DESC`, stabilized by `id ASC` — the same
deterministic-secondary-sort convention `LetterRepository` already
uses), full `page`/`page_size`/`total`/`total_pages` pagination
matching `LetterListResponse`'s exact shape (Phase 4C). Every
non-`create` repository method (`list_by_recipient`, `count_unread`,
`find_by_id_and_recipient`, `mark_all_read`) is scoped by
`recipient_user_id` at the query level — there is no code path by which
one user's request can return or mutate another's notification, and no
`recipient_user_id` parameter exists anywhere a client could attempt to
supply one (confirmed absent from every endpoint signature and both
schemas).

### 2.5 `mark_read`/`mark_all_read` idempotency (CONFIRMED)

Both are idempotent: `mark_read` on an already-`is_read=true` row is a
no-op returning the current state unchanged (no `read_at` overwrite);
`mark_all_read` only touches currently-unread rows and returns the
count actually flipped (`0` if the caller had none unread) — safe to
call repeatedly, including redundantly.

### 2.6 Notification generation (CONFIRMED — context only, not this phase's concern)

Best-effort, via a database `SAVEPOINT`, triggered solely by
`LetterService.create_letter` (Phase 4E) — recipients are the target
department's `ACTIVE` Admins at the moment of registration. This phase
consumes notifications; it does not generate them, and nothing here
proposes changing the trigger set or recipient strategy (both remain
exactly as Phase 4E's own review left them, `PROVISIONAL` per that
review, unchanged).

---

## 3. Document upload architecture

### 3.1 Where upload belongs (RECOMMENDED)

**Inline on `LetterDetailPage`, inside the existing labeled placeholder
section** (`frontend/src/pages/LetterDetailPage.jsx:151-157`,
confirmed still present, unchanged since Phase 5C) — not a modal, not a
separate route. A document has no independent existence or URL a user
would navigate to directly (`documents.py` is nested under
`/letters/{letter_id}/documents`, matching the "documents have no
standalone route" decision `routes/index.jsx`'s own header comment
already states); the Letter detail page is already the one place a
document's context (which letter, whether the caller can even see it)
is established. A modal would add focus-management complexity for no
real benefit over an inline section that's already on the page the user
came from.

### 3.2 Multiple files — single-file selection only (RECOMMENDED, `PROVISIONAL` on the exact UX)

The endpoint's own signature — `file: UploadFile = File(...)`, one
field — accepts exactly one file per request. **Multiple files means
multiple sequential requests**, never a batch/bulk endpoint (none
exists). RECOMMENDED: allow selecting multiple files in one file-picker
interaction (a native `<input type="file" multiple>` is a UX
convenience with no backend cost), but upload them as **sequential**,
not concurrent, requests — concurrent uploads to the same
letter would each independently re-authorize the same Letter and offer
no real speed benefit given the 10 MB ceiling and typical letter-
attachment counts, while sequential upload keeps the UI's "which file
succeeded, which failed, retry just this one" bookkeeping trivial
(one in-flight request at a time, one clear per-file status). Whether
multi-file selection is worth the added state-tracking versus a
simpler one-file-at-a-time flow is `PROVISIONAL` — not mandated by any
backend or accessibility constraint either way.

### 3.3 Progress reporting (CONFIRMED capability, clarifying the brief's own framing)

The brief's §5 asks whether "progress reporting is actually supported
by the current API" — this is not quite the right question: upload
progress is a **client-side, transport-level** capability (`axios`
already exposes `onUploadProgress` on every request, unrelated to
anything the backend opts into or must support), not a backend feature
to check for. **CONFIRMED**: `axios` (already the one HTTP client in
this codebase, Phase 5A) supports `onUploadProgress` natively — RECOMMENDED
for files approaching the 10 MB ceiling, where a multi-second upload
with no feedback would read as a hang. Not RECOMMENDED as a hard
requirement for every upload, given typical letter attachments are
likely far smaller than 10 MB — `PROVISIONAL` whether it's worth the
added complexity for small files versus a simple disabled-button
loading state.

### 3.4 Client-side vs. backend validation (RECOMMENDED, mirrors §14's own already-correct answer)

Client-side extension + size pre-checks are a **UX nicety only** —
reject obviously-wrong files before spending a round trip, but never
treat a client-side pass as authoritative: the backend re-validates
extension, the authoritative magic-byte signature, and size
independently, and will reject anything the client-side check let
through incorrectly. The frontend must never skip or weaken its own
handling of a `422`/`413` on the assumption its own pre-check already
covered it.

### 3.5 Duplicate filenames / duplicate documents (CONFIRMED — no special handling needed or possible)

There is no uniqueness constraint on `original_filename` anywhere in
the schema, and no duplicate-detection logic in `document_service.py`
— two documents with the identical filename (even byte-identical
content) can coexist on the same Letter without conflict. **The
frontend must not invent a "this filename already exists" warning** —
nothing in the confirmed backend contract supports or implies one, and
adding one would be inventing a business rule this document is
explicitly told not to.

### 3.6 Replacement and deletion (CONFIRMED, restated precisely per the brief's §7 instruction)

**No deletion exists.** The upload form/action must never be labeled or
described as "replace" in a way that implies the prior document is
superseded, hidden, or removed — RECOMMENDED wording: "Upload another
document" or "Add document," never "Replace document." **No delete
action of any kind belongs in this UI** — confirmed there is nothing
for one to call.

### 3.7 Retry (RECOMMENDED)

A failed upload is retryable simply by re-submitting the same file —
no special backend retry semantics exist or are needed (each request is
independent; a failed request has no side effect to undo, since
write-then-commit-with-compensation, §1.8/`document_service.py`,
guarantees a failed upload never leaves a visible document behind).

---

## 4. Document download architecture

### 4.1 Authenticated fetch + blob is required, not a plain `<a href>` (CONFIRMED, a real technical constraint — restating §14's already-correct finding with the exact mechanism)

`GET /letters/{letter_id}/documents/{document_id}` requires the same
`Authorization: Bearer <token>` header as every other endpoint in this
API (`get_current_user`, no exception). A plain `<a href="...">` click
is a normal browser navigation, which cannot attach a custom
`Authorization` header — this is a browser platform limitation, not a
backend design choice, and no amount of frontend cleverness routes
around it without either (a) a cookie-based session (this backend does
not use cookies, confirmed since Phase 3A: the bearer token is returned
in a JSON body, never set as a cookie) or (b) a signed/pre-authenticated
URL (does not exist — §22). **RECOMMENDED**: fetch the document through
the existing authenticated `apiClient` instance (`responseType:
'blob'`), then either `URL.createObjectURL(blob)` for a programmatic
download trigger (a synthetic, immediately-clicked `<a>` with the
`download` attribute set to the original filename) or an inline
`<iframe>`/`<img>` preview for previewable types — see §25 for whether
preview is even in scope.

### 4.2 What the service layer should return (RECOMMENDED, answering §16 directly)

`documentService.download(letterId, documentId)` should return the raw
`Blob` (via `apiClient.get(..., {responseType: 'blob'})`), **not** an
object URL and **not** a triggered download — object-URL creation and
revocation (`URL.revokeObjectURL`, to avoid leaking memory) is a
component-lifecycle concern (create it when the user clicks download,
revoke it when the component unmounts or the download completes), not
a service-layer one; keeping the service function a pure
"fetch bytes" call matches every other service module's own
single-responsibility shape (`letterService.get`, `adminService.get`,
etc. all just fetch and return `response.data`, never manage
browser-side object lifecycle).

### 4.3 "Open in a shareable new-tab URL" is not available (CONFIRMED limitation, restating §14/§22)

Since every download requires an authenticated fetch, there is no
bookmarkable, shareable, or "open in new tab via address bar" URL for a
document — only a same-page, script-triggered blob download/preview.
A signed, short-lived URL (the standard fix for this class of problem)
does not exist in this backend and is explicitly out of this phase's
scope to add (§28's own "signed URLs unless already supported"
instruction — none are). **PENDING BACKEND API** if this UX is ever
wanted.

### 4.4 Download error handling (RECOMMENDED, distinguishing exactly what the brief's §6 asks for)

| Case | Backend signal | Frontend handling |
|---|---|---|
| Expired/invalid session | `401` (handled centrally, `apiClient.js`'s existing interceptor — unchanged, this phase adds nothing new here) | Existing centralized redirect-to-login; no per-download handling needed |
| Inaccessible resource (wrong department, classified, nonexistent, wrong-letter/document pairing) | `404` (`"Letter not found."` or `"Document not found."`) | Generic "not found" — **never** distinguished by cause (§4.1's own two-message nuance is a backend-internal detail; the frontend still renders both identically, per §13's classified-resource discipline) |
| Server/storage failure | `500` | Generic retryable `ErrorState` |
| Browser/blob failure (network drop mid-download, an unexpected non-file response body) | Caught client-side (a rejected fetch/blob promise) | Generic retryable error — never a raw browser exception message |

### 4.5 A precise distinction the backend itself makes that the frontend should know about, but never expose differently (CONFIRMED)

A `404` from the **list** endpoint (`GET .../documents`) always means
`"Letter not found."` (the Letter itself is inaccessible — there is no
per-document 404 possible from a list call). A `404` from **download**
can mean either `"Letter not found."` (same as above) or `"Document not
found."` (the Letter is accessible, but this specific `document_id`
doesn't belong to it) — two different backend strings, but the
frontend renders **the exact same generic behavior** either way (a
"not found" state, no retry-implying language, no elaboration) — the
distinction matters only in that the frontend must never manufacture
a *third*, more specific message ("this document was deleted" is
categorically false, since deletion doesn't exist) by inferring meaning
from which of the two strings came back.

---

## 5. Document lifecycle (CONFIRMED summary, consolidating §1.8/§3.6)

| Operation | Exists? | Notes |
|---|---|---|
| Upload | Yes | `POST`, one file, unlimited count per Letter |
| List | Yes | `GET`, unpaginated (returns everything) |
| Retrieval/download | Yes | `GET .../{document_id}`, streamed |
| Replacement | No — upload again instead | Old document fully untouched |
| Deletion | No | Not V1, not planned; confirmed in code and docstrings |
| Archival (of a document specifically) | No | Only the parent *Letter* has an archive concept (`LetterStatus`); documents have no status field of their own at all |
| Historical preservation | Yes, by construction | Nothing removes a document; an archived Letter keeps its documents fully downloadable (this exact guarantee was directly tested in Phase 4D — `tests/integration/test_document_management.py`) |

---

## 6. Document security model

### 6.1 Letter authorization (CONFIRMED — reused, never duplicated)

Every document operation authorizes through the same
`assert_letter_access` chain Letters already use (§1.7) — department
isolation first, then the classified-access narrowing for a
non-recording `USER`. The frontend's obligation is identical to what
Phase 5C already established for Letters: **never** independently
decide whether a Letter (or, by extension, its documents) is
accessible — render exactly what the API returns.

### 6.2 IDOR (Letter and Document ids) (CONFIRMED, no frontend action needed)

Both `letter_id` and `document_id` are UUIDs, and both are re-validated
against the full authorization chain on **every** request — a
frontend-visible `document_id` in a URL/route param carries no implicit
trust; the backend re-derives everything from scratch each time. The
frontend must not assume "I already loaded this document once, so a
later request for the same id is safe" — nothing caches or shortcuts
authorization anywhere in this stack (the same "never cache
authorization" principle Phase 4D's own review established, restated
because a document-download UI is exactly the kind of feature where a
lazily-cached "yes this is downloadable" flag would be tempting to add
and must not be).

### 6.3 Classified Letters (CRITICAL — CONFIRMED, extends Phase 5C's discipline)

A classified Letter's documents are gated by the identical
`assert_letter_access` check as the Letter itself — there is no
document-level classification concept independent of its parent
Letter. A `404` on a document list or download must render exactly the
same generic "not found" Phase 5C already uses for a classified Letter
detail page — never "this document is classified" or any language that
would confirm the document (or the Letter) exists.

### 6.4 Cross-department access (CONFIRMED, no frontend action needed)

Identical reasoning to §6.1 — department isolation is enforced entirely
server-side via the same chain; the frontend adds nothing on top and
removes nothing from it.

### 6.5 Bearer-token handling (CONFIRMED — unchanged, no new pattern needed)

Every document request (list, upload, download) goes through the
existing `apiClient` instance, which already attaches
`Authorization: Bearer <token>` via its request interceptor
(`services/apiClient.js`, unchanged since Phase 5A) — a blob-typed
download request needs no different token handling than any JSON
request already gets.

### 6.6 What the frontend must never expose (CONFIRMED, direct answers to §4's checklist)

* **Storage paths / physical file paths** — never available to expose;
  `DocumentResponse` has no such field (§1.2).
* **Internal UUIDs beyond API URLs** — `id`/`letter_id` are already
  necessarily visible in the API surface the frontend calls (they're
  the URL path parameters); nothing beyond that is exposed, and nothing
  should be additionally surfaced (e.g., no raw `id` displayed
  decoratively in the UI where a human-readable label would do).
* **Signed URLs / public URLs** — none exist; §4.3.

### 6.7 `X-Content-Type-Options: nosniff` (CONFIRMED — already backend-enforced, informational for the frontend)

The download response always includes this header (§1.4) — it
instructs the *browser* not to MIME-sniff the response content and
override the declared `Content-Type`, mitigating a class of
content-sniffing XSS/confusion attack. This is entirely a backend
response-header concern; the frontend has nothing to configure or
verify about it beyond not fighting it (e.g., never manually re-setting
a different `Content-Type` on a blob before triggering a download in a
way that would defeat the point).

---

## 7. Notification architecture

### 7.1 Component split (RECOMMENDED, answering §15's own diagram precisely)

```
Topbar
  └─ NotificationBell            (unread-count badge, opens the panel)
       └─ NotificationPanel      (a dropdown — see §7.2 for why a full page is not RECOMMENDED for V1)
            └─ NotificationItem  (one row: message, relative time, read/unread state, click → mark-read + navigate)
```

Plus, RECOMMENDED as a secondary surface (see §7.2): a lightweight
`/app/notifications` route reusing the same `NotificationItem`
rendering, for the case where a user wants to review notifications
beyond what a dropdown can reasonably show. `navigationConfig.js`
already lists "Notifications" for every role, pointing at
`/app/notifications` (Phase 5A, unchanged) — that slot already exists
and expects a real page eventually, independent of whether a dropdown
also exists.

### 7.2 Dropdown vs. dedicated page — both are justified, for different reasons (RECOMMENDED)

A **dropdown** (`NotificationPanel` from the Topbar bell) is the
primary, low-friction surface for "what's new" — a small number of
recent items, mark-read inline, click through to a Letter. A **dedicated
page** at `/app/notifications` (the route `navigationConfig.js` already
points every role's Sidebar entry at) is justified separately because
the backend already supports full pagination (`page`/`page_size`,
§2.1) that a small dropdown has no good way to expose — a dropdown
showing "page 3 of 12" would be an awkward, cramped UX. RECOMMENDED:
the dropdown shows a bounded recent slice (e.g., the first page at a
small `page_size`, RECOMMENDED default same as Letters' 25, or
smaller for a dropdown's limited vertical space — `PROVISIONAL` exact
number) with a "View all" link into the full paginated page; the full
page reuses the identical `NotificationItem` component and the
identical `notificationService.list` call with a real `page`/`page_size`
control, much like `LetterListPage`'s own pagination (Phase 5C) but
without sort/filter controls, since the backend supports neither for
notifications (§2.1).

### 7.3 Unread/read visual distinction (RECOMMENDED)

`is_read` drives both a visual treatment (RECOMMENDED: unread rows
slightly emphasized — e.g. a bold message or a small dot indicator,
never color alone per this project's established accessibility rule)
and an `aria-label`/visually-hidden text distinction ("Unread:
{message}" vs. just "{message}") — matching the `StatusBadge` `domain`
prefix pattern Phase 5D already established for exactly this kind of
accessible-context problem.

### 7.4 Mark read: on click/navigate vs. only explicit (PENDING BUSINESS CLARIFICATION — genuinely open, not decided here)

The backend supports both `PATCH .../read` (one) and `PATCH
.../read-all` (bulk) as explicit actions; **nothing about the API
implies or requires an automatic mark-read on view** — `GET
/notifications` never touches `is_read` (§2.1, confirmed by reading
`list_notifications`, which calls only `list_by_recipient`, a pure
read). Two real, defensible options exist: (a) mark read automatically
the moment a notification is clicked/navigated from (a common pattern,
e.g. most email/chat clients), or (b) require an explicit "mark read"
affordance separate from navigating to the Letter. **RECOMMENDED
default, if a decision is needed before business input arrives**: mark
read on click-to-navigate (option a) — it matches the mental model
"I opened it, so I've seen it," and the explicit `PATCH .../read-all`
button remains available for bulk clearing without opening each one.
This default is **PROVISIONAL**, not a confirmed requirement — flagged
in §23 for an actual decision.

### 7.5 Ordering (CONFIRMED, no design decision needed)

Newest-first is the backend's only supported order (§2.4) — no sort
control should be built; there is nothing for one to control.

---

## 8. Notification security model

### 8.1 The frontend cannot request another user's notifications (CONFIRMED — structural, not a check to add)

No endpoint accepts a `recipient_user_id` (or any equivalent) parameter
anywhere — confirmed absent from `list_notifications`,
`unread_count`, `mark_read`, `mark_all_read`'s full signatures. There
is no code path, correct or malicious, by which a request could target
another user's notifications; this is not a rule the frontend
"preserves," it is a capability that was never given to it at all.

### 8.2 Cannot mark another user's notification read (CONFIRMED — same structural guarantee)

`mark_read`/`mark_all_read` are both scoped to `current_user` at the
repository query level (§2.4/§2.5) — a `notification_id` belonging to
someone else simply 404s (§8.3), never succeeds silently against the
wrong row.

### 8.3 No existence inference through error differences (CONFIRMED)

`NotificationNotFoundError` (`app/services/exceptions.py`, restated
here for this phase) collapses "doesn't exist" and "exists but belongs
to a different recipient" into one identical `404` — the frontend must
render this exactly like every other collapsed-404 case in this
project (Letters, Documents, Users, Admins) — generic, unelaborated.

### 8.4 Error-status mapping (RECOMMENDED, direct answer to §9)

| Status | Meaning here | Frontend handling |
|---|---|---|
| `401` | Session expired/invalid | Existing centralized handler — unchanged |
| `403` | Not applicable — no role restriction exists on any notification endpoint (§2.1); should never occur in practice | If it somehow did (a defensive case, e.g. a future backend change), treat as a generic `ErrorState`, never inventing meaning |
| `404` | Mark-read target not found/not yours | Generic — §8.3 |
| `409` | Not applicable — no conflict-producing operation exists (nothing here has a state machine with a rejectable transition) | N/A |
| `422` | Not applicable in practice — no request body/query parameter validation is complex enough to realistically fail beyond FastAPI's own `page`/`page_size` bounds | If it occurred, standard field-error rendering (`errorNormalization.js`, unchanged) |
| `500` | Server failure | Generic retryable `ErrorState` |
| Network failure | Unreachable server | Generic retryable `ErrorState`, matching every other list screen |

### 8.5 XSS through notification messages (CONFIRMED safe — §2.3)

Already resolved: the one generated message is a fixed, server-authored
template with one interpolated non-sensitive value, rendered through
ordinary JSX text interpolation (auto-escaped by React) — never through
`dangerouslySetInnerHTML`. No sanitization library is needed or should
be added.

---

## 9. Notification UX

Covered in full in §7. Summarizing the specific brief questions:

* **Dropdown sufficient?** Yes, for the "what's new" glance use case —
  §7.2.
* **Dedicated page needed?** Yes, because pagination exists and a
  dropdown can't reasonably expose it — §7.2.
* **Both justified?** Yes, for the reasons above — not redundant, each
  serves a different interaction.
* **Unread badge behavior** — RECOMMENDED: the bell shows the raw
  `unread_count` number (capped visually at a reasonable display width,
  e.g. "99+", a pure display truncation, never a backend request
  change) from `GET /notifications/unread-count`, refreshed per §11's
  polling design.
* **Polling strategy** — §11.
* **Stale notification handling** — RECOMMENDED: after any mark-read
  action (single or bulk), update the local unread count and the
  affected item(s) directly from the action's own response, matching
  every other Phase 5C/5D mutation's "refresh from the response, not a
  second fetch" convention — never leave a stale unread badge after an
  action the user just took.

---

## 10. Letter integration

### 10.1 Documents in `LetterDetailPage` (CONFIRMED insertion point)

`frontend/src/pages/LetterDetailPage.jsx:151-157` already has a
labeled placeholder exactly for this
(`<div className={styles.documentsPlaceholder}><h2>Documents</h2>...`)
— RECOMMENDED: this becomes the real `DocumentList` + upload section,
replacing the placeholder text, not a new page or route. **No document
integration on `LetterListPage`** — the brief itself and Phase 5's own
`docs/architecture/frontend.md` §14 agree there is no standalone
document list/route; a document only ever appears in the context of
its one Letter.

### 10.2 Notifications in `AppShell`/`Topbar` (RECOMMENDED insertion point)

`frontend/src/layouts/Topbar.jsx` currently renders only the app name
and (when authenticated) the identity block + logout button — RECOMMENDED:
`NotificationBell` mounts inside `Topbar`, alongside the identity
block, visible for every authenticated role (no role restriction exists
on notifications, §14). `AppShell` itself needs no change beyond
already rendering `Topbar` (unchanged since Phase 5A).

### 10.3 Notification → Letter navigation (CONFIRMED behavior, RECOMMENDED implementation)

`NotificationResponse.letter_id` is **nullable** (§2.2) — confirmed
directly, and the model's own docstring explains why: today's only
notification type always has one, but the field was deliberately left
optional so a future non-Letter notification type doesn't need a schema
change. **Exact implication for the frontend**: a `NotificationItem`
must render two states — `letter_id` present → the item is a real link/
button that navigates to `/app/letters/{letter_id}` on click (§7.4's
mark-read-on-click question applies here); `letter_id` null → the item
renders as plain, non-interactive text (no dead link, no
navigate-to-nowhere). RECOMMENDED: reuse `/app/letters/{id}` — the
existing shared Letter detail route (Phase 5C) — **never** a
role-branching path (`/app/system/letters/{id}` does not exist as a
detail route; only the LIST is role-split, per Phase 5C's own routing,
confirmed unchanged — `LetterDetailPage` is mounted once, at
`/app/letters/:id`, and handles any role's access via the backend's own
authorization).

### 10.4 A real, narrow race window worth documenting (CONFIRMED reasoning, RECOMMENDED handling — extends §13)

Because a `LETTER_REGISTERED` notification's recipient is always an
`ACTIVE` Admin of the letter's *then-current* recipient department at
generation time (§2.6), and Admin access is always re-checked live
(never cached, Phase 4D's own principle), a navigate-to-Letter click
can still `404` if the recipient's own access changed *after* the
notification was created — e.g. the Admin was transferred to a
different department (Phase 5D's own confirmed instant-effect
behavior) or their department was deactivated. **RECOMMENDED**: this is
not a bug to work around — it's rendered exactly like any other Letter
`404` (§13), the identical generic "Letter not found" Phase 5C already
shows. The notification item itself is not retroactively hidden or
specially labeled; it simply leads to a normal 404 if clicked after the
recipient's access has changed.

---

## 11. Notification polling

### 11.1 What to poll (CONFIRMED, restating §15's already-correct answer with the exact endpoint)

**`GET /notifications/unread-count` only** — never the full
`GET /notifications` list on an interval; the count endpoint is a
single `SELECT COUNT(*)` (§2.4's `count_unread`), cheap regardless of
how often it's called, while the list endpoint does real pagination
work and returns a meaningfully larger payload for no benefit when all
that's needed is "has anything changed."

### 11.2 Interval (RECOMMENDED, `PROVISIONAL` on the exact number)

RECOMMENDED: 60 seconds. Reasoning: this is an internal, single-tenant-
per-department operational tool, not a chat application — sub-minute
notification latency has no confirmed business requirement (§25), and
a 60-second interval keeps request volume low (60 requests/hour/active
tab) while still feeling "live enough" for a workplace tool where
letters are registered at human, not real-time, pace. The exact number
is `PROVISIONAL` — nothing in the confirmed backend or business
requirements mandates 60 specifically over, say, 30 or 120.

### 11.3 Pausing (RECOMMENDED, matching an existing capability, not a new mechanism)

RECOMMENDED: pause polling when the browser tab is hidden
(`document.visibilityState`/the `visibilitychange` event — a native
browser API, not a new dependency) and resume (with an immediate
refresh) when it becomes visible again — avoids polling a tab nobody is
looking at. This is a plain `useEffect` + native event listener, the
same category of mechanism `AuthContext`'s own session-restoration
effect already uses (Phase 5A/5B) — **no state-management library**
is needed or should be added for this (§21's own explicit instruction,
already satisfied by the existing architecture).

### 11.4 Where polling lives (RECOMMENDED)

In `NotificationBell` itself (or a small hook it uses,
e.g. `useUnreadCount`) — not in `AuthContext` (unread count is not
authentication state) and not in a new global store (none exists or is
being added, §21). `NotificationBell` mounts once, inside `Topbar`,
inside `AppShell`, which itself mounts once per authenticated session
(Phase 5A) — so the interval naturally starts/stops with
mount/unmount, no separate lifecycle management needed.

---

## 12. Classified-resource handling (CRITICAL — direct answers to §13's four scenarios)

| Scenario | Confirmed backend behavior | Frontend handling |
|---|---|---|
| A notification references a Letter the user cannot access | The notification itself was correctly delivered (recipient was authorized at generation time, §10.4) but access changed since — clicking it hits the Letter's own `assert_letter_access` check | Render the identical generic Letter "not found" (§10.4) — the notification list/panel itself never hides, filters, or specially labels this item; only the *navigation target* 404s |
| A Letter returns `404` | Collapses nonexistent/wrong-department/classified-inaccessible identically (Phase 5C, unchanged) | Generic "Letter not found" — unchanged, this phase adds nothing new |
| A document list returns `404` | Means the **parent Letter** is inaccessible (§1.1 — there is no other 404 cause for the list endpoint) | Generic "not found" on the Documents section of the Letter detail page — but note: if the Letter itself already 404'd, `LetterDetailPage` never reaches the point of rendering a Documents section at all (§10.1 — the whole page is the generic not-found state), so this case in practice only matters for a defensive/direct API-testing scenario, not a reachable UI state |
| A document download returns `404` | Either cause from §4.5 | Generic "not found" for that one document's download action — the rest of the document list and the Letter detail page around it are unaffected |

**The frontend must never** — direct restatement of §13's own
instruction — independently determine or infer whether a Letter is
classified or a document exists; every case above is the backend's
`404` rendered as-is, with zero added or inferred meaning.

---

## 13. Role behavior (CONFIRMED — no role-specific functionality anywhere in either API)

**Documents**: every route uses `get_current_user` only — no role
dependency at all (§1.7). `SYSTEM_ADMIN` gets the same cross-department
access it already has to Letters (no separate document permission
tier, confirmed in the endpoint module's own docstring); `ADMIN`/`USER`
get whatever their existing Letter access already grants. **Nothing in
this UI should branch on role** — unlike `LetterListPage`
(Phase 5C, which legitimately shows a Department column only for
`SYSTEM_ADMIN` because *that* data requires a SYSTEM_ADMIN-only
reference-data endpoint) or the Phase 5D administration screens (which
are role-gated routes entirely), Documents has no analogous asymmetry
to render differently for — the same `DocumentList`/upload UI is
correct for every role, and the backend's own authorization is what
actually differs the *content* returned, never something the frontend
needs to branch its rendering on.

**Notifications**: identical reasoning — no role dependency exists
anywhere (§2.1's own docstring: "there is no role restriction, because
a notification's entire access rule is per-account ownership... not
department/role scoping"). `NotificationBell`/`NotificationPanel`
render identically for every role.

**Navigation visibility remains discoverability only, not a security
mechanism** (restated per §14's own instruction, already the
established convention since Phase 5A/5D) — even though this phase
introduces no role-gated route, this document does not change that
principle for the routes it does touch (`/app/notifications` remains
listed identically for `SYSTEM_ADMIN`/`ADMIN`/`USER` in
`navigationConfig.js`, unchanged).

---

## 14. Component architecture (RECOMMENDED — only where real reuse exists)

### 14.1 Documents

* **`DocumentList`** — RECOMMENDED, real reuse candidate: renders
  `DocumentResponse[]` as a semantic list/table (filename, human-
  formatted size, upload date; §1.2 confirms no uploader-name
  resolution is possible, so `uploaded_by` is not rendered as a raw
  UUID — either omitted or, if shown at all, only as "uploaded" without
  a name, matching `LetterDetailPage`'s own precedent for
  `recorded_by`), each row with a download action. Genuinely reusable
  in the narrow sense that it's the one document-list rendering used
  wherever `LetterDetailPage` needs it — not reused across multiple
  *different* pages (there is only one page that ever shows documents),
  but still worth its own component for the same reason `LetterTable`
  was factored out in Phase 5C: keeps `LetterDetailPage` from growing a
  second large rendering block inline.
* **`DocumentUploadForm`** (RECOMMENDED name over "Dialog" — see §3.1:
  this is inline, not a modal) — the file input, client-side pre-check
  errors, upload-in-flight state, and success/failure feedback. Owns
  the upload interaction; does not own the list refresh afterward
  (that's `LetterDetailPage`'s job, the same "business logic in the
  page, not the presentational component" split Phase 5C/5D already
  follow).
* **`DownloadButton`** — **NOT RECOMMENDED as a separate component.**
  A single button with a click handler calling
  `documentService.download` + blob-URL trigger is small enough (a
  handful of lines) that factoring it out would be exactly the
  "speculative abstraction" this project's own conventions warn
  against (§14/§26 of Phase 5D's own review reached the identical
  conclusion for an analogous case, `AccountActionMenu`) — inline it in
  `DocumentList`'s row rendering instead.

### 14.2 Notifications

* **`NotificationBell`** — RECOMMENDED: owns the unread-count fetch +
  poll (§11.4) and the open/closed state of the panel. A real, single-
  purpose component.
* **`NotificationPanel`** — RECOMMENDED: the dropdown itself — fetch
  (or receive) a page of notifications, render `NotificationItem[]`,
  mark-all-read action, "View all" link to `/app/notifications`. Needs
  its own accessible-dialog-adjacent mechanics (§19) — not a
  `role="dialog"` modal (it doesn't block interaction with the rest of
  the page the way `ConfirmDialog` does), but does need focus
  management and `Escape`-to-close, closer to a disclosure/menu pattern
  than Phase 5D's `ConfirmDialog`. **Not built on top of
  `ConfirmDialog`** — that component's semantics (a blocking, modal
  confirm/cancel decision) don't fit a notification tray.
* **`NotificationItem`** — RECOMMENDED, genuine reuse: the identical
  row rendering is needed in both `NotificationPanel` (the dropdown)
  and the full `/app/notifications` page — exactly the kind of real,
  demonstrated duplication this project's components exist to remove
  (matching `StatusBadge`'s own "used in many places, one definition"
  reasoning).
* **`NotificationList`** — **NOT RECOMMENDED as a fourth, separate
  component.** The dropdown and the full page both just map
  `NotificationItem` over an array plus a loading/empty/error state
  around it — the same `LoadingState`/`EmptyState`/`ErrorState`
  primitives already used everywhere else in this codebase are
  sufficient; a wrapping `NotificationList` component would only add a
  layer with no real logic of its own, splitting what's naturally
  simple into an extra file for its own sake.
* **`UnreadBadge`** — **NOT RECOMMENDED as a separate component.** A
  small `<span>` with the count, rendered inline inside
  `NotificationBell` — one use site, not worth its own file, following
  the same "don't factor out something used exactly once" reasoning
  `DownloadButton` above already applies.

---

## 15. Service architecture (RECOMMENDED — extends the existing convention exactly)

Following `letterService.js`/`adminService.js`'s established shape
(Phase 5C/5D: named exports, one function per endpoint, no raw Axios
calls outside the service layer, no call for a nonexistent endpoint):

```
documentService.js  (NEW FILE)
  list(letterId)                          → GET  /letters/:letterId/documents
  upload(letterId, file, onUploadProgress?) → POST /letters/:letterId/documents  (multipart/form-data)
  download(letterId, documentId)          → GET  /letters/:letterId/documents/:documentId
                                              (responseType: 'blob' — returns a Blob, §4.2)

notificationService.js  (NEW FILE)
  list(params)                            → GET  /notifications  (page?, page_size?)
  unreadCount()                           → GET  /notifications/unread-count
  markRead(notificationId)                → PATCH /notifications/:notificationId/read
  markAllRead()                           → PATCH /notifications/read-all
```

**No method exists for an endpoint that doesn't exist** — no
`documentService.delete`/`replace`, no
`notificationService.updateRecipient`/`create`. `upload`'s multipart
body is built with a native `FormData` (no new dependency — the
browser platform API, already usable via `axios`'s existing
`post(url, formData, {headers: {'Content-Type': 'multipart/form-data'},
onUploadProgress})` support) — matching how every other write function
in this codebase (`letterService.create`, `adminService.authorize`,
etc.) stays a thin, single-purpose wrapper around one `apiClient` call.

---

## 16. Route architecture (RECOMMENDED — minimum needed, nothing speculative)

**One new route**: `/app/notifications` (already an existing
`PlaceholderPage` slot, `routes/index.jsx`, confirmed unchanged since
Phase 5A — no `RoleGuard` needed or present today, matching §13's "no
role-specific functionality" finding) becomes the real notifications
page. **No new route for Documents** — confirmed nothing belongs
outside `LetterDetailPage`'s existing route (§10.1); `/app/letters/:id`
already exists (Phase 5C) and needs no new child route, since the
Documents section is inline content on that same page, not a
navigable sub-resource. **No route change to `LetterListPage`/
`LetterFormPage`** — neither needs any document/notification awareness.

---

## 17. Error handling (RECOMMENDED — the complete matrix, per §18)

| Status | Documents | Notifications |
|---|---|---|
| `401` | Existing centralized handler (unchanged) | Existing centralized handler (unchanged) |
| `403` | Not expected in practice (no role dependency, §13) — if it somehow occurred (e.g. an unrelated backend change), generic `ErrorState`, never reinterpreted as `404` | Same — not expected, generic fallback if it occurred |
| `404` | Generic "not found," collapsing every cause identically (§4.5/§12) | Generic "not found" on a mark-read target (§8.3) |
| `409` | Not applicable — no endpoint here has a conflict-producing state transition | Not applicable |
| `422` | Upload validation failure — **shown distinctly from other failure modes**: "Unsupported, unrecognized, or mismatched file type" or "Uploaded file is empty," rendered inline near the upload control, never merged into a generic "upload failed" | Not expected in practice beyond FastAPI's own query-param bounds |
| `413` | **Distinct from `422`** — file too large, with the exact configured limit in the message (`settings.MAX_DOCUMENT_SIZE_BYTES`, already human-readable-formattable client-side) | N/A |
| `500` | Storage/server failure — generic retryable `ErrorState`, distinguished from a validation failure (never implies the user's file was the problem) | Generic retryable `ErrorState` |
| Network failure | Generic retryable `ErrorState`, matching every other list/action screen in this codebase | Same |

For uploads specifically (§18's own explicit breakdown): **client
validation failure** (a pre-check catch, before any request is sent) →
inline, immediate, no network round trip; **backend validation failure**
(`422`/`413`) → inline near the upload control, backend's own message
verbatim; **authorization failure** (`404` on the parent Letter — in
practice unreachable from this UI, since the user is already viewing
an authorized Letter detail page, but defensively handled identically
to any other 404 if it somehow occurred, e.g. a Letter archived/
department-deactivated mid-session) → the same generic Letter-not-found
treatment; **network failure** → retryable, generic; **storage/server
failure** (`500`) → retryable, generic, distinct wording from a
validation failure so the user doesn't think their file was rejected
for content reasons.

---

## 18. Accessibility (RECOMMENDED — extends the Phase 5A-5D baseline, no new pattern)

**Document upload**: `<label>` associated with the file `<input>`;
visible text stating the accepted types (`.pdf, .jpg, .jpeg, .png,
.txt`) and the size limit ("up to 10 MB") near the control, not only
implied by a validation error after the fact; validation errors
`role="alert"`, associated via `aria-describedby`; upload-in-flight
state communicated via a disabled submit + `aria-busy`/a `role="status"`
loading indicator, matching `LetterFormPage`'s own submit-in-flight
pattern (Phase 5C).

**Document list**: semantic list/table markup (`<table>` with
`scope="col"` headers if tabular, matching `LetterTable`/Phase 5D's
`*Table` components' established convention); each download action a
real `<button>` with an accessible name that includes the filename
("Download {filename}," not a bare "Download" repeated identically on
every row); keyboard-operable by construction (a real `<button>`, no
`<div onClick>`).

**Notification bell**: a real `<button>` with an `aria-label` including
the current unread count ("Notifications, 3 unread" — RECOMMENDED,
updates as the count changes, not a static label with a visually-only
badge number); keyboard-operable (`Enter`/`Space`, native button
behavior); `aria-expanded` reflecting whether the panel is open
(§20's `aria-expanded` requirement, directly applicable here — the one
genuinely disclosure-pattern UI this phase introduces).

**Notification panel**: focus moves into the panel on open (RECOMMENDED:
to the panel container or its first interactive item, not necessarily
away from the bell if a lighter "focus stays put, panel is
`aria-live`-announced" pattern is preferred — `PROVISIONAL` exact
choice, not backend/security-constrained either way); `Escape` closes
it and returns focus to the bell button (the same restore-focus-on-
close discipline `ConfirmDialog`/`AdminTransferDialog` already
establish, Phase 5D); keyboard navigation between items (native
tab order through real `<button>`/`<a>` elements is sufficient — no
custom roving-tabindex arrow-key pattern is required by any existing
convention in this codebase, and adding one would be complexity beyond
what a short dropdown list needs).

**Notification items**: `is_read` state communicated via more than
color (§7.3 — text/visually-hidden prefix, not a bare color dot);
each item with a `letter_id` is a real, keyboard-operable link/button
whose accessible name states the destination clearly, not a bare
"View."

---

## 19. Responsive UX (RECOMMENDED — existing tokens/patterns only, no new mechanism)

**Letter detail document section**: the document list uses the same
horizontal-scroll-container pattern (`overflow-x: auto` on a fixed-
min-width inner table, `LetterTable.module.css`'s established
convention) if rendered as a table on narrow screens, or a simple
stacked-row layout if a lighter list (not table) markup is chosen
(`PROVISIONAL` — either is consistent with existing conventions,
neither is mandated). **Upload controls**: a native file input and a
button stack to full width on narrow viewports, matching
`LetterFormPage`'s existing single-column-below-tablet-breakpoint
pattern. **Notification dropdown**: RECOMMENDED a fixed or
viewport-relative max-width/max-height with internal scrolling on
narrow screens, anchored to the bell — no new CSS mechanism needed
beyond what `AdminTransferDialog`'s positioned-overlay pattern already
demonstrates (Phase 5D), adapted from a centered modal to a
corner-anchored dropdown. **No CSS/UI framework** — CSS Modules +
`styles/tokens.css` remain the only styling mechanism, unchanged.

---

## 20. Performance (RECOMMENDED — direct answers to §21's checklist)

* **Notification polling** — §11 (unread-count only, ~60s, paused when
  the tab is hidden).
* **Document list loading** — one request per Letter detail page view
  (`GET .../documents`), already naturally bounded since it's
  unpaginated and a single Letter is unlikely to accumulate an
  unbounded number of attachments; no additional caching layer
  RECOMMENDED for V1.
* **Blob downloads** — one request per explicit user click, never
  pre-fetched or pre-loaded speculatively (a Letter with several
  documents should not trigger several download requests just because
  the list rendered).
* **Large file handling** — bounded by the existing 10 MB ceiling
  (§1.3); no chunked/resumable upload is proposed (not supported by
  the backend, and out of scope per §28's own "do not solve backend
  gaps in the frontend" instruction).
* **Repeated Letter detail requests** — none introduced by this phase;
  `LetterDetailPage`'s own existing single `GET /letters/:id` fetch is
  unchanged, and the new Documents section makes its own separate
  `GET .../documents` call once per page load, not a duplicate Letter
  fetch.
* **Unnecessary notification API calls** — avoided by §11.3's
  visibility-based pause and by never polling the full list (§11.1).
* **No React Query, Redux, Zustand, or other caching framework** —
  confirmed nothing here needs one; every data need is a plain
  `useEffect` + `useState` fetch, the same pattern every Phase 5C/5D
  page already uses successfully.

---

## 21. Test plan (design only — no test code written this phase)

**Documents (RECOMMENDED ~20-24 tests)**: document list — success,
empty, `404` (Letter inaccessible) — 3; upload — client-side validation
(no file selected), success (list refreshes, new document appears),
`422` unsupported/mismatched type, `413` too large, `500` storage
failure, network failure — 6; download — success (blob triggers a
download, verified via a mocked `URL.createObjectURL`/anchor-click
rather than an actual browser download), `404` (Letter or Document not
found, both rendered identically), `401` (existing centralized handler
— confirm it still fires for a blob-typed request, not a new behavior
but worth one regression test given the different `responseType`),
network failure — 4; **no delete action exists** — a dedicated test
asserting no delete/remove control renders anywhere in the Documents
section, mirroring Phase 5C's own "no permanent-delete language" test
pattern for Letters — 1; classified/inaccessible document — a `404` on
a specific document (Document not found, distinct from Letter not
found) still renders the identical generic state — 1; accessibility —
labeled file input, accessible error association, accessible download
button names — 2-3.

**Notifications (RECOMMENDED ~22-26 tests)**: unread count — initial
fetch, poll updates it, paused when tab hidden (if implemented exactly
as designed) — 3; notification list (panel and/or full page) —
success, empty, error, pagination on the full page — 4; unread/read
rendering — visual + accessible distinction — 2; mark one read —
success updates the item and decrements the count, `404` on a
stale/foreign id — 2; mark all read — success clears the badge, a
already-zero-unread no-op — 2; notification isolation — a dedicated
test confirming no request ever includes a `recipient_user_id`-shaped
parameter regardless of what local state might contain (mirroring
Phase 5D's own payload-shape-assertion test pattern) — 1; `401`/other
errors — existing centralized handling regression — 2; navigation to
related Letter — a `letter_id`-present item navigates and (per §7.4's
chosen default) marks read; a `letter_id`-null item renders
non-interactively — 2-3; polling behavior — interval firing (using
fake timers, matching how this project would extend its existing
Vitest setup — no new test-infrastructure dependency) and pause/resume
on visibility change — 2-3.

**Integration (RECOMMENDED ~8-10 tests)**: `LetterDetailPage` +
Documents — the section renders real data end-to-end (not a mocked
sub-component boundary) — 2; `AppShell`/`Topbar` + `NotificationBell` —
the bell renders for every role, with no role-gating regression — 2;
notification → Letter navigation, full round trip through the actual
router (mirroring Phase 5C's own `routing.test.jsx` end-to-end pattern)
— 2; session expiration during a document download or notification
poll — confirms the existing centralized 401 handling still fires
correctly for these new request shapes (blob responseType, a
polling-interval-triggered request) — 2-3.

**Total RECOMMENDED range: roughly 50-60 new tests**, bringing the
suite from Phase 5D's 159 to somewhere in the **209-219** range. **Not
implemented this phase** — a planning estimate only.

---

## 22. Security threat review (direct answers to §24's 15 items)

| # | Threat | Existing backend mitigation | Frontend responsibility | Remaining risk |
|---|---|---|---|---|
| 1 | Document IDOR | `find_by_id_and_letter` scopes by both ids; Letter-first auth chain (§1.7/§6.2) | Never assume a previously-seen `document_id` is still valid; always go through the real request | None beyond the backend's own — the frontend adds nothing to defend and can remove nothing |
| 2 | Letter IDOR | `assert_letter_access`, unchanged since Phase 4B | Same as always — render backend results as-is | None new from this phase |
| 3 | Classified document leakage | Documents inherit the parent Letter's classification gate entirely (§6.3) | Render every 404 identically (§12) | None if §12 is followed; a distinguishing message would be the only way to introduce leakage here |
| 4 | Cross-department document access | Same chain as Letters (§6.4) | None — nothing to add | None |
| 5 | Download URL exposure | No signed/public URL exists (§4.3) | Never fabricate one; never suggest "share this link" UX | None — the capability simply doesn't exist to misuse |
| 6 | Token leakage | `apiClient`'s existing interceptor, unchanged | Route blob downloads through the same `apiClient` instance — never a second, ad hoc fetch that might mishandle the token | None if the existing service-layer convention is followed (§15) |
| 7 | Filename/path leakage | `storage_path` never serialized (§1.2); filenames sanitized before the `Content-Disposition` header (§1.4) | Never display a raw storage path (none is ever received, so nothing to accidentally render) | None |
| 8 | Unauthorized notification access | Recipient-scoped at every query (§8.1) | None — nothing to add | None |
| 9 | Notification recipient spoofing | No `recipient_user_id` field exists anywhere (§8.1) | Never attempt to add one to a request, even speculatively | None — structurally impossible |
| 10 | Notification → Letter existence leakage | The Letter's own 404 collapse applies identically when reached via a notification click (§10.4/§12) | Render the generic 404, never a "this letter used to exist" or similar message | None if §12 is followed |
| 11 | XSS through notification messages | Fixed server-authored template, one non-sensitive interpolated value (§2.3/§8.5) | Render via ordinary JSX text (auto-escaped); never `dangerouslySetInnerHTML` | None — confirmed safe by construction, but worth a lint-adjacent discipline (§8.5) during implementation |
| 12 | Malicious file uploads | Layered validation — extension, size, authoritative magic-byte signature (§1.3); explicitly **not** malware/antivirus scanning (out of scope, confirmed in `document_validation.py`'s own docstring and §28's explicit non-scope) | Client-side pre-check is a UX nicety only, never authoritative (§3.4) | **A structurally-valid PDF/JPEG/PNG/text file containing a genuine malware payload would pass both the backend's and any frontend check** — this is a confirmed, accepted, pre-existing V1 limitation (Phase 4D's own review), not something this phase changes or should attempt to change |
| 13 | Oversized files | Bounded read (`MAX_DOCUMENT_SIZE_BYTES + 1` bytes) before validation (§1.3) | Client-side size pre-check avoids wasting the user's upload bandwidth on a doomed request, never authoritative | None — the backend's own bound is what actually protects it |
| 14 | MIME spoofing | Client `Content-Type` never trusted; magic-byte sniff is authoritative (§1.3) | Never read or rely on `file.type` (the browser's own guess) for anything beyond an optional pre-check hint | None |
| 15 | Client-side authorization bypass | Every operation re-authorized server-side on every request (§6.1/§6.2) | Never gate a UI action on a locally-cached "can I do this" flag; always let the backend's own response decide (§6.2's explicit warning against exactly this) | None if this discipline is followed during implementation — the one place a future implementer could accidentally introduce risk, flagged explicitly here |

---

## 23. Business clarifications (genuinely open — not manufactured)

Verified each against the confirmed backend/existing docs before
listing — none of these can be resolved from source alone:

* **Whether mark-read should happen automatically on
  click-to-navigate, or only via an explicit action** (§7.4) — a
  RECOMMENDED default (automatic on click) is offered, but this is a
  genuine UX/business preference the backend is agnostic to (both are
  fully supported).
* **Notification retention** — nothing in the confirmed backend
  ever expires or archives a `Notification` row; whether old,
  long-since-read notifications should ever be hidden from the default
  view (vs. always showing full history, paginated) is open. No
  retention/expiry field exists to support automatic expiry even if
  wanted (`PENDING BACKEND API` if that's ever the actual requirement).
* **Notification polling frequency** — §11.2's 60-second RECOMMENDED
  default is a judgment call, not a confirmed requirement.
* **Whether a dedicated notification page is desired** beyond the
  dropdown — RECOMMENDED yes (§7.2, since pagination already exists
  to support one), but the business may prefer dropdown-only for V1
  simplicity; verify rather than assume the fuller build-out is wanted.
* **Whether document previews are required** (vs. download-only) —
  nothing in the confirmed backend contract implies or requires
  preview; `Content-Disposition: attachment` (§1.4) already forces a
  download by default for every accepted type, and building an inline
  preview would require the frontend to *override* that default
  behavior (fetch as blob, then render via `<iframe>`/`<img>` instead
  of triggering a save) — a real, additional feature this document does
  not assume is wanted.
* **Whether multiple simultaneous (concurrent, not just multi-select)
  uploads are desired** — §3.2's RECOMMENDED sequential default is a
  judgment call; nothing backend-side prevents concurrent requests, but
  nothing requires supporting them either.
* **Whether original filenames should be preserved on download** —
  **already CONFIRMED, not open**: the backend always serves the
  original filename via `Content-Disposition` (§1.4) — there is no
  scenario where it wouldn't be; this item from the brief's own list
  is resolved by source inspection, not left open.

---

## 24. Implementation sequence (RECOMMENDED — adjusted from the brief's own suggested structure based on what this review found)

The brief's suggested `5E.1 Documents → 5E.2 Notifications → 5E.3
Integration → 5E.4 Tests → 5E.5 Manual verification → 5E.6
Documentation → 5E.7 Commit` is sound and is not restructured — this
review found no reason to reorder it (unlike, say, Phase 5D's review
finding a genuine "simplest resource first" argument for reordering
Departments before Admins). Refined with the specific slices this
review's own findings imply:

1. **5E.1 — Document UI**: `documentService.js` (data layer first,
   matching every prior phase's own starting point) → `DocumentList` +
   inline upload form, wired into `LetterDetailPage`'s existing
   placeholder section → no new route needed.
2. **5E.2 — Notification UI**: `notificationService.js` →
   `NotificationBell` (unread count + poll) → `NotificationPanel` +
   `NotificationItem` (dropdown) → the `/app/notifications` full page
   (reusing `NotificationItem`) → wire `NotificationBell` into
   `Topbar`.
3. **5E.3 — Integration**: notification → Letter navigation; confirm
   the classified/inaccessible-resource 404 discipline holds
   end-to-end (§12); confirm role behavior is genuinely uniform (§13).
4. **5E.4 — Tests**: per §21, alongside each slice above rather than
   deferred to the end (every prior phase's own established practice).
5. **5E.5 — Manual verification**: against a real running backend +
   `lrs_dev`, matching every prior implementation phase's own practice
   — upload real files of each accepted type (and at least one
   rejected type/oversized file), download and confirm the browser
   actually saves with the original filename, exercise the poll/pause
   behavior by switching tabs, click a notification through to its
   Letter.
6. **5E.6 — Documentation**: this file's own implementation-record
   section (matching `administration-ui.md` §26's established
   pattern), plus the six project documentation files (§27).
7. **5E.7 — Commit checkpoint.**

---

## 25. Documentation (this phase's own footprint)

Created: `docs/architecture/document-notification-ui.md` (this file).
Updated: `README.md`, `docs/README.md`, `docs/PROJECT_STATUS.md`,
`docs/architecture/frontend.md`, `docs/architecture/overview.md` — all
recording that this review exists and what it covers, matching the
exact documentation-only footprint every prior review-only phase (4A,
4D's review, 4E's review, Phase 5's review, Phase 5D's review) has
left.

---

## 26. Explicit scope confirmation

This phase produced documentation only. It did **not** produce or
modify: any file under `frontend/src/`, any file under `backend/app/`
or `backend/alembic/`, any test file, any migration, any database
change, any configuration change, any package dependency change. It
did not implement OCR, antivirus scanning, cloud storage, public/signed
file URLs (none exist to build on), email/SMS/push notifications,
WebSockets, queues, Celery, Redis, an audit UI, a dashboard, exports,
document deletion, a document replacement endpoint, notification
recipient management, a notification-creation UI, or any new frontend
authorization logic. `git status` before and after this session is
identical except for this new documentation file and the five project
documentation updates listed in §25. Phase 5E implementation begins
only when explicitly instructed, per this project's standing rule that
phases are reviewed before the next begins.

---

## 27. Implementation record — IMPLEMENTED

Built directly on §1-26's own design — no new architecture decisions,
only the ones already recommended, built. Every item below is
IMPLEMENTED unless marked otherwise (CONFIRMED/PROVISIONAL/PENDING).

### Services (§15) — IMPLEMENTED

`services/documentService.js` — `list(letterId)`, `upload(letterId,
file, onUploadProgress)`, `download(letterId, documentId)` (returns
the raw `Blob`, `responseType: 'blob'` on the existing `apiClient`);
no `deleteDocument`/`replaceDocument`/`archiveDocument` exists, because
no such endpoint exists (§1.1, §5). `services/notificationService.js`
— `list(params)`, `unreadCount()`, `markRead(id)`, `markAllRead()`;
`list` forwards only `page`/`page_size` — no `is_read` parameter is
accepted or invented (§2.2, §23), and no function anywhere accepts or
sends a recipient identifier (§8, verified by the §31/security-review
grep below).

### Components (§14) — IMPLEMENTED, exactly the set §14 named

`components/DocumentUploadForm.jsx` — labeled file input, client-side
pre-checks (`utils/formValidation.js`'s new `validateDocumentFile`) for
missing file/unsupported extension/oversized file, explicitly labeled
as a UX convenience and not authoritative (§6.3); `onUploadProgress`
drives a real percentage where the browser can measure it, falling
back to an indeterminate "Uploading…" state otherwise — no WebSocket
or polling was added for this (§3.5's own explicit instruction).
`components/DocumentList.jsx` — reuses Phase 5D's
`DataTable.module.css`; renders only confirmed `DocumentResponse`
fields (`original_filename`, `file_size`, `mime_type`, `uploaded_at`)
plus one Download action per row; no Delete/Replace/Archive action
exists anywhere in this component (§6.1, verified by its own "never
renders a delete or replace action" test). Download is inlined in
`DocumentList` itself, not factored into a separate `DownloadButton`
(§14's own explicit recommendation against splitting a handler this
small).

`components/NotificationItem.jsx` — reused, unmodified, by both
`NotificationPanel` and `NotificationsPage` — the single source of
truth for one notification's read/unread visual state, message,
timestamp, and related-Letter link, per §14's explicit instruction not
to create a separate `NotificationList` unless real duplication
appeared (none did: both call sites map an array of `NotificationItem`
directly). Its Letter `<Link>` is structurally separate from its
"Mark as read" button — clicking through to the Letter never marks
the notification read (see the mark-read decision below).
`components/NotificationPanel.jsx` — the `Topbar` dropdown,
`page_size: 10`, `role="region"`, closes on `Escape` and on an
outside click, "View all notifications" link to `/app/notifications`.
`components/NotificationBell.jsx` — owns the unread-count polling
described below; `aria-expanded`/accessible name reflect open/closed
and current unread count.

No `UnreadBadge` was factored out — the count renders inline in
`NotificationBell`'s own accessible label and a small visual badge,
one small piece of markup, not worth a fifth component (§14's own
"unless real duplication appears" instruction, applied the same way
it was applied to `DownloadButton`/`NotificationList`).

### Pages and routes (§16) — IMPLEMENTED

| Route | Page | Notes |
|---|---|---|
| `/app/notifications` | `NotificationsPage` | replaces the Phase 5A `PlaceholderPage`; real pagination via the confirmed `page`/`total_pages` response fields, reusing Phase 5C's `Pagination` component — its first real notification-side use, since no Phase 5D resource had backend pagination |
| *(no route)* | Documents | integrated directly into `LetterDetailPage` — no `/app/letters/:id/documents` route exists or was added (§16's own explicit instruction) |

`Topbar.jsx` renders `NotificationBell` inside the existing
`.identity` block — the one existing `Topbar` instance, never a
second one; logout and identity display are unchanged and covered by
regression tests (`Topbar.test.jsx`, new this phase, since no such
test previously existed).

### The mark-read decision (§9, §23) — IMPLEMENTED per explicit override

§23 of this review left "mark read on navigate vs. explicit button
only" as a genuine `PENDING BUSINESS CLARIFICATION`, with a
PROVISIONAL lean toward mark-on-navigate. The implementation brief
explicitly overrode that lean: **explicit "Mark as read" only**.
Clicking a notification's related-Letter link never marks it read,
regardless of role or entry point (panel or full page); only the
dedicated button does, via `PATCH /notifications/{id}/read`. This is
implemented structurally, not just by convention — `NotificationItem`
accepts `onNavigate` (closes the panel on click, nothing else) and
`onMarkRead` (wired only to the button) as two separate props, so
there is no code path by which navigation alone could trigger a
mark-read call. The business question itself remains open; this
implementation records which behavior was actually built, not a new
resolution of the underlying policy question.

### Polling (§11) — IMPLEMENTED as PROVISIONAL, not silently finalized

`NotificationBell` polls `GET /notifications/unread-count` only —
never the full list — on a single `setInterval`, centralized as
`POLL_INTERVAL_MS = 60000` at the top of the file. Paused via the
`visibilitychange` event when the tab is hidden, with an immediate
refresh on becoming visible again; the interval is created and cleared
inside one `useEffect`, so it starts/stops with `NotificationBell`'s
own mount/unmount (which tracks the authenticated session, per
`AppShell`). The 60-second figure remains `PROVISIONAL`, exactly as
§11.2 flagged it — nothing about the implementation treats it as a
confirmed requirement.

### Upload/download behavior (§3, §4, §6) — IMPLEMENTED

Upload posts `multipart/form-data` with one `file` field, matching
§1.1 exactly; success appends the returned `DocumentResponse` to
`LetterDetailPage`'s in-memory document list directly from the upload
response, without a redundant `GET` (verified by test: `list` is
called exactly once per page load). Download requests
`responseType: 'blob'` through the existing authenticated `apiClient`
(bearer token attached the same way every other authenticated request
gets it — no second HTTP client, no unauthenticated `fetch`), creates
an object URL, triggers a synthetic anchor click using
`doc.original_filename` as the saved filename, and revokes the object
URL after a short delay. No storage path, physical filesystem path, or
signed/public URL is ever read from the response or rendered — there
is nothing to expose, since `DocumentResponse` carries none of those
fields (§1.2, confirmed unchanged this phase).

### Classified-resource handling (§12) — IMPLEMENTED: no frontend rule added

Neither `DocumentList`, `DocumentUploadForm`, nor
`LetterDetailPage`'s document-fetching logic contains any
classification-based branch. `fetchDocuments` runs only after
`LetterDetailPage`'s own `letterService.get` call already succeeded —
if the Letter itself 404s, no document request is ever made (verified
by test: "never fetches documents when the Letter itself is
inaccessible"); if a document-level request 404s, the existing generic
not-found handling renders unchanged, with no language distinguishing
"classified" from "does not exist" (verified by test, mirroring the
same assertion pattern `LetterDetailPage.test.jsx` already used for
Letter-level 404s since Phase 5C).

### Error handling (§17) — IMPLEMENTED, no new special cases

Both new services route every failure through the existing
`errorNormalization.js` unchanged; no 401/403/404/409/422/500/network
status is remapped to another status anywhere in the new code (grepped
this phase — see the security review below). Upload failures preserve
the selected file and allow retry; download failures render via the
existing `ErrorState`, scoped to the Documents section so a download
failure never clears or replaces the Letter detail already on screen.

### Tests (§21) — IMPLEMENTED

66 new tests (159 baseline → **225**): `utils/formValidation.test.js`
extended (+5, `validateDocumentFile`), `components/
DocumentUploadForm.test.jsx` (9), `components/DocumentList.test.jsx`
(7), `components/NotificationItem.test.jsx` (7), `components/
NotificationBell.test.jsx` (9), `components/NotificationPanel.test.jsx`
(9), `pages/NotificationsPage.test.jsx` (9), `layouts/Topbar.test.jsx`
(5, new file — no such test previously existed), plus 6 new
integration cases added to the existing `pages/
LetterDetailPage.test.jsx` and a `notificationService` mock added to
`routes/routing.test.jsx` (regression fix, not new coverage — see
below). Run 3 consecutive times against the final code, identical
**225 passed, 0 failed** each time.

Two issues were found and fixed during test authoring, not left as
unexplained failures: (1) `@testing-library/user-event`'s `upload()`
respects an `<input accept>` attribute and silently drops a
non-matching file before it reaches the component — the same
filtering a real browser's native file picker applies — so the
unsupported-file-type test uses `fireEvent.change` instead, simulating
the drag-and-drop path a real user could still use to bypass the
picker's own filter; (2) jsdom does not implement the `download`
attribute's non-navigating save behavior, so a real `.click()` on the
synthetic download anchor attempted an unsupported navigation and
logged stderr noise unrelated to the component itself —
`HTMLAnchorElement.prototype.click` is stubbed in that one test file.
Neither was a production-code bug.

### Regression (§21, §30 of the brief) — IMPLEMENTED, verified by test

Both `LetterDetailPage.test.jsx` and `routes/routing.test.jsx` needed a
new service mock (`documentService` and `notificationService`
respectively) because the real components under test now make network
calls that didn't exist before this phase — an unmocked
`documentService.list` inside a pre-existing `LetterDetailPage` test
and an unmocked `notificationService.unreadCount` inside
`routing.test.jsx`'s real `Topbar` render. Both were caught by running
the full suite before adding new Phase 5E-specific tests, and both are
regression-test fixes, not behavior changes.

### Validation

`npm run build` succeeds (176 modules, no errors). `npm run test` —
**225 passed**, 0 failed, run 3 consecutive times against the final
code with clean stderr output (no unexplained errors or warnings).
Backend regression: `pytest tests/` — **458 passed**, unaffected,
confirming zero backend impact. `git status` confirms no file under
`backend/app/`, `backend/alembic/`, or `backend/tests/` was touched.

### Security review (§22, verified this phase, not merely designed)

Grepped the full new/changed file set for `jwt`/`decode`/
`localStorage`/`recipient_user_id`/`dangerouslySetInnerHTML`/`DELETE`/
storage-path patterns/signed-or-public-URL patterns/hardcoded role
checks/hardcoded department IDs. Every match found is a comment or a
test name documenting the *absence* of the pattern (e.g.
"`recipient_user_id` parameter anywhere" in a doc comment explaining
none is sent, or a test literally named "never renders a delete or
replace action") — zero matches represent actual usage. No file
sends a recipient identifier of any kind; no file reads or renders a
storage path; no file constructs a signed or public document URL; no
file branches on `role` or `department_id` value; `dangerouslySetInnerHTML`
appears only inside a comment and a test name asserting it is never
used.

### Manual verification (§33 of the brief) — NOT PERFORMED

No backend or dev environment was running at any point in this
session (confirmed: no process was started, no database connection
was attempted). This report covers automated verification
(tests/build) only, per the brief's own instruction to report this
honestly rather than claim live verification that did not happen.

### Known limitations (post-implementation, restating this review's own findings — none newly discovered)

* **60-second unread-count polling interval** — `PROVISIONAL`, per
  §11.2; not backed by a confirmed business requirement.
* **Explicit-only mark-read behavior** — implements the brief's
  explicit override of this review's own PROVISIONAL lean; the
  underlying business question (§23) remains `PENDING BUSINESS
  CLARIFICATION`.
* **No document pagination** — `GET /letters/{id}/documents` returns
  the complete list with no `page`/`page_size` parameters (§1.1,
  unchanged); `DocumentList` renders the full result set, matching the
  backend contract exactly. `PENDING BACKEND API` if this becomes a
  problem at real volumes.
* **No `is_read` filter on the notification list** — confirmed absent
  from the backend contract (§2.2); `NotificationsPage` does not
  invent one. `PENDING BACKEND API`.
* **No document delete/replace/archive** — no such endpoint exists;
  none was added or worked around. `PENDING BACKEND API` if the
  business ever requires document lifecycle beyond upload.
