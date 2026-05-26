"""Account utilities shared by services, management commands, and tests.

Helpers in this package are intentionally side-effect-light and
exempt from the service-layer transaction rule (A.4.4). They run
inside a caller's transaction when state-changing, and are called
from both service code AND management-command / test code.

The first member is :func:`ensure_verified_email_address`, which
idempotently installs a verified primary allauth ``EmailAddress``
row for a user. Used by:

* ``UserManager.create_superuser`` — so the first-time admin
  isn't blocked by allauth's mandatory email verification
  middleware.
* ``seed_dev_tenant`` management command — so the demo admin
  can sign in without a Mailpit roundtrip.

The helper writes through the allauth ORM directly. This is
acceptable in a utility module because:

* allauth's ``EmailAddress`` is not a tenant-owned model; the
  A.4.4 service-layer rule covers state changes to OUR domain
  models, not third-party auth-system rows.
* ``update_or_create`` provides natural idempotency.
* The two callers (manager method + seed command) are both
  legitimately outside the service layer.
"""

from __future__ import annotations

from apps.platform.accounts.utils.email_verification import (
    ensure_verified_email_address,
)

__all__ = ["ensure_verified_email_address"]
