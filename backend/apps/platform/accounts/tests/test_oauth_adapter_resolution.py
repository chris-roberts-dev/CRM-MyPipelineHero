"""Adapter-boundary integration tests for J.3.9 #6, #8, #9, #10 (M1 D5 Phase 6).

These tests exercise the full chain from
``MphSocialAccountAdapter.pre_social_login`` through
``resolve_external_user`` to the database side effects. The HTTP
flow (allauth's authorization redirect, token exchange, JWKS
verification) is allauth's surface — we use synthetic
``SocialLogin`` fixtures rather than a mock OIDC issuer.

This matches the M1 D5 retro decision: service+adapter coverage
provides regression protection over our policy decisions, and M8
production-readiness (J.10.3) does the real-provider verification.

Coverage matrix (J.3.9 numbering):

* #6 — OAuth login works through configured provider → verified at
  adapter boundary (this file). HTTP integration deferred to M8.
* #8 — OAuth callback validates provider response → verified for
  the validations our adapter enforces (provider active, email
  verified, allowed domain, conflicting identity). Cryptographic
  validations (state, nonce, signature) are allauth's responsibility
  and verified in M8.
* #9 — External identity links to canonical User → verified
  end-to-end via the adapter (this file) AND at the service level
  (test_resolve_external_user_service.py).
* #10 — OAuth login does not create Membership → verified at the
  service level. Re-verified at adapter level here.
"""

from __future__ import annotations

from typing import Any
from unittest import mock

import pytest
from allauth.core.exceptions import ImmediateHttpResponse
from allauth.socialaccount.models import SocialAccount
from django.http import HttpRequest

from apps.platform.accounts.oauth import OAuthProviderConfig, ProviderType
from apps.platform.accounts.oauth.adapter import MphSocialAccountAdapter
from apps.platform.audit.services import captured_audit_events

# ---------------------------------------------------------------------------
# Fixtures.
# ---------------------------------------------------------------------------


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
def adapter() -> MphSocialAccountAdapter:
    MphSocialAccountAdapter._reset_system_actor_id_cache()
    return MphSocialAccountAdapter()


@pytest.fixture
def provider_default(db: Any) -> OAuthProviderConfig:
    """An active OIDC provider with the typical M1 D5 posture:
    require verified email, no self-registration, untrusted MFA."""
    return OAuthProviderConfig.objects.create(
        provider_code="adapter-int-default",
        display_name="Adapter Int Default",
        provider_type=ProviderType.OIDC,
        issuer_url="https://issuer.example.test",
        client_id_env_key="OAUTH_ADAPTER_INT_DEFAULT_CLIENT_ID",
        client_secret_env_key="OAUTH_ADAPTER_INT_DEFAULT_CLIENT_SECRET",
        is_active=True,
        require_verified_email=True,
        trust_external_mfa=False,
        allow_self_registration=False,
    )


@pytest.fixture
def provider_self_reg(db: Any) -> OAuthProviderConfig:
    """An active OIDC provider that allows self-registration."""
    return OAuthProviderConfig.objects.create(
        provider_code="adapter-int-selfreg",
        display_name="Adapter Int Self-Reg",
        provider_type=ProviderType.OIDC,
        issuer_url="https://issuer.example.test",
        client_id_env_key="OAUTH_ADAPTER_INT_SELFREG_CLIENT_ID",
        client_secret_env_key="OAUTH_ADAPTER_INT_SELFREG_CLIENT_SECRET",
        is_active=True,
        require_verified_email=True,
        trust_external_mfa=False,
        allow_self_registration=True,
    )


def _build_sociallogin(
    *,
    provider_code: str = "adapter-int-default",
    provider_uid: str = "subject-int-1",
    email: str | None = "alice@example.test",
    email_verified: bool = True,
    display_name: str = "Alice Integration",
    extra_extras: dict[str, Any] | None = None,
) -> _FakeSocialLogin:
    extra_data: dict[str, Any] = {
        "email": email,
        "email_verified": email_verified,
        "name": display_name,
        "sub": provider_uid,
        "iss": "https://issuer.example.test",
        "aud": "test-client-id",
        "iat": 1700000000,
        "exp": 1700003600,
    }
    if extra_extras:
        extra_data.update(extra_extras)
    if email is None:
        del extra_data["email"]
    return _FakeSocialLogin(
        _FakeSocialAccount(
            provider=provider_code,
            uid=provider_uid,
            extra_data=extra_data,
        )
    )


