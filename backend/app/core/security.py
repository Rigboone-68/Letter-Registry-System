"""Centralized security primitives.

PHASE 1 — STRUCTURAL PLACEHOLDER ONLY.

This module is the single place where password hashing and token handling
will live. Nothing is implemented in this phase by design; the file exists so
that later phases have one obvious home for these concerns and no other layer
grows its own copy.

Planned responsibilities (Phase 2+):
  * password hashing and verification
  * access-token creation and decoding (JWT, local signing key only)
  * token payload validation helpers

Deliberately excluded: any external or cloud identity provider. LRS runs on a
private government intranet and must authenticate entirely on its own.
"""

from app.core.config import settings

__all__ = ["settings"]
