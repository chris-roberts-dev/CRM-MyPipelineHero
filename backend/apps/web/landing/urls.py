"""Public root-domain URLs."""

from __future__ import annotations

from django.urls import path

from apps.web.landing import views

app_name = "landing"

urlpatterns = [
    path("", views.LandingPageView.as_view(), name="home"),
]
