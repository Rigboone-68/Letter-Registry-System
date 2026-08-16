# LRS Backend

FastAPI service for the Letter Registry System. **Phase 1 foundation only** —
no models, endpoints, migrations, or business logic are implemented.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env               # fill in local values; never commit .env
uvicorn app.main:app --reload
```

Available now: `GET /health`, plus `/docs` and `/redoc`.

## Package layout

| Path | Responsibility |
|---|---|
| `app/main.py` | Application factory: logging, CORS, router mounting |
| `app/core/config.py` | Environment-based settings (single source of truth) |
| `app/core/security.py` | Placeholder — all hashing and token logic goes here |
| `app/core/logging.py` | Uniform log format and level |
| `app/database/base.py` | Declarative `Base`; models are imported here for Alembic |
| `app/database/session.py` | Lazy engine, session factory, `get_db()` dependency |
| `app/models/` | SQLAlchemy models (empty) |
| `app/schemas/` | Pydantic request/response contracts (empty) |
| `app/api/v1/endpoints/` | One router per resource (empty) |
| `app/services/` | Business logic and workflow (empty) |
| `app/repositories/` | The only layer that queries the database (empty) |
| `app/middleware/` | Request correlation and audit middleware (empty) |
| `app/utils/` | Pure helpers, no framework imports (empty) |

## Layering rules

* Endpoints call services. Endpoints do not build queries.
* Services call repositories. Services do not import routers.
* Repositories own the SQLAlchemy session and are the only ORM consumers.
* `utils` imports nothing from `api`, `services`, or `repositories`.

## Database & migrations

Alembic is configured but **contains no revisions**. `alembic.ini` leaves
`sqlalchemy.url` blank on purpose — `alembic/env.py` injects `DATABASE_URL`
from the environment at runtime.

Once models exist (Phase 2), import them in `app/database/base.py` so that
autogeneration can see them, then:

```bash
alembic revision --autogenerate -m "description"
alembic upgrade head
```

Do not run these commands in Phase 1; there is nothing to migrate.

## Configuration

Every setting is read from the environment via `app/core/config.py`. Required
keys are listed in `.env.example`. `SECRET_KEY` and `DATABASE_URL` have no
usable defaults — the application fails loudly rather than falling back to an
insecure value.

## Tests

```bash
pytest
```

`tests/unit` and `tests/integration` are scaffolded and currently empty.
