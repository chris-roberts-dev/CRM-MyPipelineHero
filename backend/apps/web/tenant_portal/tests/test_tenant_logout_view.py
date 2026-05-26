"""Tests for TenantLogoutView (M1 D6 Phase 5, B.4.17)."""

from __future__ import annotations

from datetime import timedelta
from typing import Any
from uuid import UUID

import pytest
from django.contrib.sessions.backends.db import SessionStore
from django.test import Client
from django.utils import timezone

from apps.platform.accounts.handoff.services import (
    SESSION_KEY_ORGANIZATION_ID,
    create_handoff_signing_key,
    issue_handoff_token,
    promote_handoff_signing_key,
)
from apps.platform.accounts.handoff.services._redis_client import (
    get_handoff_redis_client,
)
from apps.platform.audit.services import captured_audit_events
from apps.platform.organizations.models import (
    Membership,
    MembershipStatus,
    Organization,
)


@pytest.fixture(autouse=True)
def _enable_host_routing(settings: Any) -> None:
    """Tenant logout tests exercise tenant-subdomain routing."""
    settings.MPH_HOST_URLCONF_ROUTING_ENABLED = True


@pytest.fixture
def system_actor_id(db: Any) -> UUID:
    from django.contrib.auth import get_user_model

    return get_user_model().objects.get(is_system=True).id


@pytest.fixture
def signing_key(system_actor_id: UUID) -> Any:
    create_handoff_signing_key(actor_id=system_actor_id, key_id="hsk_tlogout")
    return promote_handoff_signing_key(actor_id=system_actor_id, key_id="hsk_tlogout")


@pytest.fixture
def user_org_membership(
    user_verified_with_totp: Any,
) -> tuple[Any, Any, Any]:
    org = Organization.objects.create(
        slug="tlogout",
        name="TLogout Co",
        primary_contact_email="tl@example.test",
    )
    membership = Membership.objects.create(
        user=user_verified_with_totp,
        organization=org,
        status=MembershipStatus.ACTIVE,
    )
    return user_verified_with_totp, org, membership


def _load_session_for_host(client: Client, host: str) -> dict[str, Any]:
    """Read the session for a specific host's cookie."""
    from apps.common.sessions.host_resolution import resolve_session_scope

    scope = resolve_session_scope(host)
    cookie = client.cookies.get(scope.cookie_name)
    if cookie is None:
        return {}
    return dict(SessionStore(session_key=cookie.value).load())


@pytest.mark.django_db
class TestTenantLogoutDestroysSession:
    def test_logout_clears_tenant_session(
        self,
        client: Client,
        user_org_membership: tuple[Any, Any, Any],
        signing_key: Any,
    ) -> None:
        user, org, membership = user_org_membership
        # Establish a tenant session via handoff.
        token = issue_handoff_token(
            user_id=user.id,
            organization_id=org.id,
            membership_id=membership.id,
            auth_method="password",
            auth_provider=None,
            mfa_satisfied_at=timezone.now() - timedelta(seconds=10),
        )
        tenant_host = f"{org.slug}.mph.local"
        client.post("/handoff/", data={"token": token}, HTTP_HOST=tenant_host)

        # Confirm session has org id.
        session_before = _load_session_for_host(client, tenant_host)
        assert session_before.get(SESSION_KEY_ORGANIZATION_ID) == str(org.id)

        # Logout.
        response = client.post("/logout/", HTTP_HOST=tenant_host)
        assert response.status_code == 302
        # Redirects to root domain picker.
        assert "/select-org/" in response["Location"]

        # Session is empty now.
        session_after = _load_session_for_host(client, tenant_host)
        assert session_after.get(SESSION_KEY_ORGANIZATION_ID) is None

    def test_logout_emits_tenant_session_logout_audit(
        self,
        client: Client,
        user_org_membership: tuple[Any, Any, Any],
        signing_key: Any,
    ) -> None:
        user, org, membership = user_org_membership
        token = issue_handoff_token(
            user_id=user.id,
            organization_id=org.id,
            membership_id=membership.id,
            auth_method="password",
            auth_provider=None,
            mfa_satisfied_at=timezone.now() - timedelta(seconds=10),
        )
        tenant_host = f"{org.slug}.mph.local"
        client.post("/handoff/", data={"token": token}, HTTP_HOST=tenant_host)

        client.post("/logout/", HTTP_HOST=tenant_host)

        events = captured_audit_events(event_type="TENANT_SESSION_LOGOUT")
        assert len(events) == 1
        evt = events[0]
        assert evt.actor_id == user.id
        assert evt.organization_id == org.id

    def test_logout_does_not_revoke_handoff_tokens(
        self,
        client: Client,
        user_org_membership: tuple[Any, Any, Any],
        signing_key: Any,
    ) -> None:
        """Tenant logout MUST NOT revoke outstanding handoff tokens.

        Other tenant sessions established from the same root session
        should remain accessible.
        """
        user, org, membership = user_org_membership
        # Issue a token (Phase 5 adds it to user_handoffs index).
        # We don't consume it — we want to verify it survives logout.
        issue_handoff_token(
            user_id=user.id,
            organization_id=org.id,
            membership_id=membership.id,
            auth_method="password",
            auth_provider=None,
            mfa_satisfied_at=timezone.now() - timedelta(seconds=10),
        )

        redis_client = get_handoff_redis_client()
        before = redis_client.scard(f"user_handoffs:{user.id}")
        assert before == 1

        # Establish a session via a separate token, then logout.
        token = issue_handoff_token(
            user_id=user.id,
            organization_id=org.id,
            membership_id=membership.id,
            auth_method="password",
            auth_provider=None,
            mfa_satisfied_at=timezone.now() - timedelta(seconds=10),
        )
        tenant_host = f"{org.slug}.mph.local"
        client.post("/handoff/", data={"token": token}, HTTP_HOST=tenant_host)

        # 2 tokens issued, 1 consumed → 1 left.
        assert redis_client.scard(f"user_handoffs:{user.id}") == 1

        # Now tenant logout.
        client.post("/logout/", HTTP_HOST=tenant_host)

        # The remaining token MUST still be in the index — tenant
        # logout doesn't touch it.
        assert redis_client.scard(f"user_handoffs:{user.id}") == 1


@pytest.mark.django_db
class TestTenantLogoutEdgeCases:
    def test_logout_when_not_authenticated_redirects(self, client: Client) -> None:
        """Anonymous tenant logout request just redirects to root picker."""
        response = client.post("/logout/", HTTP_HOST="acme.mph.local")
        assert response.status_code == 302
        assert "/select-org/" in response["Location"]
