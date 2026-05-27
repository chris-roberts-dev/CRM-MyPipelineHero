"""Tests for tenant-side impersonation views (M1 D7 Phase 5)."""

from __future__ import annotations

from datetime import timedelta
from typing import Any
from uuid import UUID

import pytest
from django.test import Client
from django.utils import timezone

from apps.platform.accounts.handoff.services import (
    create_handoff_signing_key,
    issue_handoff_token,
    promote_handoff_signing_key,
)
from apps.platform.accounts.impersonation.models import (
    ImpersonationEndReason,
    ImpersonationSession,
)
from apps.platform.accounts.impersonation.services import start_impersonation
from apps.platform.organizations.models import (
    Membership,
    MembershipStatus,
    Organization,
)


@pytest.fixture(autouse=True)
def _enable_host_routing(settings: Any) -> None:
    settings.MPH_HOST_URLCONF_ROUTING_ENABLED = True


@pytest.fixture
def system_actor_id(db: Any) -> UUID:
    from django.contrib.auth import get_user_model

    return get_user_model().objects.get(is_system=True).id


@pytest.fixture
def signing_key(system_actor_id: UUID) -> Any:
    create_handoff_signing_key(actor_id=system_actor_id, key_id="hsk_p5tib")
    return promote_handoff_signing_key(actor_id=system_actor_id, key_id="hsk_p5tib")


@pytest.fixture
def staff_admin(user_factory: Any) -> Any:
    """Staff admin. Doesn't hit tenant URLs directly, so no TOTP needed.

    See ``test_impersonation_liveness_middleware.py`` for the
    rationale on why ``target_user`` (below) DOES need TOTP.
    """
    user = user_factory(email="tib-admin-direct@example.test")
    user.is_staff = True
    user.save()
    return user


@pytest.fixture
def target_user(user_with_totp: Any) -> Any:
    """Target user MUST have TOTP enrolled.

    After impersonation handoff establishes the tenant session,
    ``request.user`` IS the target on subsequent tenant requests.
    ``RequireMfaEnrollmentMiddleware`` redirects users without
    TOTP to enrollment. v1 impersonation does not bypass this.
    """
    return user_with_totp


@pytest.fixture
def org_and_membership(
    target_user: Any,
) -> tuple[Organization, Membership]:
    org = Organization.objects.create(
        slug="tiborg",
        name="Tenant Imp Banner Org",
        primary_contact_email="tib@example.test",
    )
    membership = Membership.objects.create(
        user=target_user,
        organization=org,
        status=MembershipStatus.ACTIVE,
    )
    return org, membership


@pytest.fixture
def impersonation_session(
    staff_admin: Any,
    target_user: Any,
    org_and_membership: tuple[Organization, Membership],
) -> ImpersonationSession:
    org, membership = org_and_membership
    return start_impersonation(
        admin_user_id=staff_admin.id,
        target_user_id=target_user.id,
        organization_id=org.id,
        membership_id=membership.id,
        reason="tenant-side impersonation banner test",
    )


def _establish_impersonation_tenant_session(
    client: Client,
    staff_admin: Any,
    target_user: Any,
    org: Organization,
    membership: Membership,
) -> str:
    token = issue_handoff_token(
        user_id=target_user.id,
        organization_id=org.id,
        membership_id=membership.id,
        auth_method="impersonation",
        auth_provider=None,
        mfa_satisfied_at=timezone.now() - timedelta(seconds=10),
        impersonator_admin_id=staff_admin.id,
    )
    tenant_host = f"{org.slug}.mph.local"
    response = client.post("/handoff/", data={"token": token}, HTTP_HOST=tenant_host)
    assert response.status_code == 302, (
        f"Handoff consume failed: status={response.status_code}, "
        f"body={response.content[:200]!r}"
    )
    return tenant_host


