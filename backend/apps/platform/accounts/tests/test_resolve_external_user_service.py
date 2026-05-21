"""Tests for resolve_external_user (M1 D5 Phase 2, B.4.6 / B.4.7).

Covers J.3.6 #1, #3, #4 and J.3.5 #3, #4, #5 at the service level.
The end-to-end HTTP flow lands in Phase 6.

J.3.5 #3 — OAuth/OIDC login with linked external identity:
  → test_subject_id_lookup_returns_linked_user

J.3.5 #4 — OAuth/OIDC login with verified email linking to existing
            invited user:
  → test_verified_email_links_to_existing_user

J.3.5 #5 — OAuth/OIDC login rejected for unverified email when
            verification is required:
  → test_unverified_email_rejected_when_required

J.3.6 #1 — provider subject ID maps to existing external identity:
  → test_subject_id_lookup_returns_linked_user

J.3.6 #3 — unverified email cannot link to existing user:
  → test_unverified_email_does_not_link_to_existing_user

J.3.6 #4 — conflicting external identity blocks login:
  → test_conflicting_external_identity_blocks_link
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

import pytest
from allauth.socialaccount.models import SocialAccount
from django.contrib.auth import get_user_model

from apps.platform.accounts.oauth import (
    ExternalIdentityClaims,
    OAuthProviderConfig,
    ProviderType,
)
from apps.platform.accounts.services import (
    ConflictingExternalIdentityError,
    EmailDomainNotAllowedError,
    EmailNotVerifiedError,
    NoExistingUserAndSelfRegistrationDisabledError,
    ProviderNotActiveError,
    UserInactiveError,
    resolve_external_user,
)
from apps.platform.audit.services import captured_audit_events

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def system_actor_id(db: Any) -> UUID:
    """The System User id — the canonical actor for OAuth resolution."""
    User = get_user_model()
    return User.objects.get(is_system=True).id


@pytest.fixture
def oidc_provider(db: Any) -> OAuthProviderConfig:
    """A standard, active OIDC provider with strict verification."""
    return OAuthProviderConfig.objects.create(
        provider_code="test-oidc",
        display_name="Test OIDC",
        provider_type=ProviderType.OIDC,
        issuer_url="https://issuer.example.test",
        client_id_env_key="OAUTH_TEST_OIDC_CLIENT_ID",
        client_secret_env_key="OAUTH_TEST_OIDC_CLIENT_SECRET",
        is_active=True,
        require_verified_email=True,
        trust_external_mfa=False,
        allow_self_registration=False,
    )


@pytest.fixture
def oidc_provider_with_self_registration(db: Any) -> OAuthProviderConfig:
    """Like ``oidc_provider`` but with self-registration enabled."""
    return OAuthProviderConfig.objects.create(
        provider_code="test-oidc-selfreg",
        display_name="Test OIDC Self-Reg",
        provider_type=ProviderType.OIDC,
        issuer_url="https://issuer.example.test",
        client_id_env_key="OAUTH_TEST_OIDC_SELFREG_CLIENT_ID",
        client_secret_env_key="OAUTH_TEST_OIDC_SELFREG_CLIENT_SECRET",
        is_active=True,
        require_verified_email=True,
        trust_external_mfa=False,
        allow_self_registration=True,
    )


def _claims(
    *,
    provider_code: str = "test-oidc",
    provider_uid: str = "subject-12345",
    email: str | None = "alice@example.test",
    email_verified: bool = True,
    display_name: str | None = "Alice Example",
) -> ExternalIdentityClaims:
    """Construct a claims fixture inline (small enough not to need a factory)."""
    return ExternalIdentityClaims(
        provider_code=provider_code,
        provider_uid=provider_uid,
        email=email,
        email_verified=email_verified,
        display_name=display_name,
    )


# ---------------------------------------------------------------------------
# Step 1 / 2 / 3: input-validation rejections.
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestProviderActiveCheck:
    def test_inactive_provider_rejected(
        self, oidc_provider: OAuthProviderConfig, system_actor_id: UUID
    ) -> None:
        oidc_provider.is_active = False
        oidc_provider.save()

        with pytest.raises(ProviderNotActiveError) as exc:
            resolve_external_user(
                claims=_claims(),
                provider_config=oidc_provider,
                actor_id=system_actor_id,
            )
        assert exc.value.provider_code == "test-oidc"


@pytest.mark.django_db
class TestEmailDomainAllowlist:
    def test_email_domain_not_in_allowlist_rejected(
        self, oidc_provider: OAuthProviderConfig, system_actor_id: UUID
    ) -> None:
        oidc_provider.allowed_email_domains = ["allowed.test", "also-allowed.test"]
        oidc_provider.save()

        with pytest.raises(EmailDomainNotAllowedError) as exc:
            resolve_external_user(
                claims=_claims(email="alice@blocked.test"),
                provider_config=oidc_provider,
                actor_id=system_actor_id,
            )
        assert exc.value.email == "alice@blocked.test"
        assert exc.value.allowed_domains == ["allowed.test", "also-allowed.test"]

    def test_email_domain_in_allowlist_proceeds(
        self,
        oidc_provider_with_self_registration: OAuthProviderConfig,
        system_actor_id: UUID,
    ) -> None:
        oidc_provider_with_self_registration.allowed_email_domains = ["example.test"]
        oidc_provider_with_self_registration.save()

        user = resolve_external_user(
            claims=_claims(
                provider_code="test-oidc-selfreg",
                email="alice@example.test",
            ),
            provider_config=oidc_provider_with_self_registration,
            actor_id=system_actor_id,
        )
        assert user.email == "alice@example.test"

    def test_allowlist_check_case_insensitive(
        self,
        oidc_provider_with_self_registration: OAuthProviderConfig,
        system_actor_id: UUID,
    ) -> None:
        oidc_provider_with_self_registration.allowed_email_domains = ["EXAMPLE.test"]
        oidc_provider_with_self_registration.save()

        # claims email is already lowercased; the allowlist contains
        # uppercase. The check must succeed.
        user = resolve_external_user(
            claims=_claims(
                provider_code="test-oidc-selfreg",
                email="alice@example.test",
            ),
            provider_config=oidc_provider_with_self_registration,
            actor_id=system_actor_id,
        )
        assert user is not None

    def test_empty_allowlist_means_any_domain_allowed(
        self,
        oidc_provider_with_self_registration: OAuthProviderConfig,
        system_actor_id: UUID,
    ) -> None:
        # allowed_email_domains is None/empty → any verified email passes.
        oidc_provider_with_self_registration.allowed_email_domains = None
        oidc_provider_with_self_registration.save()

        user = resolve_external_user(
            claims=_claims(
                provider_code="test-oidc-selfreg",
                email="alice@anything.test",
            ),
            provider_config=oidc_provider_with_self_registration,
            actor_id=system_actor_id,
        )
        assert user.email == "alice@anything.test"


@pytest.mark.django_db
class TestEmailVerificationRequirement:
    """J.3.5 #5 + J.3.6 #3: unverified email rejected when required."""

    def test_unverified_email_rejected_when_required(
        self, oidc_provider: OAuthProviderConfig, system_actor_id: UUID
    ) -> None:
        with pytest.raises(EmailNotVerifiedError) as exc:
            resolve_external_user(
                claims=_claims(email_verified=False),
                provider_config=oidc_provider,
                actor_id=system_actor_id,
            )
        assert exc.value.provider_code == "test-oidc"

    def test_unverified_email_does_not_link_to_existing_user(
        self, oidc_provider: OAuthProviderConfig, system_actor_id: UUID, db: Any
    ) -> None:
        """J.3.6 #3: even if email matches an existing user, unverified
        email MUST NOT silently link."""
        User = get_user_model()
        User.objects.create_user(
            email="alice@example.test", password="strong-password-12345!"
        )

        with pytest.raises(EmailNotVerifiedError):
            resolve_external_user(
                claims=_claims(email_verified=False),
                provider_config=oidc_provider,
                actor_id=system_actor_id,
            )

        # And no SocialAccount was created.
        assert not SocialAccount.objects.filter(
            provider="test-oidc", uid="subject-12345"
        ).exists()


