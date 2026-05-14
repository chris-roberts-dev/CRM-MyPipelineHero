"""App config for apps.common.tenancy."""

from __future__ import annotations

from django.apps import AppConfig


class TenancyConfig(AppConfig):
    name = "apps.common.tenancy"
    label = "common_tenancy"
    verbose_name = "Tenancy primitives"
