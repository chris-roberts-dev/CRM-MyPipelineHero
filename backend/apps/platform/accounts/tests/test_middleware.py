"""Tests for RequireMfaEnrollmentMiddleware (M1 D4).

The middleware enforces B.4.9: authenticated local-password users
without an enrolled TOTP authenticator must be redirected to
``/accounts/2fa/totp/activate/`` (allauth.mfa's TOTP activation
form) before reaching any non-allowlist path.
"""

from __future__ import annotations

from typing import Any

import pytest
from django.test import Client

from apps.platform.audit.services import captured_audit_events

# The allauth-mfa URL that the middleware redirects unenrolled users
# to. In allauth 65.x the canonical name for the TOTP activation
# view resolves to this path. The middleware reverses
# ``mfa_activate_totp``; this constant is the resolved URL so tests
# don't have to round-trip through ``reverse()`` for every assertion.
MFA_ACTIVATE_PATH = "/accounts/2fa/totp/activate/"


@pytest.mark.django_db
class TestRequireMfaEnrollmentMiddleware:
    def test_anonymous_user_passes_through(self, client: Client) -> None:
        # Landing page is anonymous-accessible. Anonymous + no MFA
        # state must not redirect to enrollment.
        response = client.get("/")
        # Either 200 (landing renders) or a redirect to login is fine,
        # but it must NOT be a redirect to the enrollment path.
        if response.status_code == 302:
            assert MFA_ACTIVATE_PATH not in response["Location"]

    def test_authenticated_no_totp_redirected_to_enrollment(
        self, client: Client, user_verified_no_mfa: Any
    ) -> None:
        client.force_login(user_verified_no_mfa)
        response = client.get("/select-org/")
        assert response.status_code == 302
        assert response["Location"] == MFA_ACTIVATE_PATH

    def test_authenticated_with_totp_passes_through(
        self, client: Client, user_with_totp: Any
    ) -> None:
        client.force_login(user_with_totp)
        response = client.get("/select-org/")
        # Either 200 or some other non-enrollment response. The point
        # is it's NOT a redirect to the enrollment path.
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
        # The path itself may 404 (e.g. /static/anything.css), but the
        # middleware must NOT redirect to enrollment.
        if response.status_code == 302:
            assert MFA_ACTIVATE_PATH not in response["Location"]

    def test_emits_local_mfa_challenge_required_once_per_session(
        self, client: Client, user_verified_no_mfa: Any
    ) -> None:
        client.force_login(user_verified_no_mfa)

        # First non-allowlisted request → should emit.
        client.get("/select-org/")
        first = captured_audit_events(event_type="LOCAL_MFA_CHALLENGE_REQUIRED")
        assert len(first) == 1

        # Second request → should NOT emit again (throttled).
        client.get("/select-org/")
        second = captured_audit_events(event_type="LOCAL_MFA_CHALLENGE_REQUIRED")
        assert len(second) == 1, (
            "Middleware emitted LOCAL_MFA_CHALLENGE_REQUIRED twice for "
            "the same session — throttle is broken."
        )

    def test_system_user_carve_out(self, client: Client, db: Any) -> None:
        """The System User should never be redirected to enrollment.

        Defensive: in practice the System User has an unusable password
        and cannot authenticate; this verifies the carve-out logic in
        case a session with ``is_system=True`` ever arrives.
        """
        from django.contrib.auth import get_user_model

        User = get_user_model()
        system_user = User.objects.get(is_system=True)
        client.force_login(system_user)
        response = client.get("/select-org/")
        if response.status_code == 302:
            assert MFA_ACTIVATE_PATH not in response["Location"]
