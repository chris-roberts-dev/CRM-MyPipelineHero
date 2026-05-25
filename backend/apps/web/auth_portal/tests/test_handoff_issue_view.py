"""Tests for HandoffIssueView (M1 D6 Phase 4B)."""

from __future__ import annotations

from datetime import timedelta
from typing import Any
from uuid import UUID

import pytest
from django.test import Client
from django.utils import timezone

from apps.platform.accounts.handoff.services import (
    create_handoff_signing_key,
    promote_handoff_signing_key,
)
from apps.platform.accounts.signals_mfa import SESSION_KEY_MFA_SATISFIED_AT
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
def primary_signing_key(system_actor_id: UUID) -> Any:
    create_handoff_signing_key(actor_id=system_actor_id, key_id="hsk_issue_view")
    return promote_handoff_signing_key(
        actor_id=system_actor_id, key_id="hsk_issue_view"
    )


@pytest.fixture
def user_with_org(
    user_verified_with_totp: Any,
) -> tuple[Any, Any, Any]:
    org = Organization.objects.create(
        slug="issueview",
        name="IssueView Co",
        primary_contact_email="iv@example.test",
    )
    membership = Membership.objects.create(
        user=user_verified_with_totp,
        organization=org,
        status=MembershipStatus.ACTIVE,
    )
    return user_verified_with_totp, org, membership


def _login_with_mfa(client: Client, user: Any) -> None:
    client.force_login(user)
    session = client.session
    session[SESSION_KEY_MFA_SATISFIED_AT] = (
        timezone.now() - timedelta(seconds=10)
    ).isoformat()
    session.save()


@pytest.mark.django_db
class TestHandoffIssueView:
    def test_post_with_valid_membership_id_renders_form(
        self,
        client: Client,
        user_with_org: tuple[Any, Any, Any],
        primary_signing_key: Any,
    ) -> None:
        user, org, membership = user_with_org
        _login_with_mfa(client, user)
        response = client.post(
            "/handoff/issue/",
            data={"membership_id": str(membership.id)},
        )
        assert response.status_code == 200
        assert b"issueview.mph.local/handoff/" in response.content
        # Token in hidden field.
        assert b'name="token"' in response.content

    def test_post_with_missing_membership_id_returns_400(
        self, client: Client, user_verified_with_totp: Any
    ) -> None:
        _login_with_mfa(client, user_verified_with_totp)
        response = client.post("/handoff/issue/", data={})
        assert response.status_code == 400

    def test_post_with_invalid_uuid_returns_400(
        self, client: Client, user_verified_with_totp: Any
    ) -> None:
        _login_with_mfa(client, user_verified_with_totp)
        response = client.post("/handoff/issue/", data={"membership_id": "not-a-uuid"})
        assert response.status_code == 400

    def test_post_with_other_users_membership_returns_404(
        self,
        client: Client,
        user_with_org: tuple[Any, Any, Any],
        primary_signing_key: Any,
        user_factory: Any,
    ) -> None:
        user, org, _ = user_with_org
        other_user = user_factory(email="other@example.test")
        other_membership = Membership.objects.create(
            user=other_user,
            organization=org,
            status=MembershipStatus.ACTIVE,
        )

        _login_with_mfa(client, user)
        response = client.post(
            "/handoff/issue/",
            data={"membership_id": str(other_membership.id)},
        )
        # 404, not 403 — don't leak existence of other users' memberships.
        assert response.status_code == 404
