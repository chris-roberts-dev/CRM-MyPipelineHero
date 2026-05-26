"""Logout signal handler — root-domain revocation (M1 D6 Phase 5, B.4.17).

Hooks the logout signal. When logout happens on the root domain, all
outstanding handoff tokens for the user are revoked and ROOT_SESSION_LOGOUT
is emitted.

When logout happens on a tenant subdomain, the tenant logout view owns
TENANT_SESSION_LOGOUT audit emission and this handler returns early.
Tenant logouts MUST NOT revoke cross-tenant handoff tokens.

This handler is intentionally defensive because Django's logout signal may
fire in test-client flows, mocked signal tests, or other code paths where the
request object is incomplete or does not have normal host metadata.
"""

from __future__ import annotations

import logging
from typing import Any

from allauth.account.signals import user_logged_out
from django.conf import settings
from django.core.exceptions import DisallowedHost
from django.dispatch import receiver

from apps.common.sessions.host_resolution import HostScope, resolve_session_scope
from apps.platform.accounts.handoff.services import (
    revoke_all_handoff_tokens_for_user,
)
from apps.platform.accounts.services import record_auth_event

logger = logging.getLogger(__name__)


def _fallback_host() -> str:
    """Return a safe fallback host for tests or incomplete requests.

    Prefer an explicit root-domain-style setting if the project defines one.
    Otherwise use ``testserver``, which is Django's conventional test host.
    """
    for setting_name in (
        "ROOT_DOMAIN",
        "PUBLIC_ROOT_DOMAIN",
        "BASE_DOMAIN",
        "PRIMARY_DOMAIN",
    ):
        value = getattr(settings, setting_name, None)
        if isinstance(value, str) and value.strip():
            return value.strip().split(":", 1)[0].lower()

    return "testserver"


def _safe_request_host(request: Any) -> str:
    """Safely extract a normalized host from a possibly incomplete request.

    ``request.get_host()`` can fail in tests when the request lacks
    ``HTTP_HOST`` and ``SERVER_NAME``. Mocked requests may also return a
    MagicMock instead of a string. This helper normalizes those cases so the
    logout signal receiver never crashes while handling audit/revocation.
    """
    host: Any = None

    try:
        host = request.get_host()
    except (AttributeError, KeyError, DisallowedHost, TypeError, ValueError):
        host = None

    if not isinstance(host, str) or not host.strip():
        host = _fallback_host()

    return host.strip().split(":", 1)[0].lower()


def _is_tenant_logout_host(host: str) -> bool:
    """Return True when host clearly resolves to a tenant subdomain.

    If host classification fails, default to root-style behavior. That means
    we revoke outstanding handoff tokens rather than leaving them active.
    Tenant logout requests should have a real tenant host, so they will still
    be classified correctly in normal request flows.
    """
    try:
        scope = resolve_session_scope(host)
    except (TypeError, ValueError):
        logger.debug(
            "Could not resolve logout host scope for host=%r; treating as "
            "root/unknown logout.",
            host,
        )
        return False

    return scope.host_scope == HostScope.TENANT


@receiver(user_logged_out)
def _on_user_logged_out(
    sender: Any,
    request: Any,
    user: Any,
    **kwargs: Any,
) -> None:
    """Revoke outstanding handoff tokens when logout is on the root domain.

    Args:
        sender: Signal sender.
        request: The HTTP request. Used for host classification.
        user: The user who just logged out. May be None for edge-case flows.
    """
    if user is None or getattr(user, "id", None) is None:
        logger.debug("user_logged_out fired without a user; skipping revocation.")
        return

    if request is None:
        logger.debug("user_logged_out fired without a request; skipping revocation.")
        return

    host = _safe_request_host(request)

    if _is_tenant_logout_host(host):
        logger.debug(
            "user_logged_out on tenant host %s; skipping handoff token "
            "revocation because tenant logout flow owns its own audit.",
            host,
        )
        return

    revoked_count = revoke_all_handoff_tokens_for_user(user_id=user.id)

    record_auth_event(
        event_type="ROOT_SESSION_LOGOUT",
        actor_id=user.id,
        organization_id=None,
        object_kind="platform_accounts.User",
        object_id=str(user.id),
        metadata={
            "host": host,
            "tokens_revoked": revoked_count,
        },
    )
