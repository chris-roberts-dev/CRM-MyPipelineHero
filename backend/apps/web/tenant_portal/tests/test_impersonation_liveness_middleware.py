"""Tests for EnforceImpersonationLiveness middleware (M1 D7 Phase 5)."""

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
from apps.platform.accounts.impersonation.services import (
    end_impersonation,
    start_impersonation,
)
from apps.platform.organizations.models import (
    Membership,
    MembershipStatus,
    Organization,
)


@pytest.fixture(autouse=True)
def _enable_host_routing(settings: Any) -> None:
    """Tenant tests exercise tenant-subdomain routing."""
    settings.MPH_HOST_URLCONF_ROUTING_ENABLED = True


@pytest.fixture
def system_actor_id(db: Any) -> UUID:
    from django.contrib.auth import get_user_model

    return get_user_model().objects.get(is_system=True).id


@pytest.fixture
def signing_key(system_actor_id: UUID) -> Any:
    create_handoff_signing_key(actor_id=system_actor_id, key_id="hsk_p5midware")
    return promote_handoff_signing_key(actor_id=system_actor_id, key_id="hsk_p5midware")


@pytest.fixture
def staff_admin(user_factory: Any) -> Any:
    """Staff admin user. Admin never makes tenant requests directly,
    so they don't need TOTP — the RequireMfaEnrollmentMiddleware
    only fires on requests where ``request.user`` is the actor on
    the request path, and admin actions happen via root domain.
    """
    user = user_factory(email="mid-admin-direct@example.test")
    user.is_staff = True
    user.save()
    return user


@pytest.fixture
def target_user(user_with_totp: Any) -> Any:
    """Target user MUST have TOTP enrolled.

    Why: once impersonation establishes the tenant session,
    ``request.user`` on subsequent tenant requests IS the target.
    ``RequireMfaEnrollmentMiddleware`` fires on those requests and
    redirects users without TOTP to enrollment. v1 impersonation
    does NOT bypass this check — admin's MFA gates the START of
    impersonation, but the middleware enforces the target's own
    MFA state on every subsequent tenant request.

    Real-world impact: impersonating a no-TOTP user lands them on
    the enrollment page rather than the tenant. Tracked as a v1
    UX limitation in the M1 D7 retro.
    """
    return user_with_totp


@pytest.fixture
def org_and_membership(
    target_user: Any,
) -> tuple[Organization, Membership]:
    org = Organization.objects.create(
        slug="midorg",
        name="Mid Org",
        primary_contact_email="mid@example.test",
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
        reason="middleware test - impersonation session",
    )


def _establish_impersonation_tenant_session(
    client: Client,
    staff_admin: Any,
    target_user: Any,
    org: Organization,
    membership: Membership,
) -> str:
    """Mint an impersonation handoff token and consume it on the
    tenant subdomain so the tenant session cookie is set under the
    right name.

    Returns the tenant host for follow-up requests.
    """
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


@pytest.mark.django_db
class TestEnforceImpersonationLiveness:
    def test_passes_when_impersonation_session_active(
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

    def test_force_logout_when_session_ended(
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
        end_impersonation(
            session_id=impersonation_session.id,
            ended_by_user_id=staff_admin.id,
            end_reason=ImpersonationEndReason.ADMIN_ENDED,
        )
        response = client.get("/", HTTP_HOST=tenant_host)
        assert response.status_code == 302
        assert "/select-org/" in response["Location"]

    def test_noop_for_non_impersonation_session(
        self,
        client: Client,
        signing_key: Any,
        user_with_totp: Any,
    ) -> None:
        """A normal (non-impersonation) tenant session passes the
        middleware untouched."""
        org = Organization.objects.create(
            slug="midnormal",
            name="Mid Normal Org",
            primary_contact_email="midnormal@example.test",
        )
        membership = Membership.objects.create(
            user=user_with_totp,
            organization=org,
            status=MembershipStatus.ACTIVE,
        )
        token = issue_handoff_token(
            user_id=user_with_totp.id,
            organization_id=org.id,
            membership_id=membership.id,
            auth_method="password",
            auth_provider=None,
            mfa_satisfied_at=timezone.now() - timedelta(seconds=10),
        )
        tenant_host = f"{org.slug}.mph.local"
        consume_response = client.post(
            "/handoff/", data={"token": token}, HTTP_HOST=tenant_host
        )
        assert consume_response.status_code == 302

        response = client.get("/", HTTP_HOST=tenant_host)
        assert response.status_code == 200

    def test_noop_for_anonymous_request(
        self,
        client: Client,
        org_and_membership: tuple[Organization, Membership],
    ) -> None:
        """Anonymous tenant requests pass through middleware; the
        TenantLandingView's own redirect handles the no-session case."""
        org, _ = org_and_membership
        response = client.get("/", HTTP_HOST=f"{org.slug}.mph.local")
        assert response.status_code == 302
        assert "/select-org/" in response["Location"]
