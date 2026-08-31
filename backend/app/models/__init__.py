"""SQLAlchemy ORM models.

PHASE 2: database architecture and core models. Every model must inherit
from `app.database.base.Base` and be imported here. `app.database.base`
itself does NOT import this package (see its docstring) — code that needs
every model registered on `Base.metadata` imports this package explicitly
(e.g. `import app.models`), in addition to importing `Base`.

No API endpoints, services, or repositories consume these models yet — this
package defines the schema only.
"""

from app.models.audit_log import AuditLog
from app.models.category import Category
from app.models.classification import Classification
from app.models.department import Department
from app.models.designation import Designation
from app.models.letter import Letter
from app.models.letter_document import LetterDocument
from app.models.letter_sequence import LetterNumberSequence
from app.models.notification import Notification
from app.models.user import User
from app.models.user_authorization import UserAuthorization

__all__ = [
    "AuditLog",
    "Category",
    "Classification",
    "Department",
    "Designation",
    "Letter",
    "LetterDocument",
    "LetterNumberSequence",
    "Notification",
    "User",
    "UserAuthorization",
]
