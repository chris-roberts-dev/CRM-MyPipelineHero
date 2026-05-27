"""Tenant-portal views (M1 D6 Phase 4B + Phase 5, M1 D7 Phase 5)."""

from __future__ import annotations

import logging
from uuid import UUID

from django.conf import settings
from django.contrib.auth import get_user_model
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
    SESSION_KEY_IMPERSONATOR_ADMIN_ID,
    SESSION_KEY_MEMBERSHIP_ID,
    SESSION_KEY_ORGANIZATION_ID,
    HandoffInvalidError,
    consume_handoff_token,
    establish_tenant_session,
)
from apps.platform.accounts.impersonation.models import (
    ImpersonationEndReason,
    ImpersonationSession,
)
from apps.platform.accounts.impersonation.services import (
    ImpersonationSessionAlreadyEndedError,
    ImpersonationSessionNotFoundError,
    end_impersonation,
)
from apps.platform.accounts.services import record_auth_event

logger = logging.getLogger(__name__)


def _root_domain_url(request: HttpRequest, path: str) -> str:
    scheme = "https" if request.is_secure() else "http"
    return f"{scheme}://{settings.MPH_ROOT_DOMAIN}{path}"


def _impersonation_context_for_session(
    request: HttpRequest,
) -> dict[str, object] | None:
    """Build template context for the impersonation banner.

    Returns None if this is not an impersonation session. Returns a
    dict with admin email, session id, and a flag for the template
    when it IS an impersonation session.

    Single DB hit (admin user lookup). The session row liveness is
    enforced by ``EnforceImpersonationLiveness`` middleware before
    this view runs, so we can trust the session key here.
    """
    impersonator_raw = request.session.get(SESSION_KEY_IMPERSONATOR_ADMIN_ID)
    if impersonator_raw is None:
        return None

    try:
        impersonator_id = UUID(impersonator_raw)
    except (TypeError, ValueError):
        # Malformed session key — middleware should have caught it,
        # but be defensive.
        return None

    # Active session by admin id (the middleware verified it exists).
    active_session = ImpersonationSession.objects.active_for_admin(impersonator_id)
    if active_session is None:
        return None

    UserModel = get_user_model()
    try:
        admin = UserModel.objects.get(id=impersonator_id)
    except UserModel.DoesNotExist:
        return None

    return {
        "impersonation_active": True,
        "impersonation_admin_email": admin.email,
        "impersonation_session_id": active_session.id,
    }


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
    """GET-only tenant landing page after handoff."""

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

        context: dict[str, object] = {
            "organization": organization,
            "user": request.user,
        }
        impersonation_ctx = _impersonation_context_for_session(request)
        if impersonation_ctx is not None:
            context.update(impersonation_ctx)

        return render(request, "tenant_portal/landing.html", context)


class TenantLogoutView(View):
    """Tenant-local logout (M1 D6 Phase 5, B.4.17, M1 D7 Phase 5).

    M1 D7 Phase 5: if this is an impersonation session, end the
    underlying ImpersonationSession (with end_reason=LOGOUT) BEFORE
    flushing the Django session. Audit emits both
    ``IMPERSONATION_ENDED`` (from the service) and
    ``TENANT_SESSION_LOGOUT`` (here).
    """

    http_method_names = ["post"]

    def post(self, request: HttpRequest) -> HttpResponse:
        if not request.user.is_authenticated:
            return HttpResponseRedirect(_root_domain_url(request, "/select-org/"))

        user_id: UUID = request.user.id
        organization_id_raw = request.session.get(SESSION_KEY_ORGANIZATION_ID)
        membership_id_raw = request.session.get(SESSION_KEY_MEMBERSHIP_ID)
        impersonator_raw = request.session.get(SESSION_KEY_IMPERSONATOR_ADMIN_ID)

        organization_id = UUID(organization_id_raw) if organization_id_raw else None

        # M1 D7 Phase 5: end the impersonation session row before
        # logout flushes the Django session. If for any reason the
        # session was already ended (race with platform-console
        # end), tolerate that and continue with logout.
        if impersonator_raw is not None:
            try:
                impersonator_id = UUID(impersonator_raw)
                active = ImpersonationSession.objects.active_for_admin(impersonator_id)
                if active is not None:
                    try:
                        end_impersonation(
                            session_id=active.id,
                            ended_by_user_id=user_id,
                            end_reason=ImpersonationEndReason.LOGOUT,
                        )
                    except (
                        ImpersonationSessionNotFoundError,
                        ImpersonationSessionAlreadyEndedError,
                    ):
                        # Concurrent end from another path — fine.
                        logger.info(
                            "TenantLogoutView: impersonation session "
                            "already ended for admin %s.",
                            impersonator_id,
                        )
            except (TypeError, ValueError):
                logger.warning(
                    "TenantLogoutView: malformed impersonator session "
                    "key %r; skipping impersonation-end.",
                    impersonator_raw,
                )

        # TENANT_SESSION_LOGOUT audit FIRST — django_logout flushes
        # the session and we still need access to the values.
        logout_metadata: dict[str, object | None] = {
            "host": request.get_host().split(":", 1)[0],
            "membership_id": membership_id_raw,
        }
        if impersonator_raw is not None:
            logout_metadata["impersonator_admin_id"] = impersonator_raw

        record_auth_event(
            event_type="TENANT_SESSION_LOGOUT",
            actor_id=user_id,
            organization_id=organization_id,
            object_kind="platform_accounts.User",
            object_id=str(user_id),
            metadata=logout_metadata,
        )

        django_logout(request)
        return HttpResponseRedirect(_root_domain_url(request, "/select-org/"))


class EndImpersonationFromTenantView(View):
    """End-impersonation action from the tenant-side banner.

    POSTed when the admin clicks "End impersonation" on the banner.
    Calls ``end_impersonation`` with ``end_reason=ADMIN_ENDED``, then
    flushes the tenant session and redirects to root.

    Only fires if this is genuinely an impersonation session. If
    the user clicks this on a non-impersonation session (which the
    UI shouldn't allow, but defensive), returns a redirect to root
    without changing state.
    """

    http_method_names = ["post"]

    def post(self, request: HttpRequest) -> HttpResponse:
        if not request.user.is_authenticated:
            return HttpResponseRedirect(_root_domain_url(request, "/select-org/"))

        impersonator_raw = request.session.get(SESSION_KEY_IMPERSONATOR_ADMIN_ID)
        if impersonator_raw is None:
            return HttpResponseRedirect("/")

        try:
            impersonator_id = UUID(impersonator_raw)
        except (TypeError, ValueError):
            logger.warning(
                "EndImpersonationFromTenantView: malformed "
                "impersonator session key; flushing session.",
            )
            django_logout(request)
            return HttpResponseRedirect(_root_domain_url(request, "/select-org/"))

        active = ImpersonationSession.objects.active_for_admin(impersonator_id)
        if active is not None:
            # The admin (who is the actor here, since they're the
            # ones impersonating) is ending their own session.
            try:
                end_impersonation(
                    session_id=active.id,
                    ended_by_user_id=impersonator_id,
                    end_reason=ImpersonationEndReason.ADMIN_ENDED,
                )
            except (
                ImpersonationSessionNotFoundError,
                ImpersonationSessionAlreadyEndedError,
            ):
                logger.info(
                    "EndImpersonationFromTenantView: session already "
                    "ended for admin %s.",
                    impersonator_id,
                )

        django_logout(request)
        return HttpResponseRedirect(_root_domain_url(request, "/select-org/"))
