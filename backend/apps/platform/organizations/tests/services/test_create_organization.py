"""Tests for apps.platform.organizations.services.create_organization."""

from __future__ import annotations

import pytest
from django.apps import apps as django_apps
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError

from apps.platform.audit.services import captured_audit_events
from apps.platform.organizations.services import (
    OrganizationSlugInUseError,
    UserNotFoundError,
    create_organization,
)


@pytest.fixture
def Organization():
    return django_apps.get_model("platform_organizations", "Organization")


@pytest.fixture
def Role():
    return django_apps.get_model("platform_rbac", "Role")


@pytest.fixture
def RoleCapability():
    return django_apps.get_model("platform_rbac", "RoleCapability")


@pytest.fixture
def system_user_id():
    User = get_user_model()
    return User.objects.get(is_system=True).id


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_happy_path_creates_org_and_eleven_per_tenant_roles(
    Organization, Role, RoleCapability, system_user_id
) -> None:
    org = create_organization(
        slug="acme",
        name="Acme Co.",
        primary_contact_email="ops@acme.example",
        actor_id=system_user_id,
    )

    # Organization row
    assert Organization.objects.filter(slug="acme").count() == 1
    assert org.slug == "acme"
    assert org.name == "Acme Co."
    assert org.status == "ACTIVE"

    # 11 per-tenant roles, with the expected flags
    tenant_roles = Role.objects.filter(organization=org)
    assert tenant_roles.count() == 11
    for role in tenant_roles:
        assert role.is_default is False
        assert role.is_locked is False

    # Capabilities replicated from each template
    templates = Role.objects.filter(organization__isnull=True, is_default=True)
    for template in templates:
        clone = tenant_roles.get(code=template.code)
        template_codes = set(
            RoleCapability.objects.filter(role=template).values_list(
                "capability__code", flat=True
            )
        )
        clone_codes = set(
            RoleCapability.objects.filter(role=clone).values_list(
                "capability__code", flat=True
            )
        )
        assert template_codes == clone_codes, (
            f"Role clone {clone.code!r} has different capabilities than "
            f"its template"
        )
        # Scoped flag preserved
        assert clone.is_scoped_role is template.is_scoped_role


# ---------------------------------------------------------------------------
# Audit emission
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_create_organization_emits_org_created_audit(system_user_id) -> None:
    org = create_organization(
        slug="audited",
        name="Audited Co.",
        primary_contact_email="a@audited.example",
        actor_id=system_user_id,
    )

    events = [
        event
        for event in captured_audit_events(event_type="ORG_CREATED")
        if event.organization_id == org.id and event.object_id == str(org.id)
    ]
    assert len(events) == 1
    evt = events[0]
    assert evt.event_type == "ORG_CREATED"
    assert evt.actor_id == system_user_id
    assert evt.organization_id == org.id
    assert evt.object_kind == "platform_organizations.Organization"
    assert evt.object_id == str(org.id)
    assert evt.payload_after is not None
    assert evt.payload_after["slug"] == "audited"


# ---------------------------------------------------------------------------
# Slug collision
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_slug_collision_raises_typed_exception(Organization, system_user_id) -> None:
    create_organization(
        slug="collide",
        name="First",
        primary_contact_email="a@collide.example",
        actor_id=system_user_id,
    )

    with pytest.raises(OrganizationSlugInUseError) as excinfo:
        create_organization(
            slug="collide",
            name="Second",
            primary_contact_email="b@collide.example",
            actor_id=system_user_id,
        )
    assert excinfo.value.slug == "collide"

    # Only the first org exists; the second attempt rolled back cleanly.
    assert Organization.objects.filter(slug="collide").count() == 1


@pytest.mark.django_db
def test_collision_does_not_emit_audit_event(system_user_id) -> None:
    """The audit event is inside the atomic block, so a slug collision
    rolls back the audit event along with the (failed) Organization
    insert.
    """
    create_organization(
        slug="collide-audit",
        name="First",
        primary_contact_email="a@collide-audit.example",
        actor_id=system_user_id,
    )
    events_after_first = len(captured_audit_events(event_type="ORG_CREATED"))

    with pytest.raises(OrganizationSlugInUseError):
        create_organization(
            slug="collide-audit",
            name="Second",
            primary_contact_email="b@collide-audit.example",
            actor_id=system_user_id,
        )
    events_after_second = len(captured_audit_events(event_type="ORG_CREATED"))
    assert events_after_second == events_after_first


