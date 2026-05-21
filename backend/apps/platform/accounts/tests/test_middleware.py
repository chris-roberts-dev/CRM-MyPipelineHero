"""Tests for RequireMfaEnrollmentMiddleware (M1 D4 + M1 D5 Phase 4).

M1 D4 — B.4.9 local password enforcement:
- authenticated local-password users without TOTP are redirected
  to /accounts/2fa/totp/activate/.
- allowlisted paths pass through regardless of MFA state.
- LOCAL_MFA_CHALLENGE_REQUIRED emitted once per session.
- system user is exempt.

M1 D5 Phase 4 — B.4.8 trusted-provider MFA policy:
- OAuth user via TRUSTED provider with no TOTP bypasses enrollment.
- OAuth user via UNTRUSTED provider with no TOTP is forced to enroll.
- OAUTH_PROVIDER_MFA_TRUSTED / _NOT_TRUSTED emitted once per session.
- missing OAuthProviderConfig falls back to forcing enrollment
  (safe-default failure mode).
- existing TOTP enrollment bypasses the middleware regardless of
  login method.
"""

from __future__ import annotations

from typing import Any

import pytest
from django.test import Client

from apps.platform.accounts.middleware import (
    SESSION_KEY_LOGIN_PROVIDER_CODE,
)
from apps.platform.accounts.oauth.models import OAuthProviderConfig, ProviderType
from apps.platform.audit.services import captured_audit_events

# The allauth-mfa URL the middleware redirects unenrolled users to.
# In allauth 65.x the canonical name `mfa_activate_totp` resolves
# to this path.
MFA_ACTIVATE_PATH = "/accounts/2fa/totp/activate/"


# ---------------------------------------------------------------------------
# M1 D4 — preserved.
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestRequireMfaEnrollmentMiddleware:
    def test_anonymous_user_passes_through(self, client: Client) -> None:
        response = client.get("/")
        if response.status_code == 302:
            assert MFA_ACTIVATE_PATH not in response["Location"]

    def test_authenticated_no_totp_local_login_redirected_to_enrollment(
        self, client: Client, user_verified_no_mfa: Any
    ) -> None:
        # Local-password login — no provider code on session.
        client.force_login(user_verified_no_mfa)
        response = client.get("/select-org/")
        assert response.status_code == 302
        assert response["Location"] == MFA_ACTIVATE_PATH

    def test_authenticated_with_totp_passes_through(
        self, client: Client, user_with_totp: Any
    ) -> None:
        client.force_login(user_with_totp)
        response = client.get("/select-org/")
        # Either 200 or some other non-enrollment response. The
        # point is it's NOT a redirect to the enrollment path.
        if response.status_code == 302:
            assert MFA_ACTIVATE_PATH not in response["Location"]
        else:
            assert response.status_code == 200

    @pytest.mark.parametrize(
        "allowlisted_path",
        [
            "/accounts/login/",
            "/accounts/logout/",
            "/accounts/2fa/",
            "/accounts/2fa/totp/",
            "/accounts/2fa/totp/activate/",
            "/accounts/password/change/",
            "/accounts/email/",
            "/static/anything.css",
            "/healthz",
            "/readyz",
            "/oauth-help/email_not_verified/",  # M1 D5 Phase 3
        ],
    )
    def test_allowlisted_paths_pass_through(
        self,
        client: Client,
        user_verified_no_mfa: Any,
        allowlisted_path: str,
    ) -> None:
        client.force_login(user_verified_no_mfa)
        response = client.get(allowlisted_path)
        if response.status_code == 302:
            assert MFA_ACTIVATE_PATH not in response["Location"]

    def test_local_mfa_required_emits_once_per_session(
        self, client: Client, user_verified_no_mfa: Any
    ) -> None:
        client.force_login(user_verified_no_mfa)

        client.get("/select-org/")
        first = captured_audit_events(event_type="LOCAL_MFA_CHALLENGE_REQUIRED")
        assert len(first) == 1

        client.get("/select-org/")
        second = captured_audit_events(event_type="LOCAL_MFA_CHALLENGE_REQUIRED")
        assert len(second) == 1, (
            "Middleware emitted LOCAL_MFA_CHALLENGE_REQUIRED twice for "
            "the same session — throttle is broken."
        )

    def test_system_user_carve_out(self, client: Client, db: Any) -> None:
        from django.contrib.auth import get_user_model

        User = get_user_model()
        system_user = User.objects.get(is_system=True)
        client.force_login(system_user)
        response = client.get("/select-org/")
        if response.status_code == 302:
            assert MFA_ACTIVATE_PATH not in response["Location"]


