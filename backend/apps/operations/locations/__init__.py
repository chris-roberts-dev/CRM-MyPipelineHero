"""Region / Market / Location (RML) — operating-scope hierarchy (B.2).

Per B.2.1:

    Organization
      └── Region (many)
            └── Market (many)
                  └── Location (many)

These three models are tenant-owned (TenantOwnedModel subclasses,
organization FK with on_delete=PROTECT). They define the operating
scope a Membership can be restricted to via MembershipScopeAssignment
(see ``apps.platform.organizations.scope_models``).

Public API:

* :class:`Region`
* :class:`Market`
* :class:`Location`
* :class:`LocationQuerySet` — per-model QuerySet overriding
  ``intersect_with_operating_scope`` because Location IS the leaf
  model in the hierarchy.

Imports are lazy (PEP 562) so this package can appear in
``INSTALLED_APPS`` without triggering ``AppRegistryNotReady`` during
Django startup.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

__all__ = ["Location", "LocationQuerySet", "Market", "Region"]


if TYPE_CHECKING:
    from apps.operations.locations.models import (
        Location,
        LocationQuerySet,
        Market,
        Region,
    )


_EXPORTS: dict[str, tuple[str, str]] = {
    "Location": ("apps.operations.locations.models", "Location"),
    "LocationQuerySet": ("apps.operations.locations.models", "LocationQuerySet"),
    "Market": ("apps.operations.locations.models", "Market"),
    "Region": ("apps.operations.locations.models", "Region"),
}


def __getattr__(name: str) -> Any:
    target = _EXPORTS.get(name)
    if target is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    import importlib

    module = importlib.import_module(target[0])
    value = getattr(module, target[1])
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    return sorted(set(__all__) | set(globals().keys()))
