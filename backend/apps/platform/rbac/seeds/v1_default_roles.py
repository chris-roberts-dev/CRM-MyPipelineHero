"""V1 default role templates (B.6.4).

Each entry describes a template role that the ``seed_v1`` migration
installs with ``organization=NULL, is_default=True, is_locked=True``.

When ``services.create_organization`` runs (I.6.6), these templates are
cloned to org-scoped Role rows so per-tenant role assignment can begin.

The ``ALL_CAPABILITIES`` sentinel below means "every non-deprecated
capability in V1_CAPABILITIES at seed time." The seed migration
expands it. New capabilities added in later seed migrations (I.6.5)
auto-extend the Owner template only; they DO NOT auto-extend templates
that materialized this sentinel at seed time.
"""

from __future__ import annotations

from typing import TypedDict

from apps.platform.rbac.seeds.v1_capabilities import V1_CAPABILITIES


class V1DefaultRoleDef(TypedDict, total=False):
    code: str
    name: str
    description: str
    is_scoped_role: bool
    capabilities: list[str]


# Sentinel — replaced by the seed migration with every code in V1_CAPABILITIES.
ALL_CAPABILITIES: list[str] = [c["code"] for c in V1_CAPABILITIES]


# Convenience: every capability that ends in `.view` or `.view_all`.
_VIEW_CAPABILITIES: list[str] = [
    c["code"]
    for c in V1_CAPABILITIES
    if c["code"].endswith(".view") or c["code"].endswith(".view_all")
]


V1_DEFAULT_ROLES: list[V1DefaultRoleDef] = [
    # 1. Owner — every capability.
    {
        "code": "owner",
        "name": "Owner",
        "description": "Tenant account owner. Holds every capability.",
        "is_scoped_role": False,
        "capabilities": list(ALL_CAPABILITIES),
    },
    # 2. Org Admin — every capability (B.6.4 says "all except platform-level";
    #    no platform-level capabilities exist in the v1 tenant capability set).
    {
        "code": "org_admin",
        "name": "Org Admin",
        "description": "Office / operations manager. All tenant capabilities.",
        "is_scoped_role": False,
        "capabilities": list(ALL_CAPABILITIES),
    },
    # 3. Regional Manager — same capability set as Org Admin, scoped by Region.
    {
        "code": "regional_manager",
        "name": "Regional Manager",
        "description": "Regional manager. All non-platform capabilities, "
        "restricted to assigned Region scope (B.2.5).",
        "is_scoped_role": True,
        "capabilities": list(ALL_CAPABILITIES),
    },
    # 4. Market Manager — same, scoped by Market.
    {
        "code": "market_manager",
        "name": "Market Manager",
        "description": "Market manager. All non-platform capabilities, "
        "restricted to assigned Market scope (B.2.5).",
        "is_scoped_role": True,
        "capabilities": list(ALL_CAPABILITIES),
    },
    # 5. Location Manager — same, scoped by Location.
    {
        "code": "location_manager",
        "name": "Location Manager",
        "description": "Location manager. All non-platform capabilities, "
        "restricted to assigned Location scope (B.2.5).",
        "is_scoped_role": True,
        "capabilities": list(ALL_CAPABILITIES),
    },
    # 6. Sales Staff — per B.6.4 plus client contacts/locations management
    #    (D2 follow-up: explicit user direction).
    {
        "code": "sales_staff",
        "name": "Sales Staff",
        "description": "Salespeople. Lead-to-quote workflow plus tasks "
        "and communications.",
        "is_scoped_role": False,
        "capabilities": [
            # leads.*
            "leads.view",
            "leads.create",
            "leads.edit",
            "leads.edit_any",
            "leads.archive",
            "leads.convert",
            "leads.assign",
            # quotes selected verbs
            "quotes.view",
            "quotes.create",
            "quotes.edit",
            "quotes.send",
            # clients selected verbs + contacts/locations management
            "clients.view",
            "clients.create",
            "clients.edit",
            "clients.contacts.manage",
            "clients.locations.manage",
            # tasks.*
            "tasks.view",
            "tasks.create",
            "tasks.edit",
            "tasks.assign",
            "tasks.complete",
            "tasks.manage",
            # communications.*
            "communications.view",
            "communications.log",
            "communications.send",
            "communications.manage",
            # read access into downstream domains
            "orders.view",
            "catalog.view",
            "pricing.rules.view",
            "pricing.approval.request",
        ],
    },
    # 7. Service Staff — per B.6.4. Object-level "own WO/task" enforcement
    #    happens at the view/RBAC layer, not by capability slicing.
    {
        "code": "service_staff",
        "name": "Service Staff",
        "description": "Field service worker. Own work orders and tasks.",
        "is_scoped_role": False,
        "capabilities": [
            "workorders.view",
            "workorders.update_status",
            "workorders.complete",
            "tasks.view",
            "tasks.complete",
            "communications.view",
            "communications.log",
        ],
    },
    # 8. Production Staff — per B.6.4. Object-level "own build/task"
    #    enforcement at view layer.
    {
        "code": "production_staff",
        "name": "Production Staff",
        "description": "Shop floor. Own build orders and tasks.",
        "is_scoped_role": False,
        "capabilities": [
            "build.view",
            "build.manage",
            "build.labor.record",
            "tasks.view",
            "tasks.complete",
        ],
    },
    # 9. Pricing Manager — per B.6.4.
    {
        "code": "pricing_manager",
        "name": "Pricing Manager",
        "description": "Pricing and contract administrator.",
        "is_scoped_role": False,
        "capabilities": [
            "catalog.view",
            # All pricing capabilities
            "pricing.rules.view",
            "pricing.rules.manage",
            "pricing.price_lists.manage",
            "pricing.contracts.manage",
            "pricing.labor_rates.manage",
            "pricing.segments.manage",
            "pricing.promotions.manage",
            "pricing.bundles.manage",
            "pricing.approval.request",
            "pricing.approval.grant",
            # Quote line economics
            "quotes.view",
            "quotes.edit",
            "quotes.line.override_price",
            "quotes.line.apply_discount",
        ],
    },
    # 10. Billing Staff — per B.6.4.
    {
        "code": "billing_staff",
        "name": "Billing Staff",
        "description": "Accounts receivable.",
        "is_scoped_role": False,
        "capabilities": [
            # All billing capabilities
            "billing.view",
            "billing.invoice.create",
            "billing.invoice.send",
            "billing.invoice.void",
            "billing.payment.record",
            "billing.payment.edit",
            "billing.reports.view",
            # Supporting reads
            "clients.view",
            "orders.view",
            # Limited task surface
            "tasks.view",
            "tasks.create",
        ],
    },
    # 11. Viewer — every *.view / *.view_all capability.
    {
        "code": "viewer",
        "name": "Viewer",
        "description": "Read-only stakeholder.",
        "is_scoped_role": False,
        "capabilities": list(_VIEW_CAPABILITIES),
    },
]
