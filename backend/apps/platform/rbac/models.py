"""RBAC models: Capability, Role, RoleCapability, MembershipRole,
MembershipCapabilityGrant (B.6.7).

The capability registry is populated by the ``seed_v1`` data migration
(I.6.3). Role templates with ``organization=None, is_locked=True,
is_default=True`` are also seeded; per-tenant Owner/Admin/etc. roles
are created by ``services.create_organization`` (I.6.6).

Permission evaluation algorithm: B.6.2.

Index naming: every ``models.Index`` carries an explicit ``name=``
argument. Auto-generated index names are fragile across Django versions
(the 6-char hash suffix Django computes can drift) and cause spurious
``RenameIndex`` migrations on every ``makemigrations`` run. Always name
indexes explicitly going forward.
"""

from __future__ import annotations

import uuid
from typing import Any, ClassVar

from django.conf import settings
from django.db import models
from django.db.models import Q, UniqueConstraint
from django.utils.translation import gettext_lazy as _


def _new_uuid() -> uuid.UUID:
    """UUID v7 factory (Python 3.14+)."""
    factory = getattr(uuid, "uuid7", uuid.uuid4)
    return factory()


# ---------------------------------------------------------------------------
# Choices
# ---------------------------------------------------------------------------


class CapabilityGrantType(models.TextChoices):
    """Per-membership capability overrides (B.6.7)."""

    GRANT = "GRANT", _("Grant")
    DENY = "DENY", _("Deny")


# ---------------------------------------------------------------------------
# Capability
# ---------------------------------------------------------------------------


