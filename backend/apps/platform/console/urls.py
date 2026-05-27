"""Platform console URLs (M1 D7 Phase 1-5)."""

from __future__ import annotations

from django.urls import path

from apps.platform.console import views

app_name = "platform_console"

urlpatterns = [
    path("", views.PlatformHomeView.as_view(), name="home"),
    # Phase 2: orgs.
    path("orgs/", views.OrgListView.as_view(), name="orgs"),
    path("orgs/<slug:slug>/", views.OrgDetailView.as_view(), name="org_detail"),
    # Phase 2: users.
    path("users/", views.UserSearchView.as_view(), name="users"),
    path(
        "users/<uuid:user_id>/",
        views.UserDetailView.as_view(),
        name="user_detail",
    ),
    # Phase 5: impersonate from user detail.
    path(
        "users/<uuid:user_id>/impersonate/",
        views.UserImpersonateView.as_view(),
        name="user_impersonate",
    ),
    # Phase 3: handoff signing keys.
    path(
        "signing-keys/",
        views.SigningKeysListView.as_view(),
        name="signing_keys",
    ),
    path(
        "signing-keys/create/",
        views.SigningKeyCreateView.as_view(),
        name="signing_keys_create",
    ),
    path(
        "signing-keys/emergency-rotate/",
        views.SigningKeyEmergencyRotateView.as_view(),
        name="signing_keys_emergency_rotate",
    ),
    path(
        "signing-keys/<str:key_id>/promote/",
        views.SigningKeyPromoteView.as_view(),
        name="signing_keys_promote",
    ),
    path(
        "signing-keys/<str:key_id>/retire/",
        views.SigningKeyRetireView.as_view(),
        name="signing_keys_retire",
    ),
    # Phase 5: impersonation log + end action.
    path(
        "impersonation/",
        views.ImpersonationLogView.as_view(),
        name="impersonation",
    ),
    path(
        "impersonation/<uuid:session_id>/end/",
        views.EndImpersonationFromConsoleView.as_view(),
        name="impersonation_end",
    ),
]
