"""Platform console URLs (M1 D7 Phase 1 + Phase 2 + Phase 3).

Phase 3 emergency-rotate URL has NO ``<key_id>`` parameter.
The service determines the current primary itself; the operator
provides ``new_key_id`` via the confirmation form.
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
    # Emergency rotate has NO <key_id> — service determines primary.
    # Placed BEFORE the keyed paths so /emergency-rotate/ isn't
    # mistakenly matched as <key_id>=emergency-rotate (Django's URL
    # resolver matches in order).
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
    # Phase 5: impersonation.
    path(
        "impersonation/",
        views.ImpersonationLogView.as_view(),
        name="impersonation",
    ),
]
