"""Allauth socialaccount signal handlers (M1 D5 Phases 3, 4, 5).

Maps allauth's socialaccount signals to B.4.19 audit events and
writes the post-login session key the middleware reads.

Successful-login paths (Phase 3, Phase 4):
* ``social_account_added`` → OAUTH_LOGIN_SUCCEEDED (first-time link);
  also writes the provider-code session key for the MFA enrollment
  middleware (Phase 4).
* ``social_account_updated`` → OAUTH_LOGIN_SUCCEEDED (repeat login);
  same session-key write.

Unlink path (Phase 3):
* ``social_account_removed`` → OAUTH_ACCOUNT_UNLINKED.

Pre-adapter failure paths (Phase 5):
* ``social_account_login_failed`` (provider returned an error /
  cryptographic validation failed) → OAUTH_LOGIN_FAILED with
  failure_reason='authentication_error'.
* (Login cancellation is handled by the user-facing template only —
  allauth doesn't fire a dedicated signal for cancellation that
  carries enough context for an audit event. Tracked in retro.)

Note: ``pre_social_login`` is intentionally not wired here. The
adapter (Phase 3) emits ``OAUTH_LOGIN_STARTED`` directly with full
claims context the signal payload doesn't carry.
"""

from __future__ import annotations

import logging
from typing import Any

from allauth.socialaccount.signals import (
    social_account_added,
    social_account_removed,
    social_account_updated,
)
from django.dispatch import receiver

from apps.platform.accounts.middleware import SESSION_KEY_LOGIN_PROVIDER_CODE
from apps.platform.accounts.services import record_auth_event

logger = logging.getLogger(__name__)


def _write_login_provider_code_to_session(request: Any, provider_code: str) -> None:
    """Store the login provider code on the session.

    Read by :class:`RequireMfaEnrollmentMiddleware` to determine
    whether to bypass or force local TOTP enrollment.

    If the request has no ``session`` attribute (unusual for a real
    HTTP request, but possible for synthetic signals from tests),
    silently skip — the middleware will treat the absence as a
    local-password login and force enrollment, which is the safe
    default.
    """
    session = getattr(request, "session", None)
    if session is None:
        logger.debug(
            "Cannot write login provider code to session: request has no session."
        )
        return
    session[SESSION_KEY_LOGIN_PROVIDER_CODE] = provider_code


@receiver(
    social_account_added,
    dispatch_uid="apps.platform.accounts.oauth.on_social_account_added",
)
def _on_social_account_added(
    sender: Any,
    request: Any,
    sociallogin: Any,
    **kwargs: object,
) -> None:
    """First-time SocialAccount creation for a User.

    Emits OAUTH_LOGIN_SUCCEEDED. The OAUTH_ACCOUNT_LINKED event is
    already emitted by :func:`resolve_external_user` from inside the
    service's atomic boundary; this signal-side emission is the
    *login outcome* counterpart.

    Also writes the login provider code to the session so the MFA
    enrollment middleware can apply the trusted-provider policy.
    """
    account = sociallogin.account
    user_id = sociallogin.user.id if sociallogin.user else None
    provider_code = str(account.provider)

    _write_login_provider_code_to_session(request, provider_code)

    record_auth_event(
        event_type="OAUTH_LOGIN_SUCCEEDED",
        actor_id=user_id,
        object_kind="platform_accounts.User",
        object_id=str(user_id) if user_id else None,
        metadata={
            "provider_code": provider_code,
            "first_login": True,
        },
    )


@receiver(
    social_account_removed,
    dispatch_uid="apps.platform.accounts.oauth.on_social_account_removed",
)
def _on_social_account_removed(
    sender: Any,
    request: Any,
    socialaccount: Any,
    **kwargs: object,
) -> None:
    """SocialAccount unlinking — B.4.18.

    Emits OAUTH_ACCOUNT_UNLINKED. The actor is the user themselves
    (only the account owner can unlink); pre-emption-by-admin
    unlinking happens through a separate platform-tier flow which
    will emit the same event with a different actor in M1 D7.
    """
    user_id = socialaccount.user_id
    record_auth_event(
        event_type="OAUTH_ACCOUNT_UNLINKED",
        actor_id=user_id,
        object_kind="platform_accounts.User",
        object_id=str(user_id),
        metadata={
            "provider_code": str(socialaccount.provider),
        },
    )


