"""V1 capability registry (B.6.3).

Each entry is a dict with the shape:

    {
        "code": "leads.view",
        "name": "View leads",
        "description": "Read access to lead records.",
        "category": "Lead Management",
    }

Codes are stable contract strings. Renames are breaking changes
(propagation policy: B.6.5/B.6.6).
"""

from __future__ import annotations

from typing import TypedDict


class V1CapabilityDef(TypedDict):
    code: str
    name: str
    description: str
    category: str


V1_CAPABILITIES: list[V1CapabilityDef] = [
    # --- Lead Management ------------------------------------------------
    {
        "code": "leads.view",
        "name": "View leads",
        "description": "Read access to lead records.",
        "category": "Lead Management",
    },
    {
        "code": "leads.create",
        "name": "Create leads",
        "description": "Create new lead records.",
        "category": "Lead Management",
    },
    {
        "code": "leads.edit",
        "name": "Edit own leads",
        "description": "Edit leads assigned to the acting member.",
        "category": "Lead Management",
    },
    {
        "code": "leads.edit_any",
        "name": "Edit any lead",
        "description": "Edit leads regardless of ownership.",
        "category": "Lead Management",
    },
    {
        "code": "leads.archive",
        "name": "Archive leads",
        "description": "Move leads to the archived terminal state.",
        "category": "Lead Management",
    },
    {
        "code": "leads.convert",
        "name": "Convert lead to quote",
        "description": "Convert a qualified lead to a quote.",
        "category": "Lead Management",
    },
    {
        "code": "leads.assign",
        "name": "Assign leads",
        "description": "Change lead ownership.",
        "category": "Lead Management",
    },
    # --- Quote Management -----------------------------------------------
    {
        "code": "quotes.view",
        "name": "View quotes",
        "description": "Read access to quotes and quote versions.",
        "category": "Quote Management",
    },
    {
        "code": "quotes.create",
        "name": "Create quotes",
        "description": "Create new quotes and DRAFT quote versions.",
        "category": "Quote Management",
    },
    {
        "code": "quotes.edit",
        "name": "Edit DRAFT quotes",
        "description": "Edit DRAFT quote versions and their lines.",
        "category": "Quote Management",
    },
    {
        "code": "quotes.send",
        "name": "Send quotes",
        "description": "Transition a DRAFT quote version to SENT.",
        "category": "Quote Management",
    },
    {
        "code": "quotes.retract",
        "name": "Retract sent quotes",
        "description": "Retract a SENT quote version.",
        "category": "Quote Management",
    },
    {
        "code": "quotes.approve",
        "name": "Accept quotes",
        "description": "Accept a SENT quote, creating a Sales Order.",
        "category": "Quote Management",
    },
    {
        "code": "quotes.decline",
        "name": "Decline quotes",
        "description": "Mark a SENT quote as declined.",
        "category": "Quote Management",
    },
    {
        "code": "quotes.line.override_price",
        "name": "Override quote line price",
        "description": "Apply a manual price override to a quote line.",
        "category": "Quote Management",
    },
    {
        "code": "quotes.line.apply_discount",
        "name": "Apply quote line discount",
        "description": "Apply a discount modifier to a quote line.",
        "category": "Quote Management",
    },
    {
        "code": "quotes.delete_draft",
        "name": "Delete DRAFT quote versions",
        "description": "Hard-delete a DRAFT quote version.",
        "category": "Quote Management",
    },
    # --- Client Management ----------------------------------------------
    {
        "code": "clients.view",
        "name": "View clients",
        "description": "Read access to client records.",
        "category": "Client Management",
    },
    {
        "code": "clients.create",
        "name": "Create clients",
        "description": "Create new client records.",
        "category": "Client Management",
    },
    {
        "code": "clients.edit",
        "name": "Edit clients",
        "description": "Edit client records.",
        "category": "Client Management",
    },
    {
        "code": "clients.merge",
        "name": "Merge clients",
        "description": "Merge duplicate client records.",
        "category": "Client Management",
    },
    {
        "code": "clients.deactivate",
        "name": "Deactivate clients",
        "description": "Move clients to the INACTIVE status.",
        "category": "Client Management",
    },
    {
        "code": "clients.contacts.manage",
        "name": "Manage client contacts",
        "description": "Add/edit/remove client contact records.",
        "category": "Client Management",
    },
    {
        "code": "clients.locations.manage",
        "name": "Manage client locations",
        "description": "Add/edit/remove client location records.",
        "category": "Client Management",
    },
    # --- Sales Order ----------------------------------------------------
    {
        "code": "orders.view",
        "name": "View sales orders",
        "description": "Read access to sales orders.",
        "category": "Sales Order",
    },
    {
        "code": "orders.edit",
        "name": "Edit sales orders",
        "description": "Edit sales-order header fields where permitted.",
        "category": "Sales Order",
    },
    {
        "code": "orders.cancel",
        "name": "Cancel sales orders",
        "description": "Cancel a sales order.",
        "category": "Sales Order",
    },
    {
        "code": "orders.generate_fulfillment",
        "name": "Generate fulfillment",
        "description": "Trigger fulfillment dispatch for a sales order.",
        "category": "Sales Order",
    },
    # --- Catalog --------------------------------------------------------
    {
        "code": "catalog.view",
        "name": "View catalog",
        "description": "Read access to services, products, materials, and BOMs.",
        "category": "Catalog",
    },
    {
        "code": "catalog.services.manage",
        "name": "Manage services",
        "description": "Add/edit/retire service catalog items.",
        "category": "Catalog",
    },
    {
        "code": "catalog.products.manage",
        "name": "Manage products",
        "description": "Add/edit/retire product catalog items.",
        "category": "Catalog",
    },
    {
        "code": "catalog.materials.manage",
        "name": "Manage materials",
        "description": "Add/edit/retire material catalog items.",
        "category": "Catalog",
    },
    {
        "code": "catalog.suppliers.manage",
        "name": "Manage suppliers",
        "description": "Add/edit/retire supplier records.",
        "category": "Catalog",
    },
    {
        "code": "catalog.bom.manage",
        "name": "Manage BOMs",
        "description": "Add/edit/version bills of materials.",
        "category": "Catalog",
    },
    # --- Pricing --------------------------------------------------------
    {
        "code": "pricing.rules.view",
        "name": "View pricing rules",
        "description": "Read access to pricing rule definitions.",
        "category": "Pricing",
    },
    {
        "code": "pricing.rules.manage",
        "name": "Manage pricing rules",
        "description": "Add/edit/retire pricing rules.",
        "category": "Pricing",
    },
    {
        "code": "pricing.price_lists.manage",
        "name": "Manage price lists",
        "description": "Add/edit price lists and price list items.",
        "category": "Pricing",
    },
    {
        "code": "pricing.contracts.manage",
        "name": "Manage client contracts",
        "description": "Add/edit client-specific contract pricing.",
        "category": "Pricing",
    },
    {
        "code": "pricing.labor_rates.manage",
        "name": "Manage labor rate cards",
        "description": "Add/edit labor rate cards and rate lines.",
        "category": "Pricing",
    },
    {
        "code": "pricing.segments.manage",
        "name": "Manage customer segments",
        "description": "Add/edit customer segments used by pricing.",
        "category": "Pricing",
    },
    {
        "code": "pricing.promotions.manage",
        "name": "Manage promotions",
        "description": "Add/edit promotion campaigns.",
        "category": "Pricing",
    },
    {
        "code": "pricing.bundles.manage",
        "name": "Manage bundles",
        "description": "Add/edit bundle definitions and components.",
        "category": "Pricing",
    },
    {
        "code": "pricing.approval.request",
        "name": "Request pricing approval",
        "description": "Submit a quote line for pricing-manager approval.",
        "category": "Pricing",
    },
    {
        "code": "pricing.approval.grant",
        "name": "Grant pricing approval",
        "description": "Approve or reject a pricing approval request.",
        "category": "Pricing",
    },
    # --- Work Order -----------------------------------------------------
    {
        "code": "workorders.view",
        "name": "View own work orders",
        "description": "Read access to work orders assigned to the acting member.",
        "category": "Work Order",
    },
    {
        "code": "workorders.assign",
        "name": "Assign work orders",
        "description": "Assign work orders to service staff.",
        "category": "Work Order",
    },
    {
        "code": "workorders.update_status",
        "name": "Update work-order status",
        "description": "Transition a work order through service states.",
        "category": "Work Order",
    },
    {
        "code": "workorders.manage",
        "name": "Manage work orders",
        "description": "Edit work-order header fields and lines.",
        "category": "Work Order",
    },
    {
        "code": "workorders.complete",
        "name": "Complete work orders",
        "description": "Mark a work order as completed with outcome notes.",
        "category": "Work Order",
    },
    {
        "code": "workorders.view_all",
        "name": "View all work orders",
        "description": "Read access to work orders regardless of assignment.",
        "category": "Work Order",
    },
    # --- Purchase Order -------------------------------------------------
    {
        "code": "purchasing.view",
        "name": "View purchase orders",
        "description": "Read access to purchase orders.",
        "category": "Purchase Order",
    },
    {
        "code": "purchasing.create",
        "name": "Create purchase orders",
        "description": "Create new purchase orders.",
        "category": "Purchase Order",
    },
    {
        "code": "purchasing.edit",
        "name": "Edit purchase orders",
        "description": "Edit DRAFT purchase-order fields and lines.",
        "category": "Purchase Order",
    },
    {
        "code": "purchasing.submit",
        "name": "Submit purchase orders",
        "description": "Submit a DRAFT purchase order to a supplier.",
        "category": "Purchase Order",
    },
    {
        "code": "purchasing.receive",
        "name": "Receive purchase-order lines",
        "description": "Record receipts against purchase-order lines.",
        "category": "Purchase Order",
    },
    {
        "code": "purchasing.cancel",
        "name": "Cancel purchase orders",
        "description": "Cancel a purchase order where permitted by state.",
        "category": "Purchase Order",
    },
    # --- Build Order ----------------------------------------------------
    {
        "code": "build.view",
        "name": "View own build orders",
        "description": "Read access to build orders assigned to the acting member.",
        "category": "Build Order",
    },
    {
        "code": "build.manage",
        "name": "Manage build orders",
        "description": "Create, start, and progress build orders.",
        "category": "Build Order",
    },
    {
        "code": "build.labor.record",
        "name": "Record build labor",
        "description": "Log labor entries against a build order.",
        "category": "Build Order",
    },
    {
        "code": "build.labor.edit_any",
        "name": "Edit any build labor entry",
        "description": "Adjust build-labor entries regardless of authorship.",
        "category": "Build Order",
    },
    {
        "code": "build.qa.review",
        "name": "Review build QA",
        "description": "Submit and adjudicate build QA reviews.",
        "category": "Build Order",
    },
    {
        "code": "build.cost.view",
        "name": "View build cost detail",
        "description": "Read access to actual vs estimated cost detail.",
        "category": "Build Order",
    },
    # --- Billing --------------------------------------------------------
    {
        "code": "billing.view",
        "name": "View billing",
        "description": "Read access to invoices and payments.",
        "category": "Billing",
    },
    {
        "code": "billing.invoice.create",
        "name": "Create invoices",
        "description": "Create invoices from sales-order activity.",
        "category": "Billing",
    },
    {
        "code": "billing.invoice.send",
        "name": "Send invoices",
        "description": "Send a DRAFT invoice to the client.",
        "category": "Billing",
    },
    {
        "code": "billing.invoice.void",
        "name": "Void invoices",
        "description": "Void an invoice with zero non-reversed allocations.",
        "category": "Billing",
    },
    {
        "code": "billing.payment.record",
        "name": "Record payments",
        "description": "Record a payment received from a client.",
        "category": "Billing",
    },
    {
        "code": "billing.payment.edit",
        "name": "Edit payment allocations",
        "description": "Reverse / re-allocate payment applications.",
        "category": "Billing",
    },
    {
        "code": "billing.reports.view",
        "name": "View billing reports",
        "description": "Read access to billing reports (A/R aging, etc.).",
        "category": "Billing",
    },
    # --- Tasks ----------------------------------------------------------
    {
        "code": "tasks.view",
        "name": "View own tasks",
        "description": "Read access to tasks assigned to the acting member.",
        "category": "Tasks",
    },
    {
        "code": "tasks.create",
        "name": "Create tasks",
        "description": "Create new tasks.",
        "category": "Tasks",
    },
    {
        "code": "tasks.edit",
        "name": "Edit own tasks",
        "description": "Edit tasks assigned to the acting member.",
        "category": "Tasks",
    },
    {
        "code": "tasks.assign",
        "name": "Assign tasks",
        "description": "Reassign tasks to other members.",
        "category": "Tasks",
    },
    {
        "code": "tasks.complete",
        "name": "Complete tasks",
        "description": "Mark a task as completed.",
        "category": "Tasks",
    },
    {
        "code": "tasks.manage",
        "name": "Manage any task",
        "description": "Edit/assign/cancel tasks regardless of ownership.",
        "category": "Tasks",
    },
    # --- Communications -------------------------------------------------
    {
        "code": "communications.view",
        "name": "View communications",
        "description": "Read access to communication logs.",
        "category": "Communications",
    },
    {
        "code": "communications.log",
        "name": "Log communications",
        "description": "Record a communication touchpoint (call/email/note).",
        "category": "Communications",
    },
    {
        "code": "communications.send",
        "name": "Send communications",
        "description": "Send outbound emails through MyPipelineHero.",
        "category": "Communications",
    },
    {
        "code": "communications.manage",
        "name": "Manage communications",
        "description": "Edit and reassign existing communication records.",
        "category": "Communications",
    },
    # --- Reporting ------------------------------------------------------
    {
        "code": "reporting.view",
        "name": "View reports",
        "description": "Read access to the fixed v1 report catalog.",
        "category": "Reporting",
    },
    {
        "code": "reporting.export",
        "name": "Export reports",
        "description": "Run report exports to CSV / archive.",
        "category": "Reporting",
    },
    {
        "code": "reporting.advanced",
        "name": "Run advanced reports",
        "description": "Access reports flagged as advanced / restricted.",
        "category": "Reporting",
    },
    # --- Tenant Administration ------------------------------------------
    {
        "code": "admin.members.view",
        "name": "View members",
        "description": "Read access to members of the organization.",
        "category": "Tenant Administration",
    },
    {
        "code": "admin.members.invite",
        "name": "Invite members",
        "description": "Send membership invitations.",
        "category": "Tenant Administration",
    },
    {
        "code": "admin.members.deactivate",
        "name": "Deactivate members",
        "description": "Move memberships to INACTIVE.",
        "category": "Tenant Administration",
    },
    {
        "code": "admin.members.suspend",
        "name": "Suspend members",
        "description": "Move memberships to SUSPENDED with a reason.",
        "category": "Tenant Administration",
    },
    {
        "code": "admin.roles.view",
        "name": "View roles",
        "description": "Read access to organization roles.",
        "category": "Tenant Administration",
    },
    {
        "code": "admin.roles.manage",
        "name": "Manage roles",
        "description": "Add/edit/retire custom (tenant-defined) roles.",
        "category": "Tenant Administration",
    },
    {
        "code": "admin.roles.assign",
        "name": "Assign roles",
        "description": "Attach roles to memberships.",
        "category": "Tenant Administration",
    },
    {
        "code": "admin.capabilities.grant",
        "name": "Grant/deny capabilities",
        "description": "Apply per-membership capability overrides.",
        "category": "Tenant Administration",
    },
    {
        "code": "admin.org.settings",
        "name": "Manage organization settings",
        "description": "Edit organization profile and global settings.",
        "category": "Tenant Administration",
    },
    {
        "code": "admin.numbering.configure",
        "name": "Configure entity numbering",
        "description": "Edit numbering prefixes and sequence configuration.",
        "category": "Tenant Administration",
    },
    {
        "code": "admin.export.request",
        "name": "Request data export",
        "description": "Request and download tenant data exports (G.7.2).",
        "category": "Tenant Administration",
    },
    {
        "code": "admin.deletion.request",
        "name": "Request tenant deletion",
        "description": "Request or cancel tenant deletion (G.7.3); sensitive.",
        "category": "Tenant Administration",
    },
    {
        "code": "admin.audit.view",
        "name": "View audit log",
        "description": "Read access to the tenant audit event log.",
        "category": "Tenant Administration",
    },
    # --- Tax Configuration ----------------------------------------------
    {
        "code": "tax.jurisdictions.manage",
        "name": "Manage tax jurisdictions",
        "description": "Add/edit tax jurisdictions and rate components.",
        "category": "Tax Configuration",
    },
]
