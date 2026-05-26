"""Tests for user search and detail views (M1 D7 Phase 2)."""

from __future__ import annotations

from typing import Any
from uuid import uuid4

import pytest
from django.test import Client
from django.utils import timezone

from apps.platform.organizations.models import (
    Membership,
    MembershipStatus,
    Organization,
)


@pytest.fixture
def staff_user(user_verified_with_totp: Any) -> Any:
    user_verified_with_totp.is_staff = True
    user_verified_with_totp.save()
    return user_verified_with_totp


@pytest.fixture
def staff_client(client: Client, staff_user: Any) -> Client:
    client.force_login(staff_user)
    return client


@pytest.mark.django_db
class TestUserSearch:
    def test_empty_query_shows_prompt_not_results(
        self, staff_client: Client, user_factory: Any
    ) -> None:
        # Make sure there ARE users so an empty-result page isn't
        # confused with an empty database.
        user_factory(email="someone@example.test")
        response = staff_client.get("/platform/users/")
        assert response.status_code == 200
        body = response.content.decode()
        # Prompt visible; that user NOT visible.
        assert "Enter an email substring to search" in body
        assert "someone@example.test" not in body

    def test_query_filters_by_email(
        self, staff_client: Client, user_factory: Any
    ) -> None:
        user_factory(email="alice@example.test")
        user_factory(email="bob@example.test")
        user_factory(email="charlie@example.test")
        response = staff_client.get("/platform/users/?q=ali")
        body = response.content.decode()
        assert "alice@example.test" in body
        assert "bob@example.test" not in body

    def test_query_case_insensitive(
        self, staff_client: Client, user_factory: Any
    ) -> None:
        user_factory(email="alice@example.test")
        response = staff_client.get("/platform/users/?q=ALICE")
        body = response.content.decode()
        assert "alice@example.test" in body

    def test_query_no_matches_shows_message(
        self, staff_client: Client, user_factory: Any
    ) -> None:
        user_factory(email="alice@example.test")
        response = staff_client.get("/platform/users/?q=zzznomatch")
        body = response.content.decode()
        assert "No users match" in body

    def test_user_row_links_to_detail(
        self, staff_client: Client, user_factory: Any
    ) -> None:
        u = user_factory(email="link-test@example.test")
        response = staff_client.get("/platform/users/?q=link-test")
        body = response.content.decode()
        assert f"/platform/users/{u.id}/" in body


@pytest.mark.django_db
class TestUserDetail:
    def test_detail_renders_for_valid_uuid(
        self, staff_client: Client, user_factory: Any
    ) -> None:
        u = user_factory(email="detail-test@example.test")
        response = staff_client.get(f"/platform/users/{u.id}/")
        assert response.status_code == 200
        body = response.content.decode()
        assert "detail-test@example.test" in body

    def test_detail_404_for_unknown_uuid(self, staff_client: Client) -> None:
        random_uuid = uuid4()
        response = staff_client.get(f"/platform/users/{random_uuid}/")
        assert response.status_code == 404

    def test_detail_shows_mfa_not_enrolled_for_user_without_totp(
        self, staff_client: Client, user_factory: Any
    ) -> None:
        u = user_factory(email="no-mfa@example.test")
        response = staff_client.get(f"/platform/users/{u.id}/")
        body = response.content.decode()
        # MFA enrolled section shows "No".
        assert "MFA enrolled" in body
        # Verify totp_enrolled_at row absent — we render literal "No".
        # The check is conservative: find "MFA enrolled" then ensure "No" appears within the next 200 chars.
        idx = body.find("MFA enrolled")
        snippet = body[idx : idx + 300]
        assert "No" in snippet

    def test_detail_shows_mfa_enrolled_for_user_with_totp(
        self, staff_client: Client, user_factory: Any
    ) -> None:
        u = user_factory(email="with-mfa@example.test")
        u.totp_enrolled_at = timezone.now()
        u.save()
        response = staff_client.get(f"/platform/users/{u.id}/")
        body = response.content.decode()
        idx = body.find("MFA enrolled")
        snippet = body[idx : idx + 300]
        assert "Yes" in snippet

    def test_detail_does_not_expose_totp_secret(
        self, staff_client: Client, user_factory: Any
    ) -> None:
        u = user_factory(email="secret-test@example.test")
        u.totp_secret = "JBSWY3DPEHPK3PXP-DO-NOT-LEAK"
        u.totp_enrolled_at = timezone.now()
        u.save()
        response = staff_client.get(f"/platform/users/{u.id}/")
        body = response.content.decode()
        assert "JBSWY3DPEHPK3PXP-DO-NOT-LEAK" not in body

    def test_detail_does_not_expose_backup_codes_hash(
        self, staff_client: Client, user_factory: Any
    ) -> None:
        u = user_factory(email="codes-test@example.test")
        u.backup_codes_hash = "sentinel-hash-do-not-leak-1234"
        u.save()
        response = staff_client.get(f"/platform/users/{u.id}/")
        body = response.content.decode()
        assert "sentinel-hash-do-not-leak-1234" not in body

    def test_detail_does_not_expose_password_hash(
        self, staff_client: Client, user_factory: Any
    ) -> None:
        u = user_factory(email="pwd-test@example.test", password="real-password-1234!")
        response = staff_client.get(f"/platform/users/{u.id}/")
        body = response.content.decode()
        # The password hash starts with the hasher prefix.
        assert "pbkdf2_sha256" not in body
        assert "argon2" not in body

    def test_detail_lists_memberships(
        self, staff_client: Client, user_factory: Any
    ) -> None:
        u = user_factory(email="multi-org@example.test")
        org_a = Organization.objects.create(
            slug="org-a", name="Org A", primary_contact_email="a@example.test"
        )
        org_b = Organization.objects.create(
            slug="org-b", name="Org B", primary_contact_email="b@example.test"
        )
        Membership.objects.create(
            user=u, organization=org_a, status=MembershipStatus.ACTIVE
        )
        Membership.objects.create(
            user=u, organization=org_b, status=MembershipStatus.INVITED
        )
        response = staff_client.get(f"/platform/users/{u.id}/")
        body = response.content.decode()
        assert "Org A" in body
        assert "Org B" in body
        assert "/platform/orgs/org-a/" in body
        assert "/platform/orgs/org-b/" in body

    def test_detail_shows_lockout_when_locked(
        self, staff_client: Client, user_factory: Any
    ) -> None:
        u = user_factory(email="locked@example.test")
        u.locked_until = timezone.now() + timezone.timedelta(hours=1)
        u.save()
        response = staff_client.get(f"/platform/users/{u.id}/")
        body = response.content.decode()
        assert "locked until" in body

    def test_detail_back_link_to_user_list(
        self, staff_client: Client, user_factory: Any
    ) -> None:
        u = user_factory(email="back-link@example.test")
        response = staff_client.get(f"/platform/users/{u.id}/")
        body = response.content.decode()
        assert "All users" in body
        assert 'href="/platform/users/"' in body
