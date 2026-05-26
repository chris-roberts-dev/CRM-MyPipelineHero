"""Tests for the user_logged_out signal handler (M1 D6 Phase 5)."""

from __future__ import annotations

from datetime import timedelta
from typing import Any
from uuid import UUID

import pytest
from allauth.account.signals import user_logged_out
from django.test import RequestFactory
from django.utils import timezone

from apps.platform.accounts.handoff.services import (
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


@pytest.fixture
def system_actor_id(db: Any) -> UUID:
    from django.contrib.auth import get_user_model

    return get_user_model().objects.get(is_system=True).id


@pytest.fixture
def signing_key(system_actor_id: UUID) -> Any:
    create_handoff_signing_key(actor_id=system_actor_id, key_id="hsk_signal_logout")
    return promote_handoff_signing_key(
        actor_id=system_actor_id, key_id="hsk_signal_logout"
    )


@pytest.fixture
def user_with_token(
    user_factory: Any,
    signing_key: Any,
) -> tuple[Any, Any]:
    user = user_factory(email="logout-signal@example.test")
    org = Organization.objects.create(
        slug="logoutsig",
        name="Logout Sig Co",
        primary_contact_email="ls@example.test",
    )
    membership = Membership.objects.create(
        user=user,
        organization=org,
        status=MembershipStatus.ACTIVE,
    )
    issue_handoff_token(
        user_id=user.id,
        organization_id=org.id,
        membership_id=membership.id,
        auth_method="password",
        auth_provider=None,
        mfa_satisfied_at=timezone.now() - timedelta(seconds=10),
    )
    return user, org


@pytest.mark.django_db
class TestRootDomainLogoutRevokesTokens:
    def test_root_logout_signal_revokes_tokens(
        self, user_with_token: tuple[Any, Any]
    ) -> None:
        user, _ = user_with_token
        factory = RequestFactory()
        request = factory.post("/accounts/logout/", HTTP_HOST="mph.local")

        client = get_handoff_redis_client()
        assert client.scard(f"user_handoffs:{user.id}") == 1

        user_logged_out.send(sender=None, request=request, user=user)

        # Tokens were revoked.
        assert client.scard(f"user_handoffs:{user.id}") == 0

    def test_root_logout_emits_root_session_logout_audit(
        self, user_with_token: tuple[Any, Any]
    ) -> None:
        user, _ = user_with_token
        factory = RequestFactory()
        request = factory.post("/accounts/logout/", HTTP_HOST="mph.local")

        user_logged_out.send(sender=None, request=request, user=user)

        events = captured_audit_events(event_type="ROOT_SESSION_LOGOUT")
        assert len(events) >= 1
        evt = events[-1]
        assert evt.actor_id == user.id
        assert evt.metadata is not None
        assert evt.metadata["host"] == "mph.local"
        assert evt.metadata["tokens_revoked"] == 1


@pytest.mark.django_db
class TestTenantHostLogoutDoesNotRevoke:
    def test_tenant_logout_signal_does_not_revoke_tokens(
        self, user_with_token: tuple[Any, Any]
    ) -> None:
        user, org = user_with_token
        factory = RequestFactory()
        request = factory.post("/logout/", HTTP_HOST=f"{org.slug}.mph.local")

        client = get_handoff_redis_client()
        assert client.scard(f"user_handoffs:{user.id}") == 1

        user_logged_out.send(sender=None, request=request, user=user)

        # Tokens are still there — tenant logout shouldn't revoke.
        assert client.scard(f"user_handoffs:{user.id}") == 1

    def test_tenant_logout_signal_no_root_session_logout_audit(
        self, user_with_token: tuple[Any, Any]
    ) -> None:
        user, org = user_with_token
        factory = RequestFactory()
        request = factory.post("/logout/", HTTP_HOST=f"{org.slug}.mph.local")

        user_logged_out.send(sender=None, request=request, user=user)

        # No ROOT_SESSION_LOGOUT events because handler skipped.
        events = captured_audit_events(event_type="ROOT_SESSION_LOGOUT")
        assert len(events) == 0


@pytest.mark.django_db
class TestSignalDefensiveBehavior:
    def test_no_user_does_not_crash(self) -> None:
        factory = RequestFactory()
        request = factory.post("/accounts/logout/", HTTP_HOST="mph.local")
        # Should silently no-op.
        user_logged_out.send(sender=None, request=request, user=None)

    def test_no_request_does_not_crash(self, user_factory: Any) -> None:
        user = user_factory(email="no-req@example.test")
        # Should silently no-op.
        user_logged_out.send(sender=None, request=None, user=user)
