"""Tests for auth_portal URL routing (M1 D4).

Verifies:
- /login/ permanent-redirects to /accounts/login/ (preserving ?next=).
- /select-org/ requires authentication.
- /accounts/login/ resolves to allauth's LoginView (override is picked up).
"""

from __future__ import annotations

from typing import Any

import pytest
from django.test import Client
from django.urls import resolve


@pytest.mark.django_db
class TestAuthPortalRouting:
    def test_login_redirect_to_allauth(self, client: Client) -> None:
        response = client.get("/login/")
        assert response.status_code in (301, 302)
        assert response["Location"].startswith("/accounts/login/")

    def test_login_redirect_preserves_next(self, client: Client) -> None:
        response = client.get("/login/?next=/some/page/")
        assert response.status_code in (301, 302)
        assert "next=" in response["Location"]
        assert (
            "%2Fsome%2Fpage%2F" in response["Location"]
            or "/some/page/" in response["Location"]
        )

    def test_select_org_requires_authentication(self, client: Client) -> None:
        response = client.get("/select-org/")
        # Anonymous → 302 to login (Django's @login_required behavior).
        assert response.status_code == 302
        # Must redirect to LOGIN_URL, NOT to /accounts/2fa/totp/ —
        # anonymous users haven't authenticated, so MFA gating doesn't
        # apply.
        assert "/accounts/login/" in response["Location"]

    def test_select_org_accessible_post_login_and_mfa(
        self, client: Client, user_with_totp: Any
    ) -> None:
        client.force_login(user_with_totp)
        response = client.get("/select-org/")
        # With TOTP enrolled, MFA middleware passes through.
        # The placeholder view returns 200.
        assert response.status_code == 200
        assert user_with_totp.email in response.content.decode()

    def test_accounts_login_resolves_to_allauth(self) -> None:
        """allauth.urls is mounted at /accounts/ — verify it owns login."""
        match = resolve("/accounts/login/")
        # Allauth's LoginView lives at allauth.account.views.LoginView.
        assert "allauth" in match.func.__module__
