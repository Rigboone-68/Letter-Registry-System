"""Endpoint routers for API v1.

One module per resource, each exposing an APIRouter that the v1
aggregate router (app/api/v1/router.py) includes: auth, departments,
admins, users, categories, classifications, letters, documents (Phase
4D — nested under /letters/{letter_id}/documents). Notifications remain
a future module.
"""
