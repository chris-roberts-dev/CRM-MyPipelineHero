"""Tests for the MphSocialAccountAdapter (M1 D5 Phase 3).

Covers:
- pre_social_login dispatches to resolve_external_user
- success path: sociallogin.user is set to the resolved user
- each typed exception maps to the right failure_reason audit
- each typed exception maps to the right help-page redirect
- OAUTH_LOGIN_STARTED is emitted on every call
- OAUTH_LOGIN_FAILED is emitted with structured failure_reason
- unknown provider_code is handled as provider_not_active
- the System User id is cached after first lookup

The adapter is tested with stub SocialLogin instances rather than
running allauth's full flow. The full-flow tests live in Phase 6
with the mock OIDC issuer.
"""

from __future__ import annotations

from typing import Any
from unittest import mock
from uuid import UUID

import pytest
from allauth.exceptions import ImmediateHttpResponse
from django.contrib.auth import get_user_model
from django.http import HttpRequest

from apps.platform.accounts.oauth import (
    OAuthProviderConfig,
    ProviderType,
)
from apps.platform.accounts.oauth.adapter import MphSocialAccountAdapter
from apps.platform.audit.services import captured_audit_events


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
def fake_request() -> HttpRequest:
    return mock.MagicMock(spec=HttpRequest)


@pytest.fixture
def active_provider(db: Any) -> OAuthProviderConfig:
    return OAuthProviderConfig.objects.create(
        provider_code="test-adapter-oidc",
        display_name="Test Adapter OIDC",
        provider_type=ProviderType.OIDC,
        issuer_url="https://issuer.example.test",
        client_id_env_key="OAUTH_TEST_ADAPTER_OIDC_CLIENT_ID",
        client_secret_env_key="OAUTH_TEST_ADAPTER_OIDC_CLIENT_SECRET",
        is_active=True,
        require_verified_email=True,
        allow_self_registration=False,
    )


@pytest.fixture
def adapter() -> MphSocialAccountAdapter:
    # Reset the class-level System User cache so each test starts
    # clean. The adapter is normally singleton-ish (allauth instantiates
    # one per request), so the cache reset is just a hygiene measure.
    MphSocialAccountAdapter._reset_system_actor_id_cache()
    return MphSocialAccountAdapter()


def _build_sociallogin(
    *,
    provider_code: str = "test-adapter-oidc",
    provider_uid: str = "subject-adapter-1",
    email: str | None = "alice@example.test",
    email_verified: bool = True,
) -> _FakeSocialLogin:
    extra_data: dict[str, Any] = {}
    if email is not None:
        extra_data["email"] = email
    extra_data["email_verified"] = email_verified
    extra_data["name"] = "Alice Adapter"
    return _FakeSocialLogin(
        _FakeSocialAccount(
            provider=provider_code,
            uid=provider_uid,
            extra_data=extra_data,
        )
    )


@pytest.mark.django_db
class TestSystemActorIdCache:
    def test_caches_after_first_call(self, adapter: MphSocialAccountAdapter) -> None:
        first = MphSocialAccountAdapter._get_system_actor_id()
        second = MphSocialAccountAdapter._get_system_actor_id()
        assert first == second
        assert isinstance(first, UUID)

    def test_lookup_returns_system_user_id(
        self, adapter: MphSocialAccountAdapter
    ) -> None:
        UserModel = get_user_model()
        expected = UserModel.objects.get(is_system=True).id
        assert MphSocialAccountAdapter._get_system_actor_id() == expected


@pytest.mark.django_db
class TestPreSocialLoginSuccess:
    def test_success_swaps_in_resolved_user(
        self,
        adapter: MphSocialAccountAdapter,
        active_provider: OAuthProviderConfig,
        fake_request: HttpRequest,
        user_factory: Any,
    ) -> None:
        existing_user = user_factory(email="alice@example.test")
        sociallogin = _build_sociallogin()

        adapter.pre_social_login(fake_request, sociallogin)

        assert sociallogin.user.id == existing_user.id

    def test_success_emits_oauth_login_started(
        self,
        adapter: MphSocialAccountAdapter,
        active_provider: OAuthProviderConfig,
        fake_request: HttpRequest,
        user_factory: Any,
    ) -> None:
        user_factory(email="alice@example.test")
        sociallogin = _build_sociallogin()

        adapter.pre_social_login(fake_request, sociallogin)

        started = captured_audit_events(event_type="OAUTH_LOGIN_STARTED")
        assert len(started) == 1
        assert started[0].metadata is not None
        assert started[0].metadata["provider_code"] == "test-adapter-oidc"
        assert started[0].metadata["email_present"] is True
        assert started[0].metadata["email_verified"] is True

    def test_success_does_not_emit_login_failed(
        self,
        adapter: MphSocialAccountAdapter,
        active_provider: OAuthProviderConfig,
        fake_request: HttpRequest,
        user_factory: Any,
    ) -> None:
        user_factory(email="alice@example.test")
        sociallogin = _build_sociallogin()

        adapter.pre_social_login(fake_request, sociallogin)

        failed = captured_audit_events(event_type="OAUTH_LOGIN_FAILED")
        assert failed == []


