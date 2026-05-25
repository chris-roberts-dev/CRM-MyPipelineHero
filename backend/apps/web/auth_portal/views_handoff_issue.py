"""Handoff issue HTTP endpoint (M1 D6 Phase 4B, B.4.12 issue side).

POST /handoff/issue/

Form data: ``membership_id`` (UUID).

The endpoint is the user-explicit-selection counterpart to the
single-membership auto-advance code path in
:mod:`apps.web.auth_portal.views_select_org`. It validates that
the membership belongs to the requesting user and is active, mints
the handoff token, emits ``MEMBERSHIP_SELECTED`` with
``auto_selected=False``, and renders the auto-POST form.

**Security boundary.** The endpoint trusts the POST'd
``membership_id`` to identify which org the user wants. It does
NOT trust it to identify the USER — that comes from
``request.user`` (Django auth). The membership lookup is
constrained to the current user; a forged membership_id pointing
to another user's row returns 404.

CSRF protection: standard Django CSRF (this is a same-origin POST
from the picker page on root domain to the issue endpoint on root
domain).
"""

from __future__ import annotations

import logging
from uuid import UUID

from django.contrib.auth.decorators import login_required
from django.http import Http404, HttpRequest, HttpResponse, HttpResponseBadRequest
from django.utils.decorators import method_decorator
from django.views import View

from apps.platform.organizations.models import Membership, MembershipStatus
from apps.web.auth_portal.views_select_org import (
    SelectOrgView,
    _issue_token_for_membership,
)

logger = logging.getLogger(__name__)


@method_decorator(login_required, name="dispatch")
class HandoffIssueView(View):
    """POST-only handoff issue endpoint."""

    http_method_names = ["post"]

    def post(self, request: HttpRequest) -> HttpResponse:
        membership_id_raw = request.POST.get("membership_id", "").strip()
        if not membership_id_raw:
            return HttpResponseBadRequest("Missing membership_id.")

        try:
            membership_id = UUID(membership_id_raw)
        except ValueError:
            return HttpResponseBadRequest("Invalid membership_id format.")

        # Membership lookup constrained to the current user.
        # A forged ID pointing at someone else's row 404s here.
        try:
            membership = Membership.objects.select_related("organization").get(
                id=membership_id,
                user=request.user,
                status=MembershipStatus.ACTIVE,
            )
        except Membership.DoesNotExist:
            logger.info(
                "HandoffIssueView: membership_id %s not found or not "
                "active for user %s.",
                membership_id,
                request.user.id,
            )
            raise Http404("Membership not found.")

        token = _issue_token_for_membership(
            request=request,
            membership=membership,
            auto_selected=False,
        )

        if token is None:
            # No active signing key. Reuse the SelectOrgView's error
            # rendering for visual consistency.
            view = SelectOrgView()
            return view._render_no_signing_key_available(request)

        # Render the auto-POST form. Reuse SelectOrgView's helper.
        view = SelectOrgView()
        return view._render_handoff_form(request, membership=membership, token=token)
