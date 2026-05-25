"""MFA satisfaction signal handlers (M1 D6 Phase 4A).

Writes ``mph_mfa_satisfied_at`` to the request session when the
user completes an MFA event — TOTP challenge passed, recovery code
consumed, or fresh TOTP enrollment.

The session key is consumed by the org picker view (Phase 4B) to
populate ``HandoffResult.mfa_satisfied_at`` at handoff-token issue
time. The token then carries the timestamp across to the tenant
subdomain, where B.4.10 freshness checks can be enforced from the
tenant session.

**Two allauth.mfa signals handled:**

* ``authenticator_used`` — fires when a user verifies an
  authenticator (TOTP code passed, recovery code consumed,
  passkey verified). The canonical "MFA was just satisfied"
  signal.
* ``authenticator_added`` — fires when a user enrolls a new
  authenticator. Allauth's enrollment flow requires the user to
  enter a valid TOTP code as part of activation, so we treat
  enrollment success as equivalent to "MFA was just satisfied."
  Without this, a freshly-enrolled user would have no
  ``mph_mfa_satisfied_at`` on session and would fail B.4.10
  freshness checks immediately after enrolling.

Trusted-provider OAuth bypass — where MFA is "satisfied" by the
identity provider rather than a local challenge — is handled
separately in
:mod:`apps.platform.accounts.middleware` (the
``RequireMfaEnrollmentMiddleware._emit_provider_mfa_trusted_once``
codepath, which now also sets the session key).

**Why this lives in signals, not middleware.** Allauth's MFA
challenge / enrollment views complete the MFA event and then
redirect to ``LOGIN_REDIRECT_URL``. By the time the redirect target
runs, allauth's signal has already fired. Hooking the signal
captures the satisfaction moment precisely; hooking the redirect-
target view would race with the picker and produce stale
timestamps.

**No audit emission from these handlers.** This is purely session
state. Audit events for MFA enrollment / use are emitted elsewhere
(``MFA_ENROLLED``, ``LOCAL_MFA_CHALLENGE_PASSED``) by signal
handlers wired in M1 D4. The signals here are session-only side
effects and don't need to go through ``record_auth_event``.
"""

from __future__ import annotations

import logging
from typing import Any

from allauth.mfa.signals import authenticator_added, authenticator_used
from django.dispatch import receiver
from django.utils import timezone

logger = logging.getLogger(__name__)


# Session key written by these handlers, read by the org-picker
# view (Phase 4B) at handoff-token issue time. ISO 8601 timestamp.
SESSION_KEY_MFA_SATISFIED_AT = "mph_mfa_satisfied_at"


@receiver(authenticator_used)
def _on_authenticator_used(
    sender: Any,
    request: Any,
    user: Any,
    authenticator: Any,
    **kwargs: Any,
) -> None:
    """Write ``mph_mfa_satisfied_at`` when a user passes an MFA check.

    Fires for TOTP challenge passes, recovery-code consumption, and
    passkey verification. The session is the request's session
    (root-domain when the user is logging in to mph.local).
    """
    _record_mfa_satisfaction(request, source="authenticator_used")


@receiver(authenticator_added)
def _on_authenticator_added(
    sender: Any,
    request: Any,
    user: Any,
    authenticator: Any,
    **kwargs: Any,
) -> None:
    """Write ``mph_mfa_satisfied_at`` when a user enrolls a new authenticator.

    Allauth's enrollment flow validates a TOTP code as part of
    activation, so enrollment success is functionally equivalent
    to passing an MFA challenge. Without this handler, a user who
    enrolls and then immediately hits the picker would have no
    satisfaction timestamp on session.
    """
    _record_mfa_satisfaction(request, source="authenticator_added")


def _record_mfa_satisfaction(request: Any, *, source: str) -> None:
    """Write the timestamp to session, with defensive guards."""
    if request is None:
        # Some signal callers may not pass request (programmatic
        # enrollment in management commands, etc.). Skip silently.
        return
    if not hasattr(request, "session"):
        logger.debug(
            "MFA satisfaction signal received without request.session "
            "(source=%s). Skipping session write.",
            source,
        )
        return
    timestamp = timezone.now().isoformat()
    request.session[SESSION_KEY_MFA_SATISFIED_AT] = timestamp
    # The session may not be marked modified if the key already
    # existed with the same value (Django's session machinery is
    # subtle here). Force modification so the cookie gets refreshed.
    request.session.modified = True
    logger.debug(
        "Recorded MFA satisfaction (source=%s, timestamp=%s).",
        source,
        timestamp,
    )
