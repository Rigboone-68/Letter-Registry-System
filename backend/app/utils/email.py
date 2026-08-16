"""Email normalization.

A single, reused definition of "the same email" for LRS: trimmed of
surrounding whitespace and lowercased. This must match the SQL-side
comparison used by the database's own case-insensitive uniqueness index
(`lower(email)` on `users`, see docs/database/schema.md) — using this
function everywhere an email is looked up or stored keeps the Python side
and the database side in agreement.
"""


def normalize_email(email: str) -> str:
    return email.strip().lower()
