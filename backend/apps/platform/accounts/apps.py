from __future__ import annotations

from django.apps import AppConfig


class AccountsConfig(AppConfig):
    name = "apps.platform.accounts"
    label = "platform_accounts"
    verbose_name = "Platform · Accounts"
    default_auto_field = "django.db.models.BigAutoField"

    def ready(self) -> None:
        """Bind allauth signal handlers (M1 D4).

        Importing the signals module is what triggers the
        ``@receiver`` decorators to connect. The
        ``register_signal_handlers()`` call is a no-op marker that
        makes the import explicit and grep-able.
        """
        # Imported here, not at module top, so Django's app registry is
        # fully populated before we touch allauth.
        from apps.platform.accounts import signals

        signals.register_signal_handlers()
