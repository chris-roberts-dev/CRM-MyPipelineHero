from __future__ import annotations

import logging
import os
from typing import Any

logger = logging.getLogger(__name__)


def _read_env_secret(env_key: str) -> str | None:
    """Read an env var; return None if missing/empty.

    Centralized so future changes (e.g. reading from a secret manager
    instead of os.environ) happen in one place.
    """
    value = os.environ.get(env_key, "")
    if not value:
        return None
    return value


def _build_openid_connect_app(config: Any) -> dict[str, Any] | None:
    """Build the per-provider 'APPS' entry for an OIDC provider.

    Returns None if the env-backed credentials aren't available; the
    caller skips the provider.
    """
    client_id = _read_env_secret(config.client_id_env_key)
    client_secret = _read_env_secret(config.client_secret_env_key)

    if not client_id or not client_secret:
        logger.warning(
            "OAuth provider %r is active but credentials are missing: "
            "client_id_env_key=%s present=%s, "
            "client_secret_env_key=%s present=%s. Skipping registration.",
            config.provider_code,
            config.client_id_env_key,
            bool(client_id),
            config.client_secret_env_key,
            bool(client_secret),
        )
        return None

    settings_block: dict[str, Any] = {
        # Allauth's openid_connect provider expects server_url to be
        # the issuer URL; it does its own /.well-known discovery from
        # there.
        "server_url": config.issuer_url
        or "",
    }
    if config.scopes:
        settings_block["scope"] = list(config.scopes)

    return {
        "provider_id": config.provider_code,
        "name": config.display_name,
        "client_id": client_id,
        "secret": client_secret,
        "settings": settings_block,
    }


def load_socialaccount_providers() -> dict[str, Any]:
    """Build the SOCIALACCOUNT_PROVIDERS dict from active configs.

    Called at app-ready time from
    ``apps.platform.accounts.apps.AccountsConfig.ready()`` (Phase 3
    wires this).

    Returns:
        A dict in allauth's ``SOCIALACCOUNT_PROVIDERS`` shape. May be
        empty if no providers are active or all active providers are
        missing env credentials.
    """
    # Imported lazily — this function is called from AppConfig.ready(),
    # at which point the app registry IS ready but importing models at
    # module top would still be discouraged.
    from apps.platform.accounts.oauth.models import (
        OAuthProviderConfig,
        ProviderType,
    )

    oidc_apps: list[dict[str, Any]] = []

    active_configs = OAuthProviderConfig.objects.filter(is_active=True).order_by(
        "display_name"
    )

    for config in active_configs:
        if config.provider_type == ProviderType.OIDC:
            entry = _build_openid_connect_app(config)
            if entry is not None:
                oidc_apps.append(entry)
        else:
            # OAUTH2 providers are not wired in Phase 1. Each OAUTH2
            # provider needs a provider-specific allauth adapter
            # (e.g. allauth.socialaccount.providers.google). They land
            # case-by-case as actual providers are approved. For M1 D5
            # the only supported provider_type for the loader is OIDC.
            logger.info(
                "OAuth provider %r has provider_type=OAUTH2; "
                "OAUTH2 providers require provider-specific allauth "
                "configuration and are not auto-loaded in M1 D5.",
                config.provider_code,
            )

    result: dict[str, Any] = {}
    if oidc_apps:
        result["openid_connect"] = {"APPS": oidc_apps}

    return result


def apply_socialaccount_providers_to_settings() -> None:
    """Mutate ``django.conf.settings.SOCIALACCOUNT_PROVIDERS`` in place.

    Called from ``AccountsConfig.ready()``. Safe to call multiple times
    (idempotent); each call rebuilds the dict from scratch.

    Note on settings mutation: Django settings are read-only by
    contract, but ``SOCIALACCOUNT_PROVIDERS`` is consumed by allauth
    at runtime (not at import time), so mutating it after Django has
    finished loading works. The alternative (database-backed allauth
    apps via ``SocialApp``) requires Django Sites + admin management
    we don't want at this stage.
    """
    from django.conf import settings

    providers = load_socialaccount_providers()
    settings.SOCIALACCOUNT_PROVIDERS = providers
    logger.info(
        "Loaded %d OAuth/OIDC provider(s) into SOCIALACCOUNT_PROVIDERS: %s",
        len(providers.get("openid_connect", {}).get("APPS", [])),
        [
            app["provider_id"]
            for app in providers.get("openid_connect", {}).get("APPS", [])
        ],
    )
