"""Platform console views (M1 D7 Phase 1-5).

Phase 1 — Skeleton.
Phase 2 — Read-only org/user surfaces.
Phase 3 — Handoff signing key management.
Phase 4 — Impersonation backend (no UI).
Phase 5 — Impersonation UI:
* :class:`UserImpersonateView` — confirmation + start + handoff mint.
* :class:`ImpersonationLogView` — list active + recent sessions.
* :class:`EndImpersonationFromConsoleView` — end action from console.
"""

from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

from django.contrib.auth import get_user_model
from django.db.models import Count, Q
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.utils import timezone
from django.views import View
from django.views.generic import ListView

from apps.platform.accounts.handoff.models import HandoffSigningKey
from apps.platform.accounts.handoff.services import (
    HandoffInvalidIssueParamError,
    HandoffSigningKeyAlreadyExistsError,
    HandoffSigningKeyAlreadyPromotedError,
    HandoffSigningKeyAlreadyRetiredError,
    HandoffSigningKeyInvalidIdError,
    HandoffSigningKeyNotFoundError,
    HandoffSigningKeyNotPromotedError,
    NoActiveHandoffSigningKeyError,
    TooManyActiveHandoffSigningKeysError,
    active_handoff_signing_keys_ordered_by_created_desc,
    create_handoff_signing_key,
    emergency_rotate_handoff_signing_key,
    issue_handoff_token,
    promote_handoff_signing_key,
    retire_handoff_signing_key,
)
from apps.platform.accounts.impersonation.models import (
    ImpersonationEndReason,
    ImpersonationSession,
)
from apps.platform.accounts.impersonation.services import (
    ImpersonationActorNotStaffError,
    ImpersonationAlreadyActiveError,
    ImpersonationError,
    ImpersonationMembershipInvalidError,
    ImpersonationReasonRequiredError,
    ImpersonationSelfTargetError,
    ImpersonationSessionAlreadyEndedError,
    ImpersonationSessionNotFoundError,
    ImpersonationTargetInvalidError,
    end_impersonation,
    start_impersonation,
)
from apps.platform.console.access import PlatformConsoleAccessMixin
from apps.platform.organizations.models import (
    Membership,
    MembershipStatus,
    Organization,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Phase 1 — Home redirect.
# ---------------------------------------------------------------------------


class PlatformHomeView(PlatformConsoleAccessMixin, View):
    """``/platform/`` — redirect to the org list."""

    def get(self, request: HttpRequest) -> HttpResponse:
        return HttpResponseRedirect(reverse("platform_console:orgs"))


# ---------------------------------------------------------------------------
# Phase 2 — Organizations.
# ---------------------------------------------------------------------------


class OrgListView(PlatformConsoleAccessMixin, ListView):
    template_name = "platform_console/org_list.html"
    context_object_name = "organizations"
    paginate_by = 25

    def get_queryset(self) -> Any:
        qs = (
            Organization.objects.all()
            .annotate(
                active_member_count=Count(
                    "memberships",
                    filter=Q(memberships__status=MembershipStatus.ACTIVE),
                )
            )
            .order_by("name")
        )
        query = self.request.GET.get("q", "").strip()
        if query:
            qs = qs.filter(Q(name__icontains=query) | Q(slug__icontains=query))
        return qs

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context["query"] = self.request.GET.get("q", "").strip()
        return context


class OrgDetailView(PlatformConsoleAccessMixin, View):
    def get(self, request: HttpRequest, slug: str) -> HttpResponse:
        organization = get_object_or_404(Organization, slug=slug)
        memberships = (
            Membership.objects.filter(organization=organization)
            .select_related("user")
            .order_by("-status", "created_at")
        )
        active_count = sum(
            1 for m in memberships if m.status == MembershipStatus.ACTIVE
        )
        return render(
            request,
            "platform_console/org_detail.html",
            {
                "organization": organization,
                "memberships": memberships,
                "active_member_count": active_count,
                "total_member_count": len(memberships),
            },
        )


# ---------------------------------------------------------------------------
# Phase 2 — Users.
# ---------------------------------------------------------------------------


class UserSearchView(PlatformConsoleAccessMixin, ListView):
    template_name = "platform_console/user_search.html"
    context_object_name = "users"
    paginate_by = 25

    def get_queryset(self) -> Any:
        query = self.request.GET.get("q", "").strip()
        if not query:
            return get_user_model().objects.none()
        return get_user_model().objects.filter(email__icontains=query).order_by("email")

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context["query"] = self.request.GET.get("q", "").strip()
        return context


class UserDetailView(PlatformConsoleAccessMixin, View):
    def get(self, request: HttpRequest, user_id: UUID) -> HttpResponse:
        UserModel = get_user_model()
        user = get_object_or_404(UserModel, id=user_id)
        memberships = (
            Membership.objects.filter(user=user)
            .select_related("organization")
            .order_by("organization__name")
        )

        # Phase 5: determine which memberships are eligible for
        # impersonation (ACTIVE, target is not system / not staff).
        can_impersonate = not (user.is_staff or getattr(user, "is_system", False))

        return render(
            request,
            "platform_console/user_detail.html",
            {
                "subject_user": user,
                "totp_enrolled": user.totp_enrolled_at is not None,
                "memberships": memberships,
                "can_impersonate": can_impersonate,
            },
        )


# ---------------------------------------------------------------------------
# Phase 3 — Handoff signing keys.
# ---------------------------------------------------------------------------


def _annotate_signing_key_state(
    key: HandoffSigningKey, primary_key_id: str | None
) -> dict[str, Any]:
    if key.retired_at is not None:
        return {
            "state": "retired",
            "state_display": "Retired",
            "css_class": "bg-gray-100 text-gray-800",
        }
    if key.promoted_at is None:
        return {
            "state": "pending",
            "state_display": "Pending",
            "css_class": "bg-blue-100 text-blue-800",
        }
    if primary_key_id is not None and key.key_id == primary_key_id:
        return {
            "state": "primary",
            "state_display": "Primary",
            "css_class": "bg-green-100 text-green-800",
        }
    return {
        "state": "active",
        "state_display": "Active (overlap)",
        "css_class": "bg-yellow-100 text-yellow-800",
    }


class SigningKeysListView(PlatformConsoleAccessMixin, View):
    def get(self, request: HttpRequest) -> HttpResponse:
        all_keys = list(HandoffSigningKey.objects.all().order_by("-created_at"))
        active_keys = active_handoff_signing_keys_ordered_by_created_desc()
        primary_key_id = active_keys[0].key_id if active_keys else None

        annotated_keys = [
            {
                "key": key,
                **_annotate_signing_key_state(key, primary_key_id),
            }
            for key in all_keys
        ]

        return render(
            request,
            "platform_console/signing_keys_list.html",
            {
                "annotated_keys": annotated_keys,
                "primary_key_id": primary_key_id,
                "any_active": bool(active_keys),
            },
        )


class SigningKeyCreateView(PlatformConsoleAccessMixin, View):
    def get(self, request: HttpRequest) -> HttpResponse:
        return render(
            request,
            "platform_console/signing_keys_create.html",
            {"error": None, "submitted_key_id": ""},
        )

    def post(self, request: HttpRequest) -> HttpResponse:
        key_id = request.POST.get("key_id", "").strip()

        if not key_id:
            return self._render_with_error(request, "Key ID is required.", key_id)

        try:
            create_handoff_signing_key(actor_id=request.user.id, key_id=key_id)
        except HandoffSigningKeyInvalidIdError as exc:
            return self._render_with_error(request, str(exc), key_id)
        except HandoffSigningKeyAlreadyExistsError:
            return self._render_with_error(
                request,
                f"A signing key with ID {key_id!r} already exists.",
                key_id,
            )
        except TooManyActiveHandoffSigningKeysError as exc:
            return self._render_with_error(request, str(exc), key_id)

        return HttpResponseRedirect(reverse("platform_console:signing_keys"))

    def _render_with_error(
        self, request: HttpRequest, message: str, submitted_key_id: str
    ) -> HttpResponse:
        return render(
            request,
            "platform_console/signing_keys_create.html",
            {"error": message, "submitted_key_id": submitted_key_id},
            status=400,
        )


class _SigningKeyKeyedActionView(PlatformConsoleAccessMixin, View):
    confirm_template: str = ""

    def perform_action(self, *, actor_id: UUID, key_id: str) -> None:
        raise NotImplementedError

    def get(self, request: HttpRequest, key_id: str) -> HttpResponse:
        key = get_object_or_404(HandoffSigningKey, key_id=key_id)
        return render(
            request,
            self.confirm_template,
            {"key": key, "error": None},
        )

    def post(self, request: HttpRequest, key_id: str) -> HttpResponse:
        get_object_or_404(HandoffSigningKey, key_id=key_id)

        try:
            self.perform_action(actor_id=request.user.id, key_id=key_id)
        except (
            HandoffSigningKeyNotFoundError,
            HandoffSigningKeyAlreadyPromotedError,
            HandoffSigningKeyAlreadyRetiredError,
            HandoffSigningKeyNotPromotedError,
        ) as exc:
            return self._render_with_error(request, key_id, str(exc))

        return HttpResponseRedirect(reverse("platform_console:signing_keys"))

    def _render_with_error(
        self, request: HttpRequest, key_id: str, message: str
    ) -> HttpResponse:
        key = HandoffSigningKey.objects.filter(key_id=key_id).first()
        return render(
            request,
            self.confirm_template,
            {"key": key, "error": message},
            status=400,
        )


class SigningKeyPromoteView(_SigningKeyKeyedActionView):
    confirm_template = "platform_console/signing_keys_promote_confirm.html"

    def perform_action(self, *, actor_id: UUID, key_id: str) -> None:
        promote_handoff_signing_key(actor_id=actor_id, key_id=key_id)


class SigningKeyRetireView(_SigningKeyKeyedActionView):
    confirm_template = "platform_console/signing_keys_retire_confirm.html"

    def perform_action(self, *, actor_id: UUID, key_id: str) -> None:
        retire_handoff_signing_key(actor_id=actor_id, key_id=key_id)


class SigningKeyEmergencyRotateView(PlatformConsoleAccessMixin, View):
    template_name = "platform_console/signing_keys_emergency_rotate_confirm.html"

    def get(self, request: HttpRequest) -> HttpResponse:
        active = active_handoff_signing_keys_ordered_by_created_desc()
        current_primary = active[0] if active else None
        return render(
            request,
            self.template_name,
            {
                "current_primary": current_primary,
                "error": None,
                "submitted_new_key_id": "",
            },
        )

    def post(self, request: HttpRequest) -> HttpResponse:
        new_key_id = request.POST.get("new_key_id", "").strip()

        if not new_key_id:
            return self._render_with_error(
                request,
                "New key ID is required for emergency rotation.",
                new_key_id,
            )

        try:
            emergency_rotate_handoff_signing_key(
                actor_id=request.user.id, new_key_id=new_key_id
            )
        except HandoffSigningKeyInvalidIdError as exc:
            return self._render_with_error(request, str(exc), new_key_id)
        except HandoffSigningKeyAlreadyExistsError:
            return self._render_with_error(
                request,
                f"A signing key with ID {new_key_id!r} already exists "
                f"(or matches the current primary). Choose a different ID.",
                new_key_id,
            )

        return HttpResponseRedirect(reverse("platform_console:signing_keys"))

    def _render_with_error(
        self, request: HttpRequest, message: str, submitted_new_key_id: str
    ) -> HttpResponse:
        active = active_handoff_signing_keys_ordered_by_created_desc()
        current_primary = active[0] if active else None
        return render(
            request,
            self.template_name,
            {
                "current_primary": current_primary,
                "error": message,
                "submitted_new_key_id": submitted_new_key_id,
            },
            status=400,
        )


# ---------------------------------------------------------------------------
# Phase 5 — Impersonation UI.
# ---------------------------------------------------------------------------


class UserImpersonateView(PlatformConsoleAccessMixin, View):
    """Start an impersonation session from the user detail page.

    GET: render confirmation page (target user info + membership
    picker + reason field).
    POST: validate membership_id + reason, call ``start_impersonation``,
    mint an impersonation handoff token, render auto-POST form to
    the tenant subdomain.

    The auto-POST form pattern matches the existing root-side handoff
    issue view (M1 D6 Phase 4B's HandoffIssueView).
    """

    template_name = "platform_console/user_impersonate_confirm.html"
    handoff_form_template = "platform_console/impersonate_handoff_redirect.html"

    def get(self, request: HttpRequest, user_id: UUID) -> HttpResponse:
        target_user = self._resolve_target(user_id)
        active_memberships = self._eligible_memberships(target_user)
        return render(
            request,
            self.template_name,
            {
                "target_user": target_user,
                "active_memberships": active_memberships,
                "error": None,
                "submitted_membership_id": "",
                "submitted_reason": "",
            },
        )

    def post(self, request: HttpRequest, user_id: UUID) -> HttpResponse:
        target_user = self._resolve_target(user_id)
        membership_id_raw = request.POST.get("membership_id", "").strip()
        reason = request.POST.get("reason", "")

        if not membership_id_raw:
            return self._render_with_error(
                request,
                target_user,
                "Please select a membership.",
                membership_id_raw,
                reason,
            )

        try:
            membership_id = UUID(membership_id_raw)
        except ValueError:
            return self._render_with_error(
                request,
                target_user,
                "Invalid membership selection.",
                membership_id_raw,
                reason,
            )

        # Verify the chosen membership is one of the eligible ones.
        try:
            membership = Membership.objects.select_related("organization").get(
                id=membership_id,
                user_id=user_id,
                status=MembershipStatus.ACTIVE,
            )
        except Membership.DoesNotExist:
            return self._render_with_error(
                request,
                target_user,
                "Selected membership is no longer active.",
                membership_id_raw,
                reason,
            )

        # Start the impersonation session.
        try:
            session = start_impersonation(
                admin_user_id=request.user.id,
                target_user_id=user_id,
                organization_id=membership.organization_id,
                membership_id=membership.id,
                reason=reason,
            )
        except (
            ImpersonationReasonRequiredError,
            ImpersonationSelfTargetError,
            ImpersonationTargetInvalidError,
            ImpersonationMembershipInvalidError,
            ImpersonationActorNotStaffError,
            ImpersonationAlreadyActiveError,
        ) as exc:
            return self._render_with_error(
                request,
                target_user,
                str(exc),
                membership_id_raw,
                reason,
            )
        except ImpersonationError as exc:
            # Catch-all for any future subclass.
            return self._render_with_error(
                request,
                target_user,
                f"Impersonation failed: {exc}",
                membership_id_raw,
                reason,
            )

        # Mint the impersonation handoff token. The mfa_satisfied_at
        # for impersonation handoffs is "now" — the admin's own MFA
        # gate already passed for them to reach the platform console.
        # The target user's MFA state is irrelevant for impersonation.
        try:
            token = issue_handoff_token(
                user_id=user_id,
                organization_id=membership.organization_id,
                membership_id=membership.id,
                auth_method="impersonation",
                auth_provider=None,
                mfa_satisfied_at=timezone.now(),
                impersonator_admin_id=request.user.id,
            )
        except (
            HandoffInvalidIssueParamError,
            NoActiveHandoffSigningKeyError,
        ) as exc:
            # The impersonation session was already created. End it
            # so we don't leave a dangling row.
            try:
                end_impersonation(
                    session_id=session.id,
                    ended_by_user_id=request.user.id,
                    end_reason=ImpersonationEndReason.ADMIN_ENDED,
                )
            except Exception:
                logger.exception(
                    "UserImpersonateView: failed to roll back session "
                    "%s after handoff issue failure.",
                    session.id,
                )
            return self._render_with_error(
                request,
                target_user,
                f"Could not mint handoff token: {exc}",
                membership_id_raw,
                reason,
            )

        # Render the auto-POST form targeting the tenant subdomain.
        from django.conf import settings as dj_settings

        tenant_host = dj_settings.MPH_TENANT_DOMAIN_TEMPLATE.format(
            slug=membership.organization.slug
        )
        scheme = "https" if request.is_secure() else "http"
        post_url = f"{scheme}://{tenant_host}/handoff/"

        return render(
            request,
            self.handoff_form_template,
            {
                "post_url": post_url,
                "tenant_host": tenant_host,
                "token": token,
                "org_name": membership.organization.name,
            },
        )

    def _resolve_target(self, user_id: UUID) -> Any:
        UserModel = get_user_model()
        return get_object_or_404(UserModel, id=user_id)

    def _eligible_memberships(self, target_user: Any) -> list[Any]:
        """Active memberships eligible for impersonation."""
        return list(
            Membership.objects.filter(user=target_user, status=MembershipStatus.ACTIVE)
            .select_related("organization")
            .order_by("organization__name")
        )

    def _render_with_error(
        self,
        request: HttpRequest,
        target_user: Any,
        message: str,
        submitted_membership_id: str,
        submitted_reason: str,
    ) -> HttpResponse:
        return render(
            request,
            self.template_name,
            {
                "target_user": target_user,
                "active_memberships": self._eligible_memberships(target_user),
                "error": message,
                "submitted_membership_id": submitted_membership_id,
                "submitted_reason": submitted_reason,
            },
            status=400,
        )


class ImpersonationLogView(PlatformConsoleAccessMixin, View):
    """List active + recent impersonation sessions.

    Active sessions at the top, then the 50 most-recent ended
    sessions. Each row links to org/user detail and offers an
    "End" action for active sessions.
    """

    def get(self, request: HttpRequest) -> HttpResponse:
        active_sessions = list(
            ImpersonationSession.objects.filter(ended_at__isnull=True)
            .select_related("admin_user", "target_user", "organization")
            .order_by("-started_at")
        )
        recent_sessions = list(
            ImpersonationSession.objects.filter(ended_at__isnull=False)
            .select_related(
                "admin_user", "target_user", "organization", "ended_by_user"
            )
            .order_by("-ended_at")[:50]
        )
        return render(
            request,
            "platform_console/impersonation_log.html",
            {
                "active_sessions": active_sessions,
                "recent_sessions": recent_sessions,
            },
        )


class EndImpersonationFromConsoleView(PlatformConsoleAccessMixin, View):
    """End an impersonation session from the platform console.

    GET: render a confirmation page with session details.
    POST: call ``end_impersonation`` with end_reason=ADMIN_ENDED.

    The admin's tenant session (if their browser still holds it)
    will be force-flushed by the ``EnforceImpersonationLiveness``
    middleware on the next tenant request.
    """

    template_name = "platform_console/impersonation_end_confirm.html"

    def get(self, request: HttpRequest, session_id: UUID) -> HttpResponse:
        session = get_object_or_404(
            ImpersonationSession.objects.select_related(
                "admin_user", "target_user", "organization"
            ),
            id=session_id,
        )
        return render(
            request,
            self.template_name,
            {"session": session, "error": None},
        )

    def post(self, request: HttpRequest, session_id: UUID) -> HttpResponse:
        session = get_object_or_404(
            ImpersonationSession.objects.select_related(
                "admin_user", "target_user", "organization"
            ),
            id=session_id,
        )

        try:
            end_impersonation(
                session_id=session.id,
                ended_by_user_id=request.user.id,
                end_reason=ImpersonationEndReason.ADMIN_ENDED,
            )
        except ImpersonationSessionNotFoundError as exc:
            return render(
                request,
                self.template_name,
                {"session": session, "error": str(exc)},
                status=400,
            )
        except ImpersonationSessionAlreadyEndedError as exc:
            return render(
                request,
                self.template_name,
                {"session": session, "error": str(exc)},
                status=400,
            )

        return HttpResponseRedirect(reverse("platform_console:impersonation"))
