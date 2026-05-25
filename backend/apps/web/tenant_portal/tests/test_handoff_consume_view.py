"""Tests for HandoffConsumeView + TenantLandingView (M1 D6 Phase 4B)."""

from __future__ import annotations

from datetime import timedelta
from typing import Any
from uuid import UUID

import pytest
from django.contrib.sessions.backends.db import SessionStore
from django.test import Client
from django.utils import timezone

from apps.platform.accounts.handoff.services import (
    SESSION_KEY_MEMBERSHIP_ID,
    SESSION_KEY_ORGANIZATION_ID,
    create_handoff_signing_key,
    issue_handoff_token,
    promote_handoff_signing_key,
)
from apps.platform.organizations.models import (
    Membership,
    MembershipStatus,
    Organization,
)


@pytest.fixture(autouse=True)
def _enable_host_routing(settings: Any) -> None:
    """These tests exercise tenant-subdomain routing."""
    settings.MPH_HOST_URLCONF_ROUTING_ENABLED = True


@pytest.fixture
def system_actor_id(db: Any) -> UUID:
    from django.contrib.auth import get_user_model

    return get_user_model().objects.get(is_system=True).id


@pytest.fixture
def signing_key(system_actor_id: UUID) -> Any:
    create_handoff_signing_key(actor_id=system_actor_id, key_id="hsk_consume_view")
    return promote_handoff_signing_key(
        actor_id=system_actor_id, key_id="hsk_consume_view"
    )


@pytest.fixture
def user_org_membership(
    user_verified_with_totp: Any,
) -> tuple[Any, Any, Any]:
    org = Organization.objects.create(
        slug="consume",
        name="Consume Co",
        primary_contact_email="c@example.test",
    )
    membership = Membership.objects.create(
        user=user_verified_with_totp,
        organization=org,
        status=MembershipStatus.ACTIVE,
    )
    return user_verified_with_totp, org, membership


def _load_session_for_host(client: Client, host: str) -> dict[str, Any]:
    """Read the session for a specific host's cookie.

    Django's ``client.session`` is host-blind — it always reads the
    cookie named ``settings.SESSION_COOKIE_NAME``. Our
    ``PerTenantSessionMiddleware`` writes the cookie under a host-
    derived name (``tenant_session_{slug}`` on tenant subdomains).
    This helper resolves the right cookie name and loads the
    session row from the DB backend.
    """
    from apps.common.sessions.host_resolution import (
        resolve_session_scope,
    )

    scope = resolve_session_scope(host)
    cookie = client.cookies.get(scope.cookie_name)
    if cookie is None:
        return {}
    return dict(SessionStore(session_key=cookie.value).load())


@pytest.mark.django_db
class TestHandoffConsumeView:
    def test_valid_token_establishes_session_and_redirects_to_root(
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
        response = client.post(
            "/handoff/",
            data={"token": token},
            HTTP_HOST=tenant_host,
        )

        assert response.status_code == 302
        assert response["Location"] == "/"

        # Session has the B.4.14 keys — read by tenant cookie name,
        # NOT by client.session (which is host-blind).
        session_data = _load_session_for_host(client, tenant_host)
        assert session_data.get(SESSION_KEY_ORGANIZATION_ID) == str(org.id)
        assert session_data.get(SESSION_KEY_MEMBERSHIP_ID) == str(membership.id)

    def test_invalid_token_renders_failure_page(
        self,
        client: Client,
        user_org_membership: tuple[Any, Any, Any],
        signing_key: Any,
    ) -> None:
        user, org, _ = user_org_membership
        response = client.post(
            "/handoff/",
            data={"token": "obviously.not.a.valid.token"},
            HTTP_HOST=f"{org.slug}.mph.local",
        )
        assert response.status_code == 400
        assert b"Sign-in failed" in response.content

    def test_missing_token_returns_400(
        self,
        client: Client,
        user_org_membership: tuple[Any, Any, Any],
    ) -> None:
        _, org, _ = user_org_membership
        response = client.post(
            "/handoff/",
            data={},
            HTTP_HOST=f"{org.slug}.mph.local",
        )
        assert response.status_code == 400


@pytest.mark.django_db
class TestTenantLandingView:
    def test_landing_page_renders_for_established_session(
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
        # Consume first to establish session.
        client.post(
            "/handoff/",
            data={"token": token},
            HTTP_HOST=tenant_host,
        )
        # Now hit the landing.
        response = client.get("/", HTTP_HOST=tenant_host)
        assert response.status_code == 200
        assert org.name.encode() in response.content