# ---------------------------------------------------------------------------
# Step 4: subject-ID lookup. (J.3.6 #1 / J.3.5 #3)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestSubjectIdLookup:
    """J.3.6 #1 + J.3.5 #3: subject ID maps to linked external identity."""

    def test_subject_id_lookup_returns_linked_user(
        self,
        oidc_provider: OAuthProviderConfig,
        system_actor_id: UUID,
        user_factory: Any,
    ) -> None:
        existing_user = user_factory(email="alice@example.test")
        SocialAccount.objects.create(
            user=existing_user,
            provider="test-oidc",
            uid="subject-12345",
            extra_data={},
        )

        resolved = resolve_external_user(
            claims=_claims(),
            provider_config=oidc_provider,
            actor_id=system_actor_id,
        )
        assert resolved.id == existing_user.id

    def test_subject_id_lookup_inactive_user_rejected(
        self,
        oidc_provider: OAuthProviderConfig,
        system_actor_id: UUID,
        user_factory: Any,
    ) -> None:
        user = user_factory(email="alice@example.test")
        user.is_active = False
        user.save()
        SocialAccount.objects.create(
            user=user,
            provider="test-oidc",
            uid="subject-12345",
            extra_data={},
        )

        with pytest.raises(UserInactiveError) as exc:
            resolve_external_user(
                claims=_claims(),
                provider_config=oidc_provider,
                actor_id=system_actor_id,
            )
        assert exc.value.user_id == user.id

    def test_subject_id_lookup_no_audit_event_emitted_on_return(
        self,
        oidc_provider: OAuthProviderConfig,
        system_actor_id: UUID,
        user_factory: Any,
    ) -> None:
        """No new linking happened — no OAUTH_ACCOUNT_LINKED audit event."""
        existing_user = user_factory(email="alice@example.test")
        SocialAccount.objects.create(
            user=existing_user,
            provider="test-oidc",
            uid="subject-12345",
            extra_data={},
        )

        resolve_external_user(
            claims=_claims(),
            provider_config=oidc_provider,
            actor_id=system_actor_id,
        )
        # The user was already linked; resolving them again is not a
        # *new* link, so OAUTH_ACCOUNT_LINKED MUST NOT fire.
        events = captured_audit_events(event_type="OAUTH_ACCOUNT_LINKED")
        assert events == []

    def test_subject_id_lookup_updates_extra_data(
        self,
        oidc_provider: OAuthProviderConfig,
        system_actor_id: UUID,
        user_factory: Any,
    ) -> None:
        """Repeated logins refresh the SocialAccount extra_data with
        the latest provider claims (minus tokens)."""
        existing_user = user_factory(email="alice@example.test")
        sa = SocialAccount.objects.create(
            user=existing_user,
            provider="test-oidc",
            uid="subject-12345",
            extra_data={"old": "data"},
        )

        new_claims = ExternalIdentityClaims(
            provider_code="test-oidc",
            provider_uid="subject-12345",
            email="alice@example.test",
            email_verified=True,
            display_name="Alice Updated",
            raw_claims={
                "email": "alice@example.test",
                "name": "Alice Updated",
                "access_token": "should-be-stripped",
            },
        )
        resolve_external_user(
            claims=new_claims,
            provider_config=oidc_provider,
            actor_id=system_actor_id,
        )

        sa.refresh_from_db()
        assert sa.extra_data["name"] == "Alice Updated"
        assert "access_token" not in sa.extra_data
        assert "mph_last_seen_at" in sa.extra_data


