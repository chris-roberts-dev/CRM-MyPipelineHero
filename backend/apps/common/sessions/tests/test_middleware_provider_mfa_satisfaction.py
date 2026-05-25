"""Tests for trusted-provider mph_mfa_satisfied_at session write (M1 D6 Phase 4A).

When ``RequireMfaEnrollmentMiddleware`` bypasses enrollment for a
trusted-provider OAuth user, it also writes
``mph_mfa_satisfied_at`` to session. This test guards that.
"""

from __future__ import annotations

from typing import Any

import pytest
from django.test import Client

from apps.platform.accounts.middleware import (
    SESSION_KEY_LOGIN_PROVIDER_CODE,
)
from apps.platform.accounts.oauth.models import OAuthProviderConfig, ProviderType
from apps.platform.accounts.signals_mfa import SESSION_KEY_MFA_SATISFIED_AT


def _login_via_provider(client: Client, user: Any, provider_code: str) -> None:
    client.force_login(user)
    session = client.session
    session[SESSION_KEY_LOGIN_PROVIDER_CODE] = provider_code
    session.save()


@pytest.mark.django_db
class TestTrustedProviderRecordsMfaSatisfaction:
    def test_trusted_provider_writes_mph_mfa_satisfied_at(
        self,
        client: Client,
        user_verified_no_mfa: Any,
        db: Any,
    ) -> None:
        provider = OAuthProviderConfig.objects.create(
            provider_code="phase4a-trusted",
            display_name="Phase 4A Trusted",
            provider_type=ProviderType.OIDC,
            issuer_url="https://issuer.example.test",
            client_id_env_key="OAUTH_PHASE4A_TRUSTED_CLIENT_ID",
            client_secret_env_key="OAUTH_PHASE4A_TRUSTED_CLIENT_SECRET",
            is_active=True,
            trust_external_mfa=True,
        )
        _login_via_provider(client, user_verified_no_mfa, provider.provider_code)
        # Hit any non-allowlisted page — triggers the middleware.
        # /select-org/ is the picker placeholder.
        client.get("/select-org/")

        session = client.session
        assert SESSION_KEY_MFA_SATISFIED_AT in session, (
            f"Expected {SESSION_KEY_MFA_SATISFIED_AT} in session; got keys: "
            f"{list(session.keys())!r}"
        )

    def test_untrusted_provider_does_not_write_mph_mfa_satisfied_at(
        self,
        client: Client,
        user_verified_no_mfa: Any,
        db: Any,
    ) -> None:
        provider = OAuthProviderConfig.objects.create(
            provider_code="phase4a-untrusted",
            display_name="Phase 4A Untrusted",
            provider_type=ProviderType.OIDC,
            issuer_url="https://issuer.example.test",
            client_id_env_key="OAUTH_PHASE4A_UNTRUSTED_CLIENT_ID",
            client_secret_env_key="OAUTH_PHASE4A_UNTRUSTED_CLIENT_SECRET",
            is_active=True,
            trust_external_mfa=False,
        )
        _login_via_provider(client, user_verified_no_mfa, provider.provider_code)
        client.get("/select-org/")
        # Untrusted → redirected to enrollment, MFA satisfaction NOT recorded.
        session = client.session
        assert SESSION_KEY_MFA_SATISFIED_AT not in session
