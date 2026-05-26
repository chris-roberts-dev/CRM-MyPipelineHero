"""Platform console views (M1 D7 Phase 1 + Phase 2).

Phase 1 — Skeleton.
* :class:`PlatformHomeView` — root ``/platform/`` redirect.
* :class:`HandoffSigningKeysView` — placeholder (Phase 3).
* :class:`ImpersonationLogView` — placeholder (Phase 5).

Phase 2 — Read-only org/user surfaces.
* :class:`OrgListView` — paginated list with name/slug search.
* :class:`OrgDetailView` — single org with member count + metadata.
* :class:`UserSearchView` — search-driven list (no query → no results).
* :class:`UserDetailView` — single user with memberships, MFA, security.

All Phase 2 views are READ-ONLY. No state changes, no audit emission.
Phase 3 adds the signing-key state-changing endpoints; Phase 4-5
adds impersonation.

Cross-tenant read posture (B.1.5). The TenantManager doesn't auto-
filter — service-layer code uses ``for_org`` / ``for_membership``
explicitly when it wants tenant scope. The platform console is the
explicit cross-tenant exception path. We use plain ``Model.objects.all()``
queries here because the docstring on TenantManager calls out that
auto-filtering would invert the safety posture.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from django.contrib.auth import get_user_model
from django.db.models import Count, Q
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.views import View
from django.views.generic import ListView

from apps.platform.console.access import PlatformConsoleAccessMixin
from apps.platform.organizations.models import (
    Membership,
    MembershipStatus,
    Organization,
)

# ---------------------------------------------------------------------------
# Phase 1 — Skeleton views.
# ---------------------------------------------------------------------------


class PlatformHomeView(PlatformConsoleAccessMixin, View):
    """``/platform/`` — redirect to the org list."""

    def get(self, request: HttpRequest) -> HttpResponse:
        return HttpResponseRedirect(reverse("platform_console:orgs"))


class _PlatformPlaceholderView(PlatformConsoleAccessMixin, View):
    """Base class for Phase 1 placeholder views.

    Phase 2 superseded org/user placeholders. The remaining
    placeholders (signing keys, impersonation) still use this.
    """

    title: str = ""
    phase_target: str = ""
    description: str = ""

    def get(self, request: HttpRequest) -> HttpResponse:
        return render(
            request,
            "platform_console/placeholder.html",
            {
                "title": self.title,
                "phase_target": self.phase_target,
                "description": self.description,
            },
        )


class HandoffSigningKeysView(_PlatformPlaceholderView):
    title = "Handoff Signing Keys"
    phase_target = "M1 D7 Phase 3"
    description = (
        "Create, promote, retire, and emergency-rotate handoff "
        "signing keys. Phase 3 will wire the existing M1 D6 Phase 1 "
        "services to a confirmation-driven UI."
    )


class ImpersonationLogView(_PlatformPlaceholderView):
    title = "Impersonation Log"
    phase_target = "M1 D7 Phase 5"
    description = (
        "Browse past and active impersonation sessions. Phase 5 will "
        "add the start-impersonation flow and live-session list."
    )


# ---------------------------------------------------------------------------
# Phase 2 — Organizations.
# ---------------------------------------------------------------------------


class OrgListView(PlatformConsoleAccessMixin, ListView):
    """Paginated list of all tenant organizations.

    Search: ``?q=...`` matches case-insensitively against name AND
    slug. Empty query returns every org.

    Pagination: 25 per page via ``paginate_by``. Django's ListView
    handles ``?page=N`` query param automatically.

    Annotated with ``active_member_count`` so each card can show
    the active member count without N+1.
    """

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
    """Read-only org detail.

    Resolves by slug (URL-friendly + matches the tenant-subdomain
    convention used elsewhere). Shows org metadata, active member
    count, and the active membership list with role names.
    """

    def get(self, request: HttpRequest, slug: str) -> HttpResponse:
        organization = get_object_or_404(Organization, slug=slug)

        # Active memberships first, then non-active. Within each
        # group, ordered by membership creation date (oldest first
        # — owners appear first).
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
    """Search-driven user list.

    By design: empty query → empty result set. The user table can
    grow to millions of rows; we don't render a default "first 25"
    dump. The user enters an email substring and we filter.

    Search matches ``email`` icontains. Case-insensitive.
    """

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
    """Read-only user detail.

    Resolves by UUID. Shows email, staff/superuser/system/active
    flags, MFA enrollment status (boolean only, not the secret),
    security counters (last login, password changed, failed login,
    lockout), and the user's full membership list.

    Sensitive fields NEVER rendered:
    * password hash
    * totp_secret
    * backup_codes_hash
    * any OAuth tokens (those live on socialaccount.SocialToken,
      which we don't query here)
    """

    def get(self, request: HttpRequest, user_id: UUID) -> HttpResponse:
        UserModel = get_user_model()
        user = get_object_or_404(UserModel, id=user_id)

        memberships = (
            Membership.objects.filter(user=user)
            .select_related("organization")
            .order_by("organization__name")
        )

        return render(
            request,
            "platform_console/user_detail.html",
            {
                "subject_user": user,  # 'user' would shadow request.user
                "totp_enrolled": user.totp_enrolled_at is not None,
                "memberships": memberships,
            },
        )
