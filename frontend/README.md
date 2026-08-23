# LRS Frontend

React + Vite client for the Letter Registry System. **Phase 5B:
Authentication & Account UX — implemented**, on top of Phase 5A's
foundation and Phase 5's own architecture/UX review
(`docs/architecture/frontend.md`). Login, signup, pending-approval and
deactivated-account states, session restoration, logout, and every
supporting redirect/validation/accessibility/error-handling behavior
around them now exist and work against the real backend. **No business
feature screens exist yet** — Letters, Documents, Notifications, and
every administrative screen are still placeholders; see
`docs/architecture/frontend.md` §32 for the recommended build-out
sequence.

## Setup

```bash
npm install
cp .env.example .env.local     # optional — see "Configuration" below
npm run dev
```

Runs on `http://localhost:5173`. Requests to `/api` are proxied to the FastAPI
backend on port 8000 (see `vite.config.js`), so no absolute backend URL is
baked into the source.

```bash
npm run build      # production build (vite build)
npm run preview    # preview the production build locally
npm run test       # run the test suite once (vitest run)
npm run test:watch # run the test suite in watch mode
```

## Configuration

Only `VITE_`-prefixed variables are exposed to the browser bundle — never
place a secret in one. `.env.example` documents the two currently used:

| Variable | Purpose |
|---|---|
| `VITE_APP_NAME` | Display name shown in the Topbar |
| `VITE_API_BASE_URL` | Backend API base URL (default `/api/v1`, proxied in dev by `vite.config.js`) |

`.env.local` (git-ignored, like every `.env*` file except `.env.example`
— see the root `.gitignore`) is where a real local override would go;
neither variable is a secret, so committing `.env.example` with its
current placeholder values is safe.

## Authentication & token handling

`src/context/AuthContext.jsx` is the single authentication state
mechanism (`status`: `'loading' | 'authenticated' | 'unauthenticated'`,
plus `user`, always the `UserPublic` object most recently returned by
the backend — never decoded from the JWT client-side). On app start it
restores a session by validating any stored token against
`GET /auth/me` before rendering any protected route (`src/routes/ProtectedRoute.jsx`),
which avoids an authentication flicker.

**Token storage is isolated to one module**, `src/services/tokenStorage.js`
— nothing else reads/writes it directly. **V1 approach: `localStorage`.**
This is a **documented, PROVISIONAL placeholder**, not a settled
decision — `docs/architecture/frontend.md` §28 flags the exact storage
strategy as a pending deployment decision (a shared/kiosk workstation
would favor `sessionStorage` instead; a cookie-based approach would
require a backend change this project has not made, since the backend
issues a bearer token in a JSON body, not a cookie). Changing the
strategy later means editing only `tokenStorage.js`.

There is no logout endpoint on the backend (unchanged since Phase 3A —
no refresh-token/revocation mechanism exists) — logout is purely
client-side: `AuthContext.logout()` clears the stored token and cached
user, nothing more. **An already-issued JWT is not revoked server-side
by logging out** — it simply expires naturally later; this is the
accepted V1 architecture, not a defect.

A network failure while restoring a session (the server can't be
reached) is treated differently from a rejected token: the stored
credential is **not** discarded (it might still be valid), `status`
becomes `'unauthenticated'` so no protected content is ever shown, and
`LoginPage` displays a retry-capable banner (`restoreError` /
`retryRestoreSession` on `AuthContext`) instead of silently demanding a
fresh login.

## Authentication & account UX (Phase 5B)

* **Login** (`pages/LoginPage.jsx`) — email + password, client-side
  required/format validation with `aria-invalid`/`aria-describedby` on
  each field, a disabled submit button with a loading label while the
  request is in flight. A `401` always shows the backend's own generic
  "Incorrect email or password." — this page never distinguishes a
  nonexistent account from a wrong password. A `403` for a pending or
  deactivated account renders a dedicated notice component instead of a
  generic error (see below).
* **Signup** (`pages/SignupPage.jsx`) — `full_name`/`email`/`password`/
  `password_confirm` only; the backend's `SignupRequest` schema has
  `extra="forbid"` and no `role`/`department`/`status` field, so there is
  nothing on this form for one to bind to even accidentally (verified by
  a test asserting the exact payload shape sent to the backend). A
  successful signup never assumes the account is active — it always
  shows the pending-approval notice, since every new account starts
  `PENDING_APPROVAL`.
* **Pending approval** (`components/PendingApprovalNotice.jsx`) — reused
  in two places: right after signup, and after a login attempt against a
  `PENDING_APPROVAL` account. States only what the backend confirms —
  no approval timeline, no email-notification promise, no administrator
  contact information is invented.
* **Deactivated account** (`components/DeactivatedAccountNotice.jsx`) —
  shown only after a login attempt against a deactivated account (the
  backend only distinguishes this case at `POST /auth/login`; a
  mid-session deactivation instead surfaces as a generic `401`, handled
  by the existing centralized 401 handler). States the account is
  disabled and its record has not been deleted; exposes no
  administrative detail and no reactivation action (that is an
  administrative, backend-only operation).