# ---------------------------------------------------------------------------
# M1 D5 Phase 4 — trusted-vs-untrusted provider MFA policy.
# ---------------------------------------------------------------------------


@pytest.fixture
def trusted_provider(db: Any) -> OAuthProviderConfig:
    """A provider configured as trusted for external MFA."""
    return OAuthProviderConfig.objects.create(
        provider_code="trusted-oidc",
        display_name="Trusted OIDC",
        provider_type=ProviderType.OIDC,
        issuer_url="https://trusted-issuer.example.test",
        client_id_env_key="OAUTH_TRUSTED_OIDC_CLIENT_ID",
        client_secret_env_key="OAUTH_TRUSTED_OIDC_CLIENT_SECRET",
        is_active=True,
        require_verified_email=True,
        trust_external_mfa=True,
    )


@pytest.fixture
def untrusted_provider(db: Any) -> OAuthProviderConfig:
    """A provider configured as NOT trusted for external MFA."""
    return OAuthProviderConfig.objects.create(
        provider_code="untrusted-oidc",
        display_name="Untrusted OIDC",
        provider_type=ProviderType.OIDC,
        issuer_url="https://untrusted-issuer.example.test",
        client_id_env_key="OAUTH_UNTRUSTED_OIDC_CLIENT_ID",
        client_secret_env_key="OAUTH_UNTRUSTED_OIDC_CLIENT_SECRET",
        is_active=True,
        require_verified_email=True,
        trust_external_mfa=False,
    )


def _login_via_provider(
    client: Client,
    user: Any,
    provider_code: str,
) -> None:
    """Test helper: simulate an OAuth login by setting the session key
    that the OAuth signal handler would have written at login time.

    Used instead of running allauth's full OAuth flow because:
    - the full flow needs the mock OIDC issuer (Phase 6).
    - the middleware behavior under test is independent of how the
      session key got there.
    """
    client.force_login(user)
    session = client.session
    session[SESSION_KEY_LOGIN_PROVIDER_CODE] = provider_code
    session.save()


@pytest.mark.django_db
class TestTrustedProviderBypassesEnrollment:
    """B.4.8: trusted-provider OAuth user with no TOTP can proceed."""

    def test_trusted_provider_no_totp_passes_through(
        self,
        client: Client,
        user_verified_no_mfa: Any,
        trusted_provider: OAuthProviderConfig,
    ) -> None:
        _login_via_provider(client, user_verified_no_mfa, "trusted-oidc")

        response = client.get("/select-org/")
        # Must NOT redirect to enrollment.
        if response.status_code == 302:
            assert MFA_ACTIVATE_PATH not in response["Location"]
        else:
            assert response.status_code == 200

    def test_trusted_provider_emits_provider_mfa_trusted(
        self,
        client: Client,
        user_verified_no_mfa: Any,
        trusted_provider: OAuthProviderConfig,
    ) -> None:
        _login_via_provider(client, user_verified_no_mfa, "trusted-oidc")
        client.get("/select-org/")

        events = captured_audit_events(event_type="OAUTH_PROVIDER_MFA_TRUSTED")
        assert len(events) == 1
        event = events[0]
        assert event.actor_id == user_verified_no_mfa.id
        assert event.metadata is not None
        assert event.metadata["provider_code"] == "trusted-oidc"
        assert event.metadata["decision"] == "bypass_local_enrollment"

    def test_trusted_provider_emits_once_per_session(
        self,
        client: Client,
        user_verified_no_mfa: Any,
        trusted_provider: OAuthProviderConfig,
    ) -> None:
        _login_via_provider(client, user_verified_no_mfa, "trusted-oidc")
        client.get("/select-org/")
        client.get("/select-org/")
        client.get("/select-org/")

        events = captured_audit_events(event_type="OAUTH_PROVIDER_MFA_TRUSTED")
        assert (
            len(events) == 1
        ), f"Expected one emission, got {len(events)} — throttle broken."


