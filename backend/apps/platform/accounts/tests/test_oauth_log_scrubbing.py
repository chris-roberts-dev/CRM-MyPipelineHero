"""J.3.9 #20 — OAuth-specific log scrubbing (M1 D5 Phase 6).

Verifies that the OAuth flow does not write tokens, authorization
codes, client secrets, ID tokens, or TOTP secrets into log records.

M1 D4 already covered the local-auth flow (test_log_scrubbing.py).
This file covers the OAuth-specific paths: claims normalization,
adapter resolution, signal-driven audit emission.

Probe-not-proof: G.5.5 masking lives in M2's audit storage. Until
then, this test confirms the M1 D5 code paths don't leak.
"""

from __future__ import annotations

import logging
from typing import Any
from unittest import mock

import pytest
from allauth.core.exceptions import ImmediateHttpResponse
from django.http import HttpRequest

from apps.platform.accounts.oauth import (
    OAuthProviderConfig,
    ProviderType,
    normalize_socialaccount_claims,
)
from apps.platform.accounts.oauth.adapter import MphSocialAccountAdapter

# Sentinel tokens used across tests. If any of these strings appear in
# a log record at any level, the test fails. Pinned uppercase to
# avoid false matches against ordinary words.
_LEAK_VALUE_ACCESS = "ACCESSTOKEN-LEAK-CANARY-001"
_LEAK_VALUE_REFRESH = "REFRESHTOKEN-LEAK-CANARY-002"
_LEAK_VALUE_ID_TOKEN = "IDTOKEN.HEADER.PAYLOAD-LEAK-CANARY-003"
_LEAK_VALUE_CODE = "AUTHCODE-LEAK-CANARY-004"
_LEAK_VALUE_SECRET = "CLIENTSECRET-LEAK-CANARY-005"
_LEAK_VALUE_PRIVATE_KEY = "-----BEGIN-PRIVATE-KEY-CANARY-006-----"


_ALL_LEAKS = [
    _LEAK_VALUE_ACCESS,
    _LEAK_VALUE_REFRESH,
    _LEAK_VALUE_ID_TOKEN,
    _LEAK_VALUE_CODE,
    _LEAK_VALUE_SECRET,
    _LEAK_VALUE_PRIVATE_KEY,
]


def _assert_no_leaks(records: list[logging.LogRecord]) -> None:
    """Walk all records, fail if any leak string appears anywhere."""
    for record in records:
        msg = record.getMessage()
        for leak in _ALL_LEAKS:
            assert (
                leak not in msg
            ), f"Leak value {leak!r} appeared in a log record: {msg!r}"


class _FakeSocialAccount:
    def __init__(self, provider: str, uid: str, extra_data: dict[str, Any]) -> None:
        self.provider = provider
        self.uid = uid
        self.extra_data = extra_data


class _FakeSocialLogin:
    def __init__(self, account: _FakeSocialAccount) -> None:
        self.account = account
        self.user: Any = None


@pytest.fixture
def provider_log_test(db: Any) -> OAuthProviderConfig:
    return OAuthProviderConfig.objects.create(
        provider_code="log-scrub-test",
        display_name="Log Scrub Test",
        provider_type=ProviderType.OIDC,
        issuer_url="https://issuer.example.test",
        client_id_env_key="OAUTH_LOG_SCRUB_TEST_CLIENT_ID",
        client_secret_env_key="OAUTH_LOG_SCRUB_TEST_CLIENT_SECRET",
        is_active=True,
        require_verified_email=True,
        allow_self_registration=True,
    )


@pytest.fixture
def fake_request() -> HttpRequest:
    return mock.MagicMock(spec=HttpRequest)


@pytest.fixture
def adapter() -> MphSocialAccountAdapter:
    MphSocialAccountAdapter._reset_system_actor_id_cache()
    return MphSocialAccountAdapter()


@pytest.mark.django_db
class TestNormalizationDoesNotLogTokens:
    """normalize_socialaccount_claims strips tokens (Phase 1). Verify
    the stripping path itself doesn't log the values it's stripping."""

    def test_normalize_with_full_token_payload_no_leak(self, caplog: Any) -> None:
        sociallogin = _FakeSocialLogin(
            _FakeSocialAccount(
                provider="log-scrub-test",
                uid="leak-canary",
                extra_data={
                    "email": "leakcheck@example.test",
                    "email_verified": True,
                    "access_token": _LEAK_VALUE_ACCESS,
                    "refresh_token": _LEAK_VALUE_REFRESH,
                    "id_token": _LEAK_VALUE_ID_TOKEN,
                    "code": _LEAK_VALUE_CODE,
                    "client_secret": _LEAK_VALUE_SECRET,
                    "private_key": _LEAK_VALUE_PRIVATE_KEY,
                },
            )
        )
        with caplog.at_level(logging.DEBUG):
            claims = normalize_socialaccount_claims(sociallogin)

        # Claims object doesn't carry the leaks.
        for leak in _ALL_LEAKS:
            assert leak not in str(claims.raw_claims)

        # And nothing was logged that contains them.
        _assert_no_leaks(caplog.records)


@pytest.mark.django_db
class TestAdapterDoesNotLogTokens:
    """Adapter's success and failure paths both must scrub."""

    def test_adapter_success_path_no_token_in_log(
        self,
        adapter: MphSocialAccountAdapter,
        provider_log_test: OAuthProviderConfig,
        fake_request: HttpRequest,
        caplog: Any,
    ) -> None:
        sociallogin = _FakeSocialLogin(
            _FakeSocialAccount(
                provider="log-scrub-test",
                uid="success-canary",
                extra_data={
                    "email": "success@example.test",
                    "email_verified": True,
                    "access_token": _LEAK_VALUE_ACCESS,
                    "refresh_token": _LEAK_VALUE_REFRESH,
                    "id_token": _LEAK_VALUE_ID_TOKEN,
                    "code": _LEAK_VALUE_CODE,
                    "client_secret": _LEAK_VALUE_SECRET,
                },
            )
        )
        with caplog.at_level(logging.DEBUG):
            adapter.pre_social_login(fake_request, sociallogin)
        _assert_no_leaks(caplog.records)

    def test_adapter_failure_path_no_token_in_log(
        self,
        adapter: MphSocialAccountAdapter,
        provider_log_test: OAuthProviderConfig,
        fake_request: HttpRequest,
        caplog: Any,
    ) -> None:
        """Failure path emits OAUTH_LOGIN_FAILED + logs an info line.
        Neither emission carries the tokens."""
        provider_log_test.is_active = False
        provider_log_test.save()

        sociallogin = _FakeSocialLogin(
            _FakeSocialAccount(
                provider="log-scrub-test",
                uid="failure-canary",
                extra_data={
                    "email": "fail@example.test",
                    "email_verified": True,
                    "access_token": _LEAK_VALUE_ACCESS,
                    "refresh_token": _LEAK_VALUE_REFRESH,
                    "id_token": _LEAK_VALUE_ID_TOKEN,
                },
            )
        )
        with caplog.at_level(logging.DEBUG):
            with pytest.raises(ImmediateHttpResponse):
                adapter.pre_social_login(fake_request, sociallogin)
        _assert_no_leaks(caplog.records)
