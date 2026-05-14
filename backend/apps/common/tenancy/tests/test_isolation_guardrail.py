"""B.1.7 tenant-isolation CI guardrail.

This test is the codified shape of B.1.7. It walks every model
registered with Django and asserts the tenant-isolation invariants on
the ones flagged with ``is_tenant_owned = True``.

The test is BLOCKING in CI from M1 D1 onward. Adding a model that
declares ``is_tenant_owned = True`` without wiring up TenantManager
and the ``organization`` FK MUST fail the build. That is the entire
point.

Note on the discriminant attribute: ``is_tenant_owned`` is declared on
:class:`apps.common.tenancy.models.TenantOwnedModel` and inherited by
every subclass. A non-subclass that sets the attribute manually is a
bug — the guardrail still fires on it, which is correct.
"""

from __future__ import annotations

from typing import Any

from django.apps import apps
from django.db import models

from apps.common.tenancy.managers import TenantManager
from apps.common.tenancy.models import TenantOwnedModel


def _is_tenant_owned(model: type[models.Model]) -> bool:
    return getattr(model, "is_tenant_owned", False) is True


def _has_organization_fk(model: type[models.Model]) -> bool:
    """True iff the model has a field named ``organization`` that is a FK."""
    try:
        field = model._meta.get_field("organization")
    except Exception:
        return False
    return isinstance(field, models.ForeignKey)


def _organization_fk_target(model: type[models.Model]) -> str:
    """Return the model label that the ``organization`` FK targets."""
    field = model._meta.get_field("organization")
    if not isinstance(field, models.ForeignKey):
        return ""
    return field.related_model._meta.label  # type: ignore[union-attr]


def _organization_fk_on_delete(model: type[models.Model]) -> Any:
    """Return the on_delete callable for the ``organization`` FK."""
    field = model._meta.get_field("organization")
    if not isinstance(field, models.ForeignKey):
        return None
    return field.remote_field.on_delete


# ---------------------------------------------------------------------------
# B.1.7 — every tenant-owned model uses TenantManager
# ---------------------------------------------------------------------------


def test_every_tenant_owned_model_uses_tenant_manager() -> None:
    offenders: list[str] = []
    for model in apps.get_models():
        if not _is_tenant_owned(model):
            continue
        manager = model._default_manager
        if not isinstance(manager, TenantManager):
            offenders.append(
                f"{model._meta.label}: default manager is "
                f"{type(manager).__name__}, expected TenantManager."
            )
    assert not offenders, (
        "Tenant-isolation guardrail (B.1.7) failed. The following models "
        "declare is_tenant_owned=True but do not use TenantManager:\n  - "
        + "\n  - ".join(offenders)
    )


# ---------------------------------------------------------------------------
# B.1.7 — every tenant-owned model has an organization FK
# ---------------------------------------------------------------------------


def test_every_tenant_owned_model_has_organization_fk() -> None:
    offenders: list[str] = []
    for model in apps.get_models():
        if not _is_tenant_owned(model):
            continue
        if not _has_organization_fk(model):
            offenders.append(f"{model._meta.label}: missing `organization` ForeignKey.")
    assert not offenders, (
        "Tenant-isolation guardrail (B.1.7) failed. The following models "
        "declare is_tenant_owned=True but lack an `organization` FK:\n  - "
        + "\n  - ".join(offenders)
    )


# ---------------------------------------------------------------------------
# Stronger invariant: the FK must target the canonical Organization model
# ---------------------------------------------------------------------------


def test_every_tenant_owned_model_organization_fk_targets_canonical_org() -> None:
    """Tenant-owned models MUST reference the canonical Organization.

    B.1.3 explicitly names ``platform_organizations.Organization`` as
    the target. Catching the wrong target here prevents accidental
    references to a future "OrgLite" or shadow model.
    """
    expected = "platform_organizations.Organization"
    offenders: list[str] = []
    for model in apps.get_models():
        if not _is_tenant_owned(model):
            continue
        if not _has_organization_fk(model):
            continue  # caught by the sibling test
        target = _organization_fk_target(model)
        if target != expected:
            offenders.append(
                f"{model._meta.label}: organization FK targets {target!r}, "
                f"expected {expected!r}."
            )
    assert not offenders, (
        "Tenant-isolation guardrail (B.1.7) failed. The following models "
        "point their `organization` FK at the wrong target:\n  - "
        + "\n  - ".join(offenders)
    )


