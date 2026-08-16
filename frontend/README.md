# LRS Frontend

React + Vite client for the Letter Registry System. **Phase 1 foundation only** —
no routing, authentication, layouts, or screens are implemented.

## Setup

```bash
npm install
cp .env.example .env.local     # optional
npm run dev
```

Runs on `http://localhost:5173`. Requests to `/api` are proxied to the FastAPI
backend on port 8000 (see `vite.config.js`), so no absolute backend URL is
baked into the source.

## Source layout

| Path | Responsibility |
|---|---|
| `src/main.jsx` | React entry point |
| `src/App.jsx` | Application shell; the router mounts here in Phase 2 |
| `src/assets/` | Images, icons, fonts |
| `src/components/` | Reusable presentational components |
| `src/layouts/` | Page shells (authenticated app layout, auth layout) |
| `src/pages/` | One component per screen |
| `src/routes/` | Route definitions and role-based guards |
| `src/services/` | Axios instance and per-resource API clients |
| `src/hooks/` | Reusable React hooks |
| `src/context/` | Context providers (current user, permissions) |
| `src/utils/` | Pure helpers |
| `src/constants/` | App-wide constants (`app.js`) |

The structure anticipates authentication, role-based navigation, dashboards,
the letter registry, user management, notifications, document viewing, and
administrative modules. None of these exist yet.

## Conventions

* Components never call Axios directly — all HTTP goes through `src/services/`.
* Only `VITE_`-prefixed variables reach the browser. Never put a secret in one.
* `@` resolves to `src/` (configured in `vite.config.js`).
