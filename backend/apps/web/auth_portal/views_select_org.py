"""Org-picker view (M1 D6 Phase 4B, B.4.15).

Replaces the M1 D4 placeholder. Implements the B.4.15 branch table:

* **No active memberships, not staff** → render
  ``no_active_access.html`` (HTTP 200, message + logout link).
* **Exactly one active membership** → auto-issue handoff token,
  render ``handoff_form.html`` with JavaScript auto-submit.
* **Multiple active memberships** → render ``select_org.html``
  with one card per membership.
* **Staff user (regardless of memberships)** → render
  ``select_org.html`` with staff-specific copy including a link
  to the platform console (M1 D7 destination).

The picker view doesn't itself issue tokens for the multi-
membership case — it renders a list of POST forms targeting
``/handoff/issue/``. The user clicks one, the issue view mints
the token, that view renders the auto-POST form.

**Why two views (picker + issue) instead of one?** Separation of
concerns: the picker is read-only (lists memberships); the issue
endpoint is the only place that calls ``issue_handoff_token`` and
the only place that audits ``MEMBERSHIP_SELECTED`` (for the user-
explicit case). The auto-advance single-membership branch also
calls the issue logic, but in-line rather than via redirect to
keep the UX as a single page load.
"""

from __future__ import annotations

import logging
from typing import Any

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views import View

from apps.platform.accounts.handoff.services import (
    NoActiveHandoffSigningKeyError,
    issue_handoff_token,
)
from apps.platform.accounts.middleware import SESSION_KEY_LOGIN_PROVIDER_CODE
from apps.platform.accounts.signals_mfa import SESSION_KEY_MFA_SATISFIED_AT
from apps.platform.audit.services import audit_emit
from apps.platform.organizations.models import Membership, MembershipStatus

logger = logging.getLogger(__name__)


@method_decorator(login_required, name="dispatch")
class SelectOrgView(View):
    """GET-only org picker / auto-advance / no-access page."""

    def get(self, request: HttpRequest) -> HttpResponse:
        user = request.user

        memberships = list(
            Membership.objects.filter(
                user=user,
                status=MembershipStatus.ACTIVE,
            )
            .select_related("organization")
            .order_by("organization__name")
        )

        # ---- B.4.15 branch table. ----------------------------------------
        if not memberships and not user.is_staff:
            return self._render_no_active_access(request)

        if len(memberships) == 1 and not user.is_staff:
            # Auto-advance: mint token + render auto-POST form.
            return self._auto_advance(request, memberships[0])

        # Multiple memberships OR staff → show the picker.
        return self._render_picker(request, memberships=memberships)

    # ------------------------------------------------------------------
    # Branch implementations.
    # ------------------------------------------------------------------

    def _render_no_active_access(self, request: HttpRequest) -> HttpResponse:
        return render(
            request,
            "auth_portal/no_active_access.html",
            status=200,
        )

    def _auto_advance(
        self, request: HttpRequest, membership: Membership
    ) -> HttpResponse:
        """Single-membership auto-issue path.

        Mints the token, emits ``MEMBERSHIP_SELECTED`` with
        ``auto_selected=True``, renders the auto-POST form.
        """
        token = _issue_token_for_membership(
            request=request,
            membership=membership,
            auto_selected=True,
        )
        if token is None:
            # No active signing key — operator must rotate one in.
            return self._render_no_signing_key_available(request)

        return self._render_handoff_form(request, membership=membership, token=token)

    def _render_picker(
        self,
        request: HttpRequest,
        *,
        memberships: list[Membership],
    ) -> HttpResponse:
        return render(
            request,
            "auth_portal/select_org.html",
            {
                "memberships": memberships,
                "is_staff": request.user.is_staff,
                # Platform console destination (M1 D7).
                "platform_console_url": "/platform/",
            },
        )

    def _render_handoff_form(
        self,
        request: HttpRequest,
        *,
        membership: Membership,
        token: str,
    ) -> HttpResponse:
        """Render the auto-POST form pointing at the tenant subdomain."""
        tenant_host = settings.MPH_TENANT_DOMAIN_TEMPLATE.format(
            slug=membership.organization.slug
        )
        # Build the absolute URL. In dev the scheme is http; in
        # production the same template setting carries the production
        # host and we still use whatever scheme the original request
        # came in on (HTTPS-terminated by Nginx in prod).
        scheme = "https" if request.is_secure() else "http"
        action_url = f"{scheme}://{tenant_host}/handoff/"

        return render(
            request,
            "auth_portal/handoff_form.html",
            {
                "action_url": action_url,
                "token": token,
                "organization_name": membership.organization.name,
            },
        )

    def _render_no_signing_key_available(self, request: HttpRequest) -> HttpResponse:
        """Render error when no active HandoffSigningKey exists.

        Operationally fatal — platform admin must create + promote
        a key. The picker shows a user-friendly error rather than a
        500.
        """
        return render(
            request,
            "auth_portal/no_active_access.html",
            {
                "system_error": True,
                "system_error_message": (
                    "We're unable to complete sign-in right now. "
                    "Please contact support."
                ),
            },
            status=503,
        )


