"""Auth-portal views (M0 scaffold).

In M0 ``LoginPageView`` renders the styled login form so the landing
page's sign-in CTA reaches a real, well-designed page. POST does not
authenticate yet — full login lands in M1 against django-allauth
(B.3.2, B.4.3).
"""

from __future__ import annotations

from typing import Any

from django.urls import reverse
from django.views.generic import FormView

from apps.web.auth_portal.forms import LoginForm


class LoginPageView(FormView):
    template_name = "auth_portal/login.html"
    form_class = LoginForm

    def get_initial(self) -> dict[str, Any]:
        initial = super().get_initial()
        next_url = self.request.GET.get("next") or ""
        if next_url:
            initial["next"] = next_url
        return initial

    def get_success_url(self) -> str:
        # Wired up in M1. Stays harmless in M0.
        return reverse("landing:home")

    def form_valid(self, form: LoginForm) -> Any:
        # M0: explicitly do NOT authenticate. M1 replaces this view body
        # with the allauth-backed login flow (B.4.3).
        form.add_error(
            None,
            "Authentication is not yet wired up in M0. Full login lands in M1.",
        )
        return self.form_invalid(form)
