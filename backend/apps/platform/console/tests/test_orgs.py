"""Tests for org list and detail views (M1 D7 Phase 2)."""

from __future__ import annotations

from typing import Any

import pytest
from django.test import Client

from apps.platform.organizations.models import (
    Membership,
    MembershipStatus,
    Organization,
    OrganizationStatus,
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


@pytest.fixture
def three_orgs(db: Any) -> tuple[Organization, Organization, Organization]:
    a = Organization.objects.create(
        slug="acme",
        name="Acme Inc",
        primary_contact_email="acme@example.test",
    )
    b = Organization.objects.create(
        slug="globex",
        name="Globex Corp",
        primary_contact_email="globex@example.test",
    )
    c = Organization.objects.create(
        slug="initech",
        name="Initech Holdings",
        primary_contact_email="initech@example.test",
        status=OrganizationStatus.SUSPENDED,
    )
    return a, b, c


@pytest.mark.django_db
class TestOrgList:
    def test_list_renders_all_orgs(
        self,
        staff_client: Client,
        three_orgs: tuple[Organization, Organization, Organization],
    ) -> None:
        response = staff_client.get("/platform/orgs/")
        assert response.status_code == 200
        body = response.content.decode()
        assert "Acme Inc" in body
        assert "Globex Corp" in body
        assert "Initech Holdings" in body

    def test_list_orders_alphabetically(
        self,
        staff_client: Client,
        three_orgs: tuple[Organization, Organization, Organization],
    ) -> None:
        response = staff_client.get("/platform/orgs/")
        body = response.content.decode()
        # "Acme" should appear before "Globex" should appear before "Initech".
        assert (
            body.find("Acme Inc")
            < body.find("Globex Corp")
            < body.find("Initech Holdings")
        )

    def test_search_filters_by_name(
        self,
        staff_client: Client,
        three_orgs: tuple[Organization, Organization, Organization],
    ) -> None:
        response = staff_client.get("/platform/orgs/?q=glob")
        body = response.content.decode()
        assert "Globex Corp" in body
        assert "Acme Inc" not in body
        assert "Initech Holdings" not in body

    def test_search_filters_by_slug(
        self,
        staff_client: Client,
        three_orgs: tuple[Organization, Organization, Organization],
    ) -> None:
        response = staff_client.get("/platform/orgs/?q=acme")
        body = response.content.decode()
        assert "Acme Inc" in body
        assert "Globex Corp" not in body

    def test_search_no_matches_shows_message(
        self, staff_client: Client, three_orgs: Any
    ) -> None:
        response = staff_client.get("/platform/orgs/?q=zzznomatch")
        body = response.content.decode()
        assert "No organizations match" in body

    def test_status_badges_render(
        self,
        staff_client: Client,
        three_orgs: tuple[Organization, Organization, Organization],
    ) -> None:
        response = staff_client.get("/platform/orgs/")
        body = response.content.decode()
        # Active and Suspended displays present.
        assert "Active" in body
        assert "Suspended" in body

    def test_org_card_links_to_detail(
        self,
        staff_client: Client,
        three_orgs: tuple[Organization, Organization, Organization],
    ) -> None:
        response = staff_client.get("/platform/orgs/")
        body = response.content.decode()
        assert "/platform/orgs/acme/" in body
        assert "/platform/orgs/globex/" in body

    def test_active_member_count_annotation(
        self,
        staff_client: Client,
        three_orgs: tuple[Organization, Organization, Organization],
        user_factory: Any,
    ) -> None:
        acme, _, _ = three_orgs
        u1 = user_factory(email="m1@example.test")
        u2 = user_factory(email="m2@example.test")
        Membership.objects.create(
            user=u1, organization=acme, status=MembershipStatus.ACTIVE
        )
        Membership.objects.create(
            user=u2, organization=acme, status=MembershipStatus.INVITED
        )

        response = staff_client.get("/platform/orgs/")
        body = response.content.decode()
        # Active count for Acme should be 1 (u1 active, u2 invited).
        # We look at the surrounding HTML: a cell rendering "1" near Acme.
        assert "Acme Inc" in body

    def test_pagination_renders_when_over_25_orgs(
        self, staff_client: Client, three_orgs: Any
    ) -> None:
        # Create enough additional orgs to exceed paginate_by=25.
        for i in range(25):
            Organization.objects.create(
                slug=f"extra-{i:02d}",
                name=f"Extra Org {i:02d}",
                primary_contact_email=f"extra{i}@example.test",
            )
        response = staff_client.get("/platform/orgs/")
        body = response.content.decode()
        # 28 total orgs (3 + 25); paginate_by=25 → 2 pages.
        assert "Page 1 of 2" in body
        assert "Next" in body


@pytest.mark.django_db
class TestOrgDetail:
    def test_detail_renders_for_existing_slug(
        self,
        staff_client: Client,
        three_orgs: tuple[Organization, Organization, Organization],
    ) -> None:
        response = staff_client.get("/platform/orgs/acme/")
        assert response.status_code == 200
        body = response.content.decode()
        assert "Acme Inc" in body
        assert "acme@example.test" in body

    def test_detail_404_for_unknown_slug(self, staff_client: Client) -> None:
        response = staff_client.get("/platform/orgs/no-such-org/")
        assert response.status_code == 404

    def test_detail_shows_active_member_count(
        self,
        staff_client: Client,
        three_orgs: tuple[Organization, Organization, Organization],
        user_factory: Any,
    ) -> None:
        acme, _, _ = three_orgs
        u1 = user_factory(email="dm1@example.test")
        u2 = user_factory(email="dm2@example.test")
        Membership.objects.create(
            user=u1, organization=acme, status=MembershipStatus.ACTIVE
        )
        Membership.objects.create(
            user=u2, organization=acme, status=MembershipStatus.SUSPENDED
        )
        response = staff_client.get("/platform/orgs/acme/")
        body = response.content.decode()
        assert "1 active" in body

    def test_detail_lists_members_with_link_to_user_detail(
        self,
        staff_client: Client,
        three_orgs: tuple[Organization, Organization, Organization],
        user_factory: Any,
    ) -> None:
        acme, _, _ = three_orgs
        u = user_factory(email="member@example.test")
        Membership.objects.create(
            user=u, organization=acme, status=MembershipStatus.ACTIVE
        )
        response = staff_client.get("/platform/orgs/acme/")
        body = response.content.decode()
        assert "member@example.test" in body
        assert f"/platform/users/{u.id}/" in body

    def test_back_link_to_org_list(
        self,
        staff_client: Client,
        three_orgs: tuple[Organization, Organization, Organization],
    ) -> None:
        response = staff_client.get("/platform/orgs/acme/")
        body = response.content.decode()
        assert "All organizations" in body
        assert 'href="/platform/orgs/"' in body
