# Architecture Documentation

Planned contents:

* `overview.md` — layered architecture and dependency rules
* `deployment.md` — intranet deployment topology (no internet dependency)
* `security.md` — authentication, RBAC model, audit requirements
* `decisions/` — architecture decision records (ADRs)

## Layering rule (enforced from Phase 1)

```
Frontend → API (app/api) → Services (app/services) → Repositories (app/repositories) → PostgreSQL
```

Dependencies point downward only. The API layer never touches a SQLAlchemy
session directly; repositories never import services or routers. Document
storage is reached through a dedicated service and never through the ORM.
