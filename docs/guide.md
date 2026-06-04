# MyPipelineHero — Technical Development Guide (MVP)

**Version:** 1.0 (MVP build specification)  
**Status:** Complete — all 22 sections  
**Authority:** NORMATIVE where labeled. This guide is the single source of truth for the MVP build.  

---
## Table of Contents
- [MyPipelineHero CRM — Technical Development Guide](#mypipelinehero--technical-development-guide-mvp)
  - [Section 1: Front Matter](#section-1--front-matter)
  - [Section 2: Product Overview](#section-2--product-overview)
  - [Section 3: MVP Scope](#section-3--mvp-scope)
  - [Section 4: System Architecture](#section-4--system-architecture)
  - [Section 5: Multi-Tenancy](#section-5--multi-tenancy)
  - [Section 6: Tenant Onboarding](#section-6--tenant-onboarding)
  - [Section 7: Packages, Tiers, Entitlements, and Limits](#section-7--packages-tiers-entitlements-and-limits)
  - [Section 8: Identity and Access Control](#section-8--identity-and-access-control)
  - [Section 9: CRM Domain Requirements](#section-9--crm-domain-requirements)
  - [Section 10: Catalog and Pricing Requirements](#section-10--catalog-and-pricing-requirements)
  - [Section 11: Operational Workflow Requirements](#section-11--operational-workflow-requirements)
  - [Section 12: Billing Requirements](#section-12--billing-requirements)
  - [Section 13: Admin and Workflow Surfaces](#section-13--admin-and-workflow-surfaces)
  - [Section 14: Branding and UI Design System](#section-15--data-model-inventory)
  - [Section 15: Data Model Inventory](#section-15--data-model-inventory)
  - [Section 16: Service Layer Requirements](#section-16--service-layer-requirements)
  - [Section 17: Audit, Security, and Compliance](#section-17--audit-security-and-compliance)
  - [Section 18: Async and Background Jobs](#section-18--async-and-background-jobs)
  - [Section 19: Testing and Quality](#section-19--testing-and-quality)
  - [Section 20: Deployment and Operations](#section-20--deployment-and-operations)
  - [Section 21: MVP Milestones](#section-21--mvp-milestones)
  - [Section 22: Post-MVP Deferred Scope](#section-22--post-mvp-deferred-scope)

## Section 1 — Front Matter

### 1.1 Purpose

**Status: NORMATIVE.**

This document is the canonical engineering reference for the MyPipelineHero **MVP** build. It is the single source of truth for architectural decisions, the multi-tenant data model, subscription/entitlement enforcement, authentication and authorization, the CPQ pricing engine, commercial and operational state machines, async semantics, branding, and operational posture.

The MVP is a backend-first, server-rendered, multi-tenant SaaS platform built on Django. It ships a complete commercial product — not a prototype — but deliberately excludes a React front end, a public API, a payment processor, and self-service subscription management. Each of these is documented as post-MVP and, where relevant, the MVP is built so that the post-MVP transition is cheap.

Where this guide conflicts with any prior draft, this guide wins.

### 1.2 Audience

**Status: INFORMATIVE.**

- **Application engineers** building the server-rendered Django surfaces, the service layer, and the internal DRF API.
- **Platform / infrastructure engineers** operating the Docker-based DigitalOcean deployment, PostgreSQL, Redis, Celery, object storage, and observability stack.
- **QA engineers** designing and maintaining the test suite (unit, service, integration, entitlement, RBAC, pricing, state-machine, property-based).
- **Support / platform operators** using the platform console for tenant creation, plan and add-on assignment, and impersonation.
- **Security reviewers** auditing tenant isolation, Auth0 integration, authorization, entitlement enforcement, audit, and data-handling controls.
- **Product / engineering managers** scoping milestones and tracking exit criteria.

### 1.3 Authority

**Status: NORMATIVE.**

Every section header carries an authority label:

- **NORMATIVE** — implementation MUST conform. Deviation requires a guide pull request.
- **INFORMATIVE** — context, rationale, and worked examples. May be revised without a guide PR.

Tables, code skeletons, and field-level model definitions inside NORMATIVE sections are themselves NORMATIVE unless explicitly marked otherwise.

The keywords **MUST**, **MUST NOT**, **SHOULD**, **SHOULD NOT**, **MAY**, and **REQUIRED** carry their RFC 2119 meanings. A **MUST/MUST NOT** violation is a defect. A **SHOULD/SHOULD NOT** deviation requires a documented justification in the PR description.

Every guide change goes through pull-request review with at least one engineering reviewer and one product-or-architecture reviewer. A `CHANGELOG.md` adjacent to this file records all changes with date, author, version, and a one-line summary.

### 1.4 MVP Terminology

**Status: NORMATIVE.**

This guide uses **MVP** and **post-MVP** consistently. It does not use "v1," "Phase 1," or "Phase 2" to describe scope.

The word **version** is reserved exclusively for technical versioning of artifacts that carry their own version contract:

- **Pricing engine version** — the `<major>.<minor>` string identifying the deterministic pricing pipeline contract. The MVP ships engine version `"1.0"`.
- **Internal API version** — the URL segment `/api/v1/...`. The MVP ships `v1`.
- **Audit schema version** — the integer `AuditEvent.schema_version`. The MVP ships version `1`.

"MVP" describes the product scope and milestone set. "Post-MVP" describes everything deferred (Section 22). When this guide says a feature "ships in the MVP," it means the feature is delivered by milestones M0–M8.

### 1.5 Foundational Decisions (Locked)

**Status: NORMATIVE.**

These decisions are settled and bind the rest of the guide. They are recorded here so no downstream section silently contradicts them.

| # | Decision | Detail |
|---|---|---|
| 1 | **Authentication is Auth0.** | Auth0 Universal Login (OIDC) owns the login UI, credential storage, signup-at-invite, password reset, and MFA challenge. Django owns the canonical `User`, the `Auth0Identity` linkage, membership resolution, RBAC, RML scope, session establishment, cross-subdomain handoff, and audit. No locally-managed passwords or local TOTP machinery are built. `django-allauth` is not used. |
| 2 | **Subscription tiers and entitlements are MVP-core.** | Four plans (Starter, Growth, Pro, Enterprise), curated add-on packs, a stable feature-code registry, plan limits, and a two-gate enforcement model (RBAC + entitlement) ship in the MVP. Plan and add-on assignment is operator-managed in the platform console. |
| 3 | **No payment processor in the MVP.** | No Stripe/Paddle/subscription-provider integration, no self-service signup, no self-service plan changes or add-on purchases. Platform operators set plan and add-ons manually. Tenant→customer invoicing (the tenant's own billing of its customers) is a separate domain from platform SaaS subscription billing. |
| 4 | **Server-rendered front end; no React in the MVP.** | The tenant portal, platform console, custom tenant admin, auth pages, and landing page are Django templates + Tailwind + django-vite + HTMX. A React tenant portal is post-MVP. |
| 5 | **An internal DRF API ships in the MVP.** | The API is internal-only, session-cookie authenticated, and sized to make a post-MVP React overlay cheap. It shares the service layer with the server-rendered surfaces. It is not a public API. |
| 6 | **Manufacturing is built but gated to Pro+.** | BOMs, manufactured products, build orders, build labor, and cost variance are implemented in the MVP and gated behind the `bom_manufacturing` / `build_orders` family of feature codes. |
| 7 | **Brand primary is teal `#0f766e`.** | The provided CSS (`homepage.css`, `dashboard.css`) is the brand source of truth. The design system in Section 14 derives from those files. |
| 8 | **Operator-created tenants start `active`.** | New tenants created by a platform operator default to `Subscription.status = active`. Entitlement resolution treats `{active, trialing}` as entitled; `trialing` remains available for future use. |
| 9 | **"Limited" plan cells are an enabled feature plus a plan limit.** | Where the tier matrix marks a feature "Limited," the feature code is enabled (`has_feature` → true) and a numeric plan-limit row constrains it. "Limited" is not a third entitlement state and is not modeled as a separate feature code. |

### 1.6 Glossary

**Status: NORMATIVE.** Authoritative term registry.

| Term | Meaning |
|---|---|
| **Tenant** | A customer organization on the platform. Synonym for Organization in commercial context. |
| **Organization** | The Django model representing a tenant. Every tenant-owned record references an Organization by foreign key. |
| **User** | A globally unique identity, keyed by normalized email, linked to an Auth0 identity. May hold memberships in zero or more organizations. |
| **Membership** | The relationship of a User to an Organization, carrying role assignments, operating-scope assignments, and status. The authoritative tenant-access record. |
| **System User** | A single platform-level User row with `is_system=True`. Owns all automated state transitions. |
| **Support User** | A platform user (`is_staff=True`) authorized to use the platform console and to enter tenant contexts under controlled, audited impersonation. |
| **Capability** | A platform-defined permission code (e.g., `quotes.send`), format `{domain}.{resource}.{action}`. Answers "can this *user* do it?" Tenants cannot mint custom codes in the MVP. |
| **Role** | A named collection of capabilities. Platform-seeded default roles are read-only templates; tenants may compose custom roles from existing capabilities. |
| **Feature Code** | A platform-defined, stable string (e.g., `bom_manufacturing`) gating a tenant-level capability. Answers "did this *tenant* pay for it?" Distinct from Capability. |
| **Subscription** | The per-tenant record of plan, status, included seats, and limit ceilings. Created during organization creation. |
| **Plan** | One of Starter / Growth / Pro / Enterprise. Determines the baseline set of enabled feature codes and limits. |
| **Add-On Pack** | A purchasable bundle of feature codes (e.g., Work Orders Add-On) that enables features above a tenant's base plan. |
| **Entitlement** | The resolved answer to "does this tenant have this feature right now," computed from override → plan → active add-on → deny. |
| **Plan Limit** | A numeric ceiling tied to a Subscription (max users, max locations, import rows per batch, active price lists, etc.). |
| **Operating Scope (RML)** | A Region / Market / Location restriction on a Membership that intersects all queryset and object access. Also a pricing input. |
| **Strategy** | A reusable base pricing calculation (e.g., `strategy.cost_plus`). Pure function; no database access. |
| **Resolver** | A database-backed input selector (e.g., `cost_source.selected_supplier`) that populates the pricing context before a strategy runs. |
| **Modifier** | A reusable adjustment applied to a strategy's output (e.g., `modifier.location`, `modifier.tax`). Pure transform. |
| **PricingContext** | The immutable input bundle to the pricing pipeline, constructed by `PricingContextBuilder`. |
| **PricingSnapshot** | The persisted, immutable record of a pricing result. Written once at quote/invoice time. Replayable via stored engine version. |
| **Outbox** | A transactional table that durably publishes side-effect intents. Workers consume outbox rows idempotently. |
| **Handoff** | The signed, single-use, 60-second token mechanism that carries authenticated identity from the root domain to a tenant subdomain. |
| **Audit Event** | An append-only, schema-versioned record of a state-changing or sensitive action, retained per the retention policy. |
| **Service Layer** | The plain-Python orchestration functions in `apps/<domain>/services/` that own all state-changing workflow logic and enforce capability + entitlement checks. |
| **Tenant-local session** | The Django session established on a tenant subdomain after handoff. Independent of the root-domain session. |
| **Sensitive Action** | An action requiring fresh re-authentication regardless of session age (e.g., quote acceptance, payment, impersonation start, tenant deletion). |
| **Auth0 Identity** | The linkage row connecting a canonical User to an Auth0 subject (`sub`) claim. Auth0 proves identity; it does not grant tenant access. |

---

## Section 2 — Product Overview

### 2.1 What MyPipelineHero Is

**Status: INFORMATIVE.**

MyPipelineHero is a multi-tenant **CRM + CPQ + operational-workflow** SaaS platform for businesses that sell a mix of **services, resold products, and manufactured or assembled products**. It manages the entire commercial lifecycle from lead intake through quoting, sales order creation, fulfillment, invoicing, and payment — with a flexible pricing engine, region/market/location operating-scope authorization, immutable commercial history, and subscription-tiered feature access.

It is deliberately more than a CRM. A CRM tracks relationships and deals. MyPipelineHero additionally:

- **Quotes accurately** through a composable pricing engine (CPQ), not a single price field.
- **Turns accepted quotes into operational work** — work orders for services, purchase orders for resale, build orders for manufactured goods.
- **Invoices from what actually happened**, sourced from immutable pricing snapshots so commercial history is reproducible.
- **Tracks cost and margin**, including manufactured build-up cost and labor variance.

### 2.2 Who It Serves

**Status: INFORMATIVE.**

The target tenant is an operating business — typically small to mid-sized — that has outgrown spreadsheets or a simple CRM because its selling motion is genuinely operational:

- A field-service company that quotes jobs, dispatches technicians, and invoices on completion.
- A reseller/distributor that quotes products sourced from suppliers and invoices on receipt.
- A light manufacturer or fabricator that quotes built-to-order products with a bill of materials, tracks labor, and reports cost variance.
- Mixed businesses doing all three, often across multiple locations, regions, or markets.

Tenants range from a three-person Starter team to a multi-market Enterprise organization. The subscription model (Section 7) matches this range: simpler businesses pay for CRM and quoting; complex businesses pay for pricing governance, purchasing, and manufacturing.

### 2.3 Core Lifecycle

**Status: INFORMATIVE.**

The commercial spine of the product:

```text
Lead → Quote → Acceptance → Sales Order → Fulfillment Artifacts → Invoice → Payment
                                          (Work Order / Purchase Order / Build Order)
```

- A **Lead** is qualified and converted into a **Quote**.
- A **Quote** holds versioned line items; each line is priced through the engine and stamped with an immutable **PricingSnapshot**. A quote is sent, then accepted, declined, expired, or retracted.
- **Acceptance** resolves the client and creates a **Sales Order** copying the snapshot-backed commercial values.
- Each sales order line **dispatches a fulfillment artifact** based on its type: service → Work Order, manufactured → Build Order, resale → operator-driven Purchase Order, bundle → decomposed into child lines.
- When fulfillment makes a line eligible, an **Invoice** is created from the snapshot, sent, and tracked.
- **Payments** are recorded and allocated against invoices; the sales order closes when fully fulfilled and paid.

Every state transition is governed by an explicit state machine and emits an audit event. Commercial records are immutable or append-only; corrections happen through reversal, adjustment, or successor-version workflows, never destructive edits.

### 2.4 Why It Is Different From Generic CRMs

**Status: INFORMATIVE.**

| Generic CRM | MyPipelineHero |
|---|---|
| A deal has a single amount field. | A quote line is priced by a composable engine — base strategy + cost resolver + modifiers + approval — and the result is a replayable snapshot. |
| Pricing is whatever the rep types. | Pricing supports cost-plus, target margin, rate cards, tiers, component sums, recurring plans, contracts, segments, location adjustments, discounts, floors, approvals, and tax — all without per-scenario code. |
| Won deals are just a status. | Acceptance generates real operational work (work orders, purchase orders, build orders) and ties it back to commercial history. |
| No cost or margin awareness. | Manufactured build-up cost, BOM versioning, labor tracking, and estimated-vs-actual variance. |
| History is mutable. | Sent quotes, accepted pricing, posted payments, and audit events are immutable/append-only and reproducible. |
| One-size pricing for the SaaS itself. | Tiered subscriptions match price to value: simple CRM users pay less; complex operations pay for pricing governance and manufacturing. |

The differentiators that justify the pricing (CPQ pricing engine, operations, manufacturing, audit-grade history) are precisely the features gated to higher tiers.

### 2.5 MVP Positioning

**Status: NORMATIVE.**

The MVP is a **production-ready, server-rendered, multi-tenant build** that delivers the full commercial lifecycle and the subscription/entitlement system, deployed on Docker/DigitalOcean without Kubernetes.

**The MVP ships:**

- Multi-tenant identity and access: Auth0 authentication, canonical users, memberships, RBAC, RML operating scope, cross-subdomain handoff, and support impersonation.
- The subscription and entitlement system: four plans, add-on packs, feature codes, plan limits, two-gate enforcement (RBAC + entitlement), downgrade-to-read-only behavior, and operator-managed plan assignment.
- Operator-mediated tenant onboarding with plan/add-on selection, owner invite via Auth0, and a first-login setup wizard.
- The full commercial domain: Lead, Quote (versioned), Client, Sales Order, Work Order, Purchase Order, Build Order, Invoice, Payment, Task, Communication, and Document Attachment.
- The CPQ pricing engine: 7 base strategies, cost/input resolvers, reusable modifiers, approval workflow, immutable snapshots, and replay.
- Catalog and manufacturing: services, products, raw materials, suppliers, BOM versioning (Pro+ gated).
- Billing: snapshot-driven invoicing, payments and allocations, per-jurisdiction tax, a Noop accounting adapter, ten fixed reports, and async CSV exports.
- An Import Center for guided onboarding/migration, gated and limited by plan.
- Audit (append-only, retained), outbox-driven async, idempotent Celery workers, single beat scheduler.
- Server-rendered surfaces: custom landing page, Auth0-backed auth pages, tenant portal, platform console, and custom tenant admin — all on the MyPipelineHero teal design system.
- An internal, session-authenticated DRF API sized for a clean post-MVP React overlay.
- Docker-based deployment with backups, restore drill, anonymized staging refresh, and observability.

**The MVP explicitly excludes** (full catalog in Section 22): React tenant portal; public/external API; payment-processor integration and self-service plan changes; Kubernetes; multi-currency; refunds/credit notes; inventory; native mobile; and self-service signup.

**MVP-to-post-MVP transition principle:** every state-changing operation runs through the service layer; every surface (HTMX views, the DRF API, and the future React client) calls the same service functions. The DRF API is built in the MVP precisely so the post-MVP React portal overlays the existing Django backend without re-implementing business logic. The service layer, handoff protocol, RBAC, entitlement enforcement, pricing engine, and audit are surface-agnostic and survive the React transition untouched.

---

## Section 3 — MVP Scope

### 3.1 Scope Philosophy

**Status: NORMATIVE.**

The MVP is production-ready, not infrastructure-heavy. It ships the complete commercial lifecycle and the full subscription/entitlement system, but it deploys without Kubernetes, integrates no payment processor, and renders no React.

Two rules govern every scope decision:

1. **Composition over proliferation.** Pricing behavior is composed from a small set of base strategies, resolvers, and modifiers — never one class per business scenario. Subscription gating is composed from feature codes resolved through one entitlement function — never per-feature bespoke logic.
2. **Build for the overlay.** Because a React tenant portal follows post-MVP, every state-changing operation lives in the service layer and is reachable identically from HTMX views and the DRF API. Nothing in the MVP front end may hold business logic that the React portal would have to re-implement.

### 3.2 What the MVP Includes

**Status: NORMATIVE.**

**Identity, access, and tenancy**

- Auth0 Universal Login (OIDC); canonical `User` linked to an Auth0 identity; Auth0-owned credentials, signup-at-invite, password reset, and MFA.
- Row-based multi-tenancy: every tenant-owned record carries `organization_id`; `TenantManager`/`TenantQuerySet` enforce isolation.
- RBAC: capability registry, default role templates, custom roles, membership grants with DENY-beats-GRANT.
- RML operating scope (Region / Market / Location) intersecting queryset and object access — gated by `rml_scope` (Growth+).
- Cross-subdomain signed handoff, tenant-local sessions, and support impersonation with a server-rendered, unstrippable banner.

**Subscriptions and entitlements**

- Four plans (Starter / Growth / Pro / Enterprise), six add-on packs, ~38 feature codes, and plan limits.
- `Subscription`, `PlanEntitlement`, `PlanAddOnEntitlement`, `OrganizationAddOnSubscription`, `OrganizationEntitlementOverride` models.
- Two-gate enforcement: RBAC (`require_capability`) **and** entitlement (`require_feature`), both at the service layer.
- Plan-limit enforcement at create paths (`PlanLimitExceededError`); "Limited" tier cells modeled as enabled-feature + numeric limit.
- Downgrade-to-read-only behavior (no destructive data loss); operator-managed plan/add-on assignment in the platform console; entitlement audit events; upgrade-prompt UX.

**Onboarding**

- Operator-mediated tenant creation including plan and add-on selection and Subscription creation.
- Owner invite via Auth0; invite acceptance; first-login setup wizard (locations, tax, numbering, team) respecting the tenant's plan and limits.
- Import Center (guided CSV import) gated by `import_center` with per-plan row limits.

**Commercial domain**

- Lead (with contacts/sites) and lead lifecycle; lead→quote conversion.
- Quote container + versioning + lines + discounts; quote send, accept (with client resolution), decline, expire, retract-with-inheritance-and-re-pricing.
- Client (contacts, locations, segment, merge); Sales Order + lines with bundle decomposition.
- Tasks and Communications with typed link tables; Document Attachments with retention.

**Catalog, pricing, manufacturing**

- Services, products, raw materials, suppliers, supplier costs.
- BOM + BOMVersion + BOMLine with effective-dated versioning (Pro+ gated).
- Pricing engine: 7 base strategies, 6 cost/input resolvers, 16 modifiers, rule resolution, approval workflow, immutable snapshots, replay.
- Pricing configuration: PriceList, ClientContractPricing, LaborRateCard, CustomerSegment, PromotionCampaign, BundleDefinition — each tier-gated per Section 7.
- Tax: TaxJurisdiction + TaxRate, per-jurisdiction resolution.

**Operations**

- Fulfillment dispatch (service→WorkOrder, manufactured→BuildOrder, resale→operator-driven PurchaseOrder, bundle→decompose).
- Work orders (assignment, status, completion); purchase orders (allocation, receipt); build orders (BOM snapshot, labor entries/adjustments, cost variance).

**Billing and reporting**

- InvoicingPolicy; snapshot-driven Invoice + InvoiceLine; invoice eligibility rules.
- Payment + PaymentAllocation + PaymentAdjustment (append-only; reversals via new rows).
- Per-jurisdiction tax application; Noop accounting adapter (outbox-driven sync boundary).
- Ten fixed reports + async CSV export (ReportExportJob); advanced reports gated by `advanced_reporting`.

**Cross-cutting and platform**

- Service-layer-first architecture with static AST enforcement; typed exception taxonomy including `FeatureNotEntitledError` and `PlanLimitExceededError`.
- Append-only AuditEvent (partitioned, retained); outbox pattern; idempotent Celery workers; single Celery beat per environment.
- Tenant data export and tenant deletion (30-day grace) — available on all plans.
- Custom platform console and custom tenant admin; dev-only Django admin for raw inspection.
- Internal DRF API (session-authenticated, cursor-paginated, OpenAPI-documented) sized for the React overlay.
- Observability (structured logs, error monitoring, OpenTelemetry SDK), backups, restore drill, anonymized staging refresh.
- Docker-based DigitalOcean deployment.

### 3.3 What the MVP Excludes

**Status: NORMATIVE.**

The following are **not** built in the MVP. Items marked post-MVP appear with their target in Section 22.

- **React tenant portal** (post-MVP). The MVP is server-rendered.
- **Payment-processor integration** for SaaS subscriptions (Stripe/Paddle), self-service signup, self-service plan changes, add-on self-purchase, proration, failed-payment workflows (post-MVP). Plan/add-on assignment is operator-managed.
- **Public / external API, webhooks, API tokens** (post-MVP). The MVP API is internal and session-authenticated only.
- **Kubernetes**, Helm, ingress controllers, cert-manager, HPA, cluster autoscaling, service mesh, sealed secrets, Kubernetes migration Jobs, Kubernetes beat-singleton leases (post-MVP scalability appendix).
- **Multi-currency invoicing within a single org**; FX sourcing (post-MVP). One base currency per organization; modifier hooks reserved.
- **Refunds, credit notes, write-offs** (post-MVP). Corrections via payment reversal/adjustment only.
- **Inventory tracking / stock deduction** (post-MVP).
- **Concrete accounting adapters** (QuickBooks/Xero/NetSuite). MVP ships the adapter interface and the Noop adapter only.
- **Inbound email sync / mailbox threading** (post-MVP). Communications are manual-log or outbound-only.
- **Customer-facing public quote acceptance**; native e-signature integration (post-MVP).
- **Native mobile applications** (post-MVP).
- **Schema-per-tenant deployment** (post-MVP, if ever). Row-based tenancy only.
- **Parent/child client account hierarchy** (post-MVP).
- **Ad hoc / custom report builder, scheduled report delivery, BI export, dashboard KPIs** (post-MVP). Ten fixed reports only.
- **Recurring service templates, route optimization, dispatch automation** (post-MVP).
- **SAML, SCIM, tenant-managed custom IdPs, IdP group→role mapping** (post-MVP). Auth0 with platform-managed connections only.
- **Local password authentication and local TOTP machinery.** Auth0 owns all credential and MFA handling; the MVP does not build a parallel local auth system.
- **One-off pricing strategy classes** for supplier selection, rush, location, complexity, etc. — these are resolvers/modifiers, not strategies.

### 3.4 What Is Post-MVP

**Status: INFORMATIVE.**

Section 22 is the authoritative deferred-scope catalog with target versions and accommodation notes. The headline post-MVP items are: the React tenant portal; the public API and webhooks; payment-processor integration and self-service subscription management; advanced/custom reporting; concrete accounting adapters; multi-currency; refunds/credit notes; inventory; native mobile; and Kubernetes.

Each deferred item has a corresponding entry recording what the MVP already does to make its later implementation cheap (the "accommodation"). A deferred decision without a Section 22 entry is a prohibited implicit decision.

### 3.5 The No-React-in-MVP Rule

**Status: NORMATIVE.**

The MVP front end is server-rendered: Django templates + Tailwind + django-vite + HTMX, with Alpine.js for trivial client-only interactivity. No React, Vue, or Svelte ships in the MVP.

This is a hard rule, but it is paired with an equally hard obligation: **the MVP is built so the post-MVP React portal is a thin overlay, not a rewrite.** Concretely:

1. **Service-layer exhaustiveness.** Every state-changing operation invoked by any view has a corresponding service function. Views never contain workflow logic.
2. **Surface-agnostic services.** Service functions accept primitives and dataclasses — never `request` objects — and return domain entities or result dataclasses. They are equally callable from an HTMX view, a DRF endpoint, a Celery task, or a future React-backing endpoint.
3. **Both gates in services.** `require_capability` and `require_feature` are enforced in the service layer, not only in decorators or templates, so every surface inherits enforcement.
4. **Internal DRF API now.** The MVP builds the internal, session-authenticated DRF API (Section 4.9, Section 11 of the data/API treatment) against the same services. The React portal consumes this API; it is not invented post-MVP.
5. **Permanent server-rendered surfaces.** The landing page, Auth0 auth pages, organization picker, platform console, custom tenant admin, support tooling, and email/PDF templates remain server-rendered permanently. React replaces only tenant-portal *workflow* screens, domain by domain.
6. **Style-token continuity.** Server-rendered screens use the shared MyPipelineHero teal design tokens (Section 14) so the React portal preserves the same visual language.

A static AST check (Section 16) blocks PRs that put `.save()`, `.delete()`, `Model.objects.create()`, `.update()`, or `transaction.atomic()` outside the service layer, or that reference `request.user` inside services. This guardrail is what keeps the no-React rule from quietly creating front-end-coupled business logic.

---

## Section 4 — System Architecture

### 4.1 Architectural Principles

**Status: NORMATIVE.**

These are decision rules. In code review, citing a principle by number is sufficient justification to block a PR.

1. **Tenant safety over convenience.** No cross-tenant data leakage, ever — including during support work. Shared querysets without `for_org`, `GenericForeignKey`, and raw SQL bypassing the tenant manager are prohibited.
2. **Two independent gates.** Authorization (RBAC: can this user?) and entitlement (subscription: did this tenant pay?) are separate checks, both enforced in the service layer. Neither substitutes for the other.
3. **Commercial immutability is auditable history.** Sent quotes, accepted pricing, generated orders, posted payments, and audit events are reproducible from stored data without destructive edits.
4. **The service layer is the authoritative orchestration boundary.** Every state-changing workflow executes through `apps/<domain>/services/`. Views, forms, admin actions, Celery tasks, DRF endpoints, and signal handlers call services rather than re-implementing logic.
5. **Idempotency is required for async.** Every Celery task that creates or transitions state is safe to retry; side effects publish through the outbox; idempotency keys are deterministic from input.
6. **Audit is append-only and complete.** Every state transition, authentication event, authorization-grant change, entitlement change, impersonation start/end, and pricing override/approval emits an AuditEvent. Audit carries both the acting user and the on-behalf-of user under impersonation.
7. **Typed links over polymorphic relations.** Cross-domain links use explicit FK link tables with CHECK constraints. `GenericForeignKey` is prohibited for business-object linkage.
8. **State machines are authoritative.** The transition tables are the contract; code may not add, remove, or reorder transitions without amending the guide in the same PR. Property tests verify code matches the tables.
9. **Observability by default.** Every service function runs inside a structured logging context with a correlation ID. Production debugging without logs/metrics/errors is unacceptable.
10. **Explicit over clever.** Signal-driven cascades, metaclass autodiscovery, `**kwargs` plumbing through services, and monkey-patches are prohibited in domain code.
11. **Deferred decisions are documented, not implicit.** Every deferred/future-friendly decision appears in Section 22 with an MVP accommodation note.

### 4.2 Technology Stack

**Status: NORMATIVE.**

| Concern | Choice |
|---|---|
| Language / framework | Python 3.12+, Django 5.x |
| Database | PostgreSQL 17 |
| Cache / broker / locks / handoff store / rate limits | Redis 7 |
| Async execution | Celery (worker + single beat per environment) |
| Authentication | Auth0 Universal Login (OIDC), via a server-side OIDC client (Authlib) |
| Internal API | Django REST Framework, `drf-spectacular` for OpenAPI |
| Server templating | Django templates |
| CSS | Tailwind CSS 4.x (compiled; no browser CDN in non-dev) |
| Asset pipeline | django-vite (ESM) |
| Interactivity | HTMX (global default); Alpine.js (trivial client-only) |
| Object storage | S3-compatible (MinIO in dev) |
| Reverse proxy / TLS | Nginx or Caddy |
| PDF rendering | WeasyPrint |
| Containerization | Docker + Docker Compose (dev and prod) |
| Hosting | DigitalOcean (no Kubernetes) |
| Observability | structlog (JSON), Sentry-equivalent error monitoring, OpenTelemetry SDK |

Runtime configuration comes from environment variables. Secrets are managed outside source control (Section 17).

### 4.3 High-Level Topology

**Status: NORMATIVE.**

```text
                          ┌─────────────────────────────┐
                          │ Auth0 Tenant                │
                          │ Universal Login, MFA, IdPs  │
                          └──────────────┬──────────────┘
                                         │ OIDC (root domain only)
                          ┌──────────────▼──────────────┐
                          │ DNS                         │
                          │ mypipelinehero.com          │
                          │ *.mypipelinehero.com        │
                          └──────────────┬──────────────┘
                                         │
                          ┌──────────────▼──────────────┐
                          │ Reverse Proxy (Nginx/Caddy) │
                          │ TLS, HTTP→HTTPS, sec headers│
                          └──────────────┬──────────────┘
                ┌────────────────────────┼────────────────────────┐
        ┌───────▼───────┐        ┌───────▼───────┐        ┌────────▼───────┐
        │ root domain   │        │ {slug}.tenant │        │ platform       │
        │ landing/login │        │ subdomain     │        │ console        │
        └───────┬───────┘        └───────┬───────┘        └────────┬───────┘
                └────────────────────────┼─────────────────────────┘
                          ┌──────────────▼──────────────┐
                          │ Django web (Gunicorn)       │
                          │ stateless; serves HTMX + API│
                          └──────────────┬──────────────┘
        ┌──────────────┬─────────────────┼─────────────────┬──────────────┐
 ┌──────▼──────┐ ┌─────▼─────┐    ┌───────▼──────┐  ┌───────▼─────┐ ┌──────▼──────┐
 │ pgBouncer   │ │ Redis     │    │ Object store │  │ Outbox      │ │ Structured  │
 │ (non-dev)   │ │ broker/   │    │ S3-compatible│  │ (Postgres   │ │ JSON logs   │
 │             │ │ cache/    │    │              │  │  table)     │ │ → log sink  │
 │             │ │ handoff   │    │              │  │             │ │             │
 └──────┬──────┘ └───────────┘    └──────────────┘  └─────────────┘ └─────────────┘
        │
 ┌──────▼──────┐     Async tier:
 │ PostgreSQL  │     ┌────────────────┐   ┌──────────────────┐
 │ managed or  │     │ Celery worker  │   │ Celery beat      │
 │ self-hosted │     │ critical/      │   │ exactly one per  │
 └─────────────┘     │ default/bulk/  │   │ environment      │
                     │ reports queues │   └──────────────────┘
                     └────────────────┘
```

Auth0 sits at the edge and is contacted only from the root domain during login and callback. Tenant subdomains never initiate Auth0 login directly; tenant access is established only through the signed handoff flow after root-domain authentication.

### 4.4 Component Requirements

**Status: NORMATIVE.**

**DNS.** Routes the apex/root domain and wildcard tenant subdomains to the reverse proxy.

**Reverse proxy.** Nginx or Caddy terminates TLS, redirects HTTP→HTTPS, routes root-domain, tenant-subdomain, and platform-console traffic to the Django web container, and applies baseline security headers (Section 17). TLS certificates via Let's Encrypt, DigitalOcean-managed certificates, or equivalent.

**Django web tier.** Django behind Gunicorn, in a container, **stateless**. Serves both the HTMX server-rendered surfaces and the internal DRF API. Long-running work goes through the outbox and Celery, never inline in the request path.

**Auth0.** The identity provider. Owns the login UI, credential storage, signup-at-invite, password reset, and MFA. OIDC callbacks terminate on the root domain only. Auth0 client secret is an environment-supplied secret. Auth0 proves identity; it never grants tenant access (Section 8).

**Worker tier.** Celery workers in one or more containers. The MVP MAY start with one worker consuming all queues, but logical queue separation is preserved:

| Queue | Purpose | Posture |
|---|---|---|
| `critical` | Auth-adjacent work: invite emails, notifications | Low latency |
| `default` | General domain async work | Normal |
| `bulk` | High-volume notification/reminder/import work | Batch-friendly |
| `reports` | Long-running reports and exports | Lower concurrency |

**Beat tier.** Exactly one Celery beat scheduler per environment. Multiple beats are prohibited. Beat-triggered jobs are idempotent and use a Redis or Postgres lock where duplicate execution would be harmful.

**PostgreSQL.** Production SHOULD use DigitalOcean Managed PostgreSQL unless cost/ops require self-hosting (then: durable volumes, automated backups, WAL/PITR, documented restore).

**pgBouncer.** SHOULD be used in staging/production once connection count requires pooling; transaction pooling default.

**Redis.** Celery broker, cache, org-slug cache, handoff token store, entitlement cache, rate-limit counters, optional distributed locks. Production SHOULD use managed Redis where feasible.

**Object storage.** S3-compatible outside dev. Object keys include environment and organization prefix:

```text
{environment}/orgs/{org_id}/{domain}/{record_id}/{filename}
```

### 4.5 Environments

**Status: NORMATIVE.**

| Environment | Settings module | Purpose | Auth0 connection |
|---|---|---|---|
| `dev` | `config.settings.dev` | Local development (Docker Compose) | Dev Auth0 tenant/app |
| `test` | `config.settings.test` | Automated tests | Auth0 mocked |
| `staging` | `config.settings.staging` | Production-like validation | Staging Auth0 tenant/app |
| `demo` | `config.settings.demo` | Demo/sandbox tenants | Demo Auth0 tenant/app |
| `prod` | `config.settings.prod` | Live tenants | Production Auth0 tenant/app |

Each environment uses its own Auth0 application and callback URL set. Production OAuth/OIDC callback URLs are configured and verified before launch (Section 20).

### 4.6 Cross-Domain Flow: Authentication and Handoff

**Status: NORMATIVE.**

All authentication starts on the root domain and flows through Auth0:

```text
1. User → GET https://mypipelinehero.com/login → Django web
2. Django redirects to Auth0 Universal Login (OIDC authorize), root-domain callback
3. Auth0 authenticates the user (credentials + MFA) and redirects to
   https://mypipelinehero.com/auth/callback?code=...
4. Django validates the callback (state, nonce, issuer, audience, ID-token signature, expiry)
5. Django resolves or links the canonical User from the Auth0 subject claim
6. Django establishes a ROOT-DOMAIN session (no tenant access yet)
7. Django loads the user's ACTIVE memberships:
   - 0 memberships, non-staff → "no active access" page
   - 0 memberships, staff → platform console
   - 1 membership → issue handoff token
   - 2+ memberships → organization picker → issue handoff token
8. Django stores a single-use handoff token in Redis (60s TTL), signed (kid + HS256)
9. 302 → https://{slug}.mypipelinehero.com/handoff?token=...
10. Tenant subdomain validates + atomically consumes the token (host-bound, replay-protected)
11. Tenant subdomain establishes a TENANT-LOCAL session and 302 → /dashboard
```

The root-domain session never grants tenant data access. The tenant-local session is per-subdomain, database-backed, and bound to a specific active membership. A shared parent-domain tenant session is prohibited. Handoff signing keys rotate quarterly with a two-key overlap window (Section 8).

### 4.7 Cross-Domain Flow: Outbox

**Status: NORMATIVE.**

```text
1. Service function opens a transaction
2. Service mutates domain rows
3. Service inserts an OutboxEntry (payload + idempotency_key + correlation_id)
4. Transaction commits  ← outbox insert and domain mutation are atomic together
5. Outbox dispatcher (beat-triggered, ~5s) selects PENDING rows with skip-locked
6. Dispatcher marks DISPATCHED and enqueues a Celery task with the outbox row id
7. Worker consumes the task and processes the row idempotently
8. Worker marks the row CONSUMED (or moves it to dead-letter after max attempts)
```

The outbox table is the durability boundary; Celery is the execution mechanism, not the source of truth. This is how every side effect (emails, PDFs, fulfillment dispatch, accounting sync, exports) is published.

### 4.8 Entitlement Resolution in the Architecture

**Status: NORMATIVE.**

Entitlement enforcement is a first-class architectural layer, distinct from RBAC and resolved once per request.

- Each tenant has exactly one `Subscription`. Entitlement resolution computes `has_feature(organization_id, feature_code)` via precedence: **organization override → base plan entitlement → active add-on entitlement → deny**. Resolution returns `False` if the subscription status is not in `{active, trialing}`.
- Resolution is **request-scoped cached**: the resolver loads the subscription, active add-ons, overrides, and the plan/add-on entitlement sets once per request (keyed by `organization_id`) and answers all `has_feature` calls for that request from the cache. This prevents N+1 entitlement queries on gated service calls. The cache is also usable inside outbox workers, keyed by the org on the outbox payload.
- `require_feature(organization_id, feature_code)` raises `FeatureNotEntitledError` (HTTP 403, distinct `error_code`) when denied. Plan limits raise `PlanLimitExceededError` (HTTP 403) at create paths.
- The resolver tolerates a missing `Subscription` only during the organization-creation transaction (the Subscription row is created in the same transaction as the Organization, mirroring the InvoicingPolicy pattern).
- Entitlement is enforced in the **service layer**, so every surface (HTMX views, DRF endpoints, Celery tasks that create restricted records, future React-backing endpoints) inherits it. Template nav-hiding and the `@require_plan_feature` view decorator are conveniences, not the security boundary.

### 4.9 Internal API in the Architecture

**Status: NORMATIVE.**

The MVP ships an internal DRF API, architecturally positioned as the contract the post-MVP React portal will consume:

- **Same backend, same services.** API endpoints call the identical service functions the HTMX views call. No parallel business logic.
- **Session-cookie authentication only.** The API authenticates via the tenant-local Django session established after Auth0 handoff. No API tokens, no bearer auth, no Auth0 token forwarding into API calls. CSRF applies to mutating requests; HTMX and the future same-origin React client both satisfy this.
- **Tenant + scope + entitlement enforced.** Every endpoint applies `for_membership` queryset scoping, `require_capability`, and (for gated domains) `require_feature` — inherited from the shared service layer and DRF mixins.
- **Cursor pagination, versioned URL (`/api/v1/`), `drf-spectacular` OpenAPI**, with the committed schema validated in CI.
- **Surface, not source of truth.** In the MVP the API primarily backs HTMX partial endpoints (autocomplete search, pricing preview, draft autosave) and provides read endpoints for React development. Complex multi-step writes (quote send/accept, payment record) flow through server-rendered form views in the MVP; the API surface expands by addition post-MVP.

### 4.10 Deployment Posture

**Status: NORMATIVE.**

The MVP deploys with Docker images and environment-specific Docker Compose files (or equivalent host-level container orchestration) on DigitalOcean.

The production stack includes (directly or via managed services): reverse proxy, web, worker, beat, PostgreSQL, Redis, and optional pgBouncer. It excludes dev-only services (MinIO console, Vite dev server, Mailpit).

Explicitly **not** in the MVP: Kubernetes manifests, Helm, ingress-nginx, cert-manager, HPA, cluster autoscaling, service mesh, sealed secrets, Kubernetes Jobs for migrations, Kubernetes beat-singleton leases, blue-green traffic shifting, canary weighting. These belong to a post-MVP scalability appendix.

Deployment is migrate-before-serve: build and push image → pull on host → run migrations → restart web/worker/beat → `check --deploy` → `/readyz` smoke test. Migrations are backward-compatible across at least one deployed version; rollback redeploys a prior known-good image tag and never auto-runs reverse migrations (Section 20).

---

## Section 5 — Multi-Tenancy

### 5.1 Tenancy Posture

**Status: NORMATIVE.**

MyPipelineHero uses **row-based multi-tenancy**. Every tenant-owned record carries an `organization_id` foreign key. Schema-per-tenant deployment is out of scope and is not a future option for the MVP (Section 22 records it as "v3+ if ever").

The `Organization` is the tenant root. A `User` is global and gains access to a tenant only through a `Membership`. Tenant isolation is enforced at three layers — the model manager, the service layer, and the RBAC object check — and verified by a CI guardrail. No single layer is trusted alone.

### 5.2 Organization Model

**Status: NORMATIVE.**

```text
Organization
  id: UUID, pk                                      -- UUID v7
  slug: TEXT, unique                                -- subdomain-safe, immutable after creation
  name: TEXT
  status: ENUM(ACTIVE, SUSPENDED, OFFBOARDING, DELETED)
  primary_contact_name: TEXT
  primary_contact_email: TEXT
  primary_contact_phone: TEXT, null
  timezone: TEXT                                    -- IANA tz name
  base_currency_code: CHAR(3)                       -- ISO 4217; single currency per org (MVP)
  default_tax_jurisdiction_id: UUID, fk -> TaxJurisdiction, null
  invoicing_policy_id: UUID, fk -> InvoicingPolicy, null
                                -- non-null after services.create_organization completes;
                                -- null only during the create transaction
  numbering_config: JSONB                           -- prefix overrides per entity
  accounting_adapter_code: TEXT, default("noop")
  accounting_adapter_config: JSONB, default({})     -- field-encrypted at rest (Section 17)
  org_setup_complete: BOOL, default(false)          -- set true when the Setup Wizard is dismissed
  created_at: TIMESTAMPTZ
  updated_at: TIMESTAMPTZ
```

The `Subscription` row (Section 7.5) is created in the same transaction as the Organization. The relationship is one-to-one and the tenant always has exactly one subscription after creation completes.

**Slug rules.** Slug MUST match `^[a-z][a-z0-9-]{1,61}[a-z0-9]$` (DNS-safe), is globally unique, and is immutable after creation in the MVP.

**Status semantics.**

| Status | Meaning | Tenant-portal access | Entitlement effect |
|---|---|---|---|
| `ACTIVE` | Normal operating state | Full | Per subscription |
| `SUSPENDED` | Platform-imposed suspension | Blocked at handoff | n/a (no access) |
| `OFFBOARDING` | Tenant-initiated termination, 30-day grace | Read-only; exports allowed | Read-only |
| `DELETED` | Cascade complete; row retained for audit attribution only | None | n/a |

Organization status and subscription status are distinct but interact. A `SUSPENDED` organization is blocked at handoff regardless of subscription. A `past_due` or `suspended` *subscription* (Section 7.11) degrades the tenant to read-only via the entitlement gate even while the organization remains `ACTIVE`.

### 5.3 Tenant-Owned Record Requirement

**Status: NORMATIVE.**

Every tenant-owned model MUST:

1. Declare `organization = models.ForeignKey(Organization, on_delete=models.PROTECT, ...)`.
2. Set `objects = TenantManager()`.
3. Set the class attribute `is_tenant_owned = True`.
4. Inherit from the `TenantOwnedModel` abstract base.

```python
# NORMATIVE: shape
class TenantOwnedModel(models.Model):
    organization = models.ForeignKey(
        "platform_organizations.Organization",
        on_delete=models.PROTECT,
        related_name="+",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+", null=True,
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+", null=True,
    )

    is_tenant_owned: bool = True
    objects: "TenantManager" = TenantManager()

    class Meta:
        abstract = True
```

### 5.4 TenantManager and TenantQuerySet

**Status: NORMATIVE.**

```python
# NORMATIVE: shape
class TenantQuerySet(models.QuerySet):
    def for_org(self, organization_id: UUID) -> "TenantQuerySet":
        return self.filter(organization_id=organization_id)

    def for_membership(self, membership: "Membership") -> "TenantQuerySet":
        """Apply org scope AND operating-scope intersection."""
        qs = self.for_org(membership.organization_id)
        return qs.intersect_with_operating_scope(membership)

    def intersect_with_operating_scope(self, membership: "Membership") -> "TenantQuerySet":
        # Default no-op; overridden by querysets of RML-scoped entities (Section 8).
        return self


class TenantManager(models.Manager.from_queryset(TenantQuerySet)):
    use_in_migrations = False  # NEVER use in migrations
```

`for_org` is the floor for every tenant-scoped query. `for_membership` additionally intersects the RML operating scope and is the default in tenant-facing views and API endpoints. RML intersection is itself entitlement-gated: when `rml_scope` is not entitled, the tenant operates organization-wide and `intersect_with_operating_scope` is a no-op (Section 8).

### 5.5 Tenant Isolation Rules

**Status: NORMATIVE.**

1. **No unscoped tenant queries.** Every read of a tenant-owned model goes through `for_org` (minimum) or `for_membership` (default). Bare `Model.objects.all()` on a tenant-owned model in domain code is a defect.
2. **Same-org foreign-key invariant.** When a tenant-owned record references another tenant-owned record, both MUST belong to the same Organization. Enforced at the service layer via `ensure_same_org(*records)` (raises `TenantViolationError`) and at the RBAC object check (Section 8).
3. **No polymorphic relations.** `GenericForeignKey` is prohibited for business-object linkage; typed link tables with CHECK constraints are required.
4. **No raw SQL bypass.** Raw SQL that reads tenant-owned tables without an `organization_id` predicate is prohibited.
5. **Object storage isolation.** Object keys embed the org: `{environment}/orgs/{org_id}/{domain}/{record_id}/{filename}`. Download URLs re-check tenancy on every request.

Cross-table org-consistency is enforced at the service layer, not via database CHECK constraints across tables, in the MVP.

### 5.6 Cross-Tenant Access Restrictions

**Status: NORMATIVE.**

Two narrow, audited exception paths permit cross-tenant queries; nothing else may:

1. **Support User platform console.** Custom platform-console views may perform controlled cross-tenant queries via explicit platform query services or `Model.objects.platform_admin_queryset()`. Each such query emits a `PLATFORM_ADMIN_QUERY` audit event. The base Django admin MUST NOT be used as the production platform console.
2. **Migrations.** `TenantManager.use_in_migrations = False`; migrations operate on the base manager intentionally and never carry tenant context.

Support impersonation (Section 8) is *not* a cross-tenant query path — it enters a single tenant context and operates with the impersonated membership's scope.

### 5.7 CI Tenant-Isolation Guardrail

**Status: NORMATIVE.**

A CI test enumerates all models and asserts isolation invariants:

```python
# NORMATIVE: behavior
def test_all_tenant_owned_models_use_tenant_manager():
    for model in apps.get_models():
        if getattr(model, "is_tenant_owned", False):
            assert isinstance(model._default_manager, TenantManager), (
                f"{model.__name__} declares is_tenant_owned=True but does not use TenantManager"
            )
            assert any(
                f.name == "organization" and isinstance(f, ForeignKey)
                for f in model._meta.fields
            ), f"{model.__name__} is tenant-owned but has no organization FK"
```

This test blocks merge. It is on the "NEVER cut" list (Section 21): isolation scaffolding is irreducible.

### 5.8 ID Strategy and Common Conventions

**Status: NORMATIVE.**

| Entity class | PK type | Rationale |
|---|---|---|
| Org-facing entities (Organization, Membership, Lead, Quote, etc.) | UUID v7 | Sortable by creation, B-tree-friendly, non-enumerable |
| AuditEvent, PricingSnapshot, OutboxEntry | BigInt (`BIGSERIAL`) | High volume |
| Numbering counters | `BIGSERIAL` | Native, atomic |

UUID v7 is generated in application code (`uuid6.uuid7()`). Every mutable tenant-owned entity carries `created_at`, `updated_at`, `created_by_id`, `updated_by_id`. Soft-deletable entities carry `deleted_at`/`deleted_by_id` with org-scoped uniqueness via partial indexes (`WHERE deleted_at IS NULL`). Entity numbering follows `{PREFIX}-{YEAR}-{SEQUENCE}` allocated under a row lock (Section 9); number gaps from rolled-back transactions are expected and acceptable.

### 5.9 Tenant Lifecycle Overview

**Status: NORMATIVE.**

The tenant lifecycle spans creation, operation, offboarding, and deletion. Onboarding (creation through first productive login) is specified in Section 6; offboarding and deletion are specified in Section 17. This subsection is the lifecycle map.

```text
[operator creates org + subscription] -> ACTIVE
        -> owner invited (Auth0) -> owner accepts -> setup wizard -> operating
ACTIVE  -> (operator) SUSPENDED -> (operator) ACTIVE          -- platform suspension/reinstatement
ACTIVE  -> (tenant admin) OFFBOARDING (30-day grace, read-only, exports allowed)
OFFBOARDING -> (tenant admin) ACTIVE                          -- cancellation of deletion
OFFBOARDING -> (beat job, after grace) DELETED                -- cascade executed
```

| Phase | Trigger | Key effects |
|---|---|---|
| Creation | Operator action (Section 6) | Organization + Subscription created atomically; owner invited via Auth0 |
| Operation | Owner accepts, wizard dismissed | `org_setup_complete=true`; tenant operates under plan/entitlements |
| Suspension | Operator action | `status=SUSPENDED`; handoff blocked; data retained |
| Offboarding | Tenant admin request (`tenant_deletion`) | `status=OFFBOARDING`; read-only; 30-day grace; export allowed |
| Deletion | Beat job after grace | Tenant-owned rows hard-deleted; `Organization` tombstone + AuditEvent + ImpersonationAuditLog retained |

Tenant data export and deletion are available on all plans (the `tenant_export` and `tenant_deletion` feature codes are universal). Deletion preserves the `Organization` row with `status=DELETED` for audit attribution and never removes audit or impersonation records (Section 17).

### 5.10 Acceptance Criteria

**Status: NORMATIVE.**

| # | Criterion | Verification |
|---|---|---|
| 1 | Every tenant-owned model declares an `organization` FK and uses `TenantManager` | CI isolation test |
| 2 | Slug enforces the DNS-safe regex and is globally unique and immutable | model + service test |
| 3 | A query through `for_org` returns only the target org's rows | service test |
| 4 | `for_membership` additionally applies RML intersection when `rml_scope` is entitled | service test |
| 5 | When `rml_scope` is not entitled, `for_membership` returns org-wide rows | service test |
| 6 | A service writing a record referencing a different org's record raises `TenantViolationError` | service test |
| 7 | Platform-console cross-tenant query emits `PLATFORM_ADMIN_QUERY` | integration test |
| 8 | `Subscription` is created in the same transaction as `Organization` | service test |
| 9 | Object-storage keys embed environment + org id; download re-checks tenancy | integration test |
| 10 | Organization `SUSPENDED` blocks handoff; `OFFBOARDING` is read-only with export allowed | integration test |
| 11 | Deletion retains the Organization tombstone, AuditEvent, and ImpersonationAuditLog rows | integration test |

---

## Section 6 — Tenant Onboarding

### 6.1 Scope and Posture

**Status: NORMATIVE.**

MVP onboarding is **operator-mediated**: a platform operator creates the tenant, selects its plan and add-ons, and invites the first owner. Self-service signup is post-MVP (Section 22). Auth0 owns credential creation; the owner sets up their login through Auth0 at invite acceptance, not through a MyPipelineHero-built signup form.

Onboarding has four actors and four phases:

```text
Actors:   Platform operator . Prospective owner . Auth0 . System User
Phases:   1. Create tenant (+ subscription)
          2. Invite owner
          3. Owner accepts (Auth0 signup/login)
          4. First-login setup wizard
```

### 6.2 Roles

**Status: NORMATIVE.**

- **Platform operator** — a Support User (`is_staff=True`) with the capability to create organizations and set subscriptions. Works from the platform console at `https://mypipelinehero.com/platform/`.
- **Prospective owner** — the person who becomes the first `Owner` membership. May or may not already have a canonical `User` (and Auth0 identity).

### 6.3 Phase 1 — Create Tenant (with Subscription)

**Status: NORMATIVE.**

From the platform console, the operator opens the **Create Tenant** workflow. The form collects:

```text
name                     -- display name
slug                     -- DNS-safe; pre-flight uniqueness check
primary_contact_name
primary_contact_email
primary_contact_phone    -- optional
timezone                 -- IANA; dropdown; default America/Chicago (placeholder)
base_currency_code       -- default USD
initial_owner_email      -- becomes the first Owner
plan_code                -- Starter / Growth / Pro / Enterprise   (NEW vs. base draft)
enabled_add_ons          -- multi-select of add-on packs           (NEW)
```

Submitting requires sensitive-action re-auth (Section 8). The handler calls `services.create_organization(...)`, which **atomically**:

1. Creates the `Organization` row with `status=ACTIVE`.
2. Creates the `Subscription` row with the selected `plan_code`, `status=ACTIVE` (operator-created tenants start active — Locked Decision #8), and the plan's limit ceilings (`included_seats`, `max_users`, `max_locations`, `max_import_rows_per_batch`, and the other `max_*` fields per Section 7.6).
3. Creates `OrganizationAddOnSubscription` rows (`status=ACTIVE`) for each selected add-on, and applies any limit ceilings the add-on raises (e.g., Advanced Pricing add-on sets a non-zero `max_price_lists`).
4. Copies the platform default Role templates into org-scoped Role rows (Owner, Org Admin, Regional/Market/Location Manager, Sales/Service/Production Staff, Pricing Manager, Billing Staff, Viewer). Platform templates are not directly assignable; only the org-scoped copies are.
5. Creates the default `CustomerSegment` (`code=STANDARD`, `default_multiplier=1.00`, `is_default=true`).
6. Creates the default `InvoicingPolicy` with MVP defaults.
7. Creates a default empty `LaborRateCard` in DRAFT status (operators populate later; gated by `labor_rate_cards` at use time, not at seed time).
8. Sets `numbering_config` to the default numbering configuration.
9. Emits `ORG_CREATED`, `SUBSCRIPTION_CREATED` (with the on-behalf-of operator), and `ORG_SETTINGS_UPDATED`.

At this point the Organization exists with **zero memberships**. The slug-routed subdomain is reachable but rejects all traffic because there are no active memberships.

**Subscription is mandatory.** `create_organization` MUST create the `Subscription` in the same transaction. An Organization without a Subscription is a defect; the entitlement resolver tolerates a missing Subscription only inside this transaction (Section 7.8).

### 6.4 Phase 2 — Invite the Owner

**Status: NORMATIVE.**

After org creation, the console transitions to an **Invite Owner** step. The operator confirms `initial_owner_email`. The system:

1. Looks up a canonical `User` by normalized email. If found, reuse it. If not found, no `User` is pre-created — the canonical `User` and its `Auth0Identity` are created at acceptance.
2. Creates a `Membership` with `status=INVITED`, `organization_id` set, and a signed invitation token (7-day expiry, single-use) hashed at rest.
3. Assigns the org-scoped `Owner` Role (created in Phase 1) to the Membership. Owner holds all capabilities including `admin.*`.
4. Enqueues outbox entry `membership.send_invite_email` targeting `initial_owner_email`.
5. Emits `MEMBER_INVITED`.

The invite email links to the **root domain**, not the tenant subdomain:

```text
https://mypipelinehero.com/accept-invite/?token={invite_token}
```

### 6.5 Phase 3 — Owner Accepts (via Auth0)

**Status: NORMATIVE.**

The acceptance flow at `/accept-invite/` validates the token (signature, expiry, single-use), then routes the owner through Auth0:

1. **Token valid.** The flow records the pending invite in the session and redirects to Auth0 Universal Login.
2. **Auth0 authentication.** Auth0 handles credential creation (signup) for a new owner, or login for an existing one, plus MFA enrollment/challenge. MyPipelineHero builds no password or TOTP UI.
3. **Callback + identity resolution.** On the root-domain Auth0 callback, the system validates the OIDC response and resolves or links the canonical `User` from the Auth0 subject claim (Section 8). Email-based linking to an existing invited user requires a verified email from Auth0.
4. **Membership activation.** The system verifies the authenticated email matches the invite, transitions the Membership `INVITED -> ACTIVE`, and sets `accepted_at`.
5. **Audit.** Emits `MEMBER_ACCEPTED_INVITE`.
6. **Handoff.** Issues a root-domain session and a handoff token, then redirects to the tenant subdomain (Section 4.6).

Because Auth0 owns MFA, there is no separate MyPipelineHero MFA-enrollment gate at acceptance; MFA is enforced by the Auth0 policy for the connection (Section 8).

### 6.6 Phase 4 — First-Login Setup Wizard

**Status: NORMATIVE.**

On first arrival at `https://{slug}.mypipelinehero.com/`, the tenant portal renders the **Tenant Setup Wizard**, a one-time flow gated on `Organization.org_setup_complete=false`. The wizard respects the tenant's plan and limits throughout.

| Step | Required? | Content | Plan/limit interaction |
|---|---|---|---|
| 1. Welcome | No | Confirm timezone, currency, primary contact | — |
| 2. Locations | Yes (>=1) | Create first Region/Market/Location; defaults: "Default Region" -> "Default Market" -> "Main Office" with the operator-provided address | Creating beyond the first location requires `multi_location` and respects `max_locations`; the first location is always allowed |
| 3. Tax | Recommended | Create one default `TaxJurisdiction` from the location's country/region; rates added later | `tax_rates` is at least `Basic` on every plan |
| 4. Numbering | Optional | Customize entity prefixes; defaults pre-filled | — |
| 5. Team | Optional | Invite teammates | Invites respect `max_users`; the upgrade prompt appears if the ceiling is reached |
| 6. Done | — | "You're ready." Sets `org_setup_complete=true` | — |

Steps 2 and 3 cannot be skipped: the system enforces at least one Location and at least one TaxJurisdiction before the wizard can be dismissed, because the rest of the product depends on them. Steps 1, 4, and 5 are skippable with reasonable defaults.

After dismissal, the owner lands on the empty dashboard with onboarding callouts ("Create your first lead," "Create your first catalog item") until the org has at least one Lead and one Service or Product.

### 6.7 `Organization.org_setup_complete`

**Status: NORMATIVE.**

```text
org_setup_complete: BOOL, default(false)
```

Set to `true` when the Setup Wizard is dismissed by the first owner. Once `true`, it never reverts automatically. A platform operator MAY force it back to `false` from the platform console (audited `ORG_SETUP_RESET`) for support purposes.

### 6.8 Import Center During Onboarding

**Status: NORMATIVE.**

The Import Center (guided CSV import) is available during and after onboarding, gated by `import_center` and bounded by `max_import_rows_per_batch`. Its models, workflow, and write-through-services behavior are specified in Section 13 (Admin and Workflow Surfaces); this subsection states only the onboarding interaction:

- A Starter tenant has `import_center=Limited` (enabled with a small `max_import_rows_per_batch`, default 1,000). The Import Plus add-on raises the ceiling and unlocks saved mappings.
- Import batches always write through the domain service layer (e.g., location import calls `create_location`), so entitlement and limit checks (location limits, RML gating) apply identically whether a record is created by hand or by import.
- Imports that would exceed a feature gate or a plan limit are reported as per-row issues, not partial commits.

### 6.9 Edge Cases

**Status: NORMATIVE.**

| Case | Behavior |
|---|---|
| Operator creates org but never invites owner | Org exists with zero memberships, shown as "Awaiting Owner Invite." Operator may invite later or delete the unused org (`ORG_DELETED_PRE_USE`). The Subscription still exists. |
| Owner does not accept within 7 days | Membership transitions `INVITED -> EXPIRED` (beat job). Any Org Admin or the operator may issue a fresh invite (new Membership row; expired one retained for audit). |
| Owner email matches an existing User in other orgs | The `User` is reused; a new Membership is created; the user sees the org picker on next login. |
| Owner accepts then immediately resigns | An admin with `admin.members.invite` invites another user and assigns the Owner role manually. There is no "transfer ownership" workflow in the MVP (Section 22). |
| Auth0 email unverified at acceptance | Acceptance stops; the owner must complete Auth0 email verification before the Membership activates (no unverified-email linking — Section 8). |
| Plan chosen at creation lacks a feature the tenant expects | The operator changes the plan or enables an add-on in the platform console; entitlement re-resolves prospectively. |
| Slug squatting | Slugs are global; the operator intervenes manually. No automatic dispute mechanism in the MVP. |

### 6.10 Decisions Embedded in This Section

**Status: INFORMATIVE.**

- MVP onboarding is operator-mediated only; self-service signup is post-MVP.
- Org creation and owner invite are two distinct console steps.
- **The Create Tenant form selects plan and add-ons, and `create_organization` creates the `Subscription` atomically** — the principal change versus the base draft's onboarding.
- Operator-created tenants start `active` (not `trialing`).
- The first Owner Membership is created `INVITED`; activation requires Auth0 acceptance.
- Auth0 owns credential creation and MFA; MyPipelineHero builds no signup/password/TOTP UI.
- A one-time Setup Wizard runs on first login, gated on `org_setup_complete`, and respects plan limits.
- At least one Location and one TaxJurisdiction are mandatory before the wizard can be dismissed.

### 6.11 Acceptance Criteria

**Status: NORMATIVE.**

| # | Criterion | Verification |
|---|---|---|
| 1 | Create Tenant requires plan selection and supports add-on selection | view + service test |
| 2 | `create_organization` creates Organization + Subscription (+ selected add-ons) atomically | service test |
| 3 | Subscription is created with `status=ACTIVE` and the plan's limit ceilings | service test |
| 4 | Org creation seeds roles, default segment, invoicing policy, draft labor rate card, numbering | service test |
| 5 | Org creation emits `ORG_CREATED` and `SUBSCRIPTION_CREATED` with on-behalf-of operator | service test |
| 6 | A newly created org with zero memberships rejects all tenant-subdomain traffic | integration test |
| 7 | Owner invite creates an `INVITED` Membership with hashed single-use token, assigns Owner role | service test |
| 8 | Invite email links to the root-domain `/accept-invite/`, not the tenant subdomain | unit test |
| 9 | Acceptance routes through Auth0; an unverified Auth0 email blocks activation | integration test |
| 10 | Successful acceptance transitions Membership `INVITED -> ACTIVE`, issues handoff, emits `MEMBER_ACCEPTED_INVITE` | integration test |
| 11 | Expired invite (>7 days) transitions to `EXPIRED`; re-invite creates a new Membership row | service test |
| 12 | Setup Wizard renders only while `org_setup_complete=false` | view test |
| 13 | Wizard cannot be dismissed without >=1 Location and >=1 TaxJurisdiction | view + service test |
| 14 | Creating a second location during the wizard requires `multi_location` and respects `max_locations` | service test |
| 15 | Team-invite step respects `max_users` and shows the upgrade prompt at the ceiling | view test |
| 16 | Import during onboarding writes through domain services and respects `import_center` + row limit | integration test |
| 17 | Dismissing the wizard sets `org_setup_complete=true`; it does not auto-revert | service test |

---

## Section 7 — Packages, Tiers, Entitlements, and Limits

### 7.1 Purpose and Position in the Architecture

**Status: NORMATIVE.**

Entitlements answer a different question than RBAC. RBAC answers *"can this **user** perform this action?"* Entitlements answer *"did this **tenant** pay for this capability?"* Both gates are independent, and **both must pass** for a restricted operation to proceed.

```text
Request → RBAC check (require_capability)  → user allowed?
        → Entitlement check (require_feature) → tenant paid?
        → Plan-limit check (where applicable)  → under the ceiling?
        → Service-layer mutation
```

Entitlement is a tenant-level concern resolved from the tenant's `Subscription`, active add-on packs, and any organization-specific overrides. It is enforced in the **service layer** (Section 16), so every surface — HTMX views, the internal DRF API, Celery tasks that create restricted records, and the post-MVP React portal — inherits enforcement without re-implementation.

In the MVP, plan and add-on assignment is **operator-managed** in the platform console. There is no payment processor, no self-service signup, and no self-service plan changes (Section 22).

### 7.2 Plans

**Status: NORMATIVE for codes and structure; INFORMATIVE for prices.**

The MVP ships four plans. Public prices are product/marketing decisions and are INFORMATIVE here; the **plan codes**, **included/limit values**, and **feature mapping** are NORMATIVE because code, seed data, migrations, tests, and audit events depend on them.

| Plan | Code | Monthly (info) | Included users | Intended customer |
|---|---|---:|---:|---|
| Starter | `starter` | $149 | 3 | Small teams moving off spreadsheets / simple CRM |
| Growth | `growth` | $399 | 10 | Default plan for operating businesses |
| Pro | `pro` | $799 | 20 | Advanced pricing, operations, and manufacturing |
| Enterprise | `enterprise` | from $1,500 / custom | custom | Larger / multi-market / migration / SLA tenants |

```python
class PlanCode(models.TextChoices):
    STARTER = "starter", "Starter"
    GROWTH = "growth", "Growth"
    PRO = "pro", "Pro"
    ENTERPRISE = "enterprise", "Enterprise"
```

### 7.3 Add-On Packs

**Status: NORMATIVE.**

Advanced features are sold to lower-tier tenants as **curated add-on packs**, not as dozens of individual switches. An add-on pack is a named bundle of feature codes that resolves through the same entitlement flow as base-plan features.

| Add-On Pack | Code | Enables (feature codes) | Availability (info) |
|---|---|---|---|
| Multi-Location | `multi_location` | `multi_location`, `rml_scope` (limited) | Starter, Growth |
| Work Orders | `work_orders` | `work_orders` | Starter |
| Purchasing | `purchasing` | `purchase_orders`, `suppliers`, `supplier_costs` | Starter |
| Advanced Pricing | `advanced_pricing` | `price_lists`, `client_contract_pricing`, `customer_segments`, `labor_rate_cards`, `advanced_pricing_rules` (limited) | Starter, Growth |
| Bundles | `bundles` | `bundles` (basic component-sum / fixed-price only) | Starter, Growth |
| Import Plus | `import_plus` | larger import batches, saved mappings, assisted validation (raises `import_center` limits) | Starter, Growth |

```python
class AddOnCode(models.TextChoices):
    MULTI_LOCATION = "multi_location", "Multi-Location"
    WORK_ORDERS = "work_orders", "Work Orders"
    PURCHASING = "purchasing", "Purchasing"
    ADVANCED_PRICING = "advanced_pricing", "Advanced Pricing"
    BUNDLES = "bundles", "Bundles"
    IMPORT_PLUS = "import_plus", "Import Plus"
```

Note the deliberate naming overlap: the add-on **code** `multi_location` is distinct from the feature **code** `multi_location`. The `PlanAddOnEntitlement` join is what maps an add-on code to the set of feature codes it enables. Some features (`bom_manufacturing`, `build_orders`, `pricing_approvals`, `promotions`, `configurable_bundles`, advanced reporting, custom overrides, historical migration) are **never** offered à la carte to Starter; they require Pro or Enterprise.

### 7.4 Feature-Code Registry

**Status: NORMATIVE.**

Feature codes are stable strings. They appear in code, migrations, tests, audit events, seed data, and support tooling, and **MUST NOT be renamed casually**; a rename is a migration plus a guide PR. Adding a feature code requires a guide PR amending this table.

In the matrix below: **Yes** = enabled; **Lim** = enabled with a plan limit (Section 7.6); **Basic** = enabled with reduced configuration depth; **No** = denied (unless an add-on or override enables it).

| Feature Code | Description | Starter | Growth | Pro | Enterprise |
|---|---|:--:|:--:|:--:|:--:|
| `leads` | Lead management | Yes | Yes | Yes | Yes |
| `clients` | Client management | Yes | Yes | Yes | Yes |
| `tasks` | Task management | Yes | Yes | Yes | Yes |
| `communications` | Notes + outbound messages | Yes | Yes | Yes | Yes |
| `basic_catalog` | Services + simple products | Yes | Yes | Yes | Yes |
| `basic_quotes` | Quote creation + versioning | Yes | Yes | Yes | Yes |
| `basic_invoicing` | Invoices + payment recording | Yes | Yes | Yes | Yes |
| `standard_reports` | Fixed reports + CSV exports | Yes | Yes | Yes | Yes |
| `tenant_export` | Tenant export requests | Yes | Yes | Yes | Yes |
| `tenant_deletion` | Tenant deletion / offboarding | Yes | Yes | Yes | Yes |
| `import_center` | Guided CSV import center | Lim | Yes | Yes | Yes |
| `multi_location` | More than one operating location | Lim | Yes | Yes | Yes |
| `customer_segments` | Segment-based pricing inputs | Lim | Yes | Yes | Yes |
| `tax_rates` | Tax jurisdictions + rates | Basic | Yes | Yes | Yes |
| `sales_orders` | Sales order workflow | Lim | Yes | Yes | Yes |
| `rml_scope` | Region/Market/Location scoping | No | Yes | Yes | Yes |
| `work_orders` | Work order workflow | No | Yes | Yes | Yes |
| `purchase_orders` | Purchase order workflow | No | Yes | Yes | Yes |
| `suppliers` | Supplier management | No | Yes | Yes | Yes |
| `supplier_costs` | Supplier product/material costs | No | Yes | Yes | Yes |
| `price_lists` | Price list management | No | Yes | Yes | Yes |
| `client_contract_pricing` | Client-specific contract pricing | No | Yes | Yes | Yes |
| `labor_rate_cards` | Labor role cost/bill rates | No | Lim | Yes | Yes |
| `advanced_pricing_rules` | Advanced pricing rule config | No | Lim | Yes | Yes |
| `manual_price_overrides` | Manual quote-line override workflow | No | Lim | Yes | Yes |
| `bundles` | Bundle definitions + component-sum | No | Lim | Yes | Yes |
| `advanced_reporting` | Advanced operational/margin reports | No | Lim | Yes | Yes |
| `pricing_approvals` | Approval workflow | No | No | Yes | Yes |
| `configurable_bundles` | Configurable bundle options | No | No | Yes | Yes |
| `promotions` | Promotion campaign modifiers | No | No | Yes | Yes |
| `raw_materials` | Raw material catalog | No | Lim | Yes | Yes |
| `bom_manufacturing` | BOMs + manufactured-product quoting | No | No | Yes | Yes |
| `bom_versioning` | Effective-dated BOM versions | No | No | Yes | Yes |
| `build_orders` | Build order workflow | No | No | Yes | Yes |
| `build_labor_tracking` | Build labor entries + adjustments | No | No | Yes | Yes |
| `build_cost_variance` | Estimated vs. actual build variance | No | No | Yes | Yes |
| `entitlement_overrides` | Org-specific feature overrides | No | No | No | Yes |
| `custom_import_mapping` | Custom migration/import mapping | No | No | Add-on | Yes |

The feature-code registry is defined once in seed data (`seed_v1`) and validated by a CI test asserting the registry matches this table.

### 7.5 Entitlement Models

**Status: NORMATIVE.**

These models live in `apps/platform/subscriptions/` and are built in milestone M2A (Section 21), immediately after RBAC and audit. All carry UUID v7 primary keys except where noted; field-level model conventions follow Section 15.

```text
Subscription
  id: UUID, pk
  organization_id: UUID, fk -> Organization on_delete=PROTECT, unique
  plan_code: TEXT                                  -- PlanCode
  status: ENUM(TRIALING, ACTIVE, PAST_DUE, SUSPENDED, CANCELLED)
  included_seats: INT, default(1)
  max_users: INT, null                             -- null = unlimited (Enterprise)
  max_locations: INT, null
  max_import_rows_per_batch: INT, default(1000)
  max_price_lists: INT, null
  max_client_contracts: INT, null
  max_promotion_campaigns: INT, null
  max_boms: INT, null
  max_labor_rate_cards: INT, null
  file_storage_bytes: BIGINT, null
  audit_retention_tier: ENUM(STANDARD, EXTENDED, CUSTOM), default(STANDARD)
  current_period_ends_at: TIMESTAMPTZ, null
  created_at, updated_at: TIMESTAMPTZ

PlanEntitlement                                    -- platform-level; not tenant-owned
  id: UUID, pk
  plan_code: TEXT
  feature_code: TEXT
  is_enabled: BOOL, default(true)
  unique_together (plan_code, feature_code)

PlanAddOnEntitlement                               -- platform-level
  id: UUID, pk
  add_on_code: TEXT
  feature_code: TEXT
  is_enabled: BOOL, default(true)
  unique_together (add_on_code, feature_code)

OrganizationAddOnSubscription
  id: UUID, pk
  organization_id: UUID, fk -> Organization on_delete=CASCADE
  add_on_code: TEXT
  status: ENUM(TRIALING, ACTIVE, CANCELLED, EXPIRED)
  starts_at: TIMESTAMPTZ
  ends_at: TIMESTAMPTZ, null
  created_at, updated_at: TIMESTAMPTZ
  unique_together (organization_id, add_on_code)

OrganizationEntitlementOverride
  id: UUID, pk
  organization_id: UUID, fk -> Organization on_delete=CASCADE
  feature_code: TEXT
  is_enabled: BOOL                                 -- may force-enable OR force-disable
  reason: TEXT                                     -- required
  granted_by_id: UUID, fk -> User
  expires_at: TIMESTAMPTZ, null
  created_at, updated_at: TIMESTAMPTZ
  unique_together (organization_id, feature_code)
```

`PlanEntitlement` and `PlanAddOnEntitlement` are **platform-level** (no `organization_id`) — they are the seeded mapping from plan/add-on to feature codes. The per-tenant records are `Subscription`, `OrganizationAddOnSubscription`, and `OrganizationEntitlementOverride`.

The `Subscription.max_*` ceilings carry the "Limited" cells from Section 7.4 as numbers (Section 7.6). A null limit means unlimited (used by Enterprise and by limits a plan does not constrain).

### 7.6 Plan Limits

**Status: NORMATIVE for code/structure; INFORMATIVE for specific values.**

"Limited" in the feature matrix is modeled as **the feature code enabled plus a numeric ceiling** on `Subscription`. The feature works; the count is bounded. This avoids a third entitlement state.

| Limit | Subscription field | Starter | Growth | Pro | Enterprise |
|---|---|---:|---:|---:|---:|
| Included users | `included_seats` | 3 | 10 | 20 | custom |
| Max active users | `max_users` | 5 | 25 | 75 | null |
| Included locations | (info) | 1 | 5 | 25 | custom |
| Max active locations | `max_locations` | 1 | 25 | 100 | null |
| Import rows / batch | `max_import_rows_per_batch` | 1,000 | 10,000 | 50,000 | custom |
| File storage | `file_storage_bytes` | 5 GB | 50 GB | 250 GB | null |
| Active price lists | `max_price_lists` | 0 | 10 | null | null |
| Active client contracts | `max_client_contracts` | 0 | 100 | null | null |
| Active promotion campaigns | `max_promotion_campaigns` | 0 | 0 | 100 | null |
| Active BOMs | `max_boms` | 0 | 0 | null | null |
| Active labor rate cards | `max_labor_rate_cards` | 0 | 1 | null | null |
| Audit retention | `audit_retention_tier` | STANDARD | STANDARD | EXTENDED | CUSTOM |

Where a limit is `0` for a plan, the corresponding feature code is also `No` for that plan (e.g., Starter `max_price_lists=0` and `price_lists=No`) — the feature gate denies before the limit is ever consulted. A limit only matters when its feature is enabled. Add-on packs that enable a feature also set the appropriate ceiling (e.g., the Advanced Pricing add-on enabling `price_lists` for a Starter tenant sets a non-zero `max_price_lists`, applied as part of provisioning the add-on).

### 7.7 Entitlement Resolution

**Status: NORMATIVE.**

Resolution precedence is **organization override → base plan entitlement → active add-on entitlement → deny**. Resolution returns `False` when the subscription status is not in `{active, trialing}`.

```python
# NORMATIVE: behavior. Implementation is request-scoped cached (see 7.8).
def has_feature(*, organization_id: UUID, feature_code: str) -> bool:
    sub = get_subscription(organization_id)               # cached per request
    if sub.status not in {SubscriptionStatus.ACTIVE, SubscriptionStatus.TRIALING}:
        return False

    override = get_override(organization_id, feature_code) # cached
    if override is not None and not override.is_expired():
        return override.is_enabled                         # may force-enable OR force-disable

    if plan_enables(sub.plan_code, feature_code):          # cached PlanEntitlement set
        return True

    for add_on in active_add_ons(organization_id):         # cached
        if add_on_enables(add_on.add_on_code, feature_code):
            return True

    return False


def require_feature(*, organization_id: UUID, feature_code: str) -> None:
    if not has_feature(organization_id=organization_id, feature_code=feature_code):
        sub = get_subscription(organization_id)
        raise FeatureNotEntitledError(feature_code=feature_code, plan_code=sub.plan_code)
```

An **override is bidirectional**: it can force-enable a feature above a tenant's plan (e.g., a custom Enterprise grant) or force-disable a feature (e.g., a compliance or support hold). Overrides are Enterprise/support-only, require a `reason`, are audited, and are visible to support users.

Plan-limit enforcement is separate and applies at create paths:

```python
# NORMATIVE: behavior
def enforce_limit(*, organization_id: UUID, limit_field: str, current_count: int) -> None:
    sub = get_subscription(organization_id)
    ceiling = getattr(sub, limit_field)
    if ceiling is None:                 # null = unlimited
        return
    if current_count >= ceiling:
        raise PlanLimitExceededError(limit_name=limit_field, limit_value=ceiling)
```

`FeatureNotEntitledError` and `PlanLimitExceededError` are part of the domain exception taxonomy (Section 16) and both map to HTTP 403 with distinct `error_code` values (`feature_not_entitled`, `plan_limit_exceeded`).

### 7.8 Request-Scoped Resolution and Caching

**Status: NORMATIVE.**

Entitlement resolution MUST be request-scoped cached to avoid N+1 queries on gated service calls:

- On first entitlement query within a request (or within an outbox worker invocation), the resolver loads the tenant's `Subscription`, active `OrganizationAddOnSubscription` rows, and `OrganizationEntitlementOverride` rows, plus the relevant seeded `PlanEntitlement` / `PlanAddOnEntitlement` sets, and caches them keyed by `organization_id` for the duration of that request/invocation.
- All subsequent `has_feature` calls in the same request answer from the cache.
- The platform-level `PlanEntitlement` / `PlanAddOnEntitlement` seed sets are stable between deploys and MAY additionally be process-cached with invalidation on the (rare) seed migration.
- The resolver tolerates a **missing `Subscription`** only during the organization-creation transaction (the `Subscription` row is created in the same transaction as the `Organization`, mirroring the `InvoicingPolicy` pattern). Outside that transaction, a missing `Subscription` is a defect and raises `ConfigurationError`.

Celery tasks and management commands that create restricted records MUST call `require_feature` (resolved against the org on the task payload), except maintenance-only tasks (retention pruning, partition pre-creation) which are exempt.

### 7.9 Two-Gate Enforcement Pattern

**Status: NORMATIVE.**

Restricted operations are protected at both the view and service layers. The service layer is the authoritative boundary; the view decorator and template hiding are conveniences.

```python
# View layer (convenience + correct HTTP/UX): both gates declared
@require_capability("catalog.bom.manage")     # RBAC
@require_plan_feature("bom_manufacturing")     # entitlement → renders upgrade prompt on deny
def bom_create_view(request, product_id):
    ...

# Service layer (authoritative): both gates enforced
def create_bom_version(*, organization_id, actor_id, product_id, lines, ...) -> BOMVersion:
    """
    Required capability: catalog.bom.manage
    Required feature:    bom_manufacturing
    Required limit:      active BOMs < max_boms
    """
    require_feature(organization_id=organization_id, feature_code="bom_manufacturing")
    # ... capability check, limit check, mutation
```

Template navigation hiding uses a `has_feature` template tag so users do not see entry points to features their tenant lacks — but hiding a link is never a security control; the service-layer `require_feature` is.

### 7.10 Domain Gating Map

**Status: NORMATIVE.**

This is the authoritative map of which service operations require which feature code. It is the contract every gated domain section (Sections 9–12) references.

| Domain operation | Feature code | Limit (where applicable) |
|---|---|---|
| Create additional location (beyond first) | `multi_location` | `max_locations` |
| Assign RML scope; scoped querysets | `rml_scope` | — |
| Create/manage sales orders | `sales_orders` | — |
| Create/manage work orders | `work_orders` | — |
| Create/manage purchase orders; suppliers | `purchase_orders`, `suppliers`, `supplier_costs` | — |
| Create/manage price lists | `price_lists` | `max_price_lists` |
| Create/manage client contract pricing | `client_contract_pricing` | `max_client_contracts` |
| Create/manage customer segments | `customer_segments` | — |
| Create/manage tax jurisdictions/rates | `tax_rates` | — |
| Create/manage labor rate cards | `labor_rate_cards` | `max_labor_rate_cards` |
| Create/manage advanced pricing rules | `advanced_pricing_rules` | — |
| Manual price override on a quote line | `manual_price_overrides` | — |
| Request/grant pricing approvals | `pricing_approvals` | — |
| Create/manage bundles | `bundles` | — |
| Configurable bundle options | `configurable_bundles` | — |
| Create/manage promotion campaigns | `promotions` | `max_promotion_campaigns` |
| Create/manage raw materials | `raw_materials` | — |
| Create/manage BOMs; quote manufactured products | `bom_manufacturing` | `max_boms` |
| Activate BOM versions | `bom_versioning` | — |
| Create/manage build orders | `build_orders` | — |
| Record/adjust build labor | `build_labor_tracking` | — |
| View build cost variance | `build_cost_variance` | — |
| Run advanced reports | `advanced_reporting` | — |
| Import via Import Center | `import_center` | `max_import_rows_per_batch` |
| Manage organization entitlement overrides | `entitlement_overrides` | — |

Features without an entry (leads, clients, tasks, communications, basic catalog, basic quotes, basic invoicing, standard reports, tenant export/deletion) are universal and require no `require_feature` call.

### 7.11 Downgrade Behavior

**Status: NORMATIVE.**

Downgrades and status changes **never automatically delete tenant business data.** A downgrade disables creation and editing of newly-restricted records while preserving read-only access to existing records.

| Scenario | Behavior |
|---|---|
| Pro tenant with BOMs → Growth | Existing BOMs remain visible read-only; new BOM creation blocked (`bom_manufacturing` now denied) |
| Growth tenant with multiple locations → Starter | Existing locations remain; creating additional locations blocked (`max_locations` exceeded) |
| Pro tenant with pricing approvals → Growth | Existing approvals remain in history; new approval workflows blocked |
| Tenant becomes `past_due` | `has_feature` returns `False` for all features (status gate); read access governed by org status; high-value mutations blocked |
| Tenant `suspended` | Tenant-portal access blocked at handoff per organization status (Section 5) |

Because `has_feature` returns `False` when status leaves `{active, trialing}`, a `past_due` or `suspended` subscription degrades gracefully to read-only at the feature gate without per-feature special-casing. Read-only enforcement for downgraded-but-active tenants relies on the create/edit paths calling `require_feature`; list/detail (read) paths do not call `require_feature` and therefore remain accessible.

When a feature is downgraded, the tenant portal surfaces affected records with a non-blocking banner explaining they are read-only on the current plan.

### 7.12 Upgrade Prompt UX

**Status: NORMATIVE.**

A normal tenant user blocked by entitlement (not by RBAC) MUST see an upgrade prompt, not a raw 403. The distinction:

- **RBAC denial** (`CapabilityRequiredError`) → "You don't have permission to perform this action."
- **Entitlement denial** (`FeatureNotEntitledError`) → upgrade prompt naming the required plan.

Server-rendered prompt:

```text
BOM manufacturing is available on the Pro plan.
Your current plan: Growth
[Contact your administrator]   [Learn about Pro]
```

Because the MVP has no self-service upgrade, the prompt routes to "contact administrator / contact support" rather than a checkout flow. The DRF API error envelope for entitlement denial:

```json
{
  "error_code": "feature_not_entitled",
  "message": "Feature 'bom_manufacturing' is not available on plan 'growth'.",
  "details": { "feature": "bom_manufacturing", "required_plan": "pro", "current_plan": "growth" }
}
```

`drf-spectacular` documents this envelope. The post-MVP React portal renders the same upgrade prompt from the `X-Error-Code` header and `details`.

### 7.13 Operator Management (Platform Console)

**Status: NORMATIVE.**

In the MVP, the platform console (support/`is_staff` users) is the sole interface for subscription management:

- Set or change a tenant's `plan_code` (sensitive action; re-auth required; emits `SUBSCRIPTION_PLAN_CHANGED`).
- Enable or disable add-on packs (`OrganizationAddOnSubscription`); emits `ADD_ON_ENABLED` / `ADD_ON_DISABLED`.
- Create/edit/expire `OrganizationEntitlementOverride` rows (sensitive; requires `reason`; emits `ENTITLEMENT_OVERRIDE_SET` / `_CLEARED`).
- Adjust `Subscription` limit ceilings for Enterprise/custom tenants.

Changing a plan or add-on re-provisions the tenant's effective limits. Changes apply prospectively; existing records are never deleted. There is no tenant-facing self-service plan change in the MVP (Section 22).

### 7.14 SaaS Billing Separation

**Status: NORMATIVE.**

Platform SaaS subscription billing and tenant→customer invoicing are **strictly separate domains**:

- `Subscription` / add-ons / overrides describe what **MyPipelineHero charges its tenants**. In the MVP there is no payment processor; these are operator-set records only.
- `Invoice` / `Payment` (Section 12) describe what **a tenant charges its own customers**. These are tenant business records.

The two never share models, tables, or numbering. Payment-provider integration for SaaS subscriptions is post-MVP (Section 22).

### 7.15 Entitlement Audit Events

**Status: NORMATIVE.**

Entitlement changes are audited (category `ADMIN`, retained per the ADMIN retention policy in Section 17):

```text
SUBSCRIPTION_CREATED
SUBSCRIPTION_PLAN_CHANGED
SUBSCRIPTION_STATUS_CHANGED
SUBSCRIPTION_LIMITS_UPDATED
ADD_ON_ENABLED
ADD_ON_DISABLED
ENTITLEMENT_OVERRIDE_SET
ENTITLEMENT_OVERRIDE_CLEARED
FEATURE_ACCESS_DENIED            -- sampled; emitted when require_feature denies
```

`FEATURE_ACCESS_DENIED` is sampled (not every denial) to avoid audit noise while preserving signal for support investigation. Plan/status/override changes are always audited and carry the on-behalf-of operator.

### 7.16 Acceptance Criteria

**Status: NORMATIVE.**

| # | Criterion | Verification |
|---|---|---|
| 1 | The four plans and six add-on packs exist in seed data with the exact codes in 7.2/7.3 | `pytest` seed test |
| 2 | The feature-code registry matches Section 7.4 exactly | registry completeness test |
| 3 | `PlanEntitlement` seed rows match the 7.4 matrix for every (plan, feature) | parametrized seed test |
| 4 | `PlanAddOnEntitlement` seed rows match the 7.3 add-on→feature mapping | parametrized seed test |
| 5 | `has_feature` returns `False` when subscription status ∉ {active, trialing} | service test |
| 6 | Resolution precedence override → plan → add-on → deny is honored | service test (each branch) |
| 7 | A force-disable override denies a feature the plan would otherwise grant | service test |
| 8 | `require_feature` raises `FeatureNotEntitledError` (HTTP 403, `feature_not_entitled`) on deny | service + API test |
| 9 | Add-on activation enables its mapped features for the tenant | integration test |
| 10 | `enforce_limit` raises `PlanLimitExceededError` at the ceiling; passes when `null` | service test |
| 11 | "Limited" features are enabled with a non-zero limit; `0`-limit features are also feature-denied | service test |
| 12 | Entitlement resolution is request-scoped cached (no N+1 on repeated `has_feature`) | query-count test |
| 13 | Service layer enforces `require_feature` even when the view decorator is absent | service test |
| 14 | A gated Celery task that creates a restricted record calls `require_feature` | service test |
| 15 | Downgrade preserves existing records read-only; blocks new creation | integration test |
| 16 | `past_due` / `suspended` degrade to read-only via the status gate | service test |
| 17 | Entitlement denial renders an upgrade prompt (not raw 403) for tenant users | view test |
| 18 | Operator plan change is sensitive (re-auth) and emits `SUBSCRIPTION_PLAN_CHANGED` | integration test |
| 19 | Override set/clear requires `reason`, is audited, visible to support | integration test |
| 20 | `Subscription` is created in the same transaction as `Organization`; absent only mid-creation | service test |
| 21 | SaaS subscription records share no tables with tenant `Invoice`/`Payment` | architecture review |

---

## Section 8 — Identity and Access Control

### 8.1 Overview and Separation of Concerns

**Status: NORMATIVE.**

Identity and access in MyPipelineHero is layered, and each layer answers exactly one question:

```text
Auth0            -> Who is this person?         (authentication, MFA, credentials)
Canonical User   -> Which platform identity?    (the durable identity record)
Membership       -> Access to which tenant?     (the tenant-access record)
RBAC             -> Can this user do it?         (capabilities)
RML scope        -> On which records?            (operating scope)
Entitlement      -> Did this tenant pay for it?  (Section 7; separate gate)
```

Auth0 proves identity. It never grants tenant access, roles, capabilities, or operating scope. Tenant authorization is determined entirely by the MyPipelineHero Membership/RBAC/RML model. An Auth0 login with zero memberships yields zero tenant access.

The clean division of ownership:

| Auth0 owns | Django/MyPipelineHero owns |
|---|---|
| Login UI (Universal Login) | Canonical `User` rows |
| Credential storage and verification | `Auth0Identity` linkage |
| Signup (at invite acceptance) | Membership resolution |
| Password reset | RBAC and operating-scope authorization |
| MFA challenge, enrollment, recovery | Root-domain session after callback |
| Social/enterprise IdP federation | Signed tenant handoff issuance |
| Auth0-side attack protection | Tenant-local session establishment |
| | Audit events |

No locally-managed passwords, no local TOTP machinery, and no `django-allauth` are built (Locked Decision #1).

### 8.2 Custom User Model

**Status: NORMATIVE.**

A custom `User` model is mandatory from migration #1; retrofitting `AUTH_USER_MODEL` after deployment is prohibited.

```python
AUTH_USER_MODEL = "platform_accounts.User"
```

```text
User
  id: UUID, pk                                       -- UUID v7
  email: TEXT, unique, lowercase-normalized          -- primary platform identity
  is_active: BOOL, default(true)
  is_staff: BOOL, default(false)                     -- may access platform console
  is_superuser: BOOL, default(false)                 -- RBAC short-circuit grant
  is_system: BOOL, default(false)                    -- the System User
  last_login_at: TIMESTAMPTZ, null
  created_at: TIMESTAMPTZ
  updated_at: TIMESTAMPTZ

  CHECK: is_system implies (is_active AND NOT is_staff AND NOT is_superuser)
  CHECK: lower(email) = email
```

`USERNAME_FIELD = "email"`; `REQUIRED_FIELDS = []`. The model has **no `password`, `totp_secret`, `backup_codes_hash`, `failed_login_count`, or `locked_until` fields** — all credential and MFA state lives in Auth0. Django uses an unusable password for every `User` (`set_unusable_password()`); the Django password field exists only because `AbstractBaseUser` provides it and is never set to a usable value.

| Flag | Meaning |
|---|---|
| `is_active` | Account is operational; an inactive user cannot complete handoff |
| `is_staff` | User may access the platform console |
| `is_superuser` | RBAC short-circuits to grant (platform-level only) |
| `is_system` | The single System User; appears as actor on automated transitions |

### 8.3 Auth0 Identity Linkage

**Status: NORMATIVE.**

The canonical `User` is linked to one or more Auth0 identities by subject claim:

```text
Auth0Identity
  id: UUID, pk                                       -- UUID v7
  user_id: UUID, fk -> User on_delete=CASCADE
  auth0_subject: TEXT, unique                        -- the OIDC `sub` claim; stable identity key
  connection: TEXT                                   -- e.g. "Username-Password-Authentication",
                                                     --      "google-oauth2", "okta"
  email_at_provider: TEXT
  email_verified: BOOL
  last_login_at: TIMESTAMPTZ, null
  created_at: TIMESTAMPTZ
  updated_at: TIMESTAMPTZ

  unique_together (auth0_subject)
  index (user_id)
```

The **`auth0_subject` (the `sub` claim) is the stable identity key** — never email. A single canonical `User` MAY have multiple `Auth0Identity` rows (e.g., a user who has both a database connection and a Google connection in Auth0, account-linked at the Auth0 side). Email is used only for first-time account matching during invite acceptance, and only when Auth0 reports the email verified (Section 8.6).

### 8.4 Membership Model

**Status: NORMATIVE.**

Membership is the authoritative tenant-access record. Auth0 login MUST NOT create a Membership.

```text
Membership
  id: UUID, pk                                       -- UUID v7
  user_id: UUID, fk -> User on_delete=PROTECT
  organization_id: UUID, fk -> Organization on_delete=PROTECT
  status: ENUM(INVITED, ACTIVE, SUSPENDED, INACTIVE, EXPIRED)
  invited_by_id: UUID, fk -> User, null
  invited_at: TIMESTAMPTZ, null
  invitation_expires_at: TIMESTAMPTZ, null
  invitation_token_hash: TEXT, null                  -- hashed; field-encrypted at rest (Section 17)
  accepted_at: TIMESTAMPTZ, null
  first_name: TEXT
  last_name: TEXT
  phone: TEXT, null
  is_default_for_user: BOOL, default(false)
  suspended_reason: TEXT, null

  unique_together (user_id, organization_id)
  partial_index (user_id) where is_default_for_user
```

Membership status governs tenant access. Only `ACTIVE` memberships can complete handoff. The membership state machine (Section 9 state-machine catalog) is:

| From | To | Trigger | Actor | Notes |
|---|---|---|---|---|
| Invited | Active | accept_invite | Invited user | Via Auth0 acceptance; `accepted_at` set |
| Invited | Expired | invite_expiry | System (beat) | After 7 days |
| Active | Inactive | deactivate | Org admin | Data retained |
| Active | Suspended | suspend | Org admin | `suspended_reason` required |
| Suspended | Active | reinstate | Org admin | — |
| Suspended | Inactive | deactivate | Org admin | — |
| Inactive | Active | reactivate | Org admin | — |

The active-user count (against `Subscription.max_users`, Section 7.6) counts `ACTIVE` memberships. Inviting or reactivating a member when the org is at its `max_users` ceiling raises `PlanLimitExceededError`.

### 8.5 System User and Support User

**Status: NORMATIVE.**

**System User.** Exactly one `User` per environment has `is_system=true`, created by the `seed_v1` migration. It has an unusable password, no `Auth0Identity` (it never logs in interactively), and appears as the actor on automated state transitions (beat jobs, outbox workers). The CHECK constraint forbids it from being staff or superuser.

**Support User.** A `User` with `is_staff=true` (usually `is_superuser=false`). Support users authenticate through Auth0 like everyone else, land on the platform console (Section 8.13), and may enter tenant contexts only through audited impersonation (Section 8.14). Support users are subject to the same Auth0 MFA policy as all users.

### 8.6 Login Flow (Auth0 OIDC)

**Status: NORMATIVE.**

All authentication starts on the root domain and delegates to Auth0. Tenant subdomains never initiate Auth0 login.

```text
1.  User -> GET https://mypipelinehero.com/login
2.  Django builds an OIDC authorization request (Authlib): generates state + nonce + PKCE,
    stores them in the pre-auth session, redirects to Auth0 Universal Login.
3.  Auth0 authenticates the user (credentials + MFA per the connection's policy).
4.  Auth0 redirects to the ROOT-DOMAIN callback:
    https://mypipelinehero.com/auth/callback?code=...&state=...
5.  Django validates the callback (Section 8.7) and exchanges the code for tokens.
6.  Django resolves or links the canonical User from the `sub` claim (Section 8.8).
7.  Django establishes a ROOT-DOMAIN session (no tenant access yet) and records
    mfa_satisfied_at from the ID token's `auth_time`/`amr` claims.
8.  Django loads the user's ACTIVE memberships and branches:
    a. 0 active memberships, not is_staff  -> "no active access" page
    b. 0 active memberships, is_staff       -> 302 /platform/
    c. 1 active membership                  -> issue handoff token
    d. 2+ active memberships                -> organization picker
    e. is_staff WITH memberships            -> choice: platform console or pick org
9.  User selects an org if required.
10. Django issues a handoff token (Section 8.10).
11. Tenant subdomain consumes the token and establishes a tenant-local session (Section 8.11).
```

There is a single login entry point (`/login`) regardless of connection. The Universal Login screen presents whatever connections Auth0 is configured with (database, Google, enterprise SSO). MyPipelineHero does not render connection-specific UI; it sends users to Auth0 and reads the result.

### 8.7 Callback Validation

**Status: NORMATIVE.**

The OIDC callback MUST validate, before establishing any session:

- `state` matches the value stored pre-auth (CSRF protection on the auth flow).
- `nonce` in the ID token matches the value stored pre-auth (replay protection).
- PKCE `code_verifier` is presented in the token exchange.
- ID token signature verifies against Auth0's JWKS (`jwks_uri`, cached with rotation).
- `iss` equals the configured Auth0 issuer.
- `aud` equals the configured client ID.
- Token `exp` is in the future; `iat`/`auth_time` are sane.
- `email_verified` is `true` if the flow requires a verified email (invite acceptance and email-based linking always require it).

Validation failures emit `LOGIN_FAILED` (with a normalized reason, never tokens) and render a generic error. Authorization codes, access tokens, ID tokens, refresh tokens, and the client secret MUST NOT be logged or stored in audit metadata.

### 8.8 Canonical User Resolution

**Status: NORMATIVE.**

```python
def resolve_auth0_user(*, claims: Auth0Claims) -> User:
    """
    Resolve or link an Auth0 identity to a canonical User.
    Does NOT create Membership, Role, Capability, or operating scope.
    """
```

Resolution order:

1. Find an existing `Auth0Identity` by `auth0_subject` (`sub`). If found, return its linked active `User`. This is the steady-state path.
2. If not found and the flow is an **invite acceptance** with a verified email matching the invited Membership's email, link the new `Auth0Identity` to the canonical `User` (creating the `User` if none exists). See Section 8.9.
3. If not found and the flow is a **plain login** (no pending invite): if an `Auth0Identity` does not exist and no invite context is present, the user has no path to access. Render "no active access / invitation required." MyPipelineHero does **not** auto-create users on arbitrary Auth0 logins — there is no self-service signup in the MVP.

Raw Auth0 claims (groups, app_metadata, roles) MUST NOT be used in authorization decisions. Auth0 proves identity only; MyPipelineHero's Membership/RBAC model is authoritative.

### 8.9 Account Linking Rules

**Status: NORMATIVE.**

Linking an Auth0 identity to an existing canonical `User` by email is permitted only when **all** of the following hold:

1. Auth0 reports `email_verified = true`.
2. The flow is a controlled one — invite acceptance, or an explicit account-settings linking action that itself passes sensitive-action re-auth (Section 8.12).
3. No conflicting `Auth0Identity` already binds that subject to a different `User`.

Silent linking based on an unverified email is prohibited. If an Auth0 login presents an email matching an existing `User` but the conditions above are not met, the flow stops and renders an account-linking help page rather than guessing. This is the primary account-takeover defense (Section 17 security review verifies it).

Auth0-side account linking (one Auth0 user with multiple connections sharing a single `sub`) is the preferred mechanism for "same person, multiple login methods"; in that case MyPipelineHero sees one stable `sub` and stores one `Auth0Identity`.

### 8.10 Handoff Token Protocol

**Status: NORMATIVE.**

Tenant access is carried from the root domain to a tenant subdomain by a signed, single-use, short-lived token. This protocol is identity-provider-agnostic: it runs after Auth0 has proven identity and is unchanged from the broader design regardless of how the user authenticated.

**Issuance:**

```python
def issue_handoff_token(*, user_id, organization_id, membership_id,
                        auth_method, mfa_satisfied_at) -> str:
    token_id = secrets.token_urlsafe(32)                  # 256 bits
    primary_key = active_handoff_signing_keys()[0]        # newest non-retired
    payload = {
        "tid": token_id, "uid": str(user_id), "oid": str(organization_id),
        "mid": str(membership_id), "amr": auth_method,
        "mfa": mfa_satisfied_at.isoformat(),
        "iat": now_unix(), "exp": now_unix() + 60,         # 60-second lifetime
    }
    signed = jwt.encode(payload, primary_key.secret, algorithm="HS256",
                        headers={"kid": primary_key.key_id})
    redis.setex(f"handoff:{token_id}", 60, json.dumps({
        "used": False, "uid": str(user_id), "oid": str(organization_id),
        "mid": str(membership_id),
    }))
    audit_emit("HANDOFF_TOKEN_ISSUED", actor=user_id, organization=organization_id,
               metadata={"token_id": token_id, "kid": primary_key.key_id})
    return signed
```

**Consumption** validates the signature (trying each active signing key by `kid`), enforces single use atomically via a Redis get-and-delete pipeline, binds the token to the correct tenant host, and resolves the active membership:

```python
def consume_handoff_token(*, token, request) -> HandoffResult:
    payload = verify_with_active_keys(token)              # tries keys; rejects expired/invalid
    raw = redis_get_and_delete(f"handoff:{payload['tid']}")  # atomic single-use
    if raw is None:
        audit_emit("HANDOFF_REPLAY_DETECTED", ...); raise HandoffInvalidError("replayed")
    org = Organization.objects.get(id=payload["oid"])
    if request.get_host() != f"{org.slug}.mypipelinehero.com":
        audit_emit("HANDOFF_HOST_MISMATCH", ...); raise HandoffInvalidError("host_mismatch")
    if org.status not in (OrganizationStatus.ACTIVE, OrganizationStatus.OFFBOARDING):
        raise HandoffInvalidError("org_not_accessible")  # SUSPENDED/DELETED blocked here
    membership = Membership.objects.get(
        id=payload["mid"], user_id=payload["uid"], organization_id=payload["oid"],
        status=MembershipStatus.ACTIVE,
    )
    audit_emit("HANDOFF_TOKEN_CONSUMED", actor=membership.user_id, organization=org.id)
    return HandoffResult(user_id=UUID(payload["uid"]), organization_id=org.id,
                         membership_id=membership.id, auth_method=payload["amr"],
                         mfa_satisfied_at=parse_datetime(payload["mfa"]))
```

**Token properties:** 256-bit token id; 60-second maximum lifetime; single-use enforced atomically; bound to organization via host check; bound to an active membership; `SUSPENDED`/`DELETED` orgs blocked at consumption; replay and host-mismatch attempts emit high-severity audit events.

### 8.10.1 Handoff Signing Key Rotation

**Status: NORMATIVE.**

```text
HandoffSigningKey
  id: UUID, pk
  key_id: TEXT, unique                 -- short stable identifier, e.g. "hsk_2026q2"
  secret: BYTEA                         -- field-encrypted at rest (Section 17)
  algorithm: TEXT, default("HS256")
  created_at: TIMESTAMPTZ
  promoted_at: TIMESTAMPTZ, null        -- when it became primary (issues new tokens)
  retired_at: TIMESTAMPTZ, null         -- when it stopped being valid for verification
  CHECK: retired_at IS NULL OR retired_at > created_at
```

`active_handoff_signing_keys()` returns non-retired keys ordered newest-first; index 0 is the primary (issues new tokens), and all non-retired keys are tried for verification.

**Quarterly rotation:** (1) generate a new key; (2) promote it (it becomes primary; the prior primary stays valid for verification); (3) wait the overlap window (recommended 5 minutes — comfortably beyond the 60-second token lifetime, covering in-flight tokens and clock skew); (4) retire the prior key. **Emergency rotation** (suspected compromise): promote immediately, overlap 60 seconds, retire, and audit `HANDOFF_SIGNING_KEY_EMERGENCY_ROTATED`.

At most **two** non-retired keys may exist; holding more than two for over an hour is prohibited and fails a CI/staging check. Rotation emits `HANDOFF_SIGNING_KEY_CREATED/PROMOTED/RETIRED`, and consumption with a non-primary key emits `HANDOFF_VERIFIED_WITH_RETIRED_KEY`.

### 8.11 Sessions

**Status: NORMATIVE.**

There are two independent session types.

**Root-domain session** — established after Auth0 callback. Used for the organization picker, platform console, issuing handoff tokens, and account-settings actions (including Auth0 identity linking). It MUST NOT grant tenant data access. Logging out of the root domain invalidates outstanding handoff tokens.

**Tenant-local session** — established on a tenant subdomain after handoff consumption:

| Property | Value |
|---|---|
| Cookie name | `tenant_session_{slug}` |
| Cookie domain | `{slug}.mypipelinehero.com` |
| Cookie flags | `Secure`, `HttpOnly`, `SameSite=Lax` |
| Idle expiry | 12 hours of inactivity |
| Absolute cap | 7 days from establishment |
| Storage | Database-backed Django session |

The tenant-local session stores `user_id`, `organization_id`, `membership_id`, `auth_method`, `mfa_satisfied_at`, and `is_impersonating`. Allowed `auth_method` values: `oidc`, `impersonation`. A shared parent-domain tenant session is prohibited; each tenant subdomain has its own cookie. Session fixation protections are preserved on login. Logging out of one tenant does not affect other tenant sessions.

**Multi-tab UX.** Opening a second tenant subdomain while authenticated to a different tenant in another tab triggers a one-time soft-warning interstitial ("You're also signed in to {OtherOrg}; continuing creates an independent session in this tab"), not a forced logout.

### 8.12 Sensitive Actions and Re-Authentication

**Status: NORMATIVE.**

Sensitive actions require fresh authentication regardless of session age. With Auth0, "fresh authentication" is a **re-prompt against Auth0 using OIDC `prompt`/`max_age`**, not a local password or TOTP challenge. The user is bounced to Auth0 with `max_age` set to the required window; Auth0 re-challenges (including MFA per its policy) and returns a fresh `auth_time`, which MyPipelineHero records as `mfa_satisfied_at`.

| Action | Required freshness (`max_age`) |
|---|---|
| Quote acceptance | 5 minutes |
| Payment recording | 5 minutes |
| Payment reversal/adjustment | 5 minutes |
| Impersonation start | 5 minutes |
| Auth0 identity linking/unlinking | 5 minutes |
| Tenant data export request | 5 minutes |
| Tenant deletion request | 5 minutes |
| Subscription plan change / override (operator) | 5 minutes |
| Role/capability changes | 15 minutes |

A sensitive action checks `now - mfa_satisfied_at` against the window; if stale, it redirects through Auth0 with `max_age`, then resumes the original action. Re-auth failure destroys the tenant-local session and emits an audit event.

### 8.13 RBAC Model

**Status: NORMATIVE.**

RBAC answers "can this user do it?" It is independent of entitlement (Section 7), which answers "did this tenant pay for it?" Both gates must pass.

**Three-layer enforcement** (every protected view/action):

```text
1. Queryset scope:  .for_org(org_id) [+ .intersect_with_operating_scope(membership)]
2. View capability: require_capability("quotes.send")
3. Object check:    target.organization_id == membership.organization_id
                    AND check_operating_scope(membership, target)
                    AND state/ownership predicates
4. Audit emission:  audit_emit("QUOTE_SENT", actor, target, metadata)
```

**Permission evaluation algorithm:**

```text
1. If user.is_superuser -> GRANT (platform short-circuit)
2. If session.is_impersonating:
   - evaluate using the IMPERSONATED membership's capabilities
   - audit attribution: actor = support user; on_behalf_of = impersonated user
3. If no ACTIVE membership for (user, org) -> DENY
4. capabilities = union of capability codes from the membership's roles
5. Apply MembershipCapabilityGrant overrides: GRANT adds; DENY removes (DENY beats GRANT)
6. If required_capability not in capabilities -> DENY
7. If target provided:
   - target.organization_id != membership.organization_id -> DENY
   - state/ownership predicates fail -> DENY
8. If membership has scope assignments AND target carries location_id:
   - target.location_id not in permitted-location closure -> DENY
9. GRANT
```

**Models:**

```text
Capability        : id, code(unique), name, description, category,
                    is_deprecated, deprecated_in_version, deprecated_replacement_code
Role              : id, organization_id(null=platform template), code, name, description,
                    is_default, is_scoped_role, is_locked
                    unique_together (organization_id, code)
RoleCapability    : id, role_id, capability_id  unique_together(role_id, capability_id)
MembershipRole    : id, membership_id, role_id, assigned_by_id, assigned_at
                    unique_together(membership_id, role_id)
MembershipCapabilityGrant : id, membership_id, capability_id,
                    grant_type ENUM(GRANT, DENY), reason, granted_by_id, granted_at
                    unique_together(membership_id, capability_id)
```

Default roles are platform-seeded, locked, read-only templates (`organization_id` null). At org creation they are copied into org-scoped rows (Section 6.3); only the org-scoped copies are assignable. Tenants may compose custom roles from existing capabilities but cannot mint new capability codes in the MVP. The default role set: Owner, Org Admin, Regional Manager, Market Manager, Location Manager, Sales Staff, Service Staff, Production Staff, Pricing Manager, Billing Staff, Viewer. The full capability registry is enumerated in the data-model and domain sections (each domain section lists its capabilities); a CI capability-coverage test asserts every URL is either `@require_capability`-decorated or explicitly exempted.

**RBAC vs. entitlement, side by side:** A Pro-plan tenant entitles `bom_manufacturing`, but only a user whose role carries `catalog.bom.manage` can create a BOM. A Growth-plan tenant whose user *has* `catalog.bom.manage` still cannot create a BOM — the entitlement gate denies first. Both gates are enforced in the service layer.

### 8.14 Operating Scope (Region / Market / Location)

**Status: NORMATIVE.**

RML is a three-level operating-scope hierarchy that restricts which records a membership can see and act on. **RML scoping is entitlement-gated by `rml_scope` (Growth+).** When `rml_scope` is not entitled, the tenant operates organization-wide: scope assignments are not offered in the UI, and `intersect_with_operating_scope` is a no-op.

**Hierarchy:** `Organization -> Region -> Market -> Location`. A Market belongs to exactly one Region; a Location to exactly one Market. Cross-organization references are prohibited.

The following operational records carry a non-null `location_id`, immutable once set on commercial records: `SalesOrder`, `WorkOrder`, `BuildOrder`, `PurchaseOrder`, `Quote`, `Lead`, `Client`, `Invoice`.

**Scope assignment:**

```text
MembershipScopeAssignment
  id, membership_id
  scope_type ENUM(REGION, MARKET, LOCATION)
  region_id / market_id / location_id (exactly one non-null)
  CHECK: exactly one of (region_id, market_id, location_id) is non-null
```

A membership with **no** scope assignments and a non-scoped role has organization-wide access. A membership with a **scoped role** and **no** scope assignments has zero data access (a visible misconfiguration, not a silent grant).

**Queryset intersection** (illustrative for an RML-scoped entity) resolves the location closure of the membership's scope assignments and filters `location_id__in=permitted`. **Object-level check** raises `OperatingScopeViolationError` when a target's `location_id` is outside the permitted closure. RML is also a pricing input (it flows into `PricingContext` and the location/tax modifiers — Section 10).

### 8.15 Support Impersonation

**Status: NORMATIVE.**

Support users (`is_staff`) land on the platform console and may enter a tenant context only through audited impersonation.

**Start:** locate the target tenant -> select a target Membership -> submit a required reason (free text, >=10 chars) -> pass sensitive-action re-auth (Section 8.12). On confirmation the system emits `IMPERSONATION_STARTED`, writes an `ImpersonationAuditLog` row, establishes a **tenant-local session on the target subdomain** with `is_impersonating=true`, and redirects there.

**Banner:** while impersonating, every tenant-subdomain page MUST render a server-side impersonation banner (rendered by the base template, not client JavaScript; CSP and structure prevent DOM-hiding). It names the impersonated user, the support user, the start time, and the reason, with an "End Impersonation" control.

**Permission evaluation** uses the impersonated membership's capabilities (Section 8.13 step 2); audit attribution records the support user as actor and the impersonated user as on-behalf-of.

```text
ImpersonationAuditLog
  id, support_user_id, target_user_id, target_membership_id, organization_id,
  reason, session_id, client_ip, client_user_agent,
  started_at, ended_at, ended_by ENUM(USER_ACTION, SESSION_EXPIRY, FORCE_TERMINATED),
  total_actions_taken, retention_until            -- 7-year retention, locked at start
```

**Restrictions:** a support user may not impersonate another `is_staff` user; may not impersonate across organizations within a single session; sessions have a 2-hour absolute cap; and may not start impersonation while themselves logged into a tenant via a direct membership. `ImpersonationAuditLog` rows are never deleted within retention and survive tenant deletion.

### 8.16 Logout

**Status: NORMATIVE.**

| Trigger | Effect |
|---|---|
| Tenant-portal logout | Destroys the tenant-local session for that subdomain only |
| Root-domain logout | Destroys the root-domain session; invalidates outstanding handoff tokens; optionally redirects through Auth0 logout |
| Auth0 (global) logout | Local logout always; provider/global logout via Auth0's logout endpoint is best-effort in the MVP |
| Idle / absolute-cap expiry | Session expires silently |
| Sensitive-action re-auth failure | Tenant-local session destroyed; audit event emitted |

Auth0 global session logout (terminating the Auth0 session itself, not just the MyPipelineHero session) is best-effort in the MVP; comprehensive single-logout is post-MVP.

### 8.17 Authentication Audit Events

**Status: NORMATIVE.**

```text
LOGIN_STARTED  LOGIN_SUCCEEDED  LOGIN_FAILED
OIDC_CALLBACK_VALIDATED  OIDC_CALLBACK_REJECTED
AUTH0_IDENTITY_LINKED  AUTH0_IDENTITY_UNLINKED
SENSITIVE_ACTION_REAUTH
HANDOFF_TOKEN_ISSUED  HANDOFF_TOKEN_CONSUMED  HANDOFF_REPLAY_DETECTED  HANDOFF_HOST_MISMATCH
HANDOFF_SIGNING_KEY_CREATED  HANDOFF_SIGNING_KEY_PROMOTED  HANDOFF_SIGNING_KEY_RETIRED
HANDOFF_SIGNING_KEY_EMERGENCY_ROTATED  HANDOFF_VERIFIED_WITH_RETIRED_KEY
IMPERSONATION_STARTED  IMPERSONATION_ENDED  IMPERSONATION_AUTO_ENDED
IMPERSONATION_FORCE_TERMINATED  PLATFORM_ADMIN_QUERY
LOGOUT  SESSION_EXPIRED
MEMBER_INVITED  MEMBER_ACCEPTED_INVITE
MEMBERSHIP_DEACTIVATED  MEMBERSHIP_SUSPENDED  MEMBERSHIP_REINSTATED  MEMBERSHIP_REACTIVATED
ROLE_ASSIGNED  ROLE_UNASSIGNED  CAPABILITY_GRANT_APPLIED
```

Audit metadata MAY include the Auth0 connection name and a normalized outcome. Tokens, authorization codes, access/ID/refresh tokens, the Auth0 client secret, and any MFA material MUST NOT be logged.

### 8.18 What Auth0 Removes From the Build

**Status: INFORMATIVE.**

Because Auth0 owns authentication, the following — present in a self-hosted-auth design — are explicitly **not built** in the MVP: local password hashing/storage, password policy enforcement, breached-password checks, password rotation, account-lockout counters, local TOTP enrollment and challenge, recovery-code generation/storage, and forgot/reset-password flows. These are configured in Auth0 (password policy, MFA policy, attack protection) rather than coded in Django. The corresponding `User` fields and the `OAuthProviderConfig` table from the broader design are removed; provider/connection configuration lives in Auth0.

### 8.19 Production Auth0 Readiness

**Status: NORMATIVE.**

Before launch, security review (Section 17, Section 20) MUST verify, per environment:

1. The production Auth0 application is configured with the exact root-domain callback URL(s) and no others.
2. The Auth0 client secret is loaded from an approved secret source and absent from source control and images.
3. Callback validation enforces state, nonce, PKCE, issuer, audience, ID-token signature, and expiry.
4. `email_verified` is required for invite acceptance and email-based linking.
5. The MFA policy is enforced for all connections, including support users.
6. Account-linking behavior is verified against takeover cases (unverified-email linking rejected).
7. No tokens, codes, secrets, or MFA material appear in logs or audit metadata.
8. No Auth0 claim (group/role/metadata) grants a MyPipelineHero capability or membership directly.

### 8.20 Acceptance Criteria

**Status: NORMATIVE.**

| # | Criterion | Verification |
|---|---|---|
| 1 | `platform_accounts.User` is the configured `AUTH_USER_MODEL` from migration #1; has no usable password | migration + model test |
| 2 | Login redirects to Auth0 and validates state, nonce, PKCE, issuer, audience, signature, expiry | integration test |
| 3 | A repeat login matches an existing `Auth0Identity` by `sub` and reuses the canonical `User` | service test |
| 4 | Auth0 login with zero active memberships yields no tenant access | integration test |
| 5 | Unverified Auth0 email cannot link to an existing user | security test |
| 6 | Auth0 login never creates a Membership, Role, capability, or scope | service test |
| 7 | Single-membership users receive a handoff token; multi-membership users see the picker | integration test |
| 8 | Handoff token is single-use, 60-second-limited, host-bound, and active-membership-bound | integration test |
| 9 | Handoff replay and host mismatch emit high-severity audit events | integration test |
| 10 | Handoff signing keys rotate with <=2 non-retired keys; CI enforces the ceiling | unit + CI test |
| 11 | `SUSPENDED`/`DELETED` organizations are blocked at handoff consumption | integration test |
| 12 | Tenant-local session is independent per subdomain; tenant logout doesn't affect others | integration test |
| 13 | Sensitive actions re-prompt Auth0 with `max_age` and refresh `mfa_satisfied_at` | integration test |
| 14 | DENY `MembershipCapabilityGrant` overrides GRANT | service test |
| 15 | Scoped role with no scope assignment yields zero data access | service test |
| 16 | RML intersection is a no-op when `rml_scope` is not entitled | service test |
| 17 | Object outside the membership's location closure raises `OperatingScopeViolationError` | service test |
| 18 | Impersonation requires reason + re-auth, evaluates with impersonated capabilities, attributes to the support user | integration test |
| 19 | Impersonation banner is server-rendered and present on every tenant page while impersonating | view test |
| 20 | A support user cannot impersonate another staff user or cross orgs in one session | service test |
| 21 | No tokens, codes, secrets, or MFA material appear in logs/audit | security test |
| 22 | Capability-coverage CI test passes (every URL decorated or exempted) | CI |

---

## Section 9 — CRM Domain Requirements

### 9.1 Scope and Conventions

**Status: NORMATIVE.**

Section 9 specifies the CRM commercial pipeline: Leads, Clients (with contacts and locations), Quotes (container + versions + lines + discounts), Sales Orders, Tasks, and Communications. Document Attachments are referenced where they attach to these entities and specified fully in Section 13.

This section defines domain shapes, state machines, service surfaces, RBAC enforcement, entitlement gating, and acceptance criteria. The pricing engine that produces the snapshots referenced here is specified in Section 10; this section treats `PricingSnapshot` as an opaque, immutable pricing result.

**Conventions used throughout:**

- Every state-changing operation is a keyword-only service function in `apps/<domain>/services/`. Views, the DRF API, and Celery tasks call these; none re-implement workflow logic (Section 16).
- Service signatures take `organization_id` and `actor_id` plus primitives/dataclasses, never `request`.
- Every transition emits an AuditEvent (Section 17). System-triggered transitions attribute the actor to the System User.
- RBAC matrices use the four-layer form: **Queryset scope . View capability . Object check . Audit event** (Section 8.13).
- **Entitlement gates** are called out per operation, referencing the feature codes in Section 7.10.

**Entitlement summary for the CRM domain:**

| Domain | Feature gate | Notes |
|---|---|---|
| Leads | `leads` (universal) | No gate; available on all plans |
| Clients | `clients` (universal) | No gate |
| Quotes (create/version) | `basic_quotes` (universal) | Gate applies to *advanced* quote features (overrides, bundles, approvals) per their own feature codes |
| Sales Orders | `sales_orders` | Starter: Limited; Growth+: full |
| Tasks | `tasks` (universal) | No gate |
| Communications | `communications` (universal) | No gate |

Quote *creation and versioning* are universal (`basic_quotes`). What is gated inside a quote is the use of advanced pricing levers: manual price overrides (`manual_price_overrides`), bundle lines (`bundles`/`configurable_bundles`), pricing approvals (`pricing_approvals`), and the pricing-configuration inputs (price lists, contracts, segments, promotions) — each enforced by the pricing engine in Section 10, not by the quote container.

### 9.2 Lead Domain

**Status: NORMATIVE.**

#### 9.2.1 Models

```text
Lead
  id: UUID, pk
  organization_id: UUID, fk -> Organization on_delete=PROTECT
  location_id: UUID, fk -> Location on_delete=PROTECT
  number: TEXT                                            -- "LD-2026-00042"
  source: ENUM(WEB, REFERRAL, COLD_OUTREACH, EVENT, INBOUND_CALL, PARTNER, OTHER)
  source_detail: TEXT, null
  status: ENUM(NEW, CONTACTED, QUALIFIED, UNQUALIFIED, CONVERTED, ARCHIVED)
  owner_membership_id: UUID, fk -> Membership on_delete=PROTECT, null
  summary: TEXT
  notes: TEXT, null
  estimated_value: NUMERIC(14,2), null
  estimated_close_date: DATE, null
  qualified_at, unqualified_at, archived_at, converted_at: TIMESTAMPTZ, null
  unqualified_reason: TEXT, null
  converted_to_quote_id: UUID, fk -> Quote, null

  unique_together (organization_id, number)
  index (organization_id, status)
  index (organization_id, owner_membership_id, status)
  index (organization_id, location_id)

LeadContact
  id: UUID, pk
  organization_id, lead_id: fk
  first_name, last_name: TEXT
  email, phone, role_title: TEXT, null
  is_primary: BOOL, default(false)
  partial_index (lead_id) where is_primary

LeadLocation                                              -- physical site of prospective work
  id: UUID, pk
  organization_id, lead_id: fk
  label: TEXT
  address_line1, address_line2, city, region_admin, postal_code, country: TEXT
  notes: TEXT, null
```

`LeadLocation` (a prospective work site) is distinct from `Location` (the RML operating-scope entity). `Lead.location_id` references the operating-scope `Location`.

#### 9.2.2 State Machine

| From | To | Trigger | Actor | Side effects |
|---|---|---|---|---|
| New | Contacted | first_contact | Sales rep | — |
| Contacted | Qualified | qualify | Sales rep | `qualified_at` set |
| Contacted | Unqualified | disqualify | Sales rep / Manager | reason set |
| Qualified | Converted | convert_to_quote | Sales rep | New Quote + DRAFT QuoteVersion created |
| Qualified | Unqualified | disqualify | Manager | reason required |
| Unqualified | Qualified | re_qualify | Manager | reason required |
| Unqualified | Archived | archive | Any member | `archived_at` set |
| Converted | Archived | archive | Manager | `archived_at` set |

**Terminal state:** Archived.

#### 9.2.3 Service Surface

```python
def create_lead(*, organization_id, actor_id, location_id, source, source_detail,
                summary, estimated_value, estimated_close_date,
                primary_contact, additional_contacts=(), sites=(),
                owner_membership_id=None, notes=None) -> Lead: ...   # cap: leads.create

def first_contact(*, organization_id, actor_id, lead_id) -> Lead: ...
def qualify(*, organization_id, actor_id, lead_id) -> Lead: ...
def disqualify(*, organization_id, actor_id, lead_id, reason) -> Lead: ...
def re_qualify(*, organization_id, actor_id, lead_id, reason) -> Lead: ...
def archive_lead(*, organization_id, actor_id, lead_id) -> Lead: ...
def assign_lead(*, organization_id, actor_id, lead_id, owner_membership_id) -> Lead: ...
```

#### 9.2.4 Lead -> Quote Conversion

```python
def convert_to_quote(*, organization_id, actor_id, lead_id) -> tuple[Lead, Quote, QuoteVersion]:
    """
    Required capabilities: leads.convert AND quotes.create
    Required Lead.status: QUALIFIED
    """
```

Field mapping at conversion:

| Source (Lead) | Target |
|---|---|
| `organization_id` | `Quote.organization_id` |
| `location_id` | `Quote.location_id` |
| `id` | `Quote.lead_id` |
| `estimated_close_date` | `QuoteVersion.expiration_date` if set, else null |
| `notes`, `summary`, contacts, sites | NOT copied at conversion |

Conversion creates the Quote container and an empty DRAFT QuoteVersion (no quote lines pre-populated). The lead transitions to `CONVERTED` and `converted_to_quote_id` is set.

#### 9.2.5 RBAC Enforcement (Lead)

| View / Action | Queryset | Capability | Object check | Audit |
|---|---|---|---|---|
| Lead list / detail | `for_membership(m)` | `leads.view` | — | — |
| Create lead | `for_org(org)` | `leads.create` | location in org+scope | `LEAD_CREATED` |
| Edit lead | `for_membership(m)` | `leads.edit` | owner == acting membership unless `leads.edit_any` | `LEAD_UPDATED` |
| Archive lead | `for_membership(m)` | `leads.archive` | not already ARCHIVED | `LEAD_ARCHIVED` |
| Assign lead | `for_membership(m)` | `leads.assign` | new owner is org member | `LEAD_ASSIGNED` |
| Contact/qualify/disqualify/re-qualify | `for_membership(m)` | `leads.edit` | state precondition | `LEAD_STATUS_CHANGED` |
| Convert to quote | `for_membership(m)` | `leads.convert` + `quotes.create` | status == QUALIFIED | `LEAD_CONVERTED` + `QUOTE_VERSION_CREATED` |

No entitlement gate (the `leads` feature is universal).

### 9.3 Client Domain

**Status: NORMATIVE.**

#### 9.3.1 Models

```text
Client
  id: UUID, pk
  organization_id: UUID, fk -> Organization on_delete=PROTECT
  location_id: UUID, fk -> Location on_delete=PROTECT
  number: TEXT                                            -- "CL-2026-00042"
  billing_account_name: TEXT
  display_name: TEXT
  status: ENUM(ACTIVE, INACTIVE)
  customer_segment_id: UUID, fk -> CustomerSegment on_delete=PROTECT, null
  external_id: TEXT, null
  notes: TEXT, null
  default_payment_terms_days: INT, default(30)
  tax_exempt: BOOL, default(false)
  tax_exempt_certificate_ref: TEXT, null
  deleted_at: TIMESTAMPTZ, null
  deleted_by_id: UUID, fk -> User, null
  partial_unique (organization_id, number) where deleted_at IS NULL

ClientContact
  id, organization_id, client_id: fk
  first_name, last_name: TEXT
  email, phone, role_title: TEXT, null
  is_primary: BOOL, default(false)
  is_billing_contact: BOOL, default(false)

ClientLocation
  id, organization_id, client_id: fk
  label: TEXT
  address_line1, address_line2, city, region_admin, postal_code, country: TEXT
  is_billing, is_service, is_install: BOOL, default(false)
  notes: TEXT, null
  CHECK: at least one of (is_billing, is_service, is_install) is true
```

#### 9.3.2 State Machine

| From | To | Trigger | Actor | Side effects |
|---|---|---|---|---|
| Active | Inactive | deactivate_client | Manager | data retained |
| Inactive | Active | reactivate_client | Manager | — |

Client uses status archival (`INACTIVE`), not deletion. Hard delete occurs only via tenant deletion (Section 17).

#### 9.3.3 Service Surface

```python
def create_client(...): ...                # cap: clients.create
def update_client(...): ...                # cap: clients.edit; status == ACTIVE
def deactivate_client(...): ...            # cap: clients.deactivate
def reactivate_client(...): ...            # cap: clients.edit; status == INACTIVE
def merge_clients(*, organization_id, actor_id, primary_client_id,
                  duplicate_client_id, reason): ...   # cap: clients.merge
def add_client_contact(...) / update_client_contact(...) / remove_client_contact(...): ...
def add_client_location(...) / update_client_location(...) / remove_client_location(...): ...
```

**Merge semantics.** `merge_clients` re-points all FK references (Quotes, SalesOrders, Invoices, Communications, Tasks) from the duplicate to the primary; ClientContacts and ClientLocations are moved, not duplicated. The duplicate is set `INACTIVE` (not hard-deleted). `CLIENT_MERGED` captures both ids and re-pointed counts. Segment changes apply prospectively — existing PricingSnapshots are unchanged.

#### 9.3.4 RBAC Enforcement (Client)

| View / Action | Queryset | Capability | Object check | Audit |
|---|---|---|---|---|
| Client list / detail | `for_membership(m)` | `clients.view` | — | — |
| Create client | `for_org(org)` | `clients.create` | location in org+scope | `CLIENT_CREATED` |
| Edit client | `for_membership(m)` | `clients.edit` | status == ACTIVE | `CLIENT_UPDATED` |
| Deactivate / reactivate | `for_membership(m)` | `clients.deactivate` / `clients.edit` | status precondition | `CLIENT_DEACTIVATED` / `_REACTIVATED` |
| Manage contacts / locations | `for_membership(m)` | `clients.contacts.manage` / `clients.locations.manage` | — | `CLIENT_*` |
| Merge clients | `for_membership(m)` | `clients.merge` | both in org+scope | `CLIENT_MERGED` |

No entitlement gate (the `clients` feature is universal). Customer segment *assignment* requires the `customer_segments` feature to be entitled to set a non-default segment (Section 10); the default STANDARD segment is always available.

### 9.4 Quote Domain

**Status: NORMATIVE.**

The Quote domain is the CPQ surface. A **Quote** is a stable container; a **QuoteVersion** is an immutable-once-sent snapshot of commercial terms; a **QuoteVersionLine** is a priced line referencing a `PricingSnapshot`.

#### 9.4.1 Models

```text
Quote                                                      -- container; stable across versions
  id: UUID, pk
  organization_id, location_id: fk
  number: TEXT                                            -- "QT-2026-00042"
  lead_id: UUID, fk -> Lead, null
  client_id: UUID, fk -> Client, null
  unique_together (organization_id, number)
  CHECK: at least one of (lead_id, client_id) is non-null

QuoteVersion
  id: UUID, pk
  organization_id, quote_id: fk
  version_number: INT
  status: ENUM(DRAFT, SENT, ACCEPTED, DECLINED, EXPIRED, RETRACTED, SUPERSEDED)
  expiration_date: DATE, null
  subtotal_amount, discount_amount, tax_amount, total_amount: NUMERIC(14,2)
  currency_code: CHAR(3)
  notes, internal_notes, terms: TEXT, null
  sent_at, sent_by_id, sent_to_emails: ...
  accepted_at, accepted_by_id: ...
  declined_at, expired_at: ...
  retracted_at, retracted_by_id, retracted_reason: ...
  superseded_at, superseded_by_version_id: ...
  optimistic_version: INT, default(0)
  unique_together (quote_id, version_number)
  partial_index (quote_id) where status = 'ACCEPTED'

QuoteVersionLine
  id: UUID, pk
  organization_id, quote_version_id: fk
  sort_order: INT
  line_type: ENUM(SERVICE, RESALE_PRODUCT, MANUFACTURED_PRODUCT, BUNDLE)
  service_id / product_id / bundle_definition_id: UUID, fk, null
  selected_supplier_id: UUID, fk -> Supplier, null
  selected_bom_version_id: UUID, fk -> BOMVersion, null
  description_snapshot: TEXT
  quantity: NUMERIC(14,4)
  unit_of_measure: TEXT
  unit_price_snapshot: NUMERIC(14,4)
  line_subtotal, line_discount_amount, line_total: NUMERIC(14,2)
  taxable: BOOL, default(true)
  pricing_snapshot_id: BIGINT, fk -> PricingSnapshot on_delete=PROTECT
  pending_pricing_approval_id: UUID, fk -> PricingApproval, null
  selected_options_json: JSONB, null               -- for CONFIGURABLE bundles
  CHECK: exactly one of (service_id, product_id, bundle_definition_id) is non-null
  CHECK: line_type matches the populated FK

QuoteVersionDiscount
  id, organization_id, quote_version_id: fk
  discount_type: ENUM(PERCENTAGE, FIXED_AMOUNT)
  value: NUMERIC(14,4)
  reason: TEXT, null
  applied_by_id, applied_at: ...
```

#### 9.4.2 State Machine

| From | To | Trigger | Actor | Side effects |
|---|---|---|---|---|
| Draft | Sent | send_quote | Sales rep w/ `quotes.send` | sent fields set; outbox publishes email; PDF async; **version becomes immutable** |
| Draft | Superseded | new_version_created | Quote editor | New DRAFT created |
| Sent | Retracted | retract_quote | rep w/ `quotes.retract` | reason set; successor DRAFT created with lines deep-copied **and re-priced** |
| Sent | Accepted | accept_quote | user w/ `quotes.approve`; sensitive | SalesOrder created; fulfillment dispatch enqueued |
| Sent | Declined | decline_quote | user w/ `quotes.decline` | `declined_at` set |
| Sent | Expired | expiry_check | System (beat) | `expired_at` set |
| Sent | Superseded | new_version_created | Quote editor | New DRAFT created; sent version preserved |

**Terminal states:** Accepted, Declined, Expired, Retracted, Superseded.

#### 9.4.3 Quote Builder Service Surface

```python
def add_quote_line(*, organization_id, actor_id, quote_version_id, line_type,
                   catalog_item_ref, quantity, unit_of_measure,
                   selected_supplier_id=None, selected_bom_version_id=None,
                   expected_optimistic_version) -> QuoteVersionLine:
    """
    Required capability: quotes.edit
    Required state: DRAFT
    Triggers PricingEngine.price_quote_line() -> PricingSnapshot persisted (Section 10)
    Entitlement: a BUNDLE line requires `bundles`; a MANUFACTURED_PRODUCT line requires
                 `bom_manufacturing`; these are enforced by the pricing engine resolvers.
    """

def update_quote_line(...): ...
def remove_quote_line(...): ...
def apply_line_discount(...): ...          # cap: quotes.line.apply_discount
def override_line_price(...): ...          # cap: quotes.line.override_price; sensitive;
                                           # entitlement: manual_price_overrides
def apply_quote_discount(...): ...
```

All draft mutations require `expected_optimistic_version`; a mismatch raises `ConcurrencyConflictError`. Draft mutations are blocked once the version leaves DRAFT.

#### 9.4.4 Quote Send

```python
def send_quote(*, organization_id, actor_id, quote_version_id,
               recipient_emails, cover_message, expected_optimistic_version) -> QuoteVersion:
    """ Required capability: quotes.send; Required state: DRAFT """
```

In transaction: lock `FOR UPDATE`; verify DRAFT; verify every line has a non-null `pricing_snapshot_id`; verify **no line has a pending PricingApproval** (else `PricingApprovalPendingError`); default `expiration_date` to `now + 30 days` if null; recompute totals defensively; set SENT fields; insert outbox entry; emit `QUOTE_SENT`. The version is immutable thereafter.

#### 9.4.5 Quote Retraction with Successor Inheritance

```python
def retract_quote(*, organization_id, actor_id, quote_version_id, reason)
    -> tuple[QuoteVersion, QuoteVersion]:
    """ Required capability: quotes.retract; Required state: SENT
        Returns (retracted_version, new_draft_version) """
```

Behavior: lock the SENT version; set RETRACTED fields; allocate the next `version_number`; create a new DRAFT version; **deep-copy lines and re-price each through the engine** (fresh PricingSnapshots — never copy old snapshots); copy the quote-level discount; emit `QUOTE_RETRACTED` + `QUOTE_VERSION_CREATED` + `QUOTE_LINES_INHERITED`. Re-pricing means the successor reflects current catalog/contract/rule state, which is the intended behavior of a retraction.

#### 9.4.6 Multi-Line / Multi-Visit Hint

The "one SalesOrderLine = one fulfillment artifact" rule is an MVP simplification. The quote builder shows a non-blocking soft warning when `line_type in {SERVICE, MANUFACTURED_PRODUCT}` and `quantity > 1`, suggesting the rep split the line if it represents multiple independent visits/batches. The hint is dismissible per line and never blocks save.

#### 9.4.7 RBAC Enforcement (Quote)

| View / Action | Queryset | Capability | Object check | Audit |
|---|---|---|---|---|
| Quote list / detail | `for_membership(m)` | `quotes.view` | — | — |
| Create quote / new version | `for_org(org)` | `quotes.create` | new version: prior status != ACCEPTED | `QUOTE_VERSION_CREATED` |
| Edit quote line | `for_membership(m)` | `quotes.edit` | DRAFT AND optimistic version matches | `QUOTE_LINE_*` |
| Apply line / quote discount | `for_membership(m)` | `quotes.line.apply_discount` | DRAFT | `QUOTE_DISCOUNT_APPLIED` |
| Override line price | `for_membership(m)` | `quotes.line.override_price`; sensitive | DRAFT | `QUOTE_LINE_PRICE_OVERRIDE` |
| Send quote | `for_membership(m)` | `quotes.send` | DRAFT; no pending approvals | `QUOTE_SENT` |
| Retract quote | `for_membership(m)` | `quotes.retract` | SENT | `QUOTE_RETRACTED` + `QUOTE_VERSION_CREATED` |
| Accept quote | `for_membership(m)` | `quotes.approve`; sensitive | SENT | `QUOTE_ACCEPTED` |
| Decline quote | `for_membership(m)` | `quotes.decline` | SENT | `QUOTE_DECLINED` |
| Delete draft | `for_membership(m)` | `quotes.delete_draft` | DRAFT | `QUOTE_DRAFT_DELETED` |

**Entitlement gates inside the quote:** override line price -> `manual_price_overrides`; bundle line -> `bundles`/`configurable_bundles`; manufactured line -> `bom_manufacturing`; pricing approval flow -> `pricing_approvals`. These are enforced where the pricing engine runs (Section 10), so a quote container itself needs only `basic_quotes`.

### 9.5 Quote Acceptance and Sales Order Creation

**Status: NORMATIVE.**

#### 9.5.1 Service Shape

```python
def accept_quote(*, organization_id, actor_id, quote_version_id,
                 client_resolution, idempotency_key) -> QuoteAcceptanceResult:
    """ Required capability: quotes.approve; sensitive (re-auth); Required state: SENT """

@dataclass(frozen=True)
class ClientResolution:
    mode: Literal["use_existing", "create_new"]
    existing_client_id: UUID | None
    new_client_data: NewClientFromLead | None

@dataclass(frozen=True)
class QuoteAcceptanceResult:
    quote_version_id: UUID
    sales_order_id: UUID
    client_id: UUID
    fulfillment_outbox_ids: list[int]
```

#### 9.5.2 Acceptance Flow

In transaction:

1. **Idempotency check** on `(organization_id, idempotency_key)` (Section 16).
2. **Lock the QuoteVersion** `FOR UPDATE`; verify `status == SENT` and `expiration_date >= today`.
3. **Verify no pending PricingApprovals** -> else `PricingApprovalPendingError`.
4. **Resolve client** (Section 9.5.3).
5. **Create SalesOrder** (`status=OPEN`, totals copied from the QuoteVersion).
6. **Create SalesOrderLines** copying commercial fields verbatim and referencing the existing snapshots.
7. **Set the QuoteVersion** to ACCEPTED (this is the semantic lock on its snapshots).
8. **Update the linked Lead** if present.
9. **Enqueue fulfillment dispatch via outbox** (one entry per resulting SalesOrderLine).
10. **Emit `QUOTE_ACCEPTED`**; mark the idempotency record consumed.

**Entitlement at acceptance:** acceptance creates a SalesOrder, which requires `sales_orders` to be entitled. On a Starter plan (where `sales_orders` is Limited), acceptance is permitted within the Starter limit posture; Growth+ is unrestricted. The fulfillment artifacts dispatched downstream (work orders, build orders, purchase orders) carry their own entitlement gates (Section 11) — a Starter tenant without `work_orders` can accept a service quote, but the resulting work-order dispatch is gated per Section 11.

#### 9.5.3 Client Resolution

```text
Lead -> Client mapping (mode == "create_new"):
  organization_id, location_id                  -> Client.*
  Lead's primary contact                         -> initial ClientContact (is_primary=True);
                                                     absent -> ClientResolutionError
  Organization.default_payment_terms_days        -> Client.default_payment_terms_days
  Organization default CustomerSegment           -> Client.customer_segment_id (null if none)
  Lead.summary, Lead's sites                      -> NOT mapped (operator adds explicitly)
  Client.billing_account_name                     -> defaults to primary contact full name
```

The acceptance UI gate requires explicit client resolution: if the quote already has a `client_id`, it is shown; if only a `lead_id` is present, the operator chooses "use existing client" (search) or "create new client from lead" with neither pre-selected — a deliberate choice is required before acceptance proceeds.

#### 9.5.4 Sales Order Models

```text
SalesOrder
  id, organization_id, location_id, number
  client_id: fk -> Client
  originating_quote_version_id: fk -> QuoteVersion
  status: ENUM(OPEN, IN_FULFILLMENT, FULFILLED, PART_INVOICED, INVOICED, CLOSED, CANCELLED)
  subtotal_amount, discount_amount, tax_amount, total_amount: NUMERIC(14,2)
  currency_code: CHAR(3)
  notes, cancelled_at, cancelled_by_id, cancelled_reason, external_id
  bundle_drift_notes: JSONB, null                 -- per-bundle drift report (Section 10)

SalesOrderLine
  id, organization_id, sales_order_id
  source_quote_version_line_id: fk -> QuoteVersionLine
  parent_sales_order_line_id: fk -> SalesOrderLine, null    -- bundle children
  sort_order, line_type
  description_snapshot, quantity, unit_of_measure
  unit_price_snapshot, line_subtotal, line_discount_amount, line_total, taxable
  pricing_snapshot_id: BIGINT, fk -> PricingSnapshot
  fulfillment_status: ENUM(PENDING, IN_PROGRESS, FULFILLED, CANCELLED, NOT_APPLICABLE)
  invoice_eligibility: ENUM(NOT_YET, ELIGIBLE, INVOICED, NOT_INVOICEABLE)
```

#### 9.5.5 Sales Order State Machine

| From | To | Trigger | Actor | Side effects |
|---|---|---|---|---|
| Open | In_Fulfillment | fulfillment_started | System | first artifact leaves initial state |
| Open | Cancelled | cancel_order | Manager | reason; only if no active WO/PO/BO |
| In_Fulfillment | Cancelled | cancel_order | Manager | reason required |
| In_Fulfillment | Fulfilled | all_fulfillment_complete | System | all artifacts terminal |
| In_Fulfillment / Fulfilled | Part_Invoiced | partial_invoice_issued | Billing user | — |
| Fulfilled | Invoiced | full_invoice_issued | Billing user | all invoiceable lines invoiced |
| Part_Invoiced | Invoiced | remaining_invoiced | Billing user | — |
| Invoiced | Closed | payment_complete | System | all invoices PAID |

**Terminal states:** Cancelled, Closed.

#### 9.5.6 Order Lifecycle Rules

- **Cancellation** (`cancel_sales_order`, cap `orders.cancel`): permitted only when no active WorkOrders, BuildOrders, PurchaseOrders, or any Invoices exist; reason required.
- **Closure**: set automatically by `recompute_sales_order_status` when all invoiceable lines are invoiced and all linked invoices are PAID.
- **Post-acceptance edits**: only `notes` and metadata (`external_id`) are mutable; commercial fields are immutable.

#### 9.5.7 RBAC Enforcement (Sales Order)

| View / Action | Queryset | Capability | Object check | Audit |
|---|---|---|---|---|
| Order list / detail | `for_membership(m)` | `orders.view` | — | — |
| Edit order notes | `for_membership(m)` | `orders.edit` | not CANCELLED/CLOSED | `ORDER_NOTES_UPDATED` |
| Cancel order | `for_membership(m)` | `orders.cancel` | no active WO/PO/BO | `ORDER_CANCELLED` |
| Manually trigger fulfillment | `for_membership(m)` | `orders.generate_fulfillment` | line still PENDING | `ORDER_FULFILLMENT_TRIGGERED` |

**Entitlement gate:** sales-order operations require `sales_orders`.

### 9.6 Tasks

**Status: NORMATIVE.**

#### 9.6.1 Models

```text
Task
  id, organization_id
  title: TEXT
  description: TEXT, null
  status: ENUM(OPEN, IN_PROGRESS, BLOCKED, COMPLETED, CANCELLED)
  priority: ENUM(LOW, NORMAL, HIGH, URGENT), default(NORMAL)
  due_at: TIMESTAMPTZ, null
  assigned_to_id: UUID, fk -> Membership, null
  blocked_reason, completed_at, completed_by_id, completion_notes
  cancelled_at, cancelled_by_id, cancelled_reason
  reopened_at, reopened_by_id, reopened_reason

TaskLink                                            -- typed link table; no GenericForeignKey
  id, organization_id, task_id
  lead_id, quote_id, client_id, sales_order_id, work_order_id,
  build_order_id, purchase_order_id, invoice_id: UUID, fk, null
  CHECK (num_nonnulls(...) = 1)
```

#### 9.6.2 State Machine

| From | To | Trigger | Actor | Side effects |
|---|---|---|---|---|
| Open | In_Progress | start_task | Assignee/Manager | — |
| Open / In_Progress | Blocked | block_task | Assignee/Manager | `blocked_reason` required |
| Blocked | In_Progress | resume_task | Assignee/Manager | — |
| Open / In_Progress | Completed | complete_task | Assignee/Manager | completion notes optional |
| Open / In_Progress / Blocked | Cancelled | cancel_task | Manager | reason required |
| Completed / Cancelled | Open | reopen_task | Manager | reason required |

**Terminal states:** none — reopen permits re-entry.

#### 9.6.3 Service Surface and Reminders

```python
def create_task(...): ...        def update_task(...): ...      def assign_task(...): ...
def start_task(...): ...         def block_task(...): ...       def resume_task(...): ...
def complete_task(...): ...      def cancel_task(...): ...      def reopen_task(...): ...
```

Tasks with `due_at` and status in {OPEN, IN_PROGRESS} get async reminders: a `task.reminder_due` outbox entry 24h before `due_at`, and a `task.reminder_overdue` entry 1h after if still open. Reminders dispatch outbound email only in the MVP.

#### 9.6.4 RBAC Enforcement (Task)

| View / Action | Queryset | Capability | Object check | Audit |
|---|---|---|---|---|
| Task list / detail | `for_membership(m)` | `tasks.view` | creator/assignee/manager unless `tasks.manage` | — |
| Create task | `for_membership(m)` | `tasks.create` | linked target in org+scope | `TASK_CREATED` |
| Update task | `for_membership(m)` | `tasks.edit` | creator/assignee/manager | `TASK_UPDATED` |
| Assign task | `for_membership(m)` | `tasks.assign` | new assignee in org | `TASK_ASSIGNED` |
| Start/block/resume | `for_membership(m)` | `tasks.edit` | state transition | `TASK_STATUS_CHANGED` |
| Complete task | `for_membership(m)` | `tasks.complete` | OPEN/IN_PROGRESS/BLOCKED | `TASK_COMPLETED` |
| Cancel / reopen | `for_membership(m)` | `tasks.manage` | state precondition | `TASK_CANCELLED` / `_REOPENED` |

No entitlement gate (`tasks` universal).

### 9.7 Communications

**Status: NORMATIVE.**

#### 9.7.1 Models

```text
Communication
  id, organization_id
  direction: ENUM(INBOUND, OUTBOUND)
  channel: ENUM(EMAIL, CALL_NOTE, MANUAL_NOTE)
  subject: TEXT, null
  body: TEXT
  body_hash: TEXT                                   -- immutability check
  participants: JSONB
  occurred_at: TIMESTAMPTZ
  sent_at: TIMESTAMPTZ, null
  delivery_status: ENUM(NOT_APPLICABLE, QUEUED, SENT, DELIVERED, BOUNCED, FAILED)
  provider_message_id: TEXT, null
  provider_metadata: JSONB, null

CommunicationLink                                   -- same typed pattern as TaskLink
```

#### 9.7.2 Service Surface

```python
def log_communication(*, organization_id, actor_id, direction, channel, subject, body,
                      participants, occurred_at, link) -> Communication:
    """ cap: communications.log """

def send_communication(*, organization_id, actor_id, subject, body,
                       recipient_emails, link) -> Communication:
    """ cap: communications.send. OUTBOUND EMAIL ONLY in MVP. Body immutable once sent. """
```

Inbound email synchronization and mailbox threading are post-MVP (Section 22); the `INBOUND` direction and `provider_message_id` fields are reserved but populated only by manual logging in the MVP. Communication bodies are immutable (the `body_hash` detects tampering); only metadata is editable via `communications.manage`.

#### 9.7.3 RBAC Enforcement (Communication)

| View / Action | Queryset | Capability | Object check | Audit |
|---|---|---|---|---|
| Communication list | `for_membership(m)` | `communications.view` | — | — |
| Log communication | `for_membership(m)` | `communications.log` | linked target in org+scope | `COMMUNICATION_LOGGED` |
| Send communication | `for_membership(m)` | `communications.send` | linked target in org+scope | `COMMUNICATION_SENT` |
| Edit metadata | `for_membership(m)` | `communications.manage` | body immutable | `COMMUNICATION_UPDATED` |

No entitlement gate (`communications` universal).

### 9.8 Typed-Link Invariant

**Status: NORMATIVE.**

`TaskLink`, `CommunicationLink`, and `DocumentAttachmentLink` (Section 13) use explicit nullable FKs with an "exactly one non-null" CHECK constraint — never `GenericForeignKey` (Architectural Principle 7). The invariant is enforced at three layers: the database CHECK constraint, the service layer (tagged-union input), and the form layer (single-select). This keeps cross-domain linkage queryable, index-friendly, and tenant-safe.

### 9.9 State-Machine Property Tests

**Status: NORMATIVE.**

For every CRM state-machine entity (Lead, QuoteVersion, SalesOrder, Task, Membership), a Hypothesis property test asserts: every declared transition maps to an executable service function with `organization_id`/`actor_id` parameters; no service function performs an undeclared transition; every terminal state has zero outgoing transitions; and every non-terminal state has at least one incoming and one outgoing transition. The state tables in this section are the contract; code may not diverge without a guide PR (Architectural Principle 8).

### 9.10 Acceptance Criteria

**Status: NORMATIVE.**

| # | Criterion | Verification |
|---|---|---|
| 1 | Lead lifecycle matches 9.2.2; property test passes | property test |
| 2 | Lead->Quote conversion creates a Quote + empty DRAFT version; no lines pre-populated | service test |
| 3 | Every quote line carries a non-null `pricing_snapshot_id` after the builder runs | service test |
| 4 | Quote send rejects when any line has a pending PricingApproval | service test |
| 5 | Quote send transitions DRAFT->SENT, enqueues `quote.send_email`, makes the version immutable | service test |
| 6 | Retraction creates a successor DRAFT, deep-copies lines, and **re-prices** (fresh snapshots) | service + property test |
| 7 | Quote-level discount is copied to the successor on retraction | service test |
| 8 | Optimistic-concurrency mismatch on a draft edit raises `ConcurrencyConflictError` | service test |
| 9 | Manual price override is sensitive (re-auth) and gated by `manual_price_overrides` | service + integration test |
| 10 | Acceptance is idempotent on `(org, idempotency_key)` | service test |
| 11 | Acceptance with `create_new` maps Lead->Client per 9.5.3; missing primary contact raises `ClientResolutionError` | service test |
| 12 | Acceptance with `use_existing` rejects a client in a different org | service test |
| 13 | Acceptance creates SalesOrder + SalesOrderLines and enqueues fulfillment dispatch per line | service test |
| 14 | Sales-order operations require the `sales_orders` entitlement | service test |
| 15 | SalesOrder lifecycle matches 9.5.5; property test passes | property test |
| 16 | Order cancellation is blocked when active WO/PO/BO or any invoice exists | service test |
| 17 | Client merge re-points FKs, moves contacts/locations, sets duplicate INACTIVE, audits both ids | service test |
| 18 | Task `block_task` requires `blocked_reason` (CHECK enforced); lifecycle property test passes | service + property test |
| 19 | Communication body is hashed and immutable; body edits fail | service test |
| 20 | TaskLink / CommunicationLink enforce exactly-one-non-null at DB, service, and form layers | service + DB test |
| 21 | Capability-coverage CI test passes for all CRM routes | CI |
| 22 | Universal CRM features (leads/clients/tasks/communications) require no `require_feature` call | service test |

---

## Section 10 — Catalog and Pricing Requirements

### 10.1 Scope and the Composition Principle

**Status: NORMATIVE.**

Section 10 specifies the catalog (services, products, raw materials, suppliers, costs), the pricing-configuration inputs (price lists, client contracts, customer segments, labor rate cards, promotions, bundles, tax), the bill-of-materials and manufactured-product model, and the deterministic **pricing engine** that turns a catalog item plus a context into an immutable, replayable `PricingSnapshot`.

The governing rule is **composition over proliferation** (Architectural Principle, Section 3.1). Pricing behavior is assembled from a small fixed set of reusable parts:

```text
PricingContext  ->  Strategy  ->  Modifiers (ordered)  ->  Approval gate  ->  PricingSnapshot
   (inputs)        (one base    (reusable, ordered    (optional, rule-     (immutable,
                    calc)        transforms)            triggered)           replayable)
```

There is **one** strategy per line, an **ordered list** of modifiers, and a set of **resolvers** that populate the context before the strategy runs. New business scenarios (rush jobs, location surcharges, supplier selection, complexity factors) are expressed as resolvers or modifiers — **never** as new strategy classes. Adding a strategy requires a guide PR; the MVP ships exactly seven.

This section is gate-dense. Every pricing-configuration input and several line behaviors are entitlement-gated per Section 7.10; the engine itself enforces those gates as it runs (Section 10.10), which is why Section 9's quote container needs only `basic_quotes`.

### 10.2 Catalog Domain

**Status: NORMATIVE.**

#### 10.2.1 Catalog Item Types

The catalog has three sellable item types and two supporting cost entities:

| Entity | Sellable | Feature gate | Purpose |
|---|---|---|---|
| `Service` | Yes | `basic_catalog` (universal) | Labor/time-based offerings |
| `Product` | Yes | `basic_catalog` (universal) | Resale or manufactured goods |
| `BundleDefinition` | Yes | `bundles` / `configurable_bundles` | Composed offerings (Section 10.7) |
| `RawMaterial` | No | `raw_materials` | BOM inputs; not directly quotable |
| `Supplier` + `SupplierCost` | No | `suppliers` / `supplier_costs` | Cost sourcing (Section 10.2.4) |

#### 10.2.2 Service and Product Models

```text
Service
  id: UUID, pk
  organization_id: fk -> Organization on_delete=PROTECT
  code: TEXT
  name: TEXT
  description: TEXT, null
  unit_of_measure: TEXT                              -- "hour", "visit", "each"
  default_pricing_strategy: TEXT                     -- a StrategyCode (Section 10.4)
  default_labor_role_id: UUID, fk -> LaborRole, null -- for rate-card strategies
  base_cost: NUMERIC(14,4), null                     -- standing cost input
  base_price: NUMERIC(14,4), null                    -- standing price input (flat strategies)
  is_taxable: BOOL, default(true)
  is_active: BOOL, default(true)
  deleted_at, deleted_by_id: ...
  partial_unique (organization_id, code) where deleted_at IS NULL

Product
  id: UUID, pk
  organization_id: fk
  code, name, description
  unit_of_measure: TEXT
  product_kind: ENUM(RESALE, MANUFACTURED)
  default_pricing_strategy: TEXT
  base_cost: NUMERIC(14,4), null                     -- standing/last-known cost
  base_price: NUMERIC(14,4), null
  preferred_supplier_id: UUID, fk -> Supplier, null  -- RESALE cost sourcing default
  is_taxable: BOOL, default(true)
  is_active: BOOL, default(true)
  deleted_at, deleted_by_id: ...
  partial_unique (organization_id, code) where deleted_at IS NULL
  CHECK: product_kind = MANUFACTURED implies a BOM may be attached (Section 10.6)
```

A `MANUFACTURED` product is quotable only when `bom_manufacturing` is entitled and the product has an active, effective BOM version (Section 10.6). A `RESALE` product sources cost from a supplier when `suppliers`/`supplier_costs` are entitled, otherwise from `base_cost`.

#### 10.2.3 Raw Material Model

```text
RawMaterial
  id: UUID, pk
  organization_id: fk
  code, name, description
  unit_of_measure: TEXT
  base_cost: NUMERIC(14,4), null                     -- fallback cost when no supplier cost
  is_active: BOOL, default(true)
  deleted_at, deleted_by_id: ...
  partial_unique (organization_id, code) where deleted_at IS NULL
```

Raw materials are not directly sellable; they appear only as BOM lines. Gated by `raw_materials` (Growth-Limited, Pro+ full).

#### 10.2.4 Supplier and Supplier Cost

```text
Supplier
  id: UUID, pk
  organization_id: fk
  code, name
  contact_name, contact_email, contact_phone: TEXT, null
  is_active: BOOL, default(true)

SupplierCost
  id: UUID, pk
  organization_id, supplier_id: fk
  product_id: UUID, fk -> Product, null              -- exactly one of product/raw_material
  raw_material_id: UUID, fk -> RawMaterial, null
  unit_cost: NUMERIC(14,4)
  currency_code: CHAR(3)
  minimum_order_quantity: NUMERIC(14,4), null
  lead_time_days: INT, null
  effective_from: DATE
  effective_to: DATE, null                           -- null = open-ended
  CHECK: exactly one of (product_id, raw_material_id) is non-null
  index (organization_id, product_id, effective_from)
  index (organization_id, raw_material_id, effective_from)
```

`SupplierCost` is **effective-dated**: cost resolution selects the row whose `[effective_from, effective_to]` window contains the pricing date. Gated by `suppliers` + `supplier_costs`.

#### 10.2.5 Catalog RBAC

| Action | Capability | Entitlement |
|---|---|---|
| View catalog | `catalog.view` | `basic_catalog` |
| Manage services/products | `catalog.manage` | `basic_catalog` |
| Manage raw materials | `catalog.raw_materials.manage` | `raw_materials` |
| Manage suppliers | `catalog.suppliers.manage` | `suppliers` |
| Manage supplier costs | `catalog.supplier_costs.manage` | `supplier_costs` |
| Manage BOMs | `catalog.bom.manage` | `bom_manufacturing` |

### 10.3 The Pricing Engine Contract

**Status: NORMATIVE.**

#### 10.3.1 Engine Version

The engine carries a version string (`"1.0"` in the MVP, per Section 1.4). The version is stamped into every `PricingSnapshot` and is the key to **replay**: a snapshot can be recomputed by loading the engine code at its stamped version against its stored inputs. Changing any strategy, modifier, resolver, or rounding behavior in a way that alters output for the same inputs is a **major or minor version bump** and a guide PR.

#### 10.3.2 Determinism Requirement

Given an identical `PricingContext` and engine version, the engine MUST produce a byte-identical `PricingSnapshot` result payload. Therefore:

- Strategies and modifiers are **pure functions** of the context — no clock reads, no `now()`, no database access, no randomness inside strategy/modifier code.
- All time-dependent and database-dependent inputs (effective-dated costs, active rules, segment multipliers, tax rates, the pricing date) are resolved **before** the pipeline runs, by resolvers, and frozen into the context.
- Decimal arithmetic only (`NUMERIC`/`Decimal`); never float. Rounding is explicit and specified (Section 10.3.5).

#### 10.3.3 PricingContext

```text
PricingContext (immutable dataclass; the frozen input bundle)
  engine_version: str                                -- "1.0"
  organization_id: UUID
  pricing_date: date                                 -- resolved once; drives effective-dating
  currency_code: str

  # Subject of pricing
  item_type: enum(SERVICE, RESALE_PRODUCT, MANUFACTURED_PRODUCT, BUNDLE)
  item_id: UUID
  quantity: Decimal
  unit_of_measure: str
  strategy_code: str                                 -- chosen strategy

  # Resolved inputs (populated by resolvers — Section 10.5)
  cost_input: Decimal | None                         -- resolved unit cost
  cost_source: str                                   -- provenance tag
  labor_lines: tuple[ResolvedLaborLine, ...]         -- rate-card strategies
  bom_resolution: ResolvedBOM | None                 -- manufactured products
  segment_multiplier: Decimal                        -- default 1.0
  location_id: UUID | None                           -- RML; modifier input
  contract_terms: ResolvedContract | None
  price_list_entry: ResolvedPriceListEntry | None
  active_rules: tuple[ResolvedPricingRule, ...]      -- ordered
  active_promotions: tuple[ResolvedPromotion, ...]   -- ordered
  tax_resolution: ResolvedTax | None

  # Entitlement snapshot (which gated inputs were permitted at resolve time)
  entitlements: frozenset[str]
```

The context is built by `PricingContextBuilder` (Section 10.5), which is the **only** component that touches the database during pricing. Once built, it is frozen and handed to the pipeline.

#### 10.3.4 PricingSnapshot

```text
PricingSnapshot (append-only; never updated after write)
  id: BIGINT, pk (BIGSERIAL)
  organization_id: fk
  engine_version: TEXT
  computed_at: TIMESTAMPTZ
  pricing_date: DATE
  item_type, item_id, quantity, unit_of_measure, currency_code
  strategy_code: TEXT
  context_payload: JSONB                              -- the full frozen PricingContext
  result_payload: JSONB                               -- ordered pipeline trace (Section 10.3.6)
  unit_price: NUMERIC(14,4)
  line_subtotal: NUMERIC(14,2)
  cost_input: NUMERIC(14,4), null
  computed_margin_amount: NUMERIC(14,2), null
  computed_margin_pct: NUMERIC(7,4), null
  requires_approval: BOOL, default(false)
  approval_trigger_codes: TEXT[]                      -- which rules/floors tripped
  content_hash: TEXT                                  -- hash(engine_version + context + result)
  index (organization_id, item_type, item_id)
  index (organization_id, computed_at)
```

A `PricingSnapshot` is **never mutated**. Re-pricing produces a **new** snapshot; quote/order lines re-point their `pricing_snapshot_id` FK. The `content_hash` lets replay assert reproduction.

#### 10.3.5 Rounding and Currency

- All money is `Decimal` with `NUMERIC(14,4)` for unit prices/costs and `NUMERIC(14,2)` for line and document totals.
- Intermediate strategy/modifier math runs at 4 decimal places; the final unit price rounds to 4; line subtotal (`unit_price x quantity`) rounds to 2 using **banker's rounding** (`ROUND_HALF_EVEN`).
- One base currency per organization (Section 5.2). Multi-currency is post-MVP; the context carries `currency_code` so the contract is forward-compatible, but no FX conversion runs in the MVP.

#### 10.3.6 Result Payload (Pipeline Trace)

The `result_payload` records an **ordered trace** so a snapshot is self-explaining and replayable:

```json
{
  "engine_version": "1.0",
  "strategy": {"code": "strategy.cost_plus", "input_cost": "40.0000",
               "params": {"markup_pct": "35.00"}, "output_unit_price": "54.0000"},
  "modifiers": [
    {"code": "modifier.segment", "before": "54.0000", "factor": "0.95", "after": "51.3000"},
    {"code": "modifier.location", "before": "51.3000", "adjust": "+5.0000", "after": "56.3000"},
    {"code": "modifier.discount", "before": "56.3000", "pct": "10.00", "after": "50.6700"},
    {"code": "modifier.floor", "before": "50.6700", "floor": "48.0000", "after": "50.6700",
     "tripped": false},
    {"code": "modifier.tax", "taxable": true, "rate": "0.0875", "tax_amount": "4.43"}
  ],
  "final_unit_price": "50.6700",
  "approval": {"required": false, "triggers": []}
}
```

### 10.4 Base Pricing Strategies (Exactly Seven)

**Status: NORMATIVE.**

A strategy computes a **pre-modifier unit price** from the context. Strategies are pure. The MVP ships exactly these seven; each Service/Product names one as its `default_pricing_strategy`, overridable per quote line (subject to entitlement).

| # | StrategyCode | Computation | Primary inputs | Entitlement to *select* |
|---|---|---|---|---|
| 1 | `strategy.flat_price` | Returns the standing `base_price` | `base_price` | `basic_catalog` |
| 2 | `strategy.cost_plus` | `cost_input x (1 + markup_pct)` | `cost_input`, `markup_pct` | `basic_catalog` |
| 3 | `strategy.target_margin` | `cost_input / (1 - target_margin_pct)` | `cost_input`, `target_margin_pct` | `advanced_pricing_rules` |
| 4 | `strategy.rate_card` | `sum(labor_line.hours x role.bill_rate)` over resolved labor lines | `labor_lines` | `labor_rate_cards` |
| 5 | `strategy.tiered_quantity` | Unit price from a quantity-tier table | `quantity`, tier table | `advanced_pricing_rules` |
| 6 | `strategy.component_sum` | `sum(component priced result)` (bundles/BOM roll-up) | `bom_resolution` / bundle components | `bundles` or `bom_manufacturing` |
| 7 | `strategy.recurring_plan` | Per-period price for a recurring term | period, per-period base | `advanced_pricing_rules` |

**Strategy selection gating.** Selecting a strategy beyond `flat_price`/`cost_plus` requires the corresponding entitlement. A Starter tenant (only `basic_catalog`) is limited to `flat_price` and `cost_plus`. The default strategy on a catalog item must be one the tenant can select, validated at catalog-save time.

```python
# NORMATIVE: shape — every strategy implements this pure protocol
class PricingStrategy(Protocol):
    code: str
    def compute(self, ctx: PricingContext) -> StrategyResult: ...
    # StrategyResult: unit_price: Decimal, trace: dict  — no I/O, no clock, no randomness
```

### 10.5 Resolvers (Exactly Six)

**Status: NORMATIVE.**

Resolvers are the **only** database-touching pricing components. `PricingContextBuilder` runs them in order, each populating part of the context, then freezes it. Resolvers are where effective-dating, entitlement filtering, and input selection happen — so the strategy/modifier pipeline stays pure.

| # | ResolverCode | Populates | Behavior | Gated input |
|---|---|---|---|---|
| 1 | `resolve.cost` | `cost_input`, `cost_source` | Supplier cost (effective-dated) -> product/material `base_cost` -> BOM roll-up | `supplier_costs` for supplier path |
| 2 | `resolve.labor` | `labor_lines` | Resolves labor roles to effective rate-card bill rates | `labor_rate_cards` |
| 3 | `resolve.bom` | `bom_resolution` | Selects the effective BOM version; rolls up component costs | `bom_manufacturing` |
| 4 | `resolve.segment` | `segment_multiplier` | Client's customer-segment multiplier (default 1.0) | `customer_segments` |
| 5 | `resolve.commercial_terms` | `contract_terms`, `price_list_entry` | Client contract pricing and/or applicable price-list entry | `client_contract_pricing`, `price_lists` |
| 6 | `resolve.rules_and_promotions` | `active_rules`, `active_promotions` | Selects active, in-effect pricing rules and promotion campaigns, ordered | `advanced_pricing_rules`, `promotions` |

**Entitlement filtering in resolvers (critical).** Each resolver consults the tenant's entitlements (snapshotted into `ctx.entitlements`). If an input's feature is **not** entitled, the resolver **omits that input** rather than failing — e.g., a Starter tenant without `customer_segments` always resolves `segment_multiplier = 1.0`; without `price_lists`, no price-list entry is selected. This is how the same engine serves every tier: ungated inputs simply do not enter the context. The **selection of a strategy or the explicit use of a gated lever** (manual override, bundle line, manufactured line) is gated harder — it raises rather than silently degrading (Section 10.10).

**Effective-dating rule.** Every effective-dated input (`SupplierCost`, `LaborRateCardEntry`, BOM version, `ClientContractPricing`, `PriceList`, `PricingRule`, `PromotionCampaign`, `TaxRate`) is selected by `ctx.pricing_date` in `[effective_from, effective_to]`. `pricing_date` is resolved once at context-build time and frozen.

### 10.6 Bill of Materials and Manufactured Products

**Status: NORMATIVE.** Entitlement: `bom_manufacturing`, `bom_versioning`. Limit: `max_boms`.

#### 10.6.1 Models

```text
BOM
  id: UUID, pk
  organization_id, product_id: fk                    -- product_kind must be MANUFACTURED
  code, name
  is_active: BOOL, default(true)
  partial_unique (organization_id, product_id) where is_active

BOMVersion
  id: UUID, pk
  organization_id, bom_id: fk
  version_number: INT
  status: ENUM(DRAFT, ACTIVE, SUPERSEDED, ARCHIVED)
  effective_from: DATE
  effective_to: DATE, null
  notes: TEXT, null
  activated_at, activated_by_id
  unique_together (bom_id, version_number)
  partial_index (bom_id) where status = 'ACTIVE'

BOMLine
  id: UUID, pk
  organization_id, bom_version_id: fk
  component_type: ENUM(RAW_MATERIAL, PRODUCT, LABOR)
  raw_material_id / product_id / labor_role_id: UUID, fk, null
  quantity_per_unit: NUMERIC(14,4)
  unit_of_measure: TEXT
  CHECK: exactly one of (raw_material_id, product_id, labor_role_id) is non-null
  CHECK: component_type matches the populated FK
```

#### 10.6.2 BOM Version State Machine

| From | To | Trigger | Actor | Side effects |
|---|---|---|---|---|
| Draft | Active | activate_bom_version | Pricing/Prod manager (`catalog.bom.manage`); entitlement `bom_versioning` | prior ACTIVE -> SUPERSEDED; `effective_from` set |
| Active | Superseded | superseded_by_activation | System | set when a successor activates |
| Draft | Archived | archive_bom_version | manager | — |
| Superseded | Archived | archive_bom_version | manager | — |

**Terminal states:** Archived. Only one ACTIVE version per BOM at a time (partial unique index). Activating a version is effective-dated: the engine selects the version whose window contains `pricing_date`.

#### 10.6.3 Manufactured Product Pricing

A `MANUFACTURED` product line uses `strategy.component_sum` over the resolved BOM:

1. `resolve.bom` selects the effective `BOMVersion` for `pricing_date`.
2. Each `BOMLine` is costed: RAW_MATERIAL/PRODUCT via `resolve.cost` (supplier-effective or base), LABOR via `resolve.labor` (rate-card bill rate).
3. The component costs roll up to a manufactured **cost_input**; the strategy and modifiers then apply (markup, segment, location, etc.).
4. The full BOM roll-up is recorded in the snapshot's `result_payload` so cost provenance is auditable and replayable.

Quoting a manufactured product without `bom_manufacturing`, or with no effective BOM version, raises (`FeatureNotEntitledError` or `PricingConfigurationError` respectively).

### 10.7 Bundles

**Status: NORMATIVE.** Entitlement: `bundles` (basic), `configurable_bundles` (options).

#### 10.7.1 Models

```text
BundleDefinition
  id: UUID, pk
  organization_id: fk
  code, name, description
  bundle_kind: ENUM(FIXED, COMPONENT_SUM, CONFIGURABLE)
  fixed_price: NUMERIC(14,4), null                   -- FIXED only
  is_active: BOOL, default(true)

BundleComponent
  id: UUID, pk
  organization_id, bundle_definition_id: fk
  component_type: ENUM(SERVICE, PRODUCT)
  service_id / product_id: UUID, fk, null
  default_quantity: NUMERIC(14,4)
  is_optional: BOOL, default(false)                  -- CONFIGURABLE only
  option_group: TEXT, null                           -- CONFIGURABLE grouping
  CHECK: exactly one of (service_id, product_id) is non-null
```

#### 10.7.2 Bundle Pricing and Decomposition

- **FIXED**: bundle priced at `fixed_price`; components recorded for fulfillment but do not sum.
- **COMPONENT_SUM**: each component is priced through the engine; the bundle price is the sum (`strategy.component_sum`). Requires `bundles`.
- **CONFIGURABLE**: buyer selects among optional components/option groups; selections recorded in `QuoteVersionLine.selected_options_json`; priced as component-sum over the selected set. Requires `configurable_bundles` (Pro+).

At quote acceptance, a bundle `SalesOrderLine` **decomposes** into child `SalesOrderLine`s (one per resolved component, `parent_sales_order_line_id` set) so each component dispatches its own fulfillment artifact (Section 11). The parent line carries the commercial total; children carry quantities and fulfillment status.

#### 10.7.3 Bundle Drift

Because a bundle's component set or component pricing can change between quote send and acceptance, the engine records a **drift check** at acceptance: it re-resolves the bundle definition and compares the component set/prices to the accepted snapshot. Any difference is written to `SalesOrder.bundle_drift_notes` (JSONB, per bundle) as an **informational** record — acceptance still uses the **accepted snapshot's** prices (immutability wins), but the drift note flags that the live definition has moved, so operators can reconcile. Drift never silently re-prices an accepted line.

### 10.8 Pricing Modifiers (Exactly Sixteen)

**Status: NORMATIVE.**

Modifiers are pure, ordered transforms applied to the strategy's unit price. The pipeline applies them in the fixed canonical order below; a modifier that has no applicable input is a no-op (records `"applied": false` in the trace). New adjustment behaviors are expressed as modifiers, not strategies.

| Order | ModifierCode | Effect | Input source | Gated by |
|---:|---|---|---|---|
| 1 | `modifier.contract` | Apply client contract price/terms | `contract_terms` | `client_contract_pricing` |
| 2 | `modifier.price_list` | Apply price-list entry | `price_list_entry` | `price_lists` |
| 3 | `modifier.segment` | Multiply by segment multiplier | `segment_multiplier` | `customer_segments` |
| 4 | `modifier.volume_tier` | Quantity-tier adjustment | tier table | `advanced_pricing_rules` |
| 5 | `modifier.rule_adjustment` | Apply active pricing-rule adjustments | `active_rules` | `advanced_pricing_rules` |
| 6 | `modifier.location` | Region/Market/Location adjustment | `location_id` | `rml_scope` |
| 7 | `modifier.complexity` | Complexity/difficulty factor | rule-supplied | `advanced_pricing_rules` |
| 8 | `modifier.rush` | Rush/expedite surcharge | rule-supplied | `advanced_pricing_rules` |
| 9 | `modifier.promotion` | Apply active promotion campaigns | `active_promotions` | `promotions` |
| 10 | `modifier.manual_override` | Replace unit price with operator override | line override | `manual_price_overrides` |
| 11 | `modifier.line_discount` | Apply line-level discount | line discount | `basic_quotes` |
| 12 | `modifier.margin_floor` | Enforce minimum margin; may trip approval | floor rule | `advanced_pricing_rules` |
| 13 | `modifier.price_floor` | Enforce absolute price floor; may trip approval | floor rule | `advanced_pricing_rules` |
| 14 | `modifier.rounding` | Apply rounding policy (Section 10.3.5) | policy | `basic_catalog` |
| 15 | `modifier.recurring_term` | Expand per-period for recurring plans | term | `advanced_pricing_rules` |
| 16 | `modifier.tax` | Compute tax amount (does not alter unit price) | `tax_resolution` | `tax_rates` |

**Notes.** `modifier.manual_override` (10) replaces the computed unit price with an explicit operator value and **always** sets a snapshot flag; combined with floors (12/13) it is a primary approval trigger (Section 10.9). `modifier.tax` (16) computes tax as a separate amount on the snapshot and never changes the unit price. Gated modifiers whose feature is not entitled are simply skipped (no-op), consistent with the resolver degradation rule — except `modifier.manual_override`, whose *explicit use* is gated hard (Section 10.10).

### 10.9 Pricing Rules and the Approval Workflow

**Status: NORMATIVE.** Entitlement: `advanced_pricing_rules` (rules), `pricing_approvals` (approval workflow, Pro+).

#### 10.9.1 Pricing Rule Model

```text
PricingRule
  id: UUID, pk
  organization_id: fk
  code, name
  rule_type: ENUM(ADJUSTMENT, MARGIN_FLOOR, PRICE_FLOOR, DISCOUNT_CEILING,
                  APPROVAL_TRIGGER, VOLUME_TIER, COMPLEXITY, RUSH)
  scope: ENUM(ORG, LOCATION, SEGMENT, CLIENT, CATALOG_ITEM, CATEGORY)
  scope_ref_id: UUID, null
  params: JSONB                                      -- thresholds, percentages, tier tables
  priority: INT                                      -- resolution order within a type
  effective_from: DATE
  effective_to: DATE, null
  is_active: BOOL, default(true)
  index (organization_id, rule_type, is_active)
```

#### 10.9.2 Rule Resolution

`resolve.rules_and_promotions` selects active, in-effect rules matching the context's scope chain (org -> location -> segment -> client -> catalog item), ordered by `(rule_type canonical order, priority, id)`. Resolution is deterministic. The selected rules are frozen into `ctx.active_rules` and consumed by the corresponding modifiers (5, 7, 8, 12, 13). Rule **selection** is gated by `advanced_pricing_rules`; an unentitled tenant resolves an empty rule set.

#### 10.9.3 Approval Triggers

A snapshot sets `requires_approval = true` and records `approval_trigger_codes` when, after the pipeline runs:

- a `MARGIN_FLOOR` or `PRICE_FLOOR` would be violated by a discount/override (the floor modifier records `tripped: true`);
- a `DISCOUNT_CEILING` is exceeded;
- a `modifier.manual_override` was applied beyond a configured tolerance;
- an explicit `APPROVAL_TRIGGER` rule matches.

#### 10.9.4 PricingApproval Model and State Machine

```text
PricingApproval
  id: UUID, pk
  organization_id: fk
  quote_version_line_id: fk -> QuoteVersionLine
  pricing_snapshot_id: BIGINT, fk -> PricingSnapshot
  trigger_codes: TEXT[]
  status: ENUM(PENDING, APPROVED, REJECTED, WITHDRAWN)
  requested_by_id, requested_at
  decided_by_id, decided_at, decision_notes
```

| From | To | Trigger | Actor | Notes |
|---|---|---|---|---|
| Pending | Approved | approve_pricing | user w/ `quotes.pricing.approve`; sensitive | line cleared to send |
| Pending | Rejected | reject_pricing | approver | reason required |
| Pending | Withdrawn | withdraw_request | requester | on line edit/removal |

**Send gate (ties to Section 9.4.4).** `send_quote` rejects if any line has a `PENDING` approval (`PricingApprovalPendingError`). **Acceptance gate (Section 9.5.2)** likewise rejects pending approvals. Thus pricing that needs approval cannot reach a customer or an order until resolved.

When `pricing_approvals` is **not** entitled (below Pro), a tripped floor/ceiling does not open an approval workflow; instead the offending action is blocked outright — the discount/override that would breach the floor is rejected at apply-time with `PricingFloorViolationError`. Approval is a Pro+ governance feature; lower tiers get a hard floor rather than a workflow.

#### 10.9.5 Approval RBAC

| Action | Capability | Entitlement |
|---|---|---|
| Request (implicit on trip) | `quotes.edit` | `advanced_pricing_rules` |
| Approve | `quotes.pricing.approve`; sensitive | `pricing_approvals` |
| Reject | `quotes.pricing.approve` | `pricing_approvals` |
| Configure rules | `pricing.rules.manage` | `advanced_pricing_rules` |

### 10.10 Entitlement Enforcement in the Engine

**Status: NORMATIVE.**

The engine enforces Section 7.10's gating map at three precise points, distinguishing **silent degradation** (ungated inputs simply don't enter the context) from **hard denial** (explicit use of a gated lever raises):

**Silent degradation (resolver-level).** If a feature behind an *input* is not entitled, the resolver omits it: no segment multiplier (-> 1.0), no price-list entry, no contract terms, no rules, no promotions, no location modifier. The same engine runs for every tier; lower tiers just see a thinner context. This is what lets a Starter quote and a Pro quote run identical code.

**Hard denial (explicit-lever level).** Explicitly invoking a gated capability raises `FeatureNotEntitledError`:

| Explicit action | Required feature |
|---|---|
| Select a strategy beyond flat/cost-plus | the strategy's gate (Section 10.4) |
| Add a BUNDLE line | `bundles` (or `configurable_bundles` for options) |
| Add a MANUFACTURED_PRODUCT line | `bom_manufacturing` |
| Apply a manual price override | `manual_price_overrides` |
| Open/approve a pricing approval | `pricing_approvals` |
| Manage any gated configuration (price lists, contracts, segments, labor cards, promotions, rules, BOMs, suppliers, raw materials) | the corresponding feature code |

**Limit enforcement.** Create paths for gated configuration call `enforce_limit` (Section 7.7): `max_price_lists`, `max_client_contracts`, `max_promotion_campaigns`, `max_boms`, `max_labor_rate_cards`. A Growth tenant with `labor_rate_cards = Limited` (enabled, `max_labor_rate_cards = 1`) can create exactly one labor rate card; the second raises `PlanLimitExceededError`.

All of this lives in the service layer, so the DRF API and the future React portal inherit it (Section 16).

### 10.11 Pricing Configuration Inputs (Gated)

**Status: NORMATIVE.** Each is a tenant-configured input consumed by a resolver/modifier, gated and limited per Section 7.

| Input | Model summary | Feature | Limit |
|---|---|---|---|
| Customer Segment | `CustomerSegment(code, name, default_multiplier, is_default)`; one STANDARD default per org | `customer_segments` (assign non-default) | — |
| Price List | `PriceList(code, effective window)` + `PriceListEntry(item, unit_price)` | `price_lists` | `max_price_lists` |
| Client Contract Pricing | `ClientContractPricing(client, item/category, price/discount, effective window)` | `client_contract_pricing` | `max_client_contracts` |
| Labor Rate Card | `LaborRateCard(status)` + `LaborRole(code, cost_rate, bill_rate, effective)` | `labor_rate_cards` | `max_labor_rate_cards` |
| Promotion Campaign | `PromotionCampaign(code, modifier, effective window, eligibility)` | `promotions` | `max_promotion_campaigns` |
| Tax | `TaxJurisdiction(code, name)` + `TaxRate(rate, effective window)` | `tax_rates` (Basic on all plans) | — |

The default `CustomerSegment` (STANDARD, multiplier 1.0) and at least Basic `tax_rates` exist on every plan (seeded at org creation, Section 6.3), so pricing always has a baseline segment and a tax path even on Starter.

### 10.12 Tax Application

**Status: NORMATIVE.**

`modifier.tax` computes tax as a separate amount and never alters the unit price. `resolve.commercial_terms`/the tax resolver select the effective `TaxRate` for the line's `TaxJurisdiction` (derived from location/client) at `pricing_date`. A line marked `taxable = false`, or a client marked `tax_exempt = true`, yields zero tax (the exemption certificate ref is recorded on the client). Tax amounts roll up to the document total (Section 12). Multi-jurisdiction compound tax beyond a single resolved rate per line is post-MVP.

### 10.13 Replay and Audit

**Status: NORMATIVE.**

- **Replay.** Given a stored `PricingSnapshot`, the engine MUST recompute the identical `result_payload` by loading the code at `engine_version` and re-running the pipeline over `context_payload`, asserting the recomputed `content_hash` equals the stored hash. A replay-mismatch is a defect (or an unversioned engine change) and fails CI's golden-snapshot test.
- **Golden snapshots.** CI stores a corpus of representative `(context -> snapshot)` pairs at engine `"1.0"`; any code change that alters a golden output without an engine-version bump fails the build.
- **Audit.** Pricing emits `PRICING_SNAPSHOT_CREATED`, `PRICING_LINE_OVERRIDDEN`, `PRICING_APPROVAL_REQUESTED/APPROVED/REJECTED/WITHDRAWN`, `PRICING_FLOOR_BLOCKED`, and configuration events (`PRICE_LIST_*`, `CONTRACT_*`, `RULE_*`, `PROMOTION_*`, `BOM_VERSION_*`, `LABOR_RATE_CARD_*`). Overrides and approvals carry the actor and on-behalf-of (under impersonation).

### 10.14 Acceptance Criteria

**Status: NORMATIVE.**

| # | Criterion | Verification |
|---|---|---|
| 1 | Exactly seven strategies exist; adding one requires a guide PR (registry test) | registry test |
| 2 | Exactly six resolvers and sixteen modifiers exist, in the canonical order of 10.5/10.8 | registry + order test |
| 3 | Strategies and modifiers are pure: no clock/DB/random access (static + runtime check) | AST + runtime test |
| 4 | Identical context + engine version => byte-identical result payload | determinism test |
| 5 | Money math is Decimal; final rounding is HALF_EVEN at the specified scales | unit test |
| 6 | `resolve.cost` selects supplier cost by effective date; falls back to base cost | service test |
| 7 | Effective-dated inputs are selected by `pricing_date` in window across all gated inputs | parametrized test |
| 8 | Unentitled inputs degrade silently (segment->1.0; no price list/contract/rules/promotions/location) | service test per input |
| 9 | Selecting a gated strategy without entitlement raises `FeatureNotEntitledError` | service test |
| 10 | Adding a bundle / manufactured line without entitlement raises | service test |
| 11 | Manual override without `manual_price_overrides` raises; with it, sets the override flag | service test |
| 12 | Manufactured product prices via component-sum over the effective BOM; roll-up in payload | service test |
| 13 | Quoting a manufactured product with no effective BOM raises `PricingConfigurationError` | service test |
| 14 | Only one ACTIVE BOM version per BOM; activation supersedes the prior (property test) | property test |
| 15 | FIXED/COMPONENT_SUM/CONFIGURABLE bundles price per 10.7.2; bundle decomposes at acceptance | service test |
| 16 | Bundle drift is recorded informationally; accepted line keeps the accepted snapshot's price | service test |
| 17 | Floor/ceiling trip sets `requires_approval` with trigger codes (Pro+) | service test |
| 18 | Below Pro, a floor-breaching discount/override is blocked with `PricingFloorViolationError` | service test |
| 19 | `send_quote` and `accept_quote` reject lines with a PENDING approval | service test |
| 20 | Approve is sensitive (re-auth) and gated by `pricing_approvals` | integration test |
| 21 | Plan limits enforced on price lists, contracts, promotions, BOMs, labor cards (`PlanLimitExceededError`) | service test |
| 22 | `modifier.tax` computes tax as a separate amount; `taxable=false`/`tax_exempt` => zero | service test |
| 23 | Snapshot replay reproduces the stored `content_hash` at engine 1.0 (golden-snapshot CI) | CI |
| 24 | Re-pricing creates a new snapshot; lines re-point FK; old snapshot never mutated | service test |
| 25 | Pricing config + override + approval events are audited with actor/on-behalf-of | integration test |

---

## Section 11 — Operational Workflow Requirements

### 11.1 Scope and Fulfillment Posture

**Status: NORMATIVE.**

Section 11 specifies what happens **after** a quote is accepted: how an accepted `SalesOrder` dispatches operational work, and how that work is tracked to completion. It covers fulfillment dispatch, Work Orders (service execution), Purchase Orders (resale procurement), and Build Orders (manufactured production). Invoicing of the resulting work is Section 12; the pricing snapshots these artifacts reference are Section 10.

The operational model rests on three rules:

1. **One `SalesOrderLine` dispatches one fulfillment artifact**, chosen by line type. This is the MVP simplification flagged by the quote builder's multi-visit hint (Section 9.4.6). Splitting one line into multiple visits/batches is post-MVP.
2. **Dispatch is outbox-driven and idempotent.** Acceptance enqueues one dispatch entry per resulting line (Section 9.5.2); a worker consumes each entry exactly once (Section 11.2). Fulfillment artifacts are never created inline in the acceptance request.
3. **Each artifact family is independently entitlement-gated.** Work Orders require `work_orders`, Purchase Orders require `purchase_orders`, Build Orders require `build_orders` (+ `bom_manufacturing`). The dispatch itself respects these gates per Section 11.2.4.

```text
Accepted SalesOrder
  +- for each SalesOrderLine:
       SERVICE              -> Work Order        (gate: work_orders)
       RESALE_PRODUCT       -> Purchase Order    (gate: purchase_orders)   [operator-driven]
       MANUFACTURED_PRODUCT -> Build Order       (gate: build_orders + bom_manufacturing)
       BUNDLE (parent)      -> decompose -> children dispatched per child type
```

### 11.2 Fulfillment Dispatch

**Status: NORMATIVE.**

#### 11.2.1 Dispatch Entry Point

Quote acceptance (Section 9.5.2) enqueues one `sales_order.dispatch_line` outbox entry per resulting `SalesOrderLine`, keyed by the line id. The dispatch worker is the single place that maps a line to its fulfillment artifact.

```python
def dispatch_sales_order_line(*, organization_id, sales_order_line_id,
                              idempotency_key) -> DispatchResult:
    """
    Outbox-consumed; actor = System User.
    Idempotent on (organization_id, sales_order_line_id): re-running finds the existing
    artifact and returns it rather than creating a duplicate.
    """
```

#### 11.2.2 Line-Type Routing

| `SalesOrderLine.line_type` | Artifact | Initial state | Entitlement | Notes |
|---|---|---|---|---|
| `SERVICE` | WorkOrder | `UNSCHEDULED` | `work_orders` | Auto-created on dispatch |
| `RESALE_PRODUCT` | PurchaseOrder | (operator-driven) | `purchase_orders` | Dispatch marks the line `awaiting_procurement`; a PO is created by an operator, not auto-generated (Section 11.4.2) |
| `MANUFACTURED_PRODUCT` | BuildOrder | `PLANNED` | `build_orders` + `bom_manufacturing` | BOM snapshot taken at dispatch (Section 11.5.3) |
| `BUNDLE` (parent) | none directly | — | per child | Parent already decomposed at acceptance (Section 10.7.2); children are themselves `SalesOrderLine`s dispatched by their own type |

A line whose type maps to no operational artifact (e.g., a non-fulfilled fee line) is set `fulfillment_status = NOT_APPLICABLE` and `invoice_eligibility = ELIGIBLE` (it can be invoiced without operational work).

#### 11.2.3 Bundle Children

Bundle decomposition happens at acceptance (Section 10.7.2): the parent bundle line is expanded into child `SalesOrderLine`s with `parent_sales_order_line_id` set, one per resolved component. Dispatch treats each **child** as an ordinary line and routes it by its own `line_type`. The **parent** bundle line carries the commercial total and is itself `fulfillment_status = NOT_APPLICABLE` (its children carry the real fulfillment). A bundle's invoice eligibility rolls up from its children (Section 12).

#### 11.2.4 Entitlement at Dispatch

Dispatch enforces the artifact's entitlement gate at the moment it would create the artifact. Two cases:

- **Entitled** -> the artifact is created and the line proceeds.
- **Not entitled** -> dispatch does **not** raise into the worker (that would dead-letter a System-actor task). Instead it sets the line `fulfillment_status = BLOCKED_ENTITLEMENT`, records the missing feature code on the line, and emits `FULFILLMENT_DISPATCH_BLOCKED`. The order surfaces a non-blocking banner ("Fulfillment for this line requires the {feature} feature"), and an operator can resolve it by having the plan/add-on enabled, then re-running dispatch.

This handles the legitimate case from Section 9.5.2: a Starter tenant without `work_orders` can accept a service quote (a sales order is a `sales_orders`-gated record, which Starter has as Limited), but the downstream work-order dispatch is blocked until `work_orders` is enabled. Acceptance is not retroactively undone; the order simply waits.

#### 11.2.5 Dispatch Idempotency and Recompute

Dispatch is idempotent on the line id: a redelivered outbox entry finds the existing artifact and returns it. After any artifact state change, the system calls `recompute_sales_order_status` (Section 9.5.5) and `recompute_invoice_eligibility` (Section 12) so the parent order's status and the line's invoice eligibility stay consistent. Both recompute functions are pure derivations of child-artifact state and are safe to call repeatedly.

### 11.3 Work Orders (Service Execution)

**Status: NORMATIVE.** Entitlement: `work_orders` (Growth+, or Starter via the Work Orders add-on).

#### 11.3.1 Models

```text
WorkOrder
  id: UUID, pk
  organization_id: fk -> Organization on_delete=PROTECT
  location_id: UUID, fk -> Location on_delete=PROTECT       -- inherited from the line; immutable
  number: TEXT                                              -- "WO-2026-00042"
  sales_order_id: fk -> SalesOrder
  sales_order_line_id: fk -> SalesOrderLine                 -- the originating service line
  status: ENUM(UNSCHEDULED, SCHEDULED, IN_PROGRESS, ON_HOLD, COMPLETED, CANCELLED)
  assigned_to_id: UUID, fk -> Membership, null
  scheduled_start_at, scheduled_end_at: TIMESTAMPTZ, null
  actual_start_at, actual_end_at: TIMESTAMPTZ, null
  on_hold_reason: TEXT, null
  completion_notes: TEXT, null
  cancelled_at, cancelled_by_id, cancelled_reason
  index (organization_id, status)
  index (organization_id, assigned_to_id, status)
  index (organization_id, sales_order_id)

WorkOrderNote
  id, organization_id, work_order_id: fk
  body: TEXT
  author_membership_id: fk -> Membership
  created_at: TIMESTAMPTZ

WorkOrderCompletionPhoto                                    -- DocumentAttachment link (Section 13)
  id, organization_id, work_order_id: fk
  document_attachment_id: fk -> DocumentAttachment
```

Completion photos/notes are an MVP feature of the Work Orders add-on (Section 7.3). They attach through the standard `DocumentAttachment` mechanism (Section 13), so retention and tenancy apply uniformly.

#### 11.3.2 State Machine

| From | To | Trigger | Actor | Side effects |
|---|---|---|---|---|
| Unscheduled | Scheduled | schedule_work_order | Dispatcher/Manager | `scheduled_*` set; line -> IN_PROGRESS |
| Unscheduled / Scheduled | In_Progress | start_work_order | Assignee | `actual_start_at` set; SO -> IN_FULFILLMENT |
| In_Progress | On_Hold | hold_work_order | Assignee/Manager | `on_hold_reason` required |
| On_Hold | In_Progress | resume_work_order | Assignee/Manager | — |
| In_Progress / On_Hold | Completed | complete_work_order | Assignee/Manager | `actual_end_at`; line FULFILLED; invoice eligibility recomputed |
| Unscheduled / Scheduled / On_Hold | Cancelled | cancel_work_order | Manager | reason; line -> CANCELLED if no other coverage |

**Terminal states:** Completed, Cancelled. Completion is the event that makes the originating service line invoice-eligible (Section 12).

#### 11.3.3 Service Surface

```python
def schedule_work_order(*, organization_id, actor_id, work_order_id,
                        assigned_to_id, scheduled_start_at, scheduled_end_at) -> WorkOrder: ...
def start_work_order(*, organization_id, actor_id, work_order_id) -> WorkOrder: ...
def hold_work_order(*, organization_id, actor_id, work_order_id, reason) -> WorkOrder: ...
def resume_work_order(*, organization_id, actor_id, work_order_id) -> WorkOrder: ...
def complete_work_order(*, organization_id, actor_id, work_order_id,
                        completion_notes=None) -> WorkOrder: ...
def cancel_work_order(*, organization_id, actor_id, work_order_id, reason) -> WorkOrder: ...
def reassign_work_order(*, organization_id, actor_id, work_order_id,
                        assigned_to_id) -> WorkOrder: ...
def add_work_order_note(*, organization_id, actor_id, work_order_id, body) -> WorkOrderNote: ...
```

Every transition requires `require_feature(work_orders)` and is RML-object-checked: a scoped membership can act only on work orders whose `location_id` is in its permitted closure (Section 8.14).

#### 11.3.4 RBAC Enforcement (Work Order)

| View / Action | Queryset | Capability | Object check | Audit |
|---|---|---|---|---|
| WO list / detail | `for_membership(m)` | `work_orders.view` | — | — |
| Schedule / reassign | `for_membership(m)` | `work_orders.schedule` | location in scope; status precondition | `WORK_ORDER_SCHEDULED` / `_REASSIGNED` |
| Start / hold / resume | `for_membership(m)` | `work_orders.execute` | assignee or manager | `WORK_ORDER_STATUS_CHANGED` |
| Complete | `for_membership(m)` | `work_orders.complete` | IN_PROGRESS/ON_HOLD | `WORK_ORDER_COMPLETED` |
| Cancel | `for_membership(m)` | `work_orders.cancel` | not terminal | `WORK_ORDER_CANCELLED` |
| Add note / photo | `for_membership(m)` | `work_orders.execute` | location in scope | `WORK_ORDER_NOTE_ADDED` |

**Entitlement gate:** all operations require `work_orders`.

### 11.4 Purchase Orders (Resale Procurement)

**Status: NORMATIVE.** Entitlement: `purchase_orders` (+ `suppliers`, `supplier_costs` for cost sourcing). Available to Growth+ or Starter via the Purchasing add-on.

#### 11.4.1 Models

```text
PurchaseOrder
  id: UUID, pk
  organization_id, location_id: fk
  number: TEXT                                              -- "PO-2026-00042"
  supplier_id: fk -> Supplier
  status: ENUM(DRAFT, ISSUED, PARTIALLY_RECEIVED, RECEIVED, CLOSED, CANCELLED)
  expected_at: DATE, null
  issued_at, issued_by_id
  notes: TEXT, null
  cancelled_at, cancelled_by_id, cancelled_reason
  index (organization_id, status)
  index (organization_id, supplier_id)

PurchaseOrderLine
  id, organization_id, purchase_order_id: fk
  product_id / raw_material_id: UUID, fk, null              -- exactly one non-null
  description_snapshot: TEXT
  quantity_ordered: NUMERIC(14,4)
  quantity_received: NUMERIC(14,4), default(0)
  unit_cost: NUMERIC(14,4)                                  -- from SupplierCost at PO creation
  currency_code: CHAR(3)
  CHECK: exactly one of (product_id, raw_material_id) is non-null
  CHECK: quantity_received <= quantity_ordered

PurchaseOrderAllocation                                     -- links a PO line to the SO line it serves
  id, organization_id
  purchase_order_line_id: fk -> PurchaseOrderLine
  sales_order_line_id: fk -> SalesOrderLine
  allocated_quantity: NUMERIC(14,4)

PurchaseOrderReceipt
  id, organization_id, purchase_order_id: fk
  received_at: TIMESTAMPTZ
  received_by_id: fk -> Membership
  notes: TEXT, null

PurchaseOrderReceiptLine
  id, organization_id, receipt_id, purchase_order_line_id: fk
  quantity_received: NUMERIC(14,4)
```

#### 11.4.2 Operator-Driven Creation

Unlike work orders and build orders, a Purchase Order is **not auto-created at dispatch**. Resale procurement is consolidated: one PO to a supplier often covers many sales-order lines. So dispatch of a `RESALE_PRODUCT` line marks it `fulfillment_status = AWAITING_PROCUREMENT` and surfaces it in a procurement queue; an operator then creates a PO, adds lines, and **allocates** PO-line quantities against the waiting sales-order lines via `PurchaseOrderAllocation`.

```python
def create_purchase_order(*, organization_id, actor_id, supplier_id,
                          expected_at=None, notes=None) -> PurchaseOrder: ...     # DRAFT
def add_purchase_order_line(*, organization_id, actor_id, purchase_order_id,
                            item_ref, quantity_ordered) -> PurchaseOrderLine:
    # unit_cost resolved from effective SupplierCost (requires supplier_costs)
def allocate_purchase_order_line(*, organization_id, actor_id, purchase_order_line_id,
                                 sales_order_line_id, allocated_quantity) -> PurchaseOrderAllocation: ...
def issue_purchase_order(*, organization_id, actor_id, purchase_order_id) -> PurchaseOrder:
    # DRAFT -> ISSUED; outbox publishes the PO document to the supplier
def receive_purchase_order(*, organization_id, actor_id, purchase_order_id,
                           receipt_lines) -> PurchaseOrderReceipt:
    # records quantities; updates line quantity_received; recomputes PO + allocated SO lines
def cancel_purchase_order(*, organization_id, actor_id, purchase_order_id, reason) -> PurchaseOrder: ...
```

#### 11.4.3 State Machine

| From | To | Trigger | Actor | Side effects |
|---|---|---|---|---|
| Draft | Issued | issue_purchase_order | Purchaser | outbox publishes PO; allocations locked |
| Draft | Cancelled | cancel_purchase_order | Purchaser/Manager | reason required |
| Issued | Partially_Received | receive_purchase_order (partial) | Receiver | allocated SO lines advance proportionally |
| Issued / Partially_Received | Received | receive_purchase_order (full) | Receiver | all lines fully received |
| Issued / Partially_Received | Cancelled | cancel_purchase_order | Manager | reason; un-received allocations released |
| Received | Closed | close_purchase_order | System/Purchaser | all allocations satisfied |

**Terminal states:** Closed, Cancelled.

#### 11.4.4 Receipt -> Fulfillment Linkage

When a receipt records quantity against a PO line, each `PurchaseOrderAllocation` on that line advances its served `SalesOrderLine`: a fully-received allocation sets the SO line `fulfillment_status = FULFILLED` and makes it invoice-eligible; a partial receipt holds it `IN_PROGRESS`. `recompute_sales_order_status` runs after each receipt. Resale lines therefore become invoiceable on **receipt**, mirroring how service lines become invoiceable on work-order **completion**.

#### 11.4.5 RBAC Enforcement (Purchase Order)

| View / Action | Queryset | Capability | Object check | Audit |
|---|---|---|---|---|
| PO list / detail | `for_membership(m)` | `purchase_orders.view` | — | — |
| Create / edit draft | `for_membership(m)` | `purchase_orders.manage` | DRAFT | `PURCHASE_ORDER_CREATED` / `_UPDATED` |
| Allocate to SO line | `for_membership(m)` | `purchase_orders.manage` | both in org+scope | `PURCHASE_ORDER_ALLOCATED` |
| Issue | `for_membership(m)` | `purchase_orders.issue` | DRAFT; >=1 line | `PURCHASE_ORDER_ISSUED` |
| Receive | `for_membership(m)` | `purchase_orders.receive` | ISSUED/PARTIALLY_RECEIVED | `PURCHASE_ORDER_RECEIVED` |
| Cancel | `for_membership(m)` | `purchase_orders.cancel` | not terminal | `PURCHASE_ORDER_CANCELLED` |

**Entitlement gate:** all operations require `purchase_orders`; cost resolution on a PO line requires `supplier_costs`.

### 11.5 Build Orders (Manufactured Production)

**Status: NORMATIVE.** Entitlement: `build_orders` + `bom_manufacturing` (Pro+). Labor tracking requires `build_labor_tracking`; variance requires `build_cost_variance`.

#### 11.5.1 Models

```text
BuildOrder
  id: UUID, pk
  organization_id, location_id: fk
  number: TEXT                                              -- "BO-2026-00042"
  sales_order_id, sales_order_line_id: fk
  product_id: fk -> Product                                 -- product_kind = MANUFACTURED
  bom_version_id: fk -> BOMVersion                          -- SNAPSHOTTED at dispatch (immutable)
  quantity: NUMERIC(14,4)
  status: ENUM(PLANNED, RELEASED, IN_PROGRESS, COMPLETED, CANCELLED)
  estimated_cost: NUMERIC(14,2)                             -- from the BOM roll-up at dispatch
  actual_cost: NUMERIC(14,2), null                          -- computed at completion
  released_at, started_at, completed_at: TIMESTAMPTZ, null
  cancelled_at, cancelled_by_id, cancelled_reason
  index (organization_id, status)

BuildOrderComponent                                          -- frozen copy of BOM lines at dispatch
  id, organization_id, build_order_id: fk
  component_type: ENUM(RAW_MATERIAL, PRODUCT, LABOR)
  raw_material_id / product_id / labor_role_id: UUID, fk, null
  planned_quantity: NUMERIC(14,4)
  planned_unit_cost: NUMERIC(14,4)
  actual_quantity: NUMERIC(14,4), null
  actual_unit_cost: NUMERIC(14,4), null

BuildLaborEntry                                              -- gate: build_labor_tracking
  id, organization_id, build_order_id: fk
  labor_role_id: fk -> LaborRole
  membership_id: fk -> Membership, null
  hours: NUMERIC(14,4)
  cost_rate_snapshot: NUMERIC(14,4)                          -- from rate card at entry time
  entered_by_id, entered_at
  adjustment_of_id: fk -> BuildLaborEntry, null              -- append-only correction
```

#### 11.5.2 State Machine

| From | To | Trigger | Actor | Side effects |
|---|---|---|---|---|
| Planned | Released | release_build_order | Production manager | components frozen; SO -> IN_FULFILLMENT |
| Released | In_Progress | start_build_order | Production staff | `started_at` set |
| In_Progress | Completed | complete_build_order | Production manager | `actual_cost` computed; line FULFILLED; variance available |
| Planned / Released / In_Progress | Cancelled | cancel_build_order | Manager | reason; line -> CANCELLED if no other coverage |

**Terminal states:** Completed, Cancelled. Completion makes the manufactured line invoice-eligible.

#### 11.5.3 BOM Snapshot at Dispatch

When a `MANUFACTURED_PRODUCT` line dispatches, the build order **snapshots** the effective `BOMVersion` (selected by the dispatch date) into `BuildOrderComponent` rows with `planned_quantity` and `planned_unit_cost` copied from the resolved BOM roll-up (Section 10.6.3). This freeze is essential: a later BOM-version activation MUST NOT alter an in-flight build order. The `estimated_cost` is the sum of planned component costs. The build order references the originating `BOMVersion` for traceability but operates off its frozen components.

#### 11.5.4 Build Labor and Cost Variance

```python
def record_build_labor(*, organization_id, actor_id, build_order_id,
                       labor_role_id, hours, membership_id=None) -> BuildLaborEntry:
    """ cap: build_orders.labor; entitlement: build_labor_tracking
        cost_rate_snapshot taken from the effective labor rate card """
def adjust_build_labor(*, organization_id, actor_id, build_labor_entry_id,
                       corrected_hours, reason) -> BuildLaborEntry:
    """ Append-only: writes a NEW entry with adjustment_of set; never edits in place """
```

Labor entries are **append-only**; a correction is a new `BuildLaborEntry` referencing the original via `adjustment_of_id` (consistent with the payment-adjustment pattern, Section 12). At completion, `actual_cost = sum(actual component costs) + sum(labor hours x cost_rate_snapshot)`. **Cost variance** (`build_cost_variance`) is the derived `actual_cost - estimated_cost`, surfaced per component and in aggregate — a reporting/analysis feature, gated separately so a Pro tenant gets build orders and labor while variance reporting can be tier-positioned independently.

Build labor tracking and variance degrade independently: a tenant with `build_orders` but not `build_labor_tracking` runs build orders with planned costs only (no labor entries); without `build_cost_variance`, actual cost is still computed but the variance view is hidden.

#### 11.5.5 RBAC Enforcement (Build Order)

| View / Action | Queryset | Capability | Object check | Audit |
|---|---|---|---|---|
| BO list / detail | `for_membership(m)` | `build_orders.view` | — | — |
| Release | `for_membership(m)` | `build_orders.release` | PLANNED | `BUILD_ORDER_RELEASED` |
| Start | `for_membership(m)` | `build_orders.execute` | RELEASED | `BUILD_ORDER_STARTED` |
| Record / adjust labor | `for_membership(m)` | `build_orders.labor` | not terminal; ent. `build_labor_tracking` | `BUILD_LABOR_RECORDED` / `_ADJUSTED` |
| Complete | `for_membership(m)` | `build_orders.complete` | IN_PROGRESS | `BUILD_ORDER_COMPLETED` |
| Cancel | `for_membership(m)` | `build_orders.cancel` | not terminal | `BUILD_ORDER_CANCELLED` |
| View variance | `for_membership(m)` | `build_orders.view` | ent. `build_cost_variance` | — |

**Entitlement gate:** all operations require `build_orders` + `bom_manufacturing`; labor requires `build_labor_tracking`; variance requires `build_cost_variance`.

### 11.6 Cross-Artifact Invariants

**Status: NORMATIVE.**

1. **Location inheritance.** A fulfillment artifact inherits `location_id` from its originating `SalesOrderLine` (via the order) and it is immutable. RML scope checks (Section 8.14) apply to all artifact operations using this location.
2. **No commercial mutation.** Fulfillment artifacts never alter pricing snapshots, line totals, or order commercial values. They carry operational state only; money is fixed at acceptance (Section 9.5) and realized at invoicing (Section 12).
3. **Invoice eligibility is artifact-driven.** A line becomes `invoice_eligibility = ELIGIBLE` when its artifact reaches the eligibility event: work order **completed**, purchase-order allocation **received**, build order **completed**, or `NOT_APPLICABLE` lines immediately. `recompute_invoice_eligibility` derives this purely from artifact state (Section 12).
4. **Order status is derived.** `recompute_sales_order_status` is the single authority for `SalesOrder.status`; artifact transitions call it but never set order status directly.
5. **System actor on dispatch.** Auto-created artifacts (work orders, build orders) are attributed to the System User; subsequent human transitions carry the acting membership. Under impersonation, attribution carries actor + on-behalf-of (Section 8.15).
6. **Cancellation coherence.** A `SalesOrder` cannot be cancelled while any non-terminal artifact exists (Section 9.5.6); artifacts must be cancelled first.

### 11.7 State-Machine Property Tests

**Status: NORMATIVE.**

For WorkOrder, PurchaseOrder, and BuildOrder, a Hypothesis property test asserts the same invariants as Section 9.9: every declared transition maps to an executable service function taking `organization_id`/`actor_id`; no service performs an undeclared transition; terminal states have no outgoing transitions; and the recompute functions (`recompute_sales_order_status`, `recompute_invoice_eligibility`) are idempotent — calling them repeatedly with unchanged artifact state yields an unchanged result. The state tables here are the contract (Architectural Principle 8).

### 11.8 Acceptance Criteria

**Status: NORMATIVE.**

| # | Criterion | Verification |
|---|---|---|
| 1 | Acceptance enqueues exactly one `dispatch_line` outbox entry per resulting SalesOrderLine | service test |
| 2 | Dispatch is idempotent on line id; redelivery returns the existing artifact (no duplicate) | service test |
| 3 | SERVICE -> WorkOrder (UNSCHEDULED); MANUFACTURED -> BuildOrder (PLANNED) auto-created on dispatch | service test |
| 4 | RESALE line dispatch sets AWAITING_PROCUREMENT; no PO auto-created | service test |
| 5 | Bundle children dispatch by their own type; parent bundle line is NOT_APPLICABLE | service test |
| 6 | Dispatch without the artifact's entitlement sets BLOCKED_ENTITLEMENT and emits `FULFILLMENT_DISPATCH_BLOCKED` (no dead-letter) | service test |
| 7 | Re-running dispatch after entitlement is enabled creates the artifact | integration test |
| 8 | WorkOrder lifecycle matches 11.3.2; property test passes | property test |
| 9 | Work-order completion makes the service line invoice-eligible | service test |
| 10 | PO creation is operator-driven; lines source unit_cost from effective SupplierCost | service test |
| 11 | PO allocation links PO lines to SO lines; over-allocation beyond ordered qty is rejected | service test |
| 12 | PO receipt advances allocated SO lines; full receipt sets FULFILLED + invoice-eligible | service test |
| 13 | PurchaseOrder lifecycle matches 11.4.3; `quantity_received <= quantity_ordered` enforced | property + DB test |
| 14 | BuildOrder snapshots the effective BOM into frozen BuildOrderComponents at dispatch | service test |
| 15 | A later BOM-version activation does not alter an in-flight build order | integration test |
| 16 | Build labor is append-only; corrections write a new entry via `adjustment_of` | service test |
| 17 | Build labor requires `build_labor_tracking`; absent it, build runs on planned cost only | service test |
| 18 | actual_cost computed at completion; variance = actual - estimated, gated by `build_cost_variance` | service test |
| 19 | BuildOrder lifecycle matches 11.5.2; property test passes | property test |
| 20 | All artifact operations require their family's entitlement and pass RML object checks | service test |
| 21 | Fulfillment artifacts never mutate pricing snapshots or commercial totals | service test |
| 22 | `recompute_sales_order_status` / `recompute_invoice_eligibility` are idempotent | property test |
| 23 | SalesOrder cancellation blocked while any non-terminal artifact exists | service test |
| 24 | Auto-created artifacts attribute to System User; human transitions carry the membership | service test |
| 25 | Capability-coverage CI test passes for all operational routes | CI |

---

## Section 12 — Billing Requirements

### 12.1 Scope and Billing Posture

**Status: NORMATIVE.**

Section 12 specifies how a tenant bills **its own customers**: invoice generation from fulfilled work, the snapshot-driven invoice model, payment recording, allocations, append-only adjustments, tax roll-up, and the accounting-sync boundary. It does **not** cover how MyPipelineHero bills its tenants — that is platform SaaS subscription billing, a wholly separate domain (Section 7.14), and the two never share models, tables, or numbering.

Three posture rules govern this domain:

1. **Invoices are snapshot-driven, never re-priced.** An invoice line copies its commercial values from the `PricingSnapshot` already attached to the originating `SalesOrderLine` (Section 9.5, Section 10.3.4). Billing performs no pricing computation; it aggregates already-frozen line math (Section 10.3.5) into document totals.
2. **Money records are immutable or append-only.** A posted invoice is immutable; corrections happen through new adjustment rows, never edits. Payments and their allocations are append-only; reversals are new rows referencing the original (the same pattern as build-labor corrections, Section 11.5.4).
3. **Invoice eligibility is artifact-driven and consumed here.** A `SalesOrderLine` becomes invoiceable when its fulfillment artifact reaches its eligibility event (Section 11.6 rule 3). Billing consumes `invoice_eligibility = ELIGIBLE`; it does not decide eligibility.

The core billing features (`basic_invoicing`, `standard_reports`) are **universal** — every plan, including Starter, can invoice customers and record payments. Only `advanced_reporting` is tier-gated (Section 7.4).

### 12.2 Invoicing Policy

**Status: NORMATIVE.**

Each organization has exactly one `InvoicingPolicy`, created in the same transaction as the Organization (Section 5.2, Section 6.3). It carries the tenant's default billing behavior.

```text
InvoicingPolicy
  id: UUID, pk
  organization_id: fk -> Organization on_delete=PROTECT, unique
  default_payment_terms_days: INT, default(30)
  invoice_on: ENUM(LINE_ELIGIBLE, ORDER_FULLY_FULFILLED), default(LINE_ELIGIBLE)
  allow_partial_invoicing: BOOL, default(true)
  default_footer_text: TEXT, null
  default_notes_text: TEXT, null
  rounding_policy: ENUM(HALF_EVEN), default(HALF_EVEN)   -- matches Section 10.3.5
  created_at, updated_at: TIMESTAMPTZ
```

`invoice_on` chooses the billing rhythm: `LINE_ELIGIBLE` invoices each line as it becomes eligible (progress billing); `ORDER_FULLY_FULFILLED` waits until every invoiceable line on the order is eligible (single final invoice). `allow_partial_invoicing` governs whether a single invoice may cover a subset of eligible lines. These are tenant-configurable defaults, overridable per invoice within policy.

### 12.3 Invoice Model

**Status: NORMATIVE.**

```text
Invoice
  id: UUID, pk
  organization_id: fk -> Organization on_delete=PROTECT
  location_id: UUID, fk -> Location on_delete=PROTECT      -- inherited from the order; immutable
  number: TEXT                                             -- "INV-2026-00042"
  client_id: fk -> Client
  sales_order_id: fk -> SalesOrder
  status: ENUM(DRAFT, ISSUED, PARTIALLY_PAID, PAID, VOID)
  issue_date: DATE, null                                   -- set at ISSUE
  due_date: DATE, null                                     -- issue_date + terms
  payment_terms_days: INT                                  -- copied from client/policy at creation
  currency_code: CHAR(3)
  subtotal_amount: NUMERIC(14,2)
  discount_amount: NUMERIC(14,2)
  tax_amount: NUMERIC(14,2)
  total_amount: NUMERIC(14,2)
  amount_paid: NUMERIC(14,2), default(0)                   -- derived; maintained on allocation
  amount_due: NUMERIC(14,2)                                -- derived = total - amount_paid + adjustments
  notes, footer_text: TEXT, null
  issued_by_id, issued_at
  voided_at, voided_by_id, voided_reason
  index (organization_id, status)
  index (organization_id, client_id)
  index (organization_id, sales_order_id)
  partial_index (organization_id, due_date) where status in ('ISSUED','PARTIALLY_PAID')

InvoiceLine
  id: UUID, pk
  organization_id, invoice_id: fk
  sales_order_line_id: fk -> SalesOrderLine                -- the fulfilled line being billed
  pricing_snapshot_id: BIGINT, fk -> PricingSnapshot       -- SAME snapshot as the SO line
  description_snapshot: TEXT
  quantity: NUMERIC(14,4)
  unit_price_snapshot: NUMERIC(14,4)
  line_subtotal: NUMERIC(14,2)
  line_discount_amount: NUMERIC(14,2)
  tax_amount: NUMERIC(14,2)
  line_total: NUMERIC(14,2)
  taxable: BOOL
  unique_together (invoice_id, sales_order_line_id)        -- a line billed once per invoice
```

An `InvoiceLine` references the **same** `PricingSnapshot` as its `SalesOrderLine`; it never recomputes. The unique constraint plus the line's `invoice_eligibility = INVOICED` flag (set on issue) guarantee a sales-order line is billed exactly once across all invoices for the order.

### 12.4 Invoice State Machine

**Status: NORMATIVE.**

| From | To | Trigger | Actor | Side effects |
|---|---|---|---|---|
| (none) | Draft | create_invoice | Billing user | lines copied from eligible SO lines |
| Draft | Issued | issue_invoice | Billing user | `issue_date`/`due_date` set; lines -> INVOICED; outbox publishes PDF/email; immutable |
| Draft | Void | void_draft_invoice | Billing user | lines released back to ELIGIBLE; no audit-money impact |
| Issued | Partially_Paid | payment_allocated (partial) | System | on allocation < amount_due |
| Issued / Partially_Paid | Paid | payment_allocated (full) | System | when amount_due reaches 0 |
| Issued / Partially_Paid | Void | void_issued_invoice | Billing manager; sensitive | reason; reverses allocations; lines released; emits reversal |
| Paid | Void | void_issued_invoice | Billing manager; sensitive | rare; reason required; full reversal |

**Terminal states:** Paid (until/unless voided), Void. An **Issued** invoice is immutable in its commercial values; the only post-issue mutations are payment allocations (which adjust derived `amount_paid`/`amount_due`) and a void (which is a reversal, not an edit). Voiding an issued invoice releases its lines back to `ELIGIBLE` so they can be re-billed on a corrected invoice.

### 12.5 Invoice Generation

**Status: NORMATIVE.**

```python
def create_invoice(*, organization_id, actor_id, sales_order_id,
                   sales_order_line_ids=None, idempotency_key) -> Invoice:
    """
    cap: invoicing.create; entitlement: basic_invoicing (universal)
    Creates a DRAFT invoice from ELIGIBLE lines on the order.
    sales_order_line_ids=None -> all currently-eligible lines (respecting invoice_on policy).
    Honors allow_partial_invoicing; rejects lines not ELIGIBLE or already INVOICED.
    Idempotent on (organization_id, idempotency_key).
    """

def issue_invoice(*, organization_id, actor_id, invoice_id) -> Invoice:
    """
    cap: invoicing.issue; Required state: DRAFT
    Sets issue/due dates, marks lines INVOICED, enqueues invoice.send (PDF + email),
    makes the invoice immutable, recomputes order status.
    """

def void_draft_invoice(...) / void_issued_invoice(...): ...   # see 12.4
def update_invoice_draft(...): ...   # cap: invoicing.edit; DRAFT only (notes/footer/line subset)
```

**Generation rules.** Eligible-line selection respects `InvoicingPolicy.invoice_on`: under `ORDER_FULLY_FULFILLED`, `create_invoice` refuses until all invoiceable lines are eligible. Bundle lines bill from their **children**: a bundle parent line is `NOT_APPLICABLE` for fulfillment (Section 11.2.3), so its child lines become individually eligible and bill as ordinary lines; the invoice presents them grouped under the parent for readability but each child carries its own snapshot. Document totals are the rounded sum of line values per Section 10.3.5 (`HALF_EVEN`); billing never re-derives unit prices.

### 12.6 Tax Roll-Up

**Status: NORMATIVE.**

Each `InvoiceLine.tax_amount` is copied from the line's `PricingSnapshot` (computed by `modifier.tax`, Section 10.12) — billing does **not** recompute tax. The invoice `tax_amount` is the sum of line tax amounts; `subtotal_amount`, `discount_amount`, and `total_amount` are the corresponding line sums. A line with `taxable = false`, or a client with `tax_exempt = true` at pricing time, contributed zero line tax and therefore zero to the invoice tax. Because tax was frozen into the snapshot at quote time, an invoice reproduces the tax the customer was quoted, even if jurisdiction rates have since changed — consistent with commercial immutability. Multi-jurisdiction compound tax beyond the single per-line rate is post-MVP (Section 10.12, Section 22).

### 12.7 Payments

**Status: NORMATIVE.**

Payments are tenant business records — money a tenant's customer pays the tenant. They are **append-only**.

```text
Payment
  id: UUID, pk
  organization_id: fk -> Organization on_delete=PROTECT
  client_id: fk -> Client
  number: TEXT                                             -- "PMT-2026-00042"
  method: ENUM(CASH, CHECK, BANK_TRANSFER, CARD_OFFLINE, OTHER)
  amount: NUMERIC(14,2)
  currency_code: CHAR(3)
  received_at: DATE
  reference: TEXT, null                                    -- check no., transfer ref
  notes: TEXT, null
  status: ENUM(RECORDED, PARTIALLY_ALLOCATED, ALLOCATED, REVERSED)
  recorded_by_id, recorded_at
  reversed_at, reversed_by_id, reversed_reason
  index (organization_id, client_id)
  index (organization_id, status)

PaymentAllocation                                          -- append-only; links payment to invoice
  id: UUID, pk
  organization_id: fk
  payment_id: fk -> Payment
  invoice_id: fk -> Invoice
  allocated_amount: NUMERIC(14,2)
  allocated_at: TIMESTAMPTZ
  allocated_by_id: fk -> User
  reversal_of_id: fk -> PaymentAllocation, null            -- a reversal is a NEW negative row
  CHECK: allocated_amount <> 0

PaymentAdjustment                                          -- append-only correction to a payment
  id: UUID, pk
  organization_id, payment_id: fk
  adjustment_type: ENUM(CORRECTION, REVERSAL)
  amount: NUMERIC(14,2)                                    -- signed
  reason: TEXT
  adjusted_by_id, adjusted_at
```

**Payment methods are offline only.** The MVP records payments the tenant received through its own channels (cash, check, bank transfer, an offline card terminal). There is **no payment-processor integration** — MyPipelineHero does not charge the tenant's customers' cards. (This is distinct from, and additional to, the absence of a processor for SaaS subscription billing, Section 7.14.) Online customer payment collection is post-MVP (Section 22).

### 12.8 Payment Recording and Allocation

**Status: NORMATIVE.**

```python
def record_payment(*, organization_id, actor_id, client_id, method, amount,
                   received_at, reference=None, notes=None,
                   allocations=(), idempotency_key) -> Payment:
    """
    cap: payments.record; sensitive (re-auth, Section 8.12); entitlement: basic_invoicing
    Records a payment and optionally allocates it across invoices in one transaction.
    Idempotent on (organization_id, idempotency_key).
    """

def allocate_payment(*, organization_id, actor_id, payment_id,
                     invoice_id, allocated_amount) -> PaymentAllocation:
    """ cap: payments.allocate. Appends an allocation; recomputes invoice + order. """

def reverse_payment_allocation(*, organization_id, actor_id, payment_allocation_id,
                               reason) -> PaymentAllocation:
    """ cap: payments.reverse; sensitive. Writes a NEW negative allocation (reversal_of set). """

def reverse_payment(*, organization_id, actor_id, payment_id, reason) -> Payment:
    """ cap: payments.reverse; sensitive. Reverses all allocations, sets status REVERSED. """
```

**Allocation rules.** The sum of a payment's active allocations MUST NOT exceed its `amount` (over-allocation raises `PaymentOverAllocationError`); the sum of an invoice's active allocations MUST NOT exceed its `amount_due` (over-payment of an invoice raises `InvoiceOverPaymentError`). Both sums treat reversal rows as negative, so a reversed-and-reallocated payment nets correctly. After every allocation or reversal, the system recomputes the invoice's derived `amount_paid`/`amount_due` and status, then `recompute_sales_order_status` (Section 9.5.5) — an order closes only when all its invoices are PAID.

**Reversal is append-only.** A correction never edits an allocation in place; it writes a new `PaymentAllocation` with a negated `allocated_amount` and `reversal_of_id` set, leaving the original intact for audit. This is the same immutability discipline as pricing snapshots and build-labor entries.

### 12.9 Accounting Adapter Boundary

**Status: NORMATIVE.**

Billing exposes an accounting-sync boundary so commercial events can be pushed to an external ledger — but the MVP ships **only the interface and a Noop adapter** (Section 3.3). No concrete QuickBooks/Xero/NetSuite adapter is built.

```python
class AccountingAdapter(Protocol):
    code: str
    def sync_invoice_issued(self, *, payload: AccountingInvoicePayload) -> None: ...
    def sync_payment_recorded(self, *, payload: AccountingPaymentPayload) -> None: ...
    def sync_invoice_voided(self, *, payload: AccountingVoidPayload) -> None: ...

class NoopAccountingAdapter:
    code = "noop"
    # records the call as handled; performs no external I/O
```

Sync is **outbox-driven** (Section 4.7): issuing an invoice, recording a payment, or voiding an invoice inserts an outbox entry (`accounting.sync_invoice_issued`, etc.) in the same transaction as the commercial mutation; a worker invokes the org's configured adapter idempotently. `Organization.accounting_adapter_code` defaults to `"noop"` and `accounting_adapter_config` is field-encrypted at rest (Section 5.2, Section 17). Because sync goes through the outbox, adding a concrete adapter post-MVP requires no change to the billing service layer — only a new adapter registration.

### 12.10 SaaS Billing Separation (Restated Boundary)

**Status: NORMATIVE.**

This section's `Invoice`/`Payment`/`PaymentAllocation` records are **tenant->customer** business records. They are categorically separate from the platform's SaaS subscription billing (`Subscription`, `OrganizationAddOnSubscription`, Section 7):

- They share no models, tables, sequences, or numbering series (tenant invoices are `INV-*`; there is no SaaS-invoice entity in the MVP at all).
- A tenant's `InvoicingPolicy`, payment terms, and tax never apply to what MyPipelineHero charges the tenant.
- The accounting adapter syncs **tenant** commercial events to the **tenant's** ledger; it has no relationship to platform revenue.

A reviewer MUST be able to confirm by inspection that no foreign key crosses between the subscription domain and the billing domain (Section 7.16 criterion 21).

### 12.11 Reporting

**Status: NORMATIVE.**

The MVP ships exactly **ten fixed reports** (`standard_reports`, universal) plus **async CSV export** (`ReportExportJob`). Advanced/margin reports are gated by `advanced_reporting` (Growth-Limited, Pro+). There is no ad hoc report builder, no scheduled delivery, no BI export, and no dashboard KPI engine in the MVP (Section 22).

| # | Report | Feature | Notes |
|---|---|---|---|
| 1 | Open invoices / AR aging | `standard_reports` | by client, by due bucket |
| 2 | Payments received | `standard_reports` | by period, by method |
| 3 | Sales orders by status | `standard_reports` | pipeline of fulfillment |
| 4 | Quote conversion | `standard_reports` | sent -> accepted rates |
| 5 | Work orders by status / assignee | `standard_reports` | operational load |
| 6 | Purchase orders outstanding | `standard_reports` | by supplier |
| 7 | Lead pipeline | `standard_reports` | by source, by status |
| 8 | Invoiced vs. fulfilled | `standard_reports` | billing completeness |
| 9 | Revenue by location/region | `standard_reports` | RML roll-up |
| 10 | Tax collected by jurisdiction | `standard_reports` | period tax summary |
| — | Margin by line/order/product | `advanced_reporting` | uses snapshot cost vs. price |
| — | Build cost variance summary | `advanced_reporting` + `build_cost_variance` | actual vs. estimated |

```text
ReportExportJob
  id: UUID, pk
  organization_id: fk
  report_code: TEXT
  parameters: JSONB
  status: ENUM(QUEUED, RUNNING, COMPLETED, FAILED)
  requested_by_id, requested_at
  completed_at: TIMESTAMPTZ, null
  output_document_id: fk -> DocumentAttachment, null       -- the generated CSV (Section 13)
  error_detail: TEXT, null
```

CSV export runs on the `reports` queue (Section 4.4), writes to object storage as a `DocumentAttachment`, and respects RML scope: a scoped membership exports only data within its location closure. Advanced reports apply `require_feature(advanced_reporting)` at request time and render the upgrade prompt (Section 7.12) on denial.

### 12.12 RBAC Enforcement (Billing)

**Status: NORMATIVE.**

| View / Action | Queryset | Capability | Object check | Audit |
|---|---|---|---|---|
| Invoice list / detail | `for_membership(m)` | `invoicing.view` | — | — |
| Create draft invoice | `for_membership(m)` | `invoicing.create` | lines ELIGIBLE, same order/client | `INVOICE_CREATED` |
| Edit draft | `for_membership(m)` | `invoicing.edit` | DRAFT | `INVOICE_UPDATED` |
| Issue invoice | `for_membership(m)` | `invoicing.issue` | DRAFT | `INVOICE_ISSUED` |
| Void invoice | `for_membership(m)` | `invoicing.void`; sensitive | reason; issued->manager | `INVOICE_VOIDED` |
| Record payment | `for_membership(m)` | `payments.record`; sensitive | client in org+scope | `PAYMENT_RECORDED` |
| Allocate payment | `for_membership(m)` | `payments.allocate` | invoice in org+scope; not over-allocated | `PAYMENT_ALLOCATED` |
| Reverse payment / allocation | `for_membership(m)` | `payments.reverse`; sensitive | reason required | `PAYMENT_REVERSED` / `_ALLOCATION_REVERSED` |
| Run standard report / export | `for_membership(m)` | `reports.view` | RML scope | `REPORT_EXPORTED` |
| Run advanced report | `for_membership(m)` | `reports.advanced` | ent. `advanced_reporting` | `REPORT_EXPORTED` |

**Entitlement gates:** invoicing and payments require `basic_invoicing` (universal); standard reports require `standard_reports` (universal); advanced reports require `advanced_reporting`. Recording a payment, reversing a payment/allocation, and voiding an issued invoice are **sensitive actions** (Auth0 `max_age` re-prompt, Section 8.12).

### 12.13 Billing Audit Events

**Status: NORMATIVE.**

```text
INVOICE_CREATED  INVOICE_UPDATED  INVOICE_ISSUED  INVOICE_VOIDED
PAYMENT_RECORDED  PAYMENT_ALLOCATED  PAYMENT_ALLOCATION_REVERSED  PAYMENT_REVERSED
INVOICE_MARKED_PAID  INVOICE_MARKED_PARTIALLY_PAID
ACCOUNTING_SYNC_DISPATCHED  ACCOUNTING_SYNC_FAILED
REPORT_EXPORTED
```

Issue, void, payment, allocation, and reversal events are append-only audit records carrying the actor and (under impersonation) the on-behalf-of user. Money-affecting events are retained per the financial retention policy (Section 17), which is longer than the default operational retention.

### 12.14 State-Machine Property Tests

**Status: NORMATIVE.**

For Invoice and Payment, a Hypothesis property test asserts the Section 9.9 invariants plus billing-specific ones: invoice `amount_due` always equals `total_amount - sum(active allocations) + sum(adjustments)`; the sum of active allocations never exceeds a payment's `amount` or an invoice's `amount_due`; reversal rows always net against their originals; a sales-order line is INVOICED on at most one non-void invoice at a time; and `recompute_sales_order_status` closes an order only when all its invoices are PAID. Issued/Paid invoices reject all commercial-value mutations.

### 12.15 Acceptance Criteria

**Status: NORMATIVE.**

| # | Criterion | Verification |
|---|---|---|
| 1 | `InvoicingPolicy` exists per org, created in the org-creation transaction | service test |
| 2 | `create_invoice` bills only ELIGIBLE lines; rejects INVOICED or non-eligible lines | service test |
| 3 | `invoice_on = ORDER_FULLY_FULFILLED` refuses partial invoicing until all lines eligible | service test |
| 4 | An InvoiceLine references the same PricingSnapshot as its SalesOrderLine (no re-pricing) | service test |
| 5 | Invoice totals are the HALF_EVEN line sums (Section 10.3.5); billing computes no unit prices | unit test |
| 6 | Invoice tax = sum line snapshot tax; `taxable=false`/`tax_exempt` contribute zero | service test |
| 7 | A sales-order line is billed at most once across all non-void invoices (unique + INVOICED flag) | DB + service test |
| 8 | Issue sets dates, marks lines INVOICED, enqueues `invoice.send`, makes invoice immutable | service test |
| 9 | Invoice lifecycle matches 12.4; property test passes | property test |
| 10 | Issued/Paid invoice rejects commercial-value edits | service test |
| 11 | Void (draft) releases lines to ELIGIBLE; void (issued) reverses allocations + releases lines | service test |
| 12 | `record_payment` is sensitive (re-auth) and idempotent on `(org, idempotency_key)` | integration test |
| 13 | Over-allocating a payment raises `PaymentOverAllocationError` | service test |
| 14 | Over-paying an invoice raises `InvoiceOverPaymentError` | service test |
| 15 | Reversal writes a new negative allocation (`reversal_of` set); original is never edited | service test |
| 16 | Invoice `amount_due` invariant holds after every allocation/reversal | property test |
| 17 | Order closes only when all its invoices are PAID (`recompute_sales_order_status`) | service test |
| 18 | Accounting sync is outbox-driven; Noop adapter records the call with no external I/O | service test |
| 19 | `accounting_adapter_config` is field-encrypted at rest | security test |
| 20 | No FK crosses between the subscription domain and the billing domain | architecture review |
| 21 | Exactly ten standard reports; advanced reports gated by `advanced_reporting` (upgrade prompt on deny) | registry + service test |
| 22 | CSV export runs on the `reports` queue, writes a DocumentAttachment, respects RML scope | integration test |
| 23 | Payment methods are offline only; no payment-processor code path exists | architecture review |
| 24 | Money-affecting events use financial retention; carry actor + on-behalf-of | integration test |
| 25 | Capability-coverage CI test passes for all billing routes | CI |

---

## Section 13 — Admin and Workflow Surfaces

### 13.1 Scope and the Three Admin Surfaces

**Status: NORMATIVE.**

Section 13 specifies the administrative and supporting surfaces that sit alongside the commercial domain: the **platform console** (operator/support), the **custom tenant admin** (tenant self-administration), the **dev-only Django admin** (raw inspection), the **Import Center** (guided CSV import/migration), **document attachments** (the cross-domain file model), and the **tenant dashboard**.

There are exactly three administrative surfaces, with strictly separated audiences and trust levels:

| Surface | Audience | Host | Trust model |
|---|---|---|---|
| Platform console | Support users (`is_staff`) | root domain `/platform/` | Cross-tenant, every access audited (Section 5.6) |
| Custom tenant admin | Tenant Owners/Org Admins | tenant subdomain `/admin/` | Single-tenant, RBAC + entitlement gated |
| Django admin | Engineers, **dev/test only** | dev host `/django-admin/` | Raw DB inspection; disabled in staging/prod |

The base Django admin **MUST NOT** be the production platform console (Section 5.6). The platform console and custom tenant admin are purpose-built Django template surfaces that call the same service layer as everything else; neither bypasses tenancy, RBAC, or entitlement enforcement.

### 13.2 Platform Console

**Status: NORMATIVE.** Audience: Support users (`is_staff=True`, Section 8.5). Host: `https://mypipelinehero.com/platform/`.

#### 13.2.1 Purpose and Access

The platform console is the operator surface for managing tenants across the platform. It is the **only** sanctioned cross-tenant query path besides migrations (Section 5.6): every cross-tenant read goes through explicit platform query services or `Model.objects.platform_admin_queryset()` and emits a `PLATFORM_ADMIN_QUERY` audit event. Access requires `is_staff`; a non-staff user reaching `/platform/` receives the "no active access" response (Section 8.6 branch 8a).

#### 13.2.2 Capabilities

The console exposes these operator workflows, each tied to a platform-level capability (distinct from tenant capabilities, prefixed `platform.`):

| Workflow | Capability | Reference |
|---|---|---|
| Create tenant (org + subscription) | `platform.tenants.create` | Section 6.3 |
| Invite tenant owner | `platform.tenants.invite_owner` | Section 6.4 |
| View tenant overview / search tenants | `platform.tenants.view` | — |
| Set / change tenant plan | `platform.subscriptions.manage`; sensitive | Section 7.13 |
| Enable / disable add-on packs | `platform.subscriptions.manage` | Section 7.13 |
| Set / clear entitlement overrides | `platform.entitlements.override`; sensitive | Section 7.7, 7.13 |
| Adjust subscription limit ceilings | `platform.subscriptions.manage` | Section 7.6 |
| Suspend / reinstate organization | `platform.tenants.suspend`; sensitive | Section 5.2 |
| Force `org_setup_complete` reset | `platform.tenants.support` | Section 6.7 |
| Start tenant impersonation | `platform.impersonation.start`; sensitive | Section 8.15 |
| View audit / impersonation logs | `platform.audit.view` | Section 17 |

Plan changes, override edits, suspension, and impersonation start are **sensitive actions** (Auth0 `max_age` re-prompt, Section 8.12). Platform capabilities are held by support users directly (not via tenant memberships) and are seeded; tenants can never acquire them.

#### 13.2.3 Tenant Overview

For a selected tenant the console shows: organization status and slug, the `Subscription` (plan, status, limits, current usage against each `max_*`), active add-ons, active overrides (with reason and grantor), membership roster and statuses, recent audit events, and any blocked-fulfillment lines (Section 11.2.4). Usage-vs-limit display reads live counts (active users, active locations, active price lists, etc.) so an operator can see when a tenant is at a ceiling before changing a plan.

#### 13.2.4 Console Constraints

The console never edits tenant commercial records (quotes, orders, invoices, payments). Operators administer **tenancy and entitlement**, not a tenant's business data; to touch business data they must impersonate (Section 8.15), which routes through the tenant's own RBAC and is fully audited. This separation keeps "operator changed a tenant's invoice" impossible without an impersonation trail.

### 13.3 Custom Tenant Admin

**Status: NORMATIVE.** Audience: tenant Owners / Org Admins. Host: `https://{slug}.mypipelinehero.com/admin/`.

#### 13.3.1 Purpose

The custom tenant admin is where a tenant administers itself: members, roles, operating scope, locations, catalog configuration, numbering, invoicing policy, tax setup, and a read-only view of its own subscription. It is a tenant-subdomain surface, fully inside the tenant-local session, RBAC-gated by `admin.*` capabilities and entitlement-gated per feature.

#### 13.3.2 Sections of the Tenant Admin

| Admin area | Capability | Entitlement | Notes |
|---|---|---|---|
| Members & invitations | `admin.members.manage` | universal | Invite/suspend/reactivate; respects `max_users` (Section 8.4) |
| Roles & capability grants | `admin.roles.manage`; sensitive | universal | Compose custom roles from existing capabilities; no new codes (Section 8.13) |
| Operating scope (RML) | `admin.scope.manage` | `rml_scope` | Region/Market/Location tree + scope assignments (Section 8.14) |
| Locations | `admin.locations.manage` | `multi_location` beyond first | Respects `max_locations` (Section 6.6) |
| Catalog configuration | `catalog.manage` | per item type | Services/products/raw materials/suppliers (Section 10.2) |
| Pricing configuration | `pricing.rules.manage` etc. | per input | Price lists, contracts, segments, labor cards, promotions, rules (Section 10.11) |
| Tax setup | `admin.tax.manage` | `tax_rates` | Jurisdictions + rates (Section 10.12) |
| Numbering | `admin.numbering.manage` | universal | Entity prefixes (Section 5.8) |
| Invoicing policy | `admin.invoicing.manage` | `basic_invoicing` | Terms, rhythm, footer (Section 12.2) |
| Subscription (read-only) | `admin.subscription.view` | universal | Plan, limits, usage, add-ons; **no self-service change** (Section 7.13) |
| Import Center | `admin.import.manage` | `import_center` | Section 13.5 |

#### 13.3.3 Subscription Is Read-Only Here

The tenant admin's subscription page **displays** plan, limits, usage, and add-ons but offers **no** self-service plan change, add-on purchase, or upgrade button — there is no payment processor in the MVP (Section 7.13). Where a tenant hits a feature gate or limit, the upgrade prompt (Section 7.12) routes to "contact your administrator / contact support," not a checkout. Changing a plan is an operator action in the platform console.

#### 13.3.4 Role and Capability Editing

Composing roles is a **sensitive action** (`admin.roles.manage`, Section 8.12) because it changes who can do what. The editor presents the platform capability registry grouped by domain; a tenant assembles org-scoped roles from existing capabilities and may apply per-membership GRANT/DENY overrides (DENY beats GRANT, Section 8.13). Tenants cannot mint new capability codes in the MVP. Every role/grant change emits `ROLE_*` / `CAPABILITY_GRANT_APPLIED` audit events.

### 13.4 Dev-Only Django Admin

**Status: NORMATIVE.**

The stock Django admin is mounted **only** in `dev` and `test` settings, at `/django-admin/`, for engineer inspection and fixture manipulation during development. It is **disabled** in `staging`, `demo`, and `prod` (not in `urls.py`, blocked at the proxy as defense in depth). It is never the platform console (Section 5.6) and is never tenant-facing.

Because the Django admin bypasses the service layer, using it to mutate data in any shared environment is prohibited; in dev it is acceptable for setup and inspection only. A CI/settings check asserts the admin is absent from non-dev URL configurations.

### 13.5 Import Center

**Status: NORMATIVE.** Entitlement: `import_center` (Starter-Limited, Growth+ full; Import Plus add-on raises ceilings and unlocks saved mappings). Limit: `max_import_rows_per_batch`.

#### 13.5.1 Purpose and Posture

The Import Center is guided CSV import for onboarding and migration: locations, members, clients, leads, catalog items, suppliers, supplier costs, and (Pro+) BOM data. Its defining rule (Section 6.8) is that **imports write through the domain service layer** — a client import calls `create_client`, a location import calls `create_location` — so every entitlement gate, plan limit, RML check, and audit event applies identically whether a record is created by hand or by import. The Import Center is a batch front end onto the same services, never a backdoor around them.

#### 13.5.2 Models

```text
ImportProject                                            -- groups batches for one migration effort
  id: UUID, pk
  organization_id: fk -> Organization on_delete=PROTECT
  name: TEXT
  status: ENUM(OPEN, COMPLETED, ARCHIVED)
  created_by_id, created_at
  index (organization_id, status)

ImportBatch                                              -- one CSV upload for one target entity
  id: UUID, pk
  organization_id, import_project_id: fk
  target_entity: ENUM(LOCATIONS, MEMBERS, CLIENTS, LEADS, SERVICES, PRODUCTS,
                      RAW_MATERIALS, SUPPLIERS, SUPPLIER_COSTS, BOM_LINES)
  source_filename: TEXT
  source_document_id: fk -> DocumentAttachment           -- the uploaded CSV (Section 13.6)
  row_count: INT
  status: ENUM(UPLOADED, MAPPED, VALIDATED, COMMITTING, COMMITTED, FAILED, CANCELLED)
  mapping_template_id: fk -> ImportMappingTemplate, null  -- Import Plus
  validated_at, committed_at: TIMESTAMPTZ, null
  committed_row_count, failed_row_count: INT, default(0)
  created_by_id, created_at
  index (organization_id, status)

ImportColumnMapping                                      -- per-batch column -> field mapping
  id, organization_id, import_batch_id: fk
  source_column: TEXT
  target_field: TEXT
  transform: TEXT, null                                  -- e.g. "trim", "uppercase", "date:MDY"

ImportMappingTemplate                                    -- Import Plus: reusable saved mapping
  id, organization_id: fk
  target_entity: TEXT
  name: TEXT
  mapping_json: JSONB
  created_by_id, created_at

ImportRowIssue                                           -- per-row validation/commit issue
  id: BIGINT, pk (BIGSERIAL)
  organization_id, import_batch_id: fk
  row_number: INT
  severity: ENUM(WARNING, ERROR)
  issue_code: TEXT                                       -- e.g. "feature_not_entitled",
                                                         --      "plan_limit_exceeded",
                                                         --      "validation_failed", "duplicate"
  field: TEXT, null
  detail: TEXT
  index (organization_id, import_batch_id, severity)
```

These models follow the import-extension design from the database model package, adapted to the entitlement model: `issue_code` includes `feature_not_entitled` and `plan_limit_exceeded` so gate/limit failures surface as ordinary row issues.

#### 13.5.3 Import Workflow

```text
1. UPLOADED   -- operator uploads a CSV; stored as a DocumentAttachment; row_count computed;
                rejected immediately if row_count > max_import_rows_per_batch
                (PlanLimitExceededError surfaced before any row work)
2. MAPPED     -- operator maps source columns -> target fields (or applies a saved template,
                Import Plus); unmapped required fields block advancement
3. VALIDATED  -- DRY RUN: every row is run through the target service in a rolled-back
                transaction; failures recorded as ImportRowIssue (ERROR/WARNING); no commits
4. COMMITTING -- operator confirms; rows are committed through the domain services on the
                `bulk` queue (Section 4.4); each row is independent
5. COMMITTED  -- terminal; committed_row_count / failed_row_count finalized
   FAILED     -- batch-level failure (bad file, etc.)
   CANCELLED  -- operator abandons before commit
```

#### 13.5.4 Row-Level Semantics (No Partial-Commit Surprises)

Per Section 6.8, imports report problems as **per-row issues, not silent partial commits**. Concretely:

- **Dry-run first.** VALIDATED runs every row through its real service inside a rolled-back transaction, so entitlement gates, plan limits, RML checks, and validation all fire exactly as they would on commit — but nothing persists. The operator sees the full issue list before committing.
- **Batch-wide gate failure is surfaced at validation.** If the target entity's feature is not entitled (e.g., a Starter tenant importing `SUPPLIER_COSTS` without `supplier_costs`), every row reports `feature_not_entitled` at VALIDATED and the batch cannot advance to COMMITTING. The operator resolves it by having the plan/add-on enabled (platform console), then re-validates.
- **Limit-aware commit.** Where a plan limit applies (e.g., `max_locations`), commit processes rows in order and rows that would exceed the ceiling record `plan_limit_exceeded` and are skipped; prior rows already committed are valid and retained. This is the one place "partial" occurs, and it is explicit, per-row, and reported — never silent.
- **Idempotent commit.** Each row commit carries a deterministic idempotency key (`batch_id` + `row_number`) so a redelivered `bulk`-queue task does not double-create (Section 4.5, Section 16).

#### 13.5.5 Import RBAC and Audit

| Action | Capability | Entitlement |
|---|---|---|
| View / create project & batch | `admin.import.view` / `admin.import.manage` | `import_center` |
| Upload CSV | `admin.import.manage` | `import_center` (+ `max_import_rows_per_batch`) |
| Map columns / save template | `admin.import.manage` | `import_center` (templates: Import Plus) |
| Validate (dry run) | `admin.import.manage` | `import_center` |
| Commit | `admin.import.commit`; sensitive | `import_center` |

Commit is a **sensitive action** (it can create many records at once). Events: `IMPORT_BATCH_UPLOADED`, `IMPORT_BATCH_VALIDATED`, `IMPORT_BATCH_COMMITTED`, `IMPORT_BATCH_FAILED`. Because rows commit through domain services, each created record **also** emits its own domain audit event (`CLIENT_CREATED`, etc.), so an import produces both batch-level and record-level audit trails.

### 13.6 Document Attachments

**Status: NORMATIVE.**

`DocumentAttachment` is the single cross-domain file model. It backs quote/invoice PDFs, work-order completion photos (Section 11.3.1), report exports (Section 12.11), import source files (Section 13.5.2), and general attachments to commercial records.

#### 13.6.1 Models

```text
DocumentAttachment
  id: UUID, pk
  organization_id: fk -> Organization on_delete=PROTECT
  kind: ENUM(UPLOAD, GENERATED_PDF, GENERATED_CSV, COMPLETION_PHOTO, IMPORT_SOURCE)
  filename: TEXT
  content_type: TEXT
  byte_size: BIGINT
  storage_key: TEXT                                      -- {env}/orgs/{org_id}/{domain}/{id}/{file}
  checksum_sha256: TEXT
  uploaded_by_id: fk -> User, null                       -- null for system-generated
  retention_class: ENUM(COMMERCIAL, OPERATIONAL, TRANSIENT)
  delete_after: DATE, null                               -- set per retention class (Section 17)
  created_at: TIMESTAMPTZ
  index (organization_id, kind)

DocumentAttachmentLink                                   -- typed link table; no GenericForeignKey
  id, organization_id, document_attachment_id: fk
  lead_id, quote_version_id, client_id, sales_order_id, work_order_id,
  build_order_id, purchase_order_id, invoice_id, import_batch_id: UUID, fk, null
  CHECK (num_nonnulls(...) = 1)
```

`DocumentAttachmentLink` follows the typed-link invariant (Section 9.8): exactly one non-null FK, enforced at the database, service, and form layers — never `GenericForeignKey`.

#### 13.6.2 Storage and Tenancy

Files live in S3-compatible object storage (MinIO in dev) under the org-scoped key `{environment}/orgs/{org_id}/{domain}/{record_id}/{filename}` (Section 4.4). Every download re-checks tenancy and RML scope on the linked record before issuing a time-limited signed URL; a storage key is never exposed directly. File-size and content-type limits are enforced at upload; storage usage counts against `Subscription.file_storage_bytes` (Section 7.6) where that limit is set.

#### 13.6.3 Retention

`retention_class` drives `delete_after`: COMMERCIAL documents (invoice/quote PDFs) follow the financial retention policy; OPERATIONAL (completion photos) follow operational retention; TRANSIENT (report CSVs) are short-lived and pruned by a beat job (Section 17, Section 18). Tenant deletion removes a tenant's document objects as part of the cascade, except where a document is referenced by a retained audit record (Section 5.9, Section 17).

#### 13.6.4 Document RBAC

| Action | Capability | Object check |
|---|---|---|
| Upload attachment | `documents.upload` | linked record in org+scope |
| View / download | `documents.view` | linked record in org+scope; tenancy re-checked at download |
| Delete attachment | `documents.delete` | not under a retention hold |

Generated documents (PDFs, CSVs) are produced by outbox workers attributed to the System User (Section 4.7).

### 13.7 Tenant Dashboard

**Status: INFORMATIVE (layout) / NORMATIVE (gating).**

The tenant dashboard at `https://{slug}.mypipelinehero.com/dashboard` is the post-login landing surface. Its current styling is the temporary `mph-dashboard-*` system (to be reconciled with the full design system in Section 14); the layout here is INFORMATIVE, but the **content gating is NORMATIVE**.

The dashboard composes widgets, each of which renders only when its capability **and** entitlement allow — using the `has_feature` template tag for convenience hiding, never as the security boundary (Section 7.9):

| Widget | Shows | Gate |
|---|---|---|
| Pipeline summary | Open leads, quotes by status | `leads.view` / `quotes.view` |
| Fulfillment queue | Open work/build/purchase orders | the artifact's view cap + entitlement |
| AR snapshot | Open invoices, overdue, recently paid | `invoicing.view` |
| Tasks due | The member's open/overdue tasks | `tasks.view` |
| Onboarding callouts | "Create your first lead / catalog item" | shown until the org has >=1 lead and >=1 catalog item (Section 6.6) |
| Blocked fulfillment | Lines in `BLOCKED_ENTITLEMENT` | shown to admins when present (Section 11.2.4) |

A scoped membership (RML) sees only data within its location closure (Section 8.14). Widgets a tenant's plan doesn't include are simply absent — the dashboard never shows an upgrade ad in place of a widget; upgrade prompts appear only when a user actively attempts a gated action (Section 7.12). The dashboard reads through normal queryset scoping and triggers no privileged queries.

### 13.8 RBAC Enforcement Summary (Admin Surfaces)

**Status: NORMATIVE.**

| Surface | Auth | Cross-tenant? | Service layer? | Audited |
|---|---|---|---|---|
| Platform console | `is_staff` + `platform.*` caps | Yes (sole sanctioned path) | Yes | Every cross-tenant query (`PLATFORM_ADMIN_QUERY`) + each action |
| Custom tenant admin | tenant session + `admin.*` caps | No | Yes | Each admin action |
| Django admin | superuser, dev/test only | n/a (dev data) | No (bypasses) | n/a |
| Import Center | tenant session + `admin.import.*` | No | Yes (writes through domain services) | Batch + per-record events |
| Documents | tenant session + `documents.*` | No | Yes | Upload/delete events |
| Dashboard | tenant session | No | Yes (read-only) | n/a (reads) |

### 13.9 Acceptance Criteria

**Status: NORMATIVE.**

| # | Criterion | Verification |
|---|---|---|
| 1 | Platform console requires `is_staff`; non-staff get "no active access" | integration test |
| 2 | Every platform-console cross-tenant query emits `PLATFORM_ADMIN_QUERY` | integration test |
| 3 | Plan change, override edit, suspension, and impersonation start are sensitive (re-auth) | integration test |
| 4 | Platform console cannot edit tenant commercial records (only via impersonation) | architecture + service test |
| 5 | Tenant overview shows live usage vs. each plan limit | view test |
| 6 | Custom tenant admin subscription page is read-only; no self-service plan change | view test |
| 7 | Role/capability editing is sensitive and emits role/grant audit events | integration test |
| 8 | Tenants cannot mint new capability codes | service test |
| 9 | Django admin is mounted only in dev/test; absent from staging/demo/prod URLConf | settings/CI test |
| 10 | Import upload rejects a file exceeding `max_import_rows_per_batch` before row work | service test |
| 11 | Import VALIDATED dry-run runs rows through real services in a rolled-back transaction | service test |
| 12 | A batch whose entity feature is unentitled reports `feature_not_entitled` per row at validation; cannot commit | service test |
| 13 | Commit skips limit-exceeding rows with `plan_limit_exceeded`; prior committed rows retained | service test |
| 14 | Each import row commits through its domain service and emits the domain audit event | integration test |
| 15 | Import row commit is idempotent on `(batch_id, row_number)` | service test |
| 16 | Saved mapping templates require the Import Plus add-on | service test |
| 17 | Import commit is a sensitive action | integration test |
| 18 | `DocumentAttachmentLink` enforces exactly-one-non-null at DB/service/form | DB + service test |
| 19 | Document storage keys are org-scoped; downloads re-check tenancy + RML and issue signed URLs | integration test |
| 20 | Document `retention_class` sets `delete_after`; the prune job respects it | service test |
| 21 | Dashboard widgets render only when capability + entitlement allow; scoped members see scoped data | view test |
| 22 | Dashboard onboarding callouts disappear once >=1 lead and >=1 catalog item exist | view test |
| 23 | No admin surface bypasses tenancy, RBAC, or entitlement except the dev-only Django admin | architecture review |
| 24 | Capability-coverage CI test passes for all admin/import/document routes | CI |

---

## Section 14 — Branding and UI Design System

### 14.1 Scope and Source of Truth

**Status: NORMATIVE.**

Section 14 specifies the MyPipelineHero design system: the brand token set, the `mph-*` class conventions, typography, spacing, components, accessibility requirements, and the rules that keep every server-rendered surface visually coherent and ready for the post-MVP React overlay.

**The shipped brand CSS is the source of truth.** Three stylesheets define the authoritative visual language; where this section states a value, it restates the CSS, and where the two ever diverge the CSS wins and this section is corrected by PR:

| Stylesheet | Owns | Namespace |
|---|---|---|
| `homepage.css` | The `:root` design tokens + public landing + auth pages + the shared app topbar | `mph-*` |
| `dashboard.css` | The temporary tenant dashboard placeholder (Milestone 1) | `mph-dashboard-*` |
| `platform_console.css` | The platform console chrome + the impersonation banner | `mph-pc-*`, `mph-imp-*` |

`homepage.css` is the token home: its `:root` block is where every `--mph-*` custom property is defined, and the other two stylesheets consume those tokens. The brand primary is teal `#0f766e` (`--mph-primary`); the blue palette in the earlier `guide.md` H.2 draft was an error and is discarded (Locked Decision #3).

### 14.2 Brand Foundations and Palette

**Status: NORMATIVE.** All values below are the literal definitions in `homepage.css :root`.

**Core brand + sidebar:**

| Token | Value | Role |
|---|---|---|
| `--mph-primary` | `#0f766e` | Brand primary (teal) |
| `--mph-primary-dark` | `#115e59` | Primary pressed / on-light text |
| `--mph-primary-hover` | `#115e59` | Primary hover (same as dark) |
| `--mph-primary-soft` | `#ccfbf1` | Primary tint (badge/pill backgrounds) |
| `--mph-primary-muted` | `#5eead4` | Primary accent |
| `--mph-sidebar` | `#343a40` | Dark chrome / brandmark text |
| `--mph-sidebar-hover` | `#495057` | Sidebar hover |
| `--mph-sidebar-muted` | `#adb5bd` | Sidebar muted |

**App neutrals:**

| Token | Value | Role |
|---|---|---|
| `--mph-shell` | `#f4f6f9` | App background |
| `--mph-surface` | `#ffffff` | Card/panel surface |
| `--mph-border` | `#dee2e6` | Hairline border |
| `--mph-text` | `#212529` | Body text |
| `--mph-muted` | `#6c757d` | Secondary text |
| `--mph-white` | `#ffffff` | On-dark / on-primary text |

**Public landing palette (dark surfaces):** `--mph-landing-bg #020617`, `--mph-landing-panel rgba(255,255,255,0.05)`, `--mph-landing-panel-strong rgba(255,255,255,0.10)`, `--mph-landing-border rgba(255,255,255,0.10)`, `--mph-landing-copy #cbd5e1`, `--mph-landing-faint #94a3b8`, plus a slate ramp `--mph-slate-200 #e2e8f0` → `--mph-slate-950 #020617`.

**Status colors (currently platform-console-local, `--mph-pc-*`):** amber `#d97706`/soft `#fef3c7`/dark `#92400e`; danger `#dc2626`/soft `#fee2e2`/dark `#991b1b`; blue `#2563eb`/soft `#dbeafe`/dark `#1e40af`; success `#16a34a`/soft `#dcfce7`/dark `#166534`; plus neutral and purple system tints. These are defined in `platform_console.css :root`, **not** in the core token set — see Section 14.3 and 14.8.

### 14.3 Design Tokens

**Status: NORMATIVE.**

All visual values are expressed as `--mph-*` custom properties — never hard-coded literals in templates or component CSS. The token families that exist today in `homepage.css :root`:

```text
Color:      --mph-primary[-dark|-hover|-soft|-muted], --mph-sidebar[-hover|-muted],
            --mph-shell, --mph-surface, --mph-border, --mph-text, --mph-muted, --mph-white,
            --mph-landing-* (bg/panel/panel-strong/border/copy/faint), --mph-slate-200…950
Layout:     --mph-max-width (80rem), --mph-page-padding (1.5rem)
Radius:     --mph-radius-xl (0.75rem), --mph-radius-2xl (1rem), --mph-radius-3xl (1.5rem)
Focus:      --mph-focus-ring (rgba(15,118,110,0.35))
Font:       --mph-font-sans (Inter, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif)
```

**Rules.**
1. **No literal colors in `mph-*` component styles or templates** — only token references. A stylelint rule (Section 14.10) fails CI on a raw hex/`rgb()` color in a `.mph-*` rule, with the `:root` definition blocks and the landing-page decorative gradients as the only allowed sites.
2. **One definition site.** Every token is defined once, in `homepage.css :root`; the other stylesheets consume them.
3. **Semantic intent over raw value.** A component references `--mph-primary`, never `#0f766e`, so the React portal inherits the same semantics (Section 14.9).

**Known token gaps to close as part of reconciliation (Section 14.8).** The audit of the shipped CSS surfaced four issues this section requires be fixed:
- `--mph-shadow-sm` is **referenced** by `.mph-topbar` but **never defined** in `:root` — it must be added (a defined elevation token), since an undefined custom property silently renders no shadow.
- `--mph-font-mono` is **referenced** (with an inline `ui-monospace, monospace` fallback) across the platform console but **never defined** — it must be added to `:root`.
- The **status colors** (amber/danger/blue/success/neutral/system) live only as `--mph-pc-*` locals; they MUST be promoted into the core `:root` as semantic tokens (`--mph-danger`, `--mph-warning`, `--mph-success`, `--mph-info`, each with a `-soft`/`-dark` pair) so badges, banners, and form errors across all three surfaces share one definition.
- There is **no formalized type-scale, spacing-scale, or elevation-scale token family** — sizes, spacing, and shadows are used as rem/`rgba` literals (Sections 14.4–14.6). The MVP may ship with the literals, but the token file MUST add `--mph-text-*`, `--mph-space-*`, and `--mph-shadow-*` families so the React portal consumes named steps rather than re-deriving magic numbers; this is tracked reconciliation work, not a launch blocker.

### 14.4 Typography

**Status: NORMATIVE.**

Inter is the UI and body typeface, declared via `--mph-font-sans` with a system-font fallback so text never blocks render. Base body is `16px` / line-height `1.5`, with `-webkit-font-smoothing: antialiased` and `text-rendering: optimizeLegibility`.

The size scale in use (rem literals today; to be tokenized per Section 14.3): `0.6875` (uppercase labels), `0.75`, `0.8125`, `0.875` (body-small), `0.9375`, `1` (body), `1.0625`, `1.125`, `1.25`, `1.5`, `1.875`, `2.25`, plus fluid headings via `clamp()` (hero up to `clamp(3rem,7vw,4.25rem)`; auth up to `clamp(2.75rem,6vw,4.75rem)`). Weights used: `500, 600, 700, 750, 800`. Headings carry tight negative tracking (down to `-0.07em` on the hero); uppercase labels carry positive tracking (`0.04`–`0.08em`). Numeric/tabular contexts (money, quantities, tables) use Inter's tabular figures so columns align.

Inter is self-hosted; no third-party font CDN is loaded in non-dev (Section 17.8 CSP). The stylesheet declares the font stack; the loading mechanism (self-hosted `@font-face`) is supplied by the asset pipeline and verified by the CSP/network test (Section 14.10).

### 14.5 Layout and Spacing

**Status: NORMATIVE.**

Content width is `--mph-max-width: 80rem`, with `--mph-page-padding: 1.5rem`; centered containers use `width: min(100% - 2rem, …)`. Spacing follows a rem-based step set (`0.125, 0.25, 0.375, 0.5, 0.625, 0.75, 0.875, 1, 1.25, 1.5, 2, 2.5, 3, 4, 5, 6`); these are to be promoted to a `--mph-space-*` family (Section 14.3).

The application shell is a fixed topbar (`mph-topbar` for app pages, `mph-pc-topbar` for the console, `mph-dashboard-topbar` for the placeholder dashboard) carrying org/tenant context and the user menu, with the impersonation-banner slot rendered above it (Section 8.15); below sits the content region (and, in the console, a left nav).

Breakpoints in the shipped CSS are not yet a single consistent set — `430px`, `560px`, `640px`, `760px`, `768px`, `980px`, `1100px` appear across the three stylesheets. The reconciliation (Section 14.8) standardizes these to a shared scale. The MVP is desktop-first for operator/staff use, usable at tablet width, and responsive to small screens without a separate mobile codebase (native mobile is post-MVP, Section 22).

### 14.6 Components

**Status: NORMATIVE.**

The MVP ships a fixed component vocabulary as `mph-*` classes plus HTMX behaviors; ad-hoc one-off styling is prohibited. The real, shipped components:

| Component | Classes | Notes |
|---|---|---|
| Button | `mph-button` + `-primary`/`-secondary`/`-small`/`-light`; console `mph-pc-btn` + `-primary`/`-secondary`/`-danger`/`-warning`/`-ghost` | Primary = `--mph-primary` bg, `--mph-white` text |
| Card / panel | `mph-card`/`mph-feature-card`/`mph-workflow-card`/`mph-plan-card`/`mph-dashboard-card`/`mph-pc-card` | `--mph-surface`, `--mph-radius-2xl`/`-3xl` |
| Form field | `mph-auth-field`; console `mph-pc-field-label`/`-input`/`-textarea`/`-help`, `mph-pc-radio-card` | Focus ring via `--mph-focus-ring`; error text in danger |
| Table | `mph-pc-table`(`-wrap`/`-link`/`-sub`) | Right-align numeric columns; tabular figures |
| Status badge | `mph-pc-badge` + `-primary`/`-active`/`-pending`/`-warning`/`-danger`/`-neutral`/`-system`; `mph-demo-badge`, `mph-popular-badge`, `mph-dashboard-badge` | One family per state-machine status group |
| Callout / alert | `mph-pc-callout` + `-info`/`-warning`/`-danger`; `mph-alert` + `-danger` | Read-only downgrade banner (7.11), blocked-fulfillment banner (11.2.4) |
| Impersonation banner | `mph-imp-banner`(`-inner`/`-content`/`-icon`/`-admin`/`-btn`) | Amber; server-rendered; defined in `platform_console.css` (Section 8.15) |
| Topbar | `mph-topbar`/`mph-pc-topbar`/`mph-dashboard-topbar` | Hosts the impersonation-banner slot |
| Pill / code | `mph-pill`, `mph-code-pill`, `mph-pc-mono` | Mono needs `--mph-font-mono` defined (14.3) |
| Empty state | `mph-pc-empty`, `mph-dashboard-notice` | Dashboard onboarding callouts (13.7) |
| Utility | `mph-focus-ring`, `mph-sr-only` | Focus ring; screen-reader-only text |

The MVP currently has **no single `mph-upgrade-prompt` component**; the entitlement-denial prompt (Section 7.12) is rendered with the existing callout/alert vocabulary (`mph-pc-callout-info` / `mph-alert`). Adding a dedicated `mph-upgrade-prompt` is optional reconciliation work; the normative requirement is that the denial UX routes to "contact your administrator / contact support," never a checkout (Section 7.13, 13.7).

**Entitlement-aware navigation.** Navigation and action entry points use the `has_feature` template tag (Section 7.9) to hide controls a tenant's plan does not include — a convenience, never the security boundary (Section 16.4). RML-scoped members see navigation scoped to their location closure (Section 8.14).

### 14.7 Accessibility

**Status: NORMATIVE.** The MVP targets **WCAG 2.1 AA** for all server-rendered surfaces.

1. **Visible focus is already implemented** and must be preserved: a global `:focus-visible { outline: 2px solid rgba(15,118,110,0.45); outline-offset: 3px }`, a layered `.mph-focus-ring:focus-visible`, and component focus rings via `box-shadow: 0 0 0 3px var(--mph-focus-ring), 0 0 0 6px …`. Focus is never suppressed without an equivalent replacement.
2. **Contrast.** The token-parity test (14.10) asserts AA contrast for each text/background pair. Measured against the shipped palette: white on `--mph-primary` is ≈5.5:1 (passes AA) and primary text on white is the same; landing copy/faint on `--mph-landing-bg` passes comfortably. **One pair is borderline and must be verified/corrected:** `--mph-muted #6c757d` on `--mph-shell #f4f6f9` is ≈4.4:1, just under the 4.5:1 normal-text threshold — the contrast test should catch it and muted may need to darken slightly for body-size use.
3. **Keyboard operability.** All workflows are keyboard-operable; modals/drawers trap and restore focus; HTMX swaps move focus to the updated region.
4. **Semantics.** Native semantic elements; real `<label>`s tied to inputs; errors associated via `aria-describedby` and summarized. `mph-sr-only` provides screen-reader-only text.
5. **Status not by color alone.** Shipped badges/callouts already pair color with a text label (e.g., a danger badge reads its status word) — this MUST be maintained.
6. **Motion (gap to close).** `homepage.css` sets `scroll-behavior: smooth` and the components animate transforms/shadows, but **no `prefers-reduced-motion` block exists yet**. The reconciliation MUST add one that disables non-essential motion; no essential information may be conveyed through animation alone.
7. **The impersonation banner** (`mph-imp-banner`) is server-rendered, in normal landmark/reading order, and meets contrast — it is structurally present, not a dismissible visual afterthought (Section 8.15).

### 14.8 Reconciling the Temporary and Console Styles

**Status: NORMATIVE.**

Three namespaces exist today — `mph-*` (shared/landing), `mph-dashboard-*` (the Milestone-1 tenant dashboard placeholder), and `mph-pc-*` (platform console). Before MVP launch they are reconciled into one coherent token system:

1. **Promote status colors into the core token set.** The `--mph-pc-amber/danger/blue/success/neutral/purple` locals become core semantic tokens (`--mph-warning`, `--mph-danger`, `--mph-info`, `--mph-success`, each `-soft`/`-dark`) in `homepage.css :root`, and `platform_console.css` consumes them rather than defining its own.
2. **Define the missing tokens** flagged in 14.3: `--mph-shadow-sm` (and a small elevation family) and `--mph-font-mono`.
3. **Replace literals in `dashboard.css`.** The placeholder dashboard hard-codes values that must become token references — e.g. `rgba(15,118,110,0.08)` → primary-tint token, `rgba(255,255,255,0.92)`/`#f8fafc` → surface tokens, `0 18px 45px rgba(15,23,42,0.08)` → an elevation token, `var(--mph-radius-3xl)` is already correct. Dashboard widgets adopt the shared `mph-card`/`mph-pc-badge`/empty-state vocabulary rather than bespoke `mph-dashboard-*` rules wherever equivalents exist.
4. **Standardize breakpoints** to the shared scale (Section 14.5).
5. **Extend the token-parity and contrast tests** to cover the dashboard and console once reconciled.

Until reconciled, the dashboard remains functional and is the one surface permitted temporary divergence; the reconciliation is a tracked MVP task (Section 21, trimmable surface polish per the "NEVER cut" list's counterpart).

### 14.9 Continuity for the Post-MVP React Portal

**Status: NORMATIVE.**

The design system is built so the post-MVP React tenant portal preserves the same visual language without a redesign (Section 3.5 rule 6):

1. **Tokens are framework-neutral.** The `--mph-*` custom properties are plain CSS, consumed identically by Django templates today and React components later. The token file is the shared contract — which is exactly why the missing families (14.3) must be formalized: a React `<Button variant="primary">` should resolve to `--mph-primary` and a named radius/space/elevation token, not a copied magic number.
2. **Semantic component names survive.** The component vocabulary (14.6) maps one-to-one to future React components.
3. **Permanent server-rendered surfaces** — landing, Auth0 auth pages, the org picker, the platform console, the custom tenant admin, email/PDF templates (Section 3.5 rule 5) — keep using `mph-*`/`mph-pc-*` classes forever; React replaces only tenant-portal workflow screens and inherits the same tokens, so the two coexist without a visual seam.

This is the visual analogue of the service-layer continuity (Section 16.10): React is a new *rendering* over the same tokens, just as it is a new *adapter* over the same services.

### 14.10 Acceptance Criteria

**Status: NORMATIVE.**

| # | Criterion | Verification |
|---|---|---|
| 1 | The brand primary is teal `#0f766e`; no `#3b82f6` blue brand value appears anywhere | grep + token test |
| 2 | All `--mph-*` tokens are defined once, in `homepage.css :root`; the other stylesheets only consume them | review + token test |
| 3 | No raw hex/`rgb()` color in a `.mph-*` rule outside the `:root` blocks and allowed landing gradients | stylelint CI |
| 4 | Every custom property referenced is defined — no undefined token (`--mph-shadow-sm`, `--mph-font-mono` resolved) | CSS-var integrity CI |
| 5 | Status colors are promoted to core semantic tokens and consumed by all three surfaces | review + token test |
| 6 | `--mph-text-*`, `--mph-space-*`, `--mph-shadow-*` token families exist (literals replaced) | token test |
| 7 | Inter is self-hosted; no third-party font CDN request in non-dev | CSP + network test |
| 8 | Components use the fixed `mph-*`/`mph-pc-*` vocabulary (14.6); no ad-hoc one-off styling | review + stylelint |
| 9 | Entitlement-unavailable nav/controls are hidden via `has_feature` (convenience only) | view test |
| 10 | The entitlement-denial UX routes to contact-support, never a checkout | view test |
| 11 | Every token text/bg pair meets WCAG 2.1 AA; the `--mph-muted` on `--mph-shell` pair is verified ≥4.5:1 | token-parity + axe |
| 12 | The implemented `:focus-visible`/`--mph-focus-ring` indicators are preserved; focus never suppressed | axe + keyboard test |
| 13 | Modals/drawers trap and restore focus; HTMX swaps move focus to the updated region | integration test |
| 14 | Status is conveyed by text/icon plus color, never color alone | review + axe |
| 15 | A `prefers-reduced-motion` block exists and disables non-essential motion | review |
| 16 | The `mph-imp-banner` is server-rendered, in landmark order, and AA-contrast | view + axe |
| 17 | `mph-dashboard-*` placeholder styles are reconciled to tokens before launch; literals replaced | CI (post-reconciliation) |
| 18 | Breakpoints are standardized to the shared scale across the three stylesheets | review |
| 19 | The `mph-pc-*` console namespace does not leak into landing or tenant-portal pages | review + scoped test |
| 20 | The token file is framework-neutral CSS custom properties (consumable by future React) | review |

---

## Section 15 — Data Model Inventory

### 15.1 Purpose

**Status: NORMATIVE.**

Section 15 is the consolidated catalog of every persistent model in the MVP, grouped by Django app, with its tenancy classification, primary-key strategy, and the section that specifies it in full. It is a **map, not a re-specification**: where a field-level definition appears in an earlier section, that section remains authoritative and this inventory points to it. The value of this section is the single place to answer "what models exist, which app owns each, which are tenant-owned, and where is each defined."

Two cross-cutting classifications used throughout:

- **Tenant-owned** — carries `organization_id`, uses `TenantManager`, declares `is_tenant_owned = True`, inherits `TenantOwnedModel` (Section 5.3). Subject to the CI isolation guardrail (Section 5.7).
- **Platform-level** — no `organization_id`; global or operator-scoped (e.g., `User`, `Capability`, the seeded plan/add-on entitlement maps). Never returned by `for_org`.

### 15.2 App Layout

**Status: NORMATIVE.**

```text
apps/
  platform_accounts/      User, Auth0Identity                          (Section 8)
  platform_organizations/ Organization, Membership, MembershipRole,    (Sections 5, 8)
                          MembershipScopeAssignment, MembershipCapabilityGrant,
                          Region, Market, Location, HandoffSigningKey,
                          ImpersonationAuditLog
  platform_rbac/          Capability, Role, RoleCapability             (Section 8.13)
  platform_subscriptions/ Subscription, PlanEntitlement,               (Section 7.5)
                          PlanAddOnEntitlement, OrganizationAddOnSubscription,
                          OrganizationEntitlementOverride
  crm/                    Lead, LeadContact, LeadLocation, Client,     (Section 9)
                          ClientContact, ClientLocation, Quote, QuoteVersion,
                          QuoteVersionLine, QuoteVersionDiscount, Task, TaskLink,
                          Communication, CommunicationLink
  catalog/                Service, Product, RawMaterial, Supplier,     (Section 10.2, 10.6, 10.7)
                          SupplierCost, BOM, BOMVersion, BOMLine,
                          BundleDefinition, BundleComponent
  pricing/                PricingSnapshot, PricingRule, PricingApproval,(Section 10)
                          CustomerSegment, PriceList, PriceListEntry,
                          ClientContractPricing, LaborRateCard, LaborRole,
                          PromotionCampaign, TaxJurisdiction, TaxRate
  orders/                 SalesOrder, SalesOrderLine                   (Section 9.5)
  fulfillment/            WorkOrder, WorkOrderNote, WorkOrderCompletionPhoto,(Section 11)
                          PurchaseOrder, PurchaseOrderLine, PurchaseOrderAllocation,
                          PurchaseOrderReceipt, PurchaseOrderReceiptLine,
                          BuildOrder, BuildOrderComponent, BuildLaborEntry
  billing/                InvoicingPolicy, Invoice, InvoiceLine,       (Section 12)
                          Payment, PaymentAllocation, PaymentAdjustment,
                          ReportExportJob
  imports/                ImportProject, ImportBatch, ImportColumnMapping,(Section 13.5)
                          ImportMappingTemplate, ImportRowIssue
  documents/              DocumentAttachment, DocumentAttachmentLink   (Section 13.6)
  platform_audit/         AuditEvent                                   (Section 17)
  platform_core/          OutboxEntry, IdempotencyRecord               (Sections 4.7, 16.6)
```

App names are normative; they determine import paths, the service-module locations the AST checks scan (Section 16.7), and the domain boundaries enforced in Section 16.9.

### 15.3 Platform-Level Models

**Status: NORMATIVE.**

These models have **no** `organization_id` and are never tenant-scoped.

| Model | App | PK | Defined | Notes |
|---|---|---|---|---|
| User | platform_accounts | UUID v7 | 8.2 | Global identity; no usable password |
| Auth0Identity | platform_accounts | UUID v7 | 8.3 | `sub`-keyed link to User |
| Capability | platform_rbac | UUID | 8.13 | Seeded registry; tenants can't mint codes |
| Role (template) | platform_rbac | UUID | 8.13 | `organization_id` null = platform template |
| RoleCapability | platform_rbac | UUID | 8.13 | Template composition |
| PlanEntitlement | platform_subscriptions | UUID | 7.5 | Seeded plan→feature map |
| PlanAddOnEntitlement | platform_subscriptions | UUID | 7.5 | Seeded add-on→feature map |
| HandoffSigningKey | platform_organizations | UUID | 8.10.1 | Rotated; secret field-encrypted |

`Role` is dual-natured: the `organization_id`-null rows are platform templates (platform-level); the org-scoped copies created at org creation (Section 6.3) are tenant-owned. The template/copy split is what lets tenants compose custom roles without mutating the seed.

### 15.4 Tenant-Owned Models

**Status: NORMATIVE.**

Every model below carries `organization_id`, uses `TenantManager`, and is covered by the isolation guardrail (Section 5.7). Grouped by domain; PK is UUID v7 unless noted.

**Tenancy & access (platform_organizations / platform_rbac org-scoped)**

| Model | Defined | Notes |
|---|---|---|
| Organization | 5.2 | The tenant root (referenced by every tenant-owned row) |
| Membership | 8.4 | Authoritative tenant-access record |
| MembershipRole | 8.13 | Role assignment |
| MembershipScopeAssignment | 8.14 | RML scope grant |
| MembershipCapabilityGrant | 8.13 | Per-member GRANT/DENY |
| Role (org-scoped copy) | 8.13 | Assignable; copied from template |
| Region / Market / Location | 8.14 | RML hierarchy |
| ImpersonationAuditLog | 8.15 | 7-yr retention; survives tenant deletion |

**Subscriptions (platform_subscriptions)**

| Model | Defined | Notes |
|---|---|---|
| Subscription | 7.5 | One per org; carries plan + `max_*` limits |
| OrganizationAddOnSubscription | 7.5 | Active add-on packs |
| OrganizationEntitlementOverride | 7.5 | Bidirectional override; audited; reason required |

**CRM (crm)**

| Model | Defined | State machine |
|---|---|---|
| Lead, LeadContact, LeadLocation | 9.2 | Lead: 9.2.2 |
| Client, ClientContact, ClientLocation | 9.3 | Client: 9.3.2 |
| Quote | 9.4.1 | container |
| QuoteVersion | 9.4.1 | 9.4.2 |
| QuoteVersionLine, QuoteVersionDiscount | 9.4.1 | — |
| Task, TaskLink | 9.6 | Task: 9.6.2 |
| Communication, CommunicationLink | 9.7 | — (append-only body) |

**Catalog (catalog)**

| Model | Defined | Gate |
|---|---|---|
| Service, Product | 10.2.2 | `basic_catalog` |
| RawMaterial | 10.2.3 | `raw_materials` |
| Supplier, SupplierCost | 10.2.4 | `suppliers` / `supplier_costs` |
| BOM, BOMVersion, BOMLine | 10.6.1 | `bom_manufacturing` / `bom_versioning`; BOMVersion SM: 10.6.2 |
| BundleDefinition, BundleComponent | 10.7.1 | `bundles` / `configurable_bundles` |

**Pricing (pricing)**

| Model | PK | Defined | Notes |
|---|---|---|---|
| PricingSnapshot | BIGINT | 10.3.4 | Append-only; immutable; replayable |
| PricingRule | UUID | 10.9.1 | Effective-dated |
| PricingApproval | UUID | 10.9.4 | SM: 10.9.4; Pro+ |
| CustomerSegment | UUID | 10.11 | Default STANDARD seeded |
| PriceList, PriceListEntry | UUID | 10.11 | `price_lists`; `max_price_lists` |
| ClientContractPricing | UUID | 10.11 | `client_contract_pricing`; `max_client_contracts` |
| LaborRateCard, LaborRole | UUID | 10.11 | `labor_rate_cards`; `max_labor_rate_cards` |
| PromotionCampaign | UUID | 10.11 | `promotions`; `max_promotion_campaigns` |
| TaxJurisdiction, TaxRate | UUID | 10.11 | `tax_rates` (Basic universal) |

**Orders (orders)**

| Model | Defined | State machine |
|---|---|---|
| SalesOrder | 9.5.4 | 9.5.5 |
| SalesOrderLine | 9.5.4 | fulfillment/invoice eligibility enums |

**Fulfillment (fulfillment)**

| Model | Defined | State machine | Gate |
|---|---|---|---|
| WorkOrder (+Note, +CompletionPhoto) | 11.3.1 | 11.3.2 | `work_orders` |
| PurchaseOrder (+Line, +Allocation, +Receipt, +ReceiptLine) | 11.4.1 | 11.4.3 | `purchase_orders` |
| BuildOrder (+Component, +BuildLaborEntry) | 11.5.1 | 11.5.2 | `build_orders` (+ `build_labor_tracking`) |

**Billing (billing)**

| Model | Defined | State machine | Notes |
|---|---|---|---|
| InvoicingPolicy | 12.2 | — | One per org |
| Invoice, InvoiceLine | 12.3 | Invoice: 12.4 | Snapshot-driven; immutable once issued |
| Payment, PaymentAllocation, PaymentAdjustment | 12.7 | — | Append-only; reversals are new rows |
| ReportExportJob | 12.11 | status enum | `reports` queue |

**Imports & documents (imports / documents)**

| Model | Defined | Notes |
|---|---|---|
| ImportProject, ImportBatch, ImportColumnMapping, ImportMappingTemplate | 13.5.2 | Write-through-services |
| ImportRowIssue | 13.5.2 | BIGINT PK; `issue_code` incl. gate/limit codes |
| DocumentAttachment | 13.6.1 | Cross-domain file model |
| DocumentAttachmentLink | 13.6.1 | Typed link; exactly-one-non-null |

**Cross-cutting (platform_audit / platform_core)**

| Model | App | PK | Defined | Notes |
|---|---|---|---|---|
| AuditEvent | platform_audit | BIGINT | 17 | Append-only; partitioned; retained |
| OutboxEntry | platform_core | BIGINT | 4.7 | Transactional outbox |
| IdempotencyRecord | platform_core | BIGINT | 16.6 | Service-layer idempotency |

### 15.5 Primary-Key Strategy Summary

**Status: NORMATIVE.** (Restates Section 5.8 as an inventory-wide rule.)

| PK type | Used for | Rationale |
|---|---|---|
| UUID v7 | All org-facing entities | Sortable by creation, B-tree-friendly, non-enumerable |
| BIGINT (`BIGSERIAL`) | PricingSnapshot, AuditEvent, OutboxEntry, IdempotencyRecord, ImportRowIssue | High-volume / append-only |
| `BIGSERIAL` | Numbering counters | Native atomic allocation |

UUID v7 is generated in application code (`uuid6.uuid7()`); high-volume append-only tables use `BIGSERIAL` for index density.

### 15.6 Immutable and Append-Only Models

**Status: NORMATIVE.**

These models are never updated-in-place after their defining event; corrections happen via new rows or successor versions. The inventory flags them in one place because the immutability discipline is load-bearing for auditability (Architectural Principle 3) and the AST/test posture (Section 16).

| Model | Discipline | Correction mechanism | Defined |
|---|---|---|---|
| PricingSnapshot | Immutable after write | Re-price → new snapshot; lines re-point FK | 10.3.4 |
| QuoteVersion (once SENT) | Immutable | New version (retraction re-prices) | 9.4 |
| AuditEvent | Append-only | Never corrected; new events only | 17 |
| ImpersonationAuditLog | Append-only; 7-yr | Never deleted in retention | 8.15 |
| Invoice (once ISSUED) | Commercial values immutable | Void (reversal) → corrected invoice | 12.4 |
| Payment / PaymentAllocation | Append-only | Reversal = new negative row | 12.7 |
| BuildLaborEntry | Append-only | Adjustment = new row via `adjustment_of` | 11.5.4 |
| BuildOrderComponent | Frozen at dispatch | Not edited; new build order if needed | 11.5.3 |
| Communication (body) | Immutable | `body_hash` detects tampering | 9.7 |

### 15.7 Typed Link Tables

**Status: NORMATIVE.** (Architectural Principle 7; Section 9.8.)

The MVP uses explicit typed link tables with an exactly-one-non-null CHECK constraint — **never** `GenericForeignKey`. The complete set:

| Link table | Links | Defined |
|---|---|---|
| TaskLink | Task → {lead, quote, client, sales_order, work_order, build_order, purchase_order, invoice} | 9.6.1 |
| CommunicationLink | Communication → same target set | 9.7.1 |
| DocumentAttachmentLink | DocumentAttachment → same target set + import_batch | 13.6.1 |
| PurchaseOrderAllocation | PO line → sales_order_line | 11.4.1 |

Each is enforced at three layers (DB CHECK, service tagged-union input, form single-select). A CI test asserts no `GenericForeignKey` exists anywhere in the codebase.

### 15.8 Effective-Dated Models

**Status: NORMATIVE.** (Section 10.5 effective-dating rule.)

Models selected by `pricing_date ∈ [effective_from, effective_to]` during pricing context build. Listed together because they share the same selection discipline and must each be indexed on their effective window.

```text
SupplierCost          BOMVersion            ClientContractPricing
PriceList             PricingRule           PromotionCampaign
TaxRate               LaborRole (rate-card effective window)
```

### 15.9 Numbered Entities

**Status: NORMATIVE.** (Section 5.8 numbering rule; prefixes configurable per Section 6.6.)

| Entity | Default prefix | Defined |
|---|---|---|
| Lead | `LD` | 9.2.1 |
| Client | `CL` | 9.3.1 |
| Quote | `QT` | 9.4.1 |
| SalesOrder | `SO` | 9.5.4 |
| WorkOrder | `WO` | 11.3.1 |
| PurchaseOrder | `PO` | 11.4.1 |
| BuildOrder | `BO` | 11.5.1 |
| Invoice | `INV` | 12.3 |
| Payment | `PMT` | 12.7 |

Numbers follow `{PREFIX}-{YEAR}-{SEQUENCE}`, allocated under a row lock; gaps from rolled-back transactions are acceptable. There is **no** SaaS-subscription invoice number series (Section 12.10) — these are all tenant→customer business records.

### 15.10 Acceptance Criteria

**Status: NORMATIVE.**

| # | Criterion | Verification |
|---|---|---|
| 1 | Every model in 15.4 carries `organization_id`, uses `TenantManager`, declares `is_tenant_owned` | CI isolation guardrail (5.7) |
| 2 | Every model in 15.3 has no `organization_id` and is never returned by `for_org` | service test |
| 3 | App layout matches 15.2; service modules live under `apps/<domain>/services/` | review + AST Check A |
| 4 | PK strategy matches 15.5 (UUID v7 vs. BIGSERIAL as listed) | model test |
| 5 | No `GenericForeignKey` exists; all cross-links are the typed tables in 15.7 | CI grep test |
| 6 | Every typed link table enforces exactly-one-non-null at DB/service/form | DB + service test |
| 7 | Immutable/append-only models in 15.6 reject in-place mutation after their defining event | service test |
| 8 | Effective-dated models in 15.8 are indexed on their effective window and selected by `pricing_date` | parametrized test |
| 9 | Numbered entities use `{PREFIX}-{YEAR}-{SEQUENCE}` under lock; no SaaS-invoice series exists | service + architecture test |
| 10 | This inventory is complete: every persistent model appears exactly once | review (model-registry diff) |

---

## Section 16 — Service Layer Requirements

### 16.1 Why the Service Layer Is the Spine

**Status: NORMATIVE.**

The service layer is the single authoritative orchestration boundary for every state-changing workflow in MyPipelineHero (Architectural Principle 4). It is not a convention or a style preference — it is the mechanism that makes a dozen guarantees made elsewhere in this guide actually true:

- **The two gates** (RBAC + entitlement) are enforced here, so every surface inherits them (Section 7.9, Section 8.13).
- **The no-React rule** holds because all workflow logic lives here, not in views — so the post-MVP React portal overlays the same services (Section 3.5).
- **Pricing purity** holds because the only database access during pricing is in resolvers, which are invoked by services, never by strategies/modifiers (Section 10.3.2).
- **Tenant isolation** holds because services apply `for_org`/`for_membership` and `ensure_same_org` (Section 5.5).
- **Auditability** holds because every transition emits its AuditEvent from the service that performs it (Section 17).
- **Idempotency** holds because services own the idempotency-key check, not the transport (Section 16.6).

A defect in any one surface (a careless view, a future API endpoint, a Celery task) cannot bypass these guarantees, because the surface has no path to mutate state except through a service that enforces them. This section specifies the contract that makes that structurally true, and the static checks that prevent erosion.

### 16.2 Service Function Contract

**Status: NORMATIVE.**

Every state-changing service function MUST conform to this contract:

1. **Location.** It lives in `apps/<domain>/services/` (or a `services` package within the domain app). Nothing outside a `services` module may perform a state-changing database operation (Section 16.7).
2. **Keyword-only signature.** All parameters are keyword-only (after a bare `*`). This prevents positional-argument drift as signatures evolve and makes every call site self-documenting.
3. **Primitive/dataclass inputs only.** A service takes `organization_id`, `actor_id`, and primitives or frozen dataclasses — **never** a `request`, a session, a view, a form, or a `User`/`Membership` object pulled from request state. This is what makes a service equally callable from an HTMX view, a DRF endpoint, a Celery task, an import row, and a future React-backing endpoint.
4. **Explicit actor.** `actor_id` is the acting `User`; where impersonation applies, an `on_behalf_of_id` accompanies it (Section 8.15). Services never read `request.user`.
5. **Typed return.** It returns a domain entity or a frozen result dataclass — never an `HttpResponse`, never a serialized payload. Serialization is the surface's job.
6. **Transaction ownership.** A service that mutates more than one row, or mutates a row and emits an outbox entry, owns its `transaction.atomic()` block (Section 16.5). Views and tasks do not open transactions around services.

```python
# NORMATIVE: the canonical shape
def <verb>_<noun>(
    *,
    organization_id: UUID,
    actor_id: UUID,
    # ... primitives and frozen dataclasses ...
    idempotency_key: str | None = None,   # required where the op has external side effects
) -> <DomainEntity | ResultDataclass>:
    """
    Required capability: <code>            # RBAC gate
    Required feature:    <feature_code>    # entitlement gate (omit if universal)
    Required limit:      <max_field>       # plan-limit gate (where applicable)
    Required state:      <precondition>    # state-machine precondition
    Emits:               <AUDIT_EVENT>
    """
```

The docstring header (capability / feature / limit / state / emits) is **mandatory** on every state-changing service and is itself checked (Section 16.7): it is the human-readable contract a reviewer and the capability-coverage test rely on.

### 16.3 The Canonical Service Skeleton

**Status: NORMATIVE.**

Every state-changing service executes the same ordered steps. The order is normative because it determines which error a caller sees first (e.g., entitlement denial before a limit error, both before any mutation).

```python
def create_bom_version(*, organization_id, actor_id, product_id, lines,
                       idempotency_key) -> BOMVersion:
    """
    Required capability: catalog.bom.manage
    Required feature:    bom_manufacturing
    Required limit:      active BOMs < max_boms
    Required state:      product.product_kind == MANUFACTURED
    Emits:               BOM_VERSION_CREATED
    """
    # 1. IDEMPOTENCY — short-circuit if this key already produced a result
    if (existing := idempotency_lookup(organization_id, idempotency_key)) is not None:
        return existing.result

    # 2. ENTITLEMENT GATE — "did the tenant pay for it?" (Section 7.7)
    require_feature(organization_id=organization_id, feature_code="bom_manufacturing")

    # 3. RBAC GATE — "can this user do it?" (Section 8.13)
    membership = resolve_membership(organization_id, actor_id)
    require_capability(membership, "catalog.bom.manage")

    with transaction.atomic():
        # 4. LOAD + LOCK — tenant-scoped; lock rows that gate the decision
        product = Product.objects.for_org(organization_id).select_for_update().get(id=product_id)

        # 5. TENANT-CONSISTENCY — every referenced record is same-org (Section 5.5)
        ensure_same_org(product, *resolve_components(organization_id, lines))

        # 6. STATE PRECONDITION — state-machine guard (Section 9.9 / 11.7)
        if product.product_kind != ProductKind.MANUFACTURED:
            raise InvalidStateError(...)

        # 7. LIMIT GATE — numeric ceiling (Section 7.7); checked under lock
        enforce_limit(organization_id=organization_id, limit_field="max_boms",
                      current_count=active_bom_count(organization_id))

        # 8. MUTATE — the actual state change
        version = _write_bom_version(organization_id, product, lines, actor_id)

        # 9. OUTBOX — publish side-effect intents in the same transaction (Section 4.7)
        outbox_publish(organization_id, "bom.indexed", payload={...},
                       idempotency_key=f"bom_indexed:{version.id}")

        # 10. AUDIT — append-only event from the service that performed the change
        audit_emit("BOM_VERSION_CREATED", actor=actor_id, organization=organization_id,
                   target=version, metadata={...})

        # 11. IDEMPOTENCY RECORD — mark the key consumed with the result reference
        idempotency_record(organization_id, idempotency_key, result=version)

    return version
```

**Gate order rationale.** Entitlement (step 2) precedes RBAC (step 3) so that a tenant user on a plan that lacks the feature sees the upgrade prompt (`FeatureNotEntitledError`) rather than a permission error — the tenant-level "you didn't buy this" answer is more actionable than the user-level "you can't do this" answer, and both are correct. The limit gate (step 7) runs **inside** the transaction under the relevant lock, so two concurrent creates cannot both pass a ceiling check (Section 16.5).

### 16.4 The Two Gates (Restated as a Service Obligation)

**Status: NORMATIVE.**

The service layer is the authoritative location for both gates. Decorators (`@require_capability`, `@require_plan_feature`) on views and the `has_feature` template tag are **conveniences for correct HTTP/UX** — they produce the right status code and the upgrade prompt — but they are never the security boundary. A view may omit a decorator and the operation is still gated, because the service it calls enforces both gates. The reverse is prohibited: a service MUST NOT rely on its callers having checked.

| Gate | Question | Function | Raises | HTTP |
|---|---|---|---|---|
| Entitlement | Did the **tenant** pay for it? | `require_feature` | `FeatureNotEntitledError` | 403 (`feature_not_entitled`) |
| Plan limit | Is the tenant **under the ceiling**? | `enforce_limit` | `PlanLimitExceededError` | 403 (`plan_limit_exceeded`) |
| RBAC | Can this **user** do it? | `require_capability` | `CapabilityRequiredError` | 403 (`capability_required`) |
| Operating scope | On **this record**? | object check / `for_membership` | `OperatingScopeViolationError` | 403 |

A universal feature (leads, clients, tasks, communications, basic catalog/quotes/invoicing, standard reports, tenant export/deletion — Section 7.10) requires **no** `require_feature` call; the docstring omits the "Required feature" line, and a service-test asserts these domains carry no entitlement gate (Section 7.16 criterion 22).

### 16.5 Transactions, Locking, and Concurrency

**Status: NORMATIVE.**

1. **Atomicity boundary.** A service owns one `transaction.atomic()` covering all of: the mutation, the outbox insert, the audit emit, and the idempotency record. The outbox insert being in the same transaction as the mutation is what makes side-effect publication exactly-once-or-not-at-all (Section 4.7). Audit and idempotency records share the transaction so a rolled-back operation leaves no audit ghost and no consumed key.
2. **Locking gating rows.** Any row whose current value gates the decision (a quote version being sent, an invoice being paid, a count being checked against a limit) is locked with `select_for_update()` before the check. Limit checks (step 7) and state-precondition checks (step 6) read locked rows so concurrent callers serialize rather than racing.
3. **Optimistic concurrency for drafts.** Long-lived editable entities (notably `QuoteVersion`, Section 9.4.3) carry an `optimistic_version` integer; the mutating service requires `expected_optimistic_version` and raises `ConcurrencyConflictError` on mismatch, so two editors of the same draft cannot silently clobber each other.
4. **No long work in the transaction.** PDF rendering, email, external sync, and anything slow runs **after** commit, via the outbox/Celery (Section 18). A transaction holds only the database work.
5. **Number allocation under lock.** Entity numbering (`{PREFIX}-{YEAR}-{SEQUENCE}`) allocates under a row lock; gaps from rolled-back transactions are expected and acceptable (Section 5.8).

### 16.6 Idempotency

**Status: NORMATIVE.**

Idempotency is owned by the service layer, not the transport, so it protects every caller uniformly (a double-submitted form, a retried API call, a redelivered Celery task, a re-run import row).

```text
IdempotencyRecord
  id: BIGINT, pk (BIGSERIAL)
  organization_id: fk -> Organization on_delete=PROTECT
  idempotency_key: TEXT                    -- caller-supplied or deterministically derived
  operation: TEXT                          -- the service function name
  result_ref: TEXT                         -- type + id of the produced entity
  status: ENUM(IN_PROGRESS, CONSUMED)
  created_at, consumed_at: TIMESTAMPTZ
  unique_together (organization_id, operation, idempotency_key)
```

Rules:

1. **Required where there are external or non-repeatable side effects.** Quote acceptance, payment recording, invoice issue, import-row commit, and fulfillment dispatch all require an idempotency key. Pure-internal idempotent-by-nature reads do not.
2. **Key sources.** A key is either caller-supplied (a form/request idempotency token) or **deterministically derived** where the operation has a natural unique source — fulfillment dispatch uses the `SalesOrderLine.id` (Section 11.2.5); import commit uses `batch_id + row_number` (Section 13.5.4); an outbox-driven task uses the outbox row id.
3. **Replay returns the prior result.** A repeated key short-circuits (skeleton step 1) and returns the same entity, never a duplicate. The `IN_PROGRESS` state plus the unique constraint guard against a concurrent duplicate while the first call is still in its transaction.
4. **Outbox idempotency is separate but analogous.** Outbox **consumers** are independently idempotent on the outbox row id, so the publish side (service -> outbox) and the consume side (worker -> effect) are both safe to retry (Section 4.7, Section 18).

### 16.7 Static Enforcement (The AST Checks)

**Status: NORMATIVE.**

The service-layer contract is not left to discipline; it is enforced by static checks that block merge. These checks are what make the architectural guarantees real rather than aspirational.

**Check A — No state mutation outside services.** A custom AST linter scans the codebase and **fails CI** if any of `.save()`, `.delete()`, `Model.objects.create()`, `.update()`, `.bulk_create()`, `.bulk_update()`, or `transaction.atomic()` appears **outside** a `services` module (allowing migrations and explicitly-annotated maintenance commands). This is the structural backing of the no-React rule (Section 3.5) and the service-layer principle: a view, serializer, template tag, or signal handler literally cannot mutate state.

**Check B — No request objects in services.** The linter fails CI if a function in a `services` module references `request`, `request.user`, `self.request`, `session`, or imports from `django.http`. This guarantees services are surface-agnostic and callable from any transport (Section 16.2 rule 3).

**Check C — Pricing purity.** Functions registered as pricing **strategies** or **modifiers** (Section 10.4, 10.8) are scanned for any database access (`objects`, `filter`, `get`, `save`, a cursor), clock reads (`now`, `today`, `datetime.now`, `time.`), or randomness (`random`, `uuid` generation). Any occurrence fails CI. Only **resolvers** (Section 10.5) may touch the database, and only `PricingContextBuilder` invokes them. This is the structural backing of the determinism/replay guarantee (Section 10.3.2, Section 10.13).

**Check D — Docstring contract present.** Every state-changing service (one containing a mutation, identified by Check A's allowlist running *inside* services) MUST carry the capability/feature/limit/state/emits docstring header (Section 16.2). A missing header fails CI and is what the capability-coverage test (Section 8.13) cross-references against the URL map.

**Check E — Keyword-only enforcement.** Service functions MUST declare keyword-only parameters (a bare `*` before the first named parameter). A positional service parameter fails CI.

These five checks run in CI on every PR and are on the "NEVER cut" list (Section 21): they are the cheapest possible insurance against the slow erosion of the architecture, and removing them would let any single careless change quietly violate tenancy, purity, or the no-React contract.

### 16.8 Exception Taxonomy

**Status: NORMATIVE.**

All service-raised exceptions descend from `MPHError` and carry a stable `error_code` (snake_case) and an HTTP mapping. Surfaces translate them uniformly: the DRF API emits the error envelope (Section 7.12) with the `error_code` and an `X-Error-Code` header; HTMX views render the matching template (upgrade prompt for entitlement, permission notice for RBAC, validation summary for input errors).

```text
MPHError                              (base; carries error_code, http_status, message, details)
+-- AuthorizationError                (403)
|   +-- CapabilityRequiredError       capability_required
|   +-- OperatingScopeViolationError  operating_scope_violation
|   +-- ImpersonationError            impersonation_error
+-- EntitlementError                  (403)
|   +-- FeatureNotEntitledError       feature_not_entitled        -- Section 7
|   +-- PlanLimitExceededError        plan_limit_exceeded         -- Section 7
+-- TenantError
|   +-- TenantViolationError          tenant_violation     (403)  -- cross-org reference
|   +-- ConfigurationError            configuration_error  (500)  -- e.g. missing Subscription
+-- StateError                        (409)
|   +-- InvalidStateError             invalid_state               -- state-machine precondition
|   +-- ConcurrencyConflictError      concurrency_conflict        -- optimistic-version mismatch
|   +-- PricingApprovalPendingError   pricing_approval_pending    -- Section 9.4.4 / 10.9
+-- ValidationError                   input_validation     (422)
+-- PricingError                      (409/422)
|   +-- PricingConfigurationError     pricing_configuration       -- e.g. no effective BOM
|   +-- PricingFloorViolationError    pricing_floor_violation     -- Section 10.9.4
+-- BillingError                      (409/422)
|   +-- PaymentOverAllocationError    payment_over_allocation     -- Section 12.8
|   +-- InvoiceOverPaymentError       invoice_over_payment        -- Section 12.8
+-- IdempotencyConflictError          idempotency_conflict (409)  -- key reused with different inputs
```

`FeatureNotEntitledError` and `PlanLimitExceededError` are first-class members of this taxonomy (not ad-hoc), so the two-gate model is wired into error handling everywhere. An `IdempotencyConflictError` is raised when a key is reused with **different** inputs (a genuine client bug), distinct from a benign replay with identical inputs (which returns the prior result).

### 16.9 Service Composition and Domain Boundaries

**Status: NORMATIVE.**

1. **Services may call services.** A higher-level workflow (e.g., `accept_quote`, Section 9.5) composes lower-level services (client resolution, sales-order creation, fulfillment-dispatch enqueue). The outermost service owns the transaction; inner services participate in it and do **not** open their own nested `atomic()` for the same logical operation (they may use savepoints where partial rollback is intended).
2. **Gates are not double-charged.** When an outer service has already established the membership and checked a capability, inner helpers receive the resolved membership rather than re-resolving from `actor_id` — but any inner service that is **also** a public entry point still performs its own gates when called directly. The rule: every public service entry point is independently safe; composition is an optimization, never a way to skip a gate.
3. **No cross-domain imports of internals.** A domain's services expose a public surface; other domains call that surface, not the first domain's models or private helpers directly. This keeps domain boundaries enforceable and the dependency graph acyclic.
4. **Signals are prohibited for workflow.** Django signals MUST NOT drive state changes or side effects (Architectural Principle 10). Cascades are explicit service calls, so the control flow is readable and testable. Signals are permitted only for framework-level concerns that never mutate domain state.

### 16.10 Surface Adapters (How Each Caller Uses Services)

**Status: NORMATIVE.**

Every surface is a thin adapter that (a) authenticates/authorizes at the transport layer, (b) deserializes input into primitives/dataclasses, (c) calls a service, (d) serializes the result or translates an exception. None contains workflow logic.

| Surface | Input -> primitives | Calls | Output | Notes |
|---|---|---|---|---|
| HTMX view | form/POST -> dataclass | service | rendered partial/page | CSRF enforced; exceptions -> templates |
| DRF endpoint | serializer -> dataclass | **same** service | serialized DTO | session-cookie auth; exceptions -> error envelope (Section 4.9) |
| Celery task | outbox payload -> primitives | service | none (effects) | idempotent on outbox row id (Section 18) |
| Import row | mapped CSV row -> dataclass | service | per-row result/issue | dry-run uses a rolled-back txn (Section 13.5.4) |
| Management command | argv -> primitives | service | stdout | maintenance commands annotated for Check A |
| Future React backing endpoint | JSON -> dataclass | **same** service | JSON DTO | identical to DRF; this is why the API exists in the MVP (Section 4.9) |

The bottom row is the entire point of the architecture: the post-MVP React portal is a new **adapter**, not a new **backend**. Because the service layer is exhaustive and surface-agnostic, the React transition adds a serialization surface and changes nothing about how state mutates, how it is gated, or how it is audited.

### 16.11 Testing the Service Layer

**Status: NORMATIVE.**

The service layer is where the densest tests live, because it is where behavior lives:

1. **Service tests are the primary unit.** Each service has tests for the happy path, each gate denial (entitlement, limit, RBAC, scope), each state precondition, idempotent replay, and tenant-isolation (a cross-org reference raises `TenantViolationError`).
2. **Gate-matrix tests.** A parametrized matrix asserts, per gated operation, that the correct exception is raised when the feature is absent, the limit is hit, the capability is missing, or the scope excludes the target — and that the operation succeeds when all gates pass (Section 7.16, Section 8.20).
3. **Idempotency tests.** Each idempotent service is called twice with the same key and asserted to produce one entity; called with a different-input same key and asserted to raise `IdempotencyConflictError`.
4. **The five AST checks (Section 16.7) run in CI** as the structural floor beneath the behavioral tests.
5. **No-mock-of-the-service-layer rule.** Surface tests (view/API) may assert that the right service was called with the right primitives, but the authoritative behavioral assertions live in service tests against a real database, so a passing surface test can never mask a broken service.

### 16.12 Acceptance Criteria

**Status: NORMATIVE.**

| # | Criterion | Verification |
|---|---|---|
| 1 | Every state-changing operation has a service in `apps/<domain>/services/` | AST Check A + review |
| 2 | Check A fails CI on `.save`/`.delete`/`.create`/`.update`/`bulk_*`/`atomic` outside services | CI (deliberate violation fixture) |
| 3 | Check B fails CI on `request`/`session`/`django.http` reference inside a service | CI |
| 4 | Check C fails CI on DB/clock/random access inside a strategy or modifier | CI |
| 5 | Check D fails CI on a mutating service missing the capability/feature/limit/state/emits docstring | CI |
| 6 | Check E fails CI on a positional (non-keyword-only) service parameter | CI |
| 7 | Services take `organization_id`/`actor_id` + primitives/dataclasses; never `request` | review + Check B |
| 8 | Gate order is entitlement -> RBAC -> (load/lock) -> state -> limit -> mutate -> outbox -> audit -> idempotency | service test |
| 9 | A tenant lacking the feature gets `FeatureNotEntitledError` before any RBAC error | service test |
| 10 | Limit checks run under `select_for_update`; concurrent creates serialize at the ceiling | concurrency test |
| 11 | Outbox insert, audit emit, and idempotency record share the mutation's transaction | service test (rollback leaves none) |
| 12 | Optimistic-version mismatch on a draft raises `ConcurrencyConflictError` | service test |
| 13 | Idempotent replay (same key, same inputs) returns the prior entity, no duplicate | service test |
| 14 | Same key with different inputs raises `IdempotencyConflictError` | service test |
| 15 | Every `MPHError` subclass carries a stable `error_code` and HTTP mapping | unit test |
| 16 | `FeatureNotEntitledError`/`PlanLimitExceededError` are members of the taxonomy (not ad-hoc) | unit test |
| 17 | Universal-feature services carry no `require_feature` call (docstring omits the line) | service test |
| 18 | Composed services share the outer transaction; no inner nested `atomic()` for one logical op | review + service test |
| 19 | Every public service entry point is independently gate-safe when called directly | service test |
| 20 | No Django signal drives a state change or side effect | review + grep test |
| 21 | DRF endpoint and HTMX view for the same operation call the identical service | review + test |
| 22 | Long work (PDF/email/sync) runs post-commit via outbox/Celery, never in the transaction | review + service test |
| 23 | Gate-matrix test passes for every gated operation across all four gates | CI |
| 24 | Service tests run against a real database; surfaces do not mock the service layer | CI |

---

## Section 17 — Audit, Security, and Compliance

### 17.1 Scope

**Status: NORMATIVE.**

Section 17 specifies the audit system, the security controls, the data-protection mechanisms (field encryption, secrets), and the tenant data lifecycle (export and deletion) that the rest of the guide forward-references. It is the authoritative home for: the `AuditEvent` model and retention policy, what is audited and what must never be logged, field-level encryption, secrets handling, the HTTP security posture, and the tenant export/offboarding/deletion workflows that Sections 5.9, 8, 12, and 13 point to.

Three principles govern this domain:

1. **Audit is append-only and complete** (Architectural Principle 6). Every state transition, auth event, authorization change, entitlement change, impersonation, and pricing override/approval emits an `AuditEvent`. Audit is never edited or deleted within its retention window.
2. **Tenant data is the tenant's.** A tenant can export its data and request deletion on any plan (`tenant_export`/`tenant_deletion` are universal, Section 7.10). Deletion is real and irreversible after a grace period — but never destroys the audit trail needed for accountability.
3. **Secrets and sensitive fields are protected at rest and never logged.** Auth tokens, the Auth0 client secret, MFA material, signing-key secrets, and adapter credentials are encrypted or externalized, and excluded from logs and audit metadata.

### 17.2 The AuditEvent Model

**Status: NORMATIVE.**

```text
AuditEvent                                   -- append-only; partitioned by month
  id: BIGINT, pk (BIGSERIAL)
  organization_id: UUID, fk -> Organization on_delete=PROTECT, null
                                             -- null only for platform-level events
                                             --   (e.g. signing-key rotation)
  schema_version: INT, default(1)            -- the audit schema contract (Section 1.4)
  category: ENUM(AUTH, AUTHZ, ADMIN, COMMERCIAL, OPERATIONAL, PRICING, BILLING,
                 ENTITLEMENT, IMPERSONATION, PLATFORM, SECURITY)
  event_code: TEXT                           -- e.g. "QUOTE_SENT", "PAYMENT_RECORDED"
  actor_user_id: UUID, fk -> User, null      -- the acting user (System User for automated)
  on_behalf_of_user_id: UUID, fk -> User, null  -- the impersonated user, if any (Section 8.15)
  membership_id: UUID, fk -> Membership, null
  target_type: TEXT, null                    -- model label of the affected entity
  target_id: TEXT, null                      -- its id (text to span UUID/BIGINT)
  correlation_id: UUID                        -- ties events within one request/workflow
  client_ip: INET, null
  client_user_agent: TEXT, null
  metadata: JSONB                             -- event-specific, scrubbed (Section 17.5)
  occurred_at: TIMESTAMPTZ                     -- partition key
  index (organization_id, occurred_at)
  index (organization_id, category, occurred_at)
  index (organization_id, target_type, target_id)
  index (correlation_id)
```

**Append-only.** `AuditEvent` has no update or delete path in the service layer; the AST check (Section 16.7) plus a database trigger that rejects `UPDATE`/`DELETE` on the table enforce this. The only removal is partition drop at end-of-retention (Section 17.4), and only for partitions wholly past retention for every category they contain.

**Partitioning.** The table is range-partitioned by `occurred_at` (monthly). This keeps the hot recent partitions small and makes retention a partition-drop rather than a mass delete. Partition pre-creation is a maintenance beat job (Section 18), exempt from entitlement checks (Section 7.8).

**`schema_version`.** The MVP ships version `1`. A change to the meaning of existing fields or the structure of `metadata` is a schema-version bump and a guide PR; readers (export, support tooling) branch on `schema_version` so old events remain interpretable.

### 17.3 What Is Audited

**Status: NORMATIVE.**

Every state-changing service emits its `AuditEvent` from within its transaction (Section 16.3 step 10), so audit and the mutation commit or roll back together. The event catalog is distributed across the domain sections; this is the consolidated category map.

| Category | Representative events | Defined |
|---|---|---|
| AUTH | `LOGIN_*`, `OIDC_CALLBACK_*`, `SENSITIVE_ACTION_REAUTH`, `LOGOUT`, `SESSION_EXPIRED` | 8.17 |
| AUTHZ | `ROLE_ASSIGNED/_UNASSIGNED`, `CAPABILITY_GRANT_APPLIED` | 8.17 |
| ADMIN | `ORG_CREATED`, `ORG_SETTINGS_UPDATED`, `MEMBER_*`, `MEMBERSHIP_*`, `ORG_SETUP_RESET` | 6, 8 |
| ENTITLEMENT | `SUBSCRIPTION_*`, `ADD_ON_*`, `ENTITLEMENT_OVERRIDE_*`, `FEATURE_ACCESS_DENIED` (sampled) | 7.15 |
| IMPERSONATION | `IMPERSONATION_STARTED/_ENDED/_AUTO_ENDED/_FORCE_TERMINATED`, `PLATFORM_ADMIN_QUERY` | 8.15, 8.17 |
| COMMERCIAL | `LEAD_*`, `CLIENT_*`, `QUOTE_*`, `ORDER_*` | 9 |
| PRICING | `PRICING_SNAPSHOT_CREATED`, `PRICING_LINE_OVERRIDDEN`, `PRICING_APPROVAL_*`, `PRICING_FLOOR_BLOCKED`, config events | 10.13 |
| OPERATIONAL | `WORK_ORDER_*`, `PURCHASE_ORDER_*`, `BUILD_ORDER_*`, `BUILD_LABOR_*`, `FULFILLMENT_DISPATCH_BLOCKED` | 11 |
| BILLING | `INVOICE_*`, `PAYMENT_*`, `ACCOUNTING_SYNC_*`, `REPORT_EXPORTED` | 12.13 |
| ADMIN (imports/docs) | `IMPORT_BATCH_*`, document upload/delete | 13.5, 13.6 |
| SECURITY | `HANDOFF_*`, `HANDOFF_SIGNING_KEY_*`, `FIELD_DECRYPTION_FAILED`, `TENANT_EXPORT_*`, `TENANT_DELETION_*` | 8.10, 17.7, 17.8 |
| PLATFORM | platform-console operator actions not tied to one tenant | 13.2 |

**Attribution under impersonation.** When `session.is_impersonating`, the event records `actor_user_id` = the support user and `on_behalf_of_user_id` = the impersonated user (Section 8.15). Automated transitions record the System User as actor (Section 8.5). Every event carries the `correlation_id` of its originating request/workflow so a multi-step operation (e.g., quote acceptance -> order -> dispatch) is traceable end to end.

### 17.4 Audit Retention

**Status: NORMATIVE.**

Retention is **per-category**, with money- and security-relevant events held longest. A partition is dropped only when it is wholly past the **maximum** retention of every category of event it contains.

| Category | Retention | Rationale |
|---|---|---|
| BILLING, PRICING (snapshots/overrides/approvals) | 7 years | Financial/commercial record-keeping |
| IMPERSONATION (`ImpersonationAuditLog` + events) | 7 years | Accountability for support access (Section 8.15) |
| SECURITY (handoff, key rotation, export/deletion, decryption failures) | 7 years | Incident investigation |
| ENTITLEMENT, AUTHZ, ADMIN | 3 years | Tenancy/permission history |
| AUTH | 2 years | Login forensics |
| COMMERCIAL, OPERATIONAL | 3 years | Business history (aligned to commercial retention) |

The `Subscription.audit_retention_tier` (STANDARD/EXTENDED/CUSTOM, Section 7.6) can **lengthen** retention for Pro/Enterprise tenants but never shortens below these floors. Retention is enforced by a maintenance beat job that drops eligible partitions and logs a `SECURITY`/`AUDIT_PARTITION_DROPPED` event (itself retained 7 years). Tenant deletion (Section 17.10) does **not** delete audit; audit outlives the tenant.

### 17.5 Logging Hygiene and Metadata Scrubbing

**Status: NORMATIVE.**

The following MUST NEVER appear in logs, `AuditEvent.metadata`, error reports, or traces:

- OAuth/OIDC authorization codes, access tokens, ID tokens, refresh tokens; the Auth0 client secret.
- Any MFA material (codes, secrets).
- Handoff tokens and `HandoffSigningKey.secret`.
- Field-encrypted values in plaintext (Section 17.6) and the encryption keys.
- Accounting/adapter credentials (`accounting_adapter_config`).
- Full payment instrument data (the MVP records offline payment *references* like a check number, never card PANs — Section 12.7).
- Personal data beyond what an event needs for its purpose (data minimization).

A structured-logging processor (structlog, Section 4.2) runs a **scrubbing filter** that redacts known-sensitive keys before emission; a CI test feeds representative payloads through it and asserts redaction. Audit `metadata` is constructed by services to hold only non-sensitive, purpose-relevant fields (e.g., a price override records the old/new price and reason, never a token). A decryption failure emits `FIELD_DECRYPTION_FAILED` (SECURITY) with the field name and record id — never the ciphertext or key.

### 17.6 Field-Level Encryption

**Status: NORMATIVE.**

Specific sensitive fields are encrypted at rest at the application layer (in addition to volume/disk encryption provided by the host), so a database dump alone does not expose them:

| Field | Model | Section |
|---|---|---|
| `accounting_adapter_config` | Organization | 5.2, 12.9 |
| `invitation_token_hash` | Membership | 8.4 (hashed; the token itself is never stored) |
| `secret` | HandoffSigningKey | 8.10.1 |
| `tax_exempt_certificate_ref` | Client | 9.3.1 (where it contains sensitive identifiers) |

Encryption uses authenticated symmetric encryption (AEAD) with a key supplied from the environment/secret manager (Section 17.7), versioned so keys can rotate without rewriting history (a `key_version` prefix on the ciphertext selects the key). Encrypt/decrypt happens in a model field or a thin service helper; plaintext is never logged (Section 17.5). A decryption failure is a `SECURITY` audit event and surfaces as `ConfigurationError`, never a silent empty value.

### 17.7 Secrets Management

**Status: NORMATIVE.**

1. **No secrets in source control or images.** The Auth0 client secret, database/Redis credentials, the field-encryption key(s), object-storage credentials, and signing material come from environment variables sourced from an approved secret store (Section 4.2, Section 20). A CI secret-scan blocks merge on a committed credential.
2. **Per-environment isolation.** Each environment (`dev`/`test`/`staging`/`demo`/`prod`, Section 4.5) has its own Auth0 application and its own secrets; production secrets never appear in non-production environments.
3. **Rotation.** Handoff signing keys rotate quarterly with a two-key overlap (Section 8.10.1); the field-encryption key is versioned for rotation without history rewrite (Section 17.6); credential rotation procedures are part of the operations runbook (Section 20).
4. **Least privilege.** Service credentials (DB, storage, Redis) are scoped to what the service needs; the web tier and worker tier may hold different credential sets.

### 17.8 HTTP Security Posture

**Status: NORMATIVE.**

Applied at the reverse proxy and/or Django middleware (Section 4.4):

- **TLS everywhere**; HTTP redirects to HTTPS; HSTS in production.
- **Security headers**: a restrictive `Content-Security-Policy` (self-hosted assets, no third-party font/script CDN in non-dev — Section 14.4), `X-Content-Type-Options: nosniff`, `Referrer-Policy`, `X-Frame-Options`/`frame-ancestors` to prevent clickjacking (the impersonation banner depends on the page not being frameable, Section 8.15).
- **CSRF** enforced on all mutating requests; HTMX and the future same-origin React client both satisfy it (Section 4.9).
- **Session cookies**: `Secure`, `HttpOnly`, `SameSite=Lax`; tenant-local cookie scoped to its subdomain (Section 8.11).
- **Rate limiting** on auth-adjacent endpoints (login start, callback, invite acceptance, handoff consumption) via Redis counters (Section 4.4) to blunt brute-force and token-guessing; handoff replay/host-mismatch already emit high-severity audit events (Section 8.10).
- **Input validation** at the surface (forms/serializers) before the service; services validate again (defense in depth) and raise `ValidationError` (Section 16.8).

Auth0 owns credential-level attack protection (breached-password, brute-force on credentials, bot detection) per its configured policy (Section 8.18); the controls here protect the MyPipelineHero edge around it.

### 17.9 Tenant Data Export

**Status: NORMATIVE.** Entitlement: `tenant_export` (universal). Sensitive action (Section 8.12).

A tenant can export its complete dataset on any plan. Export is operator- or admin-initiated, runs async, and produces a downloadable archive.

```text
TenantExportRequest
  id: UUID, pk
  organization_id: fk -> Organization on_delete=PROTECT
  requested_by_id: fk -> User
  status: ENUM(REQUESTED, RUNNING, COMPLETED, FAILED, EXPIRED)
  scope: ENUM(FULL, RANGE)                     -- FULL tenant, or a date-bounded subset
  output_document_id: fk -> DocumentAttachment, null   -- the archive (Section 13.6)
  requested_at, completed_at: TIMESTAMPTZ
  download_expires_at: TIMESTAMPTZ, null        -- signed-URL/archive expiry
  error_detail: TEXT, null
```

Workflow: request (sensitive re-auth) -> `bulk`/`reports` queue worker assembles the archive (structured data as CSV/JSON per domain, plus referenced documents) scoped strictly to the org via `for_org` -> archive stored as a `DocumentAttachment` (org-scoped key, Section 13.6.2) -> time-limited signed download. RML-scoped requesters may export only within their location closure unless they hold an org-wide export capability. Export reads only; it never mutates tenant data. Events: `TENANT_EXPORT_REQUESTED/_COMPLETED/_FAILED` (SECURITY). The archive itself is `retention_class = TRANSIENT` and is pruned after `download_expires_at`.

### 17.10 Tenant Offboarding and Deletion

**Status: NORMATIVE.** Entitlement: `tenant_deletion` (universal). Sensitive action (Section 8.12).

Tenant deletion is real and irreversible after a grace period, but is staged so it is recoverable until then and never destroys the audit trail.

```text
Organization.status lifecycle (Section 5.2, 5.9):
  ACTIVE -> (admin requests deletion) -> OFFBOARDING  (30-day grace; read-only; export allowed)
  OFFBOARDING -> (admin cancels)      -> ACTIVE
  OFFBOARDING -> (beat job, after grace) -> DELETED    (cascade executed)
```

```text
TenantDeletionRequest
  id: UUID, pk
  organization_id: fk -> Organization on_delete=PROTECT
  requested_by_id: fk -> User
  status: ENUM(GRACE, CANCELLED, EXECUTING, COMPLETED)
  requested_at: TIMESTAMPTZ
  grace_ends_at: TIMESTAMPTZ                    -- requested_at + 30 days
  cancelled_at, cancelled_by_id: ...
  executed_at: TIMESTAMPTZ, null
```

**Stages.**

1. **Request** (sensitive re-auth, `tenant_deletion`): `Organization.status -> OFFBOARDING`; a `TenantDeletionRequest` opens with a 30-day grace. During grace the tenant is **read-only** (mutating services refuse for an OFFBOARDING org), handoff still permits read access, and export remains available so the tenant can take its data. Emits `TENANT_DELETION_REQUESTED` (SECURITY).
2. **Cancel** (any time during grace, admin): `status -> ACTIVE`; request `CANCELLED`. Emits `TENANT_DELETION_CANCELLED`.
3. **Execute** (beat job after `grace_ends_at`): a transactional cascade hard-deletes the tenant's owned rows across all domains; object-storage documents are deleted (Section 13.6.3); `status -> DELETED`. Emits `TENANT_DELETION_EXECUTED` (SECURITY).

**What survives deletion.** Per Section 5.9, deletion preserves: the `Organization` row as a **tombstone** (`status = DELETED`, for audit attribution), all `AuditEvent` rows (held per category retention, Section 17.4), and all `ImpersonationAuditLog` rows (7-year retention, Section 8.15). A document referenced by a retained audit record is retained until that audit record expires; everything else is removed. This is the deliberate tension resolved: the tenant's *business data* is destroyed on request, but the *accountability record* of what happened — and who accessed it — is not, because that record protects both the platform and the tenant's own former users.

**Irreversibility.** After EXECUTING begins, the deletion cannot be cancelled. The 30-day grace is the recovery window; there is no post-execution undelete in the MVP.

### 17.11 Security Review Gate (Pre-Launch)

**Status: NORMATIVE.**

Before production launch, a security review (cross-referenced from Section 8.19 and Section 20) MUST confirm:

1. Tenant isolation: the CI isolation guardrail passes (Section 5.7); no unscoped tenant query exists in domain code; cross-tenant access only via the two audited paths (Section 5.6).
2. Auth0 integration: callback validation, `email_verified` enforcement, account-linking takeover defense, MFA policy (Section 8.19).
3. Two-gate enforcement: the gate-matrix test passes (Section 16.11); no surface bypasses the service layer (AST Check A).
4. Logging hygiene: the scrubbing filter redacts all listed sensitive keys; no token/secret/MFA material in logs or audit (Section 17.5).
5. Field encryption: listed fields are encrypted at rest; decryption failures are handled and audited (Section 17.6).
6. Secrets: no credential in source/images; per-environment isolation verified (Section 17.7).
7. HTTP posture: TLS/HSTS, CSP, CSRF, frame-ancestors, rate limits in place (Section 17.8).
8. Export/deletion: export is read-only and org-scoped; deletion preserves audit/impersonation/tombstone and is irreversible post-execution (Sections 17.9–17.10).

### 17.12 Acceptance Criteria

**Status: NORMATIVE.**

| # | Criterion | Verification |
|---|---|---|
| 1 | `AuditEvent` is append-only: no update/delete path; DB trigger rejects UPDATE/DELETE | DB + service test |
| 2 | The table is monthly-partitioned; partition pre-creation is a maintenance beat job | migration + job test |
| 3 | Every state-changing service emits its event within the mutation's transaction | service test (rollback leaves none) |
| 4 | Impersonated actions record actor = support user, on_behalf_of = impersonated user | integration test |
| 5 | Automated transitions record the System User as actor | service test |
| 6 | Events carry a `correlation_id` tying a multi-step workflow together | integration test |
| 7 | Per-category retention floors hold; `audit_retention_tier` can only lengthen, never shorten | job + service test |
| 8 | A partition drops only when wholly past max retention for every category it contains | job test |
| 9 | The scrubbing filter redacts every listed sensitive key (token/secret/MFA/ciphertext/credential) | CI scrub test |
| 10 | No token, code, secret, or MFA material appears in any log or audit metadata | security test |
| 11 | Listed fields are field-encrypted at rest (AEAD, versioned key) | security test |
| 12 | A decryption failure emits `FIELD_DECRYPTION_FAILED` and raises `ConfigurationError` (no silent empty) | service test |
| 13 | No secret in source control or images; CI secret-scan blocks committed credentials | CI |
| 14 | Each environment has isolated Auth0 app + secrets; prod secrets absent from non-prod | review |
| 15 | TLS/HSTS, CSP (no third-party font/script CDN non-dev), CSRF, frame-ancestors, rate limits applied | config + integration test |
| 16 | Auth-adjacent endpoints are rate-limited via Redis counters | integration test |
| 17 | Tenant export is universal, sensitive, async, read-only, org-scoped; archive is TRANSIENT | integration test |
| 18 | RML-scoped requester exports only within its location closure | service test |
| 19 | Deletion request sets OFFBOARDING + 30-day grace; tenant becomes read-only; export still allowed | integration test |
| 20 | Cancel during grace restores ACTIVE; execution after grace is irreversible | integration test |
| 21 | Deletion preserves Organization tombstone, all AuditEvent, all ImpersonationAuditLog | integration test |
| 22 | Documents referenced by retained audit survive deletion until that audit expires | service test |
| 23 | Pre-launch security review checklist (17.11) is completed and recorded | review gate |
| 24 | Capability-coverage CI test passes for export/deletion/audit-view routes | CI |

---

## Section 18 — Async and Background Jobs

### 18.1 Scope and the Two-Layer Model

**Status: NORMATIVE.**

Section 18 specifies how deferred and scheduled work runs: the transactional outbox dispatcher, the Celery queue topology, the single beat scheduler, idempotent worker semantics, the scheduled maintenance jobs, and dead-letter handling. It is the execution substrate beneath fulfillment dispatch (Section 11.2), reminders (Section 9.6.3), exports (Section 12.11), accounting sync (Section 12.9), import commit (Section 13.5), audit partitioning and retention (Section 17.2, 17.4), and tenant deletion (Section 17.10).

Async work is **two layers**, and the separation is the whole design:

```text
Durability layer  -> OutboxEntry (a Postgres table, written in the business transaction)
Execution layer   -> Celery (workers + one beat), which CARRIES OUT the durable intent
```

The outbox is the source of truth for "this side effect must happen"; Celery is the mechanism that makes it happen. Celery is never the durability boundary — a lost broker message loses nothing, because the intent is still a `PENDING` outbox row a dispatcher will re-enqueue (Section 18.3). This is what lets the system promise "the email/PDF/dispatch/sync either happens or is visibly pending," never "committed the order but silently dropped the fulfillment."

### 18.2 The Outbox

**Status: NORMATIVE.** (Model home: `platform_core`, Section 15.2. Flow: Section 4.7.)

```text
OutboxEntry
  id: BIGINT, pk (BIGSERIAL)
  organization_id: UUID, fk -> Organization on_delete=PROTECT, null  -- null for platform work
  topic: TEXT                                  -- e.g. "quote.send_email", "sales_order.dispatch_line"
  payload: JSONB                               -- primitives only; ids, not ORM objects
  idempotency_key: TEXT                        -- deterministic; consumer-side dedupe (Section 16.6)
  correlation_id: UUID                          -- carried into the resulting AuditEvents (Section 17.3)
  status: ENUM(PENDING, DISPATCHED, CONSUMED, FAILED, DEAD_LETTER)
  attempts: INT, default(0)
  max_attempts: INT, default(5)
  available_at: TIMESTAMPTZ                      -- earliest dispatch time (backoff)
  last_error: TEXT, null
  created_at: TIMESTAMPTZ
  dispatched_at, consumed_at: TIMESTAMPTZ, null
  index (status, available_at)                  -- the dispatcher's hot query
  index (organization_id, topic)
  unique (organization_id, topic, idempotency_key)   -- publish-side dedupe
```

**Publish (inside the business transaction).** A service that has a side effect inserts an `OutboxEntry` in the same `transaction.atomic()` as its mutation (Section 16.3 step 9, Section 16.5 rule 1). The mutation and the intent commit together or not at all. The publish-side unique constraint makes re-publishing the same logical intent (e.g., a retried service call) a no-op rather than a duplicate.

**Payload discipline.** Payloads carry **primitives** — ids, codes, amounts as strings — never serialized ORM objects. The worker re-loads from the database by id (tenant-scoped), so it always operates on current, consistent state and the payload stays small and version-stable.

### 18.3 The Dispatcher

**Status: NORMATIVE.**

A beat-triggered dispatcher moves durable intents into the execution layer:

```text
every ~5s (beat -> dispatcher task):
  SELECT * FROM outbox
    WHERE status = 'PENDING' AND available_at <= now()
    ORDER BY id
    FOR UPDATE SKIP LOCKED                       -- many dispatchers/workers never collide
    LIMIT <batch>
  for each row:
    mark DISPATCHED
    enqueue the matching Celery task on the row's queue, passing ONLY the outbox row id
```

- **`FOR UPDATE SKIP LOCKED`** lets the dispatcher run safely even if invoked concurrently; rows in flight are skipped, never double-claimed.
- **The Celery task receives only the outbox row id**, then re-reads the row and re-loads domain state by id. The broker message is therefore disposable — if it is lost, the row is still `DISPATCHED` and a reconciliation pass (below) returns it to `PENDING`.
- **Reconciliation.** A periodic sweep returns rows stuck in `DISPATCHED` past a threshold (worker crashed after claim, before consume) to `PENDING` for re-dispatch. Because consumers are idempotent (Section 18.5), re-running a partially-completed effect is safe.

### 18.4 Queue Topology

**Status: NORMATIVE.** (Queues introduced in Section 4.4.)

Logical queue separation is preserved even if the MVP starts with a single worker process consuming all queues:

| Queue | Carries | Concurrency posture |
|---|---|---|
| `critical` | Invite emails, auth-adjacent notifications, handoff-related side effects | Low latency, high priority |
| `default` | General domain async: fulfillment dispatch, accounting sync, document generation | Normal |
| `bulk` | Import-row commits, bulk reminders/notifications | Batch-friendly, isolated so a large import can't starve interactive work |
| `reports` | Report runs and CSV/export archive assembly, tenant-export assembly | Lower concurrency, long-running |

A topic maps to exactly one queue (the mapping is a registered table, asserted by a test). Long, heavy work (`reports`, `bulk`) is isolated so it cannot block low-latency `critical`/`default` work — a 50,000-row import or a full tenant export runs without delaying an invite email.

### 18.5 Worker Semantics

**Status: NORMATIVE.**

Every outbox-consuming Celery task obeys the same contract (Architectural Principle 5):

1. **Idempotent on the outbox row id.** A redelivered task (broker at-least-once delivery, reconciliation re-dispatch, manual retry) detects an already-`CONSUMED` row and returns without repeating the effect. Where the effect itself creates domain state, the underlying service is *also* idempotent on its own key (Section 16.6) — so idempotency is enforced at both the outbox layer and the service layer.
2. **Calls the service layer.** A worker is a surface adapter (Section 16.10): it translates the outbox payload into primitives and calls a service; it does not contain workflow logic and does not mutate state directly (AST Check A, Section 16.7).
3. **Re-loads by id, tenant-scoped.** It reads current domain state via `for_org`; it never trusts stale payload data for anything but identification.
4. **Marks terminal state.** On success -> `CONSUMED` (`consumed_at` set). On a retryable failure -> increment `attempts`, set `last_error`, compute `available_at` via exponential backoff, return to `PENDING`. On reaching `max_attempts` or a non-retryable error -> `DEAD_LETTER` (Section 18.7).
5. **No long synchronous external call without a timeout.** External I/O (email send, accounting adapter, object storage) uses bounded timeouts so a hung dependency fails into retry rather than pinning a worker.
6. **Attribution.** Effects that emit audit attribute the actor to the **System User** (Section 8.5), carrying the `correlation_id` from the outbox row so the async effect is traceable to its originating request (Section 17.3).

### 18.6 The Single Beat Scheduler

**Status: NORMATIVE.**

**Exactly one** Celery beat scheduler runs per environment (Section 4.4). Multiple beats are prohibited — two schedulers would double-fire every periodic job. Beat triggers periodic tasks; each is idempotent and, where double execution would be harmful, takes a short-lived Redis lock so an accidental overlap is a no-op rather than a duplicate.

The MVP runs beat as a single dedicated process. (The Kubernetes lease-based beat-singleton pattern is explicitly post-MVP, Section 4.10, Section 22; the single-process guarantee is sufficient for the Docker/DigitalOcean deployment.) A startup check warns if more than one beat is detected against the same broker.

### 18.7 Failure Handling and Dead Letter

**Status: NORMATIVE.**

```text
PENDING -> DISPATCHED -> CONSUMED                          (happy path)
PENDING -> DISPATCHED -> (retryable fail) -> PENDING       (backoff; attempts++)
                          ... up to max_attempts ...
PENDING -> DISPATCHED -> (max_attempts | non-retryable) -> DEAD_LETTER
```

- **Retryable vs. non-retryable.** Transient failures (timeouts, a temporarily-unavailable dependency, a lock conflict) retry with exponential backoff. Deterministic failures (a malformed payload, a permanently-missing referenced record, a non-retryable validation error) go straight to `DEAD_LETTER` rather than burning attempts.
- **Dead letter is visible, not silent.** A `DEAD_LETTER` row emits a `SECURITY`/`OPERATIONAL` audit event and surfaces in the platform console's operational view (Section 13.2.3) and in monitoring (Section 18.9). An operator can inspect `last_error`, fix the underlying cause, and **requeue** the row (reset to `PENDING`, `attempts = 0`) — safe because the consumer is idempotent.
- **Entitlement-blocked dispatch is not a failure.** Fulfillment dispatch that hits an unentitled artifact does **not** dead-letter; it parks the *line* in `BLOCKED_ENTITLEMENT` and marks the outbox row `CONSUMED` (the dispatch did its job: it determined the line can't proceed yet). This is the Section 11.2.4 rule, restated from the async side: a System-actor task must never dead-letter on an expected business condition.
- **Poison-message protection.** A row that would crash a worker (e.g., an exception during deserialization) is caught, recorded with `last_error`, and dead-lettered rather than crash-looping the worker.

### 18.8 Scheduled Maintenance Jobs

**Status: NORMATIVE.**

The periodic jobs beat triggers. Maintenance-only jobs (those that don't create restricted tenant records) are **exempt from entitlement checks** (Section 7.8); jobs that create tenant records call `require_feature` like any service.

| Job | Cadence | Purpose | Section |
|---|---|---|---|
| Outbox dispatcher | ~5s | Move PENDING intents to the execution layer | 18.3 |
| Outbox reconciliation | ~1 min | Return stuck-DISPATCHED rows to PENDING | 18.3 |
| Audit partition pre-creation | daily | Create next month's `AuditEvent` partition ahead of need | 17.2 |
| Audit retention prune | daily | Drop partitions wholly past max retention | 17.4 |
| Document retention prune | daily | Delete TRANSIENT docs past `delete_after`; expire export archives | 13.6.3, 17.9 |
| Invitation expiry | hourly | Transition `INVITED` memberships past 7 days to `EXPIRED` | 6.9, 8.4 |
| Quote expiry | daily | Transition SENT quotes past `expiration_date` to `EXPIRED` | 9.4.2 |
| Task reminders | frequent | Emit `task.reminder_due` (-24h) / `task.reminder_overdue` (+1h) outbox entries | 9.6.3 |
| Tenant deletion execution | daily | Execute the hard-delete cascade for OFFBOARDING orgs past grace | 17.10 |
| Idempotency record prune | daily | Remove CONSUMED idempotency records past a safe horizon | 16.6 |

Each maintenance job is idempotent (re-running after a partial failure is safe), attributes its transitions to the System User, and emits the relevant audit events. State-changing maintenance (invite/quote expiry, deletion execution) runs through the **service layer**, so the same state machines, audit, and isolation apply as for interactive transitions — beat doesn't get a backdoor.

### 18.9 Observability of Async Work

**Status: NORMATIVE.**

Async work is observable, because a silently-stuck queue is a production incident waiting to be discovered by a customer (Architectural Principle 9):

- **Queue depth and age** per queue are monitored; an alert fires on a growing backlog or a too-old oldest-PENDING row.
- **Dead-letter count** is monitored; any new `DEAD_LETTER` row alerts.
- **Beat liveness** is monitored; a missed dispatcher cycle (no PENDING rows claimed in N intervals while rows exist) alerts.
- **Structured logs** carry the `correlation_id`, outbox `topic`, `attempts`, and (on failure) `last_error`; an effect is traceable from the originating request through the outbox row to the worker run (Section 4.2, structlog).
- **Reconciliation and prune jobs log counts** (rows reset, partitions dropped, documents pruned) so their behavior is auditable over time.

### 18.10 Acceptance Criteria

**Status: NORMATIVE.**

| # | Criterion | Verification |
|---|---|---|
| 1 | A side-effecting service inserts its `OutboxEntry` in the same transaction as its mutation | service test (rollback leaves no row) |
| 2 | Publish-side unique `(org, topic, idempotency_key)` makes re-publish a no-op | service test |
| 3 | Outbox payloads carry primitives only; no serialized ORM objects | review + test |
| 4 | The dispatcher selects PENDING rows with `FOR UPDATE SKIP LOCKED`; concurrent dispatchers never double-claim | concurrency test |
| 5 | The Celery task receives only the outbox row id and re-loads domain state by id | review + test |
| 6 | A lost broker message loses nothing: the row reconciles from DISPATCHED back to PENDING | integration test |
| 7 | Each topic maps to exactly one queue (registered mapping asserted) | registry test |
| 8 | `bulk`/`reports` work cannot starve `critical`/`default` | load test |
| 9 | Every consumer is idempotent on the outbox row id (redelivery repeats no effect) | service test |
| 10 | Workers call the service layer; no direct state mutation in a task (AST Check A) | CI |
| 11 | Retryable failures back off and retry; non-retryable go straight to DEAD_LETTER | service test |
| 12 | Reaching `max_attempts` dead-letters; the row is visible and requeueable | service + integration test |
| 13 | A poison message is caught and dead-lettered, never crash-loops a worker | integration test |
| 14 | Entitlement-blocked fulfillment dispatch CONSUMES the row and parks the line (no dead-letter) | service test |
| 15 | Exactly one beat runs per environment; a second beat against the same broker is detected/warned | startup check test |
| 16 | Beat-triggered jobs that could double-fire take a Redis lock; overlap is a no-op | concurrency test |
| 17 | Maintenance jobs are idempotent and attribute transitions to the System User | service test |
| 18 | State-changing maintenance runs through the service layer (same SM/audit/isolation) | service test |
| 19 | Audit partition pre-creation and retention prune run on schedule and are exempt from entitlement checks | job test |
| 20 | Invitation expiry, quote expiry, and deletion execution transition correctly past their thresholds | job test |
| 21 | Async effects emit audit carrying the originating `correlation_id` | integration test |
| 22 | Queue depth/age, dead-letter count, and beat liveness are monitored and alert | observability review |

---

## Section 19 — Testing and Quality

### 19.1 Scope and Testing Philosophy

**Status: NORMATIVE.**

Section 19 consolidates the test posture distributed across every prior section into one strategy: the test taxonomy, where each kind of assertion lives, the CI gate, coverage expectations, and the test data discipline. It does not introduce new behavior — it specifies how the behavior already specified is verified and kept verified.

Two philosophies govern testing in MyPipelineHero:

1. **Test where the behavior lives.** Behavior lives in the service layer (Section 16), so the densest behavioral tests are service tests against a real database — not view/API tests with mocked services, and not model tests of framework plumbing. A passing surface test must never be able to mask a broken service (Section 16.11 rule 5).
2. **Structural guarantees are tested structurally.** The architecture's load-bearing promises — tenant isolation, no-mutation-outside-services, pricing purity, the no-React rule, single-feature gating — are enforced by **static and registry checks that fail CI**, not by hoping reviewers catch violations. A guarantee that only a human reviewer can verify is a guarantee that erodes; a guarantee a linter enforces is permanent. These checks are the floor beneath the behavioral suite.

### 19.2 Test Taxonomy

**Status: NORMATIVE.**

| Layer | What it asserts | Against | Density |
|---|---|---|---|
| **Static/structural** | Architectural invariants (AST checks, registries) | Source code | Exhaustive (every file) |
| **Unit** | Pure functions: pricing strategies/modifiers, rounding, value objects, error mapping | No database | High |
| **Service** | Workflow behavior, gates, state transitions, isolation, idempotency | Real database | **Primary; highest** |
| **Property** | State-machine completeness, money invariants, idempotency-record consistency | Real database + Hypothesis | Per state machine / invariant |
| **Integration** | Multi-step flows across services, outbox->worker, auth/handoff, import | Real DB + Redis + worker | Medium |
| **Surface** | View/API adapters: serialization, status codes, CSRF, error envelopes | Real DB (thin) | Thin — adapters only |
| **Golden** | Pricing-snapshot replay reproduces stored output at engine version | Stored corpus | Per engine version |
| **Accessibility** | WCAG 2.1 AA on rendered surfaces | Rendered HTML | Per surface family |

The shape is a **diamond**, not a pyramid: a thick service-test middle (where behavior is), a thin surface top (adapters carry no logic to test deeply), and an exhaustive structural floor.

### 19.3 Structural Checks (The CI Floor)

**Status: NORMATIVE.**

These run on every PR and **block merge**. They are the consolidated set referenced throughout the guide; this is their authoritative list. All are on the "NEVER cut" list (Section 21).

| Check | Asserts | Defined |
|---|---|---|
| **AST Check A** | No `.save`/`.delete`/`.create`/`.update`/`bulk_*`/`atomic` outside `services` (+ migrations, annotated commands) | 16.7 |
| **AST Check B** | No `request`/`session`/`django.http` reference inside a service | 16.7 |
| **AST Check C** | No DB/clock/random access inside a pricing strategy or modifier | 16.7, 10.3.2 |
| **AST Check D** | Every mutating service carries the capability/feature/limit/state/emits docstring | 16.7 |
| **AST Check E** | Service parameters are keyword-only | 16.7 |
| **Tenant-isolation guardrail** | Every `is_tenant_owned` model has an `organization` FK and uses `TenantManager` | 5.7 |
| **No-GenericForeignKey** | No `GenericForeignKey` anywhere; cross-links are the typed tables | 9.8, 15.7 |
| **No-React** | No React/Vue/Svelte in the MVP front end | 3.5 |
| **Capability-coverage** | Every URL is `@require_capability`-decorated or explicitly exempted | 8.13 |
| **Feature-registry parity** | The ~38 feature codes and plan/add-on maps match Section 7.4/7.3 | 7.16 |
| **Strategy/resolver/modifier counts** | Exactly 7 strategies, 6 resolvers, 16 modifiers, in canonical order | 10.14 |
| **Token-parity** | Compiled `--mph-*` tokens match the authoritative CSS; AA contrast holds | 14.10 |
| **Topic->queue mapping** | Every outbox topic maps to exactly one registered queue | 18.10 |
| **Secret-scan** | No committed credential | 17.7 |
| **Settings/admin** | Django admin absent from non-dev URLConf | 13.4 |
| **OpenAPI schema** | The committed DRF schema matches the code | 4.9 |

A green structural floor is a precondition for the behavioral suite to be meaningful: it guarantees the *shape* is correct so the behavioral tests can assert the *behavior*.

### 19.4 Service Tests (The Primary Layer)

**Status: NORMATIVE.**

Every state-changing service has, at minimum, tests for:

1. **Happy path** — valid inputs produce the expected entity/result and the expected `AuditEvent` (asserted to exist, with the right actor/on-behalf-of and `correlation_id`).
2. **Each gate denial** — the four gates of Section 16.4, each asserted to raise its specific exception:
   - entitlement absent -> `FeatureNotEntitledError`,
   - limit reached -> `PlanLimitExceededError`,
   - capability missing -> `CapabilityRequiredError`,
   - target out of scope -> `OperatingScopeViolationError`.
3. **Gate order** — a caller who fails *both* entitlement and RBAC receives `FeatureNotEntitledError` first (Section 16.3 rationale).
4. **State preconditions** — invoking from a disallowed state raises `InvalidStateError`; the allowed states succeed.
5. **Tenant isolation** — a referenced record from another org raises `TenantViolationError`; a query returns only the acting org's rows.
6. **Idempotency** — same key + same inputs returns the prior entity (no duplicate); same key + different inputs raises `IdempotencyConflictError` (for idempotent services, Section 16.6).
7. **Concurrency** — optimistic-version mismatch raises `ConcurrencyConflictError`; limit checks under `select_for_update` serialize concurrent creates at the ceiling (Section 16.5).

**The gate matrix.** A parametrized matrix (Section 16.11 rule 2) runs every gated operation x every gate state, asserting the right exception on denial and success when all gates pass. This single matrix is what proves the two-gate model holds uniformly rather than per-handcrafted-test.

### 19.5 State-Machine Property Tests

**Status: NORMATIVE.**

Every state-machine entity (Lead, QuoteVersion, SalesOrder, Membership — Section 9.9; WorkOrder, PurchaseOrder, BuildOrder — Section 11.7; Invoice, Payment — Section 12.14; BOMVersion, PricingApproval — Section 10) has a Hypothesis property test asserting:

- every declared transition maps to an executable service function taking `organization_id`/`actor_id`;
- no service performs an **undeclared** transition;
- every terminal state has zero outgoing transitions;
- every non-terminal state has >=1 incoming and >=1 outgoing transition;
- the recompute functions (`recompute_sales_order_status`, `recompute_invoice_eligibility`) are idempotent.

The state tables in the guide are the **contract** (Architectural Principle 8); these tests are what make "code may not diverge from the table without a guide PR" enforceable rather than aspirational. Billing adds money-invariant properties (Section 12.14): `amount_due = total - sum(active allocations) + sum(adjustments)`, allocations never exceed payment amount or invoice due, reversals net against originals.

### 19.6 Pricing Engine Tests

**Status: NORMATIVE.**

The pricing engine (Section 10) gets the heaviest non-service-layer testing because it is the differentiator and the most intricate component:

1. **Purity (AST Check C)** — strategies/modifiers have no DB/clock/random access (structural).
2. **Determinism** — identical `PricingContext` + engine version -> byte-identical `result_payload` (Section 10.3.2).
3. **Rounding** — Decimal math, `ROUND_HALF_EVEN` at the specified scales, never float (Section 10.3.5).
4. **Resolver effective-dating** — each effective-dated input is selected by `pricing_date in window` across all gated inputs (Section 10.5).
5. **Silent degradation** — per-input tests that an unentitled input is simply absent from the context (segment->1.0, no price list/contract/rules/promotions/location), so a Starter and a Pro quote run identical code on different contexts (Section 10.10).
6. **Hard denial** — explicit use of a gated lever (gated strategy, bundle line, manufactured line, manual override, approval) raises (Section 10.10).
7. **Golden-snapshot replay (CI)** — a stored corpus of `(context -> snapshot)` pairs at engine `"1.0"`; any code change that alters a golden output without an engine-version bump fails the build (Section 10.13). This is the structural guarantee behind replay/reproducibility.

The golden corpus is curated to cover every strategy, representative modifier chains, BOM roll-up, each bundle kind, floor/ceiling trips, and tax — so a change anywhere in the engine that shifts a real-world result is caught.

### 19.7 Integration Tests

**Status: NORMATIVE.**

Integration tests exercise multi-component flows end to end, against a real database, Redis, and a worker:

- **Auth + handoff** — login -> Auth0 callback validation -> canonical-user resolution -> membership branch -> handoff issue/consume -> tenant-local session (Section 8.6–8.11), including replay/host-mismatch rejection.
- **Quote -> order -> fulfillment -> invoice -> payment** — the full commercial spine: accept a quote, assert the sales order and dispatched artifacts, complete fulfillment, generate and issue an invoice from the snapshot, record and allocate a payment, assert the order closes (Sections 9–12).
- **Outbox -> worker** — a side-effecting service commits an outbox row; the dispatcher enqueues; the worker consumes idempotently; a redelivery repeats no effect; a lost broker message reconciles (Section 18).
- **Import** — upload -> map -> validate (dry-run rolled back) -> commit through services; entitlement/limit failures surface as row issues; commit is idempotent on `(batch, row)` (Section 13.5).
- **Entitlement lifecycle** — operator sets plan/add-on; gated operations flip from denied to allowed; a downgrade makes existing records read-only without data loss (Section 7.11).
- **Tenant export/deletion** — export is read-only and org-scoped; deletion grace -> execute preserves audit/impersonation/tombstone and is irreversible post-execution (Section 17.9–17.10).

### 19.8 Surface (View/API) Tests

**Status: NORMATIVE.**

Surface tests are deliberately **thin**, because surfaces are adapters with no workflow logic (Section 16.10). They assert only adapter concerns:

- the surface deserializes input to the right primitives and calls the right service (a service-call assertion, not a re-test of the service);
- correct HTTP status and, for the DRF API, the correct error envelope + `X-Error-Code` on each exception class (Section 7.12, 16.8);
- CSRF is enforced on mutating requests; session auth is required (Section 4.9);
- HTMX partials render the expected fragment; the upgrade prompt renders on entitlement denial (not a raw 403) for tenant users (Section 7.12);
- the impersonation banner is present and server-rendered on tenant pages while impersonating (Section 8.15).

A surface test never substitutes for the service test of the same operation.

### 19.9 Accessibility Tests

**Status: NORMATIVE.**

Per Section 14.7, each surface family (auth pages, dashboard, list/detail, forms, modals, tables, the platform console) is tested for WCAG 2.1 AA: automated axe-style checks for contrast, labels, ARIA, and focus order, plus the token-parity contrast assertion (Section 14.10) and keyboard-operability checks for modals/drawers and HTMX focus management. State-by-color-alone and missing-focus-ring are failures, not warnings.

### 19.10 Test Data and Isolation

**Status: NORMATIVE.**

1. **Real database, transactional isolation.** Service/integration tests run against a real PostgreSQL (the `test` settings, Section 4.5), each test wrapped so it rolls back — no cross-test state leakage.
2. **Factories, not fixtures-of-record.** Test entities are built by factories that produce valid tenant-scoped graphs (org + subscription + membership + roles) so a test starts from a realistic, isolated tenant. A `seed_v1`-equivalent provides the platform-level registries (capabilities, plan/add-on entitlement maps, feature codes).
3. **Multi-tenant by default.** Isolation tests create >=2 orgs and assert no cross-org leakage; the default factory posture is "this could leak" so isolation is actively disproven, not assumed.
4. **Auth0 mocked in tests.** The `test` environment mocks Auth0 (Section 4.5); callback validation logic is tested against crafted claim sets (valid, expired, unverified-email, wrong-issuer/audience) without a live IdP.
5. **Deterministic clock and ids where needed.** Tests that assert effective-dating or idempotency control the clock and id generation explicitly, consistent with the engine's purity requirement (the engine itself never reads the clock — Section 10.3.2).

### 19.11 Coverage and the Quality Gate

**Status: NORMATIVE.**

1. **The structural floor is absolute.** Any failing structural check (Section 19.3) blocks merge unconditionally — there is no coverage tradeoff that excuses a violated architectural invariant.
2. **Service-layer coverage is the meaningful metric.** Coverage is measured and gated on the **service layer and pricing engine** (where behavior lives); a high aggregate number inflated by trivial model/serializer coverage is not the target. Every state-changing service has the Section 19.4 test set; a service missing its gate-denial or idempotency tests is an incomplete service.
3. **Gate-matrix completeness.** The gate matrix (Section 19.4) must cover every operation in the Section 7.10 domain-gating map; a gated operation absent from the matrix fails the gate-completeness test.
4. **State-machine completeness.** Every state table in the guide has a corresponding property test (Section 19.5); a state machine without one fails the SM-coverage test.
5. **No skipped tests in CI.** A skipped or xfail test in the main suite requires an annotated, time-boxed reason; an unexplained skip fails the suite.
6. **CI is the gate.** Merge requires: all structural checks green, the full behavioral suite green, the golden-snapshot suite green, coverage thresholds met on the gated layers, and the OpenAPI schema in sync. This is the same CI gate the deployment pipeline depends on (Section 20).

### 19.12 Acceptance Criteria

**Status: NORMATIVE.**

| # | Criterion | Verification |
|---|---|---|
| 1 | All structural checks in 19.3 run on every PR and block merge | CI |
| 2 | Each structural check has a deliberate-violation fixture proving it fails correctly | CI meta-test |
| 3 | Every state-changing service has happy-path + four-gate-denial + state + isolation + idempotency tests | coverage audit |
| 4 | The gate matrix covers every operation in the Section 7.10 gating map | gate-completeness test |
| 5 | Gate-order (entitlement before RBAC) is asserted | service test |
| 6 | Every guide state table has a property test asserting completeness + no undeclared transitions | SM-coverage test |
| 7 | Money invariants (amount_due, allocation/over-payment, reversal netting) hold under property testing | property test |
| 8 | Pricing determinism: identical context+version -> identical payload | determinism test |
| 9 | Golden-snapshot replay reproduces stored output; an unversioned engine change fails CI | CI |
| 10 | Silent-degradation and hard-denial pricing behaviors are each tested per input/lever | service test |
| 11 | The full commercial spine (quote->...->payment->close) passes as one integration test | integration test |
| 12 | Outbox->worker is idempotent; lost-message reconciliation is tested | integration test |
| 13 | Auth/handoff integration covers replay and host-mismatch rejection | integration test |
| 14 | Import dry-run/commit, entitlement-as-row-issue, and `(batch,row)` idempotency are tested | integration test |
| 15 | Export read-only/org-scoped and deletion grace->execute->audit-survival are tested | integration test |
| 16 | Surface tests assert adapter concerns only and never substitute for the service test | review + CI |
| 17 | DRF error envelope + `X-Error-Code` asserted per exception class | surface test |
| 18 | Entitlement denial renders the upgrade prompt (not raw 403) for tenant users | surface test |
| 19 | Each surface family passes WCAG 2.1 AA (contrast, labels, focus, keyboard) | a11y test |
| 20 | Tests run against a real DB with per-test rollback; >=2-org isolation is actively disproven | CI |
| 21 | Auth0 is mocked in `test`; callback validation tested against crafted claim sets | integration test |
| 22 | Coverage is measured/gated on the service layer + pricing engine; no unexplained skips | CI |
| 23 | The committed OpenAPI schema matches the code | CI |
| 24 | The full CI gate (structural + behavioral + golden + coverage + schema) is the merge precondition | CI |

---

## Section 20 — Deployment and Operations

### 20.1 Scope and Deployment Posture

**Status: NORMATIVE.**

Section 20 specifies how MyPipelineHero is built, deployed, operated, backed up, and recovered: the container topology, the deploy pipeline, migration discipline, backups and the restore drill, the anonymized staging refresh, observability and alerting, the launch checklist, and the operational runbooks. It is the operational realization of the architecture in Section 4; where Section 4 fixed the topology, this section fixes the *process* around it.

The deployment posture is deliberately modest (Locked Decision: Docker/DigitalOcean, no Kubernetes — Section 4.10):

- **Docker images + environment-specific Compose** (or equivalent host-level orchestration) on DigitalOcean.
- **No Kubernetes, Helm, ingress controllers, service mesh, HPA, or cluster autoscaling** in the MVP — these are a post-MVP scalability appendix (Section 22).
- **Managed services preferred** where they reduce operational burden (Managed PostgreSQL, Managed Redis) without changing the application.

The guiding principle: the MVP is *production-ready*, not *infrastructure-heavy*. Everything here is sized for a single-region Docker deployment that a small team can operate, while leaving clean seams for the post-MVP scale-out.

### 20.2 Container Topology

**Status: NORMATIVE.**

The production stack runs these containers/services (Section 4.3, 4.4):

| Service | Role | Scaling note |
|---|---|---|
| Reverse proxy (Nginx/Caddy) | TLS, HTTP->HTTPS, security headers, routing | 1 (or HA pair) |
| Web (Gunicorn + Django) | HTMX surfaces + internal DRF API; **stateless** | Horizontally scalable |
| Worker (Celery) | Outbox consumers + async effects across queues | Horizontally scalable |
| Beat (Celery) | The single scheduler | **Exactly one** (Section 18.6) |
| PostgreSQL | System of record | Managed preferred; 1 primary |
| Redis | Broker, cache, handoff store, entitlement cache, rate limits, locks | Managed preferred |
| pgBouncer | Connection pooling (staging/prod once needed) | Transaction pooling |
| Object storage | S3-compatible (documents, exports) | Managed/external |

Dev-only services (MinIO console, Vite dev server, Mailpit) are excluded from the production stack (Section 4.10). The **web tier is stateless** — no local session storage, no local file writes that matter — so it scales horizontally by adding containers; all state lives in PostgreSQL, Redis, and object storage. The **single-beat constraint** is the one hard non-horizontal element and is enforced by the startup check (Section 18.6).

### 20.3 Configuration and Secrets

**Status: NORMATIVE.**

1. **Environment-variable configuration.** Runtime config comes from environment variables per the settings module for each environment (`config.settings.{dev,test,staging,demo,prod}`, Section 4.5). No environment-specific values are baked into images; the same image runs in staging and prod with different env.
2. **Secrets from an approved store, never in images or source** (Section 17.7): the Auth0 client secret, DB/Redis credentials, the field-encryption key(s), object-storage credentials, signing material. The CI secret-scan blocks committed credentials.
3. **Per-environment Auth0 application + callback URLs** (Section 4.5, 8.19): each environment has its own Auth0 app; production callback URLs are configured and verified before launch (Section 20.9).
4. **`check --deploy` clean.** Django's deployment system check passes with no warnings in staging/prod settings (secure cookies, HSTS, allowed hosts, debug off) as a pipeline step (Section 20.4).

### 20.4 Deploy Pipeline (Migrate-Before-Serve)

**Status: NORMATIVE.**

Deployment is **migrate-before-serve**, ordered so the schema is ready before new code serves traffic:

```text
1. CI gate (Section 19.11): structural + behavioral + golden + coverage + schema — all green
2. Build image; tag with immutable build id (e.g., git SHA)
3. Push image to the registry
4. Pull image on the host(s)
5. Run migrations  (single migration runner; not once-per-web-container)
6. Restart web, worker, beat onto the new image
7. manage.py check --deploy  — fail the deploy on any warning
8. /readyz smoke test  — readiness probe must pass before the deploy is "done"
9. Mark the release; record build id + migration head in the deploy log
```

- **A failing CI gate blocks the build entirely** — the same gate that blocks merge (Section 19.11) is the entry condition for a deploy. No deploy of un-gated code.
- **Migrations run once per release**, not once per container, via a dedicated migration step (a one-shot container/command), so concurrent web containers never race the schema.
- **`/readyz` vs `/healthz`.** `/healthz` is a liveness probe (process up). `/readyz` is a readiness probe that checks DB connectivity, Redis connectivity, and migration head == code's expected head; the proxy routes traffic only to `READY` containers.

### 20.5 Migration Discipline

**Status: NORMATIVE.**

1. **Backward-compatible across one deployed version.** A migration must be safe to run while the *previous* code version is still serving (brief overlap during restart). This means the expand/contract pattern for breaking changes: add the new column/table (expand) in one release, backfill, switch code to it, drop the old (contract) in a *later* release — never add-and-drop in one step that the old code can't tolerate.
2. **No data loss in a forward migration without an explicit, reviewed, audited step.** Destructive migrations (column/table drops) are isolated, reviewed, and only run after the expand release has fully rolled out.
3. **Rollback is forward-or-redeploy, never auto-reverse.** Rolling back redeploys the prior known-good image tag (Section 20.6); the pipeline does **not** auto-run reverse migrations, because a reverse migration on production data is rarely safe. Because migrations are backward-compatible across one version (rule 1), the prior image runs against the new schema during a rollback window.
4. **`UUID v7` generated in app code**, `BIGSERIAL` for high-volume tables (Section 5.8, 15.5) — migrations follow the established PK strategy.
5. **`TenantManager.use_in_migrations = False`** (Section 5.4): migrations operate on the base manager and never carry tenant context.

### 20.6 Rollback

**Status: NORMATIVE.**

Rollback redeploys the previous known-good immutable image tag and restarts web/worker/beat onto it. It does not reverse migrations (Section 20.5 rule 3). Because the schema is backward-compatible across one version, the prior image serves correctly against the current schema. The deploy log's recorded build id + migration head (Section 20.4 step 9) is what makes "the previous known-good tag" unambiguous. A rollback that would require a schema the prior image cannot tolerate indicates the expand/contract discipline was violated and is a defect, not a routine path.

### 20.7 Backups, Restore Drill, and Staging Refresh

**Status: NORMATIVE.**

1. **Automated backups.** PostgreSQL has automated backups with point-in-time recovery (WAL/PITR) — provided by Managed PostgreSQL, or, if self-hosted, configured with durable off-host storage and documented retention. Object storage is independently durable/versioned per its provider.
2. **The restore drill is mandatory and exercised.** A backup that has never been restored is not a backup. The runbook includes a **periodic restore drill**: restore the latest backup into an isolated environment and verify integrity (row counts, a sample of commercial records, a pricing-snapshot replay against the restored data). The drill is performed and recorded before launch (Section 20.9) and on a recurring cadence thereafter.
3. **Anonymized staging refresh.** Staging is refreshed from a **scrubbed** copy of production: PII (names, emails, phones, addresses), Auth0 subjects, secrets/encrypted fields, and payment references are anonymized or stripped during the refresh so staging never holds real customer data. The refresh is a documented, repeatable job; a CI/launch check asserts the scrubber covers every sensitive field enumerated in Section 17.5/17.6.

### 20.8 Observability and Alerting

**Status: NORMATIVE.** (Toolset: structlog JSON, error monitoring, OpenTelemetry SDK — Section 4.2.)

1. **Structured logs** (JSON) carry a `correlation_id` end to end (request -> service -> outbox -> worker, Sections 17.3, 18.9); the scrubbing filter (Section 17.5) runs before emission so no secret/token/MFA material is logged.
2. **Error monitoring** captures unhandled exceptions with the `correlation_id` and (scrubbed) context; `MPHError` subclasses that are expected business outcomes (entitlement/RBAC/validation denials) are **not** error-monitored as faults — they are normal 4xx responses.
3. **Metrics and alerts** (Section 18.9 for async): request latency/error rate; DB and Redis health; **queue depth/age per queue**; **dead-letter count** (any new dead-letter alerts); **beat liveness** (a missed dispatcher cycle while PENDING rows exist alerts); storage usage approaching limits.
4. **The `/readyz` and `/healthz` probes** (Section 20.4) feed both the proxy's routing and external uptime monitoring.
5. **Audit is not a substitute for logs, and vice versa.** Audit (Section 17) is the durable business-accountability record; logs/metrics are the operational-health signal. Both exist; neither replaces the other.

### 20.9 Launch Checklist (Pre-Production Gate)

**Status: NORMATIVE.**

Before serving production tenants, **all** of the following MUST be confirmed and recorded. This is a gate, not a guideline.

| # | Item | Reference |
|---|---|---|
| 1 | Full CI gate green on the release build (structural + behavioral + golden + coverage + schema) | 19.11 |
| 2 | Pre-launch **security review** completed and recorded | 17.11 |
| 3 | Production Auth0 app configured; exact root-domain callback URLs verified; MFA policy on | 8.19 |
| 4 | Secrets loaded from the approved store; none in source/images; per-env isolation verified | 17.7 |
| 5 | `check --deploy` clean in prod settings (secure cookies, HSTS, allowed hosts, debug off) | 20.3 |
| 6 | TLS/HSTS, CSP (no third-party font/script CDN), CSRF, frame-ancestors, rate limits live | 17.8 |
| 7 | Automated backups configured; **restore drill performed and verified** | 20.7 |
| 8 | Anonymized staging refresh job verified to cover every sensitive field | 20.7 |
| 9 | Observability live: logs shipping, error monitoring, queue/dead-letter/beat alerts armed | 20.8 |
| 10 | Exactly one beat per environment; startup check passing | 18.6 |
| 11 | `seed_v1` applied: capabilities, default roles, plan/add-on entitlement maps, feature codes, System User | 7.16, 8.5 |
| 12 | Tenant-isolation guardrail and the full structural floor green against the release | 5.7, 19.3 |
| 13 | `/readyz` smoke test passes against the production stack | 20.4 |
| 14 | Rollback rehearsed: prior image redeploys cleanly against the current schema | 20.6 |
| 15 | Operational runbooks present and reviewed | 20.10 |

A failed item blocks launch; there is no "launch and fix later" path for a security, backup, or isolation item.

### 20.10 Operational Runbooks

**Status: NORMATIVE (that they exist and cover the listed scenarios); INFORMATIVE (their step-by-step content).**

The operations runbook set MUST cover, at minimum:

- **Deploy and rollback** — the pipeline (20.4) and the rollback procedure (20.6), including reading the deploy log.
- **Backup restore** — the full restore drill (20.7) and an emergency production restore.
- **Dead-letter handling** — inspecting a `DEAD_LETTER` outbox row, diagnosing `last_error`, fixing the cause, and requeueing (safe because consumers are idempotent — Section 18.7).
- **Stuck queue / beat down** — diagnosing a growing backlog or a missed dispatcher cycle (20.8, 18.9).
- **Secret/key rotation** — Auth0 client secret, DB/Redis credentials, the field-encryption key (versioned, Section 17.6), and the quarterly handoff signing-key rotation (Section 8.10.1).
- **Tenant lifecycle operations** — operator tenant creation, plan/add-on changes, suspension/reinstatement, impersonation, and processing export/deletion (Sections 6, 7.13, 8.15, 17.9–17.10).
- **Incident response** — the path for a suspected isolation breach, credential compromise (emergency signing-key rotation, Section 8.10.1), or data-exposure event, including which audit categories to pull (Section 17.4).

### 20.11 Scaling Within the MVP Envelope

**Status: NORMATIVE.**

The MVP scales **vertically and by adding stateless containers**, within the no-Kubernetes envelope:

- **Web and worker scale horizontally** by adding containers (both are stateless; workers coordinate through the broker and the `SKIP LOCKED` outbox dispatcher — Section 18.3).
- **PostgreSQL scales vertically** (instance size) with pgBouncer for connection pooling (Section 4.4); read replicas are a post-MVP option.
- **Beat does not scale** — it stays singular (Section 18.6); scaling worker throughput means more *worker* containers, never more beat.
- **Queue isolation** (Section 18.4) is the lever for protecting interactive latency under bulk/report load before any infrastructure scale-out is needed.

When this envelope is exhausted (multi-region, autoscaling, cluster orchestration), that is the post-MVP scalability appendix (Section 22) — explicitly out of MVP scope, with the stateless-web and outbox-durability design already in place so the transition does not require re-architecting the application.

### 20.12 Acceptance Criteria

**Status: NORMATIVE.**

| # | Criterion | Verification |
|---|---|---|
| 1 | Production stack runs the 20.2 services; dev-only services are excluded | deploy review |
| 2 | The web tier is stateless (no local session/file state that matters); scales by adding containers | architecture review |
| 3 | The same image runs across environments; all config is env-var; nothing env-specific baked in | build review |
| 4 | No secret in source/images; CI secret-scan blocks committed credentials | CI |
| 5 | A deploy requires the full CI gate green as its entry condition | pipeline review |
| 6 | Migrations run once per release (dedicated step), not once per web container | pipeline review |
| 7 | `/readyz` checks DB + Redis + migration head; the proxy routes only to READY containers | integration test |
| 8 | `check --deploy` is clean in staging/prod settings and gates the deploy | pipeline test |
| 9 | Migrations are backward-compatible across one version (expand/contract enforced) | migration review |
| 10 | Rollback redeploys the prior image and never auto-reverses migrations | pipeline review |
| 11 | The prior image serves correctly against the current schema (rollback rehearsal) | rollback drill |
| 12 | Automated PITR backups are configured | infra review |
| 13 | The restore drill is performed, verified (incl. a pricing-snapshot replay), and recorded | restore drill |
| 14 | Staging is refreshed from an anonymized copy; the scrubber covers every sensitive field | scrub-coverage test |
| 15 | Structured logs carry `correlation_id`; the scrubbing filter runs before emission | observability review |
| 16 | Expected business denials (entitlement/RBAC/validation) are not error-monitored as faults | observability review |
| 17 | Queue depth/age, dead-letter count, and beat liveness are alerted | observability review |
| 18 | Exactly one beat per environment; startup check passes | startup test |
| 19 | The launch checklist (20.9) is fully completed and recorded before production | launch gate |
| 20 | Runbooks exist and cover every scenario in 20.10 | review |
| 21 | Web/worker scale horizontally; beat stays singular; queue isolation protects interactive latency | architecture review |
| 22 | No Kubernetes/Helm/ingress/HPA/mesh in the MVP deployment | deploy review |

---

## Section 21 — MVP Milestones

### 21.1 Purpose and Sequencing Principle

**Status: NORMATIVE.**

Section 21 is the build spine: the ordered milestones that deliver the MVP, each with its deliverables and **exit criteria**, plus the authoritative **"NEVER cut" list** that the rest of the guide references (Sections 5.7, 16.7, 19.3). A milestone is complete only when its exit criteria pass; exit criteria are concrete, testable, and tied to the acceptance criteria of the sections they realize.

One sequencing principle governs the order:

> **Build the enforcement substrate before the features that depend on it.** Tenancy, identity, RBAC, audit, and entitlements are not features layered on later — they are the floor every domain stands on. Retrofitting any of them after the domains are built would mean revisiting every view, service, query, and background job. So the spine front-loads the substrate (M0–M2A) and only then builds the commercial domains (M3–M7) on top of a complete two-gate, audited, tenant-isolated foundation.

This is why **M2A (Entitlements)** sits where it does (Section 21.6): the entitlement layer must exist before any gated domain is built, or every later milestone accumulates retrofit debt (Section 7, the tier document's own milestone recommendation).

### 21.2 Milestone Spine

**Status: NORMATIVE.**

```text
M0  Foundation                       project skeleton, settings, CI floor, base models
M1  Tenancy + Identity + Auth0       Organization, User, Auth0, handoff, sessions
M2  RBAC + Audit                     capabilities, roles, RML, AuditEvent
M2A Entitlements + Add-Ons   <- NEW  Subscription, feature codes, two-gate enforcement
M3  Catalog + Pricing Engine         catalog, the 7/6/16 engine, snapshots, replay
M4  CRM Pipeline                     Lead, Client, Quote, acceptance -> Sales Order
M5  Fulfillment                      Work / Purchase / Build Orders, dispatch
M6  Billing + Reporting              Invoice, Payment, ten reports, Noop accounting
M7  Custom Admin + Import + Lifecycle platform console, tenant admin, Import Center, export/deletion
M8  Production Readiness             backups, restore drill, observability, launch gate
---------------------------------------------------------------------------
M9+ (post-MVP)  React Portal         the overlay the whole MVP was built to accept (Section 22)
```

Each milestone's entitlement obligations follow the tier document's milestone mapping (the M1->M8 entitlement rollout): the foundation is built in M2A, and each subsequent domain milestone adds the `require_feature`/`enforce_limit` gates for the features it introduces, per the Section 7.10 gating map.

### 21.3 M0 — Foundation

**Status: NORMATIVE.**

**Deliverables.** Repository skeleton; the `apps/` layout (Section 15.2); per-environment settings modules (Section 4.5); Docker Compose for dev; the custom `User` model from migration #1 (Section 8.2); `TenantOwnedModel`/`TenantManager`/`TenantQuerySet` (Section 5.3–5.4); the `OutboxEntry`, `IdempotencyRecord`, and `AuditEvent` core models (Sections 4.7, 16.6, 17.2); the **CI structural floor** (Section 19.3) wired up *first* so the architecture is enforced from the first feature commit.

**Exit criteria.**
- The five AST checks (A–E) run in CI against the skeleton and pass; each has a deliberate-violation fixture proving it fails correctly (Section 19.12 criterion 2).
- The tenant-isolation guardrail, no-GenericForeignKey, no-React, and secret-scan checks are live.
- `User` is the configured `AUTH_USER_MODEL` from migration #1 (Section 8.20 criterion 1).
- Dev environment boots via Compose; `/healthz` and `/readyz` respond (Section 20.4).

**Why first.** The structural floor is built before any domain code so no domain can be written that violates it — the guarantees are enforced from commit one rather than retrofitted.

### 21.4 M1 — Tenancy, Identity, and Auth0

**Status: NORMATIVE.**

**Deliverables.** `Organization` + lifecycle (Section 5.2); `Auth0Identity` and the OIDC login flow via Authlib (Section 8.3, 8.6); callback validation (Section 8.7); canonical-user resolution with no auto-signup (Section 8.8); account-linking rules (Section 8.9); the handoff token protocol + signing-key rotation (Section 8.10–8.10.1); root-domain and tenant-local sessions (Section 8.11); sensitive-action re-auth via Auth0 `max_age` (Section 8.12). Per the entitlement milestone mapping, M1 also **creates the `Subscription` row during organization creation** and stores the initial plan/add-ons, so the enforcement layer that lands fully in M2A has its data present from the first tenant.

**Exit criteria.**
- Auth0 login -> callback validation -> handoff -> tenant-local session works end to end; replay and host-mismatch are rejected and audited (Section 8.20 criteria 2, 8, 9, 11).
- Zero-membership login yields no tenant access; unverified-email linking is rejected (8.20 criteria 4, 5).
- Signing-key rotation holds <=2 non-retired keys; CI enforces the ceiling (8.20 criterion 10).
- `create_organization` creates the `Subscription` in the same transaction (Section 6.11 criterion 2, Section 5.10 criterion 8).

### 21.5 M2 — RBAC and Audit

**Status: NORMATIVE.**

**Deliverables.** `Capability` registry, default `Role` templates, org-scoped role copies, `MembershipRole`, `MembershipCapabilityGrant` with DENY-beats-GRANT (Section 8.13); the three-layer permission algorithm; RML operating scope (`Region`/`Market`/`Location`, `MembershipScopeAssignment`, queryset intersection — Section 8.14, gated by `rml_scope` once M2A lands); support impersonation + `ImpersonationAuditLog` (Section 8.15); the full `AuditEvent` model, partitioning, and the append-only trigger (Section 17.2); the capability-coverage CI test (Section 8.13).

**Exit criteria.**
- DENY overrides GRANT; a scoped role with no scope assignment yields zero access; out-of-scope objects raise `OperatingScopeViolationError` (Section 8.20 criteria 14, 15, 17).
- Impersonation requires reason + re-auth, evaluates with impersonated capabilities, attributes to the support user, and shows the server-rendered banner (8.20 criteria 18, 19).
- `AuditEvent` is append-only (DB trigger rejects UPDATE/DELETE); the capability-coverage test passes (Section 17.12 criterion 1, 8.20 criterion 22).

### 21.6 M2A — Plan Entitlements and Add-On Foundation (NEW)

**Status: NORMATIVE.**

This is the milestone added per the tier document's recommendation (Section 7). It lands the entire entitlement enforcement layer **before** any gated domain is built, so M3–M7 gate features as they go rather than retrofitting.

**Deliverables.** `Subscription` (with the `max_*` limit columns), `PlanEntitlement`, `PlanAddOnEntitlement`, `OrganizationAddOnSubscription`, `OrganizationEntitlementOverride` (Section 7.5); the feature-code registry (~38 codes, Section 7.4); `has_feature`/`require_feature` with override->plan->add-on->deny precedence and request-scoped caching (Section 7.7–7.8); `enforce_limit` (Section 7.7); `FeatureNotEntitledError`/`PlanLimitExceededError` in the exception taxonomy (Section 16.8); the two-gate pattern wired into the service skeleton (Section 16.3); the gate-matrix test harness (Section 19.4); plan/add-on **seed data** for Starter/Growth/Pro/Enterprise and the six add-on packs (Section 7.16); the platform-console controls to set plan / toggle add-ons / set overrides (Section 7.13, built fully in M7 but the services exist here); template nav-hiding via the `has_feature` tag; entitlement audit events (Section 7.15); downgrade-to-read-only behavior (Section 7.11).

**Exit criteria.**
- The feature-code registry and the plan/add-on entitlement maps match Sections 7.4/7.3 exactly (registry-parity CI check, Section 7.16 criteria 1–4).
- Resolution precedence and the status gate behave per Section 7.7; a force-disable override denies a plan-granted feature (7.16 criteria 5–7).
- `require_feature` raises `FeatureNotEntitledError` (403, `feature_not_entitled`); `enforce_limit` raises `PlanLimitExceededError` at the ceiling (7.16 criteria 8, 10).
- Resolution is request-scoped cached (no N+1) (7.16 criterion 12).
- The gate-matrix harness runs (it is populated per-domain in M3–M7) (Section 19.11 rule 3).
- Downgrade preserves existing records read-only and blocks new creation (7.16 criterion 15).

**Why here.** Building this after the domains would mean revisiting every service, view, query, report, and background job to add gates (the explicit retrofit cost the tier doc warns against). Landing it now makes "every gated operation calls `require_feature`" a property the domain milestones simply maintain.

### 21.7 M3 — Catalog and Pricing Engine

**Status: NORMATIVE.**

**Deliverables.** The catalog (services, products, raw materials, suppliers, supplier costs — Section 10.2); BOM/BOMVersion/BOMLine with effective-dated activation (Section 10.6); bundles (Section 10.7); the pricing engine — exactly 7 strategies, 6 resolvers, 16 modifiers, `PricingContext`/`PricingContextBuilder`, `PricingSnapshot` (Sections 10.3–10.5, 10.8); pricing rules + approval workflow (Section 10.9); the pricing-configuration inputs — price lists, contracts, segments, labor cards, promotions, tax (Section 10.11); replay + the golden-snapshot CI corpus (Section 10.13). Gates: price lists, contracts, labor cards, promotions, bundles, BOM/manufacturing, advanced rules, per Section 7.10.

**Exit criteria.**
- The 7/6/16 counts and canonical order hold (registry+order CI check, Section 10.14 criteria 1–2).
- Strategies/modifiers are pure (AST Check C); determinism holds; golden-snapshot replay reproduces stored output and an unversioned change fails CI (10.14 criteria 3, 4, 23).
- Silent degradation vs. hard denial behaves per input/lever (10.14 criteria 8–11).
- Plan limits on price lists/contracts/promotions/BOMs/labor cards raise `PlanLimitExceededError` (10.14 criterion 21).

### 21.8 M4 — CRM Pipeline

**Status: NORMATIVE.**

**Deliverables.** Lead + lifecycle + conversion (Section 9.2); Client + contacts/locations/merge (Section 9.3); Quote/QuoteVersion/lines/discounts + the builder + send + retraction-with-reprice (Section 9.4); acceptance + client resolution + Sales Order creation + the fulfillment-dispatch enqueue (Section 9.5); Tasks and Communications (Sections 9.6–9.7). Gates: `sales_orders`; the in-quote levers (manual overrides, bundles, manufactured lines, approvals) enforced where the engine runs (Section 9.4.7).

**Exit criteria.**
- Lead/Quote/SalesOrder state machines pass their property tests (Section 9.10 criteria 1, 15).
- Every quote line carries a non-null `pricing_snapshot_id`; send rejects pending approvals; retraction re-prices into fresh snapshots (9.10 criteria 3, 4, 6).
- Acceptance is idempotent, maps Lead->Client correctly, creates the order + lines, and enqueues per-line dispatch (9.10 criteria 10, 11, 13).
- Universal CRM features carry no `require_feature` call (9.10 criterion 22).

### 21.9 M5 — Fulfillment

**Status: NORMATIVE.**

**Deliverables.** Fulfillment dispatch routing + idempotency + entitlement-blocked parking (Section 11.2); Work Orders (Section 11.3); Purchase Orders + allocations + receipts (operator-driven, Section 11.4); Build Orders + BOM snapshot + labor + variance (Section 11.5); the cross-artifact invariants and the recompute functions (Section 11.6). Gates: `work_orders`, `purchase_orders`, `build_orders` (+ `build_labor_tracking`, `build_cost_variance`).

**Exit criteria.**
- Dispatch routes per line type, is idempotent, and parks unentitled lines in `BLOCKED_ENTITLEMENT` without dead-lettering (Section 11.8 criteria 2, 3, 6).
- WorkOrder/PurchaseOrder/BuildOrder state machines pass property tests; `quantity_received <= quantity_ordered` holds (11.8 criteria 8, 13, 19).
- Build orders freeze the BOM at dispatch; a later activation doesn't disturb in-flight builds; labor is append-only (11.8 criteria 14, 15, 16).
- The recompute functions are idempotent (11.8 criterion 22).

### 21.10 M6 — Billing and Reporting

**Status: NORMATIVE.**

**Deliverables.** `InvoicingPolicy`; snapshot-driven Invoice/InvoiceLine + lifecycle (Section 12.3–12.5); tax roll-up (Section 12.6); Payment/PaymentAllocation/PaymentAdjustment, append-only with reversal rows (Section 12.7–12.8); the Noop accounting adapter on the outbox boundary (Section 12.9); the ten fixed reports + async CSV export (Section 12.11). Gates: `basic_invoicing`/`standard_reports` universal; `advanced_reporting` tier-gated.

**Exit criteria.**
- Invoices bill only ELIGIBLE lines, reference the SO line's snapshot (no re-pricing), and are immutable once issued (Section 12.15 criteria 2, 4, 10).
- A line is billed at most once across non-void invoices; the `amount_due` invariant holds after every allocation/reversal (12.15 criteria 7, 16).
- Over-allocation/over-payment raise their errors; reversals are append-only (12.15 criteria 13, 14, 15).
- No FK crosses between the subscription and billing domains; payments are offline-only (12.15 criteria 20, 23).

### 21.11 M7 — Custom Admin, Import Center, and Data Lifecycle

**Status: NORMATIVE.**

**Deliverables.** The platform console (operator surface, the sole cross-tenant query path — Section 13.2); the custom tenant admin (Section 13.3); the dev-only Django admin guard (Section 13.4); the Import Center with write-through-services and dry-run validation (Section 13.5); `DocumentAttachment` + typed links (Section 13.6); the tenant dashboard (Section 13.7); tenant export and offboarding/deletion (Section 17.9–17.10). The platform-console subscription controls scaffolded in M2A are fully realized here.

**Exit criteria.**
- The platform console is staff-only, audits every cross-tenant query, and cannot edit tenant commercial records except via impersonation (Section 13.9 criteria 1, 2, 4).
- The tenant-admin subscription page is read-only (no self-service plan change) (13.9 criterion 6).
- Import dry-run runs through real services; unentitled batches report `feature_not_entitled` per row; commit is idempotent on `(batch, row)` (13.9 criteria 11, 12, 15).
- Export is read-only/org-scoped; deletion grace->execute preserves audit/impersonation/tombstone and is irreversible post-execution (Section 17.12 criteria 17, 19, 20, 21).

### 21.12 M8 — Production Readiness

**Status: NORMATIVE.**

**Deliverables.** The deploy pipeline (migrate-before-serve — Section 20.4); migration discipline + rollback (Section 20.5–20.6); automated backups + the **restore drill** (Section 20.7); the anonymized staging refresh (Section 20.7); observability + alerting (Section 20.8); the operational runbooks (Section 20.10); the field-encryption, secrets, and HTTP-security hardening (Section 17.6–17.8); the **pre-launch security review** (Section 17.11) and the **launch checklist** (Section 20.9).

**Exit criteria.**
- The full CI gate is the deploy entry condition; rollback redeploys the prior image and is rehearsed (Section 20.12 criteria 5, 10, 11).
- The restore drill is performed and verified (incl. a snapshot replay against restored data) (20.12 criterion 13).
- The scrubbing filter covers every sensitive field; expected business denials aren't error-monitored as faults (20.12 criteria 14, 16).
- The pre-launch security review and the launch checklist are completed and recorded (Section 17.12 criterion 23, Section 20.12 criterion 19).

### 21.13 The "NEVER Cut" List

**Status: NORMATIVE.**

Under schedule pressure, these are **never** descoped, deferred, or weakened to hit a date. They are the irreducible substrate; cutting any one converts a production system into a liability. This is the authoritative list the rest of the guide references.

| # | Never cut | Why | Defined |
|---|---|---|---|
| 1 | Tenant isolation (`organization_id`, `TenantManager`, the CI guardrail) | A cross-tenant leak is an existential incident | 5.3–5.7 |
| 2 | The five AST checks (A–E) | They make no-React, service-layer, and pricing-purity structural | 16.7 |
| 3 | The two-gate enforcement in the service layer | RBAC + entitlement are the access model; bypassing either is a breach | 7.9, 16.4 |
| 4 | Append-only audit + the DB trigger | Accountability is non-negotiable and unreconstructable after the fact | 17.2 |
| 5 | Auth0 callback validation + no-auto-signup + verified-email linking | The account-takeover defense | 8.7–8.9 |
| 6 | Handoff single-use/host-binding/60s + key rotation | The cross-subdomain trust boundary | 8.10 |
| 7 | Pricing immutability + replay + golden-snapshot CI | Commercial history must be reproducible | 10.3, 10.13 |
| 8 | The outbox (durable side-effect publication) | "Committed but silently dropped the effect" is unacceptable | 4.7, 18.2 |
| 9 | Idempotency on external-effect operations | At-least-once delivery makes duplicates inevitable otherwise | 16.6 |
| 10 | Single beat per environment | Two beats double-fire every scheduled job | 18.6 |
| 11 | Automated backups + a verified restore drill | An untested backup is not a backup | 20.7 |
| 12 | Secrets out of source/images; field encryption of listed fields | A leaked secret or DB dump otherwise exposes everything | 17.6–17.7 |
| 13 | The pre-launch security review + launch checklist | The gate that prevents launching a known-unsafe system | 17.11, 20.9 |

What **may** be trimmed under pressure (with a Section 22 entry): the breadth of the ten reports, the depth of the custom tenant admin, the Import Center's saved-mapping polish, dashboard widget richness, and similar surface refinements — none of which touch the substrate above.

### 21.14 Milestone Acceptance Criteria

**Status: NORMATIVE.**

| # | Criterion | Verification |
|---|---|---|
| 1 | The milestone spine is M0->M1->M2->M2A->M3->M4->M5->M6->M7->M8, with M9+ post-MVP | guide review |
| 2 | The CI structural floor is built in M0, before any domain code | repo history + CI |
| 3 | The `Subscription` row is created from M1 (org creation), before M2A completes the enforcement layer | service test |
| 4 | M2A lands the full entitlement layer before any gated domain (M3+) is built | sequencing review |
| 5 | Each domain milestone (M3–M7) adds the `require_feature`/`enforce_limit` gates for its features | gate-matrix completeness |
| 6 | Every milestone's exit criteria map to the acceptance criteria of the sections it realizes | traceability review |
| 7 | A milestone is marked complete only when its exit criteria pass in CI | release process |
| 8 | The "NEVER cut" list (21.13) is honored: no item is descoped to hit a date | release review |
| 9 | Items trimmed under pressure have a Section 22 entry with an MVP accommodation note | Section 22 cross-check |

---

## Section 22 — Post-MVP Deferred Scope

### 22.1 Purpose and the Accommodation Rule

**Status: NORMATIVE.**

Section 22 is the authoritative catalog of everything deliberately deferred from the MVP. Every "post-MVP" reference anywhere in this guide resolves to an entry here. The rule is from Architectural Principle 11 and Section 3.4: **a deferred decision without a Section 22 entry is a prohibited implicit decision.** Each entry records three things:

1. **What** is deferred and to roughly which horizon.
2. **Why** it is out of MVP scope (not merely "not built yet" — the reasoned boundary).
3. **The MVP accommodation** — what the MVP already does so the later build is an addition, not a re-architecture. The accommodation is the load-bearing column: it is the difference between "deferred cleanly" and "deferred into future rework."

Horizons are indicative, not commitments: **post-MVP** (the next major thrust, typically the React portal era), **later** (a subsequent phase), **if-ever** (deferred indefinitely; recorded so the boundary is explicit). This section reconciles against the Section 3.3 exclusion list one-for-one, plus the deferrals introduced in later sections.

### 22.2 Front End and API

**Status: NORMATIVE.**

| # | Deferred | Horizon | Why deferred | MVP accommodation |
|---|---|---|---|---|
| 1 | **React tenant portal** | post-MVP | The MVP ships server-rendered to reach production faster without a SPA build; the portal is the headline next thrust | The entire service layer is surface-agnostic (Section 16.2); the internal DRF API is built now against the same services (Section 4.9); design tokens are framework-neutral (Section 14.9). The React portal is a new **adapter**, not a new backend (Section 16.10) |
| 2 | **Public / external API, webhooks, API tokens** | later | The MVP API is internal-only and session-authenticated; a public API needs token auth, rate plans, versioning guarantees, and abuse controls that are their own project | The API already has a versioned URL (`/api/v1/`), cursor pagination, an OpenAPI schema (Section 4.9), and shared-service enforcement — so the contract a public API would expose already exists internally |
| 3 | **Native mobile applications** | later | Native apps are a separate platform investment; the responsive server-rendered UI covers mobile-web use in the MVP | The design system is responsive to small screens (Section 14.5); the DRF API is the contract a native client would consume, identical to the React portal |

### 22.3 Subscription Billing and Payments

**Status: NORMATIVE.**

There are **two independent payment-processor deferrals**, kept distinct because they live in different domains (Section 7.14, Section 12.10).

| # | Deferred | Horizon | Why deferred | MVP accommodation |
|---|---|---|---|---|
| 4 | **SaaS payment processor + self-service subscription** (Stripe/Paddle; self-service signup, plan changes, add-on purchase, proration, failed-payment workflows, dunning) | post-MVP | Operator-managed plans let the product launch without billing-provider complexity, tax-on-SaaS handling, and subscription lifecycle automation | The full entitlement model exists and is operator-driven (Section 7.13); a processor adds a *self-service mutation surface* over the same `Subscription`/add-on records — the enforcement layer doesn't change. SaaS billing is already a separate domain from tenant invoicing (Section 7.14) |
| 5 | **Online customer payment collection** (charging a tenant's *customers'* cards via a processor) | later | The MVP records offline payments (cash/check/transfer/offline-card); collecting card payments online is a distinct integration with PCI scope | `Payment` already models methods and references; a processor adds new methods and a collection flow over the existing append-only payment/allocation model (Section 12.7–12.8) |
| 6 | **Refunds, credit notes, write-offs** | later | The MVP corrects via payment reversal/adjustment; formal credit instruments add their own numbering, tax, and accounting semantics | Payments and allocations are append-only with reversal rows (Section 12.8); credit notes extend the same reversal discipline rather than mutating history |

### 22.4 Identity and Access

**Status: NORMATIVE.**

| # | Deferred | Horizon | Why deferred | MVP accommodation |
|---|---|---|---|---|
| 7 | **SAML, SCIM, tenant-managed custom IdPs, IdP group→role mapping** | later | Enterprise SSO/provisioning is configuration-and-support-heavy; the MVP uses Auth0 with platform-managed connections | Auth0 already federates connections (Section 8.1); the canonical-user/`Auth0Identity` model is `sub`-keyed and IdP-agnostic (Section 8.3); adding a connection type doesn't change membership/RBAC |
| 8 | **Local password / local TOTP machinery** | if-ever | Auth0 owns all credential and MFA handling; a parallel local auth system would be redundant and a security liability (Section 8.18) | The `User` model deliberately has no password/TOTP fields; nothing to retrofit — this is a non-goal, recorded so it is not "added back" by habit |
| 9 | **Comprehensive single-logout** (terminating the Auth0 session globally, not just locally) | later | MVP logout is local-plus-best-effort against Auth0 (Section 8.16) | Logout already calls Auth0's logout endpoint best-effort; tightening to guaranteed global logout is a flow change, not a model change |
| 10 | **Ownership-transfer workflow** | later | The MVP has no "transfer ownership" flow; an admin re-invites and assigns the Owner role manually (Section 6.9) | The role/membership model already supports assigning Owner to another member; a transfer flow is UX over existing services |

### 22.5 Pricing, Tax, and Currency

**Status: NORMATIVE.**

| # | Deferred | Horizon | Why deferred | MVP accommodation |
|---|---|---|---|---|
| 11 | **Multi-currency invoicing within one org + FX sourcing** | later | One base currency per org keeps pricing/billing deterministic; FX adds rate sourcing, conversion timing, and reporting complexity | `PricingContext` and every money record carry `currency_code` (Section 5.2, 10.3.3) so the contract is forward-compatible; a currency modifier hook is reserved (Section 10.8) |
| 12 | **Multi-jurisdiction compound tax** (beyond one resolved rate per line) | later | The MVP resolves a single effective `TaxRate` per line per jurisdiction; compound/nested tax is jurisdiction-specific complexity | Tax is a modifier computing a separate amount (Section 10.12); `TaxJurisdiction`/`TaxRate` are effective-dated; compound tax extends the resolver/modifier without touching the pipeline |
| 13 | **One-off pricing strategy classes** (supplier-selection, rush, location, complexity as *strategies*) | if-ever | These are adjustments, not base calculations; modeling them as strategies would violate composition-over-proliferation (Section 3.1, 10.4) | They already exist as **resolvers/modifiers** (Section 10.5, 10.8); this entry records that they must never become strategies |

### 22.6 Operations, Inventory, and Catalog

**Status: NORMATIVE.**

| # | Deferred | Horizon | Why deferred | MVP accommodation |
|---|---|---|---|---|
| 14 | **Inventory tracking / stock deduction** | later | Fulfillment in the MVP is order-driven (work/build/purchase), not stock-driven; inventory is a domain of its own | Purchase receipts and build components already track quantities (Section 11.4–11.5); inventory would consume those signals rather than replace them |
| 15 | **Recurring service templates, route optimization, dispatch automation** | later | The MVP schedules and assigns work orders manually; automation and routing are optimization layers | Work orders carry scheduling/assignment fields and location (Section 11.3); automation would drive the same fields through new services |
| 16 | **Customer-facing public quote acceptance + native e-signature** | later | MVP acceptance is operator-performed inside the portal; a public accept-by-link flow needs unauthenticated-surface security and e-sign integration | The quote/acceptance services are surface-agnostic (Section 9.5); a public flow is a new adapter calling `accept_quote`, plus a signed-link mechanism analogous to the handoff token |
| 17 | **Inbound email sync / mailbox threading** | later | The MVP logs communications manually and sends outbound only; inbound sync needs mailbox integration and threading | `Communication` already reserves the `INBOUND` direction and `provider_message_id` (Section 9.7); sync populates fields that already exist |

### 22.7 Reporting and Analytics

**Status: NORMATIVE.**

| # | Deferred | Horizon | Why deferred | MVP accommodation |
|---|---|---|---|---|
| 18 | **Ad hoc / custom report builder, scheduled delivery, BI export, dashboard KPI engine** | later | The MVP ships ten fixed reports + CSV export; a query/builder surface and scheduling are a separate analytics investment | The report layer reads through normal tenant-scoped querysets and runs on the `reports` queue (Section 12.11); new reports/builders add to the same surface and respect the same RML scope and entitlement gate (`advanced_reporting`) |

### 22.8 Data Model and Tenancy

**Status: NORMATIVE.**

| # | Deferred | Horizon | Why deferred | MVP accommodation |
|---|---|---|---|---|
| 19 | **Schema-per-tenant deployment** | if-ever | Row-based tenancy with enforced isolation is sufficient and far simpler to operate; schema-per-tenant is recorded as a non-path | All tenant access already funnels through `TenantManager`/`for_org` (Section 5.4); the isolation guarantee is independent of the storage strategy, but the MVP commits to row-based (Section 5.1) |
| 20 | **Parent/child client account hierarchy** | later | The MVP models flat clients; hierarchical accounts add roll-up billing/reporting semantics | `Client` is a clean entity with merge semantics (Section 9.3); a hierarchy adds a typed parent link (never a `GenericForeignKey`, Section 9.8) over the existing model |

### 22.9 Accounting Integration

**Status: NORMATIVE.**

| # | Deferred | Horizon | Why deferred | MVP accommodation |
|---|---|---|---|---|
| 21 | **Concrete accounting adapters** (QuickBooks / Xero / NetSuite) | post-MVP | The MVP ships the adapter interface and a Noop adapter; concrete integrations are each their own auth + mapping project | Sync is outbox-driven through the `AccountingAdapter` protocol (Section 12.9); a concrete adapter registers against the existing boundary and changes **no** billing service-layer code |

### 22.10 Infrastructure and Scale

**Status: NORMATIVE.**

| # | Deferred | Horizon | Why deferred | MVP accommodation |
|---|---|---|---|---|
| 22 | **Kubernetes + the scalability appendix** (Helm, ingress controllers, cert-manager, HPA, cluster autoscaling, service mesh, sealed secrets, K8s migration Jobs, K8s beat-singleton leases, blue-green/canary) | later | The Docker/DigitalOcean deployment is sufficient for MVP scale; cluster orchestration is a scale-out investment, not a launch requirement | The web/worker tiers are already stateless and horizontally scalable; the outbox uses `SKIP LOCKED`; the single-beat constraint is explicit and lease-able later (Sections 18.3, 18.6, 20.11). The transition does not re-architect the application |
| 23 | **PostgreSQL read replicas / multi-region** | later | A single managed primary with pgBouncer covers MVP load; replicas/multi-region add routing and consistency complexity | Reads already go through tenant-scoped querysets that a replica router could target without service changes (Section 20.11) |

### 22.11 Reconciliation Against the Exclusion List

**Status: INFORMATIVE.**

Every bullet in the Section 3.3 exclusion list maps to a numbered entry above, confirming the catalog is complete:

```text
React tenant portal                              → #1
SaaS payment processor / self-service            → #4
Public API / webhooks / tokens                   → #2
Kubernetes / scalability appendix                → #22
Multi-currency / FX                              → #11
Refunds / credit notes / write-offs              → #6
Inventory / stock deduction                      → #14
Concrete accounting adapters                     → #21
Inbound email sync / threading                   → #17
Public quote acceptance / e-signature            → #16
Native mobile                                    → #3
Schema-per-tenant                                → #19
Parent/child client hierarchy                    → #20
Custom report builder / scheduling / BI / KPIs   → #18
Recurring templates / routing / dispatch auto    → #15
SAML / SCIM / custom IdPs / group mapping        → #7
Local password / TOTP                            → #8
One-off pricing strategy classes                 → #13
```

Deferrals introduced in later sections and not in the 3.3 list — online customer payment collection (#5), ownership transfer (#10), comprehensive single-logout (#9), multi-jurisdiction compound tax (#12), read replicas / multi-region (#23) — are catalogued above so no "post-MVP" reference anywhere in the guide is left without an entry.

### 22.12 Acceptance Criteria

**Status: NORMATIVE.**

| # | Criterion | Verification |
|---|---|---|
| 1 | Every "post-MVP"/"later"/"if-ever" reference in the guide resolves to a Section 22 entry | traceability review |
| 2 | Every Section 3.3 exclusion bullet maps to a numbered entry (22.11) | cross-reference review |
| 3 | Each entry records what, why, and the MVP accommodation | section review |
| 4 | The two payment-processor deferrals (SaaS #4, customer-collection #5) are distinct entries | review |
| 5 | Each accommodation names the concrete MVP artifact that makes the later build an addition, not a rewrite | review |
| 6 | No deferred item lacks an entry (no prohibited implicit decisions — Principle 11) | architecture review |
| 7 | "If-ever" entries (local auth #8, schema-per-tenant #19, one-off strategies #13) are recorded as explicit non-paths | review |

---

