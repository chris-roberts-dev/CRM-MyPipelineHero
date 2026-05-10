"""Auth-portal URLs.

M0 ships only ``/login/`` as a scaffold (the styled form renders but
does not authenticate yet). M1 introduces:

    /login/              POST handler against allauth
    /login/2fa/          TOTP challenge
    /login/2fa/enroll/   First-time TOTP enrollment
    /select-org/         Org picker → handoff token issue
    /forgot-password/
    /reset-password/
    /accept-invite/
    /no-active-access/
    /logout/
"""

from __future__ import annotations

from django.urls import path

from apps.web.auth_portal import views

app_name = "auth_portal"

urlpatterns = [
    path("login/", views.LoginPageView.as_view(), name="login"),
]
