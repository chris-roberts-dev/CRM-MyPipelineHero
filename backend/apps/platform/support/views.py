"""Platform console views.

In M0 this is a thin authenticated landing page that proves the
``/platform/`` mount renders for ``is_staff`` users (H.7.1, H.7.4).

The real platform admin (tenant search, impersonation, audit review,
dead letters, OAuth/OIDC providers) lands in M1+ as separate views,
each calling the service layer for state changes (H.7.6).
"""

from __future__ import annotations

from typing import Any

from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.http import HttpResponse
from django.views.generic import TemplateView


class PlatformConsoleHomeView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    """Authenticated platform-console landing page.

    Authorization in M0 is a simple ``is_staff`` check — capability-based
    enforcement (B.6.8) wires up in M1 once the capability registry exists.
    """

    template_name = "console/home.html"
    raise_exception = False  # redirects unauthenticated users to LOGIN_URL

    def test_func(self) -> bool:
        user = self.request.user
        return bool(user.is_authenticated and user.is_staff)

    def handle_no_permission(self) -> HttpResponse:
        # If a logged-in user lacks staff, send them to the landing page
        # rather than the login flow (which would loop). M1 introduces
        # /no-active-access/ and proper redirection rules (B.4 / H.3.7).
        if self.request.user.is_authenticated:
            from django.shortcuts import redirect

            return redirect("/")
        return super().handle_no_permission()

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        ctx = super().get_context_data(**kwargs)
        ctx["page_title"] = "Platform console"
        return ctx
