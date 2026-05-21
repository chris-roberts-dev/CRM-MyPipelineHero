"""J.3.9 #7 — provider client secret is loaded from env/secret source.

The OAuthProviderConfig model stores ONLY the env-var key NAMES
(client_id_env_key, client_secret_env_key). The actual credentials
are read from ``os.environ`` at startup by the loader. This file
verifies that:

1. The loaded SOCIALACCOUNT_PROVIDERS dict carries values from
   ``os.environ``, not from the DB row.
2. Changing the env var (without changing the DB row) changes the
   loaded value on next reload.
3. A missing env var causes the provider to be skipped (Phase 1
   behavior re-confirmed at the settings layer).
4. The OAuthProviderConfig model has no field that could hold a
   plaintext secret.
"""

from __future__ import annotations

from typing import Any

import pytest
from django.conf import settings

from apps.platform.accounts.oauth import OAuthProviderConfig, ProviderType
from apps.platform.accounts.oauth.loader import (
    apply_socialaccount_providers_to_settings,
)


def _create_provider(*, provider_code: str = "settings-test") -> OAuthProviderConfig:
    return OAuthProviderConfig.objects.create(
        provider_code=provider_code,
        display_name=f"Settings Test {provider_code}",
        provider_type=ProviderType.OIDC,
        issuer_url="https://issuer.example.test",
        client_id_env_key=f"OAUTH_{provider_code.upper().replace('-', '_')}_CLIENT_ID",
        client_secret_env_key=f"OAUTH_{provider_code.upper().replace('-', '_')}_CLIENT_SECRET",
        is_active=True,
    )


@pytest.mark.django_db
class TestClientSecretLoadedFromEnv:
    """J.3.9 #7: secret comes from env, not from DB."""

    def test_loaded_secret_matches_env_var_value(self, monkeypatch: Any) -> None:
        _create_provider(provider_code="env-load")
        monkeypatch.setenv("OAUTH_ENV_LOAD_CLIENT_ID", "env-id-value")
        monkeypatch.setenv("OAUTH_ENV_LOAD_CLIENT_SECRET", "env-secret-value")

        apply_socialaccount_providers_to_settings()

        providers = settings.SOCIALACCOUNT_PROVIDERS
        apps = providers["openid_connect"]["APPS"]
        env_load_app = next(a for a in apps if a["provider_id"] == "env-load")
        assert env_load_app["client_id"] == "env-id-value"
        assert env_load_app["secret"] == "env-secret-value"

    def test_changing_env_var_changes_loaded_secret_on_reload(
        self, monkeypatch: Any
    ) -> None:
        _create_provider(provider_code="env-reload")
        monkeypatch.setenv("OAUTH_ENV_RELOAD_CLIENT_ID", "id-v1")
        monkeypatch.setenv("OAUTH_ENV_RELOAD_CLIENT_SECRET", "secret-v1")
        apply_socialaccount_providers_to_settings()

        apps_v1 = settings.SOCIALACCOUNT_PROVIDERS["openid_connect"]["APPS"]
        v1 = next(a for a in apps_v1 if a["provider_id"] == "env-reload")
        assert v1["secret"] == "secret-v1"

        # Rotate the env var, reload.
        monkeypatch.setenv("OAUTH_ENV_RELOAD_CLIENT_SECRET", "secret-v2")
        apply_socialaccount_providers_to_settings()

        apps_v2 = settings.SOCIALACCOUNT_PROVIDERS["openid_connect"]["APPS"]
        v2 = next(a for a in apps_v2 if a["provider_id"] == "env-reload")
        assert v2["secret"] == "secret-v2"

    def test_missing_secret_env_var_skips_provider(self, monkeypatch: Any) -> None:
        _create_provider(provider_code="env-missing")
        monkeypatch.setenv("OAUTH_ENV_MISSING_CLIENT_ID", "id-only")
        monkeypatch.delenv("OAUTH_ENV_MISSING_CLIENT_SECRET", raising=False)

        apply_socialaccount_providers_to_settings()

        apps = settings.SOCIALACCOUNT_PROVIDERS.get("openid_connect", {}).get(
            "APPS", []
        )
        assert all(a["provider_id"] != "env-missing" for a in apps)


@pytest.mark.django_db
class TestModelDoesNotStoreSecrets:
    """Belt and suspenders: model surface has no plaintext-secret field."""

    def test_model_fields_have_no_secret_column(self) -> None:
        field_names = {f.name for f in OAuthProviderConfig._meta.get_fields()}
        # Only the env-var KEY NAMES are columns.
        assert "client_id_env_key" in field_names
        assert "client_secret_env_key" in field_names
        # No raw secret column.
        assert "client_id" not in field_names
        assert "client_secret" not in field_names
        assert "secret" not in field_names

    def test_model_str_does_not_expose_env_key_value(self) -> None:
        """A platform admin viewing __str__ should see the provider
        identity, not the env-var key name (the env-var key name is
        less sensitive than the secret itself, but exposing it
        widely-via-admin is still poor hygiene)."""
        cfg = OAuthProviderConfig(
            provider_code="strtest",
            display_name="Str Test",
            provider_type=ProviderType.OIDC,
            issuer_url="https://issuer.example.test",
            client_id_env_key="OAUTH_STRTEST_CLIENT_ID",
            client_secret_env_key="OAUTH_STRTEST_CLIENT_SECRET",
        )
        rendered = str(cfg)
        assert "OAUTH_STRTEST_CLIENT_SECRET" not in rendered
        assert "Str Test" in rendered
        assert "strtest" in rendered
