"""Organization-creation and owner-membership-assignment services (M1 D2).

These are the first concrete service-layer functions in the codebase.
They exemplify the discipline every future service follows:

* Primitive arguments only (no request, no model instances passed
  through views).
* Single ``transaction.atomic()`` boundary per public function.
* Audit emission inside the same boundary.
* Typed exceptions for distinguishable failure modes.
* No state-change ORM writes outside ``services/``.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING
from uuid import UUID

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction

from apps.platform.audit.services import audit_emit
from apps.platform.organizations.models import (
    Membership,
    MembershipStatus,
    Organization,
    OrganizationStatus,
)
from apps.platform.organizations.services.exceptions import (
    MembershipAlreadyExistsError,
    OrganizationNotFoundError,
    OrganizationSlugInUseError,
    UserNotFoundError,
)
from apps.platform.rbac.models import (
    MembershipRole,
    Role,
    RoleCapability,
)

if TYPE_CHECKING:
    pass


# Slug rules per B.1.2: DNS-safe, lowercase, length 3-63, no leading/
# trailing hyphen, no leading digit.
_SLUG_REGEX = re.compile(r"^[a-z][a-z0-9-]{1,61}[a-z0-9]$")


def _validate_slug(slug: str) -> None:
    """Raise ValidationError if slug doesn't match the B.1.2 shape."""
    if not isinstance(slug, str):
        raise ValidationError({"slug": "Slug must be a string."})
    if not _SLUG_REGEX.fullmatch(slug):
        raise ValidationError(
            {
                "slug": (
                    "Slug must match the pattern "
                    "^[a-z][a-z0-9-]{1,61}[a-z0-9]$ "
                    "(DNS-safe, 3-63 chars, no leading/trailing hyphen, "
                    "no leading digit)."
                ),
            },
        )


def _validate_email(value: str, field_name: str = "primary_contact_email") -> None:
    """Lightweight email shape check; full normalization happens at write time."""
    if not isinstance(value, str) or "@" not in value or len(value) > 254:
        raise ValidationError({field_name: "Must be a valid email address."})


# ---------------------------------------------------------------------------
# create_organization
# ---------------------------------------------------------------------------


def create_organization(
    *,
    slug: str,
    name: str,
    primary_contact_email: str,
    primary_contact_name: str = "",
    primary_contact_phone: str = "",
    timezone: str = "America/Chicago",
    base_currency_code: str = "USD",
    actor_id: UUID,
) -> Organization:
    """Provision a new tenant Organization with cloned per-tenant Role rows.

    Steps performed inside a single ``transaction.atomic()``:

    1. Create the Organization row.
    2. Clone all 11 default Role templates (organization=NULL, is_default=True)
       to per-tenant Role rows scoped to this Organization. For each clone,
       replicate the template's RoleCapability rows so the per-tenant Role
       holds the same capability set as its template.
    3. Emit an ``ORG_CREATED`` audit event.

    Args:
        slug: DNS-safe subdomain key per B.1.2. Validated against
            ``^[a-z][a-z0-9-]{1,61}[a-z0-9]$``.
        name: Human-readable organization name.
        primary_contact_email: Primary contact email (required by Org model).
        primary_contact_name: Optional contact display name.
        primary_contact_phone: Optional contact phone.
        timezone: IANA timezone name; defaults to America/Chicago.
        base_currency_code: ISO 4217 currency code; defaults to USD.
        actor_id: UUID of the User performing the creation. For
            system-bootstrap flows (e.g. seed_dev_tenant), pass the
            System User's id.

    Returns:
        The newly created Organization.

    Raises:
        ValidationError: any input fails validation. No DB writes
            occur in this case.
        OrganizationSlugInUseError: the slug is already taken. No
            partial state is left behind because the transaction rolls
            back.
        ValueError: actor_id is missing.
    """
    if actor_id is None:
        raise ValueError("actor_id is required.")

    _validate_slug(slug)
    if not name or not isinstance(name, str):
        raise ValidationError({"name": "Name is required."})
    _validate_email(primary_contact_email)

    User = get_user_model()
    # Confirm the actor exists. The cost is one indexed lookup.
    if not User.objects.filter(pk=actor_id).exists():
        raise UserNotFoundError(actor_id)

    try:
        with transaction.atomic():
            org = Organization.objects.create(
                slug=slug,
                name=name,
                status=OrganizationStatus.ACTIVE,
                primary_contact_name=primary_contact_name,
                primary_contact_email=primary_contact_email,
                primary_contact_phone=primary_contact_phone,
                timezone=timezone,
                base_currency_code=base_currency_code,
            )

            _clone_default_role_templates(organization=org)

            audit_emit(
                "ORG_CREATED",
                actor_id=actor_id,
                organization_id=org.id,
                object_kind="platform_organizations.Organization",
                object_id=str(org.id),
                payload_after={
                    "slug": org.slug,
                    "name": org.name,
                    "status": org.status,
                    "timezone": org.timezone,
                    "base_currency_code": org.base_currency_code,
                },
            )
    except IntegrityError as exc:
        # The Organization model's unique constraint on slug is the only
        # realistic IntegrityError source on this code path. We re-raise
        # as a typed exception so callers branch cleanly.
        if "slug" in str(exc).lower():
            raise OrganizationSlugInUseError(slug) from exc
        raise

    return org