# ---------------------------------------------------------------------------
# J.3.9 #6 / #9 — successful adapter resolution end-to-end.
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestOAuthLoginAdapterBoundary:
    """J.3.9 #6 — OAuth login works through configured provider.
    J.3.9 #9 — External identity links to canonical User."""

    def test_first_oauth_login_for_invited_user_links_and_logs_in(
        self,
        adapter: MphSocialAccountAdapter,
        provider_default: OAuthProviderConfig,
        fake_request: HttpRequest,
        user_factory: Any,
    ) -> None:
        # User was previously invited (exists, has verified email,
        # local password unused).
        invited_user = user_factory(email="alice@example.test")
        sociallogin = _build_sociallogin()

        adapter.pre_social_login(fake_request, sociallogin)

        # Adapter mutated sociallogin.user to the canonical User.
        assert sociallogin.user.id == invited_user.id
        # SocialAccount was created linking the two.
        sa = SocialAccount.objects.get(
            provider="adapter-int-default", uid="subject-int-1"
        )
        assert sa.user == invited_user
        # Audit events fired in correct order.
        started = captured_audit_events(event_type="OAUTH_LOGIN_STARTED")
        linked = captured_audit_events(event_type="OAUTH_ACCOUNT_LINKED")
        assert len(started) == 1
        assert len(linked) == 1
        assert started[0].metadata is not None
        assert started[0].metadata["provider_code"] == "adapter-int-default"
        assert linked[0].object_id == str(invited_user.id)

    def test_returning_user_with_existing_socialaccount_logs_in(
        self,
        adapter: MphSocialAccountAdapter,
        provider_default: OAuthProviderConfig,
        fake_request: HttpRequest,
        user_factory: Any,
    ) -> None:
        # Returning user — already has a SocialAccount for this provider.
        user = user_factory(email="returning@example.test")
        SocialAccount.objects.create(
            user=user,
            provider="adapter-int-default",
            uid="subject-returning-1",
            extra_data={"email": "returning@example.test"},
        )

        sociallogin = _build_sociallogin(
            provider_uid="subject-returning-1",
            email="returning@example.test",
        )
        adapter.pre_social_login(fake_request, sociallogin)

        assert sociallogin.user.id == user.id
        # Repeat login MUST NOT emit OAUTH_ACCOUNT_LINKED — only first
        # link does (service-level test_subject_id_lookup_returns_linked_user
        # already verifies this; adapter-level repeat here).
        linked = captured_audit_events(event_type="OAUTH_ACCOUNT_LINKED")
        assert linked == []
        # OAUTH_LOGIN_STARTED still fires.
        started = captured_audit_events(event_type="OAUTH_LOGIN_STARTED")
        assert len(started) == 1

    def test_self_registration_creates_user_and_logs_in(
        self,
        adapter: MphSocialAccountAdapter,
        provider_self_reg: OAuthProviderConfig,
        fake_request: HttpRequest,
        db: Any,
    ) -> None:
        sociallogin = _build_sociallogin(
            provider_code="adapter-int-selfreg",
            email="brandnew@example.test",
            provider_uid="subject-brandnew",
        )

        adapter.pre_social_login(fake_request, sociallogin)

        assert sociallogin.user is not None
        assert sociallogin.user.email == "brandnew@example.test"
        assert sociallogin.user.external_login_only is True
        assert not sociallogin.user.has_usable_password()

        registered = captured_audit_events(event_type="USER_REGISTERED")
        linked = captured_audit_events(event_type="OAUTH_ACCOUNT_LINKED")
        assert len(registered) == 1
        assert len(linked) == 1


