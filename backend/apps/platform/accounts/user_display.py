"""Allauth ``ACCOUNT_USER_DISPLAY`` callable.

Allauth's default user-display function (``default_user_display`` in
``allauth.account.internal.userkit``) reads ``user.username`` to print
a friendly identifier in templates and emails. Our custom ``User``
model (B.3.3) is email-only — ``USERNAME_FIELD = "email"`` with no
``username`` field — so that default crashes with ``AttributeError``.

Allauth lets the application override this lookup via the
``ACCOUNT_USER_DISPLAY`` setting, which it resolves at runtime as a
dotted import path to a callable taking a single user argument and
returning a string. This module provides that callable.

Used by:

* ``{% user_display user %}`` template tag (the trigger that surfaced
  the bug — used in ``account/email/email_confirmation_message.txt``,
  ``account/email_confirm.html``, ``account/email/password_reset_key_message.txt``,
  and ``account/messages/logged_in.txt``).
* Internal allauth code paths that format the user for log lines,
  error pages, and similar.

The function MUST be safe to call with any object that has at least
the shape of our ``User`` model. It MUST NOT raise. If the user
object is unexpectedly shaped (e.g. a unit-test stub), the function
falls back to ``str(user)``, which on our ``User`` returns the email
via ``__str__``.

The function MUST NOT log or return secrets. ``email`` is the safe,
human-friendly identifier we intentionally show in product UI; it is
explicitly not redacted by G.5.5.
"""

from __future__ import annotations

from typing import Any


def user_display(user: Any) -> str:
    """Return a human-readable label for a User.

    Resolution order:

    1. ``user.email`` — the canonical identifier on our User model
       (B.3.3). USERNAME_FIELD = "email", so this is always populated
       for real users.
    2. ``str(user)`` — falls back via the model's ``__str__``, which
       on our User also returns the email. Catches the case where the
       caller hands us a not-quite-User object (test stubs, etc.).
    3. ``""`` — last-ditch empty string so allauth template rendering
       never crashes on a malformed user object.
    """
    if user is None:
        return ""
    email = getattr(user, "email", None)
    if email:
        return str(email)
    try:
        return str(user)
    except Exception:
        return ""
