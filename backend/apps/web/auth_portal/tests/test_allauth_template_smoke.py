"""Allauth template-rendering smoke suite (M1 D4 + M1 D5 Phases 3, 5).

THE SPINE OF M1 D4 / D5 TEST COVERAGE.

For each allauth-rendered template, this suite:
1. Sets up the right user state (anonymous / verified / TOTP / etc.).
2. Issues a request that lands the user on that template.
3. Asserts the response is the expected status (default 200).
4. Asserts a representative ``mph-*`` class appears in the body
   (proves our override was picked up, not allauth's bundled default).

Any new template override added in future milestones MUST be added
to this table.

**Allauth-may-redirect-through-reauth note.** Allauth 65.x gates MFA
management actions behind a fresh-authentication check. Tests that
use ``client.force_login(...)`` don't satisfy this freshness check,
so a GET to e.g. ``/accounts/2fa/totp/activate/`` follows allauth's
redirect to ``/accounts/reauthenticate/`` first. The smoke assertion
therefore accepts EITHER the originally-targeted chrome class OR
the reauthenticate-page's chrome class. The end-to-end MFA test
exercises the real reauth-then-activate flow separately.

**socialaccount/login.html is NOT in this suite.** That template
renders only mid-OAuth-flow (when POSTing to
/accounts/oidc/<provider>/login/), which requires a configured
provider AND the mock OIDC issuer (Phase 6). Smoke-testing it
here would either need stubbed allauth view machinery or the mock
issuer — both belong to Phase 6.

**Non-200 expected_status note.** Some allauth views deliberately
return non-200 statuses on success-of-rendering (e.g. the
``socialaccount_login_error`` view returns 401 because it represents
an auth failure that nevertheless renders a page). The
``expected_status`` field on each ``TemplateCase`` declares the
status the test should accept. A 200 default covers most cases.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

import pytest
from allauth.account.models import EmailAddress, EmailConfirmationHMAC
from django.test import Client
from django.urls import reverse

from apps.platform.accounts.oauth.models import OAuthProviderConfig, ProviderType

MPH_PUBLIC_CLASS = "mph-auth-card"
MPH_SETTINGS_CLASS = "mph-settings-card"


@dataclass
class TemplateCase:
    """A single allauth template to smoke-test."""

    name: str
    path: str
    user_fixture: str | None
    expected_classes: list[str]
    expected_status: int = 200
    setup_fn: Callable[..., Any] | None = None


# ---------------------------------------------------------------------------
# Setup helpers.
# ---------------------------------------------------------------------------


def _setup_email_confirmation(client: Client, user: Any) -> str:
    addr = EmailAddress.objects.filter(user=user, verified=False).first()
    if addr is None:
        addr = EmailAddress.objects.create(
            user=user, email=user.email, verified=False, primary=True
        )
    conf = EmailConfirmationHMAC(addr)
    return reverse("account_confirm_email", args=[conf.key])


def _setup_password_reset_key(client: Client, user: Any) -> str:
    from allauth.account.forms import default_token_generator
    from allauth.account.utils import user_pk_to_url_str

    token = default_token_generator.make_token(user)
    uidb36 = user_pk_to_url_str(user)
    return reverse(
        "account_reset_password_from_key",
        kwargs={"uidb36": uidb36, "key": token},
    )


# ---------------------------------------------------------------------------
# The table.
# ---------------------------------------------------------------------------


TEMPLATE_CASES: list[TemplateCase] = [
    # ---------- Public shell (account/_public_base.html) ----------
    TemplateCase(
        name="account-login",
        path="/accounts/login/",
        user_fixture=None,
        expected_classes=[MPH_PUBLIC_CLASS],
    ),
    TemplateCase(
        name="account-logout",
        path="/accounts/logout/",
        user_fixture="user_with_totp",
        expected_classes=[MPH_PUBLIC_CLASS],
    ),
    TemplateCase(
        name="account-signup",
        path="/accounts/signup/",
        user_fixture=None,
        expected_classes=[MPH_PUBLIC_CLASS],
    ),
    TemplateCase(
        name="account-password-reset",
        path="/accounts/password/reset/",
        user_fixture=None,
        expected_classes=[MPH_PUBLIC_CLASS],
    ),
    TemplateCase(
        name="account-password-reset-done",
        path="/accounts/password/reset/done/",
        user_fixture=None,
        expected_classes=[MPH_PUBLIC_CLASS],
    ),
    # ---------- Settings shell (account/_settings_base.html) ----------
    TemplateCase(
        name="account-password-change",
        path="/accounts/password/change/",
        user_fixture="user_with_totp",
        expected_classes=[MPH_SETTINGS_CLASS],
    ),
    TemplateCase(
        name="account-email",
        path="/accounts/email/",
        user_fixture="user_with_totp",
        expected_classes=[MPH_SETTINGS_CLASS],
    ),
    TemplateCase(
        name="mfa-index",
        path="/accounts/2fa/",
        user_fixture="user_with_totp",
        expected_classes=[MPH_SETTINGS_CLASS],
    ),
    TemplateCase(
        name="mfa-totp-deactivate",
        path="/accounts/2fa/totp/deactivate/",
        user_fixture="user_with_totp",
        expected_classes=[MPH_SETTINGS_CLASS],
    ),
    TemplateCase(
        name="mfa-recovery-codes-index",
        path="/accounts/2fa/recovery-codes/",
        user_fixture="user_with_totp_and_recovery",
        expected_classes=[MPH_SETTINGS_CLASS],
    ),
    TemplateCase(
        name="mfa-recovery-codes-generate",
        path="/accounts/2fa/recovery-codes/generate/",
        user_fixture="user_with_totp",
        expected_classes=[MPH_SETTINGS_CLASS],
    ),
    TemplateCase(
        name="socialaccount-connections",
        path="/accounts/social/connections/",
        user_fixture="user_with_totp",
        expected_classes=[MPH_SETTINGS_CLASS],
    ),
    # ---------- TOTP enrollment ----------
    TemplateCase(
        name="mfa-totp-activate",
        path="/accounts/2fa/totp/activate/",
        user_fixture="user_verified_no_mfa",
        expected_classes=[MPH_PUBLIC_CLASS, MPH_SETTINGS_CLASS],
    ),
    # ---------- select-org placeholder ----------
    TemplateCase(
        name="select-org-placeholder",
        path="/select-org/",
        user_fixture="user_with_totp",
        expected_classes=[MPH_SETTINGS_CLASS],
    ),
    # ---------- M1 D5 Phase 3: OAuth help page ----------
    TemplateCase(
        name="oauth-help-no-existing-user",
        path="/oauth-help/no_existing_user/",
        user_fixture=None,
        expected_classes=[MPH_PUBLIC_CLASS],
    ),
    TemplateCase(
        name="oauth-help-email-not-verified",
        path="/oauth-help/email_not_verified/",
        user_fixture=None,
        expected_classes=[MPH_PUBLIC_CLASS],
    ),
    TemplateCase(
        name="oauth-help-conflicting-identity",
        path="/oauth-help/conflicting_identity/",
        user_fixture=None,
        expected_classes=[MPH_PUBLIC_CLASS],
    ),
    # ---------- M1 D5 Phase 5: socialaccount failure templates ----------
    #
    # The authentication-error view returns HTTP 401 — that's the
    # intended status for "authentication failed" pages. The template
    # itself renders correctly; the smoke test accepts the non-200
    # via expected_status.
    TemplateCase(
        name="socialaccount-authentication-error",
        path="/accounts/social/login/error/",
        user_fixture=None,
        expected_classes=[MPH_PUBLIC_CLASS],
        expected_status=401,
    ),
    TemplateCase(
        name="socialaccount-login-cancelled",
        path="/accounts/social/login/cancelled/",
        user_fixture=None,
        expected_classes=[MPH_PUBLIC_CLASS],
    ),
]


@pytest.mark.django_db
class TestAllauthTemplateSmoke:
    """One parametrized test covering every allauth-rendered template."""

    @pytest.mark.parametrize(
        "case",
        TEMPLATE_CASES,
        ids=[c.name for c in TEMPLATE_CASES],
    )
    def test_template_renders_with_mph_chrome(
        self,
        case: TemplateCase,
        client: Client,
        request: Any,
    ) -> None:
        if case.user_fixture is not None:
            user = request.getfixturevalue(case.user_fixture)
            client.force_login(user)

        response = client.get(case.path, follow=True)

        assert response.status_code == case.expected_status, (
            f"GET {case.path!r} returned {response.status_code}, "
            f"expected {case.expected_status}. "
            f"Response body (first 500 chars): "
            f"{response.content.decode(errors='replace')[:500]}"
        )

        body = response.content.decode(errors="replace")
        assert any(cls in body for cls in case.expected_classes), (
            f"Template at {case.path!r} did not contain any of "
            f"{case.expected_classes!r}. Either the override is not "
            f"picked up (allauth's bundled template rendered instead), "
            f"or the template extends an unexpected base. "
            f"Response body (first 500 chars): {body[:500]}"
        )


@pytest.mark.django_db
class TestAllauthTemplateSmokeStateful:
    """Smoke tests for templates that need stateful setup beyond
    fixture login (email confirmations, password reset keys)."""

    def test_email_confirm_renders(self, client: Client, user_unverified: Any) -> None:
        url = _setup_email_confirmation(client, user_unverified)
        response = client.get(url)
        assert response.status_code == 200
        assert MPH_PUBLIC_CLASS in response.content.decode()

    def test_password_reset_from_key_renders(
        self, client: Client, user_with_totp: Any
    ) -> None:
        url = _setup_password_reset_key(client, user_with_totp)
        response = client.get(url, follow=True)
        assert response.status_code == 200
        assert MPH_PUBLIC_CLASS in response.content.decode()

    def test_mfa_authenticate_renders_after_login_with_totp(
        self,
        client: Client,
        user_with_totp: Any,
    ) -> None:
        response = client.post(
            "/accounts/login/",
            {
                "login": user_with_totp.email,
                "password": "test-password-1234!",
            },
            follow=True,
        )
        assert response.status_code == 200
        body = response.content.decode()
        assert "/accounts/2fa/authenticate/" in response.request["PATH_INFO"]
        assert MPH_PUBLIC_CLASS in body


# ---------------------------------------------------------------------------
# Phase 5: provider-button rendering on the login page.
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestLoginPageProviderButtons:
    """The login page renders a button per active OAuthProviderConfig."""

    def test_no_providers_no_button_section(self, client: Client) -> None:
        """When no providers are active, the SSO section is absent."""
        response = client.get("/accounts/login/")
        body = response.content.decode()
        assert MPH_PUBLIC_CLASS in body
        # No provider section if no providers — the divider is the
        # cheapest tell.
        assert "or sign in with email" not in body
        assert "mph-auth-provider-button" not in body

    def test_active_provider_renders_button(self, client: Client, db: Any) -> None:
        OAuthProviderConfig.objects.create(
            provider_code="test-provider-display",
            display_name="Test Provider Inc.",
            provider_type=ProviderType.OIDC,
            issuer_url="https://issuer.example.test",
            client_id_env_key="OAUTH_TEST_PROVIDER_DISPLAY_CLIENT_ID",
            client_secret_env_key="OAUTH_TEST_PROVIDER_DISPLAY_CLIENT_SECRET",
            is_active=True,
        )

        response = client.get("/accounts/login/")
        body = response.content.decode()

        # Display name is rendered.
        assert "Test Provider Inc." in body
        # Form posts to the provider URL.
        assert 'action="/accounts/oidc/test-provider-display/login/"' in body
        # Button class is present.
        assert "mph-auth-provider-button" in body
        # Divider text appears.
        assert "or sign in with email" in body

    def test_inactive_provider_not_rendered(self, client: Client, db: Any) -> None:
        OAuthProviderConfig.objects.create(
            provider_code="inactive-provider",
            display_name="Inactive Provider",
            provider_type=ProviderType.OIDC,
            issuer_url="https://issuer.example.test",
            client_id_env_key="OAUTH_INACTIVE_PROVIDER_CLIENT_ID",
            client_secret_env_key="OAUTH_INACTIVE_PROVIDER_CLIENT_SECRET",
            is_active=False,
        )

        response = client.get("/accounts/login/")
        body = response.content.decode()

        assert "Inactive Provider" not in body
        assert "mph-auth-provider-button" not in body

    def test_multiple_active_providers_all_rendered(
        self, client: Client, db: Any
    ) -> None:
        OAuthProviderConfig.objects.create(
            provider_code="provider-alpha",
            display_name="Alpha",
            provider_type=ProviderType.OIDC,
            issuer_url="https://issuer-alpha.example.test",
            client_id_env_key="OAUTH_PROVIDER_ALPHA_CLIENT_ID",
            client_secret_env_key="OAUTH_PROVIDER_ALPHA_CLIENT_SECRET",
            is_active=True,
        )
        OAuthProviderConfig.objects.create(
            provider_code="provider-beta",
            display_name="Beta",
            provider_type=ProviderType.OIDC,
            issuer_url="https://issuer-beta.example.test",
            client_id_env_key="OAUTH_PROVIDER_BETA_CLIENT_ID",
            client_secret_env_key="OAUTH_PROVIDER_BETA_CLIENT_SECRET",
            is_active=True,
        )

        response = client.get("/accounts/login/")
        body = response.content.decode()

        assert "Alpha" in body
        assert "Beta" in body
        assert 'action="/accounts/oidc/provider-alpha/login/"' in body
        assert 'action="/accounts/oidc/provider-beta/login/"' in body


# ---------------------------------------------------------------------------
# Phase 5: connections page provider listing.
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestConnectionsPageProviderListing:
    """The connections page lists unlinked active providers."""

    def test_unlinked_provider_renders_link_button(
        self, client: Client, user_with_totp: Any, db: Any
    ) -> None:
        OAuthProviderConfig.objects.create(
            provider_code="link-me",
            display_name="LinkMe Provider",
            provider_type=ProviderType.OIDC,
            issuer_url="https://issuer.example.test",
            client_id_env_key="OAUTH_LINK_ME_CLIENT_ID",
            client_secret_env_key="OAUTH_LINK_ME_CLIENT_SECRET",
            is_active=True,
        )

        client.force_login(user_with_totp)
        response = client.get("/accounts/social/connections/", follow=True)
        body = response.content.decode()

        # The "Link LinkMe Provider" button appears.
        assert "LinkMe Provider" in body
        # The form posts to the provider's connect URL.
        assert 'action="/accounts/oidc/link-me/login/?process=connect"' in body

    def test_already_linked_provider_not_in_link_list(
        self,
        client: Client,
        user_with_totp: Any,
        db: Any,
    ) -> None:
        from allauth.socialaccount.models import SocialAccount

        OAuthProviderConfig.objects.create(
            provider_code="already-linked",
            display_name="Already Linked Provider",
            provider_type=ProviderType.OIDC,
            issuer_url="https://issuer.example.test",
            client_id_env_key="OAUTH_ALREADY_LINKED_CLIENT_ID",
            client_secret_env_key="OAUTH_ALREADY_LINKED_CLIENT_SECRET",
            is_active=True,
        )
        SocialAccount.objects.create(
            user=user_with_totp,
            provider="already-linked",
            uid="some-subject-id",
            extra_data={},
        )

        client.force_login(user_with_totp)
        response = client.get("/accounts/social/connections/", follow=True)
        body = response.content.decode()

        # The connect form should NOT appear for already-linked providers.
        assert (
            'action="/accounts/oidc/already-linked/login/?process=connect"' not in body
        )