def _clone_default_role_templates(*, organization: Organization) -> None:
    """Clone the 11 default Role templates to per-tenant Role rows.

    Called inside ``create_organization``'s atomic block. Pre-conditions:

    * The 11 templates exist (seed_v1 ran).
    * No per-tenant Role rows for this organization exist yet (the
      Organization was just created in the same transaction).

    Each clone:

    * has organization=organization (tenant-scoped),
    * has is_default=False, is_locked=False (tenant copies can be
      modified from M1 onward by Org Admin),
    * preserves the template's is_scoped_role flag,
    * has matching RoleCapability rows pointing at the same Capability
      objects.
    """
    templates = list(
        Role.objects.filter(
            organization__isnull=True, is_default=True
        ).prefetch_related("role_capabilities__capability")
    )
    if len(templates) != 11:
        raise RuntimeError(
            f"Expected 11 default role templates from seed_v1, found "
            f"{len(templates)}. The platform seed migration must run "
            f"before create_organization."
        )

    # Bulk-create the per-tenant Role rows. We don't use bulk_create
    # for the role itself because we need each row's id immediately to
    # create RoleCapability links; a per-row create is fine at 11 rows.
    cap_links: list[RoleCapability] = []
    for template in templates:
        tenant_role = Role.objects.create(
            organization=organization,
            code=template.code,
            name=template.name,
            description=template.description,
            is_default=False,
            is_scoped_role=template.is_scoped_role,
            is_locked=False,
        )
        for rc in template.role_capabilities.all():
            cap_links.append(RoleCapability(role=tenant_role, capability=rc.capability))

    if cap_links:
        RoleCapability.objects.bulk_create(cap_links)


# ---------------------------------------------------------------------------
# assign_owner_membership
# ---------------------------------------------------------------------------


def assign_owner_membership(
    *,
    organization_id: UUID,
    user_id: UUID,
    actor_id: UUID,
    first_name: str = "",
    last_name: str = "",
) -> Membership:
    """Create the bootstrap Owner Membership for a tenant.

    Steps performed inside a single ``transaction.atomic()``:

    1. Confirm the Organization and User both exist.
    2. Confirm no Membership already exists for the pair.
    3. Create a Membership with status=ACTIVE.
       ``is_default_for_user`` is set True if and only if the user
       does not already have a default Membership in another org.
    4. Look up the per-tenant Owner Role (cloned by
       :func:`create_organization`).
    5. Create a MembershipRole row linking the membership to that role.
    6. Emit ``MEMBERSHIP_CREATED`` and ``ROLE_ASSIGNED`` audit events.

    Args:
        organization_id: The Organization the new member joins.
        user_id: The User being made the Owner.
        actor_id: The User performing the action. For system-bootstrap
            flows this is the System User.
        first_name: Optional given name on the Membership.
        last_name: Optional family name on the Membership.

    Returns:
        The newly created Membership.

    Raises:
        OrganizationNotFoundError: the org doesn't exist.
        UserNotFoundError: the target user doesn't exist.
        MembershipAlreadyExistsError: the (user, org) pair is already
            a Membership.
        RuntimeError: the per-tenant Owner Role is missing (would
            indicate create_organization was bypassed).
    """
    User = get_user_model()

    with transaction.atomic():
        try:
            org = Organization.objects.get(pk=organization_id)
        except Organization.DoesNotExist as exc:
            raise OrganizationNotFoundError(organization_id) from exc
        try:
            user = User.objects.get(pk=user_id)
        except User.DoesNotExist as exc:
            raise UserNotFoundError(user_id) from exc
        if not User.objects.filter(pk=actor_id).exists():
            raise UserNotFoundError(actor_id)

        if Membership.objects.filter(user=user, organization=org).exists():
            raise MembershipAlreadyExistsError(
                user_id=user_id, organization_id=organization_id
            )

        user_has_default = Membership.objects.filter(
            user=user, is_default_for_user=True
        ).exists()

        membership = Membership.objects.create(
            user=user,
            organization=org,
            status=MembershipStatus.ACTIVE,
            first_name=first_name,
            last_name=last_name,
            is_default_for_user=not user_has_default,
        )

        try:
            owner_role = Role.objects.get(organization=org, code="owner")
        except Role.DoesNotExist as exc:
            raise RuntimeError(
                f"Per-tenant Owner role missing for organization "
                f"{org.slug!r}. Was create_organization called? "
                "Skipping it bypasses the role-template clone step."
            ) from exc

        # actor_id must be a User instance for the assigned_by FK, but
        # services accept primitives. Build the assignment with the
        # actor object loaded above.
        actor = User.objects.get(pk=actor_id)
        role_assignment = MembershipRole.objects.create(
            membership=membership,
            role=owner_role,
            assigned_by=actor,
        )

        audit_emit(
            "MEMBERSHIP_CREATED",
            actor_id=actor_id,
            organization_id=org.id,
            object_kind="platform_organizations.Membership",
            object_id=str(membership.id),
            payload_after={
                "user_id": str(user.id),
                "status": membership.status,
                "is_default_for_user": membership.is_default_for_user,
            },
        )
        audit_emit(
            "ROLE_ASSIGNED",
            actor_id=actor_id,
            organization_id=org.id,
            object_kind="platform_rbac.MembershipRole",
            object_id=str(role_assignment.id),
            payload_after={
                "membership_id": str(membership.id),
                "role_code": owner_role.code,
                "role_id": str(owner_role.id),
            },
        )

    return membership
