"""End-to-end multi-host integration tests (M1 D6 Phase 6, J.3.9 #13-#16).

These tests simulate the full root→tenant→logout flow as a browser
would experience it:

1. POST credentials to allauth login on root domain.
2. Complete MFA (TOTP authenticator pre-installed in fixtures).
3. Hit /select-org/ on root domain.
4. Auto-advance (one membership) or pick (multi-membership).
5. POST the issued JWT to the tenant subdomain's /handoff/.
6. Land on the tenant home with the B.4.14 session keys populated.
7. Tenant or root logout, depending on the test scenario.

Cookie semantics matter at every hop: the client carries one cookie
per host. Phase 3's PerTenantSessionMiddleware writes
``mph_root_session`` on root domain and ``tenant_session_{slug}`` on
tenant subdomains. ``client.session`` is host-blind (reads
``settings.SESSION_COOKIE_NAME``); we read host-scoped sessions via
the ``_load_session_for_host`` helper.

The MFA flow is bypassed for ergonomics: we pre-install a TOTP
authenticator on the user fixture and write the
``mph_mfa_satisfied_at`` session key directly. This decouples the
integration tests from allauth's MFA enrollment UI, which is exercised
in ``test_mfa_end_to_end.py``.
"""

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
    promote_handoff_signing_key,
)
from apps.platform.accounts.handoff.services._redis_client import (
    get_handoff_redis_client,
)
from apps.platform.accounts.signals_mfa import SESSION_KEY_MFA_SATISFIED_AT
from apps.platform.audit.services import captured_audit_events
from apps.platform.organizations.models import (
    Membership,
    MembershipStatus,
    Organization,
)

# ---------------------------------------------------------------------------
# Test setup.
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _enable_host_routing(settings: Any) -> None:
    """All integration tests exercise per-host URL routing."""
    settings.MPH_HOST_URLCONF_ROUTING_ENABLED = True


@pytest.fixture
def system_actor_id(db: Any) -> UUID:
    from django.contrib.auth import get_user_model

    return get_user_model().objects.get(is_system=True).id


@pytest.fixture
def signing_key(system_actor_id: UUID) -> Any:
    create_handoff_signing_key(actor_id=system_actor_id, key_id="hsk_integration")
    return promote_handoff_signing_key(
        actor_id=system_actor_id, key_id="hsk_integration"
    )


@pytest.fixture
def org_acme(db: Any) -> Organization:
    return Organization.objects.create(
        slug="acme",
        name="Acme Inc",
        primary_contact_email="contact@acme.test",
    )


@pytest.fixture
def org_globex(db: Any) -> Organization:
    return Organization.objects.create(
        slug="globex",
        name="Globex Corp",
        primary_contact_email="contact@globex.test",
    )


def _load_session_for_host(client: Client, host: str) -> dict[str, Any]:
    """Read the session for a specific host's cookie name."""
    from apps.common.sessions.host_resolution import resolve_session_scope

    scope = resolve_session_scope(host)
    cookie = client.cookies.get(scope.cookie_name)
    if cookie is None:
        return {}
    return dict(SessionStore(session_key=cookie.value).load())


def _login_user_with_mfa(client: Client, user: Any) -> None:
    """Establish a logged-in root session with MFA satisfaction marker.

    Skips the password POST + TOTP challenge UI (those flows are covered
    in test_mfa_end_to_end.py). We force_login + write the MFA marker
    directly, replicating the state the user would be in immediately
    after completing both steps via the UI.
    """
    client.force_login(user)
    session = client.session
    session[SESSION_KEY_MFA_SATISFIED_AT] = (
        timezone.now() - timedelta(seconds=5)
    ).isoformat()
    session.save()


def _follow_handoff_form(
    client: Client,
    issue_response_body: bytes,
    tenant_host: str,
) -> Any:
    """Parse the auto-POST form from the issue response and submit it."""
    import re

    body = issue_response_body.decode()

    # Extract action URL.
    action_match = re.search(r'action="([^"]+)"', body)
    assert action_match, "Issue response missing form action"
    action_url = action_match.group(1)
    assert (
        tenant_host in action_url
    ), f"Form action {action_url!r} doesn't target tenant host {tenant_host!r}"

    # Extract token.
    token_match = re.search(
        r'<input\s+type="hidden"\s+name="token"\s+value="([^"]+)"', body
    )
    assert token_match, "Issue response missing token hidden field"
    token = token_match.group(1)

    # POST to the tenant.
    return client.post("/handoff/", data={"token": token}, HTTP_HOST=tenant_host)


