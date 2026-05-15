"""End-to-end MFA tests (J.3.9 #4, #5).

These tests exercise allauth's real MFA flow — POSTing to enrollment,
satisfying the challenge with a real computed TOTP code, and consuming
a recovery code. The smoke suite uses fixture-built authenticators
for speed; these tests trade speed for fidelity to verify that the
flow itself works.

Coverage:
- J.3.9 #4: Local MFA enrollment + challenge work.
- J.3.9 #5: Recovery codes are single-use.
- J.3.5 #1: Local password login with MFA.
- J.3.5 #2: Local password login without enrolled MFA forces enrollment.

TOTP code computation uses the in-repo ``totp_code_for`` helper (RFC
6238 against MFA_TOTP_* settings), avoiding a pyotp dependency.
"""

from __future__ import annotations

import re
from typing import Any

import pytest
from allauth.mfa.models import Authenticator
from django.test import Client

from apps.platform.accounts.tests._helpers import totp_code_for


def _extract_totp_secret(client: Client, response_body: str) -> str | None:
    """Extract the TOTP setup secret from the activation page.

    Tries two strategies in order:

    1. Read it from the session, where allauth.mfa stashes the
       in-progress secret during the activation flow. Tried under
       both 65.x key names.
    2. Scrape the rendered HTML. Our template renders the secret
       inside a ``<code class="mph-mfa-secret-code">`` element, but
       attribute order and additional class tokens vary by template
       state, so use a permissive regex.

    Returns the secret as a base32 string, or None if both strategies
    fail (caller should assert and dump body for debugging).
    """
    # Strategy 1: session stash.
    session = client.session
    for key in ("allauth.mfa.totp.secret", "mfa.totp.secret"):
        secret = session.get(key)
        if secret:
            return str(secret)

    # Strategy 2: HTML scrape. Match any <code> element near our
    # `mph-mfa-secret-code` class regardless of attribute order. The
    # secret is base32 — uppercase letters A-Z and digits 2-7, with
    # optional `=` padding.
    match = re.search(
        r"<code[^>]*\bmph-mfa-secret-code\b[^>]*>\s*([A-Z2-7=]{16,})\s*</code>",
        response_body,
    )
    if match:
        return match.group(1)
    return None


@pytest.mark.django_db
class TestLocalLoginWithoutMfaForcesEnrollment:
    """J.3.5 #2: a verified user with no TOTP is forced to enroll."""

    def test_post_login_redirects_to_enrollment(
        self, client: Client, user_verified_no_mfa: Any
    ) -> None:
        response = client.post(
            "/accounts/login/",
            {
                "login": user_verified_no_mfa.email,
                "password": "test-password-1234!",
            },
            follow=True,
        )
        # The middleware intercepts and redirects to TOTP activation.
        assert response.request["PATH_INFO"] == "/accounts/2fa/totp/activate/"


@pytest.mark.django_db
class TestMfaEnrollmentAndChallenge:
    """J.3.9 #4: enrollment + challenge work end-to-end."""

    def test_full_enrollment_and_subsequent_challenge(
        self, client: Client, user_verified_no_mfa: Any
    ) -> None:
        # Step 1: log in with password.
        client.post(
            "/accounts/login/",
            {
                "login": user_verified_no_mfa.email,
                "password": "test-password-1234!",
            },
            follow=True,
        )

        # Step 2: GET the activation page to receive the secret.
        response = client.get("/accounts/2fa/totp/activate/")
        assert response.status_code == 200

        body = response.content.decode()
        secret = _extract_totp_secret(client, body)
        assert secret, (
            "Could not extract TOTP secret from activation page or "
            "session. Either allauth changed the session key where it "
            "stashes the in-progress secret, or the template no longer "
            "renders the manual-entry code with mph-mfa-secret-code. "
            f"First 1500 chars of body: {body[:1500]}"
        )

        # Step 3: POST the confirmation code.
        code = totp_code_for(secret)
        response = client.post(
            "/accounts/2fa/totp/activate/",
            {"code": code},
            follow=True,
        )
        assert response.status_code == 200
        # User should now have a TOTP authenticator.
        assert Authenticator.objects.filter(
            user=user_verified_no_mfa, type=Authenticator.Type.TOTP
        ).exists()

        # Step 4: log out and log back in to verify the challenge works.
        client.logout()
        client.post(
            "/accounts/login/",
            {
                "login": user_verified_no_mfa.email,
                "password": "test-password-1234!",
            },
            follow=True,
        )

        # Step 5: provide the TOTP code to the challenge.
        code = totp_code_for(secret)
        response = client.post(
            "/accounts/2fa/authenticate/",
            {"code": code},
            follow=True,
        )
        assert response.status_code == 200
        # Should now be on /select-org/ (the LOGIN_REDIRECT_URL).
        assert "/select-org/" in response.request["PATH_INFO"]


@pytest.mark.django_db
class TestRecoveryCodesSingleUse:
    """J.3.9 #5: recovery codes are single-use.

    Uses allauth's real generate-recovery-codes view to obtain a valid
    code (rather than the fixture-built raw seed), so the wrapper's
    consumption logic actually fires.
    """

    def test_recovery_code_consumed_once(
        self,
        client: Client,
        user_verified_no_mfa: Any,
    ) -> None:
        # Bootstrap: log in and enroll TOTP via the real flow (since
        # generating recovery codes requires TOTP first).
        client.post(
            "/accounts/login/",
            {
                "login": user_verified_no_mfa.email,
                "password": "test-password-1234!",
            },
            follow=True,
        )
        response = client.get("/accounts/2fa/totp/activate/")
        body = response.content.decode()
        secret = _extract_totp_secret(client, body)
        assert secret, "TOTP secret not in activation page or session"

        client.post(
            "/accounts/2fa/totp/activate/",
            {"code": totp_code_for(secret)},
            follow=True,
        )

        # Generate recovery codes via the real view. After POST, the
        # generated codes are rendered on the index page.
        client.post("/accounts/2fa/recovery-codes/generate/", follow=True)
        response = client.get("/accounts/2fa/recovery-codes/")
        assert response.status_code == 200

        # The codes render inside <li><code>...</code></li>.
        body = response.content.decode()
        codes = re.findall(r"<li><code>([^<]+)</code></li>", body)
        assert codes, (
            "No recovery codes found on the index page after generation. "
            f"First 1500 chars: {body[:1500]}"
        )
        first_code = codes[0].strip()

        # Log out and back in.
        client.logout()
        client.post(
            "/accounts/login/",
            {
                "login": user_verified_no_mfa.email,
                "password": "test-password-1234!",
            },
            follow=True,
        )

        # Use the recovery code to satisfy the challenge — should succeed.
        response = client.post(
            "/accounts/2fa/authenticate/",
            {"code": first_code},
            follow=True,
        )
        assert response.status_code == 200
        assert "/select-org/" in response.request["PATH_INFO"]

        # Log out and try the SAME code again — must be rejected.
        client.logout()
        client.post(
            "/accounts/login/",
            {
                "login": user_verified_no_mfa.email,
                "password": "test-password-1234!",
            },
            follow=True,
        )
        response = client.post(
            "/accounts/2fa/authenticate/",
            {"code": first_code},
            follow=True,
        )
        # The re-used code is rejected: we stay on the challenge page
        # rather than progressing to /select-org/.
        assert (
            response.request["PATH_INFO"] == "/accounts/2fa/authenticate/"
        ), "Re-used recovery code was accepted — single-use rule broken."
