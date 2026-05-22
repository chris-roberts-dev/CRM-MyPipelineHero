"""Tests for issue/consume handoff-token services (M1 D6 Phase 2)."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

import jwt
import pytest
from django.contrib.auth import get_user_model
from django.test import RequestFactory
from django.utils import timezone

from apps.platform.accounts.handoff.results import HandoffResult
from apps.platform.accounts.handoff.services import (
    HandoffInvalidError,
    HandoffInvalidIssueParamError,
    NoActiveHandoffSigningKeyError,
    consume_handoff_token,
    create_handoff_signing_key,
    issue_handoff_token,
    promote_handoff_signing_key,
)
from apps.platform.accounts.handoff.services._redis_client import (
    get_handoff_redis_client,
)
from apps.platform.audit.services import captured_audit_events

# ---------------------------------------------------------------------------
# Fixtures.
# ---------------------------------------------------------------------------


@pytest.fixture
def system_actor_id(db: Any) -> UUID:
    UserModel = get_user_model()
    return UserModel.objects.get(is_system=True).id


@pytest.fixture
def primary_key(system_actor_id: UUID) -> Any:
    """Active, promoted primary HandoffSigningKey."""
    create_handoff_signing_key(actor_id=system_actor_id, key_id="hsk_phase2_primary")
    return promote_handoff_signing_key(
        actor_id=system_actor_id, key_id="hsk_phase2_primary"
    )


@pytest.fixture
def org_and_membership(db: Any, user_factory: Any) -> tuple[Any, Any, Any]:
    """A user with an ACTIVE membership in an organization."""
    from apps.platform.organizations.models import (
        Membership,
        MembershipStatus,
        Organization,
    )

    user = user_factory(email="handoff-user@example.test")
    org = Organization.objects.create(
        slug="acme",
        name="Acme Corp",
        primary_contact_email="contact@acme.test",
    )
    membership = Membership.objects.create(
        user=user,
        organization=org,
        status=MembershipStatus.ACTIVE,
    )
    return user, org, membership


@pytest.fixture
def tenant_request_for_acme() -> Any:
    """An HttpRequest with host matching the 'acme' tenant slug."""
    factory = RequestFactory()
    request = factory.post(
        "/handoff/",
        HTTP_HOST="acme.mph.local",
    )
    return request


# ---------------------------------------------------------------------------
# issue_handoff_token — happy path.
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestIssueHappyPath:
    def test_returns_signed_jwt(
        self, primary_key: Any, org_and_membership: tuple[Any, Any, Any]
    ) -> None:
        user, org, membership = org_and_membership
        token = issue_handoff_token(
            user_id=user.id,
            organization_id=org.id,
            membership_id=membership.id,
            auth_method="password",
            auth_provider=None,
            mfa_satisfied_at=timezone.now() - timedelta(seconds=10),
        )
        assert isinstance(token, str)
        # JWT format: three base64 segments separated by dots.
        assert token.count(".") == 2

    def test_payload_contains_required_claims(
        self, primary_key: Any, org_and_membership: tuple[Any, Any, Any]
    ) -> None:
        user, org, membership = org_and_membership
        mfa_at = timezone.now() - timedelta(seconds=30)
        token = issue_handoff_token(
            user_id=user.id,
            organization_id=org.id,
            membership_id=membership.id,
            auth_method="oidc",
            auth_provider="okta",
            mfa_satisfied_at=mfa_at,
        )
        # Decode WITHOUT verification to inspect claims.
        unverified = jwt.decode(token, options={"verify_signature": False})
        assert unverified["uid"] == str(user.id)
        assert unverified["oid"] == str(org.id)
        assert unverified["mid"] == str(membership.id)
        assert unverified["amr"] == "oidc"
        assert unverified["apr"] == "okta"
        assert "tid" in unverified
        assert len(unverified["tid"]) >= 40  # 32-byte token_urlsafe = ~43 chars
        assert "iat" in unverified
        assert "exp" in unverified
        # 60-second TTL.
        assert unverified["exp"] - unverified["iat"] == 60

    def test_header_contains_kid(
        self, primary_key: Any, org_and_membership: tuple[Any, Any, Any]
    ) -> None:
        user, org, membership = org_and_membership
        token = issue_handoff_token(
            user_id=user.id,
            organization_id=org.id,
            membership_id=membership.id,
            auth_method="password",
            auth_provider=None,
            mfa_satisfied_at=timezone.now() - timedelta(seconds=10),
        )
        headers = jwt.get_unverified_header(token)
        assert headers["kid"] == "hsk_phase2_primary"
        assert headers["alg"] == "HS256"

    def test_writes_redis_nonce(
        self, primary_key: Any, org_and_membership: tuple[Any, Any, Any]
    ) -> None:
        user, org, membership = org_and_membership
        token = issue_handoff_token(
            user_id=user.id,
            organization_id=org.id,
            membership_id=membership.id,
            auth_method="password",
            auth_provider=None,
            mfa_satisfied_at=timezone.now() - timedelta(seconds=10),
        )
        unverified = jwt.decode(token, options={"verify_signature": False})
        tid = unverified["tid"]
        client = get_handoff_redis_client()
        raw = client.get(f"handoff:{tid}")
        assert raw is not None

    def test_emits_token_issued_audit_event(
        self, primary_key: Any, org_and_membership: tuple[Any, Any, Any]
    ) -> None:
        user, org, membership = org_and_membership
        issue_handoff_token(
            user_id=user.id,
            organization_id=org.id,
            membership_id=membership.id,
            auth_method="password",
            auth_provider=None,
            mfa_satisfied_at=timezone.now() - timedelta(seconds=10),
        )
        events = captured_audit_events(event_type="HANDOFF_TOKEN_ISSUED")
        assert len(events) == 1
        evt = events[0]
        assert evt.actor_id == user.id
        assert evt.organization_id == org.id
        assert evt.metadata is not None
        assert evt.metadata["key_id"] == "hsk_phase2_primary"
        assert evt.metadata["auth_method"] == "password"
        assert evt.metadata["ttl_seconds"] == 60


# ---------------------------------------------------------------------------
# issue_handoff_token — validation.
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestIssueValidation:
    def test_rejects_unknown_auth_method(
        self, primary_key: Any, org_and_membership: tuple[Any, Any, Any]
    ) -> None:
        user, org, membership = org_and_membership
        with pytest.raises(HandoffInvalidIssueParamError, match="auth_method"):
            issue_handoff_token(
                user_id=user.id,
                organization_id=org.id,
                membership_id=membership.id,
                auth_method="magic_link",  # not in allowed set
                auth_provider=None,
                mfa_satisfied_at=timezone.now() - timedelta(seconds=10),
            )

    def test_rejects_naive_mfa_satisfied_at(
        self, primary_key: Any, org_and_membership: tuple[Any, Any, Any]
    ) -> None:
        user, org, membership = org_and_membership
        naive_dt = datetime.now()  # no tzinfo
        with pytest.raises(HandoffInvalidIssueParamError, match="timezone-aware"):
            issue_handoff_token(
                user_id=user.id,
                organization_id=org.id,
                membership_id=membership.id,
                auth_method="password",
                auth_provider=None,
                mfa_satisfied_at=naive_dt,
            )

    def test_rejects_future_mfa_satisfied_at(
        self, primary_key: Any, org_and_membership: tuple[Any, Any, Any]
    ) -> None:
        user, org, membership = org_and_membership
        with pytest.raises(HandoffInvalidIssueParamError, match="future"):
            issue_handoff_token(
                user_id=user.id,
                organization_id=org.id,
                membership_id=membership.id,
                auth_method="password",
                auth_provider=None,
                mfa_satisfied_at=timezone.now() + timedelta(hours=1),
            )

    def test_rejects_stale_mfa_satisfied_at(
        self, primary_key: Any, org_and_membership: tuple[Any, Any, Any]
    ) -> None:
        user, org, membership = org_and_membership
        with pytest.raises(HandoffInvalidIssueParamError, match="more than"):
            issue_handoff_token(
                user_id=user.id,
                organization_id=org.id,
                membership_id=membership.id,
                auth_method="password",
                auth_provider=None,
                mfa_satisfied_at=timezone.now() - timedelta(days=1),
            )

    def test_rejects_nonexistent_membership(
        self, primary_key: Any, org_and_membership: tuple[Any, Any, Any]
    ) -> None:
        user, org, _ = org_and_membership
        with pytest.raises(HandoffInvalidIssueParamError, match="does not exist"):
            issue_handoff_token(
                user_id=user.id,
                organization_id=org.id,
                membership_id=uuid4(),
                auth_method="password",
                auth_provider=None,
                mfa_satisfied_at=timezone.now() - timedelta(seconds=10),
            )

    def test_rejects_inactive_membership(
        self, primary_key: Any, org_and_membership: tuple[Any, Any, Any]
    ) -> None:
        from apps.platform.organizations.models import MembershipStatus

        user, org, membership = org_and_membership
        membership.status = MembershipStatus.SUSPENDED
        membership.save()
        with pytest.raises(HandoffInvalidIssueParamError, match="ACTIVE"):
            issue_handoff_token(
                user_id=user.id,
                organization_id=org.id,
                membership_id=membership.id,
                auth_method="password",
                auth_provider=None,
                mfa_satisfied_at=timezone.now() - timedelta(seconds=10),
            )


@pytest.mark.django_db
class TestIssueNoActiveKey:
    def test_raises_when_no_signing_keys(
        self, org_and_membership: tuple[Any, Any, Any]
    ) -> None:
        # No primary_key fixture used — no signing key exists.
        user, org, membership = org_and_membership
        with pytest.raises(NoActiveHandoffSigningKeyError):
            issue_handoff_token(
                user_id=user.id,
                organization_id=org.id,
                membership_id=membership.id,
                auth_method="password",
                auth_provider=None,
                mfa_satisfied_at=timezone.now() - timedelta(seconds=10),
            )


# ---------------------------------------------------------------------------
# consume_handoff_token — happy path.
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestConsumeHappyPath:
    def test_round_trip_returns_handoff_result(
        self,
        primary_key: Any,
        org_and_membership: tuple[Any, Any, Any],
        tenant_request_for_acme: Any,
    ) -> None:
        user, org, membership = org_and_membership
        mfa_at = timezone.now() - timedelta(seconds=20)
        token = issue_handoff_token(
            user_id=user.id,
            organization_id=org.id,
            membership_id=membership.id,
            auth_method="oidc",
            auth_provider="okta",
            mfa_satisfied_at=mfa_at,
        )

        result = consume_handoff_token(token=token, request=tenant_request_for_acme)

        assert isinstance(result, HandoffResult)
        assert result.user_id == user.id
        assert result.organization_id == org.id
        assert result.membership_id == membership.id
        assert result.auth_method == "oidc"
        assert result.auth_provider == "okta"
        # mfa_satisfied_at survived the JSON serialization round-trip.
        assert abs((result.mfa_satisfied_at - mfa_at).total_seconds()) < 1

    def test_emits_token_consumed_audit(
        self,
        primary_key: Any,
        org_and_membership: tuple[Any, Any, Any],
        tenant_request_for_acme: Any,
    ) -> None:
        user, org, membership = org_and_membership
        token = issue_handoff_token(
            user_id=user.id,
            organization_id=org.id,
            membership_id=membership.id,
            auth_method="password",
            auth_provider=None,
            mfa_satisfied_at=timezone.now() - timedelta(seconds=10),
        )
        consume_handoff_token(token=token, request=tenant_request_for_acme)

        events = captured_audit_events(event_type="HANDOFF_TOKEN_CONSUMED")
        assert len(events) == 1
        evt = events[0]
        assert evt.metadata is not None
        assert evt.metadata["outcome"] == "success"
        assert evt.metadata["key_id_used"] == "hsk_phase2_primary"


# ---------------------------------------------------------------------------
# consume_handoff_token — failure modes.
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestConsumeReplayProtection:
    def test_second_consume_raises_replay(
        self,
        primary_key: Any,
        org_and_membership: tuple[Any, Any, Any],
        tenant_request_for_acme: Any,
    ) -> None:
        user, org, membership = org_and_membership
        token = issue_handoff_token(
            user_id=user.id,
            organization_id=org.id,
            membership_id=membership.id,
            auth_method="password",
            auth_provider=None,
            mfa_satisfied_at=timezone.now() - timedelta(seconds=10),
        )
        # First consume succeeds.
        consume_handoff_token(token=token, request=tenant_request_for_acme)
        # Second consume fails with replay.
        with pytest.raises(HandoffInvalidError) as exc:
            consume_handoff_token(token=token, request=tenant_request_for_acme)
        assert exc.value.reason == "not_found_or_replayed"

        replay_events = captured_audit_events(event_type="HANDOFF_REPLAY_DETECTED")
        assert len(replay_events) == 1


@pytest.mark.django_db
class TestConsumeExpiry:
    def test_expired_token_raises(
        self,
        primary_key: Any,
        org_and_membership: tuple[Any, Any, Any],
        tenant_request_for_acme: Any,
        settings: Any,
    ) -> None:
        # Use a 1-second TTL so we don't have to wait.
        settings.MPH_HANDOFF_TOKEN_TTL_SECONDS = 1

        user, org, membership = org_and_membership
        # Issue with TTL=1.
        token = issue_handoff_token(
            user_id=user.id,
            organization_id=org.id,
            membership_id=membership.id,
            auth_method="password",
            auth_provider=None,
            mfa_satisfied_at=timezone.now() - timedelta(seconds=10),
        )

        # Wait for expiry.
        import time as _time

        _time.sleep(1.5)

        with pytest.raises(HandoffInvalidError) as exc:
            consume_handoff_token(token=token, request=tenant_request_for_acme)
        assert exc.value.reason == "expired"


@pytest.mark.django_db
class TestConsumeHostBinding:
    def test_wrong_host_raises_host_mismatch(
        self,
        primary_key: Any,
        org_and_membership: tuple[Any, Any, Any],
    ) -> None:
        user, org, membership = org_and_membership
        token = issue_handoff_token(
            user_id=user.id,
            organization_id=org.id,
            membership_id=membership.id,
            auth_method="password",
            auth_provider=None,
            mfa_satisfied_at=timezone.now() - timedelta(seconds=10),
        )

        # Wrong host — request is for "other-org.mph.local" but token's
        # org is "acme".
        factory = RequestFactory()
        wrong_request = factory.post("/handoff/", HTTP_HOST="other-org.mph.local")

        with pytest.raises(HandoffInvalidError) as exc:
            consume_handoff_token(token=token, request=wrong_request)
        assert exc.value.reason == "host_mismatch"

        # And the host-mismatch audit event fired.
        events = captured_audit_events(event_type="HANDOFF_HOST_MISMATCH")
        assert len(events) == 1
        assert events[0].metadata is not None
        assert events[0].metadata["reason"] == "host_mismatch"
        assert events[0].metadata["expected_host"] == "acme.mph.local"
        assert events[0].metadata["actual_host"] == "other-org.mph.local"


@pytest.mark.django_db
class TestConsumeMembershipCheck:
    def test_membership_deactivated_after_issue_raises(
        self,
        primary_key: Any,
        org_and_membership: tuple[Any, Any, Any],
        tenant_request_for_acme: Any,
    ) -> None:
        from apps.platform.organizations.models import MembershipStatus

        user, org, membership = org_and_membership
        token = issue_handoff_token(
            user_id=user.id,
            organization_id=org.id,
            membership_id=membership.id,
            auth_method="password",
            auth_provider=None,
            mfa_satisfied_at=timezone.now() - timedelta(seconds=10),
        )

        # Deactivate the membership AFTER issuing the token.
        membership.status = MembershipStatus.SUSPENDED
        membership.save()

        with pytest.raises(HandoffInvalidError) as exc:
            consume_handoff_token(token=token, request=tenant_request_for_acme)
        assert exc.value.reason == "membership_inactive"


@pytest.mark.django_db
class TestConsumeSignatureFailure:
    def test_tampered_signature_raises(
        self,
        primary_key: Any,
        org_and_membership: tuple[Any, Any, Any],
        tenant_request_for_acme: Any,
    ) -> None:
        user, org, membership = org_and_membership
        token = issue_handoff_token(
            user_id=user.id,
            organization_id=org.id,
            membership_id=membership.id,
            auth_method="password",
            auth_provider=None,
            mfa_satisfied_at=timezone.now() - timedelta(seconds=10),
        )
        # Flip a character in the signature segment (last segment).
        head, payload_seg, sig = token.split(".")
        tampered_sig = "A" + sig[1:] if sig[0] != "A" else "B" + sig[1:]
        tampered = f"{head}.{payload_seg}.{tampered_sig}"

        with pytest.raises(HandoffInvalidError) as exc:
            consume_handoff_token(token=tampered, request=tenant_request_for_acme)
        assert exc.value.reason == "invalid_signature"

    def test_malformed_token_raises(
        self,
        primary_key: Any,
        org_and_membership: tuple[Any, Any, Any],
        tenant_request_for_acme: Any,
    ) -> None:
        with pytest.raises(HandoffInvalidError) as exc:
            consume_handoff_token(
                token="not.a.valid.jwt.shape",
                request=tenant_request_for_acme,
            )
        # Could be "invalid" or "invalid_signature" depending on which
        # step fails first.
        assert exc.value.reason in {"invalid", "invalid_signature"}


# ---------------------------------------------------------------------------
# consume_handoff_token — rotation overlap.
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestConsumeWithRetiredKey:
    def test_verifies_with_old_key_and_emits_retired_key_audit(
        self,
        primary_key: Any,
        org_and_membership: tuple[Any, Any, Any],
        tenant_request_for_acme: Any,
        system_actor_id: UUID,
    ) -> None:
        """Token issued with key A; rotation adds key B as primary;
        token still verifies with A but emits the audit event."""
        user, org, membership = org_and_membership

        # primary_key is "hsk_phase2_primary" (A). Issue with A.
        token = issue_handoff_token(
            user_id=user.id,
            organization_id=org.id,
            membership_id=membership.id,
            auth_method="password",
            auth_provider=None,
            mfa_satisfied_at=timezone.now() - timedelta(seconds=10),
        )

        # Now add key B as a newer key — B becomes the primary by
        # virtue of newer created_at.
        create_handoff_signing_key(actor_id=system_actor_id, key_id="hsk_new_primary")
        promote_handoff_signing_key(actor_id=system_actor_id, key_id="hsk_new_primary")

        # Consume the A-signed token. It must verify with A, not B.
        result = consume_handoff_token(token=token, request=tenant_request_for_acme)
        assert result.user_id == user.id

        # And the audit event for non-primary verification fired.
        events = captured_audit_events(event_type="HANDOFF_VERIFIED_WITH_RETIRED_KEY")
        assert len(events) == 1
        evt = events[0]
        assert evt.metadata is not None
        assert evt.metadata["used_key_id"] == "hsk_phase2_primary"
        assert evt.metadata["current_primary_key_id"] == "hsk_new_primary"