@pytest.mark.django_db
class TestPreSocialLoginFailures:
    """Each typed exception maps to a redirect + structured audit event."""

    def test_provider_not_active_redirects_and_audits(
        self,
        adapter: MphSocialAccountAdapter,
        active_provider: OAuthProviderConfig,
        fake_request: HttpRequest,
    ) -> None:
        active_provider.is_active = False
        active_provider.save()

        sociallogin = _build_sociallogin()
        with pytest.raises(ImmediateHttpResponse) as exc:
            adapter.pre_social_login(fake_request, sociallogin)

        # Redirect target.
        assert "/oauth-help/provider_not_active/" in exc.value.response["Location"]
        # Audit.
        failed = captured_audit_events(event_type="OAUTH_LOGIN_FAILED")
        assert len(failed) == 1
        assert failed[0].metadata is not None
        assert failed[0].metadata["failure_reason"] == "provider_not_active"

    def test_email_not_verified_redirects_and_audits(
        self,
        adapter: MphSocialAccountAdapter,
        active_provider: OAuthProviderConfig,
        fake_request: HttpRequest,
    ) -> None:
        sociallogin = _build_sociallogin(email_verified=False)
        with pytest.raises(ImmediateHttpResponse) as exc:
            adapter.pre_social_login(fake_request, sociallogin)
        assert "/oauth-help/email_not_verified/" in exc.value.response["Location"]
        failed = captured_audit_events(event_type="OAUTH_LOGIN_FAILED")
        assert failed[0].metadata["failure_reason"] == "email_not_verified"

    def test_domain_not_allowed_redirects_and_audits(
        self,
        adapter: MphSocialAccountAdapter,
        active_provider: OAuthProviderConfig,
        fake_request: HttpRequest,
    ) -> None:
        active_provider.allowed_email_domains = ["only-allowed.test"]
        active_provider.save()

        sociallogin = _build_sociallogin(email="alice@blocked.test")
        with pytest.raises(ImmediateHttpResponse) as exc:
            adapter.pre_social_login(fake_request, sociallogin)
        assert "/oauth-help/domain_not_allowed/" in exc.value.response["Location"]
        failed = captured_audit_events(event_type="OAUTH_LOGIN_FAILED")
        assert failed[0].metadata["failure_reason"] == "domain_not_allowed"

    def test_conflicting_identity_redirects_and_audits(
        self,
        adapter: MphSocialAccountAdapter,
        active_provider: OAuthProviderConfig,
        fake_request: HttpRequest,
        user_factory: Any,
    ) -> None:
        from allauth.socialaccount.models import SocialAccount

        existing_user = user_factory(email="alice@example.test")
        SocialAccount.objects.create(
            user=existing_user,
            provider="test-adapter-oidc",
            uid="OLD-SUBJECT",
            extra_data={},
        )

        sociallogin = _build_sociallogin(provider_uid="NEW-SUBJECT")
        with pytest.raises(ImmediateHttpResponse) as exc:
            adapter.pre_social_login(fake_request, sociallogin)
        assert "/oauth-help/conflicting_identity/" in exc.value.response["Location"]
        failed = captured_audit_events(event_type="OAUTH_LOGIN_FAILED")
        assert failed[0].metadata["failure_reason"] == "conflicting_identity"

    def test_user_inactive_redirects_and_audits(
        self,
        adapter: MphSocialAccountAdapter,
        active_provider: OAuthProviderConfig,
        fake_request: HttpRequest,
        user_factory: Any,
    ) -> None:
        user = user_factory(email="alice@example.test")
        user.is_active = False
        user.save()

        sociallogin = _build_sociallogin()
        with pytest.raises(ImmediateHttpResponse) as exc:
            adapter.pre_social_login(fake_request, sociallogin)
        assert "/oauth-help/user_inactive/" in exc.value.response["Location"]
        failed = captured_audit_events(event_type="OAUTH_LOGIN_FAILED")
        assert failed[0].metadata["failure_reason"] == "user_inactive"

    def test_no_existing_user_redirects_and_audits(
        self,
        adapter: MphSocialAccountAdapter,
        active_provider: OAuthProviderConfig,
        fake_request: HttpRequest,
    ) -> None:
        # No existing user, self-registration disabled (the default).
        sociallogin = _build_sociallogin(email="newuser@example.test")
        with pytest.raises(ImmediateHttpResponse) as exc:
            adapter.pre_social_login(fake_request, sociallogin)
        assert "/oauth-help/no_existing_user/" in exc.value.response["Location"]
        failed = captured_audit_events(event_type="OAUTH_LOGIN_FAILED")
        assert failed[0].metadata["failure_reason"] == "no_existing_user"


@pytest.mark.django_db
class TestUnknownProvider:
    def test_unknown_provider_code_treated_as_provider_not_active(
        self,
        adapter: MphSocialAccountAdapter,
        fake_request: HttpRequest,
    ) -> None:
        # No OAuthProviderConfig with code "unknown-provider" exists.
        sociallogin = _build_sociallogin(provider_code="unknown-provider")
        with pytest.raises(ImmediateHttpResponse) as exc:
            adapter.pre_social_login(fake_request, sociallogin)
        assert "/oauth-help/provider_not_active/" in exc.value.response["Location"]
        failed = captured_audit_events(event_type="OAUTH_LOGIN_FAILED")
        assert failed[0].metadata["failure_reason"] == "provider_not_active"


@pytest.mark.django_db
class TestOAuthHelpView:
    """Sanity tests on the help-page view itself."""

    def test_known_reason_renders_specific_copy(self, client: Any) -> None:
        response = client.get("/oauth-help/email_not_verified/")
        assert response.status_code == 200
        assert "Verify your email at the provider" in response.content.decode()

    def test_unknown_reason_renders_generic_copy(self, client: Any) -> None:
        response = client.get("/oauth-help/some-unknown-reason/")
        assert response.status_code == 200
        # Falls back to provider_not_active copy.
        assert "Sign-in unavailable" in response.content.decode()

    def test_help_page_renders_with_mph_chrome(self, client: Any) -> None:
        response = client.get("/oauth-help/email_not_verified/")
        assert "mph-auth-card" in response.content.decode()
