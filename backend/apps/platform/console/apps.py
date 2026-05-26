"""AppConfig for the platform console app."""

from __future__ import annotations

from django.apps import AppConfig


class PlatformConsoleConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.platform.console"
    label = "platform_console"
    verbose_name = "Platform / Console"
