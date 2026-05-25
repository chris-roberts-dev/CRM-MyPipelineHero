"""Tenant-portal views (M1 D6 Phase 4B)."""

from __future__ import annotations

import logging

from django.conf import settings
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

    Not ``@login_required`` because the redirect target for
    unauthenticated tenant requests is on the ROOT domain
    (``mph.local/select-org/``), not the tenant subdomain. Django's
    ``@login_required`` would redirect to ``LOGIN_URL`` on the
    current host, which doesn't exist in the tenant URLconf. The
    session-key check below routes the user back to the root domain
    where they can pick an org.
    """

    def get(self, request: HttpRequest) -> HttpResponse:
        organization_id = request.session.get(SESSION_KEY_ORGANIZATION_ID)
        membership_id = request.session.get(SESSION_KEY_MEMBERSHIP_ID)

        if organization_id is None or membership_id is None:
            # User reached the tenant landing without going through
            # handoff. Send them back to the root-domain picker.
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