# ---------------------------------------------------------------------------
# Invalid slug shapes
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "bad_slug",
    [
        "UPPER",
        "1leading-digit",
        "-leading-hyphen",
        "trailing-hyphen-",
        "way-too-long-" + "x" * 80,
        "ab",  # 2 chars; min is 3 per ^[a-z][a-z0-9-]{1,61}[a-z0-9]$
        "has space",
        "has_underscore",
        "has.dot",
        "",
    ],
)
@pytest.mark.django_db
def test_invalid_slug_raises_validation_error_before_db_write(
    bad_slug, Organization, system_user_id
) -> None:
    initial_count = Organization.objects.count()
    with pytest.raises(ValidationError):
        create_organization(
            slug=bad_slug,
            name="Invalid",
            primary_contact_email="ops@example.example",
            actor_id=system_user_id,
        )
    # No DB writes happened.
    assert Organization.objects.count() == initial_count


@pytest.mark.parametrize(
    "good_slug",
    [
        "abc",
        "acme",
        "acme-co",
        "acme-123",
        "a1b2-c3-d4",
        "x" + "y" * 61 + "z",  # 63 chars exactly, the max
    ],
)
@pytest.mark.django_db
def test_valid_slug_shapes_pass_validation(good_slug, system_user_id) -> None:
    org = create_organization(
        slug=good_slug,
        name="Valid",
        primary_contact_email="ops@example.example",
        actor_id=system_user_id,
    )
    assert org.slug == good_slug


# ---------------------------------------------------------------------------
# Idempotency rule: the service does NOT silently no-op on existing slug
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_create_is_not_idempotent_on_existing_slug(system_user_id) -> None:
    """Idempotent slug handling is the seed_dev_tenant convenience
    pattern, NOT the production service pattern. The service raises a
    typed exception so callers explicitly choose how to handle
    collisions.
    """
    create_organization(
        slug="strict",
        name="First",
        primary_contact_email="a@strict.example",
        actor_id=system_user_id,
    )
    with pytest.raises(OrganizationSlugInUseError):
        create_organization(
            slug="strict",
            name="Second",
            primary_contact_email="b@strict.example",
            actor_id=system_user_id,
        )


# ---------------------------------------------------------------------------
# Required-argument guards
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_missing_actor_id_raises_value_error() -> None:
    with pytest.raises(ValueError):
        create_organization(
            slug="no-actor",
            name="No Actor",
            primary_contact_email="x@no-actor.example",
            actor_id=None,  # type: ignore[arg-type]
        )


@pytest.mark.django_db
def test_nonexistent_actor_raises_user_not_found() -> None:
    import uuid

    with pytest.raises(UserNotFoundError):
        create_organization(
            slug="ghost-actor",
            name="Ghost Actor",
            primary_contact_email="x@ghost.example",
            actor_id=uuid.uuid4(),
        )


@pytest.mark.django_db
def test_invalid_email_raises_validation_error(system_user_id) -> None:
    with pytest.raises(ValidationError):
        create_organization(
            slug="bad-email",
            name="Bad Email",
            primary_contact_email="not-an-email",
            actor_id=system_user_id,
        )


# ---------------------------------------------------------------------------
# Atomicity
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_role_clone_runs_in_same_transaction_as_org_create(
    Organization, Role, system_user_id, monkeypatch
) -> None:
    """If role cloning blows up, the Organization insert rolls back too."""
    from apps.platform.organizations.services import _create as service_module

    def boom(**kwargs):
        raise RuntimeError("simulated clone failure")

    monkeypatch.setattr(service_module, "_clone_default_role_templates", boom)

    with pytest.raises(RuntimeError, match="simulated clone failure"):
        create_organization(
            slug="atomic-test",
            name="Atomic Test",
            primary_contact_email="a@atomic.example",
            actor_id=system_user_id,
        )

    # No Organization row was committed.
    assert Organization.objects.filter(slug="atomic-test").count() == 0
