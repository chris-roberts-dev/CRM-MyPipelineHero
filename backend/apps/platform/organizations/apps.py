"""App config for apps.platform.organizations."""

from __future__ import annotations

from django.apps import AppConfig


class OrganizationsConfig(AppConfig):
    name = "apps.platform.organizations"
    label = "platform_organizations"
    verbose_name = "Platform organizations"

    def ready(self) -> None:
        # Trigger import of scope_models so Django registers
        # MembershipScopeAssignment. Without this, the model is invisible
        # to apps.get_model() / migrations / makemigrations because
        # Django only auto-discovers models defined in models.py.
        from apps.platform.organizations import scope_models  # noqa: F401
