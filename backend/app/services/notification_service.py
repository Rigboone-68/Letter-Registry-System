"""Notification generation and retrieval (Phase 4E implementation).

Implements the architecture approved in
docs/architecture/audit-notifications.md: the one CONFIRMED V1 trigger
("a letter was registered" — §2/§12) with a PROVISIONAL recipient
strategy (§13 — the recipient department's Admins; explicitly not a
confirmed business answer), best-effort generation via a database
`SAVEPOINT` so a failure here can never abort the Letter transaction it
rides alongside (§20/§21), and strict recipient isolation on every read
(§17/§18 — every query here is scoped to the calling user's own id,
never a client-supplied `recipient_user_id`).

`message` text is deliberately generic — a reference number, never
Letter subject/content/classification details (§14/§15): a later
classification change cannot retroactively scrub text already sent to a
recipient, so nothing sensitive is ever put there in the first place.
"""

import uuid
from typing import List, Tuple

from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.models.enums import UserStatus
from app.models.letter import Letter
from app.models.notification import Notification
from app.models.user import User
from app.repositories.notification_repository import NotificationRepository
from app.repositories.user_repository import UserRepository
from app.services.exceptions import NotificationNotFoundError

logger = get_logger(__name__)

MAX_PAGE_SIZE = 100
DEFAULT_PAGE_SIZE = 25


class NotificationService:
    def __init__(self, session: Session):
        self.session = session
        self.notifications = NotificationRepository(session)
        self.users = UserRepository(session)

    # --- Generation (best-effort — §20/§21) -----------------------------------

    def notify_letter_registered(self, letter: Letter) -> None:
        """The one CONFIRMED V1 trigger. Recipient strategy — the
        recipient department's ACTIVE Admins — is an explicit,
        documented PROVISIONAL default
        (docs/architecture/audit-notifications.md §13), not a confirmed
        business answer; Admins are never narrowed by the
        classified-access boundary (`assert_letter_access`), so this
        selection is already correctly filtered with no extra
        authorization check needed (§14/§15).

        Wrapped in its own SAVEPOINT: a failure here rolls back only
        this nested transaction, never the caller's outer transaction
        (the Letter creation and its mandatory audit row) — the same
        mechanism `tests/conftest.py`'s `db_session` fixture already
        uses for an analogous reason. Never raises — a notification
        failure must not fail Letter registration (§20)."""
        try:
            with self.session.begin_nested():
                recipients = self.users.list_admins(
                    department_id=letter.recipient_department_id,
                    status_filter=UserStatus.ACTIVE,
                )
                message = (
                    f"A new letter (reference: {letter.reference_number}) "
                    "has been registered in your department."
                )
                for recipient in recipients:
                    self.notifications.create(
                        recipient_user_id=recipient.id,
                        letter_id=letter.id,
                        notification_type="LETTER_REGISTERED",
                        message=message,
                    )
                self.session.flush()
        except Exception as exc:  # noqa: BLE001 - best-effort by design, see module docstring
            logger.warning(
                "Failed to create LETTER_REGISTERED notification(s) for letter %s: %s",
                letter.id,
                exc,
            )

    def notify_letter_dispatched(self, letter: Letter) -> None:
        """Phase 6A (docs/architecture/correspondence.md §7) — a new,
        *additional* trigger for an `OUTGOING` letter, notifying the
        dispatch (destination) department rather than the recording one.
        Same provisional recipient strategy as `notify_letter_registered`
        (that department's ACTIVE Admins), same best-effort SAVEPOINT
        pattern, same message-security discipline (a reference number and
        the sending department's name — never subject, sender detail, or
        classification)."""
        try:
            with self.session.begin_nested():
                recipients = self.users.list_admins(
                    department_id=letter.dispatch_department_id,
                    status_filter=UserStatus.ACTIVE,
                )
                message = (
                    f"New correspondence (reference: {letter.reference_number}) "
                    f"has been dispatched to your department from "
                    f"{letter.recipient_department.name}."
                )
                for recipient in recipients:
                    self.notifications.create(
                        recipient_user_id=recipient.id,
                        letter_id=letter.id,
                        notification_type="LETTER_DISPATCHED",
                        message=message,
                    )
                self.session.flush()
        except Exception as exc:  # noqa: BLE001 - best-effort by design, see module docstring
            logger.warning(
                "Failed to create LETTER_DISPATCHED notification(s) for letter %s: %s",
                letter.id,
                exc,
            )

    def notify_correspondence_recorded(self, *, outgoing_letter: Letter, incoming_letter: Letter) -> None:
        """Phase 6A (docs/architecture/correspondence.md §7) — the
        receipt-confirmation trigger: once the dispatch destination
        department records its own incoming copy, the *originating*
        (dispatching) department's ACTIVE Admins are notified. Recipient
        department is `outgoing_letter.recipient_department_id` — the
        department that owns/recorded the outgoing letter — never a
        client-supplied id. Same best-effort SAVEPOINT pattern and
        message-security discipline as every other trigger here.

        `letter_id` is deliberately `outgoing_letter.id`, not
        `incoming_letter.id` — the recipient of *this* notification
        (the dispatching department) can access the outgoing letter it
        already owns, but has no access to the destination department's
        own incoming letter (`assert_letter_access` would 404 it); a
        notification must never link its own recipient to a letter that
        recipient can't open. See docs/architecture/correspondence.md
        §7 for the same reasoning applied to `notify_letter_dispatched`.
        """
        try:
            with self.session.begin_nested():
                recipients = self.users.list_admins(
                    department_id=outgoing_letter.recipient_department_id,
                    status_filter=UserStatus.ACTIVE,
                )
                message = (
                    f"Your correspondence (reference: {outgoing_letter.reference_number}) "
                    f"has been received and recorded by "
                    f"{incoming_letter.recipient_department.name}."
                )
                for recipient in recipients:
                    self.notifications.create(
                        recipient_user_id=recipient.id,
                        letter_id=outgoing_letter.id,
                        notification_type="LETTER_RECORDED",
                        message=message,
                    )
                self.session.flush()
        except Exception as exc:  # noqa: BLE001 - best-effort by design, see module docstring
            logger.warning(
                "Failed to create LETTER_RECORDED notification(s) for outgoing letter %s: %s",
                outgoing_letter.id,
                exc,
            )

    # --- Retrieval — always scoped to the caller (§17/§18) --------------------

    def list_notifications(
        self, *, user: User, page: int = 1, page_size: int = DEFAULT_PAGE_SIZE
    ) -> Tuple[List[Notification], int]:
        return self.notifications.list_by_recipient(user.id, page=page, page_size=page_size)

    def unread_count(self, *, user: User) -> int:
        return self.notifications.count_unread(user.id)

    def mark_read(self, notification_id: uuid.UUID, *, user: User) -> Notification:
        """Idempotent — marking an already-read notification read again
        just returns its current state, the same convention every other
        "lock things down" action in this project uses."""
        notification = self.notifications.find_by_id_and_recipient(notification_id, user.id)
        if notification is None:
            raise NotificationNotFoundError()
        if not notification.is_read:
            self.notifications.mark_read(notification)
            self.session.commit()
            self.session.refresh(notification)
        return notification

    def mark_all_read(self, *, user: User) -> int:
        """Returns the number of notifications actually flipped to read
        (0 if the caller had none unread)."""
        count = self.notifications.mark_all_read(user.id)
        self.session.commit()
        return count
