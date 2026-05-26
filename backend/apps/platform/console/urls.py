"""Platform console URLs (M1 D7 Phase 1 + Phase 2).

Phase 1 — Home + four list URLs.
Phase 2 — Org detail + user detail.
"""

from __future__ import annotations

from django.urls import path

from apps.platform.console import views

app_name = "platform_console"

urlpatterns = [
    path("", views.PlatformHomeView.as_view(), name="home"),
    # Phase 2: orgs.
    path("orgs/", views.OrgListView.as_view(), name="orgs"),
    path(
        "orgs/<slug:slug>/",
        views.OrgDetailView.as_view(),
        name="org_detail",
    ),
    # Phase 2: users.
    path("users/", views.UserSearchView.as_view(), name="users"),
    path(
        "users/<uuid:user_id>/",
        views.UserDetailView.as_view(),
        name="user_detail",
    ),
    # Phase 3: signing keys.
    path(
        "signing-keys/",
        views.HandoffSigningKeysView.as_view(),
        name="signing_keys",
    ),
    # Phase 5: impersonation.
    path(
        "impersonation/",
        views.ImpersonationLogView.as_view(),
        name="impersonation",
    ),
]
