"""Allauth signal handlers for authentication audit events (M1 D4).

These handlers are thin adapters. They:

1. Receive an allauth signal.
2. Extract the user id and event-relevant metadata.
3. Call :func:`apps.platform.accounts.services.record_auth_event`.

They MUST NOT contain business logic, MUST NOT make ORM writes
directly, and MUST NOT log sensitive data (B.4.19, G.5.5).

The set of handled signals maps to B.4.19's authentication audit
event catalog:

* ``user_logged_in``         → ``LOCAL_PASSWORD_LOGIN_SUCCEEDED`` + ``LOGIN_SUCCEEDED``
* ``user_login_failed``      → ``LOCAL_PASSWORD_LOGIN_FAILED`` + ``LOGIN_FAILED``
* ``user_logged_out``        → ``LOGOUT``
* ``user_signed_up``         → ``USER_REGISTERED`` (when self-signup is allowed)
* ``email_confirmed``        → ``EMAIL_VERIFIED``
* ``email_confirmation_sent``→ ``EMAIL_VERIFICATION_SENT``
* ``password_changed``       → ``PASSWORD_CHANGED``
* ``password_reset``         → ``PASSWORD_RESET_COMPLETED``
* ``password_set``           → ``PASSWORD_CHANGED`` (first-time set after invite)
* ``authenticator_added``    → ``MFA_ENROLLED``
* ``authenticator_removed``  → ``MFA_DISABLED``

Signals are connected by ``AccountsConfig.ready()``.

**OAUTH_* and HANDOFF_* events are intentionally NOT wired here.**
They land in M1 D5 (OAuth provider integration) and M1 D6 (handoff
token issuance) respectively.

**ACCOUNT_LOCKED is also NOT wired here.** Allauth doesn't emit a
distinct lockout signal — the lockout decision is made internally
during login_failed. The full B.5.4 dual-tier policy needs a custom
rate limiter; an interim ACCOUNT_LOCKED emission lands as part of
that work. Tracked in M1 retro as a follow-up.
"""

from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

from allauth.account.signals import (
    email_confirmation_sent,
    email_confirmed,
    password_changed,
    password_reset,
    password_set,
    user_logged_in,
    user_logged_out,
    user_signed_up,
)
from django.contrib.auth.signals import user_login_failed
from django.dispatch import receiver

logger = logging.getLogger(__name__)

# allauth.mfa exports its signals from a stable module path in 65.x.
# Wrapped in a try/except so older allauth versions degrade gracefully
# (no MFA audit events, no import error).
try:
    from allauth.mfa.signals import (
        authenticator_added,
        authenticator_removed,
    )

    _MFA_SIGNALS_AVAILABLE = True
except ImportError:  # pragma: no cover - defensive
    _MFA_SIGNALS_AVAILABLE = False
    authenticator_added = None  # type: ignore[assignment]
    authenticator_removed = None  # type: ignore[assignment]


def _user_id(user: Any) -> UUID | None:
    """Safely extract a user's UUID; return None if missing."""
    if user is None:
        return None
    pk = getattr(user, "pk", None) or getattr(user, "id", None)
    if pk is None:
        return None
    return pk if isinstance(pk, UUID) else None


def _safe_metadata(request: Any, **extra: Any) -> dict[str, Any]:
    """Build a metadata dict that includes only NON-SENSITIVE values.

    Per B.4.19 / G.5.5, we MUST NOT include passwords, tokens,
    authorization codes, TOTP secrets, recovery codes, CSRF tokens,
    session keys, or full request headers.

    What IS safe to include: client IP, user agent, route path,
    method, and the allauth event-specific extras passed in.
    """
    meta: dict[str, Any] = {}
    if request is not None:
        # Source IP and user agent will be auto-filled by the M2
        # audit middleware; in M1 we include a thin hint to make
        # debugging easier. Never the full headers dict.
        try:
            meta["path"] = request.path
            meta["method"] = request.method
        except AttributeError:
            pass
    meta.update(extra)
    return meta


# ---------------------------------------------------------------------------
# Login / logout
# ---------------------------------------------------------------------------