@pytest.mark.django_db
class TestUntrustedProviderForcesEnrollment:
    """B.4.8: untrusted-provider OAuth user must enroll local TOTP."""

    def test_untrusted_provider_no_totp_redirected_to_enrollment(
        self,
        client: Client,
        user_verified_no_mfa: Any,
        untrusted_provider: OAuthProviderConfig,
    ) -> None:
        _login_via_provider(client, user_verified_no_mfa, "untrusted-oidc")

        response = client.get("/select-org/")
        assert response.status_code == 302
        assert response["Location"] == MFA_ACTIVATE_PATH

    def test_untrusted_provider_emits_provider_mfa_not_trusted(
        self,
        client: Client,
        user_verified_no_mfa: Any,
        untrusted_provider: OAuthProviderConfig,
    ) -> None:
        _login_via_provider(client, user_verified_no_mfa, "untrusted-oidc")
        client.get("/select-org/")

        events = captured_audit_events(event_type="OAUTH_PROVIDER_MFA_NOT_TRUSTED")
        assert len(events) == 1
        event = events[0]
        assert event.actor_id == user_verified_no_mfa.id
        assert event.metadata is not None
        assert event.metadata["provider_code"] == "untrusted-oidc"
        assert event.metadata["decision"] == "force_local_enrollment"

    def test_untrusted_provider_emits_once_per_session(
        self,
        client: Client,
        user_verified_no_mfa: Any,
        untrusted_provider: OAuthProviderConfig,
    ) -> None:
        _login_via_provider(client, user_verified_no_mfa, "untrusted-oidc")
        client.get("/select-org/")
        client.get("/select-org/")
        client.get("/select-org/")

        events = captured_audit_events(event_type="OAUTH_PROVIDER_MFA_NOT_TRUSTED")
        assert len(events) == 1


@pytest.mark.django_db
class TestExistingTOTPBypassesMiddleware:
    """If the user already has TOTP, no enrollment policy applies.

    Belt-and-suspenders: even for an OAuth user via untrusted provider,
    if they happen to ALREADY have TOTP enrolled, the middleware
    doesn't fire OAUTH_PROVIDER_MFA_* events. The decision point is
    'is enrollment needed', not 'what login method'.
    """

    def test_user_with_totp_via_trusted_provider_no_audit(
        self,
        client: Client,
        user_with_totp: Any,
        trusted_provider: OAuthProviderConfig,
    ) -> None:
        _login_via_provider(client, user_with_totp, "trusted-oidc")
        client.get("/select-org/")

        events = captured_audit_events(event_type="OAUTH_PROVIDER_MFA_TRUSTED")
        assert events == []

    def test_user_with_totp_via_untrusted_provider_no_redirect(
        self,
        client: Client,
        user_with_totp: Any,
        untrusted_provider: OAuthProviderConfig,
    ) -> None:
        _login_via_provider(client, user_with_totp, "untrusted-oidc")
        response = client.get("/select-org/")
        if response.status_code == 302:
            assert MFA_ACTIVATE_PATH not in response["Location"]


@pytest.mark.django_db
class TestUnknownProviderCodeForcesEnrollment:
    """Defense in depth: if the provider config can't be loaded, the
    middleware MUST fall back to forcing enrollment.

    This shouldn't happen in practice (signal handler writes the code,
    and providers aren't deleted mid-session), but if it does — e.g.
    operator deactivates a provider while users are mid-session — the
    safe default is to force local MFA.
    """

    def test_unknown_provider_code_redirects_to_enrollment(
        self, client: Client, user_verified_no_mfa: Any
    ) -> None:
        # Set a provider code that doesn't match any OAuthProviderConfig.
        _login_via_provider(client, user_verified_no_mfa, "no-such-provider")

        response = client.get("/select-org/")
        assert response.status_code == 302
        assert response["Location"] == MFA_ACTIVATE_PATH

    def test_unknown_provider_code_emits_not_trusted(
        self, client: Client, user_verified_no_mfa: Any
    ) -> None:
        _login_via_provider(client, user_verified_no_mfa, "no-such-provider")
        client.get("/select-org/")

        events = captured_audit_events(event_type="OAUTH_PROVIDER_MFA_NOT_TRUSTED")
        assert len(events) == 1
        assert events[0].metadata is not None
        assert events[0].metadata["provider_code"] == "no-such-provider"


@pytest.mark.django_db
class TestThrottleIsPerSession:
    """A fresh login session gets a fresh throttle slate.

    Logging out and back in should yield a new emission because the
    session is replaced.
    """

    def test_new_session_gets_new_emission(
        self,
        client: Client,
        user_verified_no_mfa: Any,
        trusted_provider: OAuthProviderConfig,
    ) -> None:
        # Session 1.
        _login_via_provider(client, user_verified_no_mfa, "trusted-oidc")
        client.get("/select-org/")
        client.logout()

        # Session 2.
        _login_via_provider(client, user_verified_no_mfa, "trusted-oidc")
        client.get("/select-org/")

        events = captured_audit_events(event_type="OAUTH_PROVIDER_MFA_TRUSTED")
        assert len(events) == 2, (
            "Expected two emissions across two sessions, got " f"{len(events)}."
        )
