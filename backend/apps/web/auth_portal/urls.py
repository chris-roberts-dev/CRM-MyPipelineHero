"""URL configuration for the auth_portal app.

The bulk of the auth surface is mounted under /accounts/ by allauth
(see config/urls.py). This module exposes the auxiliary auth_portal
routes:

* /login/ — permanent redirect to /accounts/login/ (M1 D4).
* /select-org/ — organization-picker placeholder (M1 D6 wires the
  real picker).
* /oauth-help/<reason>/ — OAuth-failure help page (M1 D5 Phase 3).
  Mounted outside the /accounts/ namespace to avoid resolver
  ambiguity with allauth's URLconf.

The ``app_name`` namespace is ``auth_portal``; templates and the
OAuth adapter refer to routes as e.g. ``auth_portal:oauth_help``.
"""

from __future__ import annotations

from django.urls import path

from apps.web.auth_portal import views, views_oauth_help, views_select_org

app_name = "auth_portal"

urlpatterns = [
    path("login/", views.LoginPageView.as_view(), name="login"),
    path(
        "select-org/",
        views_select_org.SelectOrgPlaceholderView.as_view(),
        name="select_org",
    ),
    path(
        "oauth-help/<slug:reason>/",
        views_oauth_help.oauth_help,
        name="oauth_help",
    ),
]