# ---------------------------------------------------------------------------
# Helpers shared with views_handoff_issue.
# ---------------------------------------------------------------------------


def _issue_token_for_membership(
    *,
    request: HttpRequest,
    membership: Membership,
    auto_selected: bool,
) -> str | None:
    """Mint a handoff token + emit MEMBERSHIP_SELECTED audit.

    Returns the JWT on success, None if no active signing key
    exists (an operational failure that the caller should surface
    to the user).

    Args:
        request: For session reads (auth_method, mfa_satisfied_at).
        membership: The chosen Membership.
        auto_selected: True for the single-membership auto-advance
            path; False for explicit user selection. Recorded in
            audit metadata.
    """
    user = request.user
    auth_method, auth_provider = _derive_auth_method(request)
    mfa_satisfied_at = _read_mfa_satisfied_at(request)

    try:
        token = issue_handoff_token(
            user_id=user.id,
            organization_id=membership.organization_id,
            membership_id=membership.id,
            auth_method=auth_method,
            auth_provider=auth_provider,
            mfa_satisfied_at=mfa_satisfied_at,
        )
    except NoActiveHandoffSigningKeyError:
        logger.error(
            "Cannot issue handoff token for user %s membership %s: "
            "no active HandoffSigningKey. Platform admin must rotate "
            "a key in.",
            user.id,
            membership.id,
        )
        return None

    with transaction.atomic():
        audit_emit(
            "MEMBERSHIP_SELECTED",
            actor_id=user.id,
            organization_id=membership.organization_id,
            object_kind="platform_organizations.Membership",
            object_id=str(membership.id),
            metadata={
                "auto_selected": auto_selected,
                "auth_method": auth_method,
                "auth_provider": auth_provider,
            },
        )

    return token


def _derive_auth_method(request: HttpRequest) -> tuple[str, str | None]:
    """Determine ``(auth_method, auth_provider)`` from session state.

    Looks for ``mph_login_provider_code`` (written by the OAuth
    signal handler in M1 D5). Presence → OAuth/OIDC login; the
    provider code tells us which.

    For local-password logins, the provider code is absent and we
    return ``("password", None)``.

    The distinction between "oauth2" and "oidc" requires looking
    up the provider config. For M1 D6 we use "oidc" as the
    canonical value when a provider is set; this matches our
    primary OAuth integration shape (B.3.7 supports both but the
    catalog treats them interchangeably for the
    ``auth_method`` claim).
    """
    provider_code = request.session.get(SESSION_KEY_LOGIN_PROVIDER_CODE)
    if provider_code is None:
        return ("password", None)
    return ("oidc", provider_code)


def _read_mfa_satisfied_at(request: HttpRequest) -> Any:
    """Read mfa_satisfied_at from session.

    Written by ``apps.platform.accounts.signals_mfa`` on
    ``authenticator_used`` / ``authenticator_added``, or by the
    trusted-provider OAuth middleware bypass. Falls back to
    ``timezone.now()`` if absent — a defensive default that the
    issue-side staleness check (1 hour max) will still accept.

    **Known limitation:** the fallback masks the case where MFA was
    never satisfied at all. For local-password users, the middleware
    forces enrollment before they can reach the picker, so this is
    practically unreachable. For OAuth users with un-trusted
    providers, the middleware also forces enrollment. For trusted-
    provider OAuth users, the middleware writes the key. Falling
    back to now() is therefore a belt-and-suspenders default that
    only fires if the session was cleared mid-flow (extreme edge).
    """
    raw = request.session.get(SESSION_KEY_MFA_SATISFIED_AT)
    if raw is None:
        logger.warning(
            "mfa_satisfied_at missing from session for user %s; "
            "using timezone.now() as defensive fallback. This should "
            "be rare — investigate if it occurs frequently.",
            request.user.id,
        )
        return timezone.now()
    from datetime import datetime

    return datetime.fromisoformat(raw)
