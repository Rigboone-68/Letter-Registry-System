"""designation master data

Phase 5H. Two changes, both additive, neither touching any existing row:

1. A new `designations` table — system-wide master data for a Letter's
   sender designation (e.g. "Section Officer"), managed by SYSTEM_ADMIN.
   Mirrors `categories`/`classifications`' own shape exactly (reuses the
   existing `active_status` enum type via `create_type=False`, never
   physically deleted), with one departure: `uq_designations_name_lower`
   is a case-insensitive functional unique index (the same technique
   `uq_users_email_lower` already uses), not a plain case-sensitive
   `UNIQUE` — see app/models/designation.py for why.

2. A new, **nullable** `letters.designation_id` FK, `ondelete=RESTRICT`
   (matching `category_id`/`classification_id`'s own `ondelete`
   behavior). Deliberately nullable with **no backfill** — every
   existing Letter keeps its current `sender_designation` text exactly
   as it is; `designation_id` is simply `NULL` for every row that
   existed before this migration. See
   docs/architecture/source-designation.md §8/§15 for the full
   historical-integrity reasoning: `sender_designation` (required text)
   is unchanged and remains the field every existing Letter and every
   old API client already depends on; `designation_id` is a new,
   optional structured reference going forward.

Revision ID: 323ccfde77f4
Revises: 9fa970ffa560
Create Date: 2026-08-26 23:05:36.527896
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "323ccfde77f4"
down_revision: Union[str, None] = "9fa970ffa560"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Reuses the existing `active_status` PostgreSQL enum type — `create_type=False`
# stops SQLAlchemy from re-issuing `CREATE TYPE` for a type the baseline
# migration (3da4b7ee8167) already created and every other reference-data
# table already shares.
active_status_enum = postgresql.ENUM(
    "ACTIVE", "INACTIVE", name="active_status", create_type=False
)

_DESIGNATION_FK = "letters_designation_id_fkey"


def upgrade() -> None:
    op.create_table(
        "designations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("status", active_status_enum, nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_designations_status", "designations", ["status"])
    op.create_index(
        "uq_designations_name_lower", "designations", [sa.text("lower(name)")], unique=True
    )

    op.add_column(
        "letters", sa.Column("designation_id", postgresql.UUID(as_uuid=True), nullable=True)
    )
    op.create_index("ix_letters_designation_id", "letters", ["designation_id"])
    op.create_foreign_key(
        _DESIGNATION_FK,
        "letters",
        "designations",
        ["designation_id"],
        ["id"],
        ondelete="RESTRICT",
    )


def downgrade() -> None:
    op.drop_constraint(_DESIGNATION_FK, "letters", type_="foreignkey")
    op.drop_index("ix_letters_designation_id", table_name="letters")
    op.drop_column("letters", "designation_id")

    op.drop_index("uq_designations_name_lower", table_name="designations")
    op.drop_index("ix_designations_status", table_name="designations")
    op.drop_table("designations")
