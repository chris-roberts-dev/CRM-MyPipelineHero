"""Org-picker placeholder view (M1 D4).

The real organization picker (B.4 §B.4.3, H.3.7) is M1 D6 work:
it loads the authenticated user's ACTIVE memberships, branches on
0 / 1 / 2+, and either renders the picker UI, issues a handoff
token to the single-tenant subdomain, or shows the "no active
access" page.

M1 D4 only needs `/select-org/` to be a valid landing target so the
allauth login flow has somewhere to redirect to. This placeholder
view satisfies that requirement and intentionally does NOTHING else:

* It requires authentication (so the login flow has succeeded).
* It does not query Membership.
* It does not issue handoff tokens.
* It does not redirect to a subdomain.

It renders a one-line message that makes it obvious to anyone
landing here in M1 D4 that the picker is not yet implemented.
"""

from __future__ import annotations

from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse
from django.utils.decorators import method_decorator
from django.views.generic import TemplateView


@method_decorator(login_required, name="dispatch")
class SelectOrgPlaceholderView(TemplateView):
    """Lands authenticated users post-login; M1 D6 replaces with real picker."""

    template_name = "auth_portal/select_org_placeholder.html"

    def get_context_data(self, **kwargs: object) -> dict[str, object]:
        ctx = super().get_context_data(**kwargs)
        ctx["user_email"] = (
            self.request.user.email if self.request.user.is_authenticated else ""
        )
        return ctx

    def get(
        self, request: HttpRequest, *args: object, **kwargs: object
    ) -> HttpResponse:
        # Force a fresh response (no caching) so this placeholder never
        # gets stuck in front of the real picker once M1 D6 ships.
        response = super().get(request, *args, **kwargs)
        response["Cache-Control"] = "no-store"
        return response
