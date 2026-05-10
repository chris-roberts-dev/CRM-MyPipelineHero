from __future__ import annotations

from django.apps import AppConfig


class SupportConfig(AppConfig):
    name = "apps.platform.support"
    label = "platform_support"
    verbose_name = "Platform · Support"
    default_auto_field = "django.db.models.BigAutoField"
