"""Tests for ExternalIdentityClaims and normalize_socialaccount_claims (B.3.8)."""

from __future__ import annotations

from typing import Any

import pytest

from apps.platform.accounts.oauth import (
    ExternalIdentityClaims,
    normalize_socialaccount_claims,
)


class _FakeSocialAccount:
    """Stub mimicking allauth.socialaccount.models.SocialAccount."""

    def __init__(
        self,
        *,
        provider: str,
        uid: str,
        extra_data: dict[str, Any] | None = None,
    ) -> None:
        self.provider = provider
        self.uid = uid
        self.extra_data = extra_data or {}


class _FakeSocialLogin:
    """Stub mimicking allauth.socialaccount.models.SocialLogin."""

    def __init__(self, account: _FakeSocialAccount) -> None:
        self.account = account


class TestExternalIdentityClaims:
    def test_email_normalized_to_lowercase(self) -> None:
        c = ExternalIdentityClaims(
            provider_code="p",
            provider_uid="u",
            email="Mixed.Case@Example.TEST",
            email_verified=True,
            display_name=None,
        )
        assert c.email == "mixed.case@example.test"

    def test_email_none_is_preserved(self) -> None:
        c = ExternalIdentityClaims(
            provider_code="p",
            provider_uid="u",
            email=None,
            email_verified=False,
            display_name=None,
        )
        assert c.email is None

    def test_raw_claims_copy_isolates_caller_mutation(self) -> None:
        original = {"email": "x@y.test", "custom_claim": "value"}
        c = ExternalIdentityClaims(
            provider_code="p",
            provider_uid="u",
            email="x@y.test",
            email_verified=True,
            display_name=None,
            raw_claims=original,
        )
        original["custom_claim"] = "changed"
        # The frozen claims object should retain the original value.
        assert c.raw_claims["custom_claim"] == "value"

    def test_dataclass_is_frozen(self) -> None:
        c = ExternalIdentityClaims(
            provider_code="p",
            provider_uid="u",
            email=None,
            email_verified=False,
            display_name=None,
        )
        with pytest.raises(Exception):  # dataclasses.FrozenInstanceError
            c.email = "new@example.test"  # type: ignore[misc]


class TestNormalizeSocialaccountClaims:
    def test_oidc_claims_round_trip(self) -> None:
        account = _FakeSocialAccount(
            provider="google-workspace",
            uid="118123456789012345678",
            extra_data={
                "email": "alice@example.test",
                "email_verified": True,
                "name": "Alice Example",
                "acr": "urn:mace:incommon:iap:silver",
                "amr": ["pwd", "mfa"],
                "iss": "https://accounts.google.com",
                "aud": "client-id-here",
                "sub": "118123456789012345678",
            },
        )
        login = _FakeSocialLogin(account)

        claims = normalize_socialaccount_claims(login)

        assert claims.provider_code == "google-workspace"
        assert claims.provider_uid == "118123456789012345678"
        assert claims.email == "alice@example.test"
        assert claims.email_verified is True
        assert claims.display_name == "Alice Example"
        assert claims.acr == "urn:mace:incommon:iap:silver"
        assert claims.amr == ("pwd", "mfa")

    def test_unverified_email_default(self) -> None:
        account = _FakeSocialAccount(
            provider="some-provider",
            uid="u-1",
            extra_data={"email": "bob@example.test"},  # no email_verified
        )
        claims = normalize_socialaccount_claims(_FakeSocialLogin(account))
        assert claims.email_verified is False

    def test_token_fields_stripped_from_raw_claims(self) -> None:
        """Defense in depth: token-like keys never enter the claims object."""
        account = _FakeSocialAccount(
            provider="p",
            uid="u",
            extra_data={
                "email": "alice@example.test",
                "email_verified": True,
                "access_token": "secret-access-token-must-not-leak",
                "refresh_token": "secret-refresh-token-must-not-leak",
                "id_token": "ey.secret.idtoken",
                "code": "auth-code-must-not-leak",
                "client_secret": "client-secret-must-not-leak",
            },
        )
        claims = normalize_socialaccount_claims(_FakeSocialLogin(account))
        assert "access_token" not in claims.raw_claims
        assert "refresh_token" not in claims.raw_claims
        assert "id_token" not in claims.raw_claims
        assert "code" not in claims.raw_claims
        assert "client_secret" not in claims.raw_claims
        # Non-sensitive claims remain.
        assert claims.raw_claims["email"] == "alice@example.test"

    def test_amr_string_coerced_to_tuple(self) -> None:
        account = _FakeSocialAccount(
            provider="p",
            uid="u",
            extra_data={"amr": "pwd"},  # string, not list
        )
        claims = normalize_socialaccount_claims(_FakeSocialLogin(account))
        assert claims.amr == ("pwd",)

    def test_amr_missing_is_empty_tuple(self) -> None:
        account = _FakeSocialAccount(provider="p", uid="u", extra_data={})
        claims = normalize_socialaccount_claims(_FakeSocialLogin(account))
        assert claims.amr == ()

    def test_display_name_falls_back_to_display_name_claim(self) -> None:
        """Some providers use `display_name` instead of `name`."""
        account = _FakeSocialAccount(
            provider="p",
            uid="u",
            extra_data={"display_name": "Carol"},
        )
        claims = normalize_socialaccount_claims(_FakeSocialLogin(account))
        assert claims.display_name == "Carol"

    def test_missing_email_returns_none(self) -> None:
        account = _FakeSocialAccount(provider="p", uid="u", extra_data={})
        claims = normalize_socialaccount_claims(_FakeSocialLogin(account))
        assert claims.email is None
        assert claims.email_verified is False
