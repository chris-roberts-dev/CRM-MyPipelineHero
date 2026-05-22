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
            * allauth.mfa signals → record_auth_event.

        Signal handlers (M1 D5 Phase 3):
            * allauth.socialaccount signals → OAUTH_LOGIN_SUCCEEDED,
              OAUTH_ACCOUNT_UNLINKED.

        Model discovery (M1 D5 / M1 D6):
            * Subpackage models (oauth/, handoff/) are NOT auto-
              discovered by Django because they don't live in the
              app's top-level models.py. The imports below force the
              subpackages' __init__.py to run during app-ready, which
              in turn imports models.py from each subpackage and
              registers the models with Django's app registry.
              Without these imports, ``makemigrations`` would
              generate spurious DeleteModel migrations and the test
              DB schema would diverge from the production one.

        Settings loader (M1 D5 Phase 3):
            * Read active OAuthProviderConfig rows and write the
              resulting ``SOCIALACCOUNT_PROVIDERS`` dict to
              django.conf.settings. Triggered by ``post_migrate``
              rather than from ``ready()`` itself — Django warns
              against DB access during app init (the connection pool
              isn't fully initialized, and the query fires during
              ``migrate`` against potentially-unmigrated databases).
              ``post_migrate`` fires after every migration including
              the initial test-DB setup, so OAuth providers are
              loaded for every environment that has migrations
              applied.

              Tradeoff: long-running web servers don't see provider
              config changes between deploys unless a migration also
              runs. A future ``manage.py reload_oauth_providers``
              command can give operators a manual reload lever; for
              M1 D5, the per-deploy refresh is sufficient since
              provider config is platform-admin-managed and rarely
              changed at runtime.
        """
        # Import signals lazily so app loading order doesn't matter.
        from apps.platform.accounts import signals  # noqa: F401

        # Model-discovery imports — see docstring for why these are
        # needed. The `noqa: F401` is intentional; we import for the
        # side effect of registering the model with Django.
        from apps.platform.accounts.handoff import (
            models as _handoff_models,
        )  # noqa: F401
        from apps.platform.accounts.oauth import signals as oauth_signals  # noqa: F401

        # Hook the post_migrate signal — this is the ONLY place the
        # OAuth loader is called from app init. Direct DB access in
        # ready() triggers Django's "Accessing the database during
        # app initialization" warning and can fail against unmigrated
        # databases.
        post_migrate.connect(
            _reload_oauth_providers_after_migrate,
            sender=self,
            dispatch_uid="apps.platform.accounts.oauth.post_migrate_load",
        )


def _reload_oauth_providers_after_migrate(
    sender: AppConfig,
    **kwargs: object,
) -> None:
    """Handler for post_migrate: reload OAuth provider settings.

    Catches all exceptions so a problem here (e.g. missing env vars
    for one provider) does not break the migrate command. The loader
    itself already logs per-provider warnings; this layer is the
    final guard.
    """
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