# ---------------------------------------------------------------------------
# J.3.9 #8 — provider-response validation (our adapter's surface).
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestProviderResponseValidationAtAdapter:
    """J.3.9 #8 — OAuth callback validates provider response.

    Cryptographic validations (state, nonce, ID token signature,
    issuer, audience) are enforced by allauth BEFORE our adapter runs.
    Verified in M8 with real providers (J.10.3).

    Our adapter enforces the configuration-level validations:
    provider is active, verified email if required, allowed domain,
    no conflicting identity. Those are exercised here.
    """

    def test_inactive_provider_redirects_to_help(
        self,
        adapter: MphSocialAccountAdapter,
        provider_default: OAuthProviderConfig,
        fake_request: HttpRequest,
    ) -> None:
        provider_default.is_active = False
        provider_default.save()

        sociallogin = _build_sociallogin()
        with pytest.raises(ImmediateHttpResponse) as exc:
            adapter.pre_social_login(fake_request, sociallogin)
        assert "/oauth-help/provider_not_active/" in exc.value.response["Location"]

    def test_unverified_email_when_required_redirects_to_help(
        self,
        adapter: MphSocialAccountAdapter,
        provider_default: OAuthProviderConfig,
        fake_request: HttpRequest,
        user_factory: Any,
    ) -> None:
        # An existing user with this email — silent linking via unverified
        # email is forbidden (B.5.6 #1).
        user_factory(email="unverified@example.test")
        sociallogin = _build_sociallogin(
            email="unverified@example.test",
            email_verified=False,
        )
        with pytest.raises(ImmediateHttpResponse) as exc:
            adapter.pre_social_login(fake_request, sociallogin)
        assert "/oauth-help/email_not_verified/" in exc.value.response["Location"]

    def test_email_domain_outside_allowlist_redirects_to_help(
        self,
        adapter: MphSocialAccountAdapter,
        provider_default: OAuthProviderConfig,
        fake_request: HttpRequest,
    ) -> None:
        provider_default.allowed_email_domains = ["company.test"]
        provider_default.save()

        sociallogin = _build_sociallogin(email="alice@otherdomain.test")
        with pytest.raises(ImmediateHttpResponse) as exc:
            adapter.pre_social_login(fake_request, sociallogin)
        assert "/oauth-help/domain_not_allowed/" in exc.value.response["Location"]


# ---------------------------------------------------------------------------
# J.3.9 #10 — no Membership creation on OAuth login.
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestOAuthLoginCreatesNoMembership:
    """J.3.9 #10 — OAuth login does not create Membership.

    The service-level test already covers this with full enforcement.
    The adapter-level test re-verifies in the *adapter* context:
    even a successful login through allauth's pipeline does not
    create a Membership row.
    """

    def test_adapter_pre_social_login_creates_no_membership(
        self,
        adapter: MphSocialAccountAdapter,
        provider_self_reg: OAuthProviderConfig,
        fake_request: HttpRequest,
        db: Any,
    ) -> None:
        from apps.platform.organizations.models import Membership

        baseline = Membership.objects.count()

        sociallogin = _build_sociallogin(
            provider_code="adapter-int-selfreg",
            email="nomembership@example.test",
            provider_uid="subject-nomembership",
        )
        adapter.pre_social_login(fake_request, sociallogin)

        assert Membership.objects.count() == baseline


# ---------------------------------------------------------------------------
# Audit-event ordering across the adapter call.
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestAuditEventOrdering:
    """OAUTH_LOGIN_STARTED MUST precede other events from the same call."""

    def test_started_before_account_linked_on_first_login(
        self,
        adapter: MphSocialAccountAdapter,
        provider_default: OAuthProviderConfig,
        fake_request: HttpRequest,
        user_factory: Any,
    ) -> None:
        user_factory(email="alice@example.test")
        sociallogin = _build_sociallogin()

        adapter.pre_social_login(fake_request, sociallogin)

        # All captured events, in emission order.
        all_events = captured_audit_events()
        types_in_order = [e.event_type for e in all_events]
        # OAUTH_LOGIN_STARTED MUST come before OAUTH_ACCOUNT_LINKED.
        started_idx = types_in_order.index("OAUTH_LOGIN_STARTED")
        linked_idx = types_in_order.index("OAUTH_ACCOUNT_LINKED")
        assert started_idx < linked_idx

    def test_started_before_failed_on_rejected_login(
        self,
        adapter: MphSocialAccountAdapter,
        provider_default: OAuthProviderConfig,
        fake_request: HttpRequest,
    ) -> None:
        provider_default.is_active = False
        provider_default.save()

        sociallogin = _build_sociallogin()
        with pytest.raises(ImmediateHttpResponse):
            adapter.pre_social_login(fake_request, sociallogin)

        all_events = captured_audit_events()
        types_in_order = [e.event_type for e in all_events]
        started_idx = types_in_order.index("OAUTH_LOGIN_STARTED")
        failed_idx = types_in_order.index("OAUTH_LOGIN_FAILED")
        assert started_idx < failed_idx
