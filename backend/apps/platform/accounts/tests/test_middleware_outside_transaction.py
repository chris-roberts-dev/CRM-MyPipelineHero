"""Production-realism guard for RequireMfaEnrollmentMiddleware.

The standard middleware tests use the pytest-django @pytest.mark.django_db
decorator without ``transaction=True``, which wraps each test in a
transaction. That wrapping inadvertently satisfies the audit service's
"must be in a transaction" check — masking the bug where middleware
calls audit_emit directly without opening its own transaction.

This file's tests use ``transaction=True`` so pytest-django commits
each statement (no enclosing transaction). The middleware then runs in
the same state as production. If a future change makes the middleware
call audit_emit directly again, these tests fail with
AuditOutsideTransactionError — surfacing the bug before deploy rather
than after.
"""

from __future__ import annotations

from typing import Any

import pytest
from django.test import Client

from apps.platform.accounts.oauth.models import OAuthProviderConfig, ProviderType

# Mirror the helpers from test_middleware.py — duplicated here rather
# than imported to make each test file self-contained for the
# production-realism contract.
SESSION_KEY_LOGIN_PROVIDER_CODE = "mph_login_provider_code"
MFA_ACTIVATE_PATH = "/accounts/2fa/totp/activate/"


def _login_via_provider(client: Client, user: Any, provider_code: str) -> None:
    client.force_login(user)
    session = client.session
    session[SESSION_KEY_LOGIN_PROVIDER_CODE] = provider_code
    session.save()


@pytest.mark.django_db(transaction=True)
class TestMiddlewareEmissionsOutsideTransaction:
    """Regression guard: emit paths must not crash outside a transaction.

    Each test below would have caught the bug at:
    AuditOutsideTransactionError at /select-org/

    where the middleware called audit_emit directly while no
    request-level transaction was open.
    """

    def test_local_password_emission_does_not_crash(
        self, client: Client, user_verified_no_mfa: Any
    ) -> None:
        client.force_login(user_verified_no_mfa)
        response = client.get("/select-org/")
        # The middleware redirects to MFA enrollment. The point of
        # this test is that the redirect succeeds — it does NOT
        # raise AuditOutsideTransactionError before reaching the
        # redirect.
        assert response.status_code == 302
        assert response["Location"] == MFA_ACTIVATE_PATH

    def test_trusted_provider_emission_does_not_crash(
        self,
        client: Client,
        user_verified_no_mfa: Any,
        db: Any,
    ) -> None:
        provider = OAuthProviderConfig.objects.create(
            provider_code="prod-realism-trusted",
            display_name="Prod Realism Trusted",
            provider_type=ProviderType.OIDC,
            issuer_url="https://issuer.example.test",
            client_id_env_key="OAUTH_PROD_REALISM_TRUSTED_CLIENT_ID",
            client_secret_env_key="OAUTH_PROD_REALISM_TRUSTED_CLIENT_SECRET",
            is_active=True,
            trust_external_mfa=True,
        )
        _login_via_provider(client, user_verified_no_mfa, provider.provider_code)
        # Trusted-provider user with no TOTP: middleware emits
        # OAUTH_PROVIDER_MFA_TRUSTED and falls through (no redirect).
        # The test passes if the emission doesn't crash.
        response = client.get("/select-org/")
        # Status will be whatever /select-org/ returns for this user.
        # We just care that nothing raised before the view ran.
        assert response.status_code in (200, 302)
        # If a redirect, it MUST NOT be to enrollment (trusted bypasses).
        if response.status_code == 302:
            assert MFA_ACTIVATE_PATH not in response["Location"]

    def test_untrusted_provider_emission_does_not_crash(
        self,
        client: Client,
        user_verified_no_mfa: Any,
        db: Any,
    ) -> None:
        provider = OAuthProviderConfig.objects.create(
            provider_code="prod-realism-untrusted",
            display_name="Prod Realism Untrusted",
            provider_type=ProviderType.OIDC,
            issuer_url="https://issuer.example.test",
            client_id_env_key="OAUTH_PROD_REALISM_UNTRUSTED_CLIENT_ID",
            client_secret_env_key="OAUTH_PROD_REALISM_UNTRUSTED_CLIENT_SECRET",
            is_active=True,
            trust_external_mfa=False,
        )
        _login_via_provider(client, user_verified_no_mfa, provider.provider_code)
        response = client.get("/select-org/")
        # Untrusted-provider user with no TOTP: middleware emits
        # OAUTH_PROVIDER_MFA_NOT_TRUSTED and redirects to enrollment.
        assert response.status_code == 302
        assert response["Location"] == MFA_ACTIVATE_PATH
