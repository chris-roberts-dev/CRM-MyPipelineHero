"""MyPipelineHero tenancy primitives (B.1.3-B.1.7).

This package owns the row-level multi-tenancy foundation. Every
tenant-owned model in the codebase inherits from :class:`TenantOwnedModel`
and uses :class:`TenantManager` for ORM access. The B.1.7 CI guardrail
(``tests/test_isolation_guardrail.py``) fails the build if those rules
are broken.

============================================================
When to subclass ``TenantOwnedModel``
============================================================

**Subclass it when:** the record is owned by a single Organization and
must not be visible to any other tenant. The vast majority of
business-domain records fall in this bucket:

  - Lead, Quote, QuoteVersion, QuoteVersionLine
  - Client, ClientContact, ClientLocation
  - SalesOrder, SalesOrderLine
  - WorkOrder, BuildOrder, PurchaseOrder
  - Invoice, InvoiceLine, Payment, PaymentAllocation
  - Region, Market, Location (RML — see B.2.2)
  - PricingRule, PriceList, PriceListItem
  - DocumentAttachment, Task, Communication
  - AuditEvent, OutboxEntry

**DO NOT subclass it when:** the record is platform-tier or system
infrastructure:

  - ``Organization`` itself — it IS the tenant; it has no
    ``organization`` FK to itself.
  - ``User``, ``ExternalIdentity``, ``OAuthProviderConfig`` —
    platform-tier identity infrastructure. Tenant authorization comes
    through ``Membership``, not through tenancy on ``User``.
  - ``Capability``, default-template ``Role`` rows — platform-tier
    permission registry. Per-tenant ``Role`` rows DO have an
    organization FK but use ``models.Manager`` because the platform
    console queries across tenants.
  - ``Membership`` — the JOIN row between ``User`` and ``Organization``.
    It is tenant-scoped but the manager surface differs (the platform
    console queries across tenants; tenant-internal queries use
    ``Membership.objects.filter(organization_id=...)`` explicitly).
  - ``Capability``, ``RoleCapability``, ``MembershipRole``,
    ``MembershipCapabilityGrant`` — the RBAC tables. Cross-tenant
    queries are normal for the platform console.

If in doubt, ask: "would a Support User legitimately query this table
across tenants from the platform console?" If yes, the model is
platform-tier and should NOT be ``TenantOwnedModel``.

============================================================
Cross-tenant access exception paths (B.1.5)
============================================================

Two narrow exceptions are permitted by the guide:

1. **Support User platform console.** Custom platform admin views
   may perform controlled cross-tenant queries via
   ``Model.objects.platform_admin_queryset()`` (TODO: lands with the
   platform query service in M2) and MUST emit a
   ``PLATFORM_ADMIN_QUERY`` audit event.
2. **Migrations.** ``TenantManager.use_in_migrations = False`` means
   data migrations see ``models.Manager()`` semantics on tenant-owned
   models, allowing the migration framework to operate without tenant
   scoping. Data migrations that themselves filter by org MUST do so
   explicitly.

The base Django admin MUST NOT be used as the production platform
console (it is mounted at ``/django-admin/`` for dev inspection only).

============================================================
Foreign-key tenancy invariant (B.1.6)
============================================================

When a tenant-owned record references another tenant-owned record,
both MUST belong to the same Organization. Enforced at:

1. **Service layer** via :func:`ensure_same_org` (raises
   :exc:`TenantViolationError` if any pair of records carries
   different ``organization_id`` values).
2. **Object check in RBAC enforcement** (B.6.2 step 7).

DB-level CHECK constraints across tables are explicitly NOT used in
v1 — they would force every state-change service to load the parent's
``organization_id`` redundantly. The service-layer check is the
contractual enforcement point.

============================================================
Public API
============================================================

The names below are re-exported lazily for convenience. The lazy
re-export is required because importing model classes (or anything
that transitively defines a Django model) at package-import time
triggers ``AppRegistryNotReady`` during Django startup. PEP 562
``__getattr__`` defers the import until the attribute is first
accessed, by which point the app registry is always populated.

Convention: code inside this package imports from submodules directly
(``from apps.common.tenancy.models import TenantOwnedModel``). The lazy
re-export below exists solely so external callers can write::

    from apps.common.tenancy import TenantOwnedModel, ensure_same_org

without worrying about which submodule each name lives in.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

__all__ = [
    "OperatingScopeViolationError",
    "TenantManager",
    "TenantOwnedModel",
    "TenantQuerySet",
    "TenantViolationError",
    "ensure_same_org",
    "resolve_location_ids_for_scopes",
]


# Static type-checking imports — visible to mypy/IDE, not executed at
# runtime. Pairs with the PEP 562 ``__getattr__`` below.
if TYPE_CHECKING:
    from apps.common.tenancy.exceptions import (
        OperatingScopeViolationError,
        TenantViolationError,
    )
    from apps.common.tenancy.managers import TenantManager, TenantQuerySet
    from apps.common.tenancy.models import TenantOwnedModel
    from apps.common.tenancy.utils import (
        ensure_same_org,
        resolve_location_ids_for_scopes,
    )


# Map of public-API names to (submodule, attribute) tuples.
_EXPORTS: dict[str, tuple[str, str]] = {
    "OperatingScopeViolationError": (
        "apps.common.tenancy.exceptions",
        "OperatingScopeViolationError",
    ),
    "TenantViolationError": (
        "apps.common.tenancy.exceptions",
        "TenantViolationError",
    ),
    "TenantManager": ("apps.common.tenancy.managers", "TenantManager"),
    "TenantQuerySet": ("apps.common.tenancy.managers", "TenantQuerySet"),
    "TenantOwnedModel": ("apps.common.tenancy.models", "TenantOwnedModel"),
    "ensure_same_org": ("apps.common.tenancy.utils", "ensure_same_org"),
    "resolve_location_ids_for_scopes": (
        "apps.common.tenancy.utils",
        "resolve_location_ids_for_scopes",
    ),
}


def __getattr__(name: str) -> Any:  # PEP 562 — lazy package attribute access
    """Resolve a public-API name on first access.

    Defers submodule imports until after Django's app registry has
    finished populating. Without this, ``from apps.common.tenancy
    import TenantOwnedModel`` at the top of any module imported during
    Django startup would raise ``AppRegistryNotReady``.
    """
    target = _EXPORTS.get(name)
    if target is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module_path, attr_name = target
    import importlib

    module = importlib.import_module(module_path)
    value = getattr(module, attr_name)
    # Cache on the package module so subsequent accesses are O(1).
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    """Make ``dir(apps.common.tenancy)`` show the public API names."""
    return sorted(set(__all__) | set(globals().keys()))
