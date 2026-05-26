"""Idempotent verified-EmailAddress installation (M1 D7 Phase 1).

Extracted from the M1 D4 ``seed_dev_tenant._ensure_verified_email_address``
helper so the same logic can be reused by ``UserManager.create_superuser``
without duplicating the allauth-EmailAddress write.

**Why this exists.** Settings include
``ACCOUNT_EMAIL_VERIFICATION = "mandatory"`` per the production
posture. Every login by a user without a verified
``EmailAddress`` row gets bounced to allauth's email-confirmation
flow. For:

* The bootstrap superuser (first ``createsuperuser`` run on a
  fresh deployment) — they have no Mailpit access, no SMTP
  configured, and a chicken-and-egg blocker.
* The dev demo tenant — the engineer wants to sign in to
  ``admin@mph.local`` immediately without a Mailpit roundtrip.

Installing a pre-verified ``EmailAddress`` resolves both. The
function is idempotent so re-running ``createsuperuser`` (or
re-running the seed command after a ``--reset``) doesn't
double-create or get into half-verified states.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from allauth.account.models import EmailAddress

if TYPE_CHECKING:
    from django.contrib.auth.models import AbstractBaseUser


def ensure_verified_email_address(user: AbstractBaseUser) -> bool:
    """Idempotently install a verified primary EmailAddress for ``user``.

    Args:
        user: Any user object exposing an ``email`` attribute. In our
            codebase this is always ``apps.platform.accounts.models.User``.

    Returns:
        ``True`` if the row was newly created; ``False`` if it already
        existed (and we force-flipped it to verified/primary in case a
        prior allauth flow had left it unverified).

    Side effects:
        Writes / updates a single ``allauth.account.models.EmailAddress``
        row. Does not open its own transaction — the caller is
        responsible for transactional context if they need one. In
        practice both callers (``create_superuser`` and
        ``seed_dev_tenant``) run this in a context where atomicity
        doesn't matter: either the row commits or the entire user
        creation rolls back.
    """
    email = user.email
    _, created = EmailAddress.objects.update_or_create(
        user=user,
        email=email,
        defaults={
            "verified": True,
            "primary": True,
        },
    )
    return created
