"""Public API for the platform_organizations app.

Lazy re-exports (PEP 562) to avoid AppRegistryNotReady during Django
startup. Production code should normally import from
``apps.platform.organizations.models`` or
``apps.platform.organizations.scope_models`` directly; the names
re-exported here are a convenience layer.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

__all__ = [
    "Membership",
    "MembershipScopeAssignment",
    "MembershipStatus",
    "Organization",
    "OrganizationStatus",
    "TenantDeletionRequest",
    "TenantExportRequest",
]


if TYPE_CHECKING:
    from apps.platform.organizations.models import (
        Membership,
        MembershipStatus,
        Organization,
        OrganizationStatus,
        TenantDeletionRequest,
        TenantExportRequest,
    )
    from apps.platform.organizations.scope_models import MembershipScopeAssignment


_EXPORTS: dict[str, tuple[str, str]] = {
    "Membership": ("apps.platform.organizations.models", "Membership"),
    "MembershipStatus": ("apps.platform.organizations.models", "MembershipStatus"),
    "Organization": ("apps.platform.organizations.models", "Organization"),
    "OrganizationStatus": ("apps.platform.organizations.models", "OrganizationStatus"),
    "TenantDeletionRequest": (
        "apps.platform.organizations.models",
        "TenantDeletionRequest",
    ),
    "TenantExportRequest": (
        "apps.platform.organizations.models",
        "TenantExportRequest",
    ),
    "MembershipScopeAssignment": (
        "apps.platform.organizations.scope_models",
        "MembershipScopeAssignment",
    ),
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