# ---------------------------------------------------------------------------
# Step 5: email-based linking. (J.3.5 #4)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestEmailBasedLinking:
    """J.3.5 #4: verified email links to existing invited user."""

    def test_verified_email_links_to_existing_user(
        self,
        oidc_provider: OAuthProviderConfig,
        system_actor_id: UUID,
        user_factory: Any,
    ) -> None:
        existing_user = user_factory(email="alice@example.test")

        resolved = resolve_external_user(
            claims=_claims(),
            provider_config=oidc_provider,
            actor_id=system_actor_id,
        )

        assert resolved.id == existing_user.id
        # SocialAccount was created.
        sa = SocialAccount.objects.get(provider="test-oidc", uid="subject-12345")
        assert sa.user == existing_user

    def test_verified_email_link_emits_audit_event(
        self,
        oidc_provider: OAuthProviderConfig,
        system_actor_id: UUID,
        user_factory: Any,
    ) -> None:
        existing_user = user_factory(email="alice@example.test")

        resolve_external_user(
            claims=_claims(),
            provider_config=oidc_provider,
            actor_id=system_actor_id,
        )

        events = captured_audit_events(event_type="OAUTH_ACCOUNT_LINKED")
        assert len(events) == 1
        event = events[0]
        assert event.actor_id == system_actor_id
        assert event.object_id == str(existing_user.id)
        assert event.metadata is not None
        assert event.metadata["provider_code"] == "test-oidc"
        assert event.metadata["linked_to_new_user"] is False

    def test_verified_email_link_strips_tokens_from_extra_data(
        self,
        oidc_provider: OAuthProviderConfig,
        system_actor_id: UUID,
        user_factory: Any,
    ) -> None:
        existing_user = user_factory(email="alice@example.test")
        claims = ExternalIdentityClaims(
            provider_code="test-oidc",
            provider_uid="subject-12345",
            email="alice@example.test",
            email_verified=True,
            display_name=None,
            raw_claims={
                "email": "alice@example.test",
                "access_token": "must-not-persist",
                "refresh_token": "must-not-persist",
                "id_token": "must-not-persist",
                "code": "must-not-persist",
            },
        )

        resolve_external_user(
            claims=claims,
            provider_config=oidc_provider,
            actor_id=system_actor_id,
        )

        sa = SocialAccount.objects.get(provider="test-oidc", uid="subject-12345")
        assert "access_token" not in sa.extra_data
        assert "refresh_token" not in sa.extra_data
        assert "id_token" not in sa.extra_data
        assert "code" not in sa.extra_data

    def test_inactive_existing_user_rejected_on_email_match(
        self,
        oidc_provider: OAuthProviderConfig,
        system_actor_id: UUID,
        user_factory: Any,
    ) -> None:
        existing = user_factory(email="alice@example.test")
        existing.is_active = False
        existing.save()

        with pytest.raises(UserInactiveError):
            resolve_external_user(
                claims=_claims(),
                provider_config=oidc_provider,
                actor_id=system_actor_id,
            )