@receiver(user_logged_in)
def on_user_logged_in(sender: Any, request: Any, user: Any, **kwargs: Any) -> None:
    """Fires after a successful login (any method).

    Allauth fires this once. We emit BOTH the generic LOGIN_SUCCEEDED
    and the method-specific LOCAL_PASSWORD_LOGIN_SUCCEEDED because
    B.4.19 catalogs both. The distinction matters: an OAuth login
    will emit LOGIN_SUCCEEDED + OAUTH_LOGIN_SUCCEEDED instead (M1 D5).

    For M1 D4 (local-only), every successful login is a local
    password login.
    """
    from apps.platform.accounts.services import record_auth_event

    uid = _user_id(user)
    object_kind = "platform_accounts.User" if uid else None
    object_id = str(uid) if uid else None

    record_auth_event(
        event_type="LOCAL_PASSWORD_LOGIN_SUCCEEDED",
        actor_id=uid,
        object_kind=object_kind,
        object_id=object_id,
        metadata=_safe_metadata(request),
    )
    record_auth_event(
        event_type="LOGIN_SUCCEEDED",
        actor_id=uid,
        object_kind=object_kind,
        object_id=object_id,
        metadata=_safe_metadata(request, method="local_password"),
    )


@receiver(user_login_failed)
def on_user_login_failed(
    sender: Any,
    credentials: dict[str, Any] | None = None,
    request: Any = None,
    **kwargs: Any,
) -> None:
    """Fires when authentication credentials fail.

    The ``credentials`` dict from allauth contains the *attempted*
    identifier (usually email). We include only the email field; the
    password field is NEVER touched.
    """
    from apps.platform.accounts.services import record_auth_event

    attempted_email = None
    if credentials and isinstance(credentials, dict):
        # Allauth uses "login" for the identifier; older versions use "email".
        attempted_email = credentials.get("login") or credentials.get("email")
        # Explicitly do NOT touch credentials.get("password").

    meta = _safe_metadata(request)
    if attempted_email:
        meta["attempted_email"] = attempted_email

    record_auth_event(
        event_type="LOCAL_PASSWORD_LOGIN_FAILED",
        actor_id=None,
        metadata=meta,
    )
    record_auth_event(
        event_type="LOGIN_FAILED",
        actor_id=None,
        metadata=meta,
    )


@receiver(user_logged_out)
def on_user_logged_out(sender: Any, request: Any, user: Any, **kwargs: Any) -> None:
    """Fires when a user logs out."""
    from apps.platform.accounts.services import record_auth_event

    uid = _user_id(user)
    record_auth_event(
        event_type="LOGOUT",
        actor_id=uid,
        object_kind="platform_accounts.User" if uid else None,
        object_id=str(uid) if uid else None,
        metadata=_safe_metadata(request),
    )


# ---------------------------------------------------------------------------
# Registration / email verification / password lifecycle
# ---------------------------------------------------------------------------


@receiver(user_signed_up)
def on_user_signed_up(sender: Any, request: Any, user: Any, **kwargs: Any) -> None:
    """Fires after allauth-driven self-signup.

    This is a *secondary* code path. Production registration goes
    through ``register_local_user`` (the service) and emits the
    USER_REGISTERED event itself, inside the service's atomic block.
    But allauth's built-in signup view bypasses our service (it does
    its own ``User.objects.create_user`` under the hood), and emits
    ``user_signed_up`` after. We catch that here so the audit event
    fires regardless of which signup path was used.

    De-duplication: if both signal-driven AND service-driven emissions
    fire for the same user, that's two USER_REGISTERED events.
    Acceptable in M1 because allauth signup is gated behind email
    verification (B.4) and our service is the only path used by
    seed_dev_tenant / invite-acceptance.
    """
    from apps.platform.accounts.services import record_auth_event

    uid = _user_id(user)
    record_auth_event(
        event_type="USER_REGISTERED",
        actor_id=uid,
        object_kind="platform_accounts.User" if uid else None,
        object_id=str(uid) if uid else None,
        metadata=_safe_metadata(request, via="allauth_signup"),
    )


@receiver(email_confirmation_sent)
def on_email_confirmation_sent(
    sender: Any, request: Any, confirmation: Any, signup: bool = False, **kwargs: Any
) -> None:
    """Fires when allauth sends a verification email."""
    from apps.platform.accounts.services import record_auth_event

    user = getattr(getattr(confirmation, "email_address", None), "user", None)
    uid = _user_id(user)
    record_auth_event(
        event_type="EMAIL_VERIFICATION_SENT",
        actor_id=uid,
        metadata=_safe_metadata(request, signup=bool(signup)),
    )


