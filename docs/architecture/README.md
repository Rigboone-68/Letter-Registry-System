# Architecture Documentation

* [`overview.md`](overview.md) — role hierarchy (System Admin / Admin /
  User), department isolation, and what's implemented vs. deferred as of
  Phase 2.
* `deployment.md` — not yet created (intranet deployment topology; no
  internet dependency).
* `security.md` — not yet created (authentication, RBAC model, audit
  requirements — all deferred past Phase 2, see `overview.md` §4).
* `decisions/` — not yet created (architecture decision records).

## Layering rule (enforced from Phase 1)

```
Frontend → API (app/api) → Services (app/services) → Repositories (app/repositories) → PostgreSQL
```

Dependencies point downward only. The API layer never touches a SQLAlchemy
session directly; repositories never import services or routers. Document
storage is reached through a dedicated service and never through the ORM.