class Capability(models.Model):
    """Atomic permission unit (B.6.3, B.6.7).

    Capabilities are platform-scoped (no organization FK). Their codes
    are stable contract strings — renaming is a breaking change
    (G.2.3 analog).
    """

    id = models.UUIDField(primary_key=True, default=_new_uuid, editable=False)
    code = models.CharField(max_length=64, unique=True)
    name = models.CharField(max_length=120)
    description = models.TextField(blank=True, default="")
    category = models.CharField(max_length=64)

    is_deprecated = models.BooleanField(default=False)
    deprecated_in_version = models.CharField(max_length=32, null=True, blank=True)
    deprecated_replacement_code = models.CharField(max_length=64, null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("capability")
        verbose_name_plural = _("capabilities")
        indexes: ClassVar[list[Any]] = [
            models.Index(fields=["category"], name="platform_rb_categ_idx"),
            models.Index(fields=["is_deprecated"], name="platform_rb_dep_idx"),
        ]

    def __str__(self) -> str:
        return self.code


# ---------------------------------------------------------------------------
# Role
# ---------------------------------------------------------------------------


class Role(models.Model):
    """A bundle of capabilities (B.6.7).

    Template roles have ``organization=NULL, is_default=True,
    is_locked=True``. Per-tenant roles have a concrete organization FK
    and are cloned from templates by ``services.create_organization``
    (I.6.6).

    Uniqueness is ``(organization, code)``. Because ``organization`` is
    nullable and Postgres treats ``NULL`` as distinct by default in unique
    indexes, the constraint uses ``nulls_distinct=False`` so a single
    template per ``code`` is enforced.
    """

    id = models.UUIDField(primary_key=True, default=_new_uuid, editable=False)
    organization = models.ForeignKey(
        "platform_organizations.Organization",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="roles",
        help_text=_(
            "NULL for default templates; concrete org for tenant-scoped roles."
        ),
    )
    code = models.CharField(max_length=64)
    name = models.CharField(max_length=120)
    description = models.TextField(blank=True, default="")

    is_default = models.BooleanField(default=False)
    is_scoped_role = models.BooleanField(
        default=False,
        help_text=_("If True, membership scope assignments restrict access (B.2.5)."),
    )
    is_locked = models.BooleanField(
        default=False,
        help_text=_("If True, capabilities cannot be edited via tenant admin."),
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("role")
        verbose_name_plural = _("roles")
        constraints: ClassVar[list[Any]] = [
            # Tenant-scoped uniqueness (organization is non-null).
            UniqueConstraint(
                fields=["organization", "code"],
                condition=Q(organization__isnull=False),
                name="platform_rbac_role_org_code_unique",
            ),
            # Template uniqueness (organization is NULL).
            UniqueConstraint(
                fields=["code"],
                condition=Q(organization__isnull=True),
                name="platform_rbac_role_template_code_unique",
            ),
        ]
        indexes: ClassVar[list[Any]] = [
            models.Index(
                fields=["organization", "is_default"], name="platform_rb_org_def_idx"
            ),
        ]

    def __str__(self) -> str:
        return f"{self.code}"


# ---------------------------------------------------------------------------
# RoleCapability
# ---------------------------------------------------------------------------


class RoleCapability(models.Model):
    """Role → Capability assignment (B.6.7)."""

    id = models.UUIDField(primary_key=True, default=_new_uuid, editable=False)
    role = models.ForeignKey(
        Role,
        on_delete=models.CASCADE,
        related_name="role_capabilities",
    )
    capability = models.ForeignKey(
        Capability,
        on_delete=models.PROTECT,
        related_name="role_capabilities",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("role capability")
        verbose_name_plural = _("role capabilities")
        constraints: ClassVar[list[Any]] = [
            UniqueConstraint(
                fields=["role", "capability"],
                name="platform_rbac_rolecap_unique",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.role} → {self.capability}"


# ---------------------------------------------------------------------------
# MembershipRole
# ---------------------------------------------------------------------------


class MembershipRole(models.Model):
    """Membership → Role assignment (B.6.7).

    Note: the guide names the entity ``MembershipRole`` (B.6.7 line 2073).
    The M2M is between membership and role; one membership can hold
    multiple roles.
    """

    id = models.UUIDField(primary_key=True, default=_new_uuid, editable=False)
    membership = models.ForeignKey(
        "platform_organizations.Membership",
        on_delete=models.CASCADE,
        related_name="role_assignments",
    )
    role = models.ForeignKey(
        Role,
        on_delete=models.PROTECT,
        related_name="member_assignments",
    )
    # null=True so seed-time / bootstrap assignments don't deadlock.
    # Production assignments through services always set this.
    assigned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="+",
    )
    assigned_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("membership role")
        verbose_name_plural = _("membership roles")
        constraints: ClassVar[list[Any]] = [
            UniqueConstraint(
                fields=["membership", "role"],
                name="platform_rbac_membershiprole_unique",
            ),
        ]
        indexes: ClassVar[list[Any]] = [
            models.Index(fields=["membership"], name="platform_rb_memb_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.membership} → {self.role}"


# ---------------------------------------------------------------------------
# MembershipCapabilityGrant
# ---------------------------------------------------------------------------


class MembershipCapabilityGrant(models.Model):
    """Per-membership capability override (GRANT or DENY) — B.6.2 step 5.

    DENY beats GRANT (B.6.2). Applied on top of role-derived capabilities
    during permission evaluation.
    """

    id = models.UUIDField(primary_key=True, default=_new_uuid, editable=False)
    membership = models.ForeignKey(
        "platform_organizations.Membership",
        on_delete=models.CASCADE,
        related_name="capability_grants",
    )
    capability = models.ForeignKey(
        Capability,
        on_delete=models.PROTECT,
        related_name="membership_grants",
    )
    grant_type = models.CharField(
        max_length=8,
        choices=CapabilityGrantType.choices,
    )
    reason = models.TextField()
    granted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="+",
    )
    granted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("membership capability grant")
        verbose_name_plural = _("membership capability grants")
        constraints: ClassVar[list[Any]] = [
            UniqueConstraint(
                fields=["membership", "capability"],
                name="platform_rbac_membershipcapgrant_unique",
            ),
        ]
        indexes: ClassVar[list[Any]] = [
            models.Index(fields=["membership"], name="platform_rb_memb_grant_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.membership} {self.grant_type} {self.capability}"
