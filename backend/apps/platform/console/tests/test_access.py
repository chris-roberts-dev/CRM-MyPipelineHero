"""Tests for PlatformConsoleAccessMixin and platform-URL access.

Three scenarios per view:
* Anonymous → redirect to login.
* Authenticated non-staff → 403.
* Authenticated staff → 200 (for list URLs) or 404 (for detail URLs
  with non-existent identifiers — the auth check still passed).

We test against every Phase 1/2 platform URL to confirm the mixin
is wired uniformly. If a Phase 3+ view forgets to inherit the
mixin, the corresponding 403 test will catch it.
"""

from __future__ import annotations

from typing import Any

import pytest
from django.test import Client

# Phase 1+2 URLs that resolve to a 200 page for staff users.
# PlatformHomeView (root /platform/) is a redirect; tested
# separately below.
LIST_URLS = [
    "/platform/orgs/",
    "/platform/users/",
    "/platform/signing-keys/",
    "/platform/impersonation/",
]

# Phase 2 detail URLs. For staff users, these 404 (the identifier
# in the URL doesn't reference a real row), but the auth mixin
# fires first, so we know it ran iff we get 404 instead of 403.
DETAIL_URLS_WITH_404 = [
    "/platform/orgs/some-slug/",
    "/platform/users/00000000-0000-0000-0000-000000000000/",
]

# All URLs the mixin must guard. Used for anon/non-staff
# parametrization where the expected response is independent of
# whether the identifier resolves.
ALL_GUARDED_URLS = LIST_URLS + DETAIL_URLS_WITH_404


@pytest.mark.django_db
class TestAnonymousAccess:
    @pytest.mark.parametrize("url", ALL_GUARDED_URLS)
    def test_anonymous_request_redirects_to_login(
        self, client: Client, url: str
    ) -> None:
        response = client.get(url)
        assert response.status_code == 302
        assert "/accounts/login/" in response["Location"]
        assert url in response["Location"]


@pytest.mark.django_db
class TestNonStaffAccess:
    @pytest.mark.parametrize("url", ALL_GUARDED_URLS)
    def test_non_staff_user_gets_403(
        self,
        client: Client,
        user_verified_with_totp: Any,
        url: str,
    ) -> None:
        assert user_verified_with_totp.is_staff is False
        client.force_login(user_verified_with_totp)
        response = client.get(url)
        assert response.status_code == 403


@pytest.mark.django_db
class TestStaffAccess:
    @pytest.fixture
    def staff_user(self, user_verified_with_totp: Any) -> Any:
        user_verified_with_totp.is_staff = True
        user_verified_with_totp.save()
        return user_verified_with_totp

    @pytest.mark.parametrize("url", LIST_URLS)
    def test_staff_user_can_load_list_urls(
        self, client: Client, staff_user: Any, url: str
    ) -> None:
        client.force_login(staff_user)
        response = client.get(url)
        assert response.status_code == 200
        assert b"Platform Console" in response.content
        assert b"staff" in response.content

    @pytest.mark.parametrize("url", DETAIL_URLS_WITH_404)
    def test_staff_user_detail_urls_pass_auth_then_404(
        self, client: Client, staff_user: Any, url: str
    ) -> None:
        """For URLs with non-existent identifiers, staff sees 404 (not 403)
        — auth check passed; the resolver couldn't find the row."""
        client.force_login(staff_user)
        response = client.get(url)
        assert response.status_code == 404


@pytest.mark.django_db
class TestPlatformHomeRedirect:
    def test_unauth_root_redirects_to_login(self, client: Client) -> None:
        response = client.get("/platform/")
        assert response.status_code == 302
        assert "/accounts/login/" in response["Location"]

    def test_non_staff_root_gets_403(
        self, client: Client, user_verified_with_totp: Any
    ) -> None:
        client.force_login(user_verified_with_totp)
        response = client.get("/platform/")
        assert response.status_code == 403

    def test_staff_root_redirects_to_orgs(
        self, client: Client, user_verified_with_totp: Any
    ) -> None:
        user_verified_with_totp.is_staff = True
        user_verified_with_totp.save()
        client.force_login(user_verified_with_totp)

        response = client.get("/platform/")
        assert response.status_code == 302
        assert response["Location"] == "/platform/orgs/"


@pytest.mark.django_db
class TestNavigationChrome:
    @pytest.fixture
    def staff_user(self, user_verified_with_totp: Any) -> Any:
        user_verified_with_totp.is_staff = True
        user_verified_with_totp.save()
        return user_verified_with_totp

    def test_sidebar_lists_all_phase1_surfaces(
        self, client: Client, staff_user: Any
    ) -> None:
        client.force_login(staff_user)
        response = client.get("/platform/orgs/")
        body = response.content.decode()
        assert "Organizations" in body
        assert "Users" in body
        assert "Handoff Signing Keys" in body
        assert "Impersonation" in body

    def test_current_page_highlighted_in_sidebar(
        self, client: Client, staff_user: Any
    ) -> None:
        client.force_login(staff_user)
        response = client.get("/platform/orgs/")
        body = response.content.decode()
        assert "bg-gray-200" in body
