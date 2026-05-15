"""Typed exceptions for the accounts service layer (M1 D4).

Pattern mirrors :mod:`apps.platform.organizations.services.exceptions`:

* ``LookupError`` subclasses for missing records.
* ``ValueError`` subclasses for business-rule violations.

These are part of the public service contract — caller code branches
on them.
"""

from __future__ import annotations

from uuid import UUID


class UserNotFoundError(LookupError):
    """Raised when a service references a User id that does not exist."""

    def __init__(self, user_id: UUID | str) -> None:
        super().__init__(f"User with id {user_id!r} does not exist.")
        self.user_id = user_id


class UserAlreadyExistsError(ValueError):
    """Raised when registering a local user with an email that already exists.

    The collision is detected before any DB write; the caller can branch
    cleanly between "send password reset" vs. "first-time registration".
    """

    def __init__(self, email: str) -> None:
        super().__init__(f"A user with email {email!r} already exists.")
        self.email = email
