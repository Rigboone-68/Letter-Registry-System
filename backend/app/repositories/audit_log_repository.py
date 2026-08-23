"""Data access for `AuditLog` rows — the only code that queries
`AuditLog`.

Insert-only, by design (Phase 4E, docs/architecture/audit-notifications.md
§5): no `update`/`delete` method exists here, and none should ever be
added — an audit trail that could be edited or removed through this
codebase's own data-access layer would defeat the append-only guarantee
the architecture review concluded was CRITICAL.
"""

import uuid
from typing import Optional

from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog


class AuditLogRepository:
    def __init__(self, session: Session):
        self.session = session

    def create(
        self,
        *,
        user_id: Optional[uuid.UUID],
        action: str,
        entity_type: str,
        entity_id: Optional[uuid.UUID],
        old_values: Optional[dict] = None,
        new_values: Optional[dict] = None,
    ) -> AuditLog:
        entry = AuditLog(
            user_id=user_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            old_values=old_values,
            new_values=new_values,
        )
        self.session.add(entry)
        return entry