* **Redirects** — an authenticated user visiting `/login` or `/signup`
  is redirected into `/app`; an unauthenticated user visiting `/app/*`
  is redirected to `/login` (unchanged, `ProtectedRoute`). The two
  checks are mutually exclusive states of the same `status` value, so no
  redirect loop is possible.
* **Validation** — lightweight, dependency-free (`utils/formValidation.js`):
  required fields, email format, password-confirmation match. Never a
  replacement for backend validation, which remains authoritative; a
  `422` field error from the backend is displayed the same way a
  client-side one is.

## Source layout

| Path | Responsibility |
|---|---|
| `src/main.jsx` | React entry point; imports the global stylesheet/tokens |
| `src/App.jsx` | Provides `AuthProvider` and mounts the router |
| `src/routes/` | `router` (route tree), `ProtectedRoute` (authentication guard), `RoleGuard` (role-based navigation convenience, not security) |
| `src/context/` | `AuthContext` — the one authentication state mechanism |
| `src/services/` | `apiClient.js` (the one Axios instance), `authService.js` (login/signup/me), `tokenStorage.js` (isolated token access), `errorNormalization.js` |
| `src/navigation/` | `navigationConfig.js` — role → nav item mapping, data only |
| `src/layouts/` | `AppShell`/`Sidebar`/`Topbar` — the authenticated app's chrome |
| `src/pages/` | `LoginPage`, `SignupPage` (full auth/account UX, Phase 5B), `RootRedirect`, `PlaceholderPage` (every unbuilt business feature screen renders this generic placeholder for now) |
| `src/components/` | `LoadingState`/`ErrorState`/`EmptyState` — reusable primitives; `PendingApprovalNotice`/`DeactivatedAccountNotice` — reusable account-state notices used by `LoginPage`/`SignupPage` |
| `src/styles/` | `tokens.css` (design tokens — colors/spacing/typography/radius/shadow/breakpoints), `global.css` (minimal reset) |
| `src/test/` | `setup.js` — Vitest/Testing-Library wiring, shared by every test file |
| `src/utils/` | `formValidation.js` — lightweight, dependency-free auth-form validation |
| `src/assets/`, `src/hooks/`, `src/constants/` | Still mostly placeholders (`constants/app.js` has real content); populated as feature work needs them |

## Conventions

* Components never call Axios directly — all HTTP goes through
  `src/services/apiClient.js` and the per-resource service modules built
  on top of it (`authService.js` today; one per backend resource as
  feature work adds them).
* Only `VITE_`-prefixed variables reach the browser. Never put a secret
  in one.
* `@` resolves to `src/` (configured in `vite.config.js`).
* Component-scoped styles use CSS Modules (`*.module.css`, native to
  Vite — no new dependency); shared values come from `src/styles/tokens.css`
  via `var(--token-name)`. No CSS/UI framework is installed — see
  `docs/architecture/frontend.md` §26 for why.
* Every backend response shape is trusted as the source of truth for
  authorization (role/department/status) — the frontend never computes
  or caches a permission decision independently. See
  `docs/architecture/frontend.md` §22/§28.

## Testing

Vitest + React Testing Library (`npm run test`). 44 tests across 8
files: `services/errorNormalization.test.js` (both backend error-body
shapes, network failure, unexpected shape), `navigation/navigationConfig.test.js`
(per-role nav sets), `utils/formValidation.test.js` (client-side field
validation), `routes/ProtectedRoute.test.jsx` (the three auth states),
`routes/routing.test.jsx` (logout → redirect to `/login`, end to end),
`context/AuthContext.test.jsx` (session restore including a network
failure and its retry, login, logout, an invalid stored token),
`pages/LoginPage.test.jsx` (success, invalid credentials, pending
account, deactivated account, validation, loading state, network
failure, accessible field errors, already-authenticated redirect),
`pages/SignupPage.test.jsx` (success/pending-approval state, validation,
password mismatch, duplicate/not-authorized backend errors, the exact
payload shape sent to the backend, already-authenticated redirect) — the
API layer (`authService`/`tokenStorage`) is mocked in every test; none
of these tests requires a running backend.

## Known limitations

* `react-router-dom@^6.24.0` and the `esbuild`/`vite` toolchain both have
  `npm audit`-reported advisories with no non-breaking fix available in
  their currently pinned major versions (a v7 React Router upgrade and a
  Vite 8 upgrade would each be a breaking stack change, out of scope for
  this phase — "use the existing stack, do not replace it"). Documented
  here rather than silently upgraded or silently ignored.
* React Router logs two harmless "future flag" deprecation warnings
  during tests (`v7_startTransition`, `v7_relativeSplatPath`) — informational
  only, not a functional issue; not addressed this phase.

The structure anticipates the full feature set (Letters, Documents,
Notifications, Administration) — see `docs/architecture/frontend.md` for
the complete design and `docs/PROJECT_STATUS.md` for what's built versus
still pending.
