"""TenantOwnedModel abstract base (B.1.3).

Every tenant-owned model in the codebase inherits from this class.
The shape is dictated by B.1.3.

Subclasses MUST NOT override:
    - ``organization`` (the FK type and on_delete are mandatory)
    - ``is_tenant_owned`` (it is the discriminant for the B.1.7
      guardrail)
    - ``objects`` (the manager must remain ``TenantManager``-derived)

Subclasses MAY override:
    - ``created_at`` / ``updated_at`` semantics if a domain has a
      different audit-time concept (rare)
    - ``Meta.abstract = False`` is implicit; concrete subclasses define
      their own ``Meta`` (verbose names, indexes, constraints)
    - The QuerySet class (via ``TenantManager.from_queryset(...)``) to
      add per-model query helpers, including overriding
      ``intersect_with_operating_scope`` for models that carry
      ``location_id``.

See ``apps.common.tenancy.__init__`` for the developer primer on when
to subclass this vs use ``models.Manager``.
"""

from __future__ import annotations

from typing import ClassVar

from django.conf import settings
from django.db import models

from apps.common.tenancy.managers import TenantManager


class TenantOwnedModel(models.Model):
    """Abstract base for every tenant-owned model (B.1.3)."""

    organization = models.ForeignKey(
        "platform_organizations.Organization",
        on_delete=models.PROTECT,
        related_name="+",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="+",
        null=True,
        blank=True,
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="+",
        null=True,
        blank=True,
    )

    # Discriminant attribute checked by the B.1.7 guardrail. Subclasses
    # inherit this automatically; do not re-declare or override it.
    is_tenant_owned: ClassVar[bool] = True

    # Tenant-aware manager. Subclasses may swap in a manager built from
    # a per-model QuerySet subclass, but the manager MUST remain a
    # subclass of TenantManager so use_in_migrations=False and the
    # for_org/for_membership surface are preserved.
    objects: ClassVar[TenantManager] = TenantManager()

    class Meta:
        abstract = True
