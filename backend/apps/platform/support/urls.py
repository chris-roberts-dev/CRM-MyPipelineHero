"""Platform console URLs.

Mounted at ``/platform/`` (H.7.2). M0 exposes a single landing page that
proves staff-only routing works. Cross-tenant tooling (impersonation,
tenant search, audit review) lands in M1.
"""

from __future__ import annotations

from django.urls import path

from apps.platform.support import views

app_name = "platform_console"

urlpatterns = [
    path("", views.PlatformConsoleHomeView.as_view(), name="home"),
]