@receiver(email_confirmed)
def on_email_confirmed(
    sender: Any, request: Any, email_address: Any, **kwargs: Any
) -> None:
    """Fires when a user confirms an email address."""
    from apps.platform.accounts.services import record_auth_event

    user = getattr(email_address, "user", None)
    uid = _user_id(user)
    record_auth_event(
        event_type="EMAIL_VERIFIED",
        actor_id=uid,
        object_kind="platform_accounts.User" if uid else None,
        object_id=str(uid) if uid else None,
        metadata=_safe_metadata(request),
    )


@receiver(password_changed)
def on_password_changed(sender: Any, request: Any, user: Any, **kwargs: Any) -> None:
    """Fires when an authenticated user changes their password."""
    from apps.platform.accounts.services import record_auth_event

    uid = _user_id(user)
    record_auth_event(
        event_type="PASSWORD_CHANGED",
        actor_id=uid,
        object_kind="platform_accounts.User" if uid else None,
        object_id=str(uid) if uid else None,
        metadata=_safe_metadata(request),
    )


@receiver(password_set)
def on_password_set(sender: Any, request: Any, user: Any, **kwargs: Any) -> None:
    """Fires when a user sets a password for the first time
    (e.g. after invite acceptance, or after linking an external identity)."""
    from apps.platform.accounts.services import record_auth_event

    uid = _user_id(user)
    record_auth_event(
        event_type="PASSWORD_CHANGED",
        actor_id=uid,
        object_kind="platform_accounts.User" if uid else None,
        object_id=str(uid) if uid else None,
        metadata=_safe_metadata(request, first_time=True),
    )


@receiver(password_reset)
def on_password_reset(sender: Any, request: Any, user: Any, **kwargs: Any) -> None:
    """Fires when a user completes the password-reset flow."""
    from apps.platform.accounts.services import record_auth_event

    uid = _user_id(user)
    record_auth_event(
        event_type="PASSWORD_RESET_COMPLETED",
        actor_id=uid,
        object_kind="platform_accounts.User" if uid else None,
        object_id=str(uid) if uid else None,
        metadata=_safe_metadata(request),
    )


# ---------------------------------------------------------------------------
# MFA lifecycle
# ---------------------------------------------------------------------------

if _MFA_SIGNALS_AVAILABLE:

    @receiver(authenticator_added)  # type: ignore[misc]
    def on_authenticator_added(
        sender: Any, request: Any, user: Any, authenticator: Any, **kwargs: Any
    ) -> None:
        """Fires when a user enrolls a new MFA authenticator (TOTP, recovery codes)."""
        from apps.platform.accounts.services import record_auth_event

        uid = _user_id(user)
        kind = getattr(authenticator, "type", None) or "unknown"
        # NEVER include the authenticator's secret or codes.
        if kind == "recovery_codes":
            event = "MFA_RECOVERY_CODES_REGENERATED"
        else:
            event = "MFA_ENROLLED"
        record_auth_event(
            event_type=event,
            actor_id=uid,
            object_kind="platform_accounts.User" if uid else None,
            object_id=str(uid) if uid else None,
            metadata=_safe_metadata(request, authenticator_type=kind),
        )

    @receiver(authenticator_removed)  # type: ignore[misc]
    def on_authenticator_removed(
        sender: Any, request: Any, user: Any, authenticator: Any, **kwargs: Any
    ) -> None:
        """Fires when a user disables an MFA authenticator."""
        from apps.platform.accounts.services import record_auth_event

        uid = _user_id(user)
        kind = getattr(authenticator, "type", None) or "unknown"
        record_auth_event(
            event_type="MFA_DISABLED",
            actor_id=uid,
            object_kind="platform_accounts.User" if uid else None,
            object_id=str(uid) if uid else None,
            metadata=_safe_metadata(request, authenticator_type=kind),
        )

else:  # pragma: no cover - defensive
    logger.warning(
        "allauth.mfa.signals not importable; MFA audit events will not be emitted. "
        "Ensure django-allauth[mfa] is installed."
    )


def register_signal_handlers() -> None:
    """No-op marker called from AccountsConfig.ready().

    The @receiver decorators above register the handlers at module
    import time. This function exists so AccountsConfig.ready() has
    an explicit hook to import this module, which is what actually
    triggers the receivers to bind. Without that import, the signals
    never connect.
    """
    return None