# ---------------------------------------------------------------------------
# J.3.9 #13 — single-membership user auto-advances.
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestSingleMembershipEndToEnd:
    """User with one membership goes from picker straight to tenant."""

    def test_full_flow_root_to_tenant(
        self,
        client: Client,
        user_verified_with_totp: Any,
        org_acme: Organization,
        signing_key: Any,
    ) -> None:
        Membership.objects.create(
            user=user_verified_with_totp,
            organization=org_acme,
            status=MembershipStatus.ACTIVE,
        )

        # Step 1: log in (sim'd) on root.
        _login_user_with_mfa(client, user_verified_with_totp)

        # Step 2: hit /select-org/ — auto-advances + renders handoff form.
        select_response = client.get("/select-org/")
        assert select_response.status_code == 200
        # Single-membership branch renders the auto-POST form directly.
        assert b"acme.mph.local/handoff/" in select_response.content

        # Step 3: simulate browser auto-POSTing to tenant.
        tenant_host = "acme.mph.local"
        consume_response = _follow_handoff_form(
            client, select_response.content, tenant_host
        )

        # Consume returns 302 to / on tenant.
        assert consume_response.status_code == 302
        assert consume_response["Location"] == "/"

        # Step 4: GET tenant landing.
        landing_response = client.get("/", HTTP_HOST=tenant_host)
        assert landing_response.status_code == 200
        assert b"Acme Inc" in landing_response.content

        # Step 5: verify tenant session populated with B.4.14 keys.
        tenant_session = _load_session_for_host(client, tenant_host)
        assert tenant_session.get(SESSION_KEY_ORGANIZATION_ID) == str(org_acme.id)

    def test_audit_trail_complete(
        self,
        client: Client,
        user_verified_with_totp: Any,
        org_acme: Organization,
        signing_key: Any,
    ) -> None:
        """The full flow emits MEMBERSHIP_SELECTED, HANDOFF_TOKEN_ISSUED,
        HANDOFF_TOKEN_CONSUMED, TENANT_SESSION_ESTABLISHED in order."""
        Membership.objects.create(
            user=user_verified_with_totp,
            organization=org_acme,
            status=MembershipStatus.ACTIVE,
        )

        _login_user_with_mfa(client, user_verified_with_totp)
        select_response = client.get("/select-org/")
        _follow_handoff_form(client, select_response.content, "acme.mph.local")

        # All four audit events present.
        events_by_type = {
            "MEMBERSHIP_SELECTED": captured_audit_events(
                event_type="MEMBERSHIP_SELECTED"
            ),
            "HANDOFF_TOKEN_ISSUED": captured_audit_events(
                event_type="HANDOFF_TOKEN_ISSUED"
            ),
            "HANDOFF_TOKEN_CONSUMED": captured_audit_events(
                event_type="HANDOFF_TOKEN_CONSUMED"
            ),
            "TENANT_SESSION_ESTABLISHED": captured_audit_events(
                event_type="TENANT_SESSION_ESTABLISHED"
            ),
        }
        for event_type, events in events_by_type.items():
            assert len(events) >= 1, (
                f"Expected at least one {event_type} audit event; " f"got {len(events)}"
            )


# ---------------------------------------------------------------------------
# J.3.9 #14 — multi-membership user explicitly picks one.
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestMultiMembershipEndToEnd:
    """User with multiple memberships sees picker, chooses one, lands on tenant."""

    def test_picker_then_explicit_handoff(
        self,
        client: Client,
        user_verified_with_totp: Any,
        org_acme: Organization,
        org_globex: Organization,
        signing_key: Any,
    ) -> None:
        m_acme = Membership.objects.create(
            user=user_verified_with_totp,
            organization=org_acme,
            status=MembershipStatus.ACTIVE,
        )
        Membership.objects.create(
            user=user_verified_with_totp,
            organization=org_globex,
            status=MembershipStatus.ACTIVE,
        )

        _login_user_with_mfa(client, user_verified_with_totp)

        # Picker renders both orgs.
        picker_response = client.get("/select-org/")
        assert picker_response.status_code == 200
        assert b"Acme Inc" in picker_response.content
        assert b"Globex Corp" in picker_response.content

        # User explicitly picks Acme.
        issue_response = client.post(
            "/handoff/issue/",
            data={"membership_id": str(m_acme.id)},
        )
        assert issue_response.status_code == 200

        # Browser auto-POSTs to Acme tenant.
        tenant_host = "acme.mph.local"
        consume_response = _follow_handoff_form(
            client, issue_response.content, tenant_host
        )
        assert consume_response.status_code == 302

        # Tenant landing renders with Acme's identity.
        landing_response = client.get("/", HTTP_HOST=tenant_host)
        assert landing_response.status_code == 200
        assert b"Acme Inc" in landing_response.content


