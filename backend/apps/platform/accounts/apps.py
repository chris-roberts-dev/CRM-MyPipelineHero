from __future__ import annotations

from django.apps import AppConfig


class AccountsConfig(AppConfig):
    name = "apps.platform.accounts"
    label = "platform_accounts"
    verbose_name = "Platform · Accounts"
    default_auto_field = "django.db.models.BigAutoField"
