"""Tests for impersonation integration with the handoff flow (M1 D7 Phase 5).

Covers:
* issue_handoff_token cross-field invariants.
* JWT carries `iai` claim when impersonator_admin_id is set.
* consume_handoff_token parses `iai` into HandoffResult.
* establish_tenant_session writes the session key + audit metadata.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

import jwt as jwt_lib
import pytest
from django.test import RequestFactory
from django.utils import timezone

from apps.platform.accounts.handoff.results import HandoffResult
from apps.platform.accounts.handoff.services import (
    SESSION_KEY_AUTH_METHOD,
    SESSION_KEY_IMPERSONATOR_ADMIN_ID,
    HandoffInvalidIssueParamError,
    consume_handoff_token,
    establish_tenant_session,
    issue_handoff_token,
)
from apps.platform.accounts.handoff.services._keys import (
    create_handoff_signing_key,
    promote_handoff_signing_key,
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
def signing_key_ready(system_actor_id: UUID) -> None:
    create_handoff_signing_key(actor_id=system_actor_id, key_id="hsk_p5test")
    promote_handoff_signing_key(actor_id=system_actor_id, key_id="hsk_p5test")


@pytest.fixture
def staff_admin(user_factory: Any) -> Any:
    user = user_factory(email="p5-admin@example.test")
    user.is_staff = True
    user.save()
    return user


@pytest.fixture
def target_user(user_factory: Any) -> Any:
    return user_factory(email="p5-target@example.test")


@pytest.fixture
def org_and_membership(
    target_user: Any,
) -> tuple[Organization, Membership]:
    org = Organization.objects.create(
        slug="p5org",
        name="P5 Org",
        primary_contact_email="p5@example.test",
    )
    membership = Membership.objects.create(
        user=target_user,
        organization=org,
        status=MembershipStatus.ACTIVE,
    )
    return org, membership


# ---------------------------------------------------------------------------
# issue_handoff_token cross-field validation.
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestIssueImpersonationValidation:
    def test_iai_with_password_amr_raises(
        self,
        signing_key_ready: None,
        target_user: Any,
        org_and_membership: tuple[Organization, Membership],
        staff_admin: Any,
    ) -> None:
        org, membership = org_and_membership
        with pytest.raises(HandoffInvalidIssueParamError) as exc_info:
            issue_handoff_token(
                user_id=target_user.id,
                organization_id=org.id,
                membership_id=membership.id,
                auth_method="password",
                auth_provider=None,
                mfa_satisfied_at=timezone.now(),
                impersonator_admin_id=staff_admin.id,
            )
        assert "impersonator_admin_id" in str(exc_info.value)

    def test_impersonation_amr_without_iai_raises(
        self,
        signing_key_ready: None,
        target_user: Any,
        org_and_membership: tuple[Organization, Membership],
    ) -> None:
        org, membership = org_and_membership
        with pytest.raises(HandoffInvalidIssueParamError) as exc_info:
            issue_handoff_token(
                user_id=target_user.id,
                organization_id=org.id,
                membership_id=membership.id,
                auth_method="impersonation",
                auth_provider=None,
                mfa_satisfied_at=timezone.now(),
                impersonator_admin_id=None,
            )
        assert "impersonator_admin_id" in str(exc_info.value)

    def test_impersonation_amr_with_iai_succeeds(
        self,
        signing_key_ready: None,
        target_user: Any,
        org_and_membership: tuple[Organization, Membership],
        staff_admin: Any,
    ) -> None:
        org, membership = org_and_membership
        token = issue_handoff_token(
            user_id=target_user.id,
            organization_id=org.id,
            membership_id=membership.id,
            auth_method="impersonation",
            auth_provider=None,
            mfa_satisfied_at=timezone.now(),
            impersonator_admin_id=staff_admin.id,
        )
        assert isinstance(token, str)
        # Verify the iai claim is in the payload (unverified peek is fine
        # for the test).
        payload = jwt_lib.decode(token, options={"verify_signature": False})
        assert payload["iai"] == str(staff_admin.id)
        assert payload["amr"] == "impersonation"


# ---------------------------------------------------------------------------
# JWT shape — `iai` claim absent for non-impersonation tokens.
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestJwtShape:
    def test_iai_absent_for_password_handoff(
        self,
        signing_key_ready: None,
        target_user: Any,
        org_and_membership: tuple[Organization, Membership],
    ) -> None:
        org, membership = org_and_membership
        token = issue_handoff_token(
            user_id=target_user.id,
            organization_id=org.id,
            membership_id=membership.id,
            auth_method="password",
            auth_provider=None,
            mfa_satisfied_at=timezone.now(),
        )
        payload = jwt_lib.decode(token, options={"verify_signature": False})
        assert "iai" not in payload


# ---------------------------------------------------------------------------
# Audit metadata.
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestIssueAuditMetadata:
    def test_audit_includes_impersonator_when_impersonation(
        self,
        signing_key_ready: None,
        target_user: Any,
        org_and_membership: tuple[Organization, Membership],
        staff_admin: Any,
    ) -> None:
        org, membership = org_and_membership
        issue_handoff_token(
            user_id=target_user.id,
            organization_id=org.id,
            membership_id=membership.id,
            auth_method="impersonation",
            auth_provider=None,
            mfa_satisfied_at=timezone.now(),
            impersonator_admin_id=staff_admin.id,
        )
        events = captured_audit_events(event_type="HANDOFF_TOKEN_ISSUED")
        assert len(events) >= 1
        evt = events[-1]
        assert evt.metadata is not None
        assert evt.metadata.get("impersonator_admin_id") == str(staff_admin.id)
        assert evt.metadata.get("auth_method") == "impersonation"

    def test_audit_omits_impersonator_for_non_impersonation(
        self,
        signing_key_ready: None,
        target_user: Any,
        org_and_membership: tuple[Organization, Membership],
    ) -> None:
        org, membership = org_and_membership
        issue_handoff_token(
            user_id=target_user.id,
            organization_id=org.id,
            membership_id=membership.id,
            auth_method="password",
            auth_provider=None,
            mfa_satisfied_at=timezone.now(),
        )
        events = captured_audit_events(event_type="HANDOFF_TOKEN_ISSUED")
        assert len(events) >= 1
        evt = events[-1]
        assert evt.metadata is not None
        assert "impersonator_admin_id" not in evt.metadata


# ---------------------------------------------------------------------------
# consume_handoff_token populates HandoffResult.impersonator_admin_id.
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestConsumeImpersonation:
    def test_consume_populates_impersonator_admin_id(
        self,
        signing_key_ready: None,
        target_user: Any,
        org_and_membership: tuple[Organization, Membership],
        staff_admin: Any,
        settings: Any,
    ) -> None:
        org, membership = org_and_membership
        token = issue_handoff_token(
            user_id=target_user.id,
            organization_id=org.id,
            membership_id=membership.id,
            auth_method="impersonation",
            auth_provider=None,
            mfa_satisfied_at=timezone.now(),
            impersonator_admin_id=staff_admin.id,
        )

        # Build a request hitting the tenant subdomain.
        factory = RequestFactory(HTTP_HOST=f"{org.slug}.mph.local")
        request = factory.post("/handoff/")

        result = consume_handoff_token(token=token, request=request)
        assert isinstance(result, HandoffResult)
        assert result.impersonator_admin_id == staff_admin.id
        assert result.auth_method == "impersonation"

    def test_consume_impersonator_admin_id_none_for_password_handoff(
        self,
        signing_key_ready: None,
        target_user: Any,
        org_and_membership: tuple[Organization, Membership],
    ) -> None:
        org, membership = org_and_membership
        token = issue_handoff_token(
            user_id=target_user.id,
            organization_id=org.id,
            membership_id=membership.id,
            auth_method="password",
            auth_provider=None,
            mfa_satisfied_at=timezone.now(),
        )

        factory = RequestFactory(HTTP_HOST=f"{org.slug}.mph.local")
        request = factory.post("/handoff/")

        result = consume_handoff_token(token=token, request=request)
        assert result.impersonator_admin_id is None


# ---------------------------------------------------------------------------
# establish_tenant_session writes session key + audit metadata.
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestEstablishTenantSessionImpersonation:
    def _make_request(self) -> Any:
        """Build a request with a session backend attached."""
        from django.contrib.sessions.backends.db import SessionStore

        factory = RequestFactory()
        request = factory.post("/")
        request.session = SessionStore()
        request.session.save()
        return request

    def test_session_key_written_for_impersonation(
        self,
        target_user: Any,
        org_and_membership: tuple[Organization, Membership],
        staff_admin: Any,
    ) -> None:
        org, membership = org_and_membership
        result = HandoffResult(
            user_id=target_user.id,
            organization_id=org.id,
            membership_id=membership.id,
            auth_method="impersonation",
            auth_provider=None,
            mfa_satisfied_at=timezone.now(),
            impersonator_admin_id=staff_admin.id,
        )
        request = self._make_request()
        establish_tenant_session(request=request, handoff_result=result)

        assert request.session[SESSION_KEY_IMPERSONATOR_ADMIN_ID] == str(staff_admin.id)
        assert request.session[SESSION_KEY_AUTH_METHOD] == "impersonation"

    def test_session_key_none_for_non_impersonation(
        self,
        target_user: Any,
        org_and_membership: tuple[Organization, Membership],
    ) -> None:
        org, membership = org_and_membership
        result = HandoffResult(
            user_id=target_user.id,
            organization_id=org.id,
            membership_id=membership.id,
            auth_method="password",
            auth_provider=None,
            mfa_satisfied_at=timezone.now(),
        )
        request = self._make_request()
        establish_tenant_session(request=request, handoff_result=result)

        # Key is written as None (not omitted).
        assert request.session[SESSION_KEY_IMPERSONATOR_ADMIN_ID] is None

    def test_audit_includes_impersonator_when_impersonation(
        self,
        target_user: Any,
        org_and_membership: tuple[Organization, Membership],
        staff_admin: Any,
    ) -> None:
        org, membership = org_and_membership
        result = HandoffResult(
            user_id=target_user.id,
            organization_id=org.id,
            membership_id=membership.id,
            auth_method="impersonation",
            auth_provider=None,
            mfa_satisfied_at=timezone.now(),
            impersonator_admin_id=staff_admin.id,
        )
        request = self._make_request()
        establish_tenant_session(request=request, handoff_result=result)

        events = captured_audit_events(event_type="TENANT_SESSION_ESTABLISHED")
        assert len(events) >= 1
        evt = events[-1]
        assert evt.metadata is not None
        assert evt.metadata.get("impersonator_admin_id") == str(staff_admin.id)