# ---------------------------------------------------------------------------
# Stronger invariant: organization FK must be on_delete=PROTECT
# ---------------------------------------------------------------------------


def test_every_tenant_owned_model_organization_fk_is_protect() -> None:
    """B.1.3 mandates ``on_delete=PROTECT`` for tenant-owned ``organization`` FKs.

    Tenant deletion is a multi-stage workflow (G.7.3); a CASCADE on the
    organization FK would let a stray ``Organization.delete()`` silently
    take out tenant data without going through that workflow.
    """
    offenders: list[str] = []
    for model in apps.get_models():
        if not _is_tenant_owned(model):
            continue
        if not _has_organization_fk(model):
            continue
        on_delete = _organization_fk_on_delete(model)
        if on_delete is not models.PROTECT:
            offenders.append(
                f"{model._meta.label}: organization FK on_delete is "
                f"{on_delete.__name__}, expected PROTECT."
            )
    assert not offenders, (
        "Tenant-isolation guardrail (B.1.7) failed. The following models "
        "do not use on_delete=PROTECT on the `organization` FK:\n  - "
        + "\n  - ".join(offenders)
    )


# ---------------------------------------------------------------------------
# Anchor invariants on the primitives themselves
# ---------------------------------------------------------------------------


def test_organization_is_not_tenant_owned() -> None:
    """The Organization model IS the tenant; it MUST NOT carry the flag."""
    Organization = apps.get_model("platform_organizations", "Organization")
    assert getattr(Organization, "is_tenant_owned", False) is False, (
        "Organization MUST NOT inherit from TenantOwnedModel. It is the "
        "tenant root, not a tenant-owned record."
    )
    assert not issubclass(
        Organization, TenantOwnedModel
    ), "Organization MUST NOT be a subclass of TenantOwnedModel."


def test_user_is_not_tenant_owned() -> None:
    """User is platform-tier identity, not tenant-owned (B.3.1)."""
    User = apps.get_model("platform_accounts", "User")
    assert getattr(User, "is_tenant_owned", False) is False


def test_membership_is_not_tenant_owned() -> None:
    """Membership is the JOIN row; it is org-scoped but not TenantOwnedModel.

    Tenant authorization flows through Membership; the platform console
    queries it across tenants. See the developer primer in
    apps.common.tenancy.__init__ for the rationale.
    """
    Membership = apps.get_model("platform_organizations", "Membership")
    assert getattr(Membership, "is_tenant_owned", False) is False


def test_capability_and_role_are_not_tenant_owned() -> None:
    """RBAC tables are platform-tier; they are NOT TenantOwnedModel."""
    Capability = apps.get_model("platform_rbac", "Capability")
    Role = apps.get_model("platform_rbac", "Role")
    assert getattr(Capability, "is_tenant_owned", False) is False
    assert getattr(Role, "is_tenant_owned", False) is False


def test_tenant_manager_does_not_run_in_migrations() -> None:
    """TenantManager.use_in_migrations is False per B.1.4."""
    assert TenantManager.use_in_migrations is False


def test_tenant_owned_model_is_abstract() -> None:
    """The base class itself must remain abstract."""
    assert TenantOwnedModel._meta.abstract is True


def test_tenant_owned_model_has_organization_fk_declaration() -> None:
    """Sanity-check the abstract base's own FK declaration."""
    field = TenantOwnedModel._meta.get_field("organization")
    assert isinstance(field, models.ForeignKey)
    assert field.remote_field.on_delete is models.PROTECT
    assert field.remote_field.model == "platform_organizations.Organization"
