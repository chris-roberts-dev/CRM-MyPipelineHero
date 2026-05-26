"""Platform console views (M1 D7 Phase 1 + Phase 2 + Phase 3).

Phase 1 — Skeleton.
* :class:`PlatformHomeView` — root ``/platform/`` redirect.
* :class:`ImpersonationLogView` — placeholder (Phase 5).

Phase 2 — Read-only org/user surfaces.
* :class:`OrgListView` — paginated list with name/slug search.
* :class:`OrgDetailView` — single org with member count + metadata.
* :class:`UserSearchView` — search-driven list (no query → no results).
* :class:`UserDetailView` — single user with memberships, MFA, security.

Phase 3 — Handoff signing key management UI.
* :class:`SigningKeysListView` — list all keys with lifecycle state.
* :class:`SigningKeyCreateView` — form + POST → create.
* :class:`SigningKeyPromoteView` — confirmation + POST → promote.
* :class:`SigningKeyRetireView` — confirmation + POST → retire.
* :class:`SigningKeyEmergencyRotateView` — confirmation + POST → rotate.

All state-changing views are POST-only on the action; GET shows a
confirmation/form page. CSRF is standard Django (root domain). The
actor for audit emission is ``request.user`` — the human platform
admin doing the work.

**Emergency rotate URL design (Phase 3 finalization).** The
``emergency_rotate_handoff_signing_key`` service takes
``new_key_id`` (the operator-chosen identifier for the freshly-
created replacement key) and determines the previous primary
itself via the standard ``active_handoff_signing_keys_ordered_by_created_desc``
helper. The URL therefore does NOT take a ``<key_id>`` parameter —
the operator picks the new id on the confirmation form.
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
from django.views import View
from django.views.generic import ListView

from apps.platform.accounts.handoff.models import HandoffSigningKey
from apps.platform.accounts.handoff.services import (
    HandoffSigningKeyAlreadyExistsError,
    HandoffSigningKeyAlreadyPromotedError,
    HandoffSigningKeyAlreadyRetiredError,
    HandoffSigningKeyInvalidIdError,
    HandoffSigningKeyNotFoundError,
    HandoffSigningKeyNotPromotedError,
    TooManyActiveHandoffSigningKeysError,
    active_handoff_signing_keys_ordered_by_created_desc,
    create_handoff_signing_key,
    emergency_rotate_handoff_signing_key,
    promote_handoff_signing_key,
    retire_handoff_signing_key,
)
from apps.platform.console.access import PlatformConsoleAccessMixin
from apps.platform.organizations.models import (
    Membership,
    MembershipStatus,
    Organization,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Phase 1 — Skeleton views.
# ---------------------------------------------------------------------------


class PlatformHomeView(PlatformConsoleAccessMixin, View):
    """``/platform/`` — redirect to the org list."""

    def get(self, request: HttpRequest) -> HttpResponse:
        return HttpResponseRedirect(reverse("platform_console:orgs"))


class _PlatformPlaceholderView(PlatformConsoleAccessMixin, View):
    """Base class for placeholder views."""

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
    """Paginated list of all tenant organizations."""

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
    """Read-only org detail."""

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
    """Search-driven user list."""

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
    """Read-only user detail."""

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
                "subject_user": user,
                "totp_enrolled": user.totp_enrolled_at is not None,
                "memberships": memberships,
            },
        )


# ---------------------------------------------------------------------------
# Phase 3 — Handoff signing keys.
# ---------------------------------------------------------------------------


def _annotate_signing_key_state(
    key: HandoffSigningKey, primary_key_id: str | None
) -> dict[str, Any]:
    """Compute lifecycle state + display label for a key.

    Returns a dict with:
    * ``state``: one of "primary", "active", "pending", "retired".
    * ``state_display``: human-readable label.
    * ``css_class``: Tailwind classes for the state badge.

    Primary key determination matches the M1 D6 Phase 1 retro note:
    primary = most recent non-retired key by ``created_at`` DESC.
    """
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
    """List all handoff signing keys with lifecycle state."""

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
    """GET shows form, POST creates a new key."""

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
    """Base for promote / retire (URL-keyed by the target key_id).

    Emergency rotate does NOT inherit from this — its URL has no
    ``<key_id>`` parameter because the service determines the
    target itself.
    """

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
    """Promote a pending key to primary."""

    confirm_template = "platform_console/signing_keys_promote_confirm.html"

    def perform_action(self, *, actor_id: UUID, key_id: str) -> None:
        promote_handoff_signing_key(actor_id=actor_id, key_id=key_id)


class SigningKeyRetireView(_SigningKeyKeyedActionView):
    """Retire a key (mark unusable for future verification)."""

    confirm_template = "platform_console/signing_keys_retire_confirm.html"

    def perform_action(self, *, actor_id: UUID, key_id: str) -> None:
        retire_handoff_signing_key(actor_id=actor_id, key_id=key_id)


class SigningKeyEmergencyRotateView(PlatformConsoleAccessMixin, View):
    """Emergency rotate the current primary.

    The service determines which key is the current primary via
    ``active_handoff_signing_keys_ordered_by_created_desc()``; the
    operator provides ``new_key_id`` for the freshly-minted
    replacement.

    URL design rationale: no ``<key_id>`` URL parameter. The
    operator clicks "Emergency rotate" from the list (which shows
    next to the current primary), lands on a confirmation page
    that displays the current primary, and submits a new key_id.

    Per the M1 D6 retro: this is a zero-overlap rotation — all
    outstanding tokens become invalid. Use ONLY when compromise is
    suspected.
    """

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
