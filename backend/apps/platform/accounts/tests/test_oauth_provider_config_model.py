"""Tests for the OAuthProviderConfig model (M1 D5 Phase 1).

Covers:
- field shape per B.3.7
- provider_code validator (DNS-safe)
- env-key validators (POSIX shape)
- OIDC-requires-issuer-url validation
- OAUTH2-requires-auth-and-token-url validation
- trust_external_mfa + require_verified_email=False is rejected
- secrets are NOT stored in the model (only env-var key names)
"""

from __future__ import annotations

from typing import Any

import pytest
from django.core.exceptions import ValidationError

from apps.platform.accounts.oauth import OAuthProviderConfig, ProviderType


@pytest.mark.django_db
class TestOAuthProviderConfigShape:
    def test_secret_never_stored_in_model_fields(self) -> None:
        """The model has no `client_secret` field — only the key NAME."""
        field_names = {f.name for f in OAuthProviderConfig._meta.get_fields()}
        assert "client_secret" not in field_names
        assert "client_id" not in field_names
        assert "client_secret_env_key" in field_names
        assert "client_id_env_key" in field_names

    def test_default_factory_values(self) -> None:
        cfg = OAuthProviderConfig(
            provider_code="test",
            display_name="Test",
            client_id_env_key="OAUTH_TEST_CLIENT_ID",
            client_secret_env_key="OAUTH_TEST_CLIENT_SECRET",
            issuer_url="https://issuer.example.test",
        )
        assert cfg.is_active is False
        assert cfg.require_verified_email is True
        assert cfg.trust_external_mfa is False
        assert cfg.allow_self_registration is False
        assert cfg.provider_type == ProviderType.OIDC


@pytest.mark.django_db
class TestOAuthProviderConfigValidators:
    def _base_kwargs(self) -> dict[str, Any]:
        return {
            "provider_code": "test-provider",
            "display_name": "Test",
            "client_id_env_key": "OAUTH_TEST_CLIENT_ID",
            "client_secret_env_key": "OAUTH_TEST_CLIENT_SECRET",
            "issuer_url": "https://issuer.example.test",
        }

    def test_valid_provider_code_passes(self) -> None:
        cfg = OAuthProviderConfig(**self._base_kwargs())
        cfg.full_clean()  # must not raise

    def test_provider_code_rejects_uppercase(self) -> None:
        cfg = OAuthProviderConfig(**{**self._base_kwargs(), "provider_code": "BadCode"})
        with pytest.raises(ValidationError) as exc:
            cfg.full_clean()
        assert "provider_code" in exc.value.message_dict

    def test_provider_code_rejects_leading_digit(self) -> None:
        cfg = OAuthProviderConfig(**{**self._base_kwargs(), "provider_code": "1bad"})
        with pytest.raises(ValidationError) as exc:
            cfg.full_clean()
        assert "provider_code" in exc.value.message_dict

    def test_provider_code_rejects_underscore(self) -> None:
        cfg = OAuthProviderConfig(
            **{**self._base_kwargs(), "provider_code": "bad_code"}
        )
        with pytest.raises(ValidationError) as exc:
            cfg.full_clean()
        assert "provider_code" in exc.value.message_dict

    def test_env_key_rejects_lowercase(self) -> None:
        cfg = OAuthProviderConfig(
            **{**self._base_kwargs(), "client_id_env_key": "bad_lowercase"}
        )
        with pytest.raises(ValidationError) as exc:
            cfg.full_clean()
        assert "client_id_env_key" in exc.value.message_dict

    def test_env_key_accepts_uppercase_with_underscores(self) -> None:
        cfg = OAuthProviderConfig(
            **{
                **self._base_kwargs(),
                "client_id_env_key": "OAUTH_PROVIDER_CLIENT_ID_42",
                "client_secret_env_key": "OAUTH_PROVIDER_CLIENT_SECRET_42",
            }
        )
        cfg.full_clean()  # must not raise

    def test_oidc_without_issuer_url_rejected(self) -> None:
        kwargs = self._base_kwargs()
        kwargs["issuer_url"] = None
        cfg = OAuthProviderConfig(**kwargs)
        with pytest.raises(ValidationError) as exc:
            cfg.full_clean()
        assert "issuer_url" in exc.value.message_dict

    def test_oauth2_requires_auth_and_token_urls(self) -> None:
        kwargs = self._base_kwargs()
        kwargs["provider_type"] = ProviderType.OAUTH2
        kwargs["issuer_url"] = None  # not needed for OAUTH2
        cfg = OAuthProviderConfig(**kwargs)
        with pytest.raises(ValidationError) as exc:
            cfg.full_clean()
        assert "authorization_url" in exc.value.message_dict
        assert "token_url" in exc.value.message_dict

    def test_oauth2_with_required_urls_passes(self) -> None:
        kwargs = self._base_kwargs()
        kwargs["provider_type"] = ProviderType.OAUTH2
        kwargs["issuer_url"] = None
        kwargs["authorization_url"] = "https://auth.example.test/authorize"
        kwargs["token_url"] = "https://auth.example.test/token"
        cfg = OAuthProviderConfig(**kwargs)
        cfg.full_clean()  # must not raise

    def test_trust_external_mfa_without_verified_email_rejected(self) -> None:
        kwargs = self._base_kwargs()
        kwargs["trust_external_mfa"] = True
        kwargs["require_verified_email"] = False
        cfg = OAuthProviderConfig(**kwargs)
        with pytest.raises(ValidationError) as exc:
            cfg.full_clean()
        assert "trust_external_mfa" in exc.value.message_dict

    def test_provider_code_unique(self) -> None:
        OAuthProviderConfig.objects.create(**self._base_kwargs())
        with pytest.raises(Exception):  # IntegrityError
            OAuthProviderConfig.objects.create(**self._base_kwargs())
