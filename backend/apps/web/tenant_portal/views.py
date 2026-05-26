"""Tenant-portal views (M1 D6 Phase 4B + Phase 5)."""

from __future__ import annotations

import logging
from uuid import UUID

from django.conf import settings
from django.contrib.auth import logout as django_logout
from django.http import (
    HttpRequest,
    HttpResponse,
    HttpResponseBadRequest,
    HttpResponseRedirect,
)
from django.shortcuts import render
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt

from apps.platform.accounts.handoff.services import (
    SESSION_KEY_MEMBERSHIP_ID,
    SESSION_KEY_ORGANIZATION_ID,
    HandoffInvalidError,
    consume_handoff_token,
    establish_tenant_session,
)
from apps.platform.accounts.services import record_auth_event

logger = logging.getLogger(__name__)


def _root_domain_url(request: HttpRequest, path: str) -> str:
    scheme = "https" if request.is_secure() else "http"
    return f"{scheme}://{settings.MPH_ROOT_DOMAIN}{path}"


@method_decorator(csrf_exempt, name="dispatch")
class HandoffConsumeView(View):
    """POST receiver for cross-domain handoff."""

    http_method_names = ["post"]

    def post(self, request: HttpRequest) -> HttpResponse:
        token = request.POST.get("token", "").strip()
        if not token:
            return HttpResponseBadRequest("Missing handoff token.")

        try:
            handoff_result = consume_handoff_token(token=token, request=request)
        except HandoffInvalidError as exc:
            logger.info(
                "HandoffConsumeView: token rejected (reason=%s) on host %s.",
                exc.reason,
                request.get_host(),
            )
            return self._render_handoff_failure(request, reason=exc.reason)

        establish_tenant_session(request=request, handoff_result=handoff_result)
        return HttpResponseRedirect("/")

    def _render_handoff_failure(
        self, request: HttpRequest, *, reason: str
    ) -> HttpResponse:
        return render(
            request,
            "tenant_portal/handoff_failed.html",
            {
                "_internal_reason": reason,
                "try_again_url": _root_domain_url(request, "/select-org/"),
            },
            status=400,
        )


class TenantLandingView(View):
    """GET-only tenant landing page after handoff.

    Not ``@login_required``; the redirect target for unauthenticated
    tenant requests is on the ROOT domain (``mph.local/select-org/``).
    """

    def get(self, request: HttpRequest) -> HttpResponse:
        organization_id = request.session.get(SESSION_KEY_ORGANIZATION_ID)
        membership_id = request.session.get(SESSION_KEY_MEMBERSHIP_ID)

        if organization_id is None or membership_id is None:
            return HttpResponseRedirect(_root_domain_url(request, "/select-org/"))

        from apps.platform.organizations.models import Organization

        try:
            organization = Organization.objects.get(id=organization_id)
        except Organization.DoesNotExist:
            logger.warning(
                "TenantLandingView: session claims org %s for user %s "
                "but no such org exists.",
                organization_id,
                request.user.id if request.user.is_authenticated else "anon",
            )
            return HttpResponse("Organization not found.", status=404)

        return render(
            request,
            "tenant_portal/landing.html",
            {
                "organization": organization,
                "user": request.user,
            },
        )


class TenantLogoutView(View):
    """Tenant-local logout (M1 D6 Phase 5, B.4.17).

    Destroys ONLY this tenant's session. The root-domain session
    remains intact; other tenant sessions remain intact. Outstanding
    handoff tokens for this user are NOT revoked — root-domain
    logout owns that.

    POST-only (CSRF-protected by Django's normal CSRF middleware,
    which DOES protect tenant subdomain requests — only the cross-
    domain handoff consume endpoint needs ``@csrf_exempt``).

    Emits ``TENANT_SESSION_LOGOUT`` BEFORE calling
    ``django.contrib.auth.logout()`` so we still have access to
    ``request.user.id`` and the B.4.14 session keys for the audit
    payload. The ``user_logged_out`` signal handler in
    ``apps.platform.accounts.signals_logout`` detects this is a
    tenant host and skips the root-logout revocation path.
    """

    http_method_names = ["post"]

    def post(self, request: HttpRequest) -> HttpResponse:
        # If somehow we end up here without a tenant session, just
        # redirect to root picker — no audit event, no logout call.
        if not request.user.is_authenticated:
            return HttpResponseRedirect(_root_domain_url(request, "/select-org/"))

        user_id: UUID = request.user.id
        organization_id_raw = request.session.get(SESSION_KEY_ORGANIZATION_ID)
        membership_id_raw = request.session.get(SESSION_KEY_MEMBERSHIP_ID)

        # Capture session state before logout flushes it.
        organization_id = UUID(organization_id_raw) if organization_id_raw else None

        # Audit FIRST — django_logout() flushes the session and
        # fires the user_logged_out signal. Doing audit here keeps
        # the emission near the actual state change and avoids
        # depending on the signal handler for tenant-logout audit.
        record_auth_event(
            event_type="TENANT_SESSION_LOGOUT",
            actor_id=user_id,
            organization_id=organization_id,
            object_kind="platform_accounts.User",
            object_id=str(user_id),
            metadata={
                "host": request.get_host().split(":", 1)[0],
                "membership_id": membership_id_raw,
            },
        )

        # Now log out. This calls request.session.flush() and fires
        # the user_logged_out signal. The signal handler in
        # signals_logout.py sees this is a tenant host and skips
        # token revocation.
        django_logout(request)

        return HttpResponseRedirect(_root_domain_url(request, "/select-org/"))