def _establish_normal_tenant_session(
    client: Client,
    user: Any,
    org: Organization,
    membership: Membership,
) -> str:
    token = issue_handoff_token(
        user_id=user.id,
        organization_id=org.id,
        membership_id=membership.id,
        auth_method="password",
        auth_provider=None,
        mfa_satisfied_at=timezone.now() - timedelta(seconds=10),
    )
    tenant_host = f"{org.slug}.mph.local"
    response = client.post("/handoff/", data={"token": token}, HTTP_HOST=tenant_host)
    assert response.status_code == 302
    return tenant_host


@pytest.mark.django_db
class TestTenantLandingBanner:
    def test_banner_renders_for_impersonation_session(
        self,
        client: Client,
        signing_key: Any,
        staff_admin: Any,
        target_user: Any,
        org_and_membership: tuple[Organization, Membership],
        impersonation_session: ImpersonationSession,
    ) -> None:
        org, membership = org_and_membership
        tenant_host = _establish_impersonation_tenant_session(
            client, staff_admin, target_user, org, membership
        )
        response = client.get("/", HTTP_HOST=tenant_host)
        assert response.status_code == 200
        body = response.content.decode()
        assert "Impersonation session active" in body
        assert staff_admin.email in body
        assert "End impersonation" in body

    def test_banner_absent_for_non_impersonation_session(
        self,
        client: Client,
        signing_key: Any,
        user_with_totp: Any,
    ) -> None:
        org = Organization.objects.create(
            slug="tibnormal",
            name="Tib Normal Org",
            primary_contact_email="tibnormal@example.test",
        )
        membership = Membership.objects.create(
            user=user_with_totp,
            organization=org,
            status=MembershipStatus.ACTIVE,
        )
        tenant_host = _establish_normal_tenant_session(
            client, user_with_totp, org, membership
        )
        response = client.get("/", HTTP_HOST=tenant_host)
        assert response.status_code == 200
        body = response.content.decode()
        assert "Impersonation session active" not in body


@pytest.mark.django_db
class TestEndImpersonationFromTenantView:
    def test_post_ends_session_and_logs_out(
        self,
        client: Client,
        signing_key: Any,
        staff_admin: Any,
        target_user: Any,
        org_and_membership: tuple[Organization, Membership],
        impersonation_session: ImpersonationSession,
    ) -> None:
        org, membership = org_and_membership
        tenant_host = _establish_impersonation_tenant_session(
            client, staff_admin, target_user, org, membership
        )
        response = client.post("/end-impersonation/", HTTP_HOST=tenant_host)
        assert response.status_code == 302
        assert "/select-org/" in response["Location"]
        impersonation_session.refresh_from_db()
        assert impersonation_session.ended_at is not None

    def test_post_without_impersonation_session_redirects(
        self,
        client: Client,
        signing_key: Any,
        user_with_totp: Any,
    ) -> None:
        org = Organization.objects.create(
            slug="tibnoimp",
            name="Tib No Imp Org",
            primary_contact_email="tibnoimp@example.test",
        )
        membership = Membership.objects.create(
            user=user_with_totp,
            organization=org,
            status=MembershipStatus.ACTIVE,
        )
        tenant_host = _establish_normal_tenant_session(
            client, user_with_totp, org, membership
        )
        response = client.post("/end-impersonation/", HTTP_HOST=tenant_host)
        assert response.status_code == 302


@pytest.mark.django_db
class TestTenantLogoutEndsImpersonation:
    def test_logout_ends_impersonation_with_logout_reason(
        self,
        client: Client,
        signing_key: Any,
        staff_admin: Any,
        target_user: Any,
        org_and_membership: tuple[Organization, Membership],
        impersonation_session: ImpersonationSession,
    ) -> None:
        org, membership = org_and_membership
        tenant_host = _establish_impersonation_tenant_session(
            client, staff_admin, target_user, org, membership
        )
        response = client.post("/logout/", HTTP_HOST=tenant_host)
        assert response.status_code == 302
        impersonation_session.refresh_from_db()
        assert impersonation_session.ended_at is not None
        assert impersonation_session.end_reason == ImpersonationEndReason.LOGOUT