# ---------------------------------------------------------------------------
# B.4.7 #4: conflicting external identity. (J.3.6 #4)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestConflictingExternalIdentity:
    """J.3.6 #4: conflicting external identity blocks login."""

    def test_conflicting_external_identity_blocks_link(
        self,
        oidc_provider: OAuthProviderConfig,
        system_actor_id: UUID,
        user_factory: Any,
    ) -> None:
        """A user already has a different subject ID for the same provider.

        The login MUST stop. The user-facing message (rendered by the
        Phase 3 adapter) is the account-linking help flow.
        """
        existing_user = user_factory(email="alice@example.test")
        SocialAccount.objects.create(
            user=existing_user,
            provider="test-oidc",
            uid="OLD-SUBJECT-ID",  # different from the inbound claim
            extra_data={},
        )

        with pytest.raises(ConflictingExternalIdentityError) as exc:
            resolve_external_user(
                claims=_claims(provider_uid="NEW-SUBJECT-ID"),
                provider_config=oidc_provider,
                actor_id=system_actor_id,
            )
        assert exc.value.user_id == existing_user.id
        assert exc.value.provider_code == "test-oidc"
        assert exc.value.provider_uid == "NEW-SUBJECT-ID"

        # No new SocialAccount was created.
        assert (
            SocialAccount.objects.filter(
                provider="test-oidc", uid="NEW-SUBJECT-ID"
            ).count()
            == 0
        )

    def test_different_provider_is_NOT_a_conflict(
        self,
        oidc_provider: OAuthProviderConfig,
        system_actor_id: UUID,
        user_factory: Any,
    ) -> None:
        """A user with a Google identity can also have a Microsoft identity."""
        existing_user = user_factory(email="alice@example.test")
        SocialAccount.objects.create(
            user=existing_user,
            provider="some-other-provider",
            uid="microsoft-subject-id",
            extra_data={},
        )

        # New login via test-oidc — different provider. Should succeed.
        resolved = resolve_external_user(
            claims=_claims(),
            provider_config=oidc_provider,
            actor_id=system_actor_id,
        )
        assert resolved.id == existing_user.id


