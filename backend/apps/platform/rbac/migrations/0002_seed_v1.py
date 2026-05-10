"""Platform-seed migration (I.6.3).

Idempotent. Re-running this migration MUST be a no-op.

Seeds:

1. All V1 capabilities from ``v1_capabilities.V1_CAPABILITIES``.
2. All 11 default role templates (``organization=NULL``) from
   ``v1_default_roles.V1_DEFAULT_ROLES``, with their RoleCapability rows.
3. The System User row (``is_system=True``, unusable password).

The seed migration is one of the two narrow places in the codebase where
``.objects.update_or_create(...)`` is permitted outside the service layer
(the other is test factories). All RBAC data here is idempotent by
``code`` lookup, never by primary-key.

Per-tenant Owner/Org Admin/etc. roles are NOT created here. Those are
created by ``services.create_organization`` (I.6.6) when each tenant is
provisioned.
"""

from __future__ import annotations

from django.db import migrations

from apps.platform.rbac.seeds.v1_capabilities import V1_CAPABILITIES
from apps.platform.rbac.seeds.v1_default_roles import V1_DEFAULT_ROLES

SYSTEM_USER_EMAIL = "system@mypipelinehero.internal"


def seed_v1(apps, schema_editor):
    Capability = apps.get_model("platform_rbac", "Capability")
    Role = apps.get_model("platform_rbac", "Role")
    RoleCapability = apps.get_model("platform_rbac", "RoleCapability")
    User = apps.get_model("platform_accounts", "User")

    # ------------------------------------------------------------------
    # 1. Capabilities (idempotent by code)
    # ------------------------------------------------------------------
    for cap_def in V1_CAPABILITIES:
        Capability.objects.update_or_create(
            code=cap_def["code"],
            defaults={
                "name": cap_def["name"],
                "description": cap_def["description"],
                "category": cap_def["category"],
            },
        )

    # ------------------------------------------------------------------
    # 2. Default role templates with set-based capability sync
    # ------------------------------------------------------------------
    for role_def in V1_DEFAULT_ROLES:
        role, _ = Role.objects.update_or_create(
            organization=None,
            code=role_def["code"],
            defaults={
                "name": role_def["name"],
                "description": role_def["description"],
                "is_default": True,
                "is_scoped_role": role_def.get("is_scoped_role", False),
                "is_locked": True,
            },
        )

        existing_codes = set(
            RoleCapability.objects.filter(role=role).values_list(
                "capability__code", flat=True
            )
        )
        desired_codes = set(role_def["capabilities"])

        # Add new capabilities to this role.
        to_add = desired_codes - existing_codes
        if to_add:
            for cap in Capability.objects.filter(code__in=to_add):
                RoleCapability.objects.create(role=role, capability=cap)

        # Remove capabilities that are no longer expected on this role
        # (e.g. if a future seed migration narrows a role's capability set).
        to_remove = existing_codes - desired_codes
        if to_remove:
            RoleCapability.objects.filter(
                role=role, capability__code__in=to_remove
            ).delete()

    # ------------------------------------------------------------------
    # 3. System User (B.3.10)
    #
    # Exactly one row per environment with is_system=True. Has an
    # unusable password and must never have external identities.
    # The CHECK constraint in platform_accounts.0001 enforces:
    #   is_system implies (is_active AND NOT is_staff AND NOT is_superuser)
    # ------------------------------------------------------------------
    User.objects.update_or_create(
        email=SYSTEM_USER_EMAIL,
        defaults={
            "is_system": True,
            "is_active": True,
            "is_staff": False,
            "is_superuser": False,
            # Unusable password sentinel — Django's hasher representation
            # of "no password set". The historical model used in migrations
            # doesn't expose set_unusable_password(), so we store the
            # sentinel value directly. Matches Django's behavior.
            "password": "!unusable",
        },
    )


def unseed_v1(apps, schema_editor):
    """No-op reverse. We do not delete seeded data on reverse migration
    because doing so would cascade-delete tenant data referencing those
    rows (RoleCapability, etc.). Reverse is only meaningful in dev when
    paired with a full DB drop.
    """
    return


class Migration(migrations.Migration):

    dependencies = [
        ("platform_accounts", "0001_Initial"),
        ("platform_organizations", "0001_Initial"),
        ("platform_rbac", "0001_Initial"),
    ]

    operations = [
        migrations.RunPython(seed_v1, unseed_v1),
    ]
