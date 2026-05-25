"""URL configuration for the auth_portal app.

The bulk of the auth surface is mounted under /accounts/ by allauth
(see config/urls.py). This module exposes the auxiliary auth_portal
routes:

* /login/ — permanent redirect to /accounts/login/ (M1 D4).
* /select-org/ — real org picker (M1 D6 Phase 4B).
* /oauth-help/<reason>/ — OAuth-failure help page (M1 D5 Phase 3).
  Mounted outside the /accounts/ namespace to avoid resolver
  ambiguity with allauth's URLconf.
* /handoff/issue/ — POST endpoint that mints handoff tokens
  (M1 D6 Phase 4B).

The ``app_name`` namespace is ``auth_portal``; templates and the
OAuth adapter refer to routes as e.g. ``auth_portal:oauth_help``.
"""

from __future__ import annotations

from django.urls import path

from apps.web.auth_portal import views, views_oauth_help
from apps.web.auth_portal.views_handoff_issue import HandoffIssueView
from apps.web.auth_portal.views_select_org import SelectOrgView

app_name = "auth_portal"

urlpatterns = [
    path("login/", views.LoginPageView.as_view(), name="login"),
    path(
        "select-org/",
        SelectOrgView.as_view(),
        name="select_org",
    ),
    path(
        "oauth-help/<slug:reason>/",
        views_oauth_help.oauth_help,
        name="oauth_help",
    ),
    path("handoff/issue/", HandoffIssueView.as_view(), name="handoff_issue"),
]
