"""Response contracts for `LetterDocument` metadata.

No `storage_path` field exists on `DocumentResponse` — not merely
unselected. This is `LetterDocument`'s direct equivalent of
`UserPublic` never carrying `password_hash`: the internal filesystem
location is never serialized into any API response, so there is no
absolute path, no directory structure, and no implementation detail for
a client to learn even by accident. See
docs/architecture/document-management.md §24.

There is no `DocumentCreate` schema — upload is a multipart file field
plus an implicit `letter_id` from the URL path
(`app/api/v1/endpoints/documents.py`), not a JSON body.
"""

import uuid
from datetime import datetime
from typing import List

from pydantic import BaseModel, ConfigDict


class DocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    letter_id: uuid.UUID
    original_filename: str
    mime_type: str
    file_size: int
    uploaded_by: uuid.UUID
    uploaded_at: datetime


class DocumentListResponse(BaseModel):
    """A thin envelope, matching every other list response in this
    project (`{"items": [...], "total": N}`-shaped) rather than a bare
    array — see docs/architecture/document-management.md §24."""

    items: List[DocumentResponse]
    total: int
