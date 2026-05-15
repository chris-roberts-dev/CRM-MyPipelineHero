"""Auth-portal URLs.

M0 shipped ``/login/`` as a scaffold. M1 D4 keeps ``/login/`` as a
permanent redirect to allauth's canonical ``/accounts/login/`` so
historical links don't break, and adds the ``/select-org/``
placeholder so the post-login redirect target resolves.

Real org-picker behavior lands in M1 D6. Until then, the placeholder
view renders a minimal "membership routing pending" page.

Endpoints owned by allauth (mounted at ``/accounts/`` in config/urls.py):

    /accounts/login/           POST handler (B.4.3)
    /accounts/logout/          logout
    /accounts/signup/          self-signup (gated by ACCOUNT_EMAIL_VERIFICATION)
    /accounts/password/reset/  password reset request
    /accounts/password/change/ password change (authenticated)
    /accounts/email/           email management
    /accounts/2fa/             MFA index
    /accounts/2fa/totp/        TOTP enrollment / deactivation
    /accounts/2fa/recovery-codes/  recovery-code management
    /accounts/2fa/authenticate/    MFA challenge
    /accounts/reauthenticate/  sensitive-action re-auth (B.4.10)
"""

from __future__ import annotations

from django.urls import path

from apps.web.auth_portal import views, views_select_org

app_name = "auth_portal"

urlpatterns = [
    path("login/", views.LoginPageView.as_view(), name="login"),
    path(
        "select-org/",
        views_select_org.SelectOrgPlaceholderView.as_view(),
        name="select_org",
    ),
]