# ---------------------------------------------------------------------------
# Step 6 / 7: self-registration policy.
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestSelfRegistration:
    def test_no_existing_user_and_self_reg_disabled_rejected(
        self, oidc_provider: OAuthProviderConfig, system_actor_id: UUID
    ) -> None:
        """B.4.6 step 4 default: no User, self-registration off → reject."""
        with pytest.raises(NoExistingUserAndSelfRegistrationDisabledError) as exc:
            resolve_external_user(
                claims=_claims(email="newuser@example.test"),
                provider_config=oidc_provider,
                actor_id=system_actor_id,
            )
        assert exc.value.email == "newuser@example.test"
        assert exc.value.provider_code == "test-oidc"

        # No User created, no SocialAccount created.
        User = get_user_model()
        assert not User.objects.filter(email="newuser@example.test").exists()

    def test_no_existing_user_and_self_reg_enabled_creates_user(
        self,
        oidc_provider_with_self_registration: OAuthProviderConfig,
        system_actor_id: UUID,
    ) -> None:
        resolved = resolve_external_user(
            claims=_claims(
                provider_code="test-oidc-selfreg",
                email="newuser@example.test",
            ),
            provider_config=oidc_provider_with_self_registration,
            actor_id=system_actor_id,
        )
        assert resolved.email == "newuser@example.test"
        assert resolved.is_active is True
        assert resolved.is_staff is False
        assert resolved.is_superuser is False
        assert resolved.is_system is False
        assert resolved.external_login_only is True
        # Unusable password (per B.5.1).
        assert not resolved.has_usable_password()

        # SocialAccount was created.
        sa = SocialAccount.objects.get(
            provider="test-oidc-selfreg", uid="subject-12345"
        )
        assert sa.user == resolved

    def test_self_registration_emits_user_registered_and_oauth_account_linked(
        self,
        oidc_provider_with_self_registration: OAuthProviderConfig,
        system_actor_id: UUID,
    ) -> None:
        resolve_external_user(
            claims=_claims(
                provider_code="test-oidc-selfreg",
                email="newuser@example.test",
            ),
            provider_config=oidc_provider_with_self_registration,
            actor_id=system_actor_id,
        )

        registered = captured_audit_events(event_type="USER_REGISTERED")
        linked = captured_audit_events(event_type="OAUTH_ACCOUNT_LINKED")

        assert len(registered) == 1
        assert len(linked) == 1

        # The USER_REGISTERED payload identifies the registration source.
        assert registered[0].payload_after is not None
        assert (
            registered[0].payload_after["registration_source"]
            == "oauth_self_registration"
        )
        assert registered[0].payload_after["external_login_only"] is True
        assert registered[0].payload_after["password_was_set"] is False
        # The OAUTH_ACCOUNT_LINKED event marks this as a new user.
        assert linked[0].metadata is not None
        assert linked[0].metadata["linked_to_new_user"] is True


# ---------------------------------------------------------------------------
# B.3.9 enforcement: resolution MUST NOT create Membership.
# (J.3.9 #10)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestResolutionDoesNotCreateMembership:
    """B.3.9: OAuth/OIDC login proves identity only.

    The resolution service MUST NOT create Membership / Role /
    Capability / OperatingScope rows. This is verified by counting
    Membership rows before and after.
    """

    def test_subject_id_lookup_does_not_create_membership(
        self,
        oidc_provider: OAuthProviderConfig,
        system_actor_id: UUID,
        user_factory: Any,
    ) -> None:
        from apps.platform.organizations.models import Membership

        existing_user = user_factory(email="alice@example.test")
        SocialAccount.objects.create(
            user=existing_user,
            provider="test-oidc",
            uid="subject-12345",
            extra_data={},
        )
        baseline = Membership.objects.count()

        resolve_external_user(
            claims=_claims(),
            provider_config=oidc_provider,
            actor_id=system_actor_id,
        )

        assert Membership.objects.count() == baseline

    def test_email_link_does_not_create_membership(
        self,
        oidc_provider: OAuthProviderConfig,
        system_actor_id: UUID,
        user_factory: Any,
    ) -> None:
        from apps.platform.organizations.models import Membership

        user_factory(email="alice@example.test")
        baseline = Membership.objects.count()

        resolve_external_user(
            claims=_claims(),
            provider_config=oidc_provider,
            actor_id=system_actor_id,
        )

        assert Membership.objects.count() == baseline

    def test_self_registration_does_not_create_membership(
        self,
        oidc_provider_with_self_registration: OAuthProviderConfig,
        system_actor_id: UUID,
    ) -> None:
        from apps.platform.organizations.models import Membership

        baseline = Membership.objects.count()

        resolve_external_user(
            claims=_claims(
                provider_code="test-oidc-selfreg",
                email="newuser@example.test",
            ),
            provider_config=oidc_provider_with_self_registration,
            actor_id=system_actor_id,
        )

        assert Membership.objects.count() == baseline


# ---------------------------------------------------------------------------
# Argument hygiene.
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestArgumentHygiene:
    def test_null_actor_id_rejected(self, oidc_provider: OAuthProviderConfig) -> None:
        with pytest.raises(ValueError):
            resolve_external_user(
                claims=_claims(),
                provider_config=oidc_provider,
                actor_id=None,  # type: ignore[arg-type]
            )

    def test_provider_code_mismatch_rejected(
        self, oidc_provider: OAuthProviderConfig, system_actor_id: UUID
    ) -> None:
        with pytest.raises(ValueError) as exc:
            resolve_external_user(
                claims=_claims(provider_code="some-other-code"),
                provider_config=oidc_provider,
                actor_id=system_actor_id,
            )
        assert "provider_code mismatch" in str(exc.value)
