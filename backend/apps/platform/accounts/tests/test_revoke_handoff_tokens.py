"""Tests for revoke_all_handoff_tokens_for_user (M1 D6 Phase 5)."""

from __future__ import annotations

from datetime import timedelta
from typing import Any
from uuid import UUID

import pytest
from django.utils import timezone

from apps.platform.accounts.handoff.services import (
    create_handoff_signing_key,
    issue_handoff_token,
    promote_handoff_signing_key,
    revoke_all_handoff_tokens_for_user,
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
    create_handoff_signing_key(actor_id=system_actor_id, key_id="hsk_revoke")
    return promote_handoff_signing_key(actor_id=system_actor_id, key_id="hsk_revoke")


@pytest.fixture
def user_with_org(user_factory: Any) -> tuple[Any, Any, Any]:
    user = user_factory(email="revoke-test@example.test")
    org = Organization.objects.create(
        slug="revoke",
        name="Revoke Co",
        primary_contact_email="r@example.test",
    )
    membership = Membership.objects.create(
        user=user,
        organization=org,
        status=MembershipStatus.ACTIVE,
    )
    return user, org, membership


@pytest.mark.django_db
class TestRevokeWithNoTokens:
    def test_no_outstanding_tokens_returns_zero(
        self, user_with_org: tuple[Any, Any, Any]
    ) -> None:
        user, _, _ = user_with_org
        count = revoke_all_handoff_tokens_for_user(user_id=user.id)
        assert count == 0

    def test_no_outstanding_tokens_no_audit_event(
        self, user_with_org: tuple[Any, Any, Any]
    ) -> None:
        user, _, _ = user_with_org
        revoke_all_handoff_tokens_for_user(user_id=user.id)
        events = captured_audit_events(event_type="HANDOFF_TOKENS_REVOKED_BY_LOGOUT")
        assert len(events) == 0


@pytest.mark.django_db
class TestRevokeWithOneToken:
    def test_outstanding_token_is_revoked(
        self,
        user_with_org: tuple[Any, Any, Any],
        signing_key: Any,
    ) -> None:
        user, org, membership = user_with_org
        # Issue a token — populates the user_handoffs index.
        issue_handoff_token(
            user_id=user.id,
            organization_id=org.id,
            membership_id=membership.id,
            auth_method="password",
            auth_provider=None,
            mfa_satisfied_at=timezone.now() - timedelta(seconds=10),
        )

        # Confirm the index exists before revocation.
        client = get_handoff_redis_client()
        index_key = f"user_handoffs:{user.id}"
        assert client.scard(index_key) == 1

        count = revoke_all_handoff_tokens_for_user(user_id=user.id)
        assert count == 1

        # Index is gone.
        assert client.scard(index_key) == 0

    def test_outstanding_token_emits_audit_event(
        self,
        user_with_org: tuple[Any, Any, Any],
        signing_key: Any,
    ) -> None:
        user, org, membership = user_with_org
        issue_handoff_token(
            user_id=user.id,
            organization_id=org.id,
            membership_id=membership.id,
            auth_method="password",
            auth_provider=None,
            mfa_satisfied_at=timezone.now() - timedelta(seconds=10),
        )

        revoke_all_handoff_tokens_for_user(user_id=user.id)

        events = captured_audit_events(event_type="HANDOFF_TOKENS_REVOKED_BY_LOGOUT")
        assert len(events) == 1
        evt = events[0]
        assert evt.actor_id == user.id
        assert evt.metadata is not None
        assert evt.metadata["tokens_in_index"] == 1
        assert evt.metadata["tokens_deleted"] == 1


@pytest.mark.django_db
class TestRevokeWithMultipleTokens:
    def test_multiple_outstanding_tokens_all_revoked(
        self,
        user_with_org: tuple[Any, Any, Any],
        signing_key: Any,
    ) -> None:
        user, org, membership = user_with_org
        # Issue three tokens.
        for _ in range(3):
            issue_handoff_token(
                user_id=user.id,
                organization_id=org.id,
                membership_id=membership.id,
                auth_method="password",
                auth_provider=None,
                mfa_satisfied_at=timezone.now() - timedelta(seconds=10),
            )

        client = get_handoff_redis_client()
        assert client.scard(f"user_handoffs:{user.id}") == 3

        count = revoke_all_handoff_tokens_for_user(user_id=user.id)
        assert count == 3
        assert client.scard(f"user_handoffs:{user.id}") == 0

    def test_revoked_token_cannot_be_consumed(
        self,
        user_with_org: tuple[Any, Any, Any],
        signing_key: Any,
    ) -> None:
        """End-to-end: issue, revoke, attempted consume returns
        not_found_or_replayed."""
        from django.test import RequestFactory

        from apps.platform.accounts.handoff.services import (
            HandoffInvalidError,
            consume_handoff_token,
        )

        user, org, membership = user_with_org
        token = issue_handoff_token(
            user_id=user.id,
            organization_id=org.id,
            membership_id=membership.id,
            auth_method="password",
            auth_provider=None,
            mfa_satisfied_at=timezone.now() - timedelta(seconds=10),
        )

        revoke_all_handoff_tokens_for_user(user_id=user.id)

        factory = RequestFactory()
        request = factory.post(
            "/handoff/",
            HTTP_HOST=f"{org.slug}.mph.local",
        )
        with pytest.raises(HandoffInvalidError) as exc:
            consume_handoff_token(token=token, request=request)
        assert exc.value.reason == "not_found_or_replayed"


@pytest.mark.django_db
class TestSecondaryIndexCleanupOnConsume:
    def test_consume_removes_token_from_index(
        self,
        user_with_org: tuple[Any, Any, Any],
        signing_key: Any,
    ) -> None:
        """After successful consume, the token id is removed from
        the user_handoffs index (Phase 5 best-effort cleanup)."""
        from django.test import RequestFactory

        from apps.platform.accounts.handoff.services import (
            consume_handoff_token,
        )

        user, org, membership = user_with_org
        token = issue_handoff_token(
            user_id=user.id,
            organization_id=org.id,
            membership_id=membership.id,
            auth_method="password",
            auth_provider=None,
            mfa_satisfied_at=timezone.now() - timedelta(seconds=10),
        )

        client = get_handoff_redis_client()
        assert client.scard(f"user_handoffs:{user.id}") == 1

        factory = RequestFactory()
        request = factory.post(
            "/handoff/",
            HTTP_HOST=f"{org.slug}.mph.local",
        )
        consume_handoff_token(token=token, request=request)

        # After consume, the index should be empty (cleaned up).
        assert client.scard(f"user_handoffs:{user.id}") == 0
