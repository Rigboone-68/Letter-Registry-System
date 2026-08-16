"""Repository / data-access layer.

Repositories are the only code that talks to SQLAlchemy sessions. Keeping
queries here means services and endpoints stay free of ORM details and the
persistence layer can be tested in isolation.

PHASE 1: empty by design.
"""
