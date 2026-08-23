"""Audit-log generation (Phase 4E implementation).

Implements the architecture approved in
docs/architecture/audit-notifications.md: a single, reusable
service-level `record` call (§16/§19 — "endpoint → service →
repository", no event bus, no SQLAlchemy event listeners), append-only
(§5 — this module has no update/delete method, and neither does
`AuditLogRepository`), and mandatory/same-transaction (§20 — `record`
only `flush()`es; it deliberately never calls `commit()` or `rollback()`
itself, so a failure here surfaces inside whichever business operation's
own transaction is already open, and that operation's own `commit()`
call — not this one — is what actually fails the whole thing).

Callers pass targeted `old_values`/`new_values` field pairs, never a
full row snapshot (§8) — see each call site in `letter_service.py`,
`document_service.py`, etc. for what's actually included, and
`docs/architecture/audit-notifications.md` §8 for why a generic snapshot
was rejected.
"""

import uuid
from typing import Optional

from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog
from app.repositories.audit_log_repository import AuditLogRepository


class AuditService:
    def __init__(self, session: Session):
        self.session = session
        self.audit_logs = AuditLogRepository(session)

    def record(
        self,
        *,
        actor_id: Optional[uuid.UUID],
        action: str,
        entity_type: str,
        entity_id: Optional[uuid.UUID],
        old_values: Optional[dict] = None,
        new_values: Optional[dict] = None,
    ) -> AuditLog:
        """Record one audit event. `actor_id` is `None` only for a
        genuinely actor-less system action (none exists in this phase —
        every call site here passes a real authenticated caller's id);
        it is never inferred from the *target* of the action (the
        resource owner) — see docs/architecture/audit-notifications.md
        §6 for why actor and target must never be conflated.

        Flushes (not commits) so a write failure raises immediately,
        inside the caller's own transaction — the caller's own
        `session.commit()` is what actually makes this mandatory (§20):
        if this raises, that commit is never reached, and the whole
        operation rolls back with it."""
        entry = self.audit_logs.create(
            user_id=actor_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            old_values=old_values,
            new_values=new_values,
        )
        self.session.flush()
        return entry
