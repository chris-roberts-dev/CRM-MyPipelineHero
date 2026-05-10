"""Seed-v1 verification tests.

Covers J.2.4 exit criterion #6 plus the M0/M1 RBAC-bootstrap assertions:

* exactly one is_system=True user exists after seed runs
* all V1 capabilities exist after seed runs
* all 11 default role templates exist with their expected capability sets
* re-running the migration is a no-op (idempotency)

These tests rely on Django's migration framework having already executed
``0002_seed_v1`` before the test session begins (pytest-django's
``--reuse-db`` keeps the seeded DB warm).
"""

from __future__ import annotations

import pytest
from django.apps import apps as django_apps
from django.contrib.auth import get_user_model

from apps.platform.rbac.migrations._seed_runner import run_seed_v1_now
from apps.platform.rbac.seeds.v1_capabilities import V1_CAPABILITIES
from apps.platform.rbac.seeds.v1_default_roles import V1_DEFAULT_ROLES

SYSTEM_USER_EMAIL = "system@mypipelinehero.internal"


@pytest.fixture
def capability_model():
    return django_apps.get_model("platform_rbac", "Capability")


@pytest.fixture
def role_model():
    return django_apps.get_model("platform_rbac", "Role")


@pytest.fixture
def role_capability_model():
    return django_apps.get_model("platform_rbac", "RoleCapability")


# ---------------------------------------------------------------------------
# 1. System User
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_exactly_one_system_user_exists() -> None:
    User = get_user_model()
    system_users = User.objects.filter(is_system=True)
    assert system_users.count() == 1
    user = system_users.get()
    assert user.email == SYSTEM_USER_EMAIL
    assert user.is_active is True
    assert user.is_staff is False
    assert user.is_superuser is False
    # Unusable password sentinel — has_usable_password() must return False.
    assert user.has_usable_password() is False


# ---------------------------------------------------------------------------
# 2. Capabilities
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_all_v1_capabilities_exist(capability_model) -> None:
    expected_codes = {c["code"] for c in V1_CAPABILITIES}
    actual_codes = set(capability_model.objects.values_list("code", flat=True))
    assert (
        expected_codes <= actual_codes
    ), f"Missing capabilities: {expected_codes - actual_codes}"


@pytest.mark.django_db
def test_capability_count_matches_v1_registry(capability_model) -> None:
    assert capability_model.objects.count() == len(V1_CAPABILITIES)


@pytest.mark.django_db
def test_capability_metadata_matches_registry(capability_model) -> None:
    by_code = {c.code: c for c in capability_model.objects.all()}
    for cap_def in V1_CAPABILITIES:
        cap = by_code[cap_def["code"]]
        assert cap.name == cap_def["name"]
        assert cap.description == cap_def["description"]
        assert cap.category == cap_def["category"]


# ---------------------------------------------------------------------------
# 3. Default role templates
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_eleven_default_role_templates_exist(role_model) -> None:
    templates = role_model.objects.filter(organization__isnull=True, is_default=True)
    assert templates.count() == 11


@pytest.mark.django_db
def test_each_role_template_has_expected_capability_set(
    role_model, role_capability_model
) -> None:
    for role_def in V1_DEFAULT_ROLES:
        role = role_model.objects.get(organization__isnull=True, code=role_def["code"])
        assert role.is_default is True
        assert role.is_locked is True
        assert role.is_scoped_role is role_def.get("is_scoped_role", False)

        actual_codes = set(
            role_capability_model.objects.filter(role=role).values_list(
                "capability__code", flat=True
            )
        )
        expected_codes = set(role_def["capabilities"])
        assert actual_codes == expected_codes, (
            f"Role {role.code}: "
            f"missing={expected_codes - actual_codes}, "
            f"extra={actual_codes - expected_codes}"
        )


@pytest.mark.django_db
def test_no_per_tenant_roles_created_by_seed(role_model) -> None:
    """Per-tenant Owner/Org Admin/etc. roles are created by
    services.create_organization (I.6.6), NOT by the seed migration."""
    assert role_model.objects.filter(organization__isnull=False).count() == 0


# ---------------------------------------------------------------------------
# 4. Idempotency
# ---------------------------------------------------------------------------


@pytest.mark.django_db(transaction=True)
def test_reapplying_seed_is_idempotent(
    capability_model, role_model, role_capability_model
) -> None:
    cap_count_before = capability_model.objects.count()
    role_count_before = role_model.objects.count()
    rolecap_count_before = role_capability_model.objects.count()

    User = get_user_model()
    system_user_count_before = User.objects.filter(is_system=True).count()

    run_seed_v1_now()

    assert capability_model.objects.count() == cap_count_before
    assert role_model.objects.count() == role_count_before
    assert role_capability_model.objects.count() == rolecap_count_before
    assert User.objects.filter(is_system=True).count() == system_user_count_before


# ---------------------------------------------------------------------------
# 5. Spot-checks per B.6.4 role descriptions
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_owner_role_has_every_capability(
    role_model, role_capability_model, capability_model
) -> None:
    owner = role_model.objects.get(organization__isnull=True, code="owner")
    owner_caps = set(
        role_capability_model.objects.filter(role=owner).values_list(
            "capability__code", flat=True
        )
    )
    every_cap = set(capability_model.objects.values_list("code", flat=True))
    assert owner_caps == every_cap


@pytest.mark.django_db
def test_regional_market_location_managers_are_scoped(role_model) -> None:
    for code in ("regional_manager", "market_manager", "location_manager"):
        role = role_model.objects.get(organization__isnull=True, code=code)
        assert role.is_scoped_role is True


@pytest.mark.django_db
def test_viewer_only_holds_view_capabilities(role_model, role_capability_model) -> None:
    viewer = role_model.objects.get(organization__isnull=True, code="viewer")
    codes = role_capability_model.objects.filter(role=viewer).values_list(
        "capability__code", flat=True
    )
    for c in codes:
        assert c.endswith(
            (".view", ".view_all")
        ), f"Viewer should not hold non-view capability: {c}"


@pytest.mark.django_db
def test_sales_staff_can_request_pricing_approval_but_not_grant(
    role_model, role_capability_model
) -> None:
    sales = role_model.objects.get(organization__isnull=True, code="sales_staff")
    codes = set(
        role_capability_model.objects.filter(role=sales).values_list(
            "capability__code", flat=True
        )
    )
    assert "pricing.approval.request" in codes
    assert "pricing.approval.grant" not in codes


@pytest.mark.django_db
def test_pricing_manager_can_grant_pricing_approval(
    role_model, role_capability_model
) -> None:
    pm = role_model.objects.get(organization__isnull=True, code="pricing_manager")
    codes = set(
        role_capability_model.objects.filter(role=pm).values_list(
            "capability__code", flat=True
        )
    )
    assert "pricing.approval.grant" in codes
    assert "quotes.line.override_price" in codes


@pytest.mark.django_db
def test_billing_staff_can_void_invoices(role_model, role_capability_model) -> None:
    bs = role_model.objects.get(organization__isnull=True, code="billing_staff")
    codes = set(
        role_capability_model.objects.filter(role=bs).values_list(
            "capability__code", flat=True
        )
    )
    assert "billing.invoice.void" in codes
