"""admin management: user_authorizations purpose

Phase 3B.3. Adds one column to an existing table — no new table, and the
existing Phase 3A/3B.x migrations are untouched (frozen snapshots, per the
established convention in this project — see the baseline migration's own
docstring).

`user_authorizations.purpose` (new `authorization_purpose` enum: `USER` |
`ADMIN`) says what role a given authorization's eventual signup produces —
see app/models/user_authorization.py for why this extends the existing
table rather than introducing a parallel `AdminAuthorization` one.

Backfill-safe by construction, per the brief's explicit instruction to be
careful with any existing rows: the column is added nullable, every
existing row (if any) is backfilled to `USER` — the only purpose that has
ever existed before this phase, since ADMIN authorizations did not exist
until this migration's own accompanying application code — and only then
is the column tightened to `NOT NULL`. This is the standard, safe pattern
for adding a required column to a table that may not be empty; it works
identically whether the table currently has zero rows (true for every
environment this was developed against) or many.

Revision ID: a223396c9eac
Revises: e8a5cea2ccc6
Create Date: 2026-08-22 16:42:31.688745
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "a223396c9eac"
down_revision: Union[str, None] = "e8a5cea2ccc6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


authorization_purpose_enum = postgresql.ENUM(
    "USER", "ADMIN", name="authorization_purpose", create_type=False
)


def upgrade() -> None:
    bind = op.get_bind()
    authorization_purpose_enum.create(bind, checkfirst=True)

    op.add_column(
        "user_authorizations",
        sa.Column("purpose", authorization_purpose_enum, nullable=True),
    )
    op.execute("UPDATE user_authorizations SET purpose = 'USER' WHERE purpose IS NULL")
    op.alter_column("user_authorizations", "purpose", nullable=False)

    op.create_index(
        "ix_user_authorizations_purpose", "user_authorizations", ["purpose"]
    )


def downgrade() -> None:
    op.drop_index("ix_user_authorizations_purpose", table_name="user_authorizations")
    op.drop_column("user_authorizations", "purpose")

    bind = op.get_bind()
    authorization_purpose_enum.drop(bind, checkfirst=True)