@receiver(
    social_account_updated,
    dispatch_uid="apps.platform.accounts.oauth.on_social_account_updated",
)
def _on_social_account_updated(
    sender: Any,
    request: Any,
    sociallogin: Any,
    **kwargs: object,
) -> None:
    """Repeat-login on an existing SocialAccount.

    Emits OAUTH_LOGIN_SUCCEEDED. This is the success marker for
    every OAuth login AFTER the first. allauth fires this signal
    on each successful repeat OAuth login, BEFORE user_logged_in.

    Also writes the login provider code to the session so the MFA
    enrollment middleware can apply the trusted-provider policy.
    """
    account = sociallogin.account
    user_id = sociallogin.user.id if sociallogin.user else None
    provider_code = str(account.provider)

    _write_login_provider_code_to_session(request, provider_code)

    record_auth_event(
        event_type="OAUTH_LOGIN_SUCCEEDED",
        actor_id=user_id,
        object_kind="platform_accounts.User",
        object_id=str(user_id) if user_id else None,
        metadata={
            "provider_code": provider_code,
            "first_login": False,
        },
    )


# ---------------------------------------------------------------------------
# Phase 5: pre-adapter failure paths.
# ---------------------------------------------------------------------------
#
# Allauth 65.x exposes ``social_account_login_failed`` for the case
# where the provider returned an error to the callback (state/nonce
# validation failure, ID token signature failure, provider-side
# refusal). This fires BEFORE our adapter's pre_social_login is
# reached, so the adapter's own OAUTH_LOGIN_FAILED emission doesn't
# cover it. We wire it here.
#
# Note: the signal exists in allauth >=65.0. If a future version
# renames or removes it, this import fails — surfaced at app startup
# rather than silently. That's the safer failure mode.

try:
    from allauth.socialaccount.signals import social_account_login_failed
except ImportError:
    # Older allauth versions don't emit this signal. Wire is a no-op.
    social_account_login_failed = None  # type: ignore[assignment]
    logger.warning(
        "allauth.socialaccount.signals.social_account_login_failed not "
        "available; OAUTH_LOGIN_FAILED will not be emitted for "
        "pre-adapter callback errors. Upgrade allauth if you need this."
    )


if social_account_login_failed is not None:

    @receiver(
        social_account_login_failed,
        dispatch_uid="apps.platform.accounts.oauth.on_social_account_login_failed",
    )
    def _on_social_account_login_failed(
        sender: Any,
        request: Any,
        provider: Any = None,
        exception: BaseException | None = None,
        state: dict[str, Any] | None = None,
        **kwargs: object,
    ) -> None:
        """Provider returned an error to the callback.

        Causes include:
          - state/nonce mismatch (CSRF defense, B.4.5),
          - ID token signature failure (B.4.5),
          - provider-side error response,
          - network failure mid-callback.

        Emits OAUTH_LOGIN_FAILED with failure_reason='authentication_error'.
        The exception type is captured in metadata for support
        debugging, but the exception MESSAGE is not — exception
        messages can contain tokens or other sensitive data from
        provider responses (B.4.19 / G.5.5).
        """
        provider_code = (
            getattr(provider, "id", None)
            or getattr(provider, "name", None)
            or "unknown"
        )
        # System User as actor — no user is authenticated at this
        # point. Identical to the adapter's actor convention.
        from django.contrib.auth import get_user_model

        UserModel = get_user_model()
        try:
            actor_id = UserModel.objects.get(is_system=True).id
        except UserModel.DoesNotExist:
            logger.error(
                "Cannot emit OAUTH_LOGIN_FAILED: System User missing. "
                "Skipping audit event."
            )
            return

        record_auth_event(
            event_type="OAUTH_LOGIN_FAILED",
            actor_id=actor_id,
            object_kind=None,
            object_id=None,
            metadata={
                "provider_code": str(provider_code),
                "failure_reason": "authentication_error",
                "exception_type": (
                    type(exception).__name__ if exception is not None else None
                ),
                # Intentionally NOT including the exception message — may
                # contain provider tokens or other sensitive data.
            },
        )
