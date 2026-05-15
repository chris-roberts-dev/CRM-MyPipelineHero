"""Organization, Membership, and tenant-lifecycle entities (B.1.2, B.3.5, C.1.16).

This module owns the multi-tenant root entity. Every other tenant-owned
model in the codebase references ``Organization`` via a PROTECTed FK
(B.1.3).

Service-layer note: state-changing flows (create_organization,
invite_user, suspend_membership, request_tenant_deletion, etc.) live in
service functions added in M1+. The models in this file carry no
business logic in ``save()`` — they only declare structure.

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
    """UUID v7 factory (Python 3.14+). Falls back to uuid4 for older runtimes."""
    factory = getattr(uuid, "uuid7", uuid.uuid4)
    return factory()


# ---------------------------------------------------------------------------
# Choices
# ---------------------------------------------------------------------------


class OrganizationStatus(models.TextChoices):
    """Organization lifecycle states (B.1.2)."""

    ACTIVE = "ACTIVE", _("Active")
    SUSPENDED = "SUSPENDED", _("Suspended")
    OFFBOARDING = "OFFBOARDING", _("Offboarding")
    DELETED = "DELETED", _("Deleted")


class MembershipStatus(models.TextChoices):
    """Membership lifecycle states (B.3.5, C.2.9)."""

    INVITED = "INVITED", _("Invited")
    ACTIVE = "ACTIVE", _("Active")
    SUSPENDED = "SUSPENDED", _("Suspended")
    INACTIVE = "INACTIVE", _("Inactive")
    EXPIRED = "EXPIRED", _("Expired")


class TenantExportScope(models.TextChoices):
    """Scope of a tenant data export request (C.1.16, G.7.2)."""

    FULL = "FULL", _("Full")
    COMMERCIAL_ONLY = "COMMERCIAL_ONLY", _("Commercial only")
    AUDIT_ONLY = "AUDIT_ONLY", _("Audit only")


class TenantExportStatus(models.TextChoices):
    """Lifecycle of a tenant export request (C.1.16, G.7.2)."""

    QUEUED = "QUEUED", _("Queued")
    ASSEMBLING = "ASSEMBLING", _("Assembling")
    READY = "READY", _("Ready")
    DOWNLOADED = "DOWNLOADED", _("Downloaded")
    EXPIRED = "EXPIRED", _("Expired")
    FAILED = "FAILED", _("Failed")
    CANCELLED = "CANCELLED", _("Cancelled")


class TenantDeletionStatus(models.TextChoices):
    """Lifecycle of a tenant deletion request (C.1.16, G.7.3)."""

    GRACE_PERIOD = "GRACE_PERIOD", _("Grace period")
    EXECUTING = "EXECUTING", _("Executing")
    EXECUTED = "EXECUTED", _("Executed")
    CANCELLED = "CANCELLED", _("Cancelled")


# ---------------------------------------------------------------------------
# Organization
# ---------------------------------------------------------------------------


class Organization(models.Model):
    """Tenant root (B.1.2).

    Field notes:
    * ``slug`` matches ``^[a-z][a-z0-9-]{1,61}[a-z0-9]$`` and is the subdomain
      key for tenant routing. Slug is immutable post-creation in v1.
    * ``default_tax_jurisdiction_id`` and ``invoicing_policy_id`` reference
      models that land in later milestones (M3 catalog/pricing, M5 billing).
      They are declared as plain UUID columns for now and converted to real
      ``ForeignKey`` columns when those target models exist. The on-delete
      semantics will be ``SET_NULL`` to match the nullable shape.
    * ``accounting_adapter_config`` is required to be encrypted at rest in
      production (F.5.4). We store it as plain JSONB here; an
      ``EncryptedJSONField`` is introduced in M5 alongside the first concrete
      accounting adapter. Local-dev impact: none.
    """

    id = models.UUIDField(primary_key=True, default=_new_uuid, editable=False)
    slug = models.CharField(max_length=63, unique=True)
    name = models.CharField(max_length=200)
    status = models.CharField(
        max_length=16,
        choices=OrganizationStatus.choices,
        default=OrganizationStatus.ACTIVE,
    )

    # Primary contact
    primary_contact_name = models.CharField(max_length=200, blank=True, default="")
    primary_contact_email = models.EmailField()
    primary_contact_phone = models.CharField(max_length=64, blank=True, default="")

    # Locale and finance
    timezone = models.CharField(max_length=64, default="America/Chicago")
    base_currency_code = models.CharField(max_length=3, default="USD")

    # Forward references to later-milestone models (M3/M5).
    # TODO(M3): convert default_tax_jurisdiction_id to FK(TaxJurisdiction, SET_NULL)
    # TODO(M5): convert invoicing_policy_id to FK(InvoicingPolicy, SET_NULL)
    default_tax_jurisdiction_id = models.UUIDField(null=True, blank=True)
    invoicing_policy_id = models.UUIDField(null=True, blank=True)

    # Numbering configuration — per-entity prefix overrides (C.3).
    numbering_config = models.JSONField(default=dict, blank=True)

    # Accounting adapter (F.5.4).
    accounting_adapter_code = models.CharField(max_length=64, default="noop")
    # TODO(M5): replace with EncryptedJSONField when the adapter ships.
    accounting_adapter_config = models.JSONField(default=dict, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("organization")
        verbose_name_plural = _("organizations")
        indexes: ClassVar[list[Any]] = [
            models.Index(fields=["status"], name="platform_or_status_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.slug})"


# ---------------------------------------------------------------------------
# Membership
# ---------------------------------------------------------------------------


class Membership(models.Model):
    """Authoritative tenant-access record (B.3.5).

    Membership is the authoritative tenant-access record. OAuth/OIDC login
    proves identity only — it does not grant tenant access by itself
    (B.3.9).

    The partial unique index on ``is_default_for_user`` enforces that a
    user has at most one default membership (B.3.5).
    """

    id = models.UUIDField(primary_key=True, default=_new_uuid, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="memberships",
    )
    organization = models.ForeignKey(
        Organization,
        on_delete=models.PROTECT,
        related_name="memberships",
    )
    status = models.CharField(
        max_length=16,
        choices=MembershipStatus.choices,
        default=MembershipStatus.INVITED,
    )

    # Invitation fields (B.4 / M1)
    invited_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="+",
    )
    invited_at = models.DateTimeField(null=True, blank=True)
    invitation_expires_at = models.DateTimeField(null=True, blank=True)
    # Audit-masked in service-layer logging.
    invitation_token_hash = models.CharField(max_length=128, null=True, blank=True)
    accepted_at = models.DateTimeField(null=True, blank=True)

    # Per-membership personal name (independent of platform-level User identity)
    first_name = models.CharField(max_length=80, blank=True, default="")
    last_name = models.CharField(max_length=80, blank=True, default="")
    phone = models.CharField(max_length=64, null=True, blank=True)

    is_default_for_user = models.BooleanField(default=False)
    suspended_reason = models.TextField(blank=True, default="")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("membership")
        verbose_name_plural = _("memberships")
        constraints: ClassVar[list[Any]] = [
            UniqueConstraint(
                fields=["user", "organization"],
                name="platform_organizations_membership_user_org_unique",
            ),
            # Partial unique index — at most one default membership per user.
            UniqueConstraint(
                fields=["user"],
                condition=Q(is_default_for_user=True),
                name="platform_organizations_membership_one_default_per_user",
            ),
        ]
        indexes: ClassVar[list[Any]] = [
            models.Index(
                fields=["user", "organization"], name="platform_or_user_id_org_idx"
            ),
            models.Index(
                fields=["organization", "status"], name="platform_or_org_id_status_idx"
            ),
        ]

    def __str__(self) -> str:
        display_name = " ".join(
            part for part in [self.first_name, self.last_name] if part
        ).strip()

        if not display_name:
            get_full_name = getattr(self.user, "get_full_name", None)
            if callable(get_full_name):
                display_name = get_full_name().strip()

        if not display_name:
            display_name = getattr(self.user, "email", str(self.user))

        return (
            f"{display_name} - {self.organization.name} ({self.get_status_display()})"
        )


# ---------------------------------------------------------------------------
# Tenant lifecycle requests
# ---------------------------------------------------------------------------


class TenantExportRequest(models.Model):
    """Tenant data export request (C.1.16, G.7.2).

    Schema only — service logic lands with the export pipeline in a later
    milestone. ``output_attachment_id`` will become a FK to
    ``DocumentAttachment`` when the files app's models land; declared as a
    plain UUID column for now.
    """

    id = models.UUIDField(primary_key=True, default=_new_uuid, editable=False)
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="export_requests",
    )
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="+",
    )
    requested_at = models.DateTimeField(auto_now_add=True)
    requested_scope = models.CharField(
        max_length=24,
        choices=TenantExportScope.choices,
        default=TenantExportScope.FULL,
    )
    status = models.CharField(
        max_length=16,
        choices=TenantExportStatus.choices,
        default=TenantExportStatus.QUEUED,
    )

    # TODO(M2+): convert to FK(DocumentAttachment) once files app lands.
    output_attachment_id = models.UUIDField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    failure_reason = models.TextField(blank=True, default="")
    bytes_size = models.BigIntegerField(null=True, blank=True)
    row_count = models.BigIntegerField(null=True, blank=True)

    cancelled_at = models.DateTimeField(null=True, blank=True)
    cancelled_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="+",
    )

    class Meta:
        verbose_name = _("tenant export request")
        verbose_name_plural = _("tenant export requests")
        indexes: ClassVar[list[Any]] = [
            models.Index(
                fields=["organization", "status"],
                name="platform_or_export_org_st_idx",
            ),
            models.Index(
                fields=["status", "expires_at"], name="platform_or_status_expires_idx"
            ),
        ]

    def __str__(self) -> str:
        return (
            f"Export request {str(self.id)[:8]} "
            f"for {self.organization} "
            f"({self.get_requested_scope_display()}, {self.get_status_display()})"
        )


class TenantDeletionRequest(models.Model):
    """Tenant deletion request (C.1.16, G.7.3).

    Multi-stage workflow with a 30-day grace period. Schema only —
    ``request_tenant_deletion`` / ``cancel_tenant_deletion`` /
    ``execute_tenant_deletion`` services land in M1+.
    """

    id = models.UUIDField(primary_key=True, default=_new_uuid, editable=False)
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="deletion_requests",
    )
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="+",
    )
    requested_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(
        max_length=16,
        choices=TenantDeletionStatus.choices,
        default=TenantDeletionStatus.GRACE_PERIOD,
    )
    grace_period_ends_at = models.DateTimeField()
    # Required: confirmation phrase MUST equal the org slug (G.7.3).
    confirmation_phrase_provided = models.CharField(max_length=63)

    cancelled_at = models.DateTimeField(null=True, blank=True)
    cancelled_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="+",
    )
    cancelled_reason = models.TextField(blank=True, default="")

    executed_at = models.DateTimeField(null=True, blank=True)
    executed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="+",
    )
    rows_deleted_per_table = models.JSONField(null=True, blank=True)

    class Meta:
        verbose_name = _("tenant deletion request")
        verbose_name_plural = _("tenant deletion requests")
        indexes: ClassVar[list[Any]] = [
            models.Index(
                fields=["organization", "status"], name="platform_or_org_status_del_idx"
            ),
            models.Index(
                fields=["status", "grace_period_ends_at"],
                name="platform_or_status_grace_idx",
            ),
        ]

    def __str__(self) -> str:
        return (
            f"Deletion request {str(self.id)[:8]} "
            f"for {self.organization} "
            f"({self.get_status_display()}, grace ends {self.grace_period_ends_at:%Y-%m-%d})"
        )
