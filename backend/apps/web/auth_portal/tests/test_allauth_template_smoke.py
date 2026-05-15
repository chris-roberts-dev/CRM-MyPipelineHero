"""Allauth template-rendering smoke suite (M1 D4).

THE SPINE OF M1 D4 TEST COVERAGE.

For each allauth-rendered template, this suite:
1. Sets up the right user state (anonymous / verified / TOTP / etc.).
2. Issues a request that lands the user on that template.
3. Asserts the response is 200.
4. Asserts a representative `mph-*` class appears in the body
   (proves our override was picked up, not allauth's bundled default).

This is the test pattern that would have caught both the
`user.username` AttributeError and the `unused_count`
TemplateSyntaxError. Any new template override added in future
milestones MUST be added here.

The smoke suite is intentionally parametrized over a table of
template configurations so the boilerplate stays minimal and the
table is the readable contract.

Some templates require setup (POST a form, create an EmailConfirmation,
etc.) to reach. Each table row carries a `setup_fn` that does that
setup before the GET. The default no-op setup_fn is used for templates
reachable by a plain authenticated GET.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

import pytest
from allauth.account.models import EmailAddress, EmailConfirmationHMAC
from django.test import Client
from django.urls import reverse

# An MPH-distinctive class to assert per template. We use either
# `mph-auth-card` (public shell) or `mph-settings-card` (settings
# shell) depending on which base the template extends. If neither
# appears in the response, our override didn't render and allauth's
# bundled template did — fail loudly.
MPH_PUBLIC_CLASS = "mph-auth-card"
MPH_SETTINGS_CLASS = "mph-settings-card"


@dataclass
class TemplateCase:
    """A single allauth template to smoke-test."""

    name: str  # pytest id
    path: str  # URL to GET
    user_fixture: (
        str | None
    )  # name of the fixture giving the right user; None = anonymous
    expected_class: str  # mph-auth-card or mph-settings-card
    setup_fn: Callable[..., Any] | None = None  # optional setup before GET


# ---------------------------------------------------------------------------
# Setup helpers — used by table rows that need state before the GET.
# ---------------------------------------------------------------------------


def _setup_email_confirmation(client: Client, user: Any) -> str:
    """Create a pending EmailConfirmation for an unverified user."""
    addr = EmailAddress.objects.filter(user=user, verified=False).first()
    if addr is None:
        addr = EmailAddress.objects.create(
            user=user, email=user.email, verified=False, primary=True
        )
    conf = EmailConfirmationHMAC(addr)
    return reverse("account_confirm_email", args=[conf.key])


def _setup_password_reset_key(client: Client, user: Any) -> str:
    """Create a valid password-reset key URL."""
    from allauth.account.forms import default_token_generator
    from allauth.account.utils import user_pk_to_url_str

    token = default_token_generator.make_token(user)
    uidb36 = user_pk_to_url_str(user)
    return reverse(
        "account_reset_password_from_key",
        kwargs={"uidb36": uidb36, "key": token},
    )


# ---------------------------------------------------------------------------
# The table — every allauth template we override.
# ---------------------------------------------------------------------------

TEMPLATE_CASES: list[TemplateCase] = [
    # ---------- Public shell (account/_public_base.html) ----------
    TemplateCase(
        name="account-login",
        path="/accounts/login/",
        user_fixture=None,
        expected_class=MPH_PUBLIC_CLASS,
    ),
    TemplateCase(
        name="account-logout",
        path="/accounts/logout/",
        user_fixture="user_with_totp",
        expected_class=MPH_PUBLIC_CLASS,
    ),
    TemplateCase(
        name="account-signup",
        path="/accounts/signup/",
        user_fixture=None,
        expected_class=MPH_PUBLIC_CLASS,
    ),
    TemplateCase(
        name="account-password-reset",
        path="/accounts/password/reset/",
        user_fixture=None,
        expected_class=MPH_PUBLIC_CLASS,
    ),
    TemplateCase(
        name="account-password-reset-done",
        path="/accounts/password/reset/done/",
        user_fixture=None,
        expected_class=MPH_PUBLIC_CLASS,
    ),
    # ---------- Settings shell (account/_settings_base.html) ----------
    TemplateCase(
        name="account-password-change",
        path="/accounts/password/change/",
        user_fixture="user_with_totp",
        expected_class=MPH_SETTINGS_CLASS,
    ),
    TemplateCase(
        name="account-email",
        path="/accounts/email/",
        user_fixture="user_with_totp",
        expected_class=MPH_SETTINGS_CLASS,
    ),
    TemplateCase(
        name="mfa-index",
        path="/accounts/2fa/",
        user_fixture="user_with_totp",
        expected_class=MPH_SETTINGS_CLASS,
    ),
    TemplateCase(
        name="mfa-totp-deactivate",
        path="/accounts/2fa/totp/deactivate/",
        user_fixture="user_with_totp",
        expected_class=MPH_SETTINGS_CLASS,
    ),
    TemplateCase(
        name="mfa-recovery-codes-index",
        path="/accounts/2fa/recovery-codes/",
        user_fixture="user_with_totp_and_recovery",
        expected_class=MPH_SETTINGS_CLASS,
    ),
    TemplateCase(
        name="mfa-recovery-codes-generate",
        path="/accounts/2fa/recovery-codes/generate/",
        user_fixture="user_with_totp",
        expected_class=MPH_SETTINGS_CLASS,
    ),
    # ---------- TOTP enrollment (public shell — forced flow) ----------
    TemplateCase(
        name="mfa-totp-activate",
        path="/accounts/2fa/totp/activate/",
        user_fixture="user_verified_no_mfa",
        expected_class=MPH_PUBLIC_CLASS,
    ),
    # ---------- select-org placeholder ----------
    TemplateCase(
        name="select-org-placeholder",
        path="/select-org/",
        user_fixture="user_with_totp",
        expected_class=MPH_SETTINGS_CLASS,
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
        # Resolve the user fixture if the case needs an authenticated request.
        if case.user_fixture is not None:
            user = request.getfixturevalue(case.user_fixture)
            client.force_login(user)

        response = client.get(case.path, follow=True)

        assert response.status_code == 200, (
            f"GET {case.path!r} returned {response.status_code}, expected 200. "
            f"Response body (first 500 chars): "
            f"{response.content.decode(errors='replace')[:500]}"
        )

        body = response.content.decode(errors="replace")
        assert case.expected_class in body, (
            f"Template at {case.path!r} did not contain "
            f"{case.expected_class!r}. Either the override is not "
            f"picked up (allauth's bundled template rendered instead), "
            f"or the template extends the wrong base. "
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
        # Allauth's reset flow may redirect through an interstitial;
        # follow=True lands on the actual reset page.
        assert response.status_code == 200
        assert MPH_PUBLIC_CLASS in response.content.decode()

    def test_mfa_authenticate_renders_after_login_with_totp(
        self,
        client: Client,
        user_with_totp: Any,
    ) -> None:
        """The user authenticates with password and lands on the
        TOTP challenge page (because they have TOTP enrolled)."""
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
        # We should be on /accounts/2fa/authenticate/.
        assert "/accounts/2fa/authenticate/" in response.request["PATH_INFO"]
        assert MPH_PUBLIC_CLASS in body