# ---------------------------------------------------------------------------
# J.3.9 #15 — handoff host mismatch.
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestHostMismatchRejection:
    """Token issued for Acme is rejected if posted to Globex's subdomain."""

    def test_token_for_acme_posted_to_globex_rejected(
        self,
        client: Client,
        user_verified_with_totp: Any,
        org_acme: Organization,
        org_globex: Organization,
        signing_key: Any,
    ) -> None:
        """A handoff token bound to Acme MUST fail when consumed on
        Globex's subdomain, even if the user has a valid Globex
        membership. B.4.12 host-binding check."""
        Membership.objects.create(
            user=user_verified_with_totp,
            organization=org_acme,
            status=MembershipStatus.ACTIVE,
        )
        Membership.objects.create(
            user=user_verified_with_totp,
            organization=org_globex,
            status=MembershipStatus.ACTIVE,
        )

        _login_user_with_mfa(client, user_verified_with_totp)

        # Issue a token for Acme membership.
        m_acme = Membership.objects.get(
            user=user_verified_with_totp, organization=org_acme
        )
        issue_response = client.post(
            "/handoff/issue/",
            data={"membership_id": str(m_acme.id)},
        )
        assert issue_response.status_code == 200

        # Extract the token and POST to GLOBEX's subdomain instead of Acme's.
        import re

        token_match = re.search(
            rb'<input\s+type="hidden"\s+name="token"\s+value="([^"]+)"',
            issue_response.content,
        )
        assert token_match
        token = token_match.group(1).decode()

        # Now misroute to globex.
        consume_response = client.post(
            "/handoff/",
            data={"token": token},
            HTTP_HOST="globex.mph.local",
        )

        # Consume rejects → handoff_failed page.
        assert consume_response.status_code == 400
        assert b"Sign-in failed" in consume_response.content

        # Audit recorded the host mismatch.
        host_mismatch_events = captured_audit_events(event_type="HANDOFF_HOST_MISMATCH")
        assert len(host_mismatch_events) == 1
        evt = host_mismatch_events[0]
        assert evt.metadata is not None
        assert evt.metadata["reason"] == "host_mismatch"
        assert evt.metadata["expected_host"] == "acme.mph.local"
        assert evt.metadata["actual_host"] == "globex.mph.local"

        # Tenant session was NOT established on globex.
        tenant_session = _load_session_for_host(client, "globex.mph.local")
        assert tenant_session.get(SESSION_KEY_ORGANIZATION_ID) is None


# ---------------------------------------------------------------------------
# J.3.9 #16 — logout semantics across hosts.
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestLogoutFlowEndToEnd:
    """Logout from one host doesn't unintentionally kill the other."""

    def test_tenant_logout_preserves_root_session(
        self,
        client: Client,
        user_verified_with_totp: Any,
        org_acme: Organization,
        signing_key: Any,
    ) -> None:
        """After tenant logout, the user can return to root /select-org/
        and pick another org without re-authenticating."""
        Membership.objects.create(
            user=user_verified_with_totp,
            organization=org_acme,
            status=MembershipStatus.ACTIVE,
        )

        _login_user_with_mfa(client, user_verified_with_totp)
        select_response = client.get("/select-org/")
        tenant_host = "acme.mph.local"
        _follow_handoff_form(client, select_response.content, tenant_host)

        # Confirm tenant session exists.
        before = _load_session_for_host(client, tenant_host)
        assert before.get(SESSION_KEY_ORGANIZATION_ID) == str(org_acme.id)

        # Tenant logout.
        logout_response = client.post("/logout/", HTTP_HOST=tenant_host)
        assert logout_response.status_code == 302
        # Redirects to root domain picker.
        assert "/select-org/" in logout_response["Location"]

        # Tenant session is gone.
        after = _load_session_for_host(client, tenant_host)
        assert after.get(SESSION_KEY_ORGANIZATION_ID) is None

        # Root session is INTACT — user can still pick.
        root_response = client.get("/select-org/")
        assert root_response.status_code == 200
        # Single-membership branch auto-advances again (form rendered).
        assert b"acme.mph.local/handoff/" in root_response.content

    def test_root_logout_kills_handoff_tokens(
        self,
        client: Client,
        user_verified_with_totp: Any,
        org_acme: Organization,
        signing_key: Any,
    ) -> None:
        """Root logout revokes all outstanding handoff tokens."""
        m_acme = Membership.objects.create(
            user=user_verified_with_totp,
            organization=org_acme,
            status=MembershipStatus.ACTIVE,
        )

        _login_user_with_mfa(client, user_verified_with_totp)

        # Issue a token but DON'T consume it (leave it outstanding).
        client.post(
            "/handoff/issue/",
            data={"membership_id": str(m_acme.id)},
        )

        redis_client = get_handoff_redis_client()
        assert redis_client.scard(f"user_handoffs:{user_verified_with_totp.id}") == 1

        # Root logout (via allauth).
        client.post("/accounts/logout/")

        # Outstanding token is gone.
        assert redis_client.scard(f"user_handoffs:{user_verified_with_totp.id}") == 0

        # Audit event recorded.
        events = captured_audit_events(event_type="HANDOFF_TOKENS_REVOKED_BY_LOGOUT")
        assert len(events) >= 1

    def test_root_logout_emits_root_session_logout(
        self,
        client: Client,
        user_verified_with_totp: Any,
        org_acme: Organization,
        signing_key: Any,
    ) -> None:
        """Root logout always emits ROOT_SESSION_LOGOUT."""
        Membership.objects.create(
            user=user_verified_with_totp,
            organization=org_acme,
            status=MembershipStatus.ACTIVE,
        )
        _login_user_with_mfa(client, user_verified_with_totp)

        client.post("/accounts/logout/")

        events = captured_audit_events(event_type="ROOT_SESSION_LOGOUT")
        assert len(events) >= 1
        # Most recent event has our user.
        assert any(evt.actor_id == user_verified_with_totp.id for evt in events)
