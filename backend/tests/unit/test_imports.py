"""Regression tests for the Phase 2 self-review's circular-import finding.

`app/database/base.py` used to import `app.models` at its own bottom "so
Alembic can see every model", while every model module imports `Base` from
`app.database.base`. That created a genuine, order-dependent circular
import: `from app.models import User` (or `from app.models.user import
User`) as the *first* touch of either module in a fresh interpreter raised
`ImportError: cannot import name 'X' from partially initialized module
'app.models'`. It only "worked" in this repository because every existing
entry point (`tests/conftest.py`, `alembic/env.py`) happened to import
`app.database.base` before ever touching `app.models`.

The fix (see `app/database/base.py`'s docstring) makes `Base` a leaf module
with no knowledge of `app.models`; `app.models` depends on it one-way.
Consumers that need every model registered on `Base.metadata` (Alembic,
`tests/conftest.py`) import `app.models` themselves.

These tests run each import in a genuinely fresh Python subprocess — a
same-process import would be contaminated by whatever conftest.py or an
earlier test already imported, and would not reproduce the bug this guards
against. No database is needed, which is why these live in `tests/unit`
rather than `tests/integration`.
"""

import subprocess
import sys

# Run from backend/ regardless of pytest's invocation directory, so `app` is
# importable without relying on an already-configured sys.path or PYTHONPATH.
BACKEND_ROOT = __import__("pathlib").Path(__file__).resolve().parents[2]


def _run_fresh(code: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-c", code],
        cwd=BACKEND_ROOT,
        capture_output=True,
        text=True,
        timeout=30,
    )


def test_from_app_models_import_user_in_fresh_interpreter():
    result = _run_fresh("from app.models import User")
    assert result.returncode == 0, result.stderr


def test_from_app_models_user_submodule_import_in_fresh_interpreter():
    result = _run_fresh("from app.models.user import User")
    assert result.returncode == 0, result.stderr


def test_from_app_database_base_then_app_models_in_fresh_interpreter():
    result = _run_fresh(
        "from app.database.base import Base\nfrom app.models import User"
    )
    assert result.returncode == 0, result.stderr


def test_app_models_import_alone_registers_full_metadata():
    """`import app.models` (with no direct `Base` import at all) must still
    leave every table registered on Base.metadata once both are imported —
    proves app.models doesn't need to be entered via app.database.base."""
    result = _run_fresh(
        "import app.models\n"
        "from app.database.base import Base\n"
        "names = sorted(Base.metadata.tables.keys())\n"
        "expected = ['audit_logs', 'categories', 'classifications', 'departments', "
        "'designations', 'letter_documents', 'letter_number_sequences', 'letters', "
        "'notifications', 'user_authorizations', 'users']\n"
        "assert names == expected, names\n"
    )
    assert result.returncode == 0, result.stderr
