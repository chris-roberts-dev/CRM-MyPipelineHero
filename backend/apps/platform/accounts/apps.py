"""AppConfig for the accounts app.

Wires signal handlers and (M1 D5) loads OAuthProviderConfig rows
into ``SOCIALACCOUNT_PROVIDERS`` via the post_migrate signal.
"""

from __future__ import annotations

import logging

from django.apps import AppConfig
from django.db.models.signals import post_migrate

logger = logging.getLogger(__name__)


class AccountsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.platform.accounts"
    label = "platform_accounts"
    verbose_name = "Platform / Accounts"

    def ready(self) -> None:
        """Wire signal handlers and the post_migrate OAuth loader.

        Signal handlers (M1 D4):
            * allauth account-app signals → record_auth_event.
            * allauth.mfa lifecycle signals → record_auth_event.

        Signal handlers (M1 D5 Phase 3):
            * allauth.socialaccount signals → OAUTH_LOGIN_SUCCEEDED,
              OAUTH_ACCOUNT_UNLINKED.

        Signal handlers (M1 D6 Phase 4A):
            * allauth.mfa.signals.authenticator_used and
              authenticator_added → write
              ``mph_mfa_satisfied_at`` to session for downstream
              consumption by the org picker / handoff token issue.

        Signal handlers (M1 D6 Phase 5):
            * allauth.account.signals.user_logged_out → on root
              logout, revoke outstanding handoff tokens via the
              user_handoffs:{uid} Redis index and emit
              ``ROOT_SESSION_LOGOUT``. Tenant logouts are no-ops
              here (tenant view emits its own audit).

        Model discovery (M1 D5 / M1 D6):
            * Subpackage models (oauth/, handoff/) are NOT auto-
              discovered by Django because they don't live in the
              app's top-level models.py. The imports below force
              the subpackages' __init__.py to run during app-
              ready, which in turn imports models.py from each
              subpackage and registers the models with Django's
              app registry. Without these imports,
              ``makemigrations`` would generate spurious DeleteModel
              migrations and the test DB schema would diverge from
              the production one.

        Settings loader (M1 D5 Phase 3):
            * Read active OAuthProviderConfig rows and write the
              resulting ``SOCIALACCOUNT_PROVIDERS`` dict to
              django.conf.settings. Triggered by ``post_migrate``
              rather than from ``ready()`` itself — Django warns
              against DB access during app init.
        """
        # Import signals lazily so app loading order doesn't matter.
        from apps.platform.accounts import (
            signals,  # noqa: F401
            signals_logout,  # noqa: F401
            signals_mfa,  # noqa: F401
        )

        # Model-discovery imports — see docstring for why these are
        # needed. The `noqa: F401` is intentional; we import for the
        # side effect of registering the model with Django.
        from apps.platform.accounts.oauth import signals as oauth_signals  # noqa: F401

        # Hook the post_migrate signal — this is the ONLY place the
        # OAuth loader is called from app init.
        post_migrate.connect(
            _reload_oauth_providers_after_migrate,
            sender=self,
            dispatch_uid="apps.platform.accounts.oauth.post_migrate_load",
        )


def _reload_oauth_providers_after_migrate(
    sender: AppConfig,
    **kwargs: object,
) -> None:
    """Handler for post_migrate: reload OAuth provider settings."""
    try:
        from apps.platform.accounts.oauth.loader import (
            apply_socialaccount_providers_to_settings,
        )

        apply_socialaccount_providers_to_settings()
    except Exception as exc:
        logger.warning(
            "Could not reload OAuth providers after migrate (%s: %s).",
            type(exc).__name__,
            exc,
        )
