"""Tests for the SOCIALACCOUNT_PROVIDERS loader (M1 D5 Phase 1).

Covers:
- only is_active=True providers are loaded
- inactive providers are invisible to the loader
- missing env vars cause the provider to be skipped (warning logged)
- credentials are read from env vars (not from the model)
- the dict shape matches what allauth expects
- the apply_to_settings hook mutates settings.SOCIALACCOUNT_PROVIDERS
"""

from __future__ import annotations

import logging
from typing import Any

import pytest

from apps.platform.accounts.oauth import OAuthProviderConfig, ProviderType
from apps.platform.accounts.oauth.loader import (
    apply_socialaccount_providers_to_settings,
    load_socialaccount_providers,
)


def _create_provider(
    *,
    provider_code: str,
    is_active: bool = True,
    require_verified_email: bool = True,
    provider_type: str = ProviderType.OIDC,
    issuer_url: str | None = "https://issuer.example.test",
    scopes: list[str] | None = None,
) -> OAuthProviderConfig:
    return OAuthProviderConfig.objects.create(
        provider_code=provider_code,
        display_name=f"Test {provider_code}",
        provider_type=provider_type,
        issuer_url=issuer_url,
        client_id_env_key=f"OAUTH_{provider_code.upper().replace('-', '_')}_CLIENT_ID",
        client_secret_env_key=f"OAUTH_{provider_code.upper().replace('-', '_')}_CLIENT_SECRET",
        scopes=scopes or ["openid", "email", "profile"],
        is_active=is_active,
        require_verified_email=require_verified_email,
    )


@pytest.mark.django_db
class TestLoadSocialaccountProviders:
    def test_empty_when_no_active_providers(self, monkeypatch: Any) -> None:
        result = load_socialaccount_providers()
        assert result == {}

    def test_inactive_provider_excluded(self, monkeypatch: Any) -> None:
        _create_provider(provider_code="inactive", is_active=False)
        monkeypatch.setenv("OAUTH_INACTIVE_CLIENT_ID", "id")
        monkeypatch.setenv("OAUTH_INACTIVE_CLIENT_SECRET", "secret")

        result = load_socialaccount_providers()
        assert result == {}

    def test_active_provider_with_env_credentials_included(
        self, monkeypatch: Any
    ) -> None:
        _create_provider(provider_code="acme")
        monkeypatch.setenv("OAUTH_ACME_CLIENT_ID", "acme-client-id")
        monkeypatch.setenv("OAUTH_ACME_CLIENT_SECRET", "acme-client-secret")

        result = load_socialaccount_providers()

        assert "openid_connect" in result
        apps = result["openid_connect"]["APPS"]
        assert len(apps) == 1
        assert apps[0]["provider_id"] == "acme"
        assert apps[0]["client_id"] == "acme-client-id"
        assert apps[0]["secret"] == "acme-client-secret"
        assert apps[0]["settings"]["server_url"] == "https://issuer.example.test"
        assert apps[0]["settings"]["scope"] == ["openid", "email", "profile"]

    def test_missing_client_id_env_var_skips_provider(
        self, monkeypatch: Any, caplog: Any
    ) -> None:
        _create_provider(provider_code="missing-id")
        monkeypatch.delenv("OAUTH_MISSING_ID_CLIENT_ID", raising=False)
        monkeypatch.setenv("OAUTH_MISSING_ID_CLIENT_SECRET", "secret")

        with caplog.at_level(
            logging.WARNING, logger="apps.platform.accounts.oauth.loader"
        ):
            result = load_socialaccount_providers()

        assert result == {}
        assert any("credentials are missing" in r.message for r in caplog.records)

    def test_missing_client_secret_env_var_skips_provider(
        self, monkeypatch: Any, caplog: Any
    ) -> None:
        _create_provider(provider_code="missing-secret")
        monkeypatch.setenv("OAUTH_MISSING_SECRET_CLIENT_ID", "id")
        monkeypatch.delenv("OAUTH_MISSING_SECRET_CLIENT_SECRET", raising=False)

        with caplog.at_level(
            logging.WARNING, logger="apps.platform.accounts.oauth.loader"
        ):
            result = load_socialaccount_providers()

        assert result == {}

    def test_oauth2_provider_logs_and_skipped(
        self, monkeypatch: Any, caplog: Any
    ) -> None:
        OAuthProviderConfig.objects.create(
            provider_code="oauth2-prov",
            display_name="OAuth2 Provider",
            provider_type=ProviderType.OAUTH2,
            authorization_url="https://auth.example.test/authorize",
            token_url="https://auth.example.test/token",
            client_id_env_key="OAUTH_OAUTH2_PROV_CLIENT_ID",
            client_secret_env_key="OAUTH_OAUTH2_PROV_CLIENT_SECRET",
            is_active=True,
        )
        monkeypatch.setenv("OAUTH_OAUTH2_PROV_CLIENT_ID", "id")
        monkeypatch.setenv("OAUTH_OAUTH2_PROV_CLIENT_SECRET", "secret")

        with caplog.at_level(
            logging.INFO, logger="apps.platform.accounts.oauth.loader"
        ):
            result = load_socialaccount_providers()

        # OAUTH2 providers are not auto-loaded in M1 D5.
        assert result == {}
        assert any(
            "OAUTH2 providers require provider-specific" in r.message
            for r in caplog.records
        )

    def test_multiple_active_providers_all_included(self, monkeypatch: Any) -> None:
        _create_provider(provider_code="prov-a")
        _create_provider(provider_code="prov-b")
        monkeypatch.setenv("OAUTH_PROV_A_CLIENT_ID", "a-id")
        monkeypatch.setenv("OAUTH_PROV_A_CLIENT_SECRET", "a-secret")
        monkeypatch.setenv("OAUTH_PROV_B_CLIENT_ID", "b-id")
        monkeypatch.setenv("OAUTH_PROV_B_CLIENT_SECRET", "b-secret")

        result = load_socialaccount_providers()
        apps = result["openid_connect"]["APPS"]
        assert len(apps) == 2
        provider_ids = {a["provider_id"] for a in apps}
        assert provider_ids == {"prov-a", "prov-b"}


@pytest.mark.django_db
class TestApplySocialaccountProvidersToSettings:
    def test_writes_to_settings(self, monkeypatch: Any) -> None:
        _create_provider(provider_code="apply-test")
        monkeypatch.setenv("OAUTH_APPLY_TEST_CLIENT_ID", "id")
        monkeypatch.setenv("OAUTH_APPLY_TEST_CLIENT_SECRET", "secret")

        apply_socialaccount_providers_to_settings()

        from django.conf import settings as django_settings

        providers = django_settings.SOCIALACCOUNT_PROVIDERS
        assert "openid_connect" in providers
        assert any(
            app["provider_id"] == "apply-test"
            for app in providers["openid_connect"]["APPS"]
        )

    def test_idempotent_on_repeat_call(self, monkeypatch: Any) -> None:
        _create_provider(provider_code="idem-test")
        monkeypatch.setenv("OAUTH_IDEM_TEST_CLIENT_ID", "id")
        monkeypatch.setenv("OAUTH_IDEM_TEST_CLIENT_SECRET", "secret")

        apply_socialaccount_providers_to_settings()
        apply_socialaccount_providers_to_settings()

        from django.conf import settings as django_settings

        providers = django_settings.SOCIALACCOUNT_PROVIDERS
        apps = providers["openid_connect"]["APPS"]
        # No duplicates from the second call.
        assert len([a for a in apps if a["provider_id"] == "idem-test"]) == 1
