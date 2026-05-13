# MyPipelineHero CRM — Technical Development Guide

**Version:** 0.7 (revised — root-domain landing page, Phase 1 custom-admin/testing posture, shared design assets, Docker/DigitalOcean deployment, OAuth/OIDC authentication, simplified pricing architecture, normalized project structure)

**Status:** Consolidated working draft — revised sections incorporated

**Authority:** This guide supersedes both `mph_requirements.md` and `pricing_engine_strategy_appendix.md` where conflicts arise. The pricing simplification recommendations supersede older pricing strategy catalogs where conflicts arise. Order of authority: (1) this guide, (2) pricing simplification recommendations, (3) appendix, (4) baseline.

> **Revision note:** This version incorporates the revised v1 posture for a custom root-domain landing page, root-domain authentication entrypoint, Phase 1 custom-admin and tenant-template development workflow, shared CSS/design tokens reused by Phase 2 React, Docker/DigitalOcean deployment, OAuth/OIDC through Django/django-allauth, local/trusted-provider MFA, non-Kubernetes operations, the simplified 7-strategy pricing architecture, and the normalized `frontend/` + `backend/apps/...` project structure.

---

## Table of Contents

- [MyPipelineHero CRM — Technical Development Guide](#mypipelinehero-crm--technical-development-guide)
  - [Table of Contents](#table-of-contents)
  - [Process History](#process-history)
  - [Part FM — Front Matter](#part-fm--front-matter)
  - [Part A — Foundations](#part-a--foundations)
  - [Part B — Tenancy, Identity, and Authorization](#part-b--tenancy-identity-and-authorization)
  - [Part C — Domain Model and State Machines](#part-c--domain-model-and-state-machines)
  - [Part D — Commercial Workflow](#part-d--commercial-workflow)
  - [Part E — Catalog and Operations](#part-e--catalog-and-operations)
  - [Part F — Billing](#part-f--billing)
  - [Part G — Cross-Cutting Concerns](#part-g--cross-cutting-concerns)
  - [Part H — Frontend](#part-h--frontend)
  - [Part I — Quality, Operations, Delivery](#part-i--quality-operations-delivery)
  - [Part J — Development Phases and Milestones](#part-j--development-phases-and-milestones)
  - [Part K — Deferred / Out-of-v1 Catalog](#part-k--deferred--out-of-v1-catalog)

---

## Process History

This section captures the reconciliation, conflict resolution, and outline decisions that shaped the guide. It is INFORMATIVE and is preserved for traceability.

### Part 1 — Document Reconciliation

The reconciled v1 spec is the **baseline document, with the pricing simplification recommendations superseding the older appendix on pricing matters, plus user answers superseding both where they conflict.** Supersession order, top to bottom: user answers → this guide → pricing simplification recommendations → older appendix → baseline.

| # | What's superseded | What now applies | Source |
| --- | --- | --- | --- |
| 1 | Baseline §13.1 "three pricing strategies for v1" and older appendix strategy sprawl | Seven reusable base strategies plus resolvers/modifiers are in v1 | Pricing simplification recommendations |
| 2 | Baseline §13.4 "future extensibility" list (labor formulas, tiered pricing, bundles, customer-specific lists) | All in v1 | Same |
| 3 | Baseline §22.3 PricingRule shape | Appendix §9.1 PricingRule shape (richer fields, effective dates) | Same |
| 4 | Baseline §17.4 "credit notes, refunds, write-offs out of scope" | Confirmed still out of scope | Baseline holds |
| 5 | Baseline §10.4 default roles | Augmented to add pricing-approval-relevant capabilities | Cascade from #1 |
| 6 | Baseline §22 data model | Adds: PriceList, PriceListItem, ClientContractPricing, LaborRateCard, LaborRateCardLine, PricingApproval, PromotionCampaign, CustomerSegment, BundleDefinition+lines | Cascade from #1 |
| 7 | Baseline §23 app layout | Confirmed as written — separate Django apps for each sub-domain | User answer |
| 8 | Baseline frontend posture (Bootstrap mention in §2.5) | Tailwind for tenant portal | User answer |
| 9 | Baseline §19.2 "HTMX optional, case-by-case" | HTMX is the global default for tenant-portal interactivity in Phase 1 | User answer |
| 10 | Baseline static asset strategy | django-vite + Tailwind + ESM | User answer |
| 11 | Baseline §24 environment list | Adds: staging, demo/sandbox alongside dev/test/prod | User answer |
| 12 | Baseline §28 backup posture | Adds: production→staging anonymization pipeline | Cascade |
| 13 | Baseline ID strategy (unstated) | UUID v7 for org-facing entities, BigInt for AuditEvent / PricingSnapshot / high-volume internal | User answer |
| 14 | Baseline §17.4 currency posture | Confirmed: single currency per org; FX deferred; modifier hooks in place | User answer |
| 15 | Implicit auth posture | 2FA required at v1 launch | User answer |
| 16 | Baseline §8 password posture | Minimum length, breached-password check (HIBP-style), rotation policy required | User answer |
| 17 | Baseline §27 testing | Property-based testing (Hypothesis) for state machines and pricing engine; factory_boy + faker for fixtures | User answer |
| 18 | Baseline migration posture | Migrate-before-deploy required; deployment must support backward-compatible migrations | User answer |
| 19 | Baseline Phase 2 API library (deferred) | DRF confirmed for v1 internal API surface | User answer |
| 20 | Baseline §11.4 "one SalesOrderLine = one WorkOrder" UX | Manual rep responsibility — no auto-split. UI surfaces a hint but doesn't enforce | User answer |
| 21 | Baseline §6.2 quote retraction successor | Successor DRAFT inherits all lines from retracted SENT version | User answer |
| 22 | Baseline §9.5 multi-tenant browser sessions | Soft warning UX when opening a second tenant in same browser | User answer |
| 23 | Baseline tenant offboarding (unstated) | Tenant data export and deletion required at v1 | User answer |
| 24 | Baseline support landing (§9.3 implies) | Support users land on platform console after central login | User answer |
| 25 | Baseline audit retention (§26.1A "TBD") | 7 years for state-change events, 1 year for read-access events | User answer |

### Part 2 — Conflict Resolution Confirmation

| # | Conflict | Resolution |
| --- | --- | --- |
| 1 | v1 pricing strategy count | RESOLVED — v1 ships 7 base strategies plus resolvers/modifiers, not the older full strategy catalog. |
| 2 | Pricing precedence depth | RESOLVED — v1 uses a resolver + base strategy + modifier + approval pipeline. Older 23-step wording is superseded. |
| 3 | Markup vs. target margin | RESOLVED by cascade — both ship in v1. |
| 4 | PricingRule data model | RESOLVED — appendix §9.1 shape wins. |
| 5 | PricingApproval as v1 concern | RESOLVED by cascade — appendix §9.7 PricingApproval ships in v1. |
| 6 | Engine version semantics | RESOLVED — major bumps when deterministic precedence pipeline changes order or any modifier's math changes; minor bumps when new strategies/modifiers are added (additive only). v1 ships as `"1.0"`. |
| 7 | Customer-specific pricing in v1 | RESOLVED by cascade — ClientContractPricing ships in v1. |
| 8 | Tax modeling | RESOLVED — per-jurisdiction tax in v1 (location-based pricing in v1 → per-jurisdiction tax in v1). |
| 9 | Bundle / package handling | RESOLVED by cascade — bundle configuration modes are implemented through `strategy.component_sum`, `strategy.fixed_price`, component-level pricing, and snapshots; they are not separate base strategies. |
| 10 | Location-based pricing vs. access scope | RESOLVED by cascade — RML serves both purposes in v1. |

### Part 3 — Outline Decisions

The full guide outline is structured as:

- **Front Matter (FM):** Document purpose, conventions, glossary
- **Part A:** Foundations (vision, architectural principles, topology, phasing)
- **Part B:** Tenancy, Identity, and Authorization
- **Part C:** Domain Model and State Machines
- **Part D:** Commercial Workflow
- **Part E:** Catalog and Operations (including full pricing engine)
- **Part F:** Billing
- **Part G:** Cross-Cutting Concerns
- **Part H:** Frontend (Phase 1 + Phase 2 + DRF API) — pending expansion
- **Part I:** Quality, Operations, Delivery — pending expansion
- **Part J:** Development Phases and Milestones (M0–M8) — pending expansion
- **Part K:** Deferred / Out-of-v1 Catalog — pending expansion

Milestones M0–M8:

| Milestone | Deliverable |
| --- | --- |
| M0 — Foundation | Docker compose, Django skeleton, root landing page, shared CSS assets, custom user model, seed-v1, CI |
| M1 — Tenancy + Identity + Auth | Org/Membership/Role/Capability, RML, login landing, handoff, 2FA, support impersonation |
| M2 — RBAC + Audit | Three-layer enforcement, AuditEvent partitioned, capability-coverage CI test, exception taxonomy, outbox + worker, beat |
| M3 — Catalog + Pricing Engine + Snapshots | Service/Product/RawMaterial/Supplier, BOM versioning, PricingRule/PriceList/Contract/RateCard/Segment/Promotion/Bundle, 7 base strategies, cost/input resolvers, reusable modifiers, PricingApproval, snapshots, replay |
| M4 — CRM Pipeline | Lead, Quote container + versions + lines, retraction with inheritance, acceptance with client resolution, Tasks, Communications |
| M5 — Fulfillment | WorkOrder, PurchaseOrder + Allocation + Receipt, BuildOrder + BOM snapshot + Labor + variance, QA review |
| M6 — Billing + Reporting | Invoice, InvoiceLine, Payment + Allocation + Reversal, tax modifier, fixed reports + ReportExportJob, NoopAccountingAdapter |
| M7 — Custom Tenant Admin, Domain Admin Workflows + Data Lifecycle | Custom tenant admin site, domain admin workflows, tenant-facing template coverage, data export, offboarding/deletion, audit retention prune |
| M8 — Production Readiness | Backups + restore drill, anonymization pipeline, RPO/RTO, runbooks, observability dashboards, security review, load test, Docker/DigitalOcean deploy, pgBouncer if needed |
| M9 (post-v1) — Phase 2 React Portal | DRF API surface, React tenant portal, Phase 1 retirement |

---

## Part FM — Front Matter

### FM.1 Document Purpose, Audience, and Status

**Status: NORMATIVE.**

This document is the canonical engineering reference for the MyPipelineHero v1 build. It is the single source of truth for architectural decisions, domain shapes, state machines, RBAC enforcement, pricing engine behavior, async semantics, and operational posture. Where it conflicts with prior documents, this guide wins.

#### FM.1.1 Audience

- **Application engineers** building Phase 1 (server-rendered Django) and Phase 2 (DRF + React) surfaces.
- **Platform / infrastructure engineers** operating the Docker/DigitalOcean deployment, Postgres, Redis, object storage, and observability stack.
- **QA engineers** designing and maintaining the test suite (unit, service, integration, property-based, mutation, contract).
- **Support engineers** using the platform console and impersonation tooling.
- **Security reviewers** auditing tenant isolation, authorization, audit, and data-handling controls.
- **Product/engineering managers** scoping milestones and tracking exit criteria.

#### FM.1.2 Versioning and change control

The guide is versioned with semantic-version-like tags (`<major>.<minor>`):

- **Minor** version bumps when sections are added or expanded without changing prior commitments.
- **Major** version bumps when a NORMATIVE rule changes or a previously-shipped behavior is revised.

Every guide change MUST go through pull-request review with at least one engineering reviewer and one product-or-architecture reviewer. Drive-by edits to NORMATIVE sections are prohibited.

A `CHANGELOG.md` adjacent to this file records all changes with date, author, version, and one-line summary.

#### FM.1.3 Authority labels

Every section header carries an authority label:

- **NORMATIVE** — implementation MUST conform. Deviation requires guide PR.
- **INFORMATIVE** — context, rationale, and worked examples. May be revised without a guide PR.

Tables, code skeletons, and field-level model definitions inside NORMATIVE sections are themselves NORMATIVE unless explicitly marked otherwise.

### FM.2 How to Read This Guide

**Status: INFORMATIVE.**

#### FM.2.1 Reading paths

- **New engineer onboarding:** read FM, A, B in order; skim C and D to locate domains relevant to your first ticket.
- **Building a new feature in an existing domain:** locate the domain in C/D/E/F; cross-reference G (cross-cutting) and I (testing/deploy).
- **Investigating a production incident:** start at G (observability), then locate the affected domain.
- **Reviewing security posture:** B.6, B.7, G.5, G.6, G.7.
- **Pricing-related work:** E.5–E.10 are the heart; B.6 covers approval capabilities; F.4 covers tax integration.
- **Phase 2 API work:** H.6 is the entry point; service-layer rules in G.1 govern the contract boundary.

#### FM.2.2 Glossary (Authoritative term registry)

| Term | Meaning |
| --- | --- |
| **Tenant** | A customer organization on the platform. Synonym for Organization in commercial context. |
| **Organization** | The Django model representing a tenant. Tenant-owned records reference an Organization via FK. |
| **Membership** | The relationship of a User to an Organization, carrying role assignments, scope assignments, and status. |
| **User** | A globally unique identity, identified by email. May have memberships in zero or more organizations. |
| **System User** | A single platform-level User row with `is_system=True`. Owns all automated state transitions. |
| **Support User** | A platform user with `is_staff=True` (and optionally `is_superuser=True`) authorized to enter tenant contexts under controlled, audited conditions. |
| **Capability** | A platform-defined permission code (e.g., `quotes.send`). Codes follow `{domain}.{resource}.{action}`. Tenants may not create custom codes in v1. |
| **Role** | A named collection of capabilities. Default roles are platform-seeded read-only templates; tenants may define custom roles by composing existing capabilities. |
| **Operating Scope** | A Region / Market / Location restriction on a Membership that intersects all queryset and object access for that membership. |
| **Region / Market / Location (RML)** | Three-level operating scope hierarchy within an organization. Market belongs to one Region; Location belongs to one Market. Also a pricing input as of the appendix supersession. |
| **Strategy** | A reusable base pricing calculation (e.g., `strategy.cost_plus`). Pure function; does not access the database. |
| **Modifier** | A reusable adjustment applied to a strategy's output (e.g., `modifier.location`, `modifier.line_discount`). |
| **PricingContext** | An immutable input bundle to a strategy. Constructed by `PricingContextBuilder`, which coordinates database-backed resolver inputs. |
| **PricingResult** | An immutable output bundle from a strategy + modifier pipeline. Persisted as a `PricingSnapshot`. |
| **PricingSnapshot** | The persisted record of a PricingResult. Written once at quote time. Never mutated. Replayable via stored engine_version. |
| **Outbox** | A transactional table that durably publishes side-effect intents. Workers consume outbox rows idempotently. |
| **Handoff** | The signed, single-use, 60-second token mechanism that carries authentication from the root domain to a tenant subdomain. |
| **Audit Event** | An append-only record of a state-changing or sensitive action. Schema-versioned. Retained per the retention table in G.5. |
| **Service Layer** | The set of plain-Python orchestration functions in `apps/<domain>/services/` that own all state-changing workflow logic. |
| **Tenant-local session** | The Django session established on a tenant subdomain after handoff completion. Independent of the root-domain session. |
| **Sensitive Action** | An action requiring re-authentication regardless of session age. Enumerated in B.4. |
| **Engine Version** | The `<major>.<minor>` string identifying the pricing pipeline contract. v1 ships as `"1.0"`. |

### FM.3 Document Conventions

**Status: NORMATIVE.**

#### FM.3.1 RFC 2119 keywords

The keywords **MUST**, **MUST NOT**, **SHOULD**, **SHOULD NOT**, **MAY**, and **REQUIRED** carry their RFC 2119 meanings.

- **MUST** / **REQUIRED**: violation is a defect.
- **MUST NOT**: violation is a defect.
- **SHOULD**: deviation requires a documented justification in code comments or PR description.
- **SHOULD NOT**: same as SHOULD, inverted.
- **MAY**: optional behavior; choose by context.

#### FM.3.2 State machine table format

State machine tables in C.2 follow this column order:

| From | To | Trigger Event | Actor | Side Effects / Notes |

- **From** / **To**: state names in the canonical CamelCase used in the model's `Status` enum.
- **Trigger Event**: the snake_case service function name.
- **Actor**: human role or `System` for automated transitions.
- **Side Effects / Notes**: side-effecting workflows, required reasons, downstream entity creation.

#### FM.3.3 RBAC enforcement matrix format

| View / Action | Queryset Scope | View Capability | Object Check | Audit Event |

Each row defines all four enforcement layers for a single view or action. No layer substitutes for another.

#### FM.3.4 Code skeleton conventions

```python
# NORMATIVE: signature shape
def accept_quote(
    *,
    organization_id: UUID,
    actor_id: UUID,
    quote_version_id: UUID,
    client_resolution: ClientResolution,
    idempotency_key: str,
) -> QuoteAcceptanceResult:
    ...
```

Keyword-only arguments (`*,`) are REQUIRED on all service-layer functions. Positional arguments are PROHIBITED on service-layer functions.

#### FM.3.6 Field-level model definitions

```text
ModelName
  field_name: TYPE [, modifier ...]              -- description
```

Common modifiers: `pk`, `null`, `unique`, `unique_together(...)`, `index`, `partial_index(condition)`, `default(value)`, `fk -> Model`, `fk -> Model on_delete=PROTECT`, `audit_masked`.

---

## Part A — Foundations

### A.1 Product Vision and v1 Scope

**Status: NORMATIVE.**

#### A.1.1 Vision

MyPipelineHero is a multi-tenant CRM and operations platform for organizations that sell a mix of services, resold products, and in-house manufactured products. The platform spans the full commercial lifecycle from lead intake through fulfillment to invoicing and payment, with a pricing engine, regional/market/location operating-scope authorization, and immutable commercial history.

The lifecycle:

```text
Lead → Quote → Acceptance → Sales Order → Fulfillment Artifacts → Invoice → Payment
                                          (Work Order / Purchase Order / Build Order)
```

#### A.1.2 v1 scope is production-ready, not infrastructure-heavy

v1 is a CRM plus a CPQ-capable pricing foundation. The pricing engine MUST be flexible enough to support services, resale products, manufactured products, bundles, recurring plans, discounts, approvals, tax, and immutable quote-time snapshots.

The v1 pricing architecture MUST NOT create one pricing strategy class for every named business scenario. Pricing behavior MUST be composed from:

```text
7 base pricing strategies
+ cost/input resolvers
+ reusable modifiers
+ approval policies
+ billing schedules
+ immutable pricing snapshots
```

Infrastructure MUST be production-ready but intentionally simple. v1 deploys without Kubernetes. Local development uses Docker Compose. Staging, demo, and production deploy to DigitalOcean using Docker images and Docker Compose or equivalent host-level container orchestration.

Kubernetes, Helm, ingress controllers, HPA, cluster autoscaling, service mesh, and Kubernetes-native secret tooling are deferred to the future scalability appendix.

#### A.1.3 What v1 ships

- Multi-tenant identity, authentication with OAuth/OIDC support, local or trusted-provider MFA, authorization with RBAC + RML scope, session handoff, and support impersonation.
- Lead, Quote with versioning, Client, Sales Order, Work Order, Purchase Order, Build Order, Invoice, Payment, Task, Communication, and Document Attachment domains.
- Pricing engine based on 7 reusable base strategies:
  - `strategy.fixed_price`
  - `strategy.cost_plus`
  - `strategy.target_margin`
  - `strategy.rate_card`
  - `strategy.tiered`
  - `strategy.component_sum`
  - `strategy.recurring_plan`
- Cost/input resolvers for catalog prices, manual cost, selected supplier cost, BOM version cost, manufactured build-up cost, and labor rate cards.
- Reusable pricing modifiers for customer contracts, customer segment, location, service zone, complexity, rush, after-hours, promotion, line discount, quote discount, minimum charge, trip fee, manual override, floor margin, tax, and rounding.
- PricingApproval workflow for manual overrides, excessive discounts, below-floor pricing, below-margin pricing, and contract deviations.
- Immutable PricingSnapshot records with engine version, strategy code, cost source, base inputs, modifier deltas, approval state, tax, rounding, final totals, gross profit, and margin.
- PriceList, PriceListItem, ClientContractPricing, LaborRateCard/LaborRateCardLine, CustomerSegment, PromotionCampaign, BundleDefinition/BundleComponent, TaxJurisdiction/TaxRate.
- Service, Product, RawMaterial, Supplier, SupplierProduct, BOM, BOMVersion, and BOMLine catalog models.
- BOM with effective-from versioning, immutable build snapshots, labor tracking, and variance reporting.
- Tenant data export and deletion.
- Append-only AuditEvent with 7-year retention for state-changing events and 1-year retention for read-access events.
- Outbox pattern, idempotent Celery workers, and a single Celery beat scheduler per environment.
- Custom login landing page on root domain, signed-token cross-subdomain handoff, and tenant-local sessions.
- Server-rendered Phase 1 tenant portal using Django templates, Tailwind, django-vite, and HTMX as the default interactivity layer.
- Custom platform admin site for support engineers and custom tenant admin site for organization administrators.
- Fixed reports and async CSV exports.
- Docker-based production deployment on DigitalOcean.
- PostgreSQL, Redis, reverse proxy, Celery worker, Celery beat, optional pgBouncer, object storage, automated backups, restore drill, production-to-staging anonymization pipeline, RPO 1h, and RTO 4h.
- Observability: structured JSON logging, Sentry-equivalent error monitoring, OpenTelemetry SDK with logging exporter wired.
- DRF-based internal API as Phase 2 prerequisite.

#### A.1.4 What v1 does NOT ship

- Kubernetes deployment.
- Helm charts.
- Kubernetes ingress controllers.
- Kubernetes-native sealed secrets.
- Kubernetes Jobs for migrations.
- Kubernetes Lease-based Celery beat singleton.
- Horizontal Pod Autoscaling.
- Multi-currency invoicing within a single org.
- Refunds, credit notes, write-offs.
- Customer-facing public quote acceptance.
- Inbound email synchronization or mailbox threading.
- Native mobile applications.
- Schema-per-tenant deployment.
- Public/external API.
- Shipment/delivery tracking as a domain.
- Ad hoc report builder or saved custom-report designer.
- Native e-signature platform integration.
- Native payment processor as system of record.
- Advanced recurring service templates, route optimization, or advanced dispatch.
- Parent/child client account hierarchy.
- OpenTelemetry metrics and traces export beyond no-op SDK wiring.
- Public marketing site at root domain.
- One-off strategy classes for supplier selection, rush pricing, location adjustment, complexity adjustment, or other behavior better represented as resolvers or modifiers.
- Tenant-managed custom identity providers.
- SAML.
- SCIM.
- Provider group-to-role mapping.
- Passwordless magic links.
- Passkeys-only login.

### A.2 Architectural Principles

**Status: NORMATIVE.**

These ten principles are decision rules. When two implementation paths conflict, prefer the path that better honors the principle. In code review, citing a principle by number is sufficient justification to block a PR.

#### A.2.1 Tenant safety over convenience

No cross-tenant data leakage, ever, under any circumstance, including during emergency support work. Convenience patterns that weaken isolation (shared querysets without `for_org`, GenericForeignKey, raw SQL bypassing TenantManager) are prohibited.

#### A.2.2 Commercial immutability is auditable history

Sent quotes, accepted pricing, generated orders, posted payments, and audit events MUST be reproducible from stored data without destructive in-place edits. Edits to commercial records require explicit reversal, adjustment, or successor-version workflows that preserve the prior state.

#### A.2.3 The service layer is the authoritative orchestration boundary

Every state-changing workflow MUST execute through a function in `apps/<domain>/services/`. Views, forms, admin actions, Celery tasks, DRF endpoints, and signal handlers MUST call services rather than implementing parallel workflow logic. Models MAY enforce local invariants but MUST NOT orchestrate multi-object workflows or emit cross-domain side effects in `save()` or signal handlers.

#### A.2.4 Idempotency is required for async

Every Celery task that creates or transitions state records MUST be safe to retry without producing duplicate business artifacts. Side effects MUST be published through the outbox before worker pickup. Idempotency keys MUST be deterministic from input arguments.

#### A.2.5 Audit is append-only and complete

Every state transition, every authentication event, every authorization grant change, every impersonation start/end, and every pricing override or approval MUST emit an AuditEvent. Audit rows are never updated or deleted within retention. Audit attribution carries both the acting user and the on-behalf-of user where impersonation applies.

#### A.2.6 Typed links over polymorphic relations

Cross-domain links (a Task linked to a Quote, a Communication linked to a Client) MUST use typed link tables with explicit foreign keys and CHECK constraints. `GenericForeignKey` and equivalent polymorphic patterns are PROHIBITED for primary business-object linkage.

#### A.2.7 State machines are authoritative

The state transition tables in C.2 are the contract. Implementation MUST NOT add, remove, or reorder states or transitions without amending C.2 in the same PR. Property-based tests MUST verify that no transition exists in code without a corresponding row.

#### A.2.8 Observability by default

Every service-layer function operates inside a structured logging context with a correlation ID. Errors emit to the error monitoring system with full context. Metrics emit for request rate, error rate, queue depth, and task duration. Production debugging without these is unacceptable.

#### A.2.9 Explicit over clever

Magic (signal-driven cascades, metaclass autodiscovery, `**kwargs` plumbing through service layers, monkey-patches) is prohibited in domain code. If a junior engineer reading the code cannot trace what happens, the code is wrong, not the engineer.

#### A.2.10 Deferred decisions are documented, not implicit

Every decision marked "deferred" or "future-friendly" MUST appear in K.1 with a one-line v1 accommodation note. "We'll figure it out later" is not a deferred decision; it's an implicit decision, and implicit decisions are prohibited.

### A.3 High-Level System Topology

**Status: NORMATIVE.**

#### A.3.1 Topology diagram

```text
                                  ┌─────────────────────────────┐
                                  │ DNS                         │
                                  │ mypipelinehero.com          │
                                  │ *.mypipelinehero.com        │
                                  └──────────────┬──────────────┘
                                                 │
                                  ┌──────────────▼──────────────┐
                                  │ Reverse Proxy               │
                                  │ Nginx or Caddy              │
                                  │ TLS termination             │
                                  │ HTTP → HTTPS redirect       │
                                  │ Security headers            │
                                  └──────────────┬──────────────┘
                                                 │
                       ┌─────────────────────────┼─────────────────────────┐
                       │                         │                         │
                ┌──────▼──────┐          ┌───────▼──────┐          ┌──────▼─────┐
                │ root domain │          │ {slug}.tenant│          │ platform   │
                │ login       │          │ subdomain    │          │ console    │
                └──────┬──────┘          └───────┬──────┘          └──────┬─────┘
                       │                         │                         │
                       └─────────────────────────┼─────────────────────────┘
                                                 │
                                  ┌──────────────▼──────────────┐
                                  │ Django web container        │
                                  │ Gunicorn                    │
                                  │ Stateless                   │
                                  └──────────────┬──────────────┘
                                                 │
              ┌──────────────────┬───────────────┼───────────────┬──────────────────┐
              │                  │               │               │                  │
       ┌──────▼──────┐    ┌──────▼──────┐ ┌──────▼─────┐  ┌─────▼──────┐    ┌──────▼──────┐
       │ pgBouncer   │    │ Redis       │ │ Object     │  │ Outbox     │    │ Structured  │
       │ optional    │    │ broker/cache│ │ storage    │  │ table in   │    │ JSON logs   │
       │ non-dev     │    │ handoff     │ │ S3-compatible││ PostgreSQL │    │ → log sink  │
       └──────┬──────┘    └─────────────┘ └────────────┘  └────────────┘    └─────────────┘
              │
       ┌──────▼──────┐
       │ PostgreSQL  │
       │ managed or  │
       │ self-hosted │
       └─────────────┘

       Async tier:
       ┌─────────────────┐        ┌──────────────────┐
       │ Celery worker   │        │ Celery beat      │
       │ container       │        │ container        │
       │ queues:         │        │ exactly one per  │
       │ critical/default│        │ environment      │
       │ bulk/reports    │        └────────┬─────────┘
       └────────┬────────┘                 │
                │                          │
                └──────────┬───────────────┘
                           ▼
                      Redis broker
                           │
                           ▼
                    PostgreSQL outbox
```

#### A.3.2 Component requirements

**DNS.** DNS MUST route the apex/root domain and wildcard tenant subdomains to the production reverse proxy.

**Reverse proxy.** Nginx or Caddy MUST terminate TLS, redirect HTTP to HTTPS, route both root-domain and tenant-subdomain traffic to the Django web container, and apply baseline security headers. TLS certificates MAY be provisioned through Let’s Encrypt, DigitalOcean-managed certificates, or an equivalent managed certificate flow.

**Django web tier.** Django runs behind Gunicorn in a container. The web container MUST be stateless. It MUST NOT execute long-running domain work inline. Long-running work MUST go through the outbox and Celery worker tier.

**Worker tier.** Celery workers run in one or more separate containers. v1 MAY begin with one worker process consuming all queues. The worker configuration MUST preserve logical queue separation:

| Queue | Purpose | Worker posture |
| --- | --- | --- |
| `critical` | Auth-related work such as invite, password reset, and MFA notifications | Low latency |
| `default` | General domain async work | Normal |
| `bulk` | High-volume notification/reminder work | Batch-friendly |
| `reports` | Long-running reports and exports | Lower concurrency |

**Beat tier.** Exactly one Celery beat scheduler MUST run per environment. Multiple beat schedulers are PROHIBITED. Beat-triggered jobs MUST be idempotent and SHOULD use an application-level Redis or PostgreSQL lock when duplicate execution would be harmful.

**PostgreSQL.** Production SHOULD use DigitalOcean Managed PostgreSQL unless cost or operational constraints require self-hosting. If PostgreSQL is self-hosted, it MUST use durable volumes, automated backups, WAL/PITR-equivalent recovery, and documented restore procedures.

**pgBouncer.** pgBouncer SHOULD be used in staging and production once application connection count requires pooling. It MAY run as a Docker Compose service or be provided by the database platform. Transaction pooling is the default mode.

**Redis.** Redis is used for Celery broker, cache, org-slug cache, handoff token store, rate-limit counters, and optional distributed locks. Production SHOULD use managed Redis when feasible.

**Object storage.** S3-compatible object storage MUST be used outside local development. Object keys MUST include environment and organization prefix:

```text
{environment}/orgs/{org_id}/{domain}/{record_id}/{filename}
```

**Configuration.** Runtime configuration MUST come from environment variables. Secrets MUST be managed outside source control.

#### A.3.3 Environment separation

The application MUST support the following environments:

| Environment | Settings module | Purpose |
| --- | --- | --- |
| `dev` | `config.settings.dev` | Local development |
| `test` | `config.settings.test` | Automated tests |
| `staging` | `config.settings.staging` | Production-like validation |
| `demo` | `config.settings.demo` | Demo/sandbox tenant environment |
| `prod` | `config.settings.prod` | Live tenant environment |

Settings modules:

```text
config/settings/base.py
config/settings/dev.py
config/settings/test.py
config/settings/staging.py
config/settings/demo.py
config/settings/prod.py
```

`production.py` and other legacy names SHOULD NOT be used unless maintained as explicit compatibility aliases. New documentation and deploy scripts MUST use `prod.py` and `demo.py`.

#### A.3.4 Cross-domain data flow: handoff

```text
1. User → POST /login → root domain Django web container
2. Django web → PostgreSQL validates credentials and fetches memberships
3. Django web → Redis stores handoff token:
   handoff:{token_id} = {user_id, org_id, exp:60s, used:false}
4. Django web → 302 https://{slug}.mypipelinehero.com/handoff?token=...
5. Tenant subdomain Django web → Redis validates and consumes token atomically
6. Tenant subdomain Django web → establishes tenant-local Django session
7. Tenant subdomain Django web → 302 /dashboard
```

#### A.3.5 Cross-domain data flow: outbox

```text
1. Service function begins transaction
2. Service function mutates domain rows
3. Service function inserts OutboxEntry with payload + correlation_id
4. Transaction commits
5. Outbox dispatcher polls pending rows
6. Dispatcher enqueues Celery task with outbox row id
7. Worker consumes Celery task and processes outbox row idempotently
8. Worker marks outbox row consumed
```

#### A.3.6 Deployment posture

v1 deployment MUST use Docker images and environment-specific Docker Compose files or equivalent host-level container orchestration.

Kubernetes-specific resources are not part of v1:

- no Kubernetes Deployment manifests
- no Helm charts
- no ingress-nginx
- no cert-manager requirement
- no HPA
- no Kubernetes Jobs for migrations
- no Kubernetes Lease locks
- no SealedSecrets

Kubernetes MAY be documented in a future scalability appendix only.

### A.4 Phasing: Phase 1 Server-Rendered, Phase 2 React Portal

**Status: NORMATIVE.**

#### A.4.1 Phase definitions

**Phase 1.** A complete server-rendered Django CRM. Every domain, every workflow, every state machine, every pricing strategy, every RBAC enforcement, every audit event ships in Phase 1. Phase 1 launches to production and serves real tenants. The frontend is Django templates + Tailwind + django-vite + HTMX (HTMX as the global default for interactivity).

**Phase 2.** A custom React tenant portal replaces the Phase 1 server-rendered tenant-portal screens. The custom platform admin site, custom tenant admin site, login landing page, organization picker, support tooling, and email templates remain server-rendered permanently. Phase 2 consumes a DRF-based internal JSON API.

#### A.4.2 What Phase 2 inherits, untouched

- The service layer (every state-changing function in `apps/*/services/`) is unchanged between phases.
- The cross-subdomain handoff protocol (B.4) is unchanged.
- RBAC enforcement (B.6) is unchanged.
- Pricing engine (E.5–E.10) is unchanged.
- Audit events (G.5) are emitted from the same service layer regardless of which UI surface initiated the action.

#### A.4.3 What permanently survives as server-rendered

| Component | Reason |
| --- | --- |
| Custom root-domain landing page | Public entrypoint for all users; must load quickly and work without app JavaScript |
| Root-domain authentication pages | Login, OAuth/OIDC callback, MFA, password reset, invite acceptance, and organization picker are auth-adjacent and should remain simple |
| Custom platform admin site | Support engineers and platform staff need controlled cross-tenant operations |
| Custom tenant admin site | Tenant admins need organization-specific configuration screens |
| Phase 1 domain templates | Every domain needs server-rendered pages for functional testing and production v1 usage before Phase 2 React parity |
| Support impersonation tooling and banner | Banner especially: server-rendered, unstrippable by client-side JavaScript |
| Email templates (invoice PDFs, notification HTML) | No React render context |
| Error pages, terms/privacy/support pages, health checks | Static or near-static |

The root domain `/` is a real custom landing page, not a redirect. It is the entrypoint for all users and provides the path into `/login/`.

The base Django admin is not the primary platform console and is not the tenant admin UI. It MAY be enabled in local development and selected non-production environments at `/django-admin/` for raw model inspection and framework debugging, but no v1 product workflow may depend on it. Production administration MUST use custom admin views.

#### A.4.3A Phase 1 development and testing posture

Phase 1 intentionally has two complementary surfaces:

1. **Custom admin/testing surface.** The custom platform admin site and custom tenant admin site are the primary development surfaces for exercising domain models, service-layer workflows, RBAC, state transitions, pricing configuration, audit behavior, outbox behavior, and tenant administration.
2. **Tenant-facing template surface.** Each domain also owns tenant-facing Django templates that render the workflow as a tenant user would experience it.

This means engineers can test both sides of the product during Phase 1:

- staff/support view through `/platform/`,
- tenant-admin view through tenant subdomain `/admin/`,
- raw development inspection through dev-only `/django-admin/`,
- tenant-user view through the tenant portal pages.

Phase 2 React work extends or replaces the tenant-facing domain templates domain-by-domain. The Phase 1 templates remain the functional reference for workflow parity until a React domain is fully cut over.

#### A.4.4 Phase 1 obligations to make Phase 2 cheap

1. **Service-layer exhaustiveness.** Every state-changing operation invoked by a Phase 1 view MUST have a corresponding service function.
2. **Plain-Python service signatures.** Service functions accept primitives, dataclasses, or domain entities — never `request` objects.
3. **Typed domain exceptions.** Services raise the exception taxonomy in G.2.
4. **DRF serializer/service pairing** where natural.
5. **No template-embedded business logic.**
6. **Domain-owned templates.** Each domain app owns the templates needed for its Phase 1 tenant-facing workflows and admin/testing workflows.
7. **Style-token continuity.** Phase 1 templates MUST use the shared MyPipelineHero CSS/design tokens so Phase 2 React pages can preserve the same visual language.

#### A.4.5 Static enforcement of service-layer discipline

A custom AST-based check (implemented as a `ruff` plugin or a standalone script invoked by CI) MUST flag the following violations:

| Violation | Rule |
| --- | --- |
| `.save()` called outside `apps/*/services/` or inside a model `save()` override | Block PR |
| `.delete()` called outside `apps/*/services/` | Block PR |
| `Model.objects.create(...)` outside services/admin/migrations/tests | Block PR |
| `.update(...)` on a queryset outside `apps/*/services/` | Block PR |
| `transaction.atomic()` opened outside `apps/*/services/` | Warning |
| `request.user` referenced inside `apps/*/services/` | Block PR |
| `GenericForeignKey` declared anywhere | Block PR |
| `forms.ModelChoiceField` without inheriting `TenantModelChoiceField` | Block PR |

#### A.4.6 Phase 2 deferred decisions

Locked now: DRF as the API library, URL versioning (`/api/v1/...`), drf-spectacular for OpenAPI schema, cursor pagination as default, cookie-based auth inheriting from tenant-local session.

Deferred: React build tool, routing library, data-fetching library, component library, bundle deployment. CSS/design-token continuity is not deferred; Phase 2 React MUST preserve the MyPipelineHero visual language from H.8.

---

### A.5 Base Project Structure

**Status: NORMATIVE for initial layout; INFORMATIVE for future evolution.**

#### A.5.1 Purpose

The project layout MUST make domain ownership clear. Apps are grouped by platform, web, CRM, catalog, operations, reporting, files, API, and common infrastructure concerns.

The repository has a root-level `frontend/` directory reserved for the Phase 2 React tenant-facing SPA, and a `backend/` directory for the Django application. Phase 1 ships from `backend/` using Django templates. Phase 2 React code is introduced under `frontend/` when M9 begins.

This structure is the initial v1 layout. It MAY evolve as the codebase grows, but changes that move domain ownership, app boundaries, template ownership, static asset ownership, or frontend/backend boundaries MUST be reflected in this guide.

#### A.5.2 Initial repository structure

```text
frontend/                   # Phase 2 — React tenant-facing SPA source tree
backend/
├── manage.py
├── config/
│   ├── __init__.py
│   ├── asgi.py
│   ├── wsgi.py
│   ├── urls.py
│   └── settings/
│       ├── __init__.py
│       ├── base.py
│       ├── dev.py
│       ├── test.py
│       ├── staging.py
│       ├── demo.py
│       └── prod.py
├── apps/
│   ├── api/                    # Phase 2 — internal JSON API for React tenant portal
│   ├── platform/
│   │   ├── accounts/           # Custom User model and account-level identity
│   │   ├── organizations/      # Organization, Membership, tenant lifecycle
│   │   ├── rbac/               # Capabilities, roles, grants, enforcement helpers
│   │   ├── audit/              # AuditEvent and audit services
│   │   └── support/            # Platform console and support impersonation
│   ├── web/
│   │   ├── landing/            # Custom root-domain landing page; retained in Phase 2
│   │   ├── auth_portal/        # Login, MFA, invite, account, org picker
│   │   └── tenant_portal/      # Django-template UI for Phase 1
│   ├── crm/
│   │   ├── leads/
│   │   ├── quotes/
│   │   ├── clients/
│   │   ├── tasks/
│   │   ├── communications/
│   │   ├── orders/
│   │   └── billing/
│   ├── files/
│   │   └── attachments/
│   ├── reporting/
│   │   └── exports/
│   ├── catalog/
│   │   ├── services/
│   │   ├── products/
│   │   ├── materials/
│   │   ├── suppliers/
│   │   ├── pricing/
│   │   └── manufacturing/
│   ├── operations/
│   │   ├── locations/
│   │   ├── purchasing/
│   │   ├── build/
│   │   └── workorders/
│   └── common/
│       ├── admin/              # Custom admin-site framework, base views, menus
│       ├── tenancy/            # TenantOwnedModel, TenantManager, tenant context
│       ├── db/                 # DB helpers, constraints, partition helpers
│       ├── services/           # Service-layer shared primitives
│       ├── outbox/             # OutboxEntry, dispatcher, task bridge
│       ├── utils/
│       ├── choices/
│       └── tests/
├── templates/
│   ├── auth_portal/
│   ├── console/
│   ├── landing/
│   ├── rbac/
│   ├── tenant_portal/
│   └── base.html
├── static/
│   └── landing/
│       └── css/
├── media/
├── requirements/
├── docker/
│   ├── django/
│   ├── postgres/
│   ├── nginx/
│   └── workers/
├── compose.yaml
└── .env.example
```

#### A.5.3 App-boundary rules

1. Domain models MUST live in the app that owns the domain.
2. Shared abstract models, querysets, managers, and base utilities live under `apps/common/`.
3. Authentication identity belongs to `apps/platform/accounts`.
4. Tenant organization and membership records belong to `apps/platform/organizations`.
5. RBAC capabilities, roles, grants, and enforcement helpers belong to `apps/platform/rbac`.
6. AuditEvent and audit emission helpers belong to `apps/platform/audit`.
7. Support impersonation and platform staff tooling belong to `apps/platform/support`.
8. Tenant-facing CRM modules belong under `apps/crm/`.
9. Catalog and pricing modules belong under `apps/catalog/`.
10. Operational fulfillment modules belong under `apps/operations/`.
11. Phase 2 DRF API code belongs under `backend/apps/api/`.
12. Phase 2 React source belongs under root-level `frontend/`.
13. Root-domain landing-page code belongs under `apps/web/landing` and `templates/landing/`.
14. Auth portal templates belong under `templates/auth_portal/`.
15. Tenant portal templates belong under `templates/tenant_portal/` unless a domain app has a more specific template subdirectory documented.
16. Custom platform-console templates belong under `templates/console/`.
17. RBAC/admin-adjacent templates may use `templates/rbac/` when shared across tenant admin and platform admin.
18. Shared base templates belong under `templates/base.html` and related component partials.

#### A.5.4 Import rules

Domain apps MAY import from:

- `apps.common.*`
- `apps.platform.rbac`
- `apps.platform.audit`
- explicitly allowed upstream domain apps

Domain apps SHOULD NOT import later workflow-stage apps unless the dependency is explicitly documented.

Example:

```text
quotes may reference catalog/pricing.
billing may reference orders and snapshots.
catalog should not import billing.
```

#### A.5.5 Settings module names

Settings modules are:

```text
config.settings.dev
config.settings.test
config.settings.staging
config.settings.demo
config.settings.prod
```

`prod.py` is the production settings module. `demo.py` is the demo/sandbox settings module.

#### A.5.6 Template and static asset ownership

The root shared base template is:

```text
backend/templates/base.html
```

The initial committed visual system is:

```text
backend/static/landing/css/homepage.css
backend/static/landing/css/dashboard.css
```

The attached landing, login, dashboard, and base-template assets are the Phase 1 visual baseline. Future domain templates and Phase 2 React components MUST preserve the same design tokens, color palette, spacing language, focus states, and core `mph-*` class semantics unless a guide amendment updates the brand system.

#### A.5.7 Django app labels

Because the directory layout is nested, every app MUST define an explicit stable `label` in `apps.py` when needed to avoid collisions.

Example:

```python
class AccountsConfig(AppConfig):
    name = "apps.platform.accounts"
    label = "platform_accounts"
```

Model references SHOULD use `settings.AUTH_USER_MODEL` for the User model and explicit app labels for cross-app FKs where required.

## Part B — Tenancy, Identity, and Authorization

### B.1 Tenancy Model

**Status: NORMATIVE.**

#### B.1.1 Tenancy posture

The platform uses **row-based multi-tenancy**. Every tenant-owned record carries an `organization_id` foreign key. Schema-per-tenant deployment is explicitly out of scope and is not a future option.

#### B.1.2 Organization model

```text
Organization
  id: UUID, pk                                      -- UUID v7
  slug: TEXT, unique                                -- subdomain-safe
  name: TEXT
  status: ENUM(ACTIVE, SUSPENDED, OFFBOARDING, DELETED)
  primary_contact_name: TEXT
  primary_contact_email: TEXT
  primary_contact_phone: TEXT, null
  timezone: TEXT                                    -- IANA tz name
  base_currency_code: CHAR(3)                       -- ISO 4217
  default_tax_jurisdiction_id: UUID, fk -> TaxJurisdiction, null
  invoicing_policy_id: UUID, fk -> InvoicingPolicy, null
  numbering_config: JSONB                           -- prefix overrides per entity
  accounting_adapter_code: TEXT, default("noop")    -- propagated from F.5.4
  accounting_adapter_config: JSONB, default({})     -- encrypted at rest
  created_at: TIMESTAMPTZ
  updated_at: TIMESTAMPTZ
```

**Slug rules.** Slug MUST match `^[a-z][a-z0-9-]{1,61}[a-z0-9]$` (DNS-safe). Slug is unique globally. Slug is immutable after Organization creation in v1.

**Status semantics.**

| Status | Meaning | Tenant-portal access | Audit retention |
| --- | --- | --- | --- |
| `ACTIVE` | Normal operating state | Full | Per G.5 |
| `SUSPENDED` | Platform-imposed suspension | Blocked at handoff | Continues |
| `OFFBOARDING` | Tenant-initiated termination, in 30-day grace | Read-only access, exports allowed | Continues |
| `DELETED` | Cascade complete; row retained for audit attribution only | None | Retained per audit policy |

#### B.1.3 Tenant-owned record requirement

Every tenant-owned model MUST:

1. Declare `organization = models.ForeignKey(Organization, on_delete=models.PROTECT, ...)`.
2. Set `objects = TenantManager()` on the model.
3. Set the class attribute `is_tenant_owned = True`.
4. Inherit from `TenantOwnedModel` abstract base class.

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
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="+",
        null=True,
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="+",
        null=True,
    )

    is_tenant_owned: bool = True

    objects: "TenantManager" = TenantManager()

    class Meta:
        abstract = True
```

#### B.1.4 TenantManager and TenantQuerySet

```python
# NORMATIVE: shape
class TenantQuerySet(models.QuerySet):
    def for_org(self, organization_id: UUID) -> "TenantQuerySet":
        return self.filter(organization_id=organization_id)

    def for_membership(self, membership: "Membership") -> "TenantQuerySet":
        """Apply org scope AND operating-scope intersection."""
        qs = self.for_org(membership.organization_id)
        return qs.intersect_with_operating_scope(membership)

    def intersect_with_operating_scope(
        self, membership: "Membership"
    ) -> "TenantQuerySet":
        return self


class TenantManager(models.Manager.from_queryset(TenantQuerySet)):
    use_in_migrations = False  # NEVER use in migrations
```

#### B.1.5 Cross-tenant access exception paths

Two narrow exception paths permit cross-tenant queries:

1. **Support User platform console.** Custom platform admin views may perform controlled cross-tenant queries. These views MUST use explicit platform query services or `Model.objects.platform_admin_queryset()` and MUST emit an audit event (`PLATFORM_ADMIN_QUERY`).
2. **Migrations.** `TenantManager.use_in_migrations = False`.

The base Django admin MUST NOT be used as the production platform console.

#### B.1.6 Foreign key tenancy invariant

When a tenant-owned record references another tenant-owned record, both MUST belong to the same Organization. Enforced at:

1. **Service layer.** Shared utility `ensure_same_org(*records)` raises `TenantViolationError`.
2. **Object check in RBAC enforcement (B.6).**

DB-level CHECK constraints across tables NOT used in v1.

#### B.1.7 CI tenant-isolation guardrail

```python
# NORMATIVE: behavior
def test_all_tenant_owned_models_use_tenant_manager():
    for model in apps.get_models():
        if getattr(model, "is_tenant_owned", False):
            assert isinstance(model._default_manager, TenantManager), (
                f"{model.__name__} declares is_tenant_owned=True but does not "
                f"use TenantManager"
            )
            assert any(
                f.name == "organization" and isinstance(f, ForeignKey)
                for f in model._meta.fields
            )
```

### B.2 Operating Scope: Region / Market / Location

**Status: NORMATIVE.**

#### B.2.1 Hierarchy

```text
Organization
  └── Region (many)
        └── Market (many)
              └── Location (many)
```

A Market MUST belong to exactly one Region. A Location MUST belong to exactly one Market. Cross-organization references PROHIBITED.

#### B.2.2 Models

```text
Region
  id: UUID, pk
  organization_id: UUID, fk -> Organization on_delete=PROTECT
  code: TEXT
  name: TEXT
  is_active: BOOL, default(true)
  unique_together (organization_id, code)

Market
  id: UUID, pk
  organization_id: UUID, fk -> Organization on_delete=PROTECT
  region_id: UUID, fk -> Region on_delete=PROTECT
  code: TEXT
  name: TEXT
  is_active: BOOL, default(true)
  unique_together (organization_id, code)

Location
  id: UUID, pk
  organization_id: UUID, fk -> Organization on_delete=PROTECT
  market_id: UUID, fk -> Market on_delete=PROTECT
  code: TEXT
  name: TEXT
  address_line1, address_line2, city, region_admin, postal_code, country: TEXT
  tax_jurisdiction_id: UUID, fk -> TaxJurisdiction, null
  is_active: BOOL, default(true)
  unique_together (organization_id, code)
```

#### B.2.3 RML on tenant-owned operational records

The following operational records MUST carry a non-null `location_id`:

- `SalesOrder`, `WorkOrder`, `BuildOrder`, `PurchaseOrder`
- `Quote`, `Lead`, `Client`, `Invoice`

Once set, `location_id` on commercial records is **immutable**.

#### B.2.4 Membership scope assignment

```text
MembershipScopeAssignment
  id: UUID, pk
  membership_id: UUID, fk -> Membership on_delete=CASCADE
  scope_type: ENUM(REGION, MARKET, LOCATION)
  region_id: UUID, fk -> Region, null
  market_id: UUID, fk -> Market, null
  location_id: UUID, fk -> Location, null

  CHECK: exactly one of (region_id, market_id, location_id) is non-null
```

A membership with NO scope assignments and a non-scoped role has organization-wide access. A membership with a scoped role and NO scope assignments has zero data access (visible misconfiguration).

#### B.2.5 Queryset intersection

```python
# NORMATIVE: shape (illustrative for SalesOrder)
class SalesOrderQuerySet(TenantQuerySet):
    def intersect_with_operating_scope(self, membership):
        scopes = membership.scope_assignments.all()
        if not scopes.exists():
            if membership.role_set.filter(is_scoped_role=True).exists():
                return self.none()
            return self
        location_ids = resolve_location_ids_for_scopes(scopes)
        return self.filter(location_id__in=location_ids)
```

#### B.2.6 Object-level check

```python
# NORMATIVE: shape
def check_operating_scope(membership, target_record):
    if not target_record.location_id:
        return True
    permitted = resolve_location_ids_for_scopes(membership.scope_assignments.all())
    if target_record.location_id not in permitted:
        raise OperatingScopeViolationError(
            membership=membership,
            target_location_id=target_record.location_id,
        )
```

#### B.2.7 RML as pricing input

`PricingContext` carries `region_id`, `market_id`, and `location_id`.

RML is consumed by:

- pricing rule resolution,
- cost/input resolvers where location affects cost,
- `modifier.location`,
- tax jurisdiction resolution,
- reporting rollups.

Location-specific pricing MUST NOT be implemented as a standalone base strategy. It is a modifier or rule-resolution concern.

### B.3 Identity, Custom User Model, and External Login Identities

**Status: NORMATIVE.**

#### B.3.1 Custom user model is mandatory from migration #1

```python
AUTH_USER_MODEL = "platform_accounts.User"
```

The custom `User` model remains the canonical platform identity regardless of login method.

OAuth/OIDC login identities are linked to a canonical `User`. They do not replace the `User`, `Membership`, `Role`, `Capability`, or operating-scope model.

#### B.3.2 Authentication implementation

The application uses Django’s authentication framework with `django-allauth` for account login, OAuth/OIDC provider login, and MFA.

Required apps:

```python
INSTALLED_APPS = [
    # Django apps
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.sites",

    # allauth
    "allauth",
    "allauth.account",
    "allauth.socialaccount",
    "allauth.socialaccount.providers.openid_connect",
    "allauth.mfa",

    # platform apps
    "apps.platform.accounts",
    "apps.platform.organizations",
    "apps.platform.rbac",
    "apps.platform.audit",
    "apps.platform.support",

    # common infrastructure
    "apps.common.tenancy",
    "apps.common.outbox",
]
```

Authentication backends:

```python
AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",
    "allauth.account.auth_backends.AuthenticationBackend",
]
```

`django-allauth` is an implementation detail at the authentication boundary. Domain authorization remains owned by the MyPipelineHero Membership/RBAC model.

#### B.3.3 User model

```text
User
  id: UUID, pk                                       -- UUID v7
  email: TEXT, unique, lowercase-normalized          -- primary platform identity
  password: TEXT, null                               -- may be unusable for external-only users
  is_active: BOOL, default(true)
  is_staff: BOOL, default(false)
  is_superuser: BOOL, default(false)
  is_system: BOOL, default(false)

  totp_secret: TEXT, null, audit_masked              -- local MFA secret, encrypted at rest
  totp_enrolled_at: TIMESTAMPTZ, null
  backup_codes_hash: TEXT, null, audit_masked

  password_changed_at: TIMESTAMPTZ, null
  last_password_breach_check_at: TIMESTAMPTZ, null
  last_login_at: TIMESTAMPTZ, null
  failed_login_count: INT, default(0)
  locked_until: TIMESTAMPTZ, null

  preferred_auth_method: ENUM(PASSWORD, OIDC, EITHER), default(EITHER)
  external_login_only: BOOL, default(false)

  created_at: TIMESTAMPTZ
  updated_at: TIMESTAMPTZ

  CHECK: is_system implies (is_active AND NOT is_staff AND NOT is_superuser)
  CHECK: lower(email) = email
```

`USERNAME_FIELD = "email"`. `REQUIRED_FIELDS = []`.

A user authenticated only through OAuth/OIDC MAY have an unusable local password. A user MUST NOT be allowed to remove their only valid login method.

#### B.3.4 User flag semantics

| Flag | Meaning |
| --- | --- |
| `is_active` | Account is operational |
| `is_staff` | User may access the platform console |
| `is_superuser` | RBAC short-circuits to grant |
| `is_system` | User is the System User and appears as actor on automated transitions |
| `external_login_only` | User cannot authenticate with local password unless a password is later set through an approved recovery/admin flow |

#### B.3.5 Membership model

```text
Membership
  id: UUID, pk                                       -- UUID v7
  user_id: UUID, fk -> User on_delete=PROTECT
  organization_id: UUID, fk -> Organization on_delete=PROTECT
  status: ENUM(INVITED, ACTIVE, SUSPENDED, INACTIVE, EXPIRED)
  invited_by_id: UUID, fk -> User, null
  invited_at: TIMESTAMPTZ, null
  invitation_expires_at: TIMESTAMPTZ, null
  invitation_token_hash: TEXT, null, audit_masked
  accepted_at: TIMESTAMPTZ, null
  first_name: TEXT
  last_name: TEXT
  phone: TEXT, null
  is_default_for_user: BOOL, default(false)
  suspended_reason: TEXT, null

  unique_together (user_id, organization_id)
  partial_index (user_id) where is_default_for_user
```

Membership remains the authoritative tenant-access record. OAuth/OIDC login MUST NOT create tenant access by itself.

#### B.3.6 External identity model

The implementation MAY use `django-allauth`’s `SocialAccount` model as the source table for external identities. If the project wraps or mirrors allauth data, the logical model MUST preserve this shape:

```text
ExternalIdentity
  id: UUID, pk
  user_id: UUID, fk -> User on_delete=CASCADE
  provider: TEXT                                  -- e.g. google, microsoft, openid_connect:<provider_id>
  provider_uid: TEXT                              -- stable provider subject / sub claim
  email_at_provider: TEXT
  email_verified: BOOL
  display_name_at_provider: TEXT, null
  last_login_at: TIMESTAMPTZ, null
  extra_data: JSONB                               -- provider claims; masked where necessary
  created_at: TIMESTAMPTZ
  updated_at: TIMESTAMPTZ

  unique_together(provider, provider_uid)
```

The provider subject identifier MUST be preferred over email as the stable external identity key.

Email MAY be used for first-time account matching only if the provider confirms the email is verified and the linking flow satisfies B.4.10.

#### B.3.7 OAuth/OIDC provider configuration

Provider configuration is platform-managed in v1.

```text
OAuthProviderConfig
  id: UUID, pk
  provider_code: TEXT, unique
  display_name: TEXT
  provider_type: ENUM(OIDC, OAUTH2)
  issuer_url: TEXT, null
  authorization_url: TEXT, null
  token_url: TEXT, null
  userinfo_url: TEXT, null
  jwks_url: TEXT, null
  client_id_env_key: TEXT
  client_secret_env_key: TEXT, audit_masked
  scopes: TEXT[]
  is_active: BOOL, default(true)
  require_verified_email: BOOL, default(true)
  trust_external_mfa: BOOL, default(false)
  allowed_email_domains: TEXT[], null
  created_at: TIMESTAMPTZ
  updated_at: TIMESTAMPTZ
```

Provider client secrets MUST be supplied through environment variables or a secret manager. Provider secrets MUST NOT be stored in source control.

Tenant-managed custom identity providers are deferred unless explicitly required by the first production tenant.

#### B.3.8 External provider claims

The application MUST normalize provider claims into a small internal shape before account resolution:

```python
@dataclass(frozen=True)
class ExternalIdentityClaims:
    provider_code: str
    provider_uid: str
    email: str | None
    email_verified: bool
    display_name: str | None
    raw_claims: Mapping[str, Any]
    acr: str | None = None
    amr: tuple[str, ...] = ()
```

Raw provider claims MUST NOT be used directly in authorization decisions.

#### B.3.9 Membership remains authoritative

OAuth/OIDC login proves identity only.

Tenant authorization is still determined by:

```text
User
  → Membership
  → MembershipRole
  → RoleCapability
  → Capability
  → Operating Scope
```

External provider groups, domains, or claims MUST NOT grant application capabilities directly in v1.

Mapping identity-provider groups to tenant roles is deferred.

#### B.3.10 System User

Exactly one `User` row per environment has `is_system=true`. Created via the seed-v1 data migration. Has unusable password. MUST NOT have external identities.

#### B.3.11 Support User

A Support User is a `User` row with `is_staff=true` and usually `is_superuser=false`.

Support users MAY authenticate through local password + local MFA or through an approved OAuth/OIDC provider. Support users MUST satisfy MFA on every login path.

### B.4 Authentication, OAuth/OIDC, MFA, Sessions, and Cross-Subdomain Handoff

**Status: NORMATIVE.**

#### B.4.1 Supported login methods

v1 supports:

| Login method | v1 status |
| --- | --- |
| Local email/password | Supported |
| Local email/password + local MFA | Required for local password login |
| OAuth/OIDC login | Supported |
| OAuth/OIDC login + trusted provider MFA | Supported for approved providers |
| OAuth/OIDC login + local step-up MFA | Required when provider MFA is not trusted |
| SAML | Deferred |
| Passwordless magic link | Deferred |
| Passkeys-only login | Deferred |

For user-facing wording, the UI MAY say “Continue with Google,” “Continue with Microsoft,” or “Continue with SSO.” Internally, the preferred protocol for authentication is OIDC.

#### B.4.2 Root-domain login only

All authentication starts on the root domain:

```text
https://mypipelinehero.com/login
```

OAuth/OIDC callback URLs MUST terminate on the root domain, not tenant subdomains.

Callback pattern:

```text
https://mypipelinehero.com/accounts/oidc/{provider_id}/login/callback/
```

Tenant subdomains do not initiate external-provider login directly. After root-domain authentication succeeds, tenant access is established only through the signed handoff flow.

#### B.4.3 Login flow: local password

```text
1. User visits https://mypipelinehero.com/login.
2. User selects "Sign in with email".
3. User submits email + password.
4. Root domain validates credentials.
5. Root domain requires local MFA challenge.
6. User submits TOTP or recovery code.
7. Root domain establishes ROOT-DOMAIN session.
8. Root domain loads user's ACTIVE memberships.
9. Branch:
   a. 0 active memberships AND not is_staff → render "no active access" page.
   b. 0 active memberships AND is_staff → 302 to /platform/.
   c. 1 active membership → issue handoff token.
   d. 2+ active memberships OR is_staff with memberships → render org picker.
10. User selects org if required.
11. Root domain issues handoff token.
12. Tenant subdomain consumes handoff token and establishes tenant-local session.
```

#### B.4.4 Login flow: OAuth/OIDC

```text
1. User visits https://mypipelinehero.com/login.
2. User selects an approved external identity provider.
3. Root domain redirects to provider authorization endpoint.
4. Provider authenticates user.
5. Provider redirects back to root-domain callback.
6. Application validates callback and provider response.
7. Application resolves or links canonical User.
8. Application evaluates MFA requirement.
9. If local step-up MFA is required, user completes local MFA challenge.
10. Root domain establishes ROOT-DOMAIN session.
11. Root domain loads user's ACTIVE memberships.
12. Branch:
    a. 0 active memberships AND not is_staff → render "no active access" page.
    b. 0 active memberships AND is_staff → 302 to /platform/.
    c. 1 active membership → issue handoff token.
    d. 2+ active memberships OR is_staff with memberships → render org picker.
13. User selects org if required.
14. Root domain issues handoff token.
15. Tenant subdomain consumes handoff token and establishes tenant-local session.
```

#### B.4.5 OAuth/OIDC callback validation

OIDC login MUST validate:

- `state`
- `nonce`
- issuer
- audience/client ID
- ID token signature
- token expiry
- provider subject identifier
- provider configuration is active
- verified email if required by provider config
- allowed email domain if configured

OAuth/OIDC login MUST NOT trust unverified email addresses for account linking.

#### B.4.6 Canonical user resolution

```python
def resolve_external_user(
    *,
    claims: ExternalIdentityClaims,
    provider_config: OAuthProviderConfig,
) -> User:
    """
    Resolve or link an external identity to a canonical User.
    Does not create Membership.
    Does not grant Role or Capability.
    """
```

Resolution order:

1. Find existing external identity by `(provider, provider_uid)`.
2. If found, return linked active `User`.
3. If not found and provider email is verified, find existing `User` by normalized email.
4. If no `User` exists, create a global `User` only if platform policy allows external self-registration.
5. Link external identity to `User`.
6. Return `User`.

If self-registration is disabled and no existing user is found, render “no active access” or “invitation required.”

#### B.4.7 Account linking rules

Silent account linking based only on email is prohibited unless all of the following are true:

1. provider email is verified,
2. provider is active and approved,
3. provider config allows email-based linking,
4. no conflicting existing external identity exists,
5. user is completing an invite flow or passes a local confirmation challenge.

If an OAuth/OIDC login email matches an existing user but the system cannot safely link the account, the login MUST stop and render an account-linking help flow.

#### B.4.8 MFA policy

2FA/MFA is required at v1.

For local password login:

- Local MFA is REQUIRED.
- TOTP is REQUIRED for v1.
- Recovery codes are REQUIRED.
- SMS MFA is PROHIBITED.
- WebAuthn/passkeys are deferred unless explicitly added later.

For OAuth/OIDC login:

- If `OAuthProviderConfig.trust_external_mfa=True`, the system MAY treat provider MFA as satisfying login MFA.
- If provider MFA is not trusted, the application MUST require local step-up MFA after the OAuth/OIDC callback.
- If provider MFA trust cannot be technically verified or contractually/admin-enforced, local step-up MFA is REQUIRED.
- Support users MUST satisfy MFA regardless of login method.

Provider MFA trust MUST be reviewed during security review before the provider is enabled in production.

#### B.4.9 Local MFA enrollment

MFA enrollment is required when:

| Condition | Requirement |
| --- | --- |
| New local-password user accepting first invite | MUST enroll before completing invite acceptance |
| Existing local-password user without MFA | MUST enroll on next login |
| OAuth/OIDC user whose provider is not trusted for MFA | MUST enroll before entering tenant portal |
| Support user | MUST enroll unless provider MFA is explicitly trusted |
| User performing local sensitive action without trusted fresh provider auth | MUST satisfy local MFA |

Backup recovery codes are required. Codes are one-time use and stored hashed.

#### B.4.10 Re-authentication for sensitive actions

Sensitive actions require recent authentication.

| Action | Re-auth window |
| --- | --- |
| Quote acceptance | 5 minutes |
| Payment recording | 5 minutes |
| Payment reversal/adjustment | 5 minutes |
| Impersonation start | 5 minutes |
| TOTP re-enrollment | 5 minutes |
| Password change | 5 minutes |
| External identity linking/unlinking | 5 minutes |
| Role/capability changes | 15 minutes |
| Tenant data export request | 5 minutes |
| Tenant deletion request | 5 minutes |

Re-auth MAY be satisfied by:

1. local MFA challenge, or
2. fresh OAuth/OIDC provider authentication with trusted MFA.

Password-only re-authentication is not sufficient.

#### B.4.11 Root-domain session

The root-domain session is established after authentication and MFA satisfaction.

The root-domain session is used for:

- organization picker
- platform console
- issuing handoff tokens
- account security settings
- external identity linking/unlinking

The root-domain session MUST NOT directly grant tenant data access.

#### B.4.12 Handoff token protocol

**Token issuance:**

```python
def issue_handoff_token(
    *,
    user_id: UUID,
    organization_id: UUID,
    membership_id: UUID,
    auth_method: str,
    auth_provider: str | None,
    mfa_satisfied_at: datetime,
) -> str:
    token_id = secrets.token_urlsafe(32)
    payload = {
        "tid": token_id,
        "uid": str(user_id),
        "oid": str(organization_id),
        "mid": str(membership_id),
        "amr": auth_method,
        "apr": auth_provider,
        "mfa": mfa_satisfied_at.isoformat(),
        "iat": now_unix(),
        "exp": now_unix() + 60,
    }

    signed = jwt.encode(
        payload,
        settings.HANDOFF_SIGNING_KEY,
        algorithm="HS256",
    )

    redis.setex(
        f"handoff:{token_id}",
        60,
        json.dumps({
            "used": False,
            "uid": str(user_id),
            "oid": str(organization_id),
            "mid": str(membership_id),
        }),
    )

    audit_emit(
        "HANDOFF_TOKEN_ISSUED",
        actor=user_id,
        organization=organization_id,
        metadata={
            "token_id": token_id,
            "auth_method": auth_method,
            "auth_provider": auth_provider,
        },
    )

    return signed
```

**Token consumption:**

```python
def consume_handoff_token(*, token: str, request) -> HandoffResult:
    try:
        payload = jwt.decode(
            token,
            settings.HANDOFF_SIGNING_KEY,
            algorithms=["HS256"],
        )
    except jwt.ExpiredSignatureError:
        raise HandoffInvalidError("expired")
    except jwt.InvalidTokenError:
        raise HandoffInvalidError("invalid")

    token_id = payload["tid"]
    key = f"handoff:{token_id}"

    pipe = redis.pipeline()
    pipe.get(key)
    pipe.delete(key)
    raw, _ = pipe.execute()

    if raw is None:
        raise HandoffInvalidError("not_found_or_replayed")

    state = json.loads(raw)
    if state.get("used"):
        audit_emit("HANDOFF_REPLAY_DETECTED", ...)
        raise HandoffInvalidError("replayed")

    org = Organization.objects.get(id=payload["oid"])
    expected_host = f"{org.slug}.mypipelinehero.com"

    if request.get_host() != expected_host:
        audit_emit("HANDOFF_HOST_MISMATCH", ...)
        raise HandoffInvalidError("host_mismatch")

    membership = Membership.objects.get(
        id=payload["mid"],
        user_id=payload["uid"],
        organization_id=payload["oid"],
        status=MembershipStatus.ACTIVE,
    )

    return HandoffResult(
        user_id=UUID(payload["uid"]),
        organization_id=org.id,
        membership_id=membership.id,
        auth_method=payload["amr"],
        auth_provider=payload.get("apr"),
        mfa_satisfied_at=parse_datetime(payload["mfa"]),
    )
```

#### B.4.13 Handoff token properties

- 256 bits of randomness in token id.
- 60-second maximum lifetime.
- Single-use, enforced atomically.
- Bound to organization through host check.
- Bound to active membership.
- Replay attempts emit high-severity audit event.
- Handoff signing key rotates quarterly.
- Previous signing key MAY be retained for one rotation window.

#### B.4.14 Tenant-local session

| Property | Value |
| --- | --- |
| Cookie name | `tenant_session_{slug}` |
| Cookie domain | `{slug}.mypipelinehero.com` |
| Cookie path | `/` |
| Cookie flags | `Secure`, `HttpOnly`, `SameSite=Lax` |
| Idle expiry | 12 hours of inactivity |
| Absolute cap | 7 days from establishment |
| Storage | Database-backed Django session |

Tenant-local session MUST store:

```text
user_id
organization_id
membership_id
auth_method
auth_provider
mfa_satisfied_at
is_impersonating
```

Allowed `auth_method` values:

```text
password
oidc
oauth2
impersonation
```

A shared parent-domain tenant session is PROHIBITED.

#### B.4.15 Organization picker

After root-domain authentication, the system loads ACTIVE memberships.

| Membership count | Behavior |
| --- | --- |
| 0 active memberships, non-staff | render no active access page |
| 0 active memberships, staff | redirect to platform console |
| 1 active membership | issue handoff token |
| 2+ active memberships | render organization picker |
| staff with memberships | render choice between platform console and tenant access |

OAuth/OIDC provider claims MUST NOT bypass organization picker behavior.

#### B.4.16 Multi-tab UX

When a user opens a tenant subdomain in a tab while already authenticated to a different tenant in another tab, the handoff endpoint detects multiple `tenant_session_*` cookies and renders a soft warning interstitial:

```text
You're also signed in to {OtherOrg}. Continuing here will create an independent
session in this tab. Your session in the other tenant is unaffected.

[Continue] [Cancel]
```

One-time per session pair.

#### B.4.17 Logout semantics

| Trigger | Effect |
| --- | --- |
| Tenant-portal logout | Destroys tenant-local session for that subdomain only |
| Root-domain logout | Destroys root-domain session and invalidates outstanding handoff tokens |
| OAuth/OIDC logout | Local logout only in v1; provider logout not guaranteed |
| Idle expiry | Tenant or root session expires silently |
| Absolute cap | Same as idle expiry |
| Sensitive-action challenge failure | Tenant-local session destroyed and audit event emitted |

Provider global logout is deferred.

#### B.4.18 External identity unlinking

A user MAY unlink an external identity only if at least one other login method remains.

A user MUST NOT remove their only usable login method.

Unlinking requires sensitive-action re-auth.

#### B.4.19 Audit events

Authentication audit events:

```text
LOGIN_STARTED
LOGIN_SUCCEEDED
LOGIN_FAILED
LOCAL_PASSWORD_LOGIN_SUCCEEDED
LOCAL_PASSWORD_LOGIN_FAILED
LOCAL_MFA_CHALLENGE_REQUIRED
LOCAL_MFA_CHALLENGE_PASSED
LOCAL_MFA_CHALLENGE_FAILED
OAUTH_LOGIN_STARTED
OAUTH_LOGIN_SUCCEEDED
OAUTH_LOGIN_FAILED
OAUTH_ACCOUNT_LINKED
OAUTH_ACCOUNT_UNLINKED
OAUTH_PROVIDER_MFA_TRUSTED
OAUTH_PROVIDER_MFA_NOT_TRUSTED
HANDOFF_TOKEN_ISSUED
HANDOFF_TOKEN_CONSUMED
HANDOFF_REPLAY_DETECTED
HANDOFF_HOST_MISMATCH
```

Audit metadata MAY include provider code and normalized outcome. Tokens, client secrets, authorization codes, refresh tokens, access tokens, ID tokens, TOTP secrets, and recovery codes MUST NOT be logged.

### B.5 Password, OAuth/OIDC, MFA, and Account Security

**Status: NORMATIVE.**

#### B.5.1 Account security posture

The platform supports both local password authentication and OAuth/OIDC authentication.

Password policy applies when a local password is set.

OAuth/OIDC users without local passwords MUST have unusable Django passwords.

A user MUST always have at least one usable login method unless the account is intentionally disabled.

#### B.5.2 Password policy

| Rule | Value |
| --- | --- |
| Minimum length | 12 characters |
| Maximum length | 256 characters |
| Character class requirements | None |
| Breached-password check | Required on every password set |
| Reuse prevention | Not enforced in v1 |
| Hashing | Django default hashers with Argon2 preferred |

#### B.5.3 Password rotation

| User class | Rotation requirement |
| --- | --- |
| Users with admin-class capabilities and local password | 90 days |
| Users with platform-class capabilities and local password | 90 days |
| Users using only OAuth/OIDC | No local password rotation |
| All other users | None forced |

#### B.5.4 Account lockout

Local password lockout applies only to local password login.

| Trigger | Action |
| --- | --- |
| 5 failed local password attempts within 15 minutes | Lock account for 15 minutes |
| 10 failed local password attempts within 1 hour | Lock account for 24 hours; emit `ACCOUNT_LOCKED`; notify user |
| Locked account login attempt | Reject with generic “credentials invalid” message |

OAuth/OIDC provider-side failures MUST be rate-limited and audited but MUST NOT increment local password failure counters unless the failure occurred in the local application.

#### B.5.5 OAuth/OIDC provider security

Provider configuration MUST enforce:

- HTTPS provider endpoints.
- Active provider allowlist.
- Configured client ID.
- Client secret loaded from approved secret source.
- Root-domain callback URL.
- `state` validation.
- `nonce` validation for OIDC.
- ID token signature validation for OIDC.
- Token expiry validation.
- Verified email requirement unless explicitly waived.
- Allowed email-domain restriction if configured.
- PKCE where supported.

Provider secrets MUST be masked in admin, logs, and audit output.

#### B.5.6 OAuth/OIDC account takeover protections

The system MUST prevent external login from taking over an existing account.

Rules:

1. Unverified provider emails MUST NOT link to existing users.
2. Provider subject ID is the stable identity key.
3. Email-based linking requires verified email and approved linking flow.
4. Existing users SHOULD confirm linking through local MFA or invite-token context.
5. Conflicting provider identities MUST stop the login and require support/admin resolution.
6. Provider tokens MUST NOT be stored unless explicitly required.
7. If tokens are stored later, they MUST be encrypted at rest and excluded from logs.

#### B.5.7 MFA supported methods

v1 required local MFA methods:

```text
totp
recovery_codes
```

Deferred local MFA methods:

```text
webauthn
passkeys
sms
email_otp
```

SMS MFA is rejected for v1.

#### B.5.8 MFA enrollment

MFA enrollment is required for:

- local-password users,
- support users,
- users whose OAuth/OIDC provider is not trusted for MFA,
- users performing sensitive local actions without trusted fresh provider authentication.

MFA enrollment MAY be skipped for normal tenant users only when all are true:

1. user logs in exclusively through OAuth/OIDC,
2. provider is approved,
3. provider is configured to enforce MFA,
4. platform policy marks provider MFA as trusted,
5. security review approves the provider’s MFA posture.

### B.5.9 Recovery codes

Recovery codes are required.

Rules:

- 10 recovery codes generated by default.
- Recovery codes are single-use.
- Recovery codes are stored hashed.
- Consumed codes are invalidated.
- Regenerating recovery codes invalidates all prior unused codes.
- Viewing/regenerating recovery codes requires sensitive-action re-auth.

#### B.5.10 Rate limiting

| Endpoint | Limit |
| --- | --- |
| `POST /login` | 5 per IP per minute, 20 per IP per hour |
| `POST /login/2fa` | 5 per session per minute |
| `GET /accounts/oidc/*/login/` | 20 per IP per minute |
| OAuth/OIDC callback | 30 per IP per minute |
| `POST /forgot-password` | 3 per email per hour, 10 per IP per hour |
| `POST /reset-password` | 5 per IP per minute |
| `POST /accept-invite` | 10 per IP per hour |
| `POST /handoff` | 20 per IP per minute |

#### B.5.11 Session security

Session security is defined in B.4.

Additional requirements:

- Session fixation protections MUST be preserved on login.
- Root-domain and tenant-local sessions are separate.
- Tenant-local logout MUST NOT destroy other tenant sessions.
- Root-domain logout MUST invalidate outstanding handoff tokens.
- Tenant-local sessions MUST be bound to membership id.

#### B.5.12 Security review requirements

Before enabling a production OAuth/OIDC provider, security review MUST verify:

1. callback URL configuration,
2. client secret storage,
3. provider allowlist,
4. email verification behavior,
5. MFA trust decision,
6. account linking behavior,
7. logging/audit masking,
8. no tokens or authorization codes are logged,
9. no provider claim grants roles or capabilities directly.

### B.6 RBAC Model: Roles, Capabilities, Grants, Scope

**Status: NORMATIVE.**

#### B.6.1 Three-layer enforcement

```text
1. Queryset scope:    .for_org(organization_id)
                      [.intersect_with_operating_scope(membership) for scoped models]
2. View capability:   require_capability("quotes.send")
3. Object check:      target.organization_id == membership.organization_id
                      AND check_operating_scope(membership, target)
                      AND any state/ownership predicates
4. Audit emission:    audit_emit("QUOTE_SENT", actor, target, metadata)
```

#### B.6.2 Permission evaluation algorithm

```text
1. If membership.user.is_superuser → GRANT (short-circuit)
2. If session.is_impersonating:
   - Use the impersonated membership for evaluation steps 3-8
   - Audit attribution remains the support user
3. If no membership for (user, organization) OR membership.status != ACTIVE → DENY
4. capabilities = union of capability codes from all roles assigned to membership
5. Apply MembershipCapabilityGrant overrides:
   - GRANT entries: add capability code to the set
   - DENY entries: remove capability code from the set (DENY beats GRANT)
6. If required_capability not in capabilities → DENY
7. If target_object is provided:
   - If target.organization_id != membership.organization_id → DENY
   - Apply state/ownership predicates from RBAC matrix → DENY on failure
8. If membership has scope assignments AND target carries location_id:
   - permitted_locations = closure of membership scope assignments
   - If target.location_id not in permitted_locations → DENY
9. GRANT
```

#### B.6.3 Capability registry

The full v1 capability set:

**Lead Management:** `leads.view`, `leads.create`, `leads.edit`, `leads.edit_any`, `leads.archive`, `leads.convert`, `leads.assign`

**Quote Management:** `quotes.view`, `quotes.create`, `quotes.edit`, `quotes.send`, `quotes.retract`, `quotes.approve`, `quotes.decline`, `quotes.line.override_price`, `quotes.line.apply_discount`, `quotes.delete_draft`

**Client Management:** `clients.view`, `clients.create`, `clients.edit`, `clients.merge`, `clients.deactivate`, `clients.contacts.manage`, `clients.locations.manage`

**Sales Order:** `orders.view`, `orders.edit`, `orders.cancel`, `orders.generate_fulfillment`

**Catalog:** `catalog.view`, `catalog.services.manage`, `catalog.products.manage`, `catalog.materials.manage`, `catalog.suppliers.manage`, `catalog.bom.manage`

**Pricing:** `pricing.rules.view`, `pricing.rules.manage`, `pricing.price_lists.manage`, `pricing.contracts.manage`, `pricing.labor_rates.manage`, `pricing.segments.manage`, `pricing.promotions.manage`, `pricing.bundles.manage`, `pricing.approval.request`, `pricing.approval.grant`

**Work Order:** `workorders.view`, `workorders.assign`, `workorders.update_status`, `workorders.manage`, `workorders.complete`, `workorders.view_all`

**Purchase Order:** `purchasing.view`, `purchasing.create`, `purchasing.edit`, `purchasing.submit`, `purchasing.receive`, `purchasing.cancel`

**Build Order:** `build.view`, `build.manage`, `build.labor.record`, `build.labor.edit_any`, `build.qa.review`, `build.cost.view`

**Billing:** `billing.view`, `billing.invoice.create`, `billing.invoice.send`, `billing.invoice.void`, `billing.payment.record`, `billing.payment.edit`, `billing.reports.view`

**Tasks:** `tasks.view`, `tasks.create`, `tasks.edit`, `tasks.assign`, `tasks.complete`, `tasks.manage`

**Communications:** `communications.view`, `communications.log`, `communications.send`, `communications.manage`

**Reporting:** `reporting.view`, `reporting.export`, `reporting.advanced`

**Tenant Administration:** `admin.members.view`, `admin.members.invite`, `admin.members.deactivate`, `admin.members.suspend`, `admin.roles.view`, `admin.roles.manage`, `admin.roles.assign`, `admin.capabilities.grant`, `admin.org.settings`, `admin.numbering.configure`, `admin.export.request`, `admin.deletion.request`, `admin.audit.view`

**Tax Configuration:** `tax.jurisdictions.manage`

#### B.6.4 Default roles

| Role | Intended For | Capability Set |
| --- | --- | --- |
| **Owner** | Tenant account owner | All capabilities |
| **Org Admin** | Office/operations manager | All except platform-level |
| **Regional Manager** | Regional level manager | All non-platform; restricted to assigned Region scope |
| **Market Manager** | Market level manager | All non-platform; restricted to assigned Market scope |
| **Location Manager** | Location level manager | All non-platform; restricted to assigned Location scope |
| **Sales Staff** | Salespeople | leads.*, quotes.view/create/edit/send, clients.view/create/edit, tasks.*, communications.*, orders.view, catalog.view, pricing.rules.view, pricing.approval.request |
| **Service Staff** | Field service worker | workorders.view/update_status/complete, tasks.view/complete, communications.view/log — own WOs/tasks |
| **Production Staff** | Shop floor | build.view/manage/labor.record, tasks.view/complete — own build orders/tasks |
| **Pricing Manager** | Pricing/contract administrator | catalog.view, pricing.*, quotes.view/edit/line.override_price/line.apply_discount |
| **Billing Staff** | A/R | billing.*, clients.view, orders.view, tasks.view/create |
| **Viewer** | Read-only stakeholder | *.view only |

#### B.6.5 New-capability propagation policy

When a new capability is added in a release:

1. Created via data migration.
2. Owner default role auto-extended.
3. Other default roles NOT auto-extended.
4. Existing custom (tenant-defined) roles NOT modified.

#### B.6.6 Capability deprecation

1. Deprecated capability remains functional for one major guide version.
2. CI surfaces a `DeprecationWarning`.
3. After one major version, the capability is removed.

#### B.6.7 RoleCapability and MembershipCapabilityGrant

```text
Capability
  id: UUID, pk
  code: TEXT, unique
  name: TEXT
  description: TEXT
  category: TEXT
  is_deprecated: BOOL, default(false)
  deprecated_in_version: TEXT, null
  deprecated_replacement_code: TEXT, null

Role
  id: UUID, pk
  organization_id: UUID, fk -> Organization, null
  code: TEXT
  name: TEXT
  description: TEXT
  is_default: BOOL, default(false)
  is_scoped_role: BOOL, default(false)
  is_locked: BOOL, default(false)
  unique_together (organization_id, code)

RoleCapability
  id: UUID, pk
  role_id: UUID, fk -> Role on_delete=CASCADE
  capability_id: UUID, fk -> Capability on_delete=PROTECT
  unique_together (role_id, capability_id)

MembershipRole
  id: UUID, pk
  membership_id: UUID, fk -> Membership on_delete=CASCADE
  role_id: UUID, fk -> Role on_delete=PROTECT
  assigned_by_id: UUID, fk -> User
  assigned_at: TIMESTAMPTZ
  unique_together (membership_id, role_id)

MembershipCapabilityGrant
  id: UUID, pk
  membership_id: UUID, fk -> Membership on_delete=CASCADE
  capability_id: UUID, fk -> Capability on_delete=PROTECT
  grant_type: ENUM(GRANT, DENY)
  reason: TEXT
  granted_by_id: UUID, fk -> User
  granted_at: TIMESTAMPTZ
  unique_together (membership_id, capability_id)
```

#### B.6.8 Decorator and mixin shapes

```python
# View decorator (Phase 1)
@require_capability("quotes.send")
def quote_send_view(request, quote_version_id):
    membership = get_active_membership(request)
    quote_version = QuoteVersion.objects.for_membership(membership).get(id=quote_version_id)
    enforce_object_access(membership, quote_version)
    enforce_state(quote_version, expected={QuoteVersionStatus.DRAFT})
    services.send_quote(
        organization_id=membership.organization_id,
        actor_id=membership.user_id,
        quote_version_id=quote_version.id,
    )

# DRF mixin (Phase 2)
class CapabilityRequiredMixin:
    required_capability: str = None

    def check_permissions(self, request):
        super().check_permissions(request)
        membership = get_active_membership_for_request(request)
        if not has_capability(membership, self.required_capability):
            raise PermissionDenied(self.required_capability)

class TenantScopedQuerysetMixin:
    def get_queryset(self):
        membership = get_active_membership_for_request(self.request)
        return self.model.objects.for_membership(membership)
```

#### B.6.9 Capability-coverage CI test

A CI test enumerates all URL patterns and asserts each one is either decorated with `@require_capability(...)`, OR listed in an explicit allowlist `apps/platform/rbac/exempt_urls.py` with a one-line justification.

### B.7 Support User Access and Impersonation

**Status: NORMATIVE.**

#### B.7.1 Platform console as support landing surface

Support Users (`is_staff=true`) authenticated through the central login form land on the **platform console** at `https://mypipelinehero.com/platform/`.

#### B.7.2 Tenant search/list UX

The platform console homepage shows:

- A tenant search box (by name, slug, primary contact email).
- A "Recent tenants" list.
- A link to "All tenants" with filters.

#### B.7.3 Impersonation start

A Support User initiates impersonation by:

1. Locating the target tenant.
2. Selecting a target Membership.
3. Submitting a **reason** (free text, required, minimum 10 chars).
4. Completing sensitive-action re-auth.

On confirmation:

1. Application emits `IMPERSONATION_STARTED` audit.
2. Application creates an `ImpersonationAuditLog` row.
3. Application establishes a **tenant-local session on the target tenant subdomain** with impersonation flags set.
4. Application redirects to the tenant subdomain.

#### B.7.4 Impersonation banner

While `session["is_impersonating"] == True`, every page rendered on the tenant subdomain MUST include an impersonation banner. The banner is rendered by the **base template** as a server-side fragment, NOT by client-side JavaScript.

```text
[!] Impersonating {target_user.email} on {organization.name}
    Started by {support_user.email} at {started_at}
    Reason: {reason}
    [End Impersonation]
```

CSP and template structure MUST be such that the banner cannot be hidden via DOM manipulation in normal use.

#### B.7.5 Permission evaluation during impersonation

Capability evaluation uses the **impersonated membership's capabilities**, not the support user's. Audit attribution: actor is the Support User; on_behalf_of is the impersonated user.

#### B.7.6 Impersonation log

```text
ImpersonationAuditLog
  id: UUID, pk
  support_user_id: UUID, fk -> User on_delete=PROTECT
  target_user_id: UUID, fk -> User on_delete=PROTECT
  target_membership_id: UUID, fk -> Membership on_delete=PROTECT
  organization_id: UUID, fk -> Organization on_delete=PROTECT
  reason: TEXT
  session_id: TEXT
  client_ip: INET
  client_user_agent: TEXT
  started_at: TIMESTAMPTZ
  ended_at: TIMESTAMPTZ, null
  ended_by: ENUM(USER_ACTION, SESSION_EXPIRY, FORCE_TERMINATED), null
  total_actions_taken: INT, default(0)
  retention_until: TIMESTAMPTZ                 -- locked at start, 7-year retention
```

ImpersonationAuditLog rows are NEVER deleted within retention. Tenant deletion does not remove these rows.

#### B.7.7 Impersonation end

1. **User-initiated.** Clicks "End Impersonation" → tenant-local session destroyed.
2. **Session expiry.** Tenant-local session reaches idle expiry.
3. **Force terminated.** Another support user ends an in-progress impersonation.

#### B.7.8 Impersonation restrictions

- A Support User MAY NOT impersonate another `is_staff=true` user.
- A Support User MAY NOT impersonate across organizations within a single session.
- Impersonation sessions have a maximum duration of **2 hours absolute cap**.
- A Support User MAY NOT initiate impersonation while themselves logged into a tenant via direct membership.

---

## Part C — Domain Model and State Machines

### C.1 Data Model Inventory (Authoritative)

**Status: NORMATIVE.**

This section is the authoritative entity inventory for v1. Cross-references: Identity entities (User, Organization, Membership, Role, Capability) are defined in B.1, B.3, B.6. Operating-scope entities (Region, Market, Location, MembershipScopeAssignment) are defined in B.2.

#### C.1.1 ID strategy and conventions

| Entity class | PK type | Rationale |
| --- | --- | --- |
| All org-facing entities | UUID v7 | Sortable by creation, B-tree-friendly |
| User, Membership, Organization | UUID v7 | Same |
| AuditEvent | BigInt | High volume |
| PricingSnapshot | BigInt | High volume |
| OutboxEntry | BigInt | High volume |
| Sequence/numbering atomic counters | Postgres `BIGSERIAL` | Native, atomic |

**UUID v7 generation.** Use `uuid6.uuid7()` in application code.

**Audit columns.** Every mutable tenant-owned entity carries: `created_at`, `updated_at`, `created_by_id`, `updated_by_id`.

**Soft-delete pattern.** Entities permitted soft delete carry `deleted_at: TIMESTAMPTZ, null` plus `deleted_by_id`. Org-scoped uniqueness uses partial indexes (`WHERE deleted_at IS NULL`).

#### C.1.2 Lead domain

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
  qualified_at: TIMESTAMPTZ, null
  unqualified_at: TIMESTAMPTZ, null
  unqualified_reason: TEXT, null
  archived_at: TIMESTAMPTZ, null
  converted_at: TIMESTAMPTZ, null
  converted_to_quote_id: UUID, fk -> Quote, null

  unique_together (organization_id, number)
  index (organization_id, status)
  index (organization_id, owner_membership_id, status)
  index (organization_id, location_id)
  index (organization_id, created_at DESC)

LeadContact
  id: UUID, pk
  organization_id: UUID, fk -> Organization on_delete=PROTECT
  lead_id: UUID, fk -> Lead on_delete=CASCADE
  first_name: TEXT
  last_name: TEXT
  email: TEXT, null
  phone: TEXT, null
  role_title: TEXT, null
  is_primary: BOOL, default(false)
  partial_index (lead_id) where is_primary

LeadLocation
  id: UUID, pk
  organization_id: UUID, fk -> Organization on_delete=PROTECT
  lead_id: UUID, fk -> Lead on_delete=CASCADE
  label: TEXT
  address_line1, address_line2, city, region_admin, postal_code, country: TEXT
  notes: TEXT, null
```

`LeadLocation` (the physical site of the prospective work) is distinct from `Location` (the operating-scope entity).

#### C.1.3 Quote domain

```text
Quote                                                      -- container; stable across versions
  id: UUID, pk
  organization_id: UUID, fk -> Organization on_delete=PROTECT
  location_id: UUID, fk -> Location on_delete=PROTECT
  number: TEXT                                            -- "QT-2026-00042"
  lead_id: UUID, fk -> Lead on_delete=PROTECT, null
  client_id: UUID, fk -> Client on_delete=PROTECT, null

  unique_together (organization_id, number)
  CHECK: at least one of (lead_id, client_id) is non-null

QuoteVersion
  id: UUID, pk
  organization_id: UUID, fk -> Organization on_delete=PROTECT
  quote_id: UUID, fk -> Quote on_delete=PROTECT
  version_number: INT
  status: ENUM(DRAFT, SENT, ACCEPTED, DECLINED, EXPIRED, RETRACTED, SUPERSEDED)
  expiration_date: DATE, null
  subtotal_amount: NUMERIC(14,2)
  discount_amount: NUMERIC(14,2), default(0)
  tax_amount: NUMERIC(14,2)
  total_amount: NUMERIC(14,2)
  currency_code: CHAR(3)
  notes: TEXT, null
  internal_notes: TEXT, null
  terms: TEXT, null
  sent_at: TIMESTAMPTZ, null
  sent_by_id: UUID, fk -> User on_delete=PROTECT, null
  sent_to_emails: TEXT[], null
  accepted_at: TIMESTAMPTZ, null
  accepted_by_id: UUID, fk -> User on_delete=PROTECT, null
  declined_at: TIMESTAMPTZ, null
  expired_at: TIMESTAMPTZ, null
  retracted_at: TIMESTAMPTZ, null
  retracted_by_id: UUID, fk -> User on_delete=PROTECT, null
  retracted_reason: TEXT, null
  superseded_at: TIMESTAMPTZ, null
  superseded_by_version_id: UUID, fk -> QuoteVersion on_delete=PROTECT, null
  optimistic_version: INT, default(0)

  unique_together (quote_id, version_number)
  partial_index (quote_id) where status = 'ACCEPTED'

QuoteVersionLine
  id: UUID, pk
  organization_id: UUID, fk -> Organization on_delete=PROTECT
  quote_version_id: UUID, fk -> QuoteVersion on_delete=PROTECT
  sort_order: INT
  line_type: ENUM(SERVICE, RESALE_PRODUCT, MANUFACTURED_PRODUCT, BUNDLE)
  service_id: UUID, fk -> Service on_delete=PROTECT, null
  product_id: UUID, fk -> Product on_delete=PROTECT, null
  bundle_definition_id: UUID, fk -> BundleDefinition on_delete=PROTECT, null
  selected_supplier_id: UUID, fk -> Supplier on_delete=PROTECT, null
  selected_bom_version_id: UUID, fk -> BOMVersion on_delete=PROTECT, null
  description_snapshot: TEXT
  quantity: NUMERIC(14,4)
  unit_of_measure: TEXT
  unit_price_snapshot: NUMERIC(14,4)
  line_subtotal: NUMERIC(14,2)
  line_discount_amount: NUMERIC(14,2), default(0)
  line_total: NUMERIC(14,2)
  taxable: BOOL, default(true)
  pricing_snapshot_id: BIGINT, fk -> PricingSnapshot on_delete=PROTECT
  pending_pricing_approval_id: UUID, fk -> PricingApproval, null
  selected_options_json: JSONB, null   -- for CONFIGURABLE bundles (E.4.3)

  CHECK: exactly one of (service_id, product_id, bundle_definition_id) is non-null
  CHECK: line_type matches the populated FK

QuoteVersionDiscount
  id: UUID, pk
  organization_id: UUID, fk -> Organization on_delete=PROTECT
  quote_version_id: UUID, fk -> QuoteVersion on_delete=CASCADE
  discount_type: ENUM(PERCENTAGE, FIXED_AMOUNT)
  value: NUMERIC(14,4)
  reason: TEXT, null
  applied_by_id: UUID, fk -> User on_delete=PROTECT
  applied_at: TIMESTAMPTZ
```

#### C.1.4 Client domain

```text
Client
  id: UUID, pk
  organization_id: UUID, fk -> Organization on_delete=PROTECT
  location_id: UUID, fk -> Location on_delete=PROTECT
  number: TEXT
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
  id: UUID, pk
  organization_id: UUID, fk -> Organization on_delete=PROTECT
  client_id: UUID, fk -> Client on_delete=CASCADE
  first_name, last_name: TEXT
  email, phone, role_title: TEXT, null
  is_primary: BOOL, default(false)
  is_billing_contact: BOOL, default(false)

ClientLocation
  id: UUID, pk
  organization_id: UUID, fk -> Organization on_delete=PROTECT
  client_id: UUID, fk -> Client on_delete=CASCADE
  label: TEXT
  address_line1, address_line2, city, region_admin, postal_code, country: TEXT
  is_billing: BOOL, default(false)
  is_service: BOOL, default(false)
  is_install: BOOL, default(false)
  notes: TEXT, null
  CHECK: at least one of (is_billing, is_service, is_install) is true
```

#### C.1.5 Sales order domain

```text
SalesOrder
  id: UUID, pk
  organization_id: UUID, fk -> Organization on_delete=PROTECT
  location_id: UUID, fk -> Location on_delete=PROTECT
  number: TEXT
  client_id: UUID, fk -> Client on_delete=PROTECT
  originating_quote_version_id: UUID, fk -> QuoteVersion on_delete=PROTECT
  status: ENUM(OPEN, IN_FULFILLMENT, FULFILLED, PART_INVOICED, INVOICED, CLOSED, CANCELLED)
  subtotal_amount, discount_amount, tax_amount, total_amount: NUMERIC(14,2)
  currency_code: CHAR(3)
  notes: TEXT, null
  cancelled_at: TIMESTAMPTZ, null
  cancelled_by_id: UUID, fk -> User, null
  cancelled_reason: TEXT, null
  external_id: TEXT, null

SalesOrderLine
  id: UUID, pk
  organization_id: UUID, fk -> Organization on_delete=PROTECT
  sales_order_id: UUID, fk -> SalesOrder on_delete=PROTECT
  source_quote_version_line_id: UUID, fk -> QuoteVersionLine on_delete=PROTECT
  parent_sales_order_line_id: UUID, fk -> SalesOrderLine, null  -- bundle children (D.4.2)
  sort_order: INT
  line_type: ENUM(SERVICE, RESALE_PRODUCT, MANUFACTURED_PRODUCT, BUNDLE)
  description_snapshot: TEXT
  quantity: NUMERIC(14,4)
  unit_of_measure: TEXT
  unit_price_snapshot: NUMERIC(14,4)
  line_subtotal: NUMERIC(14,2)
  line_discount_amount: NUMERIC(14,2)
  line_total: NUMERIC(14,2)
  taxable: BOOL
  pricing_snapshot_id: BIGINT, fk -> PricingSnapshot on_delete=PROTECT
  fulfillment_status: ENUM(PENDING, IN_PROGRESS, FULFILLED, CANCELLED, NOT_APPLICABLE)
  invoice_eligibility: ENUM(NOT_YET, ELIGIBLE, INVOICED, NOT_INVOICEABLE)
```

#### C.1.6 Tasks and communications

```text
Task
  id: UUID, pk
  organization_id: UUID, fk -> Organization on_delete=PROTECT
  title: TEXT
  description: TEXT, null
  status: ENUM(OPEN, IN_PROGRESS, BLOCKED, COMPLETED, CANCELLED)
  priority: ENUM(LOW, NORMAL, HIGH, URGENT), default(NORMAL)
  due_at: TIMESTAMPTZ, null
  assigned_to_id: UUID, fk -> Membership on_delete=PROTECT, null
  blocked_reason: TEXT, null
  completed_at, completed_by_id, completion_notes
  cancelled_at, cancelled_by_id, cancelled_reason
  reopened_at, reopened_by_id, reopened_reason

TaskLink
  id: UUID, pk
  organization_id: UUID, fk
  task_id: UUID, fk -> Task on_delete=CASCADE
  lead_id, quote_id, client_id, sales_order_id, work_order_id,
  build_order_id, purchase_order_id, invoice_id: UUID, fk, null
  organization_operation_label: TEXT, null

  CHECK (num_nonnulls(...) = 1)

Communication
  id: UUID, pk
  organization_id: UUID, fk
  direction: ENUM(INBOUND, OUTBOUND)
  channel: ENUM(EMAIL, CALL_NOTE, MANUAL_NOTE)
  subject: TEXT, null
  body: TEXT
  body_hash: TEXT
  participants: JSONB
  occurred_at: TIMESTAMPTZ
  sent_at: TIMESTAMPTZ, null
  delivery_status: ENUM(NOT_APPLICABLE, QUEUED, SENT, DELIVERED, BOUNCED, FAILED)
  provider_message_id: TEXT, null
  provider_metadata: JSONB, null

CommunicationLink
  -- identical pattern to TaskLink
```

#### C.1.7 Document attachments

```text
DocumentAttachment
  id: UUID, pk
  organization_id: UUID, fk
  document_kind: ENUM(QUOTE_PDF, INVOICE_PDF, COMPLETION_PHOTO, SUPPORTING_DOC,
                       EXPORT_ARCHIVE, OTHER)
  storage_key: TEXT
  original_filename: TEXT
  content_type: TEXT
  size_bytes: BIGINT
  uploaded_by_id: UUID, fk -> User on_delete=PROTECT, null
  visibility: ENUM(INTERNAL, TENANT_USERS, EXTERNAL_LINK)
  malware_scan_status: ENUM(PENDING, CLEAN, INFECTED, SKIPPED), default(SKIPPED)
  malware_scan_at: TIMESTAMPTZ, null
  retention_until: TIMESTAMPTZ, null

DocumentAttachmentLink
  -- typed link table same as TaskLink
```

#### C.1.8 Catalog domain

```text
ServiceCategory
  id: UUID, pk
  organization_id, code, name, is_active
  unique_together (organization_id, code)

Service
  id: UUID, pk
  organization_id, category_id, code, name, description
  catalog_price: NUMERIC(14,4)
  default_pricing_strategy_code: TEXT
  default_unit_of_measure: TEXT
  is_active: BOOL, default(true)

Product
  id: UUID, pk
  organization_id, code, name, description
  product_type: ENUM(RESALE, MANUFACTURED)
  default_pricing_strategy_code: TEXT
  default_unit_of_measure: TEXT
  default_markup_percent: NUMERIC(7,4), null
  default_target_margin_percent: NUMERIC(7,4), null
  is_active: BOOL, default(true)
  CHECK: not (default_markup_percent IS NOT NULL AND default_target_margin_percent IS NOT NULL)

RawMaterial
  id: UUID, pk
  organization_id, code, name, description
  unit_of_measure: TEXT
  current_cost: NUMERIC(14,6)
  current_cost_effective_from: DATE
  is_active: BOOL, default(true)

Supplier
  id: UUID, pk
  organization_id, code, name
  contact_email, contact_phone: TEXT, null
  default_lead_time_days: INT, null
  is_active: BOOL, default(true)

SupplierProduct
  id: UUID, pk
  organization_id, supplier_id
  product_id: null
  raw_material_id: null
  supplier_sku: TEXT
  cost: NUMERIC(14,6)
  cost_effective_from: DATE
  cost_effective_until: DATE, null
  lead_time_days: INT, null
  is_preferred: BOOL, default(false)
  CHECK: exactly one of (product_id, raw_material_id) is non-null
```

#### C.1.9 BOM domain

```text
BOM
  id: UUID, pk
  organization_id, product_id (unique per product)
  CHECK: product_id resolves to a MANUFACTURED product

BOMVersion
  id: UUID, pk
  organization_id, bom_id
  version_number: INT
  status: ENUM(DRAFT, ACTIVE, SUPERSEDED)
  effective_from: DATE
  effective_until: DATE, null
  notes: TEXT, null
  activated_at, superseded_at: TIMESTAMPTZ, null
  partial_unique (bom_id) where status = 'ACTIVE'

BOMLine
  id: UUID, pk
  organization_id, bom_version_id
  raw_material_id: UUID, fk
  quantity: NUMERIC(14,6)
  unit_of_measure: TEXT
  cost_basis_at_creation: NUMERIC(14,6)
  notes: TEXT, null
```

#### C.1.10 Pricing domain

```text
PricingRule
  id: UUID, pk
  organization_id, code, name, description
  rule_type: ENUM(STRATEGY_OVERRIDE, MARKUP_OVERRIDE, MARGIN_OVERRIDE, MODIFIER_PARAMETER,
                   APPROVAL_THRESHOLD)
  target_line_type: ENUM(SERVICE, RESALE_PRODUCT, MANUFACTURED_PRODUCT, BUNDLE, ANY)
  target_item_type: ENUM(SERVICE, PRODUCT, RAW_MATERIAL, BUNDLE, NONE), default(NONE)
  target_item_id: UUID, null
  target_client_id, target_customer_segment_id, target_region_id, target_market_id,
  target_location_id, target_supplier_id: UUID, fk, null
  priority: INT
  effective_from: DATE
  effective_until: DATE, null
  parameters_json: JSONB
  is_active: BOOL, default(true)

PriceList
  id: UUID, pk
  organization_id, code, name, description
  currency_code: CHAR(3)
  effective_from: DATE
  effective_until: DATE, null
  status: ENUM(DRAFT, ACTIVE, SUPERSEDED)

PriceListItem
  id: UUID, pk
  organization_id, price_list_id
  line_type: ENUM(SERVICE, RESALE_PRODUCT, MANUFACTURED_PRODUCT, BUNDLE)
  service_id, product_id, bundle_definition_id: UUID, fk, null
  unit_price: NUMERIC(14,4)
  minimum_quantity, maximum_quantity: NUMERIC(14,4), null
  parameters_json: JSONB, null
  CHECK: exactly one of (service_id, product_id, bundle_definition_id) is non-null

ClientContractPricing
  id: UUID, pk
  organization_id, client_id
  contract_name: TEXT
  effective_from: DATE
  effective_until: DATE, null
  price_list_id: UUID, fk -> PriceList, null
  terms: TEXT, null
  status: ENUM(DRAFT, ACTIVE, EXPIRED, TERMINATED)
  partial_index (client_id) where status = 'ACTIVE'

LaborRateCard
  id: UUID, pk
  organization_id, code, name
  effective_from: DATE
  effective_until: DATE, null
  status: ENUM(DRAFT, ACTIVE, SUPERSEDED)
  -- partial_unique (organization_id) where status='ACTIVE'    [propagated from E.3.5]

LaborRateCardLine
  id: UUID, pk
  organization_id, rate_card_id
  labor_role: TEXT
  internal_cost_rate: NUMERIC(14,4)
  bill_rate: NUMERIC(14,4)
  currency_code: CHAR(3)

CustomerSegment
  id: UUID, pk
  organization_id, code, name
  default_multiplier: NUMERIC(7,4)
  is_default: BOOL, default(false)
  partial_unique (organization_id) where is_default

PromotionCampaign
  id: UUID, pk
  organization_id, code, name, description
  effective_from: DATE
  effective_until: DATE
  discount_type: ENUM(PERCENTAGE, FIXED_AMOUNT)
  discount_value: NUMERIC(14,4)
  applies_to_line_types: TEXT[]
  eligibility_rules_json: JSONB
  is_active: BOOL, default(true)

PromotionUsage                                    -- propagated from E.4.2
  id: UUID, pk
  organization_id, promotion_id, client_id, quote_version_id
  applied_at: TIMESTAMPTZ
  index (organization_id, promotion_id, client_id)

BundleDefinition
  id: UUID, pk
  organization_id, code, name, description
  bundle_type: ENUM(COMPONENT_SUM, FIXED_PRICE, CONFIGURABLE)
  fixed_price: NUMERIC(14,4), null
  base_price: NUMERIC(14,4), null
  bundle_discount_amount: NUMERIC(14,4), default(0)
  is_active: BOOL, default(true)

BundleComponent
  id: UUID, pk
  organization_id, bundle_definition_id
  service_id, product_id: null
  quantity: NUMERIC(14,4)
  is_required: BOOL, default(true)
  option_unit_price: NUMERIC(14,4), null
  CHECK: exactly one of (service_id, product_id) is non-null

PricingApproval
  id: UUID, pk
  organization_id, number
  quote_version_id: UUID, fk
  quote_version_line_id: UUID, fk, null
  status: ENUM(REQUESTED, APPROVED, REJECTED, EXPIRED, WITHDRAWN)
  reason_code: ENUM(MANUAL_OVERRIDE, DISCOUNT_THRESHOLD, BELOW_FLOOR, BELOW_MARGIN,
                     CONTRACT_DEVIATION, VALUE_BASED, OTHER)
  reason_notes: TEXT
  calculated_price, requested_price: NUMERIC(14,4)
  floor_price: NUMERIC(14,4), null
  calculated_margin_percent, minimum_margin_percent: NUMERIC(7,4), null
  requested_by_id, requested_at
  decided_by_id, decided_at, decision_notes
  expires_at: TIMESTAMPTZ                      -- 7 days from requested_at default

PricingSnapshot                                 -- BIGINT pk; partitioned by created_at month
  id: BIGSERIAL, pk
  organization_id: UUID, fk
  quote_version_line_id: UUID, fk, null
  invoice_line_id: UUID, fk, null
  line_type, is_active, engine_version, strategy_code
  modifiers_applied: JSONB
  inputs: JSONB
  outputs: JSONB
  effective_unit_price: NUMERIC(14,4)
  effective_line_total: NUMERIC(14,2)
  override_applied: BOOL, default(false)
  approval_required: BOOL, default(false)
  approval_id: UUID, fk -> PricingApproval, null
  created_at: TIMESTAMPTZ                       -- partition key
  created_by_id: UUID, fk -> User, null

  partition by RANGE (created_at)               -- monthly partitions
```

#### C.1.11 Tax domain

```text
TaxJurisdiction
  id: UUID, pk
  organization_id, code, name
  parent_jurisdiction_id: UUID, fk -> TaxJurisdiction, null  -- hierarchical
  is_active: BOOL, default(true)

TaxRate
  id: UUID, pk
  organization_id, tax_jurisdiction_id
  rate_type: ENUM(SALES, USE, EXCISE, OTHER), default(SALES)
  rate_percent: NUMERIC(7,4)                                -- 8.2500 = 8.25%
  effective_from: DATE
  effective_until: DATE, null
  applies_to_line_types: TEXT[], null
  is_active: BOOL, default(true)
```

#### C.1.12 Procurement and manufacturing

```text
PurchaseOrder
  id: UUID, pk
  organization_id, location_id, number
  supplier_id: UUID, fk -> Supplier
  status: ENUM(DRAFT, SUBMITTED, ACKNOWLEDGED, PART_RECEIVED, RECEIVED, CANCELLED)
  ordered_at: TIMESTAMPTZ, null
  expected_delivery_date: DATE, null
  subtotal_amount, tax_amount, total_amount: NUMERIC(14,2)
  currency_code: CHAR(3)
  notes, cancelled_reason, external_id

PurchaseOrderLine
  id: UUID, pk
  organization_id, purchase_order_id
  product_id, raw_material_id: UUID, null
  description_snapshot: TEXT
  quantity_ordered: NUMERIC(14,4)
  quantity_received: NUMERIC(14,4), default(0)
  unit_cost: NUMERIC(14,6)
  unit_of_measure: TEXT
  CHECK: exactly one of (product_id, raw_material_id) is non-null

PurchaseAllocation
  id: UUID, pk
  organization_id, sales_order_line_id, purchase_order_line_id
  allocated_quantity: NUMERIC(14,4)

BuildOrder
  id: UUID, pk
  organization_id, location_id, number
  source_sales_order_line_id: UUID, fk -> SalesOrderLine, unique
  planned_bom_version_id: UUID, fk -> BOMVersion
  status: ENUM(PLANNED, IN_PROGRESS, ON_HOLD, QUALITY_REVIEW, COMPLETE, CANCELLED)
  estimated_material_cost, estimated_labor_cost: NUMERIC(14,2)
  actual_material_cost, actual_labor_cost: NUMERIC(14,2), default(0)
  started_at, completed_at: TIMESTAMPTZ, null
  hold_reason, cancelled_reason: TEXT, null
  qa_approved_by_id: UUID, fk -> User, null
  qa_rejection_notes: TEXT, null

BuildBOMSnapshot
  id: UUID, pk
  organization_id, build_order_id (unique)
  source_bom_version_id: UUID, fk
  snapshot_payload: JSONB                       -- fully denormalized BOM lines + costs
  captured_at, captured_by_id

BuildLaborEntry
  id: UUID, pk
  organization_id, build_order_id, user_id
  labor_role: TEXT
  hours: NUMERIC(7,2)
  applied_internal_rate, applied_bill_rate: NUMERIC(14,4)
  applied_rate_card_id: UUID, fk -> LaborRateCard, null
  notes: TEXT, null
  occurred_on: DATE
  -- append-only

BuildLaborAdjustment
  id: UUID, pk
  organization_id, original_entry_id
  adjustment_type: ENUM(REVERSAL, CORRECTION)
  hours_delta: NUMERIC(7,2)
  internal_cost_delta: NUMERIC(14,4)
  reason: TEXT
  adjusted_by_id

WorkOrder
  id: UUID, pk
  organization_id, location_id, number
  source_sales_order_line_id: UUID, fk -> SalesOrderLine, unique
  client_id: UUID, fk -> Client
  client_location_id: UUID, fk -> ClientLocation, null
  status: ENUM(PENDING, ASSIGNED, IN_PROGRESS, ON_HOLD, COMPLETED, CANCELLED)
  assigned_to_membership_id: UUID, fk -> Membership, null
  scheduled_date: DATE, null
  scheduled_start_time: TIMESTAMPTZ, null
  started_at, completed_at: TIMESTAMPTZ, null
  outcome_notes: TEXT, null
  hold_reason, cancelled_reason: TEXT, null
  recurrence_template_id: UUID, null              -- reserved; null in v1
```

#### C.1.13 Billing domain

```text
InvoicingPolicy
  id: UUID, pk
  organization_id (unique)
  service_invoiceable_on: ENUM(WORK_ORDER_COMPLETE, MANUAL_RELEASE), default(WORK_ORDER_COMPLETE)
  resale_invoiceable_on: ENUM(PO_RECEIPT, MANUAL_RELEASE), default(PO_RECEIPT)
  manufactured_invoiceable_on: ENUM(BUILD_ORDER_COMPLETE, MANUAL_RELEASE), default(BUILD_ORDER_COMPLETE)
  bundle_invoiceable_on: ENUM(ALL_COMPONENTS_ELIGIBLE, MANUAL_RELEASE), default(ALL_COMPONENTS_ELIGIBLE)
  default_payment_terms_days: INT, default(30)
  rounding_policy: ENUM(NEAREST_CENT, NEAREST_DOLLAR, ROUND_UP_5, ROUND_UP_10), default(NEAREST_CENT)

Invoice
  id: UUID, pk
  organization_id, location_id, number
  client_id, sales_order_id
  status: ENUM(DRAFT, SENT, OVERDUE, PART_PAID, PAID, VOID)
  currency_code: CHAR(3)
  subtotal_amount, tax_amount, total_amount: NUMERIC(14,2)
  amount_paid: NUMERIC(14,2), default(0)
  balance_due: NUMERIC(14,2)
  issue_date, due_date: DATE
  sent_at, voided_at: TIMESTAMPTZ, null
  voided_by_id: UUID, fk -> User, null
  voided_reason: TEXT, null
  external_id: TEXT, null
  sync_status: ENUM(NOT_SYNCED, PENDING, SYNCED, FAILED), default(NOT_SYNCED)
  sync_error: TEXT, null

InvoiceLine
  id: UUID, pk
  organization_id, invoice_id
  source_sales_order_line_id: UUID, fk
  pricing_snapshot_id: BIGINT, fk
  description_snapshot: TEXT
  quantity: NUMERIC(14,4)
  unit_price_snapshot: NUMERIC(14,4)
  line_subtotal: NUMERIC(14,2)
  taxable: BOOL
  tax_amount: NUMERIC(14,2)
  line_total: NUMERIC(14,2)

Payment                                           -- append-only
  id: UUID, pk
  organization_id, client_id
  amount: NUMERIC(14,2)
  payment_date: DATE
  method: ENUM(CASH, CHECK, ACH, WIRE, CARD, OTHER)
  reference: TEXT, null
  notes: TEXT, null
  unapplied_amount: NUMERIC(14,2)
  external_id: TEXT, null

PaymentAllocation
  id: UUID, pk
  organization_id, payment_id, invoice_id
  amount_applied: NUMERIC(14,2)
  applied_at, applied_by_id
  reversed_at, reversed_by_id, reversed_reason

PaymentAdjustment
  id: UUID, pk
  organization_id, original_payment_id
  adjustment_type: ENUM(REVERSAL, CORRECTION)
  amount_delta: NUMERIC(14,2)
  reason: TEXT
  created_by_id
```

#### C.1.14 Audit and outbox

```text
AuditEvent                                         -- BIGINT pk, partitioned by event_at month
  id: BIGSERIAL, pk
  organization_id: UUID, fk, null
  actor_id: UUID, fk -> User, null
  on_behalf_of_id: UUID, fk -> User, null
  event_type: TEXT
  event_category: ENUM(AUTHENTICATION, AUTHORIZATION, STATE_TRANSITION, DATA_ACCESS,
                        ADMIN, IMPERSONATION, PRICING, BILLING, EXPORT, DELETION)
  schema_version: INT, default(1)
  object_kind, object_id: TEXT
  request_id, tenant_host: TEXT, null
  source_ip: INET, null
  user_agent: TEXT, null
  payload_before, payload_after: JSONB, null     -- masked per G.5 rules
  metadata: JSONB, null
  event_at: TIMESTAMPTZ                          -- partition key

  partition by RANGE (event_at)

OutboxEntry
  id: BIGSERIAL, pk
  organization_id: UUID, null
  topic: TEXT
  idempotency_key: TEXT
  payload: JSONB
  status: ENUM(PENDING, DISPATCHED, CONSUMED, FAILED, DEAD_LETTER)
  attempts: INT, default(0)
  next_attempt_at: TIMESTAMPTZ
  last_error: TEXT, null
  created_at, dispatched_at, consumed_at

  unique_together (topic, idempotency_key)

OutboxDeadLetter
  id: BIGSERIAL, pk
  source_outbox_id: BIGINT
  failed_at: TIMESTAMPTZ
  attempts: INT
  last_error: TEXT
  payload_snapshot: JSONB
```

#### C.1.15 Numbering and sequences

```text
EntityNumberSequence
  id: BIGSERIAL, pk
  organization_id: UUID, fk -> Organization on_delete=PROTECT
  entity_kind: ENUM(LEAD, QUOTE, SALES_ORDER, PURCHASE_ORDER, BUILD_ORDER, WORK_ORDER,
                     INVOICE, PRICING_APPROVAL, CLIENT, PRICE_LIST)
  year: INT
  next_value: BIGINT, default(1)
  prefix: TEXT

  unique_together (organization_id, entity_kind, year)
```

#### C.1.16 Tenant lifecycle entities (added from G.7)

```text
TenantExportRequest
  id: UUID, pk
  organization_id: UUID, fk -> Organization
  requested_by_id: UUID, fk -> User
  requested_at: TIMESTAMPTZ
  requested_scope: ENUM(FULL, COMMERCIAL_ONLY, AUDIT_ONLY)
  status: ENUM(QUEUED, ASSEMBLING, READY, DOWNLOADED, EXPIRED, FAILED, CANCELLED)
  output_attachment_id: UUID, fk -> DocumentAttachment, null
  expires_at: TIMESTAMPTZ
  failure_reason: TEXT, null
  bytes_size, row_count: BIGINT, null
  cancelled_at, cancelled_by_id

TenantDeletionRequest
  id: UUID, pk
  organization_id: UUID, fk -> Organization
  requested_by_id: UUID, fk -> User
  requested_at: TIMESTAMPTZ
  status: ENUM(GRACE_PERIOD, EXECUTING, EXECUTED, CANCELLED)
  grace_period_ends_at: TIMESTAMPTZ
  confirmation_phrase_provided: TEXT
  cancelled_at, cancelled_by_id, cancelled_reason
  executed_at, executed_by_id
  rows_deleted_per_table: JSONB, null
```

### C.2 State Machines (Authoritative)

**Status: NORMATIVE.**

State transitions MUST NOT be added/removed/reordered without amending this section in the same PR. Every transition produces an `AuditEvent`. System-triggered transitions attribute the actor to the System User.

#### C.2.1 Lead

| From | To | Trigger | Actor | Side Effects |
| --- | --- | --- | --- | --- |
| New | Contacted | first_contact | Sales rep | — |
| Contacted | Qualified | qualify | Sales rep | qualified_at set |
| Contacted | Unqualified | disqualify | Sales rep / Manager | reason set |
| Qualified | Converted | convert_to_quote | Sales rep | New Quote + DRAFT QuoteVersion created |
| Qualified | Unqualified | disqualify | Manager | reason required |
| Unqualified | Qualified | re_qualify | Manager | reason required |
| Unqualified | Archived | archive | Any member | archived_at set |
| Converted | Archived | archive | Manager | archived_at set |

**Terminal states:** Archived.

#### C.2.2 Quote Version

| From | To | Trigger | Actor | Side Effects |
| --- | --- | --- | --- | --- |
| Draft | Sent | send_quote | Sales rep w/ `quotes.send` | sent_at, sent_by, sent_to_emails set; outbox publishes email; PDF generated async; version becomes immutable |
| Draft | Superseded | new_version_created | Quote editor | New DRAFT version created |
| Sent | Retracted | retract_quote | Sales rep w/ `quotes.retract` | retracted_at + reason set; successor DRAFT version created with lines deep-copied |
| Sent | Accepted | accept_quote | User w/ `quotes.approve`; sensitive | accepted_at + accepted_by set; SalesOrder created; fulfillment dispatch enqueued |
| Sent | Declined | decline_quote | User w/ `quotes.decline` | declined_at set |
| Sent | Expired | expiry_check | System (Celery beat) | expired_at set |
| Sent | Superseded | new_version_created | Quote editor | New DRAFT created; sent version preserved |

**Terminal states:** Accepted, Declined, Expired, Retracted, Superseded.

#### C.2.3 Sales Order

| From | To | Trigger | Actor | Side Effects |
| --- | --- | --- | --- | --- |
| Open | In_Fulfillment | fulfillment_started | System | First fulfillment artifact leaves initial state |
| Open | Cancelled | cancel_order | Manager | reason required; only if no active WO/PO/BO |
| In_Fulfillment | Cancelled | cancel_order | Manager | reason required |
| In_Fulfillment | Fulfilled | all_fulfillment_complete | System | All linked artifacts in terminal state |
| In_Fulfillment | Part_Invoiced | partial_invoice_issued | Billing user | — |
| Fulfilled | Part_Invoiced | partial_invoice_issued | Billing user | — |
| Fulfilled | Invoiced | full_invoice_issued | Billing user | All invoiceable lines invoiced |
| Part_Invoiced | Invoiced | remaining_invoiced | Billing user | — |
| Invoiced | Closed | payment_complete | System | All invoices PAID |

**Terminal states:** Cancelled, Closed.

#### C.2.4 Work Order

| From | To | Trigger | Actor | Side Effects |
| --- | --- | --- | --- | --- |
| Pending | Assigned | assign | Dispatcher | assigned_to + scheduled_date set |
| Assigned | Pending | unassign | Manager | assigned_to cleared |
| Assigned | In_Progress | start_work | Assignee or Manager | started_at set |
| In_Progress | Completed | complete_work | Assignee | outcome_notes required; SO fulfillment-status check enqueued |
| In_Progress | On_Hold | put_on_hold | Assignee or Manager | hold_reason required |
| On_Hold | In_Progress | resume_work | Assignee or Manager | — |
| Pending | Cancelled | cancel | Manager | cancelled_reason required |
| Assigned | Cancelled | cancel | Manager | cancelled_reason required |

**Terminal states:** Completed, Cancelled.

#### C.2.5 Purchase Order

| From | To | Trigger | Actor | Side Effects |
| --- | --- | --- | --- | --- |
| Draft | Submitted | submit_po | Purchasing user | ordered_at set |
| Draft | Cancelled | cancel | Purchasing manager | reason required |
| Submitted | Acknowledged | acknowledge | Purchasing user | — |
| Submitted | Cancelled | cancel | Purchasing manager | only if supplier hasn't processed |
| Acknowledged | Part_Received | record_receipt | Receiving user | partial received |
| Acknowledged | Received | record_receipt | Receiving user | full received |
| Part_Received | Received | record_receipt | Receiving user | remaining received |

**Terminal states:** Cancelled, Received.

#### C.2.6 Build Order

| From | To | Trigger | Actor | Side Effects |
| --- | --- | --- | --- | --- |
| Planned | In_Progress | start_build | Production user | BuildBOMSnapshot created; estimated costs locked |
| Planned | Cancelled | cancel | Production manager | reason required |
| In_Progress | Quality_Review | submit_for_review | Production user | QA notification queued |
| In_Progress | On_Hold | put_on_hold | Production manager | reason required |
| On_Hold | In_Progress | resume_build | Production manager | — |
| On_Hold | Cancelled | cancel | Production manager | reason required |
| Quality_Review | Complete | approve_build | QA user | actual costs finalized |
| Quality_Review | In_Progress | reject_build | QA user | rejection notes required |

**Terminal states:** Cancelled, Complete.

#### C.2.7 Invoice

| From | To | Trigger | Actor | Side Effects |
| --- | --- | --- | --- | --- |
| Draft | Sent | send_invoice | Billing user | sent_at set; PDF + email enqueued |
| Draft | Void | void | Billing manager | reason required |
| Sent | Overdue | overdue_check | System (beat) | due_date passed |
| Sent | Part_Paid | record_payment | Billing user; sensitive | partial allocation |
| Sent | Paid | record_payment | Billing user; sensitive | full allocation |
| Sent | Void | void | Billing manager | reason required; cannot if any allocation exists |
| Overdue | Part_Paid | record_payment | Billing user; sensitive | — |
| Overdue | Paid | record_payment | Billing user; sensitive | SO Closed-check enqueued |
| Part_Paid | Paid | record_payment | Billing user; sensitive | SO Closed-check enqueued |

**Terminal states:** Void, Paid.

#### C.2.8 Task

| From | To | Trigger | Actor | Side Effects |
| --- | --- | --- | --- | --- |
| Open | In_Progress | start_task | Assignee or Manager | — |
| Open | Blocked | block_task | Assignee or Manager | blocked_reason required |
| In_Progress | Blocked | block_task | Assignee or Manager | blocked_reason required |
| Blocked | In_Progress | resume_task | Assignee or Manager | — |
| Open | Completed | complete_task | Assignee or Manager | completion_notes optional |
| In_Progress | Completed | complete_task | Assignee or Manager | — |
| Open | Cancelled | cancel_task | Manager | cancelled_reason required |
| In_Progress | Cancelled | cancel_task | Manager | cancelled_reason required |
| Blocked | Cancelled | cancel_task | Manager | cancelled_reason required |
| Completed | Open | reopen_task | Manager | reopened_reason required |
| Cancelled | Open | reopen_task | Manager | reopened_reason required |

**Terminal states:** None — reopen permits re-entry.

#### C.2.9 Membership

| From | To | Trigger | Actor | Side Effects |
| --- | --- | --- | --- | --- |
| Invited | Active | accept_invite | Invited user | accepted_at set; 2FA enrollment gate |
| Invited | Expired | invite_expiry | System (beat) | After 7 days |
| Active | Inactive | deactivate | Org admin | data retained |
| Active | Suspended | suspend | Org admin | suspended_reason required |
| Suspended | Active | reinstate | Org admin | suspended_reason cleared |
| Suspended | Inactive | deactivate | Org admin | — |
| Inactive | Active | reactivate | Org admin | — |

#### C.2.10 Pricing Approval

| From | To | Trigger | Actor | Side Effects |
| --- | --- | --- | --- | --- |
| Requested | Approved | approve | User w/ `pricing.approval.grant`; sensitive | quote line unblocked |
| Requested | Rejected | reject | User w/ `pricing.approval.grant`; sensitive | quote line remains blocked |
| Requested | Withdrawn | withdraw | Requester | — |
| Requested | Expired | expiry_check | System (beat) | expires_at < now |

**Terminal states:** Approved, Rejected, Withdrawn, Expired.

#### C.2.11 BOM Version

| From | To | Trigger | Actor | Side Effects |
| --- | --- | --- | --- | --- |
| Draft | Active | activate_bom_version | User w/ `catalog.bom.manage` | Effective_from set; prior ACTIVE version auto-superseded |
| Draft | (deleted) | delete_draft | User w/ `catalog.bom.manage` | Hard delete; only DRAFT |
| Active | Superseded | (auto on next activation) | System | effective_until set |

**Terminal states:** Superseded.

#### C.2.12 Property-based test requirement

A property-based test using Hypothesis MUST verify, for every state-machine entity:

1. Every transition declared corresponds to an executable service-layer function.
2. No service-layer function performs a transition not declared.
3. Every terminal state has zero outgoing transitions.
4. Every non-terminal state has at least one incoming and one outgoing transition.

### C.3 Entity Numbering and Sequences

**Status: NORMATIVE.**

#### C.3.1 Format

`{PREFIX}-{YEAR}-{SEQUENCE}`

- `PREFIX`: 1–6 uppercase letters; tenant-configurable per entity kind.
- `YEAR`: four-digit calendar year (UTC).
- `SEQUENCE`: zero-padded to minimum 5 digits.

#### C.3.2 Default prefixes

| Entity | Default Prefix |
| --- | --- |
| Lead | `LD` |
| Quote | `QT` |
| Sales Order | `SO` |
| Purchase Order | `PO` |
| Build Order | `BO` |
| Work Order | `WO` |
| Invoice | `INV` |
| Pricing Approval | `PA` |
| Price List | `PL` |
| Client | `CL` |

#### C.3.3 Allocation algorithm

```python
# NORMATIVE: shape
def allocate_number(*, organization_id: UUID, entity_kind: EntityKind) -> str:
    year = datetime.now(timezone.utc).year
    with transaction.atomic():
        seq, created = EntityNumberSequence.objects.select_for_update().get_or_create(
            organization_id=organization_id,
            entity_kind=entity_kind,
            year=year,
            defaults={"next_value": 1, "prefix": resolve_prefix(organization_id, entity_kind)},
        )
        value = seq.next_value
        seq.next_value = value + 1
        seq.save(update_fields=["next_value"])
    return f"{seq.prefix}-{year}-{value:05d}"
```

#### C.3.5 Gap behavior

Number gaps occur when a transaction rolls back. Gaps are EXPECTED. Gap-free numbering is NOT supported in v1.

### C.4 Soft-Delete and Immutability Policy

**Status: NORMATIVE.**

#### C.4.1 Per-entity policy

| Entity | Hard delete? | Soft delete? | Status archival? | Notes |
| --- | --- | --- | --- | --- |
| Lead | No | No | `status=ARCHIVED` | History preserved |
| Quote (container) | No | No | No | Always preserved |
| QuoteVersion | DRAFT only | No | Status terminals | DRAFT hard delete only |
| QuoteVersionLine | DRAFT only | No | — | Hard-deletable when parent is DRAFT |
| Client | Tenant-deletion only | Yes | `status=INACTIVE` | INACTIVE for normal lifecycle |
| ClientContact, ClientLocation | Yes | No | — | May be removed by tenant admin |
| SalesOrder | No | No | `status=CANCELLED` | Once created, never deleted |
| SalesOrderLine | No | No | — | Immutable post-creation |
| Task | Admin-only | No | `status=CANCELLED` | Hard delete reserved |
| Communication | No | No | — | Immutable |
| DocumentAttachment | Yes (with retention) | No | — | Hard delete blocked while retention_until > now |
| Invoice | No | No | `status=VOID` | Never deleted |
| InvoiceLine | No | No | — | Immutable |
| Payment | No | No | — | Append-only |
| PaymentAllocation | No (reverse via new row) | No | `reversed_at` | Reversal records new row |
| PricingSnapshot | No | No | `is_active=false` | Old snapshots retained |
| PricingApproval | No | No | Status terminals | Immutable once decided |
| BuildOrder | No | No | `status=CANCELLED` | — |
| BuildBOMSnapshot | No | No | — | Immutable |
| BuildLaborEntry | No | No | — | Append-only |
| WorkOrder | No | No | `status=CANCELLED` | — |
| PurchaseOrder | No | No | `status=CANCELLED` | — |
| PricingRule, PriceList, etc. | No | No | `is_active=false` | Effective-dated |
| AuditEvent | No | No | — | Pruned only by retention |
| OutboxEntry | Yes (post-CONSUMED) | No | — | CONSUMED entries pruned after 30 days |
| Membership | No | No | Status lifecycle | — |
| Capability, Role | No within version | No | Deprecation flag | Removed in major version transitions |

#### C.4.2 Tenant deletion semantics

When an Organization is deleted (G.7):

1. All tenant-owned records are HARD DELETED, except:
   - `AuditEvent` records RETAINED
   - `ImpersonationAuditLog` records RETAINED
2. The `Organization` row itself is RETAINED with `status=DELETED`.
3. DocumentAttachment rows deleted; underlying object-storage entries deleted.
4. Standard immutability rules explicitly suspended in this context.

### C.5 Database Constraints, Indexing, Concurrency

**Status: NORMATIVE.**

#### C.5.1 Constraint requirements

1. **Foreign keys** with appropriate `ON DELETE` policy.
2. **Org-scoped uniqueness** via `unique_together (organization_id, ...)` or `partial_unique`.
3. **CHECK constraints** for "exactly one of N is non-null", email lowercase invariant, mutual exclusivity, System User invariant.
4. **Partial unique indexes** for "at most one active" patterns.
5. **Cross-table org consistency** is NOT enforced via DB constraints in v1.

#### C.5.2 Index strategy

| Pattern | Index |
| --- | --- |
| Tenant-scoped list of any entity | `(organization_id, status, created_at DESC)` or domain equivalent |
| Numbering lookup | `unique (organization_id, number)` |
| Slug resolution | `unique (slug)` on Organization |
| Membership lookup | `(user_id, organization_id)` |
| Operating-scope intersection | `(organization_id, location_id)` on each scoped entity |
| Snapshot replay by quote line | `(organization_id, quote_version_line_id, is_active)` on PricingSnapshot |
| Audit lookup by object | `(organization_id, object_kind, object_id, event_at DESC)` on AuditEvent |
| Outbox dispatcher polling | `(status, next_attempt_at)` partial index |
| Pricing rule resolution | `(organization_id, target_line_type, is_active, effective_from, effective_until)` |

#### C.5.3 Partitioning

| Table | Partition Column | Granularity | Retention |
| --- | --- | --- | --- |
| `AuditEvent` | `event_at` | Monthly | Per G.5 |
| `PricingSnapshot` | `created_at` | Monthly | None automatic |
| `OutboxEntry` | `created_at` | Monthly | CONSUMED entries pruned after 30 days |

Partitions for the next 6 months MUST be pre-created by a Celery beat job running monthly.

#### C.5.4 Transaction and concurrency requirements

| Operation | Concurrency control |
| --- | --- |
| `accept_quote` | `SELECT FOR UPDATE` on QuoteVersion; outbox enqueue inside transaction |
| `record_payment` | `SELECT FOR UPDATE` on Invoice |
| `record_receipt` | `SELECT FOR UPDATE` on PurchaseOrderLine |
| `allocate_number` | `SELECT FOR UPDATE` on EntityNumberSequence |
| Fulfillment dispatch | Idempotency key `(sales_order_line_id, "dispatch")` |
| Quote draft edits | Optimistic concurrency via `QuoteVersion.optimistic_version` |
| Pricing approval decision | `SELECT FOR UPDATE` on PricingApproval |
| Build snapshot at start_build | `SELECT FOR UPDATE` on BuildOrder |

---

## Part D — Commercial Workflow

### D.1 Lead Lifecycle

**Status: NORMATIVE.**

#### D.1.1 Lead intake

```python
# NORMATIVE: shape
def create_lead(
    *,
    organization_id: UUID,
    actor_id: UUID,
    location_id: UUID,
    source: LeadSource,
    source_detail: str | None,
    summary: str,
    estimated_value: Decimal | None,
    estimated_close_date: date | None,
    primary_contact: LeadContactInput,
    additional_contacts: list[LeadContactInput] = (),
    sites: list[LeadSiteInput] = (),
    owner_membership_id: UUID | None = None,
    notes: str | None = None,
) -> Lead:
    """ Required capability: leads.create """
```

#### D.1.2 Lead state transitions

```python
def first_contact(*, organization_id, actor_id, lead_id) -> Lead: ...
def qualify(*, organization_id, actor_id, lead_id) -> Lead: ...
def disqualify(*, organization_id, actor_id, lead_id, reason) -> Lead: ...
def re_qualify(*, organization_id, actor_id, lead_id, reason) -> Lead: ...
def archive_lead(*, organization_id, actor_id, lead_id) -> Lead: ...
def assign_lead(*, organization_id, actor_id, lead_id, owner_membership_id) -> Lead: ...
```

#### D.1.3 Lead → Quote conversion

```python
def convert_to_quote(
    *,
    organization_id: UUID,
    actor_id: UUID,
    lead_id: UUID,
) -> tuple[Lead, Quote, QuoteVersion]:
    """
    Required capabilities: leads.convert AND quotes.create
    Required Lead.status: QUALIFIED
    """
```

**Field-mapping table from Lead → Quote:**

| Source (Lead) | Target (Quote / QuoteVersion) |
| --- | --- |
| `Lead.organization_id` | `Quote.organization_id` |
| `Lead.location_id` | `Quote.location_id` |
| `Lead.id` | `Quote.lead_id` |
| `Lead.estimated_close_date` | `QuoteVersion.expiration_date` if set, else null |
| `Lead.notes` | NOT copied |
| `Lead.primary_contact` | NOT copied at conversion |

#### D.1.4 RBAC enforcement matrix (Lead domain)

| View / Action | Queryset Scope | Capability | Object Check | Audit |
| --- | --- | --- | --- | --- |
| Lead list | `for_membership(m)` | `leads.view` | — | — |
| Lead detail | `for_membership(m)` | `leads.view` | — | — |
| Create lead | `for_org(org)` | `leads.create` | location belongs to org+scope | `LEAD_CREATED` |
| Edit lead | `for_membership(m)` | `leads.edit` | `lead.owner == acting_membership` unless `leads.edit_any` | `LEAD_UPDATED` |
| Archive lead | `for_membership(m)` | `leads.archive` | not already ARCHIVED | `LEAD_ARCHIVED` |
| Assign lead | `for_membership(m)` | `leads.assign` | new owner is org member | `LEAD_ASSIGNED` |
| First contact / Qualify / Disqualify / Re-qualify | `for_membership(m)` | `leads.edit` | state precondition | `LEAD_STATUS_CHANGED` |
| Convert to quote | `for_membership(m)` | `leads.convert` + `quotes.create` | `lead.status == QUALIFIED` | `LEAD_CONVERTED` + `QUOTE_VERSION_CREATED` |

### D.2 Quote, Quote Version, Quote Line

**Status: NORMATIVE.**

#### D.2.1 Quote builder service surface

```python
def add_quote_line(
    *,
    organization_id: UUID,
    actor_id: UUID,
    quote_version_id: UUID,
    line_type: LineType,
    catalog_item_ref: ServiceRef | ProductRef | BundleRef,
    quantity: Decimal,
    unit_of_measure: str,
    selected_supplier_id: UUID | None = None,
    selected_bom_version_id: UUID | None = None,
    expected_optimistic_version: int,
) -> QuoteVersionLine:
    """
    Required capability: quotes.edit
    Required QuoteVersion.status: DRAFT
    Triggers: PricingEngine.price_quote_line() → PricingSnapshot persisted
    """

def update_quote_line(...): ...
def remove_quote_line(...): ...
def apply_line_discount(...): ...
def override_line_price(...): ...   # Required: quotes.line.override_price; sensitive
def apply_quote_discount(...): ...
```

All draft mutations require `expected_optimistic_version`; mismatches raise `ConcurrencyConflictError`.

#### D.2.2 Quote send

```python
def send_quote(
    *,
    organization_id: UUID,
    actor_id: UUID,
    quote_version_id: UUID,
    recipient_emails: list[str],
    cover_message: str | None,
    expected_optimistic_version: int,
) -> QuoteVersion:
    """
    Required capability: quotes.send
    Required state: DRAFT
    """
```

Behavior (in transaction):

1. Lock QuoteVersion `FOR UPDATE`; verify state == DRAFT.
2. Verify all QuoteVersionLines have a non-null `pricing_snapshot_id`.
3. Verify NO QuoteVersionLine has a pending PricingApproval. Raise `PricingApprovalPendingError` if so.
4. Verify `expiration_date` is set; default to `now + 30 days` if null.
5. Recompute totals (defensive recalc).
6. Set `status=SENT, sent_at, sent_by_id, sent_to_emails`.
7. Insert outbox entry.
8. Emit `QUOTE_SENT` audit.

#### D.2.3 Quote retraction with successor inheritance

```python
def retract_quote(
    *,
    organization_id: UUID,
    actor_id: UUID,
    quote_version_id: UUID,
    reason: str,
) -> tuple[QuoteVersion, QuoteVersion]:
    """
    Required capability: quotes.retract
    Required state: SENT
    Returns (retracted_version, new_draft_version)
    """
```

Behavior:

1. Lock the SENT QuoteVersion `FOR UPDATE`.
2. Set retracted version: `status=RETRACTED, retracted_at, retracted_by_id, retracted_reason`.
3. Allocate next `version_number`.
4. Create new QuoteVersion with `status=DRAFT`.
5. **Deep-copy lines.** For each line: copy commercial fields; **re-price** through engine (fresh PricingSnapshots).
6. Copy quote-level discount.
7. Emit `QUOTE_RETRACTED` + `QUOTE_VERSION_CREATED` + `QUOTE_LINES_INHERITED`.

#### D.2.4 RBAC enforcement matrix (Quote domain)

| View / Action | Queryset Scope | Capability | Object Check | Audit |
| --- | --- | --- | --- | --- |
| Quote list/detail | `for_membership(m)` | `quotes.view` | — | — |
| Create quote / new version | `for_org(org)` | `quotes.create` | New version: prior status != ACCEPTED | `QUOTE_VERSION_CREATED` |
| Edit quote line | `for_membership(m)` | `quotes.edit` | DRAFT AND optimistic version matches | `QUOTE_LINE_*` |
| Apply line discount | `for_membership(m)` | `quotes.line.apply_discount` | DRAFT | `QUOTE_DISCOUNT_APPLIED` |
| Apply quote discount | `for_membership(m)` | `quotes.line.apply_discount` | DRAFT | `QUOTE_DISCOUNT_APPLIED` |
| Override line price | `for_membership(m)` | `quotes.line.override_price`; sensitive | DRAFT | `QUOTE_LINE_PRICE_OVERRIDE` |
| Send quote | `for_membership(m)` | `quotes.send` | DRAFT, no pending approvals | `QUOTE_SENT` |
| Retract quote | `for_membership(m)` | `quotes.retract` | SENT | `QUOTE_RETRACTED` + `QUOTE_VERSION_CREATED` |
| Accept quote | `for_membership(m)` | `quotes.approve`; sensitive | SENT | `QUOTE_ACCEPTED` |
| Decline quote | `for_membership(m)` | `quotes.decline` | SENT | `QUOTE_DECLINED` |
| Delete draft | `for_membership(m)` | `quotes.delete_draft` | DRAFT | `QUOTE_DRAFT_DELETED` |

#### D.2.5 Multi-line, multi-visit hint UI

The "one SalesOrderLine = one fulfillment artifact" rule is a v1 simplification. Quote builder shows a soft warning when:

- `line_type ∈ {SERVICE, MANUFACTURED_PRODUCT}` AND `quantity > 1`.

Banner: "This line will create a single fulfillment artifact for {quantity} {unit_of_measure}. If this represents multiple independent visits or batches, consider splitting into separate lines."

Dismissible per line; does NOT block save.

### D.3 Quote Acceptance and Sales Order Creation

**Status: NORMATIVE.**

#### D.3.1 Service shape

```python
def accept_quote(
    *,
    organization_id: UUID,
    actor_id: UUID,
    quote_version_id: UUID,
    client_resolution: ClientResolution,
    idempotency_key: str,
) -> QuoteAcceptanceResult:
    """
    Required capability: quotes.approve; sensitive (re-auth required)
    Required state: SENT
    """

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

#### D.3.2 Acceptance flow (REQ-CRM-ACCEPT-01)

In transaction:

1. **Idempotency check** on (organization_id, idempotency_key).
2. **Lock QuoteVersion** `FOR UPDATE`; verify `status == SENT` and `expiration_date >= today`.
3. **Verify no pending PricingApprovals** → raise `PricingApprovalPendingError`.
4. **Resolve client.**
5. **Create SalesOrder** with status=OPEN, totals copied from QuoteVersion.
6. **Create SalesOrderLines** copying commercial fields verbatim; reference snapshots.
7. **Lock pricing snapshots** (semantically; parent QuoteVersion ACCEPTED is the lock).
8. **Set QuoteVersion** to ACCEPTED.
9. **Update Lead** if linked.
10. **Enqueue fulfillment dispatch via outbox.**
11. **Emit `QUOTE_ACCEPTED` audit.**
12. **Mark idempotency outbox entry consumed.**

#### D.3.3 Field-mapping table: Lead → Client (when mode == "create_new")

| Source | Target | Notes |
| --- | --- | --- |
| `Lead.organization_id` | `Client.organization_id` | |
| `Lead.location_id` | `Client.location_id` | "Primary" location |
| Lead's primary contact | Initial `ClientContact` (is_primary=True) | If no primary, raise `ClientResolutionError` |
| `Lead.summary` | NOT mapped | |
| `Organization.default_payment_terms_days` | `Client.default_payment_terms_days` | |
| `Organization`'s default `CustomerSegment` | `Client.customer_segment_id` | Null if no default |
| `Lead`'s sites | NOT auto-mapped to ClientLocation | Operator adds explicitly |
| `Client.billing_account_name` | Defaults to "Lead's primary contact full name" | |

#### D.3.4 Client-resolution UI gate

The acceptance flow MUST NOT proceed without explicit client resolution. Modal:

1. If quote has `client_id` set already: show "Client: {client.display_name}".
2. If quote has only `lead_id` set:
   - Tab 1: "Use existing client" — search.
   - Tab 2: "Create new client from lead".
   - Neither preselected; deliberate choice required.

### D.4 Mixed-Line Order Composition and Fulfillment Dispatch

**Status: NORMATIVE.**

#### D.4.1 Dispatch rules

| line_type | Action |
| --- | --- |
| `SERVICE` | Create one `WorkOrder` with `status=PENDING` |
| `MANUFACTURED_PRODUCT` | Create one `BuildOrder` with `status=PLANNED` |
| `RESALE_PRODUCT` | Mark SOL `fulfillment_status=PENDING`; PO creation is operator-driven |
| `BUNDLE` | Decompose into component lines (each treated per its own line_type) |

#### D.4.2 Bundle decomposition at acceptance

A `BUNDLE` SalesOrderLine has its `BundleComponent` rows referenced. For each required component:

- Create child `SalesOrderLine` with `parent_sales_order_line_id` set.
- Child line carries its own pricing_snapshot_id.

#### D.4.3 Fulfillment dispatch worker

```python
@outbox_handler("sales_order.dispatch_fulfillment")
def handle_dispatch_fulfillment(payload: dict) -> None:
    sol_id = UUID(payload["sol_id"])
    line_type = payload["line_type"]
    with transaction.atomic():
        sol = SalesOrderLine.objects.select_for_update().get(id=sol_id)
        if sol.fulfillment_status != FulfillmentStatus.PENDING:
            return  # idempotent
        if line_type == "SERVICE":
            services.create_work_order_from_sales_order_line(...)
        elif line_type == "MANUFACTURED_PRODUCT":
            services.create_build_order_from_sales_order_line(...)
        elif line_type == "BUNDLE":
            services.decompose_bundle_sales_order_line(...)
        elif line_type == "RESALE_PRODUCT":
            sol.fulfillment_status = FulfillmentStatus.PENDING  # awaits PO
            sol.save(update_fields=["fulfillment_status"])
```

#### D.4.4 Fulfillment status rollup

| All children state | SalesOrder.status |
| --- | --- |
| All `PENDING` | OPEN |
| Any `IN_PROGRESS` | IN_FULFILLMENT |
| All `FULFILLED` (or NOT_APPLICABLE), no invoices | FULFILLED |
| Some lines invoiced, some not | PART_INVOICED |
| All invoiceable lines invoiced, not all paid | INVOICED |
| All invoiced AND all paid | CLOSED |
| Operator cancelled | CANCELLED |

#### D.4.5 RBAC enforcement matrix (Sales Order domain)

| View / Action | Queryset | Capability | Object Check | Audit |
| --- | --- | --- | --- | --- |
| Order list/detail | `for_membership(m)` | `orders.view` | — | — |
| Edit order notes | `for_membership(m)` | `orders.edit` | status not CANCELLED/CLOSED | `ORDER_NOTES_UPDATED` |
| Cancel order | `for_membership(m)` | `orders.cancel` | no active WO/PO/BO | `ORDER_CANCELLED` |
| Manually trigger fulfillment | `for_membership(m)` | `orders.generate_fulfillment` | line still PENDING | `ORDER_FULFILLMENT_TRIGGERED` |

### D.5 Sales Order Lifecycle

**Status: NORMATIVE.**

#### D.5.1 Order cancellation

```python
def cancel_sales_order(
    *,
    organization_id: UUID,
    actor_id: UUID,
    sales_order_id: UUID,
    reason: str,
) -> SalesOrder:
    """
    Required capability: orders.cancel
    Required: no active WorkOrders, BuildOrders, PurchaseOrders, or any Invoices
    """
```

#### D.5.2 Order closure

`SalesOrder.status = CLOSED` is set automatically by `recompute_sales_order_status` when all invoiceable lines invoiced, all linked invoices PAID, no uninvoiced eligible lines remain.

#### D.5.3 Order edits post-acceptance

Only `notes` and metadata fields like `external_id` MAY be edited. Commercial fields are immutable.

### D.6 Client Account Model

**Status: NORMATIVE.**

#### D.6.1 Service surface

```python
def create_client(...): ...
def update_client(...): ...
def deactivate_client(...): ...
def reactivate_client(...): ...
def merge_clients(*, primary_client_id, duplicate_client_id, ...): ...
def add_client_contact(...): ...
def update_client_contact(...): ...
def remove_client_contact(...): ...
def add_client_location(...): ...
def update_client_location(...): ...
def remove_client_location(...): ...
```

#### D.6.2 Client merge semantics

`merge_clients` re-points all FK references from `duplicate_client_id` to `primary_client_id`:

- Quotes, SalesOrders, Invoices, Communications, Tasks linked to the duplicate.
- ClientContacts and ClientLocations are MOVED, not duplicated.

The duplicate Client is set to `status=INACTIVE` with notes. Not hard-deleted. `CLIENT_MERGED` audit captures both IDs and re-pointed counts.

#### D.6.3 Customer segment assignment

Segment changes apply prospectively (existing PricingSnapshots unchanged).

#### D.6.4 RBAC enforcement matrix (Client domain)

| View / Action | Queryset | Capability | Object Check | Audit |
| --- | --- | --- | --- | --- |
| Client list/detail | `for_membership(m)` | `clients.view` | — | — |
| Create client | `for_org(org)` | `clients.create` | location in org+scope | `CLIENT_CREATED` |
| Edit client | `for_membership(m)` | `clients.edit` | status == ACTIVE | `CLIENT_UPDATED` |
| Deactivate client | `for_membership(m)` | `clients.deactivate` | — | `CLIENT_DEACTIVATED` |
| Reactivate client | `for_membership(m)` | `clients.edit` | status == INACTIVE | `CLIENT_REACTIVATED` |
| Manage contacts/locations | `for_membership(m)` | `clients.contacts.manage` / `clients.locations.manage` | — | `CLIENT_*` |
| Merge clients | `for_membership(m)` | `clients.merge` | both in org+scope | `CLIENT_MERGED` |

### D.7 Tasks and Communications

**Status: NORMATIVE.**

#### D.7.1 Task service surface

```python
def create_task(...): ...
def update_task(...): ...
def assign_task(...): ...
def start_task(...): ...
def block_task(...): ...
def resume_task(...): ...
def complete_task(...): ...
def cancel_task(...): ...
def reopen_task(...): ...
```

#### D.7.2 TaskLink and CommunicationLink invariants

The "exactly one of N is non-null" invariant is enforced at three layers:

1. Database CHECK constraint.
2. Service layer: tagged union input.
3. Form layer: single-select dropdown.

#### D.7.3 Task reminders

Tasks with `due_at` and `status IN (OPEN, IN_PROGRESS)` get async reminders:

- 24 hours before `due_at`: `task.reminder_due` outbox entry.
- 1 hour after `due_at` if still open: `task.reminder_overdue` outbox entry.

Reminders dispatch outbound email only in v1.

#### D.7.4 Communications service surface

```python
def log_communication(
    *, organization_id, actor_id,
    direction: CommunicationDirection,
    channel: CommunicationChannel,
    subject: str | None, body: str,
    participants: list[Participant],
    occurred_at: datetime,
    link: CommunicationLinkInput,
) -> Communication: ...

def send_communication(
    *, organization_id, actor_id,
    subject: str, body: str, recipient_emails: list[str],
    link: CommunicationLinkInput,
) -> Communication:
    """ OUTBOUND EMAIL ONLY in v1. Body immutable once sent. """
```

#### D.7.5 RBAC enforcement matrix (Task and Communication domains)

| View / Action | Queryset | Capability | Object Check | Audit |
| --- | --- | --- | --- | --- |
| Task list | `for_membership(m)` filtered | `tasks.view` | — | — |
| Task detail | `for_membership(m)` | `tasks.view` | creator/assignee/manager unless `tasks.manage` | — |
| Create task | `for_membership(m)` | `tasks.create` | linked target in org+scope | `TASK_CREATED` |
| Update task | `for_membership(m)` | `tasks.edit` | creator/assignee/manager | `TASK_UPDATED` |
| Assign task | `for_membership(m)` | `tasks.assign` | new assignee in org | `TASK_ASSIGNED` |
| Start/block/resume | `for_membership(m)` | `tasks.edit` | state transitions | `TASK_STATUS_CHANGED` |
| Complete task | `for_membership(m)` | `tasks.complete` | OPEN/IN_PROGRESS/BLOCKED | `TASK_COMPLETED` |
| Cancel task | `for_membership(m)` | `tasks.manage` | not COMPLETED/CANCELLED | `TASK_CANCELLED` |
| Reopen task | `for_membership(m)` | `tasks.manage` | COMPLETED or CANCELLED | `TASK_REOPENED` |
| Communication list | `for_membership(m)` | `communications.view` | — | — |
| Log communication | `for_membership(m)` | `communications.log` | linked target in org+scope | `COMMUNICATION_LOGGED` |
| Send communication | `for_membership(m)` | `communications.send` | linked target in org+scope | `COMMUNICATION_SENT` |
| Edit metadata | `for_membership(m)` | `communications.manage` | body immutable | `COMMUNICATION_UPDATED` |

### D.8 Document Attachments

**Status: NORMATIVE.**

#### D.8.1 Service surface

```python
def upload_attachment(
    *, organization_id, actor_id,
    file_handle: BinaryIO,
    filename: str, content_type: str, size_bytes: int,
    document_kind: DocumentKind,
    visibility: AttachmentVisibility,
    link: DocumentAttachmentLinkInput,
) -> DocumentAttachment: ...

def get_attachment_download_url(
    *, organization_id, actor_id, attachment_id: UUID, expires_in_seconds: int = 300,
) -> str:
    """
    Re-evaluates capability + tenancy + object-link permission on every call.
    Returns short-lived signed URL bound to requesting user's session.
    """

def delete_attachment(*, organization_id, actor_id, attachment_id: UUID) -> None:
    """ Hard delete blocked while retention_until > now. """
```

#### D.8.2 Storage abstraction

Per-environment via `django-storages`:

- Dev/test: filesystem at `/var/mph/media/`.
- Staging/demo/prod: S3-compatible with prefix `{environment}/orgs/{org_id}/{document_kind}/{attachment_id}/{filename}`.

#### D.8.3 Permission evaluation

Capability derived from linked target:

| Linked target | Upload capability | Download capability |
| --- | --- | --- |
| QuoteVersion | `quotes.edit` (or system-generated for QUOTE_PDF) | `quotes.view` |
| Invoice | `billing.invoice.create`/`billing.invoice.send` | `billing.view` |
| WorkOrder | `workorders.update_status` | `workorders.view` |
| BuildOrder | `build.manage` | `build.view` |
| PurchaseOrder | `purchasing.edit` | `purchasing.view` |
| Client | `clients.edit` | `clients.view` |
| Lead | `leads.edit` | `leads.view` |
| Communication | `communications.log`/`communications.send` | `communications.view` |

#### D.8.4 Malware scanning hook

`malware_scan_status=PENDING` on upload. v1: no-op scanner immediately marks SKIPPED. INFECTED attachments quarantined: download URLs return 403.

#### D.8.5 Retention

| document_kind | Default retention |
| --- | --- |
| QUOTE_PDF | 7 years from creation |
| INVOICE_PDF | 7 years from creation |
| COMPLETION_PHOTO | 3 years from WorkOrder completion |
| SUPPORTING_DOC | None (manual delete only) |
| EXPORT_ARCHIVE | 14 days from creation |
| OTHER | None |

#### D.8.6 RBAC enforcement matrix (Document Attachment domain)

| View / Action | Queryset | Capability | Object Check | Audit |
| --- | --- | --- | --- | --- |
| Upload | `for_org(org)` | (derived) | linked target in org+scope; size/type valid | `ATTACHMENT_UPLOADED` |
| Download URL | `for_org(org)` | (derived — view) | not INFECTED; not retention-expired | `ATTACHMENT_ACCESSED` (sampled) |
| Delete | `for_org(org)` | (derived — edit) | retention_until <= now OR `admin.org.settings` override | `ATTACHMENT_DELETED` |

---

## Part E — Catalog and Operations

### E.1 Catalog: Services, Products, Materials, Suppliers

**Status: NORMATIVE.**

#### E.1.1 Catalog scope

The catalog is the source of truth for what a tenant sells (Services, Products) and what it consumes (RawMaterials), plus who supplies materials and resale products (Suppliers). Catalog data is **org-scoped**.

#### E.1.2 Catalog activation lifecycle

| Action | Effect |
| --- | --- |
| Create | `is_active=true` by default |
| Edit | Mutable per capability |
| Deactivate | `is_active=false`; quote builder excludes from picker; existing references retained |
| Reactivate | `is_active=true` |

Deactivating a catalog item does NOT invalidate existing QuoteVersionLines, PricingSnapshots, or open SalesOrderLines.

#### E.1.3 Unit-of-measure enum

```python
class UnitOfMeasure(models.TextChoices):
    EACH = "EACH", "each"
    HOUR = "HOUR", "hour"
    KG = "KG", "kilogram"
    G = "G", "gram"
    LB = "LB", "pound"
    OZ = "OZ", "ounce"
    M = "M", "meter"
    FT = "FT", "foot"
    IN = "IN", "inch"
    CM = "CM", "centimeter"
    M2 = "M2", "square meter"
    FT2 = "FT2", "square foot"
    M3 = "M3", "cubic meter"
    FT3 = "FT3", "cubic foot"
    L = "L", "liter"
    ML = "ML", "milliliter"
    GAL = "GAL", "gallon"
    BOX = "BOX", "box"
    CASE = "CASE", "case"
    PALLET = "PALLET", "pallet"
```

**No UoM conversion in v1.**

#### E.1.4 Catalog service surface

```python
# Services
def create_service(*, organization_id, actor_id, code, name, description,
                   catalog_price, default_pricing_strategy_code,
                   default_unit_of_measure, category_id=None) -> Service: ...
def update_service(...) -> Service: ...
def deactivate_service(...) -> Service: ...
def reactivate_service(...) -> Service: ...

# Products
def create_product(*, organization_id, actor_id, code, name, product_type,
                   description, default_pricing_strategy_code,
                   default_unit_of_measure,
                   default_markup_percent=None,
                   default_target_margin_percent=None) -> Product: ...

# RawMaterials
def update_raw_material_cost(*, organization_id, actor_id, raw_material_id,
                              new_cost, effective_from) -> RawMaterial:
    """
    Updates current_cost and current_cost_effective_from atomically.
    Does NOT mutate historical PricingSnapshots or BOMLine.cost_basis_at_creation.
    Active BOMVersions referencing this material are NOT auto-revalued.
    """

# Suppliers / SupplierProduct
def create_supplier(...): ...
def add_supplier_product(...): ...
def update_supplier_product_cost(...): ...
def set_preferred_supplier(*, organization_id, actor_id, supplier_product_id) -> SupplierProduct:
    """ Atomically clears is_preferred on others; sets it on this row. """
```

#### E.1.5 RBAC enforcement matrix (Catalog domain)

| View / Action | Queryset | Capability | Object Check | Audit |
| --- | --- | --- | --- | --- |
| Browse catalog (quote line picker) | `for_org(org)` | `catalog.view` | `is_active=true` | — |
| Service list/detail | `for_org(org)` | `catalog.view` | — | — |
| Create/edit service | `for_org(org)` | `catalog.services.manage` | — | `CATALOG_SERVICE_SAVED` |
| Deactivate/reactivate service | `for_org(org)` | `catalog.services.manage` | — | `CATALOG_SERVICE_STATUS_CHANGED` |
| Create/edit product | `for_org(org)` | `catalog.products.manage` | — | `CATALOG_PRODUCT_SAVED` |
| Create/edit raw material | `for_org(org)` | `catalog.materials.manage` | — | `CATALOG_MATERIAL_SAVED` |
| Update raw material cost | `for_org(org)` | `catalog.materials.manage` | — | `MATERIAL_COST_UPDATED` |
| Create/edit supplier | `for_org(org)` | `catalog.suppliers.manage` | — | `CATALOG_SUPPLIER_SAVED` |
| Manage supplier products | `for_org(org)` | `catalog.suppliers.manage` | — | `SUPPLIER_PRODUCT_SAVED` |
| Set preferred supplier | `for_org(org)` | `catalog.suppliers.manage` | — | `PREFERRED_SUPPLIER_SET` |

### E.2 Bill of Materials and BOM Versioning

**Status: NORMATIVE.**

#### E.2.1 BOM container model

`BOM` is a one-per-manufactured-product container. `BOMVersion` is the versioned child. A manufactured `Product` MUST have at least one ACTIVE BOMVersion before it can be quoted.

#### E.2.2 BOM version state machine

See C.2.11.

#### E.2.3 Activation atomicity

```python
def activate_bom_version(
    *, organization_id, actor_id, bom_version_id,
    effective_from: date | None = None,
) -> BOMVersion:
    """ Required capability: catalog.bom.manage; Required state: DRAFT """
    with transaction.atomic():
        v = BOMVersion.objects.select_for_update().get(...)
        if v.status != BOMVersionStatus.DRAFT:
            raise InvalidStateTransitionError(...)
        # Snapshot material cost at activation
        for line in v.bom_lines.all():
            line.cost_basis_at_creation = line.raw_material.current_cost
            line.save(update_fields=["cost_basis_at_creation"])
        # Supersede prior ACTIVE
        prior = BOMVersion.objects.select_for_update().filter(
            bom=v.bom, status=BOMVersionStatus.ACTIVE,
        ).first()
        if prior:
            prior.status = BOMVersionStatus.SUPERSEDED
            prior.effective_until = (effective_from or today()) - timedelta(days=1)
            prior.superseded_at = now()
            prior.save()
        v.status = BOMVersionStatus.ACTIVE
        v.effective_from = effective_from or today()
        v.activated_at = now()
        v.save()
        audit_emit("BOM_VERSION_ACTIVATED", ...)
    return v
```

#### E.2.4 Build-time BOM snapshot

`start_build` creates an immutable `BuildBOMSnapshot`:

```python
def start_build(*, organization_id, actor_id, build_order_id) -> BuildOrder:
    """ Required capability: build.manage; Required state: PLANNED """
    with transaction.atomic():
        bo = BuildOrder.objects.select_for_update().get(id=build_order_id)
        bom_version = BOMVersion.objects.get(id=bo.planned_bom_version_id)
        snapshot_payload = {
            "bom_id": str(bom_version.bom_id),
            "bom_version_id": str(bom_version.id),
            "version_number": bom_version.version_number,
            "lines": [
                {
                    "raw_material_id": str(l.raw_material_id),
                    "raw_material_code": l.raw_material.code,
                    "raw_material_name": l.raw_material.name,
                    "quantity": str(l.quantity),
                    "unit_of_measure": l.unit_of_measure,
                    "cost_basis_at_creation": str(l.cost_basis_at_creation),
                    "cost_at_snapshot": str(l.raw_material.current_cost),
                }
                for l in bom_version.bom_lines.all()
            ],
            "captured_at": now().isoformat(),
        }
        BuildBOMSnapshot.objects.create(
            organization_id=organization_id,
            build_order_id=bo.id,
            source_bom_version_id=bom_version.id,
            snapshot_payload=snapshot_payload,
            captured_by_id=actor_id,
        )
        bo.status = BuildOrderStatus.IN_PROGRESS
        bo.started_at = now()
        bo.save(update_fields=["status", "started_at"])
        audit_emit("BUILD_STARTED", ...)
    return bo
```

#### E.2.5 RBAC enforcement matrix (BOM domain)

| View / Action | Queryset | Capability | Object Check | Audit |
| --- | --- | --- | --- | --- |
| BOM list/detail | `for_org(org)` | `catalog.view` | — | — |
| Create draft BOM version | `for_org(org)` | `catalog.bom.manage` | parent product is MANUFACTURED | `BOM_VERSION_CREATED` |
| Edit BOM lines | `for_org(org)` | `catalog.bom.manage` | version status = DRAFT | `BOM_LINE_SAVED` |
| Activate BOM version | `for_org(org)` | `catalog.bom.manage` | version status = DRAFT | `BOM_VERSION_ACTIVATED` |
| Delete draft BOM version | `for_org(org)` | `catalog.bom.manage` | status = DRAFT | `BOM_VERSION_DRAFT_DELETED` |

### E.3 Pricing Rules, Price Lists, Contracts, Labor Rate Cards

**Status: NORMATIVE.**

#### E.3.1 PricingRule semantics

A `PricingRule` is a parameterized configuration that influences pricing without code changes. Carries: `target_*` fields, `rule_type`, `effective_from`/`effective_until`, `parameters_json`, `priority`.

#### E.3.2 Rule resolution algorithm

```python
def resolve_pricing_rules(
    context: PricingContext,
    rule_type: PricingRuleType,
) -> list[PricingRule]:
    """
    Returns matching rules sorted by precedence: most-specific first, then priority desc,
    then created_at desc. Final tie-break by id.
    """
    today = context.requested_pricing_date or date.today()

    qs = PricingRule.objects.for_org(context.organization_id).filter(
        is_active=True,
        rule_type=rule_type,
        effective_from__lte=today,
    ).filter(
        Q(effective_until__isnull=True) | Q(effective_until__gte=today),
    )

    qs = qs.filter(Q(target_line_type=context.line_type) | Q(target_line_type="ANY"))

    candidates = list(qs)

    def specificity(r: PricingRule) -> tuple:
        return (
            int(r.target_item_id is not None and r.target_item_id == _resolve_item_id(context)),
            int(r.target_client_id == context.client_id) if r.target_client_id else 0,
            int(r.target_customer_segment_id == context.customer_segment_id) if r.target_customer_segment_id else 0,
            int(r.target_supplier_id == context.selected_supplier_id) if r.target_supplier_id else 0,
            int(r.target_location_id == context.location_id) if r.target_location_id else 0,
            int(r.target_market_id == context.market_id) if r.target_market_id else 0,
            int(r.target_region_id == context.region_id) if r.target_region_id else 0,
            r.priority,
            -int(r.created_at.timestamp() * 1000),
            -int.from_bytes(r.id.bytes, "big"),
        )

    return sorted(candidates, key=specificity, reverse=True)
```

#### E.3.3 PriceList semantics

PriceLists support `effective_from`/`effective_until`, status lifecycle, per-item min/max quantity, single currency.

**v1 PriceLists are reached only via ClientContractPricing.** Standalone PriceList strategy is deferred.

#### E.3.4 ClientContractPricing semantics

Constraints:

- Only one ACTIVE contract per (client, line_type) at a time.
- Activation supersedes any prior ACTIVE contract overlapping in date range.
- Expired contracts (status=EXPIRED) do NOT apply.

```python
def resolve_active_contract(context: PricingContext) -> ClientContractPricing | None:
    if context.client_id is None:
        return None
    today = context.requested_pricing_date or date.today()
    return ClientContractPricing.objects.for_org(context.organization_id).filter(
        client_id=context.client_id,
        status="ACTIVE",
        effective_from__lte=today,
    ).filter(
        Q(effective_until__isnull=True) | Q(effective_until__gte=today),
    ).order_by("-effective_from").first()
```

#### E.3.5 LaborRateCard semantics

Feeds `LaborRateCardPricingStrategy` (uses bill rates) and `BuildLaborEntry.applied_internal_rate`/`applied_bill_rate` (snapshotted at entry time).

```python
def resolve_active_rate_card(
    organization_id: UUID, on_date: date,
) -> LaborRateCard | None:
    return LaborRateCard.objects.for_org(organization_id).filter(
        status="ACTIVE",
        effective_from__lte=on_date,
    ).filter(
        Q(effective_until__isnull=True) | Q(effective_until__gte=on_date),
    ).order_by("-effective_from").first()
```

Partial unique index on `(organization_id)` where `status='ACTIVE'`.

#### E.3.6 Service surface

```python
def create_pricing_rule(...): ...
def update_pricing_rule(...): ...
def deactivate_pricing_rule(...): ...

def create_price_list(*, organization_id, actor_id, code, name, currency_code,
                       effective_from, effective_until=None) -> PriceList: ...
def add_price_list_item(...): ...
def activate_price_list(...): ...

def create_client_contract(...): ...
def activate_client_contract(...): ...
def terminate_client_contract(...): ...

def create_labor_rate_card(...): ...
def add_rate_card_line(...): ...
def activate_labor_rate_card(...): ...
```

#### E.3.7 RBAC enforcement matrix

| Action | Capability | Audit |
| --- | --- | --- |
| View pricing rules | `pricing.rules.view` | — |
| Create/edit pricing rule | `pricing.rules.manage` | `PRICING_RULE_SAVED` |
| Deactivate pricing rule | `pricing.rules.manage` | `PRICING_RULE_DEACTIVATED` |
| Create/edit/activate price list | `pricing.price_lists.manage` | `PRICE_LIST_*` |
| Create/edit/activate client contract | `pricing.contracts.manage` | `CLIENT_CONTRACT_*` |
| Create/edit/activate labor rate card | `pricing.labor_rates.manage` | `LABOR_RATE_CARD_*` |

### E.4 Customer Segments, Promotions, Bundles

**Status: NORMATIVE.**

### E.4.1 CustomerSegment

Tenant-defined classification (e.g., STANDARD, ENTERPRISE, PARTNER, GOVERNMENT). Each has a `default_multiplier`. At most one segment per org has `is_default=true`.

#### E.4.2 PromotionCampaign

`eligibility_rules_json` shape:

```json
{
  "min_order_subtotal": "1000.00",
  "client_segments": ["STANDARD", "ENTERPRISE"],
  "client_ids": null,
  "exclude_client_ids": null,
  "max_uses_per_client": null,
  "max_total_uses": null,
  "requires_promo_code": true,
  "promo_code": "SPRING2026"
}
```

```python
def is_promotion_eligible(promo: PromotionCampaign, context: PricingContext) -> bool:
    rules = promo.eligibility_rules_json or {}
    today = context.requested_pricing_date or date.today()
    if not (promo.effective_from <= today <= promo.effective_until):
        return False
    if not promo.is_active:
        return False
    if rules.get("requires_promo_code") and context.applied_promo_code != rules.get("promo_code"):
        return False
    if (segs := rules.get("client_segments")) and context.customer_segment_code not in segs:
        return False
    if (cids := rules.get("client_ids")) and str(context.client_id) not in cids:
        return False
    if (ex_cids := rules.get("exclude_client_ids")) and str(context.client_id) in ex_cids:
        return False
    if (min_sub := rules.get("min_order_subtotal")):
        if context.quote_subtotal_so_far < Decimal(min_sub):
            return False
    if (mpc := rules.get("max_uses_per_client")) is not None:
        used = PromotionUsage.objects.filter(
            promotion_id=promo.id, client_id=context.client_id,
        ).count()
        if used >= mpc:
            return False
    if (mtu := rules.get("max_total_uses")) is not None:
        total = PromotionUsage.objects.filter(promotion_id=promo.id).count()
        if total >= mtu:
            return False
    return True
```

`PromotionUsage` row written when a quote with promotion-bearing line is **sent** (not on acceptance). NOT removed on retraction (one-shot semantics).

#### E.4.3 BundleDefinition and BundleComponent

| bundle_type | Pricing |
| --- | --- |
| COMPONENT_SUM | `bundle_price = SUM(component prices) − bundle_discount_amount` |
| FIXED_PRICE | `bundle_price = fixed_price` |
| CONFIGURABLE | `bundle_price = base_price + SUM(selected option prices) − bundle_discount_amount` |

Components reference Service or Product (not RawMaterial, not nested BundleDefinition — bundle-of-bundles deferred).

QuoteVersionLine for a bundle carries `selected_options_json` for CONFIGURABLE bundles.

#### E.4.4 Service surface

```python
def create_customer_segment(...): ...
def update_customer_segment(...): ...
def set_default_customer_segment(...): ...

def create_promotion_campaign(...): ...

def create_bundle_definition(...): ...
def add_bundle_component(...): ...
```

#### E.4.5 RBAC enforcement matrix

| Action | Capability | Audit |
| --- | --- | --- |
| Create/edit segment | `pricing.segments.manage` | `SEGMENT_SAVED` |
| Set default segment | `pricing.segments.manage` | `SEGMENT_DEFAULT_SET` |
| Create/edit promotion | `pricing.promotions.manage` | `PROMOTION_SAVED` |
| Create/edit bundle | `pricing.bundles.manage` | `BUNDLE_SAVED` |
| Add bundle component | `pricing.bundles.manage` | `BUNDLE_COMPONENT_SAVED` |

### E.5 Pricing Engine: Architecture

**Status: NORMATIVE.**

#### E.5.1 Core architecture

The pricing engine uses a small set of reusable base strategies. Business-specific pricing behavior is composed from cost/input resolvers, modifiers, approval policies, billing schedules, and immutable snapshots.

```text
PricingContextBuilder
  → Cost/Input Resolution
  → Base Pricing Strategy
  → Modifier Pipeline
  → Approval Evaluation
  → Tax and Rounding
  → PricingResult
  → PricingSnapshot
```

The engine is invoked from the service layer ONLY.

#### E.5.2 Design principle

```text
Base Strategy = how the starting price is calculated
Cost Resolver = where the cost, rate, supplier, BOM, catalog, or contract input comes from
Modifier = how the price is adjusted
Approval Policy = whether the price requires review
Billing Schedule = when/how the customer pays
Snapshot = what happened at quote time
```

The engine MUST NOT create one strategy class per business scenario. Supplier selection, preferred supplier selection, BOM selection, landed cost calculation, customer segment adjustment, location adjustment, rush pricing, complexity adjustment, discounts, minimum charge, and floor/margin checks are resolvers, modifiers, approval policies, or billing schedules—not standalone base strategies.

#### E.5.3 v1 base strategies

The v1 base strategy registry contains exactly:

```text
strategy.fixed_price
strategy.cost_plus
strategy.target_margin
strategy.rate_card
strategy.tiered
strategy.component_sum
strategy.recurring_plan
```

Adding another base strategy requires guide amendment. `strategy.value_outcome` is deferred unless explicitly approved later.

#### E.5.4 Cost/input resolvers

Resolvers perform database-backed input selection before the pure pricing strategy runs.

Supported v1 resolver codes:

```text
cost_source.manual
cost_source.catalog_standard_cost
cost_source.selected_supplier
cost_source.bom_version
cost_source.manufactured_build_up
cost_source.labor_rate_card
```

Future resolver codes MAY include:

```text
cost_source.preferred_supplier
cost_source.lowest_available_supplier
cost_source.landed_cost
cost_source.contract_cost
```

Resolvers MAY query the database. Strategies MUST NOT query the database.

#### E.5.5 PricingContext

Immutable, frozen dataclass. The `PricingContextBuilder` performs all database access.

```python
@dataclass(frozen=True)
class PricingContext:
    organization_id: UUID
    actor_id: UUID
    quote_version_id: UUID | None
    quote_version_line_id: UUID | None
    engine_version: str
    requested_pricing_date: date

    line_type: LineType
    quantity: Decimal
    unit_of_measure: str
    currency_code: str

    strategy_code: str | None
    cost_source: str | None

    service: ServiceSnapshot | None = None
    product: ProductSnapshot | None = None
    raw_materials: tuple[RawMaterialSnapshot, ...] = ()
    bundle_definition: BundleDefinitionSnapshot | None = None
    bundle_components_selected: tuple[BundleComponentSnapshot, ...] = ()

    selected_supplier_id: UUID | None = None
    selected_supplier_cost: Decimal | None = None
    supplier_alternatives: tuple[SupplierProductSnapshot, ...] = ()
    selected_bom_version_id: UUID | None = None
    selected_bom_lines: tuple[BOMLineSnapshot, ...] = ()

    client_id: UUID | None = None
    customer_segment_id: UUID | None = None
    customer_segment_code: str | None = None
    customer_segment_multiplier: Decimal | None = None
    active_contract_id: UUID | None = None
    active_contract_price: Decimal | None = None

    region_id: UUID | None = None
    market_id: UUID | None = None
    location_id: UUID | None = None
    location_multiplier: Decimal | None = None
    service_zone_code: str | None = None
    tax_jurisdiction_id: UUID | None = None

    cost_basis: Decimal | None = None
    cost_basis_source: str | None = None
    estimated_material_cost: Decimal | None = None
    estimated_labor_cost: Decimal | None = None
    estimated_overhead_cost: Decimal | None = None
    labor_rate_lines: tuple[LaborRateLineSnapshot, ...] = ()

    tier_mode: Literal["flat_tier", "graduated_tier"] | None = None
    tiers: tuple[TierSnapshot, ...] = ()

    component_inputs: tuple[ComponentPricingInput, ...] = ()
    recurring_plan_inputs: RecurringPlanPricingInput | None = None

    applied_promo_code: str | None = None
    eligible_promotions: tuple[PromotionCampaignSnapshot, ...] = ()
    requested_complexity: ComplexityLevel | None = None
    is_rush: bool = False
    is_after_hours: bool = False

    line_discount_type: DiscountType | None = None
    line_discount_value: Decimal | None = None
    quote_discount_type: DiscountType | None = None
    quote_discount_value: Decimal | None = None
    quote_subtotal_so_far: Decimal = Decimal("0")

    manual_override_price: Decimal | None = None
    manual_override_reason: str | None = None

    approval_threshold_rules: tuple[PricingRuleSnapshot, ...] = ()
    tax_rates: tuple[TaxRateSnapshot, ...] = ()
    line_taxable: bool = True
    rounding_policy: RoundingPolicy = RoundingPolicy.NEAREST_CENT
```

#### E.5.6 PricingContextBuilder

```python
class PricingContextBuilder:
    """Single point of database access for pricing."""

    def __init__(self, *, organization_id: UUID, actor_id: UUID): ...

    def build_for_quote_line(
        self,
        *,
        quote_version_id: UUID,
        line_input: QuoteLinePricingInput,
        replay_engine_version: str | None = None,
    ) -> PricingContext: ...
```

The builder MUST resolve, in order:

1. QuoteVersion → Quote → Organization, Lead/Client, Location.
2. Catalog references.
3. Strategy code.
4. Cost/input source.
5. Cost/input resolver outputs.
6. Active client contract.
7. Customer segment.
8. Active promotions.
9. Applicable PricingRules.
10. Tax rates for the location jurisdiction.
11. Rounding policy from InvoicingPolicy.

#### E.5.7 Resolver interface

```python
@runtime_checkable
class CostInputResolver(Protocol):
    source_code: str

    def resolve(self, context: PricingContext) -> PricingContext:
        """
        MAY access database through already-approved query services.
        MUST return a new PricingContext with resolved inputs.
        MUST NOT persist snapshots or emit audit events.
        """
```

#### E.5.8 Strategy interface

```python
@runtime_checkable
class PricingStrategy(Protocol):
    strategy_code: str
    applicable_line_types: tuple[LineType, ...]

    def calculate(self, context: PricingContext) -> BasePricingResult:
        """
        Pure function.
        MUST NOT access database, network, filesystem, or clock.
        MUST be deterministic given the same context.
        MUST raise PricingValidationError on invalid context.
        """
```

#### E.5.9 Modifier interface

```python
@runtime_checkable
class PricingModifier(Protocol):
    modifier_code: str
    pipeline_step: int

    def applies(self, context: PricingContext, intermediate: IntermediateResult) -> bool: ...
    def apply(self, context: PricingContext, intermediate: IntermediateResult) -> IntermediateResult: ...
```

Modifiers MUST be composable, ordered by configured precedence, and explainable through `ModifierApplication` rows in the result.

#### E.5.10 Service-layer entry points

```python
def price_quote_line(*, organization_id, actor_id, quote_version_id, line_input) -> PricingResult: ...
def reprice_quote_version(*, organization_id, actor_id, quote_version_id) -> QuotePricingResult: ...
def apply_manual_price_override(*, organization_id, actor_id, quote_version_line_id, override_amount, reason) -> PricingResult: ...
def evaluate_pricing_approval(*, organization_id, actor_id, pricing_result) -> PricingApprovalDecision: ...
def replay_pricing_snapshot(*, organization_id, snapshot_id) -> PricingResult: ...
```

#### E.5.11 Engine version policy

| Change | Bump |
| --- | --- |
| Modifier order changes | Major |
| Modifier math changes | Major |
| Strategy math changes | Major |
| Resolver selection semantics change | Major |
| Strategy added | Minor if additive and unused by existing snapshots |
| Modifier added | Minor if additive and opt-in |
| Snapshot field shape changes | Major |

v1 ships as engine version `"1.0"`.

### E.6 Pricing Engine: Base Strategy Catalog (v1)

**Status: NORMATIVE.**

This section defines the complete v1 base strategy catalog. Each strategy receives a complete `PricingContext`, performs deterministic math, and returns a `BasePricingResult`.

```python
@dataclass(frozen=True)
class BasePricingResult:
    cost_basis: Decimal | None
    unit_price: Decimal
    line_subtotal: Decimal
    notes: tuple[str, ...] = ()
```

#### E.6.1 `strategy.fixed_price`

Use when the system starts from a configured catalog price, price list item, package price, setup fee, inspection fee, or flat price.

Formula:

```text
Price = Configured Unit Price × Quantity
```

Covers:

- flat-rate services
- catalog products
- setup fees
- inspection fees
- fixed packages
- fixed bundles
- good/better/best fixed options

#### E.6.2 `strategy.cost_plus`

Use when price is calculated from cost plus markup.

Formula:

```text
Price = Cost Basis × (1 + Markup %)
```

Covers:

- resale product pricing
- supplier-based pricing
- raw material resale
- manufactured cost build-up with markup
- BOM version pricing with markup
- labor cost-plus pricing

Supplier selection and BOM selection are resolver concerns, not strategy concerns.

#### E.6.3 `strategy.target_margin`

Use when the business manages profitability by desired gross margin instead of markup.

Formula:

```text
Price = Cost Basis ÷ (1 - Target Margin %)
```

Markup and margin are not the same. This strategy remains separate because businesses commonly manage profitability by margin.

#### E.6.4 `strategy.rate_card`

Use when price is built from one or more rates multiplied by quantities, hours, roles, units, or metrics.

Formula:

```text
Price = SUM(Quantity × Rate)
```

Covers:

- time and materials
- labor rate card pricing
- role-based services
- usage-based services
- per-asset pricing
- per-location pricing
- per-user pricing
- mileage/distance pricing
- crew-based installation pricing

#### E.6.5 `strategy.tiered`

Use when quantity determines the applicable price.

Flat-tier formula:

```text
Line Total = Quantity × Selected Tier Unit Price
```

Graduated-tier formula:

```text
Line Total = SUM(Units in Bracket × Bracket Price)
```

`PricingContext.tier_mode` MUST be one of:

```text
flat_tier
graduated_tier
```

#### E.6.6 `strategy.component_sum`

Use when a quote line or quote group is assembled from selected components, options, products, services, or scope items.

Formula:

```text
Price = SUM(Component Prices) - Included Component Discounts
```

Covers:

- bundles
- configurable packages
- service/product combinations
- scope-based services
- implementation kits
- option-based quote builders
- good/better/best packages

Component details MUST be preserved internally, even if the customer-facing quote displays one summarized line.

#### E.6.7 `strategy.recurring_plan`

Use when price is tied to a recurring billing relationship.

Formula:

```text
Recurring Price = Base Plan Price + Add-ons + Usage/Overage Charges
```

v1 supports quote-time recurring plan pricing only. Automated renewals, metered usage ingestion, and recurring invoice generation are deferred unless separately approved.

#### E.6.8 Strategy registry contract

```python
STRATEGY_REGISTRY: dict[str, PricingStrategy] = {
    "strategy.fixed_price": FixedPriceStrategy(),
    "strategy.cost_plus": CostPlusStrategy(),
    "strategy.target_margin": TargetMarginStrategy(),
    "strategy.rate_card": RateCardStrategy(),
    "strategy.tiered": TieredStrategy(),
    "strategy.component_sum": ComponentSumStrategy(),
    "strategy.recurring_plan": RecurringPlanStrategy(),
}
```

CI test `test_strategy_registry_complete` MUST assert that these are the only v1 base strategies unless the guide is amended.

### E.7 Pricing Engine: Modifier Catalog (v1)

**Status: NORMATIVE.**

Modifiers are reusable adjustments applied after base price calculation. They MUST be deterministic, ordered, explainable, and reusable across service, product, manufactured product, bundle, and recurring plan lines.

#### E.7.1 Required modifier registry

```python
MODIFIER_REGISTRY: dict[str, PricingModifier] = {
    "modifier.customer_contract": CustomerContractModifier(),
    "modifier.customer_segment": CustomerSegmentModifier(),
    "modifier.location": LocationModifier(),
    "modifier.service_zone": ServiceZoneModifier(),
    "modifier.complexity": ComplexityModifier(),
    "modifier.rush": RushModifier(),
    "modifier.after_hours": AfterHoursModifier(),
    "modifier.promotion": PromotionModifier(),
    "modifier.line_discount": LineDiscountModifier(),
    "modifier.quote_discount": QuoteDiscountModifier(),
    "modifier.minimum_charge": MinimumChargeModifier(),
    "modifier.trip_fee": TripFeeModifier(),
    "modifier.manual_override": ManualOverrideModifier(),
    "modifier.floor_margin": FloorMarginModifier(),
    "modifier.tax": TaxModifier(),
    "modifier.rounding": RoundingModifier(),
}
```

#### E.7.2 Modifier semantics

| Modifier | Behavior |
| --- | --- |
| `modifier.customer_contract` | Applies active contract or customer-specific price list adjustment |
| `modifier.customer_segment` | Applies customer segment multiplier or discount |
| `modifier.location` | Applies region/market/location pricing adjustment |
| `modifier.service_zone` | Applies service-zone multiplier or fee |
| `modifier.complexity` | Applies complexity multiplier or fee |
| `modifier.rush` | Applies rush multiplier or fee |
| `modifier.after_hours` | Applies after-hours multiplier or fee |
| `modifier.promotion` | Applies eligible promotion discount |
| `modifier.line_discount` | Applies explicit line-level discount |
| `modifier.quote_discount` | Allocates quote-level discount across lines |
| `modifier.minimum_charge` | Raises line/group total to configured minimum when needed |
| `modifier.trip_fee` | Adds trip/service-call fee |
| `modifier.manual_override` | Replaces calculated price with approved/requested manual price |
| `modifier.floor_margin` | Flags below-floor or below-margin condition; does not raise price |
| `modifier.tax` | Applies tax according to resolved tax rates and taxability |
| `modifier.rounding` | Applies configured rounding policy |

#### E.7.3 Modifier ordering

Default modifier order:

```text
1. customer_contract
2. customer_segment
3. location
4. service_zone
5. complexity
6. rush
7. after_hours
8. promotion
9. line_discount
10. quote_discount
11. minimum_charge
12. trip_fee
13. manual_override
14. floor_margin
15. tax
16. rounding
```

Changing order is a major engine-version change.

#### E.7.4 Approval implications

Modifiers MAY add approval reasons to the intermediate result. Final approval evaluation occurs in the approval policy service, not inside the base strategy.

### E.8 Pricing Engine: Cost/Input and Rule Resolution

**Status: NORMATIVE.**

#### E.8.1 Cost/input resolver registry

```python
COST_RESOLVER_REGISTRY: dict[str, CostInputResolver] = {
    "cost_source.manual": ManualCostResolver(),
    "cost_source.catalog_standard_cost": CatalogStandardCostResolver(),
    "cost_source.selected_supplier": SelectedSupplierCostResolver(),
    "cost_source.bom_version": BOMVersionCostResolver(),
    "cost_source.manufactured_build_up": ManufacturedBuildUpCostResolver(),
    "cost_source.labor_rate_card": LaborRateCardResolver(),
}
```

#### E.8.2 Resolver responsibilities

Resolvers are responsible for locating and denormalizing pricing inputs:

| Resolver | Responsibility |
| --- | --- |
| `cost_source.manual` | Uses explicit operator-entered cost basis |
| `cost_source.catalog_standard_cost` | Uses catalog price or standard cost |
| `cost_source.selected_supplier` | Uses selected SupplierProduct cost |
| `cost_source.bom_version` | Uses selected/active BOM version material cost |
| `cost_source.manufactured_build_up` | Computes material + labor + overhead cost basis |
| `cost_source.labor_rate_card` | Resolves labor roles, internal cost rates, and bill rates |

#### E.8.3 PricingRule semantics

A `PricingRule` is a parameterized configuration. Rules carry:

- target line type,
- target item/client/segment/supplier/location fields,
- rule type,
- effective dates,
- parameters JSON,
- priority.

Rules MAY affect:

- default strategy code,
- cost/input source,
- markup percentage,
- target margin percentage,
- modifier parameters,
- approval thresholds,
- minimum charges,
- floor prices,
- tax/rounding parameters where applicable.

#### E.8.4 Rule resolution precedence

Default precedence:

| Level | Scope |
| --- | --- |
| 1 | manual override input |
| 2 | active client contract |
| 3 | client-specific rule |
| 4 | customer-segment rule |
| 5 | item-specific rule |
| 6 | supplier-specific rule |
| 7 | location/market/region rule |
| 8 | line-type default |
| 9 | organization default |
| 10 | catalog fallback |

Tie-breaks: priority descending → effective_from descending → created_at descending → id.

#### E.8.5 Strategy code resolution

Strategy code resolution MUST return one of the 7 base strategy codes.

```python
def resolve_strategy_code(context: PricingContext) -> str:
    if context.strategy_code:
        return context.strategy_code

    if context.line_type == LineType.BUNDLE:
        if context.bundle_definition and context.bundle_definition.bundle_type == BundleType.FIXED_PRICE:
            return "strategy.fixed_price"
        return "strategy.component_sum"

    if context.recurring_plan_inputs is not None:
        return "strategy.recurring_plan"

    return context.catalog_default_strategy_code
```

The resolver MUST NOT return legacy product/service-specific strategy codes such as `product.preferred_supplier`, `service.rush`, or `product.location_adjusted`.

### E.9 Pricing Approval Workflow

**Status: NORMATIVE.**

#### E.9.1 Approval posture

Approval logic is separate from base strategies. Strategies calculate price. Modifiers may add approval reasons. Approval policies decide whether review is required.

#### E.9.2 Trigger conditions

| Trigger code | Source |
| --- | --- |
| `MANUAL_OVERRIDE` | `modifier.manual_override` applied |
| `DISCOUNT_THRESHOLD` | Aggregate discount percent exceeds configured threshold |
| `BELOW_FLOOR` | Final price below configured floor price |
| `BELOW_MARGIN` | Computed margin percent below configured minimum |
| `CONTRACT_DEVIATION` | Active contract price changed or overridden |
| `RUSH_WAIVED` | Rush/after-hours surcharge waived where policy requires approval |
| `OTHER` | Tenant-defined approval threshold rule |

`VALUE_BASED` is deferred unless `strategy.value_outcome` is explicitly added later.

#### E.9.3 Approval thresholds

Tenants configure thresholds via `APPROVAL_THRESHOLD` PricingRule:

```json
{
  "discount_threshold_percent": "15.00",
  "minimum_margin_percent": "20.00",
  "floor_price_lookup": "item_specific"
}
```

### E.9.4 Service surface

```python
def request_pricing_approval(
    *, organization_id, actor_id,
    quote_version_id, quote_version_line_id,
    pricing_result: PricingResult,
) -> PricingApproval:
    """Required: pricing.approval.request. Idempotent on quote_version_line_id."""

def approve_pricing_approval(
    *, organization_id, actor_id,
    approval_id, decision_notes,
) -> PricingApproval:
    """Required: pricing.approval.grant; sensitive. State: REQUESTED."""

def reject_pricing_approval(
    *, organization_id, actor_id,
    approval_id, decision_notes,
) -> PricingApproval:
    """Required: pricing.approval.grant; sensitive. State: REQUESTED."""

def withdraw_pricing_approval(
    *, organization_id, actor_id, approval_id,
) -> PricingApproval:
    """Required: pricing.approval.request; requester only. State: REQUESTED."""

def expire_pricing_approvals(*, organization_id) -> int:
    """Celery beat job. Sets REQUESTED → EXPIRED where expires_at < now."""
```

#### E.9.5 Re-pricing clears pending approval

When re-pricing writes a new PricingSnapshot, previous pending approval is auto-set to `WITHDRAWN` with system note: `Superseded by re-pricing.`

#### E.9.6 RBAC enforcement matrix

| Action | Capability | Audit |
| --- | --- | --- |
| View approval | `pricing.approval.request` OR `pricing.approval.grant` | — |
| Request approval | `pricing.approval.request` | `PRICING_APPROVAL_REQUESTED` |
| Approve | `pricing.approval.grant`; sensitive | `PRICING_APPROVAL_GRANTED` |
| Reject | `pricing.approval.grant`; sensitive | `PRICING_APPROVAL_REJECTED` |
| Withdraw | `pricing.approval.request` | `PRICING_APPROVAL_WITHDRAWN` |
| Expire | System | `PRICING_APPROVAL_EXPIRED` |

### E.10 Pricing Snapshots and Replay

**Status: NORMATIVE.**

#### E.10.1 Snapshot purpose

A `PricingSnapshot` is the immutable record of what happened when a quote line, quote group, or invoice line was priced. It must be sufficient to explain, audit, and reproduce the commercial result even if catalog prices, supplier costs, BOMs, contracts, modifiers, or pricing rules change later.

#### E.10.2 Snapshot model fields

```text
PricingSnapshot
  id: BIGSERIAL, pk
  organization_id: UUID, fk
  snapshot_type: ENUM(QUOTE_LINE, QUOTE_GROUP, INVOICE_LINE)
  quote_version_line_id: UUID, fk, null
  quote_group_id: UUID, null
  invoice_line_id: UUID, fk, null

  engine_version: TEXT
  strategy_code: TEXT
  cost_source: TEXT, null
  line_type: TEXT
  quantity: NUMERIC(14,4)
  currency_code: CHAR(3)

  catalog_item_snapshot: JSONB
  base_inputs: JSONB
  base_calculation: JSONB
  modifiers: JSONB
  approval: JSONB
  tax: JSONB
  rounding: JSONB
  outputs: JSONB
  auditability: JSONB

  effective_unit_price: NUMERIC(14,4)
  effective_line_total: NUMERIC(14,2)
  estimated_total_cost: NUMERIC(14,2), null
  gross_profit_amount: NUMERIC(14,2), null
  gross_margin_percent: NUMERIC(7,4), null

  override_applied: BOOL, default(false)
  approval_required: BOOL, default(false)
  approval_id: UUID, fk -> PricingApproval, null
  created_at: TIMESTAMPTZ
  created_by_id: UUID, fk -> User, null
```

#### E.10.3 Required snapshot contents

Every snapshot MUST capture:

```text
engine_version
snapshot_type
line_type
quantity
unit_of_measure
currency_code
strategy_code
cost_source
catalog item snapshot
base inputs
cost basis
resolver inputs
modifier codes
modifier inputs
modifier deltas
discount details
override details
approval status
approval reasons
tax inputs
tax amount
rounding policy
final unit price
final line total
gross profit amount
gross margin percent
warnings
```

#### E.10.4 Example resale product snapshot

```json
{
  "engine_version": "1.0",
  "snapshot_type": "QUOTE_LINE",
  "line_type": "RESALE_PRODUCT",
  "pricing_strategy": "strategy.cost_plus",
  "cost_source": "cost_source.selected_supplier",
  "quantity": "12",
  "unit_of_measure": "each",
  "base_inputs": {
    "selected_supplier": {
      "supplier_id": "SUP-224",
      "supplier_name": "Preferred Supply Co.",
      "supplier_sku": "PSC-FILTER-20X25-M13",
      "supplier_unit_cost": "18.50",
      "supplier_cost_effective_date": "2026-05-01"
    },
    "cost_basis_per_unit": "18.50",
    "markup_percent": "45.00"
  },
  "base_calculation": {
    "unit_cost": "18.50",
    "unit_price_before_modifiers": "26.83",
    "line_subtotal_before_modifiers": "321.90",
    "estimated_total_cost": "222.00"
  },
  "modifiers": [
    {
      "code": "modifier.line_discount",
      "input": {
        "discount_type": "percent",
        "discount_percent": "5.00"
      },
      "amount_delta": "-16.10"
    }
  ],
  "outputs": {
    "discount_amount": "16.10",
    "tax_amount": "25.23",
    "final_unit_price": "25.48",
    "final_line_total": "331.03",
    "gross_profit_amount": "83.80",
    "gross_margin_percent": "27.40",
    "approval_required": false,
    "approval_reasons": [],
    "warnings": []
  }
}
```

#### E.10.5 Mixed service/product quote groups

Service lines that include products SHOULD use a parent/child structure:

```text
Quote Group or Parent Line
  → Service Component
  → Manufactured Product Component
  → Resale Product Component
  → Group-Level Modifiers
  → Group-Level Snapshot
```

The customer-facing quote may display one grouped total, but the internal snapshot MUST preserve component-level cost, price, tax, and margin detail.

#### E.10.6 Replay

Replay reconstructs from the snapshot only. It MUST NOT query current catalog prices, supplier costs, BOMs, contracts, or pricing rules.

Replay is used for:

- quote disputes,
- invoice sanity checks,
- audit review,
- engine upgrade validation.

Recompute is separate. Recompute uses current catalog/rule data and may produce a different result.

### E.11 Procurement: Purchase Orders, Allocation, Receipt

**Status: NORMATIVE.**

#### E.11.1 PO creation from accepted lines

```python
def create_purchase_order(
    *, organization_id: UUID, actor_id: UUID,
    location_id: UUID, supplier_id: UUID,
    line_inputs: list[PurchaseOrderLineInput],
    expected_delivery_date: date | None = None,
    notes: str | None = None,
) -> PurchaseOrder:
    """ Required capability: purchasing.create """
```

#### E.11.2 Allocation invariants

```python
def add_purchase_allocation(
    *, organization_id, actor_id,
    purchase_order_line_id: UUID,
    sales_order_line_id: UUID,
    allocated_quantity: Decimal,
) -> PurchaseAllocation:
    """
    Required: purchasing.edit. State: PO is DRAFT.
    Validates: SUM of allocated_quantity for sales_order_line_id ≤ sales_order_line.quantity
               (across ALL purchase_order_lines)
    """
```

Sum-check enforced at service layer (DRAFT-state intermediate violations expected).

#### E.11.3 PO submission

```python
def submit_purchase_order(...) -> PurchaseOrder:
    """ Required: purchasing.submit; State: DRAFT """
```

Sets `status=SUBMITTED, ordered_at=now`. Outbox enqueue: `purchase_order.send_email`.

#### E.11.4 Acknowledgment and receipt

```python
def acknowledge_purchase_order(...) -> PurchaseOrder: ...

def record_receipt(
    *, organization_id, actor_id,
    purchase_order_id: UUID,
    line_receipts: list[LineReceipt],
) -> PurchaseOrder:
    """
    Required: purchasing.receive. State: ACKNOWLEDGED, PART_RECEIVED
    Updates PurchaseOrderLine.quantity_received per entry.
    Aggregates: if all lines fully received → PO status RECEIVED; else PART_RECEIVED.
    """
```

#### E.11.5 PO cancellation

| State | Cancellable? |
| --- | --- |
| DRAFT | Yes |
| SUBMITTED | Yes (with reason) |
| ACKNOWLEDGED | Yes (with reason) |
| PART_RECEIVED | No (partial cancel out of v1) |
| RECEIVED, CANCELLED | Terminal |

#### E.11.6 RBAC enforcement matrix (Procurement)

| Action | Capability | State | Audit |
| --- | --- | --- | --- |
| PO list/detail | `purchasing.view` | — | — |
| Create PO | `purchasing.create` | — | `PO_CREATED` |
| Edit PO | `purchasing.edit` | DRAFT | `PO_UPDATED` |
| Add/remove allocation | `purchasing.edit` | DRAFT | `PO_ALLOCATION_*` |
| Submit | `purchasing.submit` | DRAFT | `PO_SUBMITTED` |
| Acknowledge | `purchasing.edit` | SUBMITTED | `PO_ACKNOWLEDGED` |
| Record receipt | `purchasing.receive` | ACKNOWLEDGED, PART_RECEIVED | `PO_RECEIPT_RECORDED` |
| Cancel | `purchasing.cancel` | DRAFT, SUBMITTED, ACKNOWLEDGED | `PO_CANCELLED` |

### E.12 Manufacturing: Build Orders, BOM Snapshots, Labor

**Status: NORMATIVE.**

#### E.12.1 Build order creation

Created by fulfillment dispatch worker on quote acceptance:

```python
def create_build_order_from_sales_order_line(
    *, organization_id, actor_id, sales_order_line_id,
) -> BuildOrder:
    """ Idempotent: returns existing BO if one already references this SOL. """
    sol = SalesOrderLine.objects.get(id=sales_order_line_id)
    existing = BuildOrder.objects.filter(source_sales_order_line_id=sol.id).first()
    if existing:
        return existing
    bom = BOM.objects.get(product_id=sol.product_id)
    active_version = BOMVersion.objects.filter(bom=bom, status='ACTIVE').first()
    if not active_version:
        raise PricingValidationError("Cannot create BuildOrder: no active BOM version")

    snap = PricingSnapshot.objects.get(id=sol.pricing_snapshot_id)
    estimated_material = Decimal(snap.inputs.get("estimated_material_cost", "0"))
    estimated_labor = Decimal(snap.inputs.get("estimated_labor_cost", "0"))

    bo = BuildOrder.objects.create(
        organization_id=organization_id,
        location_id=sol.sales_order.location_id,
        number=allocate_number(organization_id=organization_id, entity_kind=EntityKind.BUILD_ORDER),
        source_sales_order_line_id=sol.id,
        planned_bom_version_id=active_version.id,
        status=BuildOrderStatus.PLANNED,
        estimated_material_cost=estimated_material,
        estimated_labor_cost=estimated_labor,
    )
    sol.fulfillment_status = FulfillmentStatus.IN_PROGRESS
    sol.save()
    audit_emit("BUILD_ORDER_CREATED", ...)
    return bo
```

#### E.12.2 Build order state services

```python
def start_build(...) -> BuildOrder: ...     # E.2.4
def put_build_on_hold(*, organization_id, actor_id, build_order_id, reason) -> BuildOrder: ...
def resume_build(...) -> BuildOrder: ...
def submit_build_for_review(...) -> BuildOrder: ...
def approve_build(*, organization_id, actor_id, build_order_id, decision_notes=None) -> BuildOrder: ...
def reject_build(*, organization_id, actor_id, build_order_id, rejection_notes) -> BuildOrder: ...
def cancel_build(*, organization_id, actor_id, build_order_id, reason) -> BuildOrder: ...
```

#### E.12.3 Labor entry

```python
def record_labor_entry(
    *, organization_id, actor_id, build_order_id,
    labor_role: str, hours: Decimal,
    rate_card_id: UUID | None = None,
    occurred_on: date | None = None,
    notes: str | None = None,
) -> BuildLaborEntry:
    """
    Required: build.labor.record; State: BuildOrder IN_PROGRESS
    Resolves applied rates from rate card active on occurred_on.
    Updates BuildOrder.actual_labor_cost atomically.
    Append-only — corrections via BuildLaborAdjustment.
    """

def adjust_labor_entry(
    *, organization_id, actor_id, original_entry_id,
    adjustment_type: AdjustmentType,
    hours_delta: Decimal,
    reason: str,
) -> BuildLaborAdjustment:
    """
    Required: build.labor.edit_any
    Computes internal_cost_delta from original entry's applied_internal_rate.
    """
```

#### E.12.4 Variance reporting

Computed read-side:

```python
def compute_build_variance(build_order_id: UUID) -> BuildVariance:
    bo = BuildOrder.objects.get(id=build_order_id)
    return BuildVariance(
        material_estimated=bo.estimated_material_cost,
        material_actual=bo.actual_material_cost,
        material_variance=bo.actual_material_cost - bo.estimated_material_cost,
        labor_estimated=bo.estimated_labor_cost,
        labor_actual=bo.actual_labor_cost,
        labor_variance=bo.actual_labor_cost - bo.estimated_labor_cost,
        total_estimated=bo.estimated_material_cost + bo.estimated_labor_cost,
        total_actual=bo.actual_material_cost + bo.actual_labor_cost,
    )
```

#### E.12.5 RBAC enforcement matrix (Manufacturing)

| Action | Capability | State | Audit |
| --- | --- | --- | --- |
| BO list/detail | `build.view` | — | — |
| Start build | `build.manage` | PLANNED | `BUILD_STARTED` |
| Put on hold | `build.manage` | IN_PROGRESS | `BUILD_ON_HOLD` |
| Resume | `build.manage` | ON_HOLD | `BUILD_RESUMED` |
| Submit for QA | `build.manage` | IN_PROGRESS | `BUILD_SUBMITTED_FOR_QA` |
| Approve (QA) | `build.qa.review` | QUALITY_REVIEW | `BUILD_APPROVED` |
| Reject (QA) | `build.qa.review` | QUALITY_REVIEW | `BUILD_REJECTED` |
| Cancel | `build.manage` | PLANNED, IN_PROGRESS, ON_HOLD | `BUILD_CANCELLED` |
| Record labor | `build.labor.record` | IN_PROGRESS | `BUILD_LABOR_RECORDED` |
| Adjust labor | `build.labor.edit_any` | IN_PROGRESS | `BUILD_LABOR_ADJUSTED` |
| View cost analysis | `build.cost.view` | any | — |

### E.13 Field Service: Work Orders

**Status: NORMATIVE.**

#### E.13.1 WO creation

Created by fulfillment dispatch worker:

```python
def create_work_order_from_sales_order_line(
    *, organization_id, actor_id, sales_order_line_id,
) -> WorkOrder:
    """ Idempotent on (sales_order_line_id). """
```

#### E.13.2 WO state services

```python
def assign_work_order(*, organization_id, actor_id, work_order_id,
                       assignee_membership_id, scheduled_date,
                       client_location_id=None) -> WorkOrder: ...

def unassign_work_order(...) -> WorkOrder: ...
def start_work_order(...) -> WorkOrder: ...
def put_work_order_on_hold(*, ..., reason) -> WorkOrder: ...
def resume_work_order(...) -> WorkOrder: ...

def complete_work_order(
    *, organization_id, actor_id, work_order_id,
    outcome_notes: str,        # required, min 10 chars
) -> WorkOrder:
    """
    Required: workorders.complete; State: IN_PROGRESS
    SOL.fulfillment_status = FULFILLED;
    SOL.invoice_eligibility evaluation per InvoicingPolicy;
    recompute_sales_order_status enqueued.
    """

def cancel_work_order(*, ..., reason) -> WorkOrder: ...
```

#### E.13.3 Outcome notes minimum

`outcome_notes` requires at least 10 characters. Empty/whitespace-only rejects with `CompletionValidationError`.

#### E.13.4 Future-friendly fields

- `WorkOrder.recurrence_template_id` — null in v1; reserved for recurring service templates.
- Completion photos via DocumentAttachment with `document_kind=COMPLETION_PHOTO`.

#### E.13.5 RBAC enforcement matrix (Work Orders)

| Action | Queryset | Capability | State | Object Check | Audit |
| --- | --- | --- | --- | --- | --- |
| WO list | `for_membership(m)` filtered by assignee unless `workorders.view_all` | `workorders.view` | — | — | — |
| WO detail | `for_membership(m)` | `workorders.view` | — | assignee or `workorders.view_all` | — |
| Assign | `for_membership(m)` | `workorders.assign` | PENDING, ASSIGNED | new assignee in org+scope | `WO_ASSIGNED` |
| Unassign | `for_membership(m)` | `workorders.assign` | ASSIGNED | — | `WO_UNASSIGNED` |
| Start work | `for_membership(m)` | `workorders.update_status` | ASSIGNED | assignee or `workorders.manage` | `WO_STARTED` |
| Put on hold | `for_membership(m)` | `workorders.update_status` | IN_PROGRESS | assignee or `workorders.manage` | `WO_ON_HOLD` |
| Resume | `for_membership(m)` | `workorders.update_status` | ON_HOLD | assignee or `workorders.manage` | `WO_RESUMED` |
| Complete | `for_membership(m)` | `workorders.complete` | IN_PROGRESS | assignee; outcome_notes ≥ 10 chars | `WO_COMPLETED` |
| Cancel | `for_membership(m)` | `workorders.manage` | PENDING, ASSIGNED | — | `WO_CANCELLED` |

---

## Part F — Billing

### F.1 Invoice Lifecycle

**Status: NORMATIVE.**

#### F.1.1 Invoice creation

Invoices are created from a SalesOrder. An Invoice covers ONE OR MORE SalesOrderLines. Lines within a single Invoice MUST come from a single SalesOrder.

```python
def create_invoice(
    *,
    organization_id: UUID,
    actor_id: UUID,
    sales_order_id: UUID,
    line_inputs: list[InvoiceLineInput],
    issue_date: date | None = None,
    due_date: date | None = None,
    notes: str | None = None,
) -> Invoice:
    """
    Required capability: billing.invoice.create
    Validates: every SOL referenced is invoice_eligibility=ELIGIBLE.
    Validates: requested invoice quantities ≤ remaining-uninvoiced-quantity per SOL.
    """

@dataclass(frozen=True)
class InvoiceLineInput:
    sales_order_line_id: UUID
    quantity: Decimal
```

Behavior (in transaction):

1. Lock the SalesOrder; verify status not in {CANCELLED, CLOSED}.
2. For each input: resolve SOL; verify `invoice_eligibility = ELIGIBLE`; check remaining quantity.
3. Allocate Invoice number.
4. Create Invoice row with totals computed from lines + tax (F.4).
5. For each input, create InvoiceLine referencing the SOL's `pricing_snapshot_id`.
6. Emit `INVOICE_CREATED` audit.
7. Update SalesOrder.status via `recompute_sales_order_status`.

#### F.1.2 Snapshot-driven invoice math

The InvoiceLine's pricing is sourced from the PricingSnapshot's `outputs`, NOT recomputed.

For partial invoicing (`input.quantity < SOL.quantity`):

```python
invoice_line.unit_price_snapshot = snapshot.effective_unit_price
invoice_line.line_subtotal = snapshot.effective_unit_price × input.quantity
invoice_line.tax_amount = (snapshot.tax_amount × input.quantity / snapshot.quantity)
invoice_line.line_total = invoice_line.line_subtotal + invoice_line.tax_amount
```

Discount allocation scales proportionally. Rounding once on final InvoiceLine totals.

#### F.1.3 Bundle invoicing

For a `BUNDLE` SalesOrderLine:

- Parent BUNDLE line appears as single InvoiceLine showing bundle name and bundle price.
- Child component lines do NOT appear on the invoice.
- Eligibility: parent ELIGIBLE only when ALL children ELIGIBLE (per InvoicingPolicy).
- Partial invoicing only at parent level in v1.

#### F.1.4 Invoice send

```python
def send_invoice(
    *, organization_id: UUID, actor_id: UUID, invoice_id: UUID,
    recipient_emails: list[str], cover_message: str | None = None,
    expected_optimistic_version: int | None = None,
) -> Invoice:
    """ Required: billing.invoice.send; State: DRAFT """
```

Behavior:

1. Lock Invoice; verify status == DRAFT.
2. Set `status=SENT, sent_at=now()`.
3. Insert outbox: `invoice.generate_pdf` then `invoice.send_email`.
4. Emit `INVOICE_SENT` audit.

#### F.1.5 Invoice void

```python
def void_invoice(
    *, organization_id: UUID, actor_id: UUID, invoice_id: UUID, reason: str,
) -> Invoice:
    """
    Required: billing.invoice.void
    Required state: NOT PAID
    Rejects if any non-reversed PaymentAllocation exists.
    """
```

If voided invoice's underlying SOLs were the only invoiced lines on a SalesOrder, `recompute_sales_order_status` rolls the SO back to IN_FULFILLMENT or FULFILLED.

#### F.1.6 Overdue marking

Daily Celery beat job `invoice.overdue_check` processes Invoices in `SENT` status with `due_date < today` and sets them to `OVERDUE`. Each transition emits `INVOICE_OVERDUE` audit and inserts `invoice.send_overdue_notification` outbox entry.

#### F.1.7 RBAC enforcement matrix

| Action | Queryset | Capability | State | Audit |
| --- | --- | --- | --- | --- |
| Invoice list/detail | `for_membership(m)` | `billing.view` | — | — |
| Create invoice | `for_membership(m)` | `billing.invoice.create` | — | `INVOICE_CREATED` |
| Send invoice | `for_membership(m)` | `billing.invoice.send` | DRAFT | `INVOICE_SENT` |
| Void invoice | `for_membership(m)` | `billing.invoice.void` | NOT PAID, no allocations | `INVOICE_VOIDED` |

### F.2 Invoice Eligibility Rules

**Status: NORMATIVE.**

#### F.2.1 Per-line-type eligibility

| line_type | InvoicingPolicy field | Trigger to ELIGIBLE |
| --- | --- | --- |
| SERVICE | `service_invoiceable_on` | WORK_ORDER_COMPLETE: WO.status → COMPLETED. MANUAL_RELEASE: explicit action |
| RESALE_PRODUCT | `resale_invoiceable_on` | PO_RECEIPT: total allocated received quantity ≥ SOL.quantity |
| MANUFACTURED_PRODUCT | `manufactured_invoiceable_on` | BUILD_ORDER_COMPLETE: BO.status → COMPLETE |
| BUNDLE | `bundle_invoiceable_on` | ALL_COMPONENTS_ELIGIBLE: all children ELIGIBLE |

#### F.2.2 Eligibility computation

```python
def recompute_sales_order_line_eligibility(
    *, organization_id: UUID, sales_order_line_id: UUID,
) -> SalesOrderLine:
    """
    Idempotent. Reads InvoicingPolicy + fulfillment artifact state.
    Sets sales_order_line.invoice_eligibility ∈ {NOT_YET, ELIGIBLE, INVOICED, NOT_INVOICEABLE}.
    """
```

#### F.2.3 Manual release

```python
def manual_release_for_invoicing(
    *, organization_id, actor_id, sales_order_line_id, reason: str,
) -> SalesOrderLine:
    """
    Required: billing.invoice.create
    Required: InvoicingPolicy field for line_type is MANUAL_RELEASE
    """
```

#### F.2.4 InvoicingPolicy

```python
def update_invoicing_policy(
    *, organization_id, actor_id, **policy_fields,
) -> InvoicingPolicy:
    """
    Required capability: admin.org.settings
    Existing SOLs are NOT retroactively re-evaluated; new policy applies prospectively.
    """
```

#### F.2.5 RBAC enforcement matrix

| Action | Capability | Audit |
| --- | --- | --- |
| View invoicing policy | `billing.view` OR `admin.org.settings` | — |
| Update invoicing policy | `admin.org.settings`; sensitive | `INVOICING_POLICY_UPDATED` |
| Manual release | `billing.invoice.create` | `LINE_RELEASED_FOR_INVOICING` |

### F.3 Payment, Allocation, Reversal

**Status: NORMATIVE.**

#### F.3.1 Payment recording

```python
def record_payment(
    *,
    organization_id: UUID,
    actor_id: UUID,
    client_id: UUID,
    amount: Decimal,
    payment_date: date,
    method: PaymentMethod,
    reference: str | None,
    notes: str | None,
    initial_allocations: list[PaymentAllocationInput] = (),
    idempotency_key: str,
) -> Payment:
    """ Required: billing.payment.record; sensitive (re-auth) """
```

Behavior (in transaction):

1. Idempotency check on (organization_id, idempotency_key).
2. Lock Client `FOR UPDATE`.
3. Validate every `invoice_id` belongs to client and is in `{SENT, OVERDUE, PART_PAID}`.
4. Validate `SUM(initial_allocations.amount_applied) ≤ amount`.
5. Validate per-invoice: `allocation.amount_applied ≤ invoice.balance_due`.
6. Insert Payment row with `unapplied_amount = amount − SUM(allocations)`.
7. Insert PaymentAllocation rows.
8. For each affected invoice: lock; recompute `amount_paid = SUM(non-reversed allocations)`; update `balance_due`; transition state.
9. Emit `PAYMENT_RECORDED` audit.

#### F.3.2 Payment allocation (post-creation)

```python
def allocate_payment(
    *, organization_id, actor_id, payment_id: UUID,
    allocations: list[PaymentAllocationInput],
) -> Payment:
    """ Validates: SUM(allocations.amount_applied) ≤ payment.unapplied_amount """
```

#### F.3.3 Allocation reversal

```python
def reverse_payment_allocation(
    *, organization_id, actor_id, allocation_id: UUID, reason: str,
) -> PaymentAllocation:
    """ Required: billing.payment.edit; sensitive """
```

Sets `reversed_at, reversed_by_id, reversed_reason` on the original (no in-place mutation of amount). Recomputes Invoice.amount_paid, balance_due, status.

#### F.3.4 Payment adjustment

```python
def create_payment_adjustment(
    *, organization_id, actor_id, original_payment_id: UUID,
    adjustment_type: AdjustmentType,
    amount_delta: Decimal,
    reason: str,
) -> PaymentAdjustment:
    """ Required: billing.payment.edit; sensitive """
```

The original Payment row is NOT modified. Effective payment amount for reporting = `original.amount + SUM(adjustments.amount_delta)`.

A REVERSAL adjustment requires all that payment's allocations to be reversed first.

#### F.3.5 Overpayment handling

A Payment with `unapplied_amount > 0` after allocations remains as unapplied credit. Visible on client's account. MAY be applied to future invoices via `allocate_payment`. NOT auto-applied. Refunds and write-offs out of v1.

#### F.3.6 RBAC enforcement matrix

| Action | Capability | State | Audit |
| --- | --- | --- | --- |
| Payment list/detail | `billing.view` | — | — |
| Record payment | `billing.payment.record`; sensitive | invoice in SENT/OVERDUE/PART_PAID | `PAYMENT_RECORDED` |
| Allocate payment | `billing.payment.record`; sensitive | unapplied_amount > 0 | `PAYMENT_ALLOCATED` |
| Reverse allocation | `billing.payment.edit`; sensitive | not already reversed | `PAYMENT_ALLOCATION_REVERSED` |
| Create payment adjustment | `billing.payment.edit`; sensitive | — | `PAYMENT_ADJUSTED` |

### F.4 Tax Calculation

**Status: NORMATIVE.**

#### F.4.1 Tax model recap

v1 ships per-jurisdictional tax. Entities: `TaxJurisdiction` (org-scoped, hierarchical), `TaxRate` (effective-dated), `Location.tax_jurisdiction_id`, `Organization.default_tax_jurisdiction_id`, `Client.tax_exempt`.

#### F.4.2 Resolution algorithm

```python
def resolve_applicable_tax_rates(
    *, organization_id: UUID, location_id: UUID,
    line_type: LineType, on_date: date,
    client_tax_exempt: bool,
) -> list[TaxRateSnapshot]:
    if client_tax_exempt:
        return []

    location = Location.objects.for_org(organization_id).get(id=location_id)
    jurisdiction_id = location.tax_jurisdiction_id

    if jurisdiction_id is None:
        jurisdiction_id = Organization.objects.get(id=organization_id).default_tax_jurisdiction_id
    if jurisdiction_id is None:
        return []

    jurisdictions = collect_jurisdiction_ancestors(jurisdiction_id)

    rates = TaxRate.objects.for_org(organization_id).filter(
        tax_jurisdiction_id__in=[j.id for j in jurisdictions],
        is_active=True,
        effective_from__lte=on_date,
    ).filter(
        Q(effective_until__isnull=True) | Q(effective_until__gte=on_date),
    )
    rates = [r for r in rates if not r.applies_to_line_types
                                   or line_type.value in r.applies_to_line_types]
    return sort_rates(rates)
```

#### F.4.3 Hierarchy semantics

A `TaxJurisdiction` MAY have a `parent_jurisdiction_id`. ALL ancestors' rates apply (sum). Walking bounded to depth 5.

```sql
WITH RECURSIVE ancestors AS (
    SELECT id, parent_jurisdiction_id, 0 AS depth
      FROM tax_jurisdictions WHERE id = %(start_id)s
    UNION ALL
    SELECT j.id, j.parent_jurisdiction_id, a.depth + 1
      FROM tax_jurisdictions j
      JOIN ancestors a ON j.id = a.parent_jurisdiction_id
     WHERE a.depth < 5
)
SELECT id FROM ancestors;
```

Cached per (location_id, on_date) for the duration of a single pricing pipeline invocation.

#### F.4.4 Tax modifier behavior recap

`modifier.tax`:

1. Reads `context.tax_rates`.
2. For each rate: `component = (final_unit_price × quantity − discount_amount) × rate_percent / 100`.
3. Sums all components into `tax_amount`.
4. Records each component in `modifier_log`.

#### F.4.5 Tax-exempt client handling

When `Client.tax_exempt=True`:

- `resolve_applicable_tax_rates` returns empty list → `tax_amount = 0`.
- PricingSnapshot records `inputs.client_tax_exempt = True` and `inputs.client_tax_exempt_certificate_ref`.
- Quote/Invoice PDFs include the exemption certificate reference.

Rule: `tax = 0 if client_tax_exempt OR not line.taxable`.

#### F.4.6 Tax service surface

```python
def create_tax_jurisdiction(
    *, organization_id, actor_id, code, name,
    parent_jurisdiction_id=None,
) -> TaxJurisdiction: ...

def update_tax_jurisdiction(...) -> TaxJurisdiction: ...
def deactivate_tax_jurisdiction(...) -> TaxJurisdiction: ...

def create_tax_rate(...) -> TaxRate: ...
def supersede_tax_rate(
    *, organization_id, actor_id, old_rate_id,
    new_rate_percent, effective_from,
) -> tuple[TaxRate, TaxRate]:
    """ Atomic: sets old.effective_until = new.effective_from - 1 day; creates new rate. """
```

#### F.4.7 RBAC enforcement matrix

| Action | Capability | Audit |
| --- | --- | --- |
| View tax jurisdictions | `billing.view` OR `tax.jurisdictions.manage` | — |
| Create/edit jurisdiction | `tax.jurisdictions.manage` | `TAX_JURISDICTION_SAVED` |
| Create tax rate | `tax.jurisdictions.manage` | `TAX_RATE_CREATED` |
| Supersede tax rate | `tax.jurisdictions.manage` | `TAX_RATE_SUPERSEDED` |

### F.5 Accounting Integration Boundary

**Status: NORMATIVE.**

#### F.5.1 Adapter interface

```python
@runtime_checkable
class AccountingAdapter(Protocol):
    adapter_code: str

    def sync_client(self, client: ClientSyncPayload) -> SyncResult: ...
    def sync_invoice(self, invoice: InvoiceSyncPayload) -> SyncResult: ...
    def sync_payment(self, payment: PaymentSyncPayload) -> SyncResult: ...

@dataclass(frozen=True)
class SyncResult:
    success: bool
    external_id: str | None
    error_message: str | None
    error_code: str | None
    raw_response: dict | None
```

#### F.5.2 NoopAccountingAdapter

```python
class NoopAccountingAdapter:
    adapter_code = "noop"

    def sync_client(self, client) -> SyncResult:
        return SyncResult(success=True, external_id=None, error_message=None,
                          error_code=None, raw_response=None)
```

The Noop adapter is the default in v1.

#### F.5.3 Sync invocation pattern

Sync is **outbox-driven**, not synchronous:

```python
outbox.publish(
    topic="accounting.sync_payment",
    idempotency_key=f"acct-payment-sync:{payment.id}",
    payload={"payment_id": str(payment.id)},
)
```

Worker consumes from outbox, calls adapter, updates sync_status fields.

#### F.5.4 Adapter registration

```python
ACCOUNTING_ADAPTER_REGISTRY: dict[str, type[AccountingAdapter]] = {
    "noop": NoopAccountingAdapter,
    # Future: "quickbooks", "xero", "netsuite"
}
```

`Organization.accounting_adapter_code` (default "noop") and `accounting_adapter_config` (JSONB, encrypted at rest).

#### F.5.5 What v1 does NOT do

- Auto-fetch chart-of-accounts.
- Post journal entries.
- Reconcile bank statements.
- Generate GL exports.

#### F.5.6 RBAC enforcement matrix

| Action | Capability | Audit |
| --- | --- | --- |
| View sync status | `billing.view` | — |
| Manually retry sync | `billing.invoice.send` | `ACCOUNTING_SYNC_RETRIED` |
| Configure adapter | `admin.org.settings`; sensitive | `ACCOUNTING_ADAPTER_CONFIGURED` |

### F.6 Reporting and Exports

**Status: NORMATIVE.**

#### F.6.1 v1 fixed report catalog

| Report code | Title | Capability | Description |
| --- | --- | --- | --- |
| `ar_aging` | A/R Aging | `billing.reports.view` | Outstanding invoices grouped by age (Current, 1-30, 31-60, 61-90, 90+) per client |
| `quote_pipeline` | Quote Pipeline by Stage | `reporting.view` | Active quote count and total value grouped by status |
| `wo_completion_rate` | Work Order Completion Rate | `reporting.view` | WO created/completed/cancelled/avg-completion-time |
| `build_cost_variance` | Build Cost Variance | `reporting.advanced` | BO actual vs. estimated material/labor variance |
| `sales_by_location` | Sales by Location | `reporting.view` | Accepted-quote total and invoiced total per Region/Market/Location |
| `sales_by_rep` | Sales by Sales Rep | `reporting.view` | Accepted-quote total per owner_membership |
| `invoice_payment_summary` | Invoice & Payment Summary | `billing.reports.view` | Total invoiced, paid, outstanding, voided per period |
| `pricing_approval_log` | Pricing Approval Log | `reporting.advanced` | All PricingApproval rows with status, requester, approver, decision, deltas |
| `tax_collected_by_jurisdiction` | Tax Collected by Jurisdiction | `billing.reports.view` | Tax components from invoice snapshots grouped by jurisdiction |
| `lead_funnel` | Lead Funnel | `reporting.view` | Lead counts by stage and source, conversion rate |

#### F.6.2 Report execution

```python
def run_report(
    *,
    organization_id: UUID,
    actor_id: UUID,
    report_code: str,
    parameters: dict,
    output_format: Literal["json", "csv"] = "json",
    async_threshold_rows: int = 5000,
) -> ReportRunResult | ReportExportJob:
    """ Required capability: per the report's catalog entry. """
```

#### F.6.3 ReportExportJob

```text
ReportExportJob
  id: UUID, pk
  organization_id: UUID, fk
  report_code: TEXT
  requested_by_id: UUID, fk -> User
  parameters_json: JSONB
  status: ENUM(QUEUED, RUNNING, SUCCEEDED, FAILED, CANCELLED)
  output_attachment_id: UUID, fk -> DocumentAttachment, null
  output_format: ENUM(CSV, JSON), default(CSV)
  row_count: BIGINT, null
  error_message: TEXT, null
  created_at, started_at, completed_at
```

Async job runs in `reports` Celery queue.

#### F.6.4 Export retention

DocumentAttachment rows from report exports have `document_kind=EXPORT_ARCHIVE` and `retention_until = created_at + 14 days`.

#### F.6.5 Tenant scoping

Every report query uses `for_org(organization_id)` and intersects with `for_membership(membership)` for operating-scope.

#### F.6.6 RBAC enforcement matrix

| Action | Capability | Audit |
| --- | --- | --- |
| View report (sync) | per report's listed capability | `REPORT_RUN` |
| Queue async export | per report's capability + `reporting.export` | `REPORT_EXPORT_QUEUED` |
| Download export | (derived from output attachment) | `ATTACHMENT_ACCESSED` (sampled) |
| Cancel export job | `reporting.export` | `REPORT_EXPORT_CANCELLED` |

---

## Part G — Cross-Cutting Concerns

### G.1 Service-Layer Architecture

**Status: NORMATIVE.**

#### G.1.1 The contract

Every state-changing workflow MUST execute through a function in `apps/<domain>/services/`.

#### G.1.2 Function shape

```python
def <verb_phrase>(
    *,
    organization_id: UUID,
    actor_id: UUID,
    <domain inputs as keyword-only primitives or frozen dataclasses>,
    idempotency_key: str | None = None,
    expected_optimistic_version: int | None = None,
) -> <DomainEntity | DomainResult>:
    """
    NORMATIVE docstring header:
    - Required capability: <code>
    - Required state(s): <list>
    - Sensitive: <yes/no>
    - Idempotent: <yes/no, key derivation>
    - Emits audit: <event types>
    - Side effects: <outbox topics>
    """
    # 1. Tenant guard
    # 2. Capability check
    # 3. Acquire locks
    # 4. Validate state preconditions
    # 5. Validate operating scope on target objects
    # 6. Mutate
    # 7. Insert outbox entries
    # 8. Emit audit
    # 9. Return
```

#### G.1.3 What services MUST NOT do

- Accept Django `request` objects, `QueryDict`, `HttpResponse`.
- Return HTTP responses or Django redirects.
- Render templates.
- Call `request.user`, `messages.add_message`, request-scoped helpers.
- Perform direct file I/O outside `django.core.files.storage` interfaces.
- Emit print statements.
- Catch a domain exception and return None.

#### G.1.4 What services MUST do

- Wrap state-changing logic in `transaction.atomic()`.
- Use `select_for_update` on entities being mutated.
- Validate inputs at the service boundary.
- Raise typed domain exceptions (G.2).
- Emit audit events INSIDE the transaction.
- Insert outbox entries INSIDE the transaction.
- Return a fully-populated domain entity or `*Result` dataclass.

#### G.1.5 File layout

```text
apps/<domain>/
  services/
    __init__.py                          # re-exports public service functions
    <verb_object>.py                     # one file per service
    _shared.py
  models.py
  views.py
  forms.py
  serializers.py                          # DRF (Phase 2)
  admin.py
  tests/
    services/
      test_<verb_object>.py
```

One file per public service function.

#### G.1.6 Result types

```python
@dataclass(frozen=True)
class QuoteAcceptanceResult:
    quote_version_id: UUID
    sales_order_id: UUID
    client_id: UUID
    fulfillment_outbox_ids: list[int]

@dataclass(frozen=True)
class QuotePricingResult:
    quote_version_id: UUID
    line_results: list[PricingResult]
    total_subtotal: Decimal
    total_discount: Decimal
    total_tax: Decimal
    total_amount: Decimal
```

#### G.1.7 Dependency injection (light-touch)

Services do NOT use a DI container. Module-level lookups + mock patching.

#### G.1.8 Static enforcement

CI lint rule blocks PRs on:

- `.save()`, `.delete()`, `Model.objects.create(...)`, `.update(...)` outside services
- `request.user` referenced inside services
- Service function declared without `*,`
- `GenericForeignKey` declared anywhere
- `forms.ModelChoiceField` not inheriting `TenantModelChoiceField`

### G.2 Domain Exception Taxonomy

**Status: NORMATIVE.**

#### G.2.1 Hierarchy

```text
DomainError                              # base; never raised directly
├── ConfigurationError                   # tenant or platform misconfiguration; usually 500
├── AuthenticationError                  # not authenticated / invalid creds
├── AuthorizationError                   # authenticated but lacks permission
│   ├── CapabilityRequiredError
│   ├── OperatingScopeViolationError
│   └── TenantViolationError
├── HandoffInvalidError                  # signed-token failures
├── ValidationError                      # input doesn't pass shape/business validation
│   ├── PricingValidationError
│   ├── CompletionValidationError
│   ├── ClientResolutionError
│   └── BundleConfigurationError
├── StateError                           # entity in wrong state for action
│   ├── InvalidStateTransitionError
│   ├── PricingApprovalPendingError
│   └── EntityLockedError
├── ConcurrencyError                     # optimistic concurrency / lock failures
│   ├── ConcurrencyConflictError
│   └── IdempotencyConflictError
├── ReplayError                          # snapshot replay
│   ├── EngineVersionMismatchError
│   └── SnapshotReplayMismatchError
└── IntegrationError                     # external system failures
    ├── AccountingSyncError
    └── EmailDeliveryError
```

#### G.2.2 Base class

```python
class DomainError(Exception):
    error_code: str = "domain_error"
    default_http_status: int = 500

    def __init__(
        self,
        message: str,
        *,
        details: dict | None = None,
        cause: Exception | None = None,
    ):
        super().__init__(message)
        self.message = message
        self.details = details or {}
        self.cause = cause

    def to_dict(self) -> dict:
        return {
            "error_code": self.error_code,
            "message": self.message,
            "details": self.details,
        }
```

#### G.2.3 Subclass contracts

| Class | error_code | HTTP | UI message template |
| --- | --- | --- | --- |
| `ConfigurationError` | `configuration_error` | 500 | "Configuration issue. Please contact support." |
| `AuthenticationError` | `authentication_required` | 401 | "Please sign in to continue." |
| `CapabilityRequiredError` | `capability_required` | 403 | "You don't have permission to perform this action." |
| `OperatingScopeViolationError` | `operating_scope_violation` | 403 | "This record is outside your assigned region/market/location." |
| `TenantViolationError` | `tenant_violation` | 403 | "This record belongs to a different organization." |
| `HandoffInvalidError` | `handoff_invalid` | 400 | "Sign-in link is invalid or expired. Please sign in again." |
| `ValidationError` (base) | `validation_error` | 400 | "Some fields are invalid. See details." |
| `PricingValidationError` | `pricing_validation_error` | 400 | "Pricing inputs are invalid: {message}" |
| `CompletionValidationError` | `completion_validation_error` | 400 | "Completion notes must be at least 10 characters." |
| `ClientResolutionError` | `client_resolution_error` | 400 | "Please confirm the client before accepting this quote." |
| `BundleConfigurationError` | `bundle_configuration_error` | 400 | "This bundle requires {message}." |
| `InvalidStateTransitionError` | `invalid_state_transition` | 409 | "This action isn't available for the current status ({current_state})." |
| `PricingApprovalPendingError` | `pricing_approval_pending` | 409 | "Cannot send: a pricing approval is pending on one or more lines." |
| `EntityLockedError` | `entity_locked` | 409 | "This {entity} is locked and cannot be edited." |
| `ConcurrencyConflictError` | `concurrency_conflict` | 409 | "Someone else updated this {entity}. Reload and try again." |
| `IdempotencyConflictError` | `idempotency_conflict` | 409 | "This action is already in progress." |
| `EngineVersionMismatchError` | `engine_version_mismatch` | 500 | "Pricing engine version mismatch on replay." |
| `SnapshotReplayMismatchError` | `snapshot_replay_mismatch` | 500 | "Stored pricing differs from recomputed value." |
| `AccountingSyncError` | `accounting_sync_error` | 502 | "Accounting sync failed. The local record is saved." |
| `EmailDeliveryError` | `email_delivery_error` | 502 | "We couldn't send the email. The record is saved; please retry sending." |

#### G.2.4 Exception-to-HTTP translator (DRF)

```python
def domain_exception_handler(exc, context):
    if isinstance(exc, DomainError):
        return Response(
            data=exc.to_dict(),
            status=exc.default_http_status,
            headers={"X-Error-Code": exc.error_code},
        )
    return drf_default_exception_handler(exc, context)
```

#### G.2.5 Exception-to-UI translator (Phase 1)

```python
class DomainErrorMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        return self.get_response(request)

    def process_exception(self, request, exception):
        if not isinstance(exception, DomainError):
            return None
        logger.warning("domain_error", extra={...})
        if isinstance(exception, (CapabilityRequiredError, OperatingScopeViolationError,
                                    TenantViolationError)):
            messages.error(request, exception.message)
            return redirect("dashboard")
        if isinstance(exception, (ConcurrencyConflictError, IdempotencyConflictError,
                                    InvalidStateTransitionError)):
            messages.warning(request, exception.message)
            return redirect(request.META.get("HTTP_REFERER", "dashboard"))
        return render(request, "errors/domain_error.html",
                       {"error": exception}, status=exception.default_http_status)
```

#### G.2.6 Logging contract

Every `DomainError` raise emits a structured log entry:

```python
logger.warning(
    "domain_error",
    extra={
        "error_code": exc.error_code,
        "details": exc.details,
        "request_id": current_request_id(),
        "actor_id": current_actor_id(),
        "organization_id": current_organization_id(),
    },
)
```

### G.3 Async Processing, Outbox, and Scheduled Jobs

**Status: NORMATIVE.**

#### G.3.1 Async posture

All async work MUST be executed by Celery workers. Domain services MUST NOT perform slow external side effects directly inside request/response paths.

Examples of async work:

- sending email
- generating quote PDFs
- generating invoice PDFs
- dispatching fulfillment artifacts
- running exports
- pruning retained data
- checking quote expiry
- checking invoice overdue status
- expiring pricing approvals
- sending task reminders

#### G.3.2 Outbox requirement

Any workflow that mutates business state and requires a side effect MUST publish that side effect through the transactional outbox.

The outbox insert MUST occur in the same database transaction as the domain mutation.

```python
# NORMATIVE: shape
def publish_outbox(
    *,
    organization_id: UUID | None,
    topic: str,
    idempotency_key: str,
    payload: dict,
    correlation_id: str,
) -> OutboxEntry:
    ...
```

The outbox table is the durability boundary. Celery is the execution mechanism, not the source of truth.

#### G.3.3 Outbox dispatcher

The outbox dispatcher MAY run as a Celery beat-triggered task or as a long-running worker command. In v1, the default implementation is a beat-triggered dispatcher.

The dispatcher MUST:

1. Select pending rows using `select_for_update(skip_locked=True)`.
2. Respect `next_attempt_at`.
3. Mark rows as `DISPATCHED` before enqueueing.
4. Enqueue a Celery task with the outbox row id.
5. Avoid duplicate dispatch under concurrent dispatcher execution.
6. Move permanently failing rows to dead letter after max attempts.

```python
# NORMATIVE: shape
def dispatch_pending_outbox_entries(*, batch_size: int = 100) -> int:
    ...
```

#### G.3.4 Celery worker requirements

Every Celery task that creates or transitions state MUST be idempotent.

Task requirements:

- Accept primitive IDs, not model instances.
- Re-load records inside the task.
- Use service-layer functions for state changes.
- Use deterministic idempotency keys.
- Emit structured logs with correlation ID.
- Treat retries as normal behavior.
- Never assume exactly-once execution.

#### G.3.5 Celery beat requirements

Exactly one Celery beat scheduler MUST run per environment.

In Docker-based deployment, this is implemented as a single `beat` container in the environment’s Compose file. Running multiple beat containers in the same environment is PROHIBITED.

Beat-triggered jobs MUST be safe to retry. Jobs that would be harmful if duplicated MUST use one of:

- Redis lock with TTL
- PostgreSQL advisory lock
- row-level `SELECT FOR UPDATE`
- deterministic idempotency key

#### G.3.6 Beat-only scheduled jobs

| Job | Frequency | Notes |
| --- | --- | --- |
| `outbox.dispatch_pending` | every 5 seconds | Dispatches pending outbox entries |
| `quotes.expire_sent_quotes` | hourly | Moves expired SENT quotes to EXPIRED |
| `pricing.expire_approvals` | hourly | Moves expired pricing approvals to EXPIRED |
| `invoices.mark_overdue` | hourly | Marks overdue invoices |
| `tasks.send_due_reminders` | every 15 minutes | Sends due/overdue task reminders |
| `audit.ensure_partitions` | daily | Pre-creates AuditEvent partitions |
| `pricing.ensure_snapshot_partitions` | daily | Pre-creates PricingSnapshot partitions |
| `audit.retention_prune` | daily | Prunes retained audit partitions according to policy |
| `attachments.retention_prune` | daily | Deletes expired attachment objects |
| `tenant_deletion.execute_due_requests` | hourly | Executes deletion requests after grace period |
| `demo.refresh_environment` | weekly | Demo environment only |
| `staging.refresh_from_anonymized_prod` | weekly | Staging only |

#### G.3.7 Queue names

The following queue names are reserved:

```text
critical
default
bulk
reports
```

The initial production deployment MAY run one worker consuming all queues. Separate worker containers per queue MAY be introduced later without changing task code.

#### G.3.8 Dead-letter handling

A failed outbox entry becomes `DEAD_LETTER` after max retry attempts. Dead-letter rows MUST preserve:

- source outbox id
- topic
- idempotency key
- payload snapshot
- last error
- attempt count
- failed_at

Dead-letter rows MUST be visible to support/admin users with appropriate permissions.

#### G.3.9 Local development

Local development runs web, worker, beat, PostgreSQL, Redis, and supporting services through Docker Compose. Developers MUST be able to run async workflows locally without Kubernetes.

### G.4 Observability: Logging, Errors, Metrics, Tracing

**Status: NORMATIVE.**

#### G.4.1 Structured logging

All logs are JSON, single-line per event, stdout.

```python
import structlog
logger = structlog.get_logger(__name__)

logger.info(
    "quote_accepted",
    quote_version_id=str(quote.id),
    sales_order_id=str(so.id),
    actor_id=str(actor.id),
    organization_id=str(org.id),
    request_id=current_request_id(),
)
```

Required log keys (auto-injected): `timestamp`, `level`, `logger_name`, `event`, `request_id`, `correlation_id`, `actor_id`, `organization_id`, `tenant_host`, `service`, `environment`, `version`.

#### G.4.2 Correlation IDs

`request_id` generated by middleware on first ingress. Propagates through web → service → outbox → worker → child outbox publishes via `contextvars.ContextVar`.

#### G.4.3 Log levels

| Level | When |
| --- | --- |
| DEBUG | Local development only |
| INFO | Normal flow events |
| WARNING | Recoverable domain errors, retried operations |
| ERROR | Unexpected exceptions, integration failures, DLQ entries |
| CRITICAL | System-wide failures |

#### G.4.4 PII and secret redaction

A structlog processor applies field-level redaction:

```python
REDACTED_FIELDS = {
    "password", "totp_secret", "backup_codes", "backup_codes_hash",
    "session_id", "csrf_token", "handoff_token", "api_token",
    "credit_card_number", "ssn", "tax_id_number",
}
```

Email addresses NOT redacted at this layer (audit needs them).

#### G.4.5 Error monitoring

Sentry integrated for web tier (5xx, sampled 4xx), worker tier (all exceptions, DLQ as ERROR), beat (lock failures). Required before first production tenant launch.

#### G.4.6 Metrics

OpenTelemetry SDK installed; metrics export configurable (no-op default in v1).

| Metric | Type | Labels |
| --- | --- | --- |
| `http_request_duration_seconds` | histogram | method, route, status_code |
| `http_requests_total` | counter | method, route, status_code |
| `domain_error_total` | counter | error_code |
| `service_function_duration_seconds` | histogram | service_name |
| `outbox_publish_total` | counter | topic |
| `outbox_pending_count` | gauge | topic, age_bucket |
| `outbox_dispatch_duration_seconds` | histogram | topic |
| `celery_task_duration_seconds` | histogram | topic, queue, status |
| `celery_task_total` | counter | topic, queue, status |
| `audit_event_emitted_total` | counter | event_type |
| `pricing_pipeline_duration_seconds` | histogram | strategy_code |
| `pricing_snapshot_replay_duration_seconds` | histogram | engine_version |

#### G.4.7 Tracing

OpenTelemetry tracing SDK installed. Spans automatically created for HTTP requests, Celery tasks, service-layer functions (via decorator), pricing pipeline invocations. Exporter MAY be no-op in v1.

#### G.4.8 Health endpoints

| Endpoint | Returns | Used by |
| --- | --- | --- |
| `GET /healthz` | 200 OK with `{"status": "ok"}` | uptime monitor / process health check |
| `GET /readyz` | 200 if DB + Redis reachable; 503 otherwise | deploy smoke test / reverse proxy health check |
| `GET /healthz/deep` | Full check (DB write, Redis SET, object store HEAD) | manual ops |

Unauthenticated.

#### G.4.9 Alert thresholds (initial)

| Alert | Condition | Severity |
| --- | --- | --- |
| Web error rate elevated | 5xx rate > 1% over 5m | warning |
| Web error rate critical | 5xx rate > 5% over 5m | critical |
| Outbox backlog | `outbox_pending_count{age_bucket=">5m"}` > 100 | warning |
| Outbox stale | `outbox_pending_count{age_bucket=">1h"}` > 10 | critical |
| Beat lock not held | held for < 80% of interval over 10m | critical |
| DLQ growing | DLQ insertion rate > 0.1/min sustained 10m | warning |
| Sentry alert volume spike | new event rate > 10× baseline | warning |
| DB replication lag | replica lag > 30s | warning |

### G.5 Audit Logging

**Status: NORMATIVE.**

#### G.5.1 What gets audited

| Category | Examples | Audited? |
| --- | --- | --- |
| Authentication | login attempts, 2FA, password reset | YES |
| Authorization decisions | denials | NO (errors-only via logs) |
| State transitions | quote send, accept, invoice paid | YES |
| Pricing | overrides, approvals, snapshot writes | YES (write); replay reads NO |
| Admin actions | role/capability changes, member invite/suspend | YES |
| Impersonation | start/end, every action during | YES |
| Data access (read) | most reads | NO |
| Data access (sensitive read) | EXPORT_ARCHIVE downloads, audit search | YES |
| Tenant lifecycle | export request, deletion, deletion execution | YES |

#### G.5.2 AuditEvent registry (consolidated)

**Authentication / session:**
`LOGIN_ATTEMPTED`, `LOGIN_SUCCEEDED`, `LOGIN_FAILED`, `2FA_ENROLLMENT_STARTED`, `2FA_ENROLLMENT_COMPLETED`, `2FA_RE_ENROLLMENT`, `2FA_BACKUP_CODE_USED`, `ACCOUNT_LOCKED`, `PASSWORD_CHANGED`, `PASSWORD_RESET_REQUESTED`, `PASSWORD_RESET_COMPLETED`, `PASSWORD_BREACH_DETECTED`, `HANDOFF_TOKEN_ISSUED`, `HANDOFF_TOKEN_CONSUMED`, `HANDOFF_TOKEN_REJECTED`, `HANDOFF_REPLAY_DETECTED`, `SENSITIVE_ACTION_REAUTH`, `LOGOUT`, `SESSION_EXPIRED`

**Impersonation:**
`IMPERSONATION_STARTED`, `IMPERSONATION_ENDED`, `IMPERSONATION_AUTO_ENDED`, `IMPERSONATION_FORCE_TERMINATED`, `PLATFORM_ADMIN_QUERY`

**Lead:** `LEAD_CREATED`, `LEAD_UPDATED`, `LEAD_ASSIGNED`, `LEAD_STATUS_CHANGED`, `LEAD_ARCHIVED`, `LEAD_CONVERTED`

**Quote:** `QUOTE_VERSION_CREATED`, `QUOTE_LINE_*`, `QUOTE_DISCOUNT_APPLIED`, `QUOTE_SENT`, `QUOTE_RETRACTED`, `QUOTE_LINES_INHERITED`, `QUOTE_ACCEPTED`, `QUOTE_DECLINED`, `QUOTE_EXPIRED`, `QUOTE_DRAFT_DELETED`

**Client:** `CLIENT_CREATED`, `CLIENT_UPDATED`, `CLIENT_DEACTIVATED`, `CLIENT_REACTIVATED`, `CLIENT_CONTACT_*`, `CLIENT_LOCATION_*`, `CLIENT_MERGED`

**Sales Order:** `ORDER_NOTES_UPDATED`, `ORDER_CANCELLED`, `ORDER_FULFILLMENT_TRIGGERED`, `ORDER_STATUS_CHANGED`

**Work Order:** `WORK_ORDER_CREATED`, `WO_ASSIGNED`, `WO_UNASSIGNED`, `WO_STARTED`, `WO_ON_HOLD`, `WO_RESUMED`, `WO_COMPLETED`, `WO_CANCELLED`

**Purchase Order:** `PO_CREATED`, `PO_UPDATED`, `PO_ALLOCATION_*`, `PO_SUBMITTED`, `PO_ACKNOWLEDGED`, `PO_RECEIPT_RECORDED`, `PO_CANCELLED`

**Build Order:** `BUILD_ORDER_CREATED`, `BUILD_STARTED`, `BUILD_ON_HOLD`, `BUILD_RESUMED`, `BUILD_SUBMITTED_FOR_QA`, `BUILD_APPROVED`, `BUILD_REJECTED`, `BUILD_CANCELLED`, `BUILD_LABOR_RECORDED`, `BUILD_LABOR_ADJUSTED`, `BOM_VERSION_CREATED`, `BOM_VERSION_ACTIVATED`, `BOM_LINE_SAVED`, `BOM_VERSION_DRAFT_DELETED`

**Catalog:** `CATALOG_SERVICE_SAVED`, `CATALOG_SERVICE_STATUS_CHANGED`, `CATALOG_PRODUCT_SAVED`, `CATALOG_MATERIAL_SAVED`, `MATERIAL_COST_UPDATED`, `CATALOG_SUPPLIER_SAVED`, `SUPPLIER_PRODUCT_SAVED`, `PREFERRED_SUPPLIER_SET`

**Pricing:** `PRICING_RULE_SAVED`, `PRICING_RULE_DEACTIVATED`, `PRICE_LIST_*`, `CLIENT_CONTRACT_*`, `LABOR_RATE_CARD_*`, `SEGMENT_*`, `PROMOTION_SAVED`, `BUNDLE_SAVED`, `BUNDLE_COMPONENT_SAVED`, `PRICING_APPROVAL_REQUESTED`, `PRICING_APPROVAL_GRANTED`, `PRICING_APPROVAL_REJECTED`, `PRICING_APPROVAL_WITHDRAWN`, `PRICING_APPROVAL_EXPIRED`

**Tax:** `TAX_JURISDICTION_SAVED`, `TAX_RATE_CREATED`, `TAX_RATE_SUPERSEDED`

**Invoice / Payment:** `INVOICE_CREATED`, `INVOICE_SENT`, `INVOICE_OVERDUE`, `INVOICE_VOIDED`, `PAYMENT_RECORDED`, `PAYMENT_ALLOCATED`, `PAYMENT_ALLOCATION_REVERSED`, `PAYMENT_ADJUSTED`, `INVOICING_POLICY_UPDATED`, `LINE_RELEASED_FOR_INVOICING`

**Accounting:** `ACCOUNTING_SYNC_RETRIED`, `ACCOUNTING_ADAPTER_CONFIGURED`, `ACCOUNTING_SYNC_SUCCEEDED`, `ACCOUNTING_SYNC_FAILED`

**Tasks / Communications:** `TASK_CREATED`, `TASK_UPDATED`, `TASK_ASSIGNED`, `TASK_STATUS_CHANGED`, `TASK_COMPLETED`, `TASK_CANCELLED`, `TASK_REOPENED`, `COMMUNICATION_LOGGED`, `COMMUNICATION_SENT`, `COMMUNICATION_UPDATED`

**Documents:** `ATTACHMENT_UPLOADED`, `ATTACHMENT_ACCESSED` (sampled), `ATTACHMENT_DELETED`

**Tenant lifecycle:** `TENANT_EXPORT_REQUESTED`, `TENANT_EXPORT_ASSEMBLED`, `TENANT_EXPORT_DOWNLOADED`, `TENANT_DELETION_REQUESTED`, `TENANT_DELETION_GRACE_STARTED`, `TENANT_DELETION_EXECUTED`, `TENANT_DELETION_CANCELLED`

**Membership / RBAC:** `MEMBER_INVITED`, `MEMBER_ACCEPTED_INVITE`, `MEMBERSHIP_DEACTIVATED`, `MEMBERSHIP_SUSPENDED`, `MEMBERSHIP_REINSTATED`, `MEMBERSHIP_REACTIVATED`, `ROLE_SAVED`, `ROLE_ASSIGNED`, `ROLE_UNASSIGNED`, `CAPABILITY_GRANT_APPLIED`, `ORG_SETTINGS_UPDATED`

**Reporting:** `REPORT_RUN`, `REPORT_EXPORT_QUEUED`, `REPORT_EXPORT_CANCELLED`, `AUDIT_SEARCHED`, `AUDIT_EXPORTED`

**Outbox / DLQ (platform):** `OUTBOX_DLQ_RESET`, `OUTBOX_DLQ_DISCARDED`

#### G.5.3 Audit emission API

```python
def audit_emit(
    event_type: str,
    *,
    actor_id: UUID | None,
    organization_id: UUID | None,
    object_kind: str | None = None,
    object_id: str | None = None,
    payload_before: dict | None = None,
    payload_after: dict | None = None,
    metadata: dict | None = None,
    on_behalf_of_id: UUID | None = None,
) -> None:
    """
    Inserts AuditEvent inside current transaction.
    Raises if not within a transaction.
    Auto-fills request_id, tenant_host, source_ip, user_agent.
    Auto-applies masking per G.5.5.
    """
```

#### G.5.4 Categorization

| Prefix or pattern | Category |
| --- | --- |
| `LOGIN_*`, `2FA_*`, `PASSWORD_*`, `HANDOFF_*`, `ACCOUNT_*`, `LOGOUT`, `SESSION_*` | AUTHENTICATION |
| `IMPERSONATION_*`, `PLATFORM_ADMIN_QUERY` | IMPERSONATION |
| `*_CREATED`, `*_UPDATED`, `*_STATUS_CHANGED`, `*_DELETED`, `*_ACTIVATED`, `*_VOIDED`, etc. | STATE_TRANSITION |
| `ATTACHMENT_ACCESSED`, `REPORT_RUN`, `REPORT_EXPORT_*`, `AUDIT_SEARCHED` | DATA_ACCESS |
| `ORG_SETTINGS_UPDATED`, `ROLE_*`, `CAPABILITY_*`, `MEMBER_*`, `MEMBERSHIP_*` | ADMIN |
| `PRICING_*` | PRICING |
| `INVOICE_*`, `PAYMENT_*`, `INVOICING_POLICY_*`, `LINE_RELEASED_*`, `TAX_*`, `ACCOUNTING_*` | BILLING |
| `TENANT_EXPORT_*` | EXPORT |
| `TENANT_DELETION_*` | DELETION |
| `OUTBOX_DLQ_*` | ADMIN |

#### G.5.5 Masking and redaction rules

| Field pattern | Action |
| --- | --- |
| `password*`, `*_token`, `*_secret`, `csrf*`, `totp*`, `backup_codes*` | "[REDACTED]" |
| `accounting_adapter_config` | full value redacted |
| `notes`, `description`, `body`, `outcome_notes` (free-text > 1000 chars) | truncated to 1000 chars + "..." |
| `email`, `phone` | preserved |
| `payment.amount`, `invoice.total_amount`, `pricing.*` | preserved |
| `body_hash` | preserved |

#### G.5.6 Retention rules

| Category | Retention |
| --- | --- |
| AUTHENTICATION | 7 years |
| IMPERSONATION | 7 years |
| STATE_TRANSITION | 7 years |
| ADMIN | 7 years |
| PRICING | 7 years |
| BILLING | 7 years |
| EXPORT | 7 years |
| DELETION | 7 years (effectively forever during legal hold) |
| DATA_ACCESS | 1 year |
| AUTHORIZATION (denials, if logged) | 90 days |

Enforced by `audit.retention_prune` beat job via partition detach-then-drop.

#### G.5.7 Schema versioning

`AuditEvent.schema_version: INT, default(1)`. v1 ships at version 1. Major schema changes require version bump + migration helper.

#### G.5.8 Audit search and export

```python
def search_audit_events(
    *, organization_id, actor_id,
    filters: AuditSearchFilters,
    limit: int = 100, cursor: str | None = None,
) -> AuditSearchResult:
    """
    Required capability: admin.audit.view
    Search itself emits a DATA_ACCESS audit row.
    """
```

#### G.5.9 RBAC enforcement matrix

| Action | Capability | Audit |
| --- | --- | --- |
| Search audit (tenant scope) | `admin.audit.view` | `AUDIT_SEARCHED` |
| Search audit (cross-tenant, support) | platform `is_staff` | `PLATFORM_ADMIN_QUERY` |
| Export audit | `admin.audit.view` AND `reporting.export` | `AUDIT_EXPORTED` |

### G.6 Security Controls

**Status: NORMATIVE.**

#### G.6.1 Security posture

Security controls MUST protect tenant isolation, authentication, authorization, sensitive commercial data, file access, secrets, and operational credentials.

Security controls are mandatory in production and SHOULD be exercised in staging before every production release.

#### G.6.2 TLS and transport security

Production MUST serve all application traffic over HTTPS.

Requirements:

- HTTP MUST redirect to HTTPS.
- TLS MUST terminate at the reverse proxy or managed load balancer.
- TLS 1.2+ is REQUIRED.
- TLS 1.3 SHOULD be supported.
- HSTS MUST be enabled after certificate issuance and subdomain routing are verified.
- Secure cookies MUST be used in non-dev environments.
- `SESSION_COOKIE_SECURE=True` in non-dev.
- `CSRF_COOKIE_SECURE=True` in non-dev.

Kubernetes ingress is not required or assumed.

#### G.6.3 Security headers

The reverse proxy and/or Django middleware MUST set:

```text
Strict-Transport-Security
Content-Security-Policy
X-Content-Type-Options
Referrer-Policy
Permissions-Policy
X-Frame-Options or CSP frame-ancestors
```

CSP MUST be enforced in production. Development MAY use report-only mode.

#### G.6.4 Secrets management

Secrets MUST NOT be committed to source control.

Production secrets MUST be supplied through one of:

- host-local environment file with restricted permissions
- DigitalOcean-managed secret/environment configuration
- approved external secret manager
- deployment-time secret injection from a password manager or vault

The following are secrets:

- Django `SECRET_KEY`
- database credentials
- Redis credentials
- email provider credentials
- object-storage keys
- handoff signing key
- encryption keys
- OAuth/OIDC client secrets
- Sentry DSN if private
- third-party API tokens

`.env.example` MAY be committed. Real `.env` files MUST NOT be committed.

#### G.6.5 Secret rotation

| Secret | Rotation requirement |
| --- | --- |
| Handoff signing key | Quarterly |
| OAuth/OIDC client secrets | At least annually or on suspected compromise |
| Django `SECRET_KEY` | On suspected compromise; planned rotation runbook required |
| Database credentials | At least annually or on staff/vendor change |
| Object storage credentials | At least annually or on staff/vendor change |
| Email provider credentials | At least annually or on staff/vendor change |
| Field encryption key | Annually, with staged re-encryption runbook |

#### G.6.6 Password, OAuth/OIDC, and authentication controls

Password and OAuth/OIDC rules are defined in B.5.

Additional requirements:

- MFA is required at v1 launch.
- Support users MUST satisfy MFA on every login path.
- Sensitive actions MUST require re-authentication.
- Account lockout MUST be enforced for local password login.
- Authentication failures MUST emit audit events without leaking whether an email exists.
- OAuth/OIDC callbacks MUST validate state, nonce, issuer, audience, signature, and expiry where applicable.
- Provider tokens and authorization codes MUST NOT be logged.

#### G.6.7 Rate limiting

Rate limits MUST be enforced using Redis-backed counters.

Minimum limits:

| Endpoint | Limit |
| --- | --- |
| `POST /login` | 5 per IP per minute, 20 per IP per hour |
| `POST /login/2fa` | 5 per session per minute |
| `GET /accounts/oidc/*/login/` | 20 per IP per minute |
| OAuth/OIDC callback | 30 per IP per minute |
| `POST /forgot-password` | 3 per email per hour, 10 per IP per hour |
| `POST /reset-password` | 5 per IP per minute |
| `POST /accept-invite` | 10 per IP per hour |
| `POST /handoff` | 20 per IP per minute |
| quote PDF generation | tenant-configurable throttle |
| report export | tenant-configurable throttle |

#### G.6.8 File upload security

Uploaded files MUST be validated before persistence.

Requirements:

- Maximum size enforced before upload completes when possible.
- MIME type checked.
- File extension allowlist by document kind.
- Object key generated by application, never user-supplied.
- Original filename stored as metadata only.
- Malware scanning hook present.
- Infected files return 403 on download.
- Download URLs are short-lived and re-check permission on every request.

#### G.6.9 Admin and support security

Support impersonation MUST follow B.7.

Additional requirements:

- Support impersonation requires reason and sensitive-action re-auth.
- Support actions MUST be audited.
- Support users MAY NOT impersonate staff users.
- Support users MAY NOT silently cross tenants inside a single tenant-local session.
- The impersonation banner MUST be server-rendered.

#### G.6.10 Dependency and image security

CI MUST scan dependencies and container images.

Minimum requirements:

- CI fails on HIGH/CRITICAL dependency vulnerabilities unless an explicit temporary exception is documented.
- Docker image MUST run as non-root unless a documented exception is approved.
- Production image MUST not include development tooling unless required at runtime.
- Debug mode MUST be disabled in staging, demo, and production.
- Django `ALLOWED_HOSTS` MUST be explicit in non-dev environments.

#### G.6.11 Database security

Database credentials MUST be environment-specific.

Requirements:

- Production database user MUST have only required privileges.
- Direct public database access SHOULD be disabled.
- Backups MUST be encrypted at rest.
- Production-to-staging refresh MUST anonymize sensitive tenant and user data.
- pgBouncer MAY be used for pooling but MUST NOT weaken TLS or credential controls.

#### G.6.12 Container host security

Production container hosts MUST be hardened.

Minimum requirements:

- SSH restricted to authorized operators.
- Password SSH login disabled.
- Firewall allows only required ports.
- Docker daemon not exposed publicly.
- Host packages patched regularly.
- Logs retained according to operational policy.
- Production `.env` files readable only by the deployment user/root.

### G.7 Tenant Data Export and Deletion

**Status: NORMATIVE.**

#### G.7.1 Why this is in v1

Per the locked answer in batch 1, tenant data export and deletion are required at v1 launch. Drives: GDPR/CCPA-equivalent obligations + clean exit story for external first-tenant CRM.

#### G.7.2 Tenant data export

##### Service surface

```python
def request_tenant_export(
    *,
    organization_id: UUID,
    actor_id: UUID,
    requested_scope: ExportScope = ExportScope.FULL,
) -> TenantExportRequest:
    """ Required: admin.export.request; sensitive (re-auth) """

def cancel_tenant_export(...) -> TenantExportRequest: ...
def list_tenant_exports(...) -> list[TenantExportRequest]: ...
```

##### TenantExportRequest

See C.1.16.

##### Worker

`tenant.export.assemble`:

1. Sets status = ASSEMBLING.
2. Streams rows scoped to organization_id into a structured archive (JSON Lines per table, CSV mirrors for common tables).
3. Includes DocumentAttachment binaries.
4. AuditEvents within retention as a single JSONL file.
5. Archive layout:

   ```text
   {organization_slug}_{requested_at_yyyymmdd}/
     manifest.json
     organization.json
     memberships.jsonl
     leads.jsonl, leads.csv
     quotes.jsonl, quotes.csv
     quote_versions.jsonl
     quote_version_lines.jsonl
     pricing_snapshots.jsonl
     clients.jsonl, clients.csv
     sales_orders.jsonl, sales_orders.csv
     ... (one entry per table)
     audit_events.jsonl
     attachments/
       {document_kind}/{attachment_id}/{filename}
   ```

6. Archive is gzipped tar (`.tar.gz`).
7. Uploaded as DocumentAttachment with `document_kind=EXPORT_ARCHIVE`, `retention_until = now() + 14 days`.
8. Sets `output_attachment_id`, `status=READY`, `expires_at`.
9. Notifies the requester.
10. Emits `TENANT_EXPORT_ASSEMBLED` audit.

##### Download

Via standard `get_attachment_download_url`. Each download emits `TENANT_EXPORT_DOWNLOADED` (not sampled).

After 14 days, the attachment is hard-deleted; `TenantExportRequest.status = EXPIRED`.

#### G.7.3 Tenant deletion

Multi-stage workflow with 30-day grace period.

##### Tenant Service surface

```python
def request_tenant_deletion(
    *,
    organization_id: UUID,
    actor_id: UUID,
    confirmation_phrase: str,
) -> TenantDeletionRequest:
    """
    Required: admin.deletion.request; sensitive (re-auth)
    confirmation_phrase MUST equal organization's slug exactly.
    """

def cancel_tenant_deletion(...) -> TenantDeletionRequest:
    """ Required: admin.deletion.request; sensitive. State: GRACE_PERIOD """

def execute_tenant_deletion(*, deletion_request_id: UUID) -> TenantDeletionRequest:
    """ Beat-driven worker. Idempotent. """
```

##### TenantDeletionRequest

See C.1.16.

##### Lifecycle

1. **Request:** validates phrase. status = `GRACE_PERIOD`. `grace_period_ends_at = now + 30 days`. `Organization.status = OFFBOARDING`. Audits `TENANT_DELETION_REQUESTED` and `TENANT_DELETION_GRACE_STARTED`.

2. **Grace period (30 days):**
   - Tenant data is read-only.
   - Tenant admins MAY request data export.
   - Tenant admins MAY cancel the deletion.
   - Daily reminder email for first 7 days, then on day 25, 28, 29.

3. **Execute (day 30):** Beat job `tenant.deletion.execute_due` finds GRACE_PERIOD requests where `grace_period_ends_at < now`. Worker:
   - Status = EXECUTING.
   - Hard-deletes tenant-owned rows scoped to organization_id (in dependency order).
   - Deletes object-store objects for DocumentAttachments.
   - Preserved: Organization (status=DELETED), AuditEvent rows for this org, ImpersonationAuditLog rows.
   - Sets `executed_at`, status = EXECUTED, `rows_deleted_per_table`.
   - Emits `TENANT_DELETION_EXECUTED` audit.

4. **Post-deletion:** Future logins for users with only-this-org memberships fail with "no active access."

##### Concurrency and safety

- Multiple deletion requests for the same org → second idempotently returns existing GRACE_PERIOD row.
- Cancellation followed by re-request creates a new 30-day window.
- Execution worker uses `select_for_update` on Organization.

#### G.7.4 RBAC enforcement matrix

| Action | Capability | Audit |
| --- | --- | --- |
| Request tenant export | `admin.export.request`; sensitive | `TENANT_EXPORT_REQUESTED` |
| Cancel tenant export | `admin.export.request` | `TENANT_EXPORT_CANCELLED` |
| Download tenant export | (derived from EXPORT_ARCHIVE attachment) | `TENANT_EXPORT_DOWNLOADED` |
| Request tenant deletion | `admin.deletion.request`; sensitive | `TENANT_DELETION_REQUESTED` |
| Cancel tenant deletion | `admin.deletion.request`; sensitive | `TENANT_DELETION_CANCELLED` |

Platform-level operators (`is_superuser`) MAY also force-execute or force-cancel via the platform console.

---
---

## Part H — Frontend

### H.1 Phase 1 Frontend Architecture

**Status: NORMATIVE.**

#### H.1.1 Stack lock

| Layer | Choice |
| --- | --- |
| Server templating | Django templates (Jinja-style not used) |
| CSS framework | Tailwind CSS 4.x |
| Build/asset pipeline | django-vite |
| JS module system | ESM only |
| Interactivity (default) | HTMX 1.9+ |
| Client-only state (sparingly) | Alpine.js 3.x |
| Icon system | Heroicons (SVG sprites) |
| Date/time picker | Native `<input type="date">` / `datetime-local` (no JS picker library in v1) |
| Forms | Django forms + django-widget-tweaks for class injection |

No React, no Vue, no Svelte in Phase 1. The Phase 2 portal will introduce React; until then, every tenant-facing surface is server-rendered.

#### H.1.2 django-vite configuration

```python
# settings/base.py
DJANGO_VITE = {
    "default": {
        "dev_mode": DEBUG,
        "manifest_path": BASE_DIR / "frontend" / "dist" / "manifest.json",
        "static_url_prefix": "vite",
        "dev_server_protocol": "http",
        "dev_server_host": "localhost",
        "dev_server_port": 5173,
    }
}

STATICFILES_DIRS = [
    BASE_DIR / "frontend" / "dist",
    BASE_DIR / "frontend" / "src" / "static",
]
```

**Frontend layout:**

```text
frontend/
├── src/
│   ├── entries/
│   │   ├── tenant_portal.ts
│   │   ├── platform_console.ts
│   │   ├── login_landing.ts
│   │   └── email_template_preview.ts
│   ├── modules/
│   │   ├── htmx_init.ts
│   │   ├── csrf.ts
│   │   ├── alpine_components/
│   │   ├── form_helpers.ts
│   │   └── notifications.ts
│   ├── styles/
│   │   ├── tenant_portal.css
│   │   ├── platform_console.css
│   │   └── login_landing.css
│   └── static/
├── tailwind.config.cjs
├── vite.config.ts
└── package.json
```

Each `entries/*.ts` becomes a separately-built bundle. Cross-bundle dependencies are PROHIBITED.

#### H.1.3 Tailwind configuration baseline

```javascript
// tailwind.config.cjs
module.exports = {
  content: [
    "./apps/**/templates/**/*.html",
    "./frontend/src/**/*.{ts,js}",
  ],
  theme: {
    extend: {
      colors: { brand: {...}, surface: {...}, text: {...}, status: {...} },
      fontFamily: {
        sans: ['"Inter"', "system-ui", "sans-serif"],
        mono: ['"JetBrains Mono"', "ui-monospace", "monospace"],
      },
    },
  },
  plugins: [
    require("@tailwindcss/forms"),
    require("@tailwindcss/typography"),
    require("@tailwindcss/container-queries"),
  ],
}
```

**Arbitrary values are PROHIBITED in templates** (e.g., `class="text-[#3b82f6]"`). A CI lint rule flags `\[#[0-9a-fA-F]+\]`, `\[\d+px\]`, and similar patterns.

#### H.1.4 HTMX as global default

| Pattern | Implementation |
| --- | --- |
| Form submission with inline error rendering | `hx-post`, `hx-target`, server returns partial |
| List filtering | `hx-get` with `hx-include`, `hx-target="#results"` |
| Inline validation | `hx-post` to validation endpoint, `hx-target="closest .field"` |
| Modal/dialog open | `hx-get` returns modal HTML; `hx-target="body"`, `hx-swap="beforeend"` |
| Status banner refresh | `hx-trigger="every 30s"`, `hx-swap="outerHTML"` (sparingly) |
| Bulk action confirmation | `hx-confirm` for trivial cases; modal for non-trivial |

Standalone JS for interactivity is the exception. If a surface needs more JS than HTMX + Alpine can provide, that's a signal it should be deferred to Phase 2.

#### H.1.5 HTMX initialization

```typescript
// frontend/src/modules/htmx_init.ts
import "htmx.org";
import { setupCsrf } from "./csrf";
import { setupNotifications } from "./notifications";

export function initHtmx() {
  setupCsrf();
  setupNotifications();

  window.htmx.config.defaultSwapStyle = "innerHTML";
  window.htmx.config.includeIndicatorStyles = false;
  window.htmx.config.scrollIntoViewOnBoost = false;
  window.htmx.config.historyCacheSize = 0;        // tenant data must never be cached
  window.htmx.config.allowEval = false;
  window.htmx.config.allowScriptTags = false;

  document.body.addEventListener("htmx:responseError", (evt: any) => {
    if (evt.detail.xhr.status === 401) {
      window.location.href = "/login?next=" + encodeURIComponent(window.location.pathname);
    }
  });

  document.body.addEventListener("htmx:responseError", (evt: any) => {
    const errorCode = evt.detail.xhr.getResponseHeader("X-Error-Code");
    if (errorCode) {
      const msg = evt.detail.xhr.responseText || "Something went wrong.";
      window.dispatchEvent(new CustomEvent("mph:toast", {
        detail: { kind: "error", message: msg, errorCode }
      }));
    }
  });
}
```

#### H.1.6 CSRF integration

```typescript
export function setupCsrf() {
  const token = readCookie("csrftoken");
  if (!token) return;
  document.body.addEventListener("htmx:configRequest", (evt: any) => {
    if (["POST", "PUT", "PATCH", "DELETE"].includes(evt.detail.verb.toUpperCase())) {
      evt.detail.headers["X-CSRFToken"] = token;
    }
  });
}
```

#### H.1.7 Alpine.js scope of use

| Permitted | Prohibited |
| --- | --- |
| Modal open/close toggle | Form validation that bypasses server |
| Dropdown menu show/hide | Computed pricing or totals |
| Tab switcher | Optimistic data updates |
| Tooltip visibility | State that must be persisted |
| Show/hide password input | Multi-step wizards (use HTMX boost) |

Alpine state that must round-trip to the server is a misuse.

#### H.1.8 Progressive enhancement

Every form MUST work without JavaScript. Every `hx-post` URL on a form MUST return a full HTML page when called without HTMX headers, and a partial when called with `HX-Request: true`.

```python
def is_htmx_request(request) -> bool:
    return request.headers.get("HX-Request") == "true"
```

#### H.1.9 Decisions Embedded in This Section

- HTMX history cache disabled. Tenant data must never persist in browser history-state.
- Arbitrary Tailwind values prohibited. Without this rule, the design system rots within three sprints.
- Alpine.js scope rules enforceable in code review only; no static check provided.
- Cross-bundle dependencies prohibited. Shared code goes in `modules/`.

#### H.1.10 Open Questions Deferred to Later Sections

- Per-tenant theming / white-labeling: K.7.
- Mobile breakpoint behavior testing matrix: I.1.

---

### H.2 Component System and Design Tokens

**Status: NORMATIVE.**

#### H.2.1 Design tokens

Tokens defined ONCE in `tailwind.config.cjs`, accessed via Tailwind utility classes. No CSS custom properties. No alternate token sources.

```javascript
colors: {
  brand: {
    50:  "#eff6ff", 100: "#dbeafe", 200: "#bfdbfe", 300: "#93c5fd",
    400: "#60a5fa", 500: "#3b82f6", 600: "#2563eb", 700: "#1d4ed8",
    800: "#1e40af", 900: "#1e3a8a",
  },
  surface: {
    canvas: "#f8fafc", raised: "#ffffff", sunken: "#f1f5f9",
    border: "#e2e8f0", "border-strong": "#cbd5e1",
  },
  text: {
    primary: "#0f172a", secondary: "#475569",
    tertiary: "#94a3b8", inverse: "#ffffff",
  },
  status: {
    info: "#3b82f6", success: "#10b981", warning: "#f59e0b",
    danger: "#ef4444", neutral: "#64748b",
    "info-bg": "#eff6ff", "success-bg": "#ecfdf5",
    "warning-bg": "#fffbeb", "danger-bg": "#fef2f2", "neutral-bg": "#f1f5f9",
  },
  impersonation: {
    bg: "#fef3c7", border: "#f59e0b", text: "#78350f",
  },
}
```

**Status color usage:**

| Status | When |
| --- | --- |
| info | Neutral informational, in-progress |
| success | Completed, paid, accepted |
| warning | Pending action, overdue-soon, needs review |
| danger | Failed, voided, rejected, overdue |
| neutral | Drafts, archived, inactive |

#### H.2.2 Component partials registry

Reusable Django template partials live under `apps/web/templates/components/`. v1 registry:

| Partial | Purpose |
| --- | --- |
| `components/button.html` | Primary/secondary/danger/ghost/icon button variants |
| `components/badge.html` | Status badges |
| `components/card.html` | Generic card container |
| `components/empty_state.html` | Empty list illustration + message |
| `components/page_header.html` | Page title + breadcrumb + primary action |
| `components/section_header.html` | Section title + secondary action |
| `components/field.html` | Form field with label, input, error, helper |
| `components/field_error.html` | Inline field error |
| `components/form_actions.html` | Submit/cancel button row |
| `components/table.html` | Tabular list with header + body + empty state |
| `components/table_row_actions.html` | Per-row action menu |
| `components/pagination.html` | Cursor or offset pagination links |
| `components/filter_bar.html` | Filter inputs + apply/clear (HTMX-driven) |
| `components/modal.html` | Modal wrapper |
| `components/confirm_modal.html` | Confirm-with-reason modal |
| `components/toast_container.html` | Toast notification region |
| `components/breadcrumbs.html` | Breadcrumb trail |
| `components/tabs.html` | Tab strip |
| `components/dropdown_menu.html` | Action dropdown (Alpine-toggled) |
| `components/avatar.html` | User avatar with fallback initials |
| `components/key_value_list.html` | Definition-list-style display |
| `components/money.html` | Currency-formatted amount |
| `components/datetime.html` | Localized datetime with `<time>` element |
| `components/state_machine_badge.html` | Specialized state-aware status badge |
| `components/audit_event_row.html` | Single audit event display row |
| `components/sensitive_action_form.html` | Form wrapper that triggers re-auth gate |
| `components/impersonation_banner.html` | Server-rendered impersonation banner |
| `components/header_nav.html` | Top navigation bar |
| `components/sidebar_nav.html` | Side navigation with capability-aware visibility |
| `components/footer.html` | Page footer |

Partials MUST NOT include domain logic.

#### H.2.3 Capability-aware UI rendering

```python
# apps/web/templatetags/permissions.py
@register.simple_tag(takes_context=True)
def has_capability(context, code: str) -> bool:
    membership = context.get("active_membership")
    if not membership:
        return False
    return capability_check(membership, code)
```

**This is a UI-affordance check, NOT a security boundary.** Hiding a button does not authorize the underlying action; the view-layer `@require_capability` decorator is the enforcement point.

#### H.2.4 Form rendering convention

```django
{# components/field.html #}
{% load widget_tweaks %}
<div class="field {% if field.errors %}field--error{% endif %}">
  <label for="{{ field.id_for_label }}" class="text-label text-text-secondary">
    {{ field.label }}{% if field.field.required %}<span class="text-status-danger">*</span>{% endif %}
  </label>
  {{ field|add_class:"input input--default" }}
  {% if field.help_text %}
    <p class="text-sm text-text-tertiary mt-1">{{ field.help_text }}</p>
  {% endif %}
  {% if field.errors %}
    {% include "components/field_error.html" with errors=field.errors %}
  {% endif %}
</div>
```

Direct Tailwind class use on individual `<input>` elements is PROHIBITED.

#### H.2.5 Money and datetime formatting

```django
{# components/money.html #}
<span class="font-mono tabular-nums {% if color_negative and amount < 0 %}text-status-danger{% endif %}">
  {{ amount|currency:currency }}
</span>

{# components/datetime.html #}
<time datetime="{{ value|date:'c' }}" class="tabular-nums">
  {{ value|localize_to:tz|format_datetime:format }}
</time>
```

Datetime display always uses the organization's `timezone` field.

#### H.2.6 Decisions Embedded in This Section

- Component partials over Django form widgets.
- `has_capability` template tag is documented as UI-affordance, not security.
- Color tokens locked into the named palette; new statuses require guide PR.
- Datetime always rendered through `components/datetime.html` with org timezone.

#### H.2.7 Open Questions Deferred to Later Sections

- Component documentation surface (Storybook-equivalent): K.7.
- Per-tenant logo upload + favicon: K.7.
- Print stylesheets for invoice/quote PDF: H.4.

---

### H.3 Root-Domain Landing and Authentication Pages

**Status: NORMATIVE.**

#### H.3.1 Scope

The root-domain pages are the public entrypoint and authentication surface. They are server-rendered Django templates and MUST NOT migrate to React in Phase 2.

The root domain `/` is a custom landing page. It is not a redirect-only placeholder. The landing page introduces MyPipelineHero and routes all users toward `/login/`.

The attached `homepage.html`, `login.html`, `base.html`, `homepage.css`, and `dashboard.css` assets define the initial Phase 1 visual baseline. They should be committed into the paths defined in A.5 and H.8.

#### H.3.2 Route inventory

| Path | View | Purpose | Auth required |
| --- | --- | --- | --- |
| `GET /` | `LandingPageView` | Custom public landing page and entrypoint for all users | No |
| `GET /login/` | `LoginView` | Email/password form and OAuth/OIDC provider entrypoints | No |
| `POST /login/` | `LoginView` | Credential validation | No |
| `GET /login/2fa/` | `TwoFactorChallengeView` | TOTP challenge | Partially-authed session |
| `POST /login/2fa/` | `TwoFactorChallengeView` | TOTP validation | Partially-authed session |
| `GET /login/2fa/enroll/` | `TwoFactorEnrollmentView` | First-time enrollment | Authed but no TOTP |
| `POST /login/2fa/enroll/` | `TwoFactorEnrollmentView` | Confirms enrollment + backup codes | Authed but no TOTP |
| `GET /select-org/` | `OrgPickerView` | Multi-org membership selection | Authed (post-MFA) |
| `POST /select-org/` | `OrgPickerView` | Issues handoff token | Authed (post-MFA) |
| `GET /forgot-password/` | `ForgotPasswordView` | Email entry form | No |
| `POST /forgot-password/` | `ForgotPasswordView` | Sends reset email (no enumeration) | No |
| `GET /reset-password/` | `ResetPasswordView` | Token-validated set form | Token |
| `POST /reset-password/` | `ResetPasswordView` | Sets new password | Token |
| `GET /accept-invite/` | `AcceptInviteView` | Token-validated invite landing | Token |
| `POST /accept-invite/` | `AcceptInviteView` | Creates user (or links existing) and membership | Token |
| `GET /no-active-access/` | `NoActiveAccessView` | "Your memberships are inactive" page | Authed |
| `GET /logout/` | `LogoutView` | Destroys root-domain session | Authed |
| `GET /platform/` | `PlatformConsoleHomeView` | Custom platform admin site landing | `is_staff` |
| `GET /django-admin/` | Django default admin | Development-only raw model inspection | Dev-only staff/superuser |

`/django-admin/` is not a product surface. It MAY exist only for development and controlled non-production debugging. It MUST NOT be required for any v1 tenant, support, or platform workflow.

#### H.3.3 Landing page behavior

The landing page MUST:

1. Render at the root domain `/`.
2. Use the shared `base.html` and landing CSS from H.8.
3. Provide a clear sign-in path to `/login/`.
4. Avoid tenant-specific data.
5. Avoid requiring authentication.
6. Avoid requiring React or tenant-portal JavaScript.
7. Remain server-rendered in Phase 2.

The initial landing page content MAY include marketing-style feature, workflow, and plan sections. These sections are public content only and MUST NOT be treated as the source of truth for tenant subscription/pricing logic.

#### H.3.4 Login form behavior

1. **Bad credentials.** Generic error: "Email or password is invalid." NO enumeration.
2. **Account locked.** "This account has been temporarily locked. Please try again later or reset your password."
3. **Valid credentials, no TOTP enrolled.** Establish partially-authed session; redirect to `/login/2fa/enroll/`.
4. **Valid credentials, TOTP enrolled.** Establish partially-authed session; redirect to `/login/2fa/`.
5. **OAuth/OIDC provider selected.** Redirect to the provider authorization endpoint from the root domain only.

The "partially-authed session" expires after 5 minutes. All routes except `/login/2fa*` and `/logout/` reject requests with only a partially-authed session.

#### H.3.5 2FA challenge form

A 6-digit input with `inputmode="numeric"`, `autocomplete="one-time-code"`. Includes a "Use backup code instead" link that swaps to a longer single-line input.

#### H.3.6 2FA enrollment screen

1. Generates `User.totp_secret` (not yet persisted).
2. Renders QR code server-side plus the manual entry secret.
3. User scans/enters secret in their authenticator, returns a 6-digit code to confirm.
4. On confirmation: `User.totp_secret` and `totp_enrolled_at` saved; backup codes generated, hashed, displayed once with mandatory acknowledgment checkbox.

Refusing to acknowledge backup codes blocks completion.

#### H.3.7 Org picker

```text
┌─────────────────────────────────────────────┐
│  Select an organization                     │
├─────────────────────────────────────────────┤
│                                             │
│  ┌───────────────────────────────────────┐  │
│  │ Acme Manufacturing                    │  │  ← is_default highlighted
│  │     Owner · Last accessed 2h ago      │  │
│  └───────────────────────────────────────┘  │
│                                             │
│  ┌───────────────────────────────────────┐  │
│  │ Beta Industries                       │  │
│  │     Sales Staff · Last accessed 3d ago│  │
│  └───────────────────────────────────────┘  │
│                                             │
│  [Sign out]                                 │
└─────────────────────────────────────────────┘
```

Click → POST `/select-org/` → handoff token issued → 302 to subdomain.

For Support Users, an additional "Go to platform console" entry appears above the membership list.

#### H.3.8 Accept invite

1. Validate token: not expired, not consumed.
2. If email matches existing User: render "Sign in to accept" — user enters password or uses linked OAuth/OIDC flow, then routes through normal MFA.
3. If no User exists: render account-creation form with email pre-filled and read-only; user sets password or links approved OAuth/OIDC identity, accepts ToS, submits.

#### H.3.9 Decisions Embedded in This Section

- `/` is a custom public landing page.
- `/login/` is the root-domain authentication entrypoint.
- Root-domain auth pages remain server-rendered permanently.
- `/django-admin/` is dev-only raw model inspection, not the production admin surface.
- Public landing-page plan text is not the source of truth for internal pricing-engine behavior.

#### H.3.10 Open Questions Deferred to Later Sections

- Public marketing-site expansion beyond the landing page: K.7.
- Public contact-sales form: K.7.

### H.4 Tenant Portal Screens

**Status: NORMATIVE.**

#### H.4.1 Scope

Daily-driver UI for tenant users. Every interactive surface uses HTMX; every screen is server-rendered. Phase 2 will replace these with a React client over the DRF API.

#### H.4.2 Layout structure

```text
┌──────────────────────────────────────────────────────────────────────────┐
│  [components/impersonation_banner.html]   ← only when impersonating      │
├──────────────────────────────────────────────────────────────────────────┤
│  [components/header_nav.html]  Logo · Search · Tasks · Messages · Avatar │
├──────────┬───────────────────────────────────────────────────────────────┤
│          │                                                               │
│ Sidebar  │  [Page content]                                               │
│ (capa-   │                                                               │
│ bility-  │                                                               │
│ aware)   │                                                               │
│          │                                                               │
└──────────┴───────────────────────────────────────────────────────────────┘
```

#### H.4.3 Tenant portal route inventory

URL prefix is the tenant subdomain (`{slug}.mypipelinehero.com`).

##### Dashboard

| Path | View | Capability | Notes |
| --- | --- | --- | --- |
| `GET /` | `DashboardView` | (any active membership) | Counts + recent activity + my open tasks |

v1 dashboard intentionally minimal. Sections:

- **Counts:** Open Leads, Active Quotes, Open Sales Orders, Overdue Invoices, My Open Tasks.
- **Recent activity:** Last 10 audit events (STATE_TRANSITION + ADMIN events).
- **My open tasks:** Top 5 OPEN/IN_PROGRESS, sorted by due_at asc.

##### Leads

| Path | View | Capability |
| --- | --- | --- |
| `GET /leads/` | `LeadListView` | `leads.view` |
| `GET /leads/new` | `LeadCreateView` | `leads.create` |
| `POST /leads/` | `LeadCreateView` | `leads.create` |
| `GET /leads/{id}/` | `LeadDetailView` | `leads.view` |
| `GET /leads/{id}/edit` | `LeadEditView` | `leads.edit` |
| `POST /leads/{id}/edit` | `LeadEditView` | `leads.edit` |
| `POST /leads/{id}/qualify` | action | `leads.edit` |
| `POST /leads/{id}/disqualify` | action | `leads.edit` |
| `POST /leads/{id}/archive` | action | `leads.archive` |
| `POST /leads/{id}/assign` | action | `leads.assign` |
| `POST /leads/{id}/convert` | action | `leads.convert` + `quotes.create` |

##### Quotes

| Path | View | Capability |
| --- | --- | --- |
| `GET /quotes/` | `QuoteListView` | `quotes.view` |
| `GET /quotes/new` | `QuoteCreateView` | `quotes.create` |
| `POST /quotes/` | `QuoteCreateView` | `quotes.create` |
| `GET /quotes/{id}/` | `QuoteDetailView` | `quotes.view` |
| `GET /quotes/{id}/v/{version_number}/` | `QuoteVersionDetailView` | `quotes.view` |
| `GET /quotes/{id}/v/{version_number}/edit` | `QuoteVersionEditView` | `quotes.edit` |
| `POST /quotes/{id}/v/{version_number}/lines/` | action | `quotes.edit` |
| `PATCH /quotes/{id}/v/{version_number}/lines/{line_id}` | action | `quotes.edit` |
| `DELETE /quotes/{id}/v/{version_number}/lines/{line_id}` | action | `quotes.edit` |
| `POST /quotes/{id}/v/{version_number}/discount` | action | `quotes.line.apply_discount` |
| `POST /quotes/{id}/v/{version_number}/lines/{line_id}/override` | action | `quotes.line.override_price` |
| `POST /quotes/{id}/v/{version_number}/send` | action | `quotes.send` |
| `POST /quotes/{id}/v/{version_number}/accept` | action | `quotes.approve` |
| `POST /quotes/{id}/v/{version_number}/decline` | action | `quotes.decline` |
| `POST /quotes/{id}/v/{version_number}/retract` | action | `quotes.retract` |
| `POST /quotes/{id}/v/{version_number}/duplicate` | action | `quotes.create` |
| `GET /quotes/{id}/v/{version_number}/pdf` | `QuoteVersionPDFView` | `quotes.view` |

##### Clients

| Path | View | Capability |
| --- | --- | --- |
| `GET /clients/` | `ClientListView` | `clients.view` |
| `GET /clients/new` | `ClientCreateView` | `clients.create` |
| `POST /clients/` | `ClientCreateView` | `clients.create` |
| `GET /clients/{id}/` | `ClientDetailView` | `clients.view` |
| `GET /clients/{id}/edit` | `ClientEditView` | `clients.edit` |
| `POST /clients/{id}/edit` | `ClientEditView` | `clients.edit` |
| `POST /clients/{id}/deactivate` | action | `clients.deactivate` |
| `POST /clients/{id}/reactivate` | action | `clients.edit` |
| `POST /clients/{id}/contacts/` | action | `clients.contacts.manage` |
| `PATCH /clients/{id}/contacts/{contact_id}` | action | `clients.contacts.manage` |
| `DELETE /clients/{id}/contacts/{contact_id}` | action | `clients.contacts.manage` |
| `POST /clients/{id}/locations/` | action | `clients.locations.manage` |
| `PATCH /clients/{id}/locations/{location_id}` | action | `clients.locations.manage` |
| `DELETE /clients/{id}/locations/{location_id}` | action | `clients.locations.manage` |
| `POST /clients/{id}/merge` | `ClientMergeView` | `clients.merge` |

##### Sales Orders

| Path | View | Capability |
| --- | --- | --- |
| `GET /orders/` | `SalesOrderListView` | `orders.view` |
| `GET /orders/{id}/` | `SalesOrderDetailView` | `orders.view` |
| `POST /orders/{id}/cancel` | action | `orders.cancel` |
| `POST /orders/{id}/notes` | action | `orders.edit` |

##### Work Orders

| Path | View | Capability |
| --- | --- | --- |
| `GET /work-orders/` | `WorkOrderListView` | `workorders.view` |
| `GET /work-orders/mine` | `WorkOrderListView` (preset) | `workorders.view` |
| `GET /work-orders/{id}/` | `WorkOrderDetailView` | `workorders.view` |
| `POST /work-orders/{id}/assign` | action | `workorders.assign` |
| `POST /work-orders/{id}/start` | action | `workorders.update_status` |
| `POST /work-orders/{id}/hold` | action | `workorders.update_status` |
| `POST /work-orders/{id}/resume` | action | `workorders.update_status` |
| `POST /work-orders/{id}/complete` | `WorkOrderCompleteView` | `workorders.complete` |
| `POST /work-orders/{id}/cancel` | action | `workorders.manage` |
| `POST /work-orders/{id}/photos` | action | `workorders.update_status` |

##### Purchase Orders

| Path | View | Capability |
| --- | --- | --- |
| `GET /purchase-orders/` | `PurchaseOrderListView` | `purchasing.view` |
| `GET /purchase-orders/new` | `PurchaseOrderCreateView` | `purchasing.create` |
| `POST /purchase-orders/` | `PurchaseOrderCreateView` | `purchasing.create` |
| `GET /purchase-orders/{id}/` | `PurchaseOrderDetailView` | `purchasing.view` |
| `GET /purchase-orders/{id}/edit` | `PurchaseOrderEditView` | `purchasing.edit` |
| `POST /purchase-orders/{id}/lines/` | action | `purchasing.edit` |
| `POST /purchase-orders/{id}/allocations/` | action | `purchasing.edit` |
| `POST /purchase-orders/{id}/submit` | action | `purchasing.submit` |
| `POST /purchase-orders/{id}/acknowledge` | action | `purchasing.edit` |
| `POST /purchase-orders/{id}/receipts` | `PurchaseOrderReceiptView` | `purchasing.receive` |
| `POST /purchase-orders/{id}/cancel` | action | `purchasing.cancel` |

##### Build Orders

| Path | View | Capability |
| --- | --- | --- |
| `GET /build-orders/` | `BuildOrderListView` | `build.view` |
| `GET /build-orders/{id}/` | `BuildOrderDetailView` | `build.view` |
| `POST /build-orders/{id}/start` | action | `build.manage` |
| `POST /build-orders/{id}/hold` | action | `build.manage` |
| `POST /build-orders/{id}/resume` | action | `build.manage` |
| `POST /build-orders/{id}/submit-qa` | action | `build.manage` |
| `POST /build-orders/{id}/qa-approve` | action | `build.qa.review` |
| `POST /build-orders/{id}/qa-reject` | action | `build.qa.review` |
| `POST /build-orders/{id}/cancel` | action | `build.manage` |
| `POST /build-orders/{id}/labor` | action | `build.labor.record` |
| `POST /build-orders/{id}/labor/{entry_id}/adjust` | action | `build.labor.edit_any` |

##### Invoices

| Path | View | Capability |
| --- | --- | --- |
| `GET /invoices/` | `InvoiceListView` | `billing.view` |
| `GET /invoices/new` | `InvoiceCreateView` | `billing.invoice.create` |
| `POST /invoices/` | `InvoiceCreateView` | `billing.invoice.create` |
| `GET /invoices/{id}/` | `InvoiceDetailView` | `billing.view` |
| `GET /invoices/{id}/pdf` | `InvoicePDFView` | `billing.view` |
| `POST /invoices/{id}/send` | `InvoiceSendView` | `billing.invoice.send` |
| `POST /invoices/{id}/void` | action | `billing.invoice.void` |

##### Payments

| Path | View | Capability |
| --- | --- | --- |
| `GET /payments/` | `PaymentListView` | `billing.view` |
| `GET /payments/new` | `PaymentRecordView` | `billing.payment.record` |
| `POST /payments/` | `PaymentRecordView` | `billing.payment.record` |
| `GET /payments/{id}/` | `PaymentDetailView` | `billing.view` |
| `POST /payments/{id}/allocate` | action | `billing.payment.record` |
| `POST /payments/{id}/allocations/{alloc_id}/reverse` | action | `billing.payment.edit` |
| `POST /payments/{id}/adjust` | `PaymentAdjustmentView` | `billing.payment.edit` |

##### Tasks

| Path | View | Capability |
| --- | --- | --- |
| `GET /tasks/mine` | `TaskListView` (own) | `tasks.view` |
| `GET /tasks/team` | `TaskListView` (team) | `tasks.view` |
| `GET /tasks/{id}/` | `TaskDetailView` | `tasks.view` |
| `POST /tasks/` | `TaskCreateView` | `tasks.create` |
| `POST /tasks/{id}/start` | action | `tasks.edit` |
| `POST /tasks/{id}/block` | action | `tasks.edit` |
| `POST /tasks/{id}/resume` | action | `tasks.edit` |
| `POST /tasks/{id}/complete` | action | `tasks.complete` |
| `POST /tasks/{id}/cancel` | action | `tasks.manage` |
| `POST /tasks/{id}/reopen` | action | `tasks.manage` |

##### Communications

| Path | View | Capability |
| --- | --- | --- |
| `GET /communications/` | `CommunicationListView` | `communications.view` |
| `POST /communications/log` | `LogCommunicationView` | `communications.log` |
| `POST /communications/send` | `SendCommunicationView` | `communications.send` |
| `GET /communications/{id}/` | `CommunicationDetailView` | `communications.view` |

##### Catalog

| Path | View | Capability |
| --- | --- | --- |
| `GET /catalog/services/` | `ServiceListView` | `catalog.view` |
| `GET /catalog/services/{id}/` | `ServiceDetailView` | `catalog.view` |
| `GET /catalog/services/new` | `ServiceCreateView` | `catalog.services.manage` |
| `GET /catalog/products/` | `ProductListView` | `catalog.view` |
| `GET /catalog/products/{id}/` | `ProductDetailView` | `catalog.view` |
| `GET /catalog/products/{id}/bom/` | `BOMVersionListView` | `catalog.view` |
| `GET /catalog/products/{id}/bom/{version_id}/` | `BOMVersionDetailView` | `catalog.view` |
| `POST /catalog/products/{id}/bom/{version_id}/activate` | action | `catalog.bom.manage` |
| `GET /catalog/materials/` | `RawMaterialListView` | `catalog.view` |
| `GET /catalog/suppliers/` | `SupplierListView` | `catalog.view` |
| `GET /catalog/suppliers/{id}/` | `SupplierDetailView` | `catalog.view` |

##### Pricing configuration

| Path | View | Capability |
| --- | --- | --- |
| `GET /pricing/rules/` | `PricingRuleListView` | `pricing.rules.view` |
| `GET /pricing/rules/{id}/` | `PricingRuleDetailView` | `pricing.rules.view` |
| `GET /pricing/rules/new` | `PricingRuleCreateView` | `pricing.rules.manage` |
| `GET /pricing/price-lists/` | `PriceListIndexView` | `pricing.price_lists.manage` |
| `GET /pricing/contracts/` | `ClientContractListView` | `pricing.contracts.manage` |
| `GET /pricing/labor-rates/` | `LaborRateCardListView` | `pricing.labor_rates.manage` |
| `GET /pricing/segments/` | `CustomerSegmentListView` | `pricing.segments.manage` |
| `GET /pricing/promotions/` | `PromotionListView` | `pricing.promotions.manage` |
| `GET /pricing/bundles/` | `BundleListView` | `pricing.bundles.manage` |
| `GET /pricing/approvals/` | `PricingApprovalListView` | `pricing.approval.request` OR `.grant` |
| `GET /pricing/approvals/{id}/` | `PricingApprovalDetailView` | as above |
| `POST /pricing/approvals/{id}/approve` | action | `pricing.approval.grant` |
| `POST /pricing/approvals/{id}/reject` | action | `pricing.approval.grant` |
| `POST /pricing/approvals/{id}/withdraw` | action | `pricing.approval.request` (own) |

##### Reports

| Path | View | Capability |
| --- | --- | --- |
| `GET /reports/` | `ReportIndexView` | (any reporting cap) |
| `GET /reports/{report_code}/` | `ReportRunView` | per-report cap |
| `POST /reports/{report_code}/export` | action | per cap + `reporting.export` |
| `GET /reports/exports/` | `ReportExportListView` | `reporting.export` |
| `GET /reports/exports/{id}/` | `ReportExportDetailView` | `reporting.export` |

##### Tenant administration

| Path | View | Capability |
| --- | --- | --- |
| `GET /admin/` | `TenantAdminHome` | (any admin.* cap) |
| `GET /admin/members/` | `MemberListView` | `admin.members.view` |
| `GET /admin/members/{id}/` | `MemberDetailView` | `admin.members.view` |
| `POST /admin/members/invite` | `InviteMemberView` | `admin.members.invite` |
| `POST /admin/members/{id}/deactivate` | action | `admin.members.deactivate` |
| `POST /admin/members/{id}/suspend` | action | `admin.members.suspend` |
| `POST /admin/members/{id}/roles` | action | `admin.roles.assign` |
| `POST /admin/members/{id}/scope` | action | `admin.roles.assign` |
| `POST /admin/members/{id}/grants` | action | `admin.capabilities.grant` |
| `GET /admin/roles/` | `RoleListView` | `admin.roles.view` |
| `GET /admin/roles/new` | `RoleCreateView` | `admin.roles.manage` |
| `GET /admin/roles/{id}/edit` | `RoleEditView` | `admin.roles.manage` |
| `GET /admin/regions/` | `RegionListView` | `admin.org.settings` |
| `GET /admin/markets/` | `MarketListView` | `admin.org.settings` |
| `GET /admin/locations/` | `LocationListView` | `admin.org.settings` |
| `GET /admin/numbering/` | `NumberingConfigView` | `admin.numbering.configure` |
| `GET /admin/invoicing-policy/` | `InvoicingPolicyView` | `admin.org.settings` |
| `GET /admin/tax/jurisdictions/` | `TaxJurisdictionListView` | `tax.jurisdictions.manage` |
| `GET /admin/tax/rates/` | `TaxRateListView` | `tax.jurisdictions.manage` |
| `GET /admin/audit/` | `AuditSearchView` | `admin.audit.view` |
| `GET /admin/exports/` | `TenantExportListView` | `admin.export.request` |
| `POST /admin/exports/request` | action | `admin.export.request` |
| `GET /admin/danger-zone/` | `DangerZoneView` | `admin.deletion.request` |
| `POST /admin/danger-zone/delete` | `RequestDeletionView` | `admin.deletion.request` |
| `GET /admin/org/settings` | `OrgSettingsView` | `admin.org.settings` |

##### Account

| Path | View | Capability |
| --- | --- | --- |
| `GET /account/` | `MyAccountView` | (any) |
| `POST /account/password` | action | (any) |
| `POST /account/2fa/regenerate-codes` | action | (any) |
| `POST /logout` | `TenantLogoutView` | (any) |

#### H.4.4 List view conventions

Every list view supports:

- **Filter bar** (HTMX-driven).
- **Pagination** — offset-based for v1 (cursor for Phase 2 API). 25 rows default.
- **Sort** — column-header click; default `created_at DESC`.
- **Empty state** — `components/empty_state.html`.
- **Bulk actions** — NOT in v1.

#### H.4.5 Detail view conventions

```text
[page_header: title, breadcrumbs, primary action]
[components/state_machine_badge: current status]
[tab strip: per-domain tabs]
[main panel: content]
[side panel (optional): metadata, audit summary, related links]
```

Tabs are server-rendered; switching tabs is a full navigation in Phase 1 (HTMX-boost adds the partial-update).

#### H.4.6 Form patterns

##### Sensitive-action gate

Forms posting to sensitive endpoints use `components/sensitive_action_form.html`. If `last_sensitive_auth_at` is too old, submission is intercepted; user redirected to `/account/reauth?next={original_url}`. TOTP-only challenge; never re-prompts password.

##### Confirm-with-reason

Cancellation actions use `components/confirm_modal.html`. Modal opens via HTMX `hx-get`; submission posts to action endpoint.

#### H.4.7 Notifications and toasts

Toasts emitted by server, rendered by client. Mechanism: response carries `HX-Trigger: {"mph:toast": {"kind": "success", "message": "Quote sent"}}` header.

Toast kinds: `success`, `info`, `warning`, `error`. Auto-dismiss after 5s for non-error; error toasts require manual dismissal.

#### H.4.8 Decisions Embedded in This Section

- Dashboard scope intentionally minimal in v1; KPI dashboards deferred (K.8).
- Bulk actions deferred. Per-row actions only in v1.
- Cursor pagination ONLY in Phase 2 API; Phase 1 offset-based.
- Toasts via `HX-Trigger` header rather than embedded markup.
- Tab strip server-rendered with `hx-boost` rather than SPA-like switching.
- Re-auth flow uses TOTP-only — never re-prompts password.

#### H.4.9 Open Questions Deferred to Later Sections

- Saved views / list filters per user: K.7.
- Dashboard customization per role: K.7.
- Inline help / tour mode: K.7.
- Print-optimized stylesheets: K.7.

---

### H.5 Phase 2 React Tenant Portal (Forward-Looking)

**Status: NORMATIVE for the contract; INFORMATIVE for tooling specifics.**

#### H.5.1 What Phase 2 IS

Phase 2 replaces the tenant-facing workflow screens from H.4 domain-by-domain with a custom-built React client, consuming the DRF API (H.6). Login, organization picker, platform console, custom tenant admin where retained, support tooling, email templates, and error pages remain server-rendered. Phase 1 domain templates are the parity reference for React replacement.

#### H.5.2 What Phase 2 is NOT

- Not a separate domain.
- Not multi-tenant by URL (tenant context comes from cookie-bound session).
- Not a public API consumer (DRF API is internal-first-party only).
- Not a Single Page everything.
- Not a different domain model.

#### H.5.3 NORMATIVE contract

1. **Cookie-bound auth** via tenant-local Django session cookie. No bearer tokens. No localStorage tokens.
2. **CSRF.** Mutating API requests MUST include `X-CSRFToken` header from cookie.
3. **Error envelope.** Errors conform to G.2's domain-error JSON shape.
4. **Capability-aware UI.** Capabilities loaded once per session via `GET /api/v1/me/capabilities` and cached client-side. Hide-not-block.
5. **Pagination.** Cursor-based. Client receives `next`/`prev` cursor tokens.
6. **Optimistic UI.** Permitted only on idempotent UI affordances. Domain mutations MUST wait for server confirmation.
7. **Session expiry handling.** 401 from API triggers redirect to `/login?next={path}` on root domain.
8. **Impersonation banner.** When API responds with `X-Impersonating: true`, React MUST render same banner as Phase 1.
9. **Feature parity.** Every Phase 1 surface in H.4.3 has Phase 2 equivalent before Phase 1 retirement.
10. **Same handoff.** Entry into React app is via existing root-domain login + handoff flow.

#### H.5.4 Deferred toolchain decisions

| Decision | Notes |
| --- | --- |
| Build tool | Vite (likely), Next.js SPA mode, Remix |
| Routing | React Router, TanStack Router, framework-bundled |
| Data fetching / caching | TanStack Query (likely), SWR |
| State management | Context + reducers, Zustand |
| Component library | Headless UI + custom, Radix + custom |
| CSS strategy | Must preserve H.8 MyPipelineHero tokens/classes; Tailwind or CSS Modules may be used if they maintain visual parity |
| Bundle deployment | CDN-served vs. served by Django |
| TypeScript | Locked: yes |
| Testing | Locked: Vitest + Playwright |

#### H.5.5 Phase 1 → Phase 2 cutover strategy

**Per-domain cutover, not big-bang.** Feature flag `react_portal.{domain}` per domain. Phase 1 templates retired only when:

- React parity confirmed via parity test suite.
- Phase 2 surface live in production for 30 days without elevated error rates.
- Visual parity with the H.8 design system confirmed for the domain.
- Guide PR records the retirement.

#### H.5.6 Decisions Embedded in This Section

- Per-domain cutover, not big-bang. Reduces blast radius.
- Capabilities cached for the session, not refreshed per request.
- Cookie-bound auth, no token storage.
- TypeScript and Vitest + Playwright locked now.

#### H.5.7 Open Questions Deferred to Later Sections

- React framework selection: Phase 2 design sprint (K.11.1).
- Bundle deployment topology: Phase 2 design sprint.
- React-side design token sharing with Tailwind config: Phase 2 design sprint.

---

### H.6 Internal API (DRF, Phase 2 Prerequisite)

**Status: NORMATIVE.**

#### H.6.1 Scope

Internal contract between Phase 2 React client and service layer. NOT a public API. Built late in Phase 1 (M9).

### H.6.2 URL versioning

```text
/api/v1/...
```

URL-based versioning. New majors (`/api/v2/`) created when breaking changes are unavoidable.

#### H.6.3 Authentication

```python
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "apps.api.permissions.IsAuthenticatedActiveMembership",
    ],
    "DEFAULT_PAGINATION_CLASS": "apps.api.pagination.CursorPagination",
    "PAGE_SIZE": 25,
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
    "DEFAULT_PARSER_CLASSES": ["rest_framework.parsers.JSONParser"],
    "EXCEPTION_HANDLER": "apps.api.exception_handler.domain_exception_handler",
    "DEFAULT_THROTTLE_CLASSES": [
        "apps.api.throttling.UserRateThrottle",
        "apps.api.throttling.UserMutationRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "user.read": "600/minute",
        "user.mutation": "60/minute",
    },
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
}
```

`SessionAuthentication` reads the tenant-local Django session cookie. No alternate auth in v1.

#### H.6.4 Tenant resolution and permission

```python
class IsAuthenticatedActiveMembership(BasePermission):
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        if not getattr(request, "tenant_organization", None):
            return False
        membership = get_active_membership(
            user_id=request.user.id,
            organization_id=request.tenant_organization.id,
        )
        if not membership:
            return False
        request.active_membership = membership
        return True


class CapabilityRequiredMixin:
    required_capability: str | None = None
    capability_per_action: dict[str, str] | None = None

    def check_permissions(self, request):
        super().check_permissions(request)
        cap = self._resolve_capability(request)
        if cap and not has_capability(request.active_membership, cap):
            raise CapabilityRequiredError(cap)

    def _resolve_capability(self, request) -> str | None:
        if self.capability_per_action:
            return self.capability_per_action.get(self.action, self.required_capability)
        return self.required_capability


class TenantScopedQuerysetMixin:
    def get_queryset(self):
        return self.model.objects.for_membership(self.request.active_membership)
```

#### H.6.5 Viewset shape

```python
class QuoteVersionViewSet(
    TenantScopedQuerysetMixin,
    CapabilityRequiredMixin,
    mixins.RetrieveModelMixin,
    mixins.ListModelMixin,
    viewsets.GenericViewSet,
):
    model = QuoteVersion
    serializer_class = QuoteVersionSerializer
    detail_serializer_class = QuoteVersionDetailSerializer
    permission_classes = [IsAuthenticatedActiveMembership]
    capability_per_action = {
        "list": "quotes.view",
        "retrieve": "quotes.view",
        "send": "quotes.send",
        "accept": "quotes.approve",
        "decline": "quotes.decline",
        "retract": "quotes.retract",
    }

    @action(detail=True, methods=["post"], url_path="send")
    def send(self, request, pk=None):
        quote_version = self.get_object()
        result = services.send_quote(
            organization_id=request.active_membership.organization_id,
            actor_id=request.active_membership.user_id,
            quote_version_id=quote_version.id,
            recipient_emails=request.data.get("recipient_emails", []),
            cover_message=request.data.get("cover_message"),
            expected_optimistic_version=request.data.get("expected_optimistic_version"),
        )
        return Response(QuoteVersionSerializer(result).data)

    @action(detail=True, methods=["post"], url_path="accept")
    def accept(self, request, pk=None):
        quote_version = self.get_object()
        input_serializer = QuoteAcceptInputSerializer(data=request.data)
        input_serializer.is_valid(raise_exception=True)
        result = services.accept_quote(
            organization_id=request.active_membership.organization_id,
            actor_id=request.active_membership.user_id,
            quote_version_id=quote_version.id,
            client_resolution=input_serializer.validated_data["client_resolution"],
            idempotency_key=request.headers.get("Idempotency-Key"),
        )
        return Response(QuoteAcceptanceResultSerializer(result).data, status=201)
```

Views pull data from the request, call services, serialize the result.

#### H.6.6 Pagination

```python
class CursorPagination(rest_framework.pagination.CursorPagination):
    page_size = 25
    max_page_size = 100
    ordering = "-created_at"
    cursor_query_param = "cursor"
    page_size_query_param = "page_size"
```

Response shape:

```json
{
  "results": [...],
  "next": "https://acme.mypipelinehero.com/api/v1/quotes/?cursor=cD0yMDI2LTAxLTE1KzEwOjAwOjAw",
  "previous": null
}
```

For known-small list endpoints, `OffsetPagination` (default 100, max 500).

#### H.6.7 Error envelope

Per G.2.4:

```json
{
  "error_code": "concurrency_conflict",
  "message": "Someone else updated this quote. Reload and try again.",
  "details": {
    "entity_kind": "QuoteVersion",
    "entity_id": "01892f7e-...",
    "expected_version": 3,
    "actual_version": 4
  }
}
```

`X-Error-Code` response header carries the same `error_code`.

#### H.6.8 Idempotency keys

Mutating endpoints that create commercial state SHOULD support `Idempotency-Key` header (24-hour TTL). Endpoints supporting idempotency keys are documented in OpenAPI via custom extension.

#### H.6.9 OpenAPI / drf-spectacular

```python
SPECTACULAR_SETTINGS = {
    "TITLE": "MyPipelineHero Internal API",
    "DESCRIPTION": "Internal API consumed by the MyPipelineHero React tenant portal.",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "COMPONENT_SPLIT_REQUEST": True,
    "POSTPROCESSING_HOOKS": [
        "apps.api.openapi.add_error_envelope_components",
        "apps.api.openapi.annotate_idempotent_endpoints",
    ],
    "ENUM_NAME_OVERRIDES": {
        "QuoteVersionStatusEnum": "apps.quotes.models.QuoteVersionStatus",
        "WorkOrderStatusEnum": "apps.workorders.models.WorkOrderStatus",
    },
    "AUTHENTICATION_WHITELIST": [
        "rest_framework.authentication.SessionAuthentication",
    ],
}
```

Schema published at `/api/v1/schema/`. Generated schema is committed (`apps/api/schema/openapi.json`) and CI fails if committed schema drifts from runtime.

#### H.6.10 Throttling

| Throttle scope | Limit |
| --- | --- |
| `user.read` (GET) | 600/minute |
| `user.mutation` (POST/PUT/PATCH/DELETE) | 60/minute |

#### H.6.11 Required v1 endpoints

| Resource | Endpoints |
| --- | --- |
| `me` | `GET /me`, `GET /me/capabilities` |
| `leads` | full CRUD + actions (`qualify`, `disqualify`, `archive`, `assign`, `convert`) |
| `quotes` | full CRUD + actions (`send`, `accept`, `decline`, `retract`, `duplicate`) |
| `quotes/{id}/versions/{n}/lines` | line CRUD |
| `quotes/{id}/versions/{n}/discount` | quote-level discount |
| `clients` | full CRUD + actions (`deactivate`, `reactivate`, `merge`) |
| `clients/{id}/contacts` | nested CRUD |
| `clients/{id}/locations` | nested CRUD |
| `sales-orders` | read + actions (`cancel`) |
| `work-orders` | read + actions (`assign`, `start`, `hold`, `resume`, `complete`, `cancel`) |
| `purchase-orders` | full CRUD + actions (`submit`, `acknowledge`, `cancel`, `receipts`) |
| `build-orders` | read + actions (`start`, `hold`, `resume`, `submit-qa`, `qa-approve`, `qa-reject`, `cancel`, `labor`) |
| `invoices` | CRUD-lite + actions (`send`, `void`, `pdf`) |
| `payments` | CRUD-lite + actions (`allocate`, `reverse-allocation`, `adjust`) |
| `tasks` | full CRUD + actions |
| `communications` | log/send/list/retrieve |
| `attachments` | upload/download/delete |
| `catalog/services` | full CRUD |
| `catalog/products` | full CRUD |
| `catalog/products/{id}/bom/versions` | full CRUD + `activate` |
| `catalog/materials` | full CRUD |
| `catalog/suppliers` | full CRUD |
| `catalog/supplier-products` | full CRUD |
| `pricing/rules` | full CRUD |
| `pricing/price-lists` | full CRUD |
| `pricing/contracts` | full CRUD |
| `pricing/labor-rates` | full CRUD |
| `pricing/segments` | full CRUD |
| `pricing/promotions` | full CRUD |
| `pricing/bundles` | full CRUD |
| `pricing/approvals` | read + actions (`approve`, `reject`, `withdraw`) |
| `tax/jurisdictions` | full CRUD |
| `tax/rates` | CRUD + `supersede` |
| `reports/{report_code}` | run + queue export |
| `reports/exports` | list + retrieve |
| `admin/members` | full CRUD + actions |
| `admin/roles` | full CRUD |
| `admin/regions` | full CRUD |
| `admin/markets` | full CRUD |
| `admin/locations` | full CRUD |
| `admin/numbering-config` | retrieve + update |
| `admin/invoicing-policy` | retrieve + update |
| `admin/audit/events` | search |
| `admin/exports` | list + create + retrieve |
| `admin/deletion-request` | retrieve + create + cancel |

#### H.6.12 What the API is NOT

- Not a hypermedia API (no HATEOAS).
- Not GraphQL.
- Not webhook-emitting (in v1).
- Not bidirectional (no streaming / SSE / WebSockets in v1).
- Not exposed beyond first-party tenant subdomains.
- Not authenticated via tokens — cookie-only.

#### H.6.13 Decisions Embedded in This Section

- URL versioning, not header versioning.
- drf-spectacular over drf-yasg or hand-written.
- Cursor pagination as default; offset for known-small endpoints.
- `Idempotency-Key` is OPTIONAL but supported on commercial mutations.
- Generated OpenAPI schema is committed and CI-validated.
- API is internal-only; public-API exposure requires architectural review (deferred to K.11).

#### H.6.14 Open Questions Deferred to Later Sections

- Webhook emitters: K.11.
- Public/external API: K.11.
- TypeScript SDK generation from OpenAPI: K.11.
- Schema diff / breaking-change CI gate: K.11.

---

### H.7 Custom Admin Sites and Development Inspection

**Status: NORMATIVE.**

#### H.7.1 Admin posture

MyPipelineHero uses custom admin sites for production administration and Phase 1 workflow testing.

There are three distinct admin/development surfaces:

| Surface | Audience | Purpose | Production posture |
| --- | --- | --- | --- |
| Custom platform admin site | Internal support/platform staff | Cross-tenant support, tenant search, impersonation, operational support, audit review | Enabled |
| Custom tenant admin site | Tenant owners/admins | Organization settings, members, roles, billing settings, pricing configuration, catalog administration | Enabled |
| Base Django admin | Developers/staff in dev or tightly controlled non-production | Raw model inspection, migration sanity checks, quick framework debugging | Disabled or highly restricted |

The custom platform admin and custom tenant admin are product surfaces. The base Django admin is not a product surface.

#### H.7.2 URL posture

Recommended URLs:

```text
/                         # custom public landing page on root domain
/platform/                 # custom platform admin site on root domain
/admin/                    # custom tenant admin site within tenant subdomain
/django-admin/             # base Django admin; development-only raw model inspection
```

`/admin/` in production refers to the custom tenant admin site, not Django’s default model registry.

`/django-admin/` MUST be disabled in production unless an explicit emergency-support exception is approved, IP-restricted, staff-superuser restricted, and audited. No tenant workflow may depend on `/django-admin/`.

#### H.7.3 Phase 1 development method

During Phase 1, engineers use the custom admin surfaces to exercise the framework before the full tenant UX is complete.

The custom admin/testing workflow MUST allow engineers and authorized staff to:

1. Create and inspect tenants.
2. Create users and memberships.
3. Assign roles and capabilities.
4. Configure RML scope.
5. Configure catalog, pricing, suppliers, BOMs, and billing policies.
6. Trigger service-layer workflows through custom admin actions.
7. Inspect AuditEvents, OutboxEntry rows, dead letters, and background-job status.
8. Validate tenant isolation and RBAC behavior.
9. Enter a tenant context and view the tenant portal as a tenant user would.

The base Django admin MAY supplement this during development for raw model/table inspection, but it MUST NOT replace custom admin workflows and MUST NOT bypass required service-layer workflows for state-changing product behavior.

#### H.7.4 Tenant-view testing requirement

Phase 1 MUST support testing both perspectives:

| Perspective | Surface |
| --- | --- |
| Platform/support user | Root-domain `/platform/` custom platform admin |
| Tenant admin | Tenant subdomain `/admin/` custom tenant admin |
| Tenant user | Tenant subdomain tenant portal pages |
| Developer raw model inspection | Dev-only `/django-admin/` |

A developer must be able to sign in, select or impersonate a tenant, and see pages as a tenant user sees them. This is required even before Phase 2 React work begins.

#### H.7.5 Domain organization

Admin navigation MUST be organized by product/domain, not by Django app registry or alphabetical model name.

Recommended platform admin sections:

```text
Platform
  - Tenants
  - Users
  - Support Impersonation
  - Audit Events
  - System Jobs
  - Dead Letters
  - OAuth/OIDC Providers
  - Security Events
```

Recommended tenant admin sections:

```text
Organization
  - Organization Profile
  - Locations
  - Members
  - Roles and Permissions
  - Numbering
  - Invoicing Policy

CRM
  - Leads
  - Clients
  - Quotes
  - Sales Orders
  - Tasks
  - Communications

Catalog
  - Services
  - Products
  - Materials
  - Suppliers
  - BOMs
  - Pricing Rules
  - Price Lists
  - Contracts
  - Labor Rate Cards
  - Promotions
  - Bundles

Operations
  - Work Orders
  - Purchase Orders
  - Build Orders

Billing
  - Invoices
  - Payments

Reporting
  - Reports
  - Exports

Security and Audit
  - Audit Events
  - Data Export
  - Deletion Requests
```

#### H.7.6 Admin implementation requirements

Custom admin views MUST:

1. Use class-based or function-based Django views, not Django’s default `ModelAdmin` as the primary implementation.
2. Call service-layer functions for state changes.
3. Use capability checks for every view/action.
4. Use tenant-aware querysets for tenant admin.
5. Use explicit platform-query services for platform admin.
6. Emit AuditEvents for all state-changing or sensitive actions.
7. Use explicit domain navigation metadata.
8. Avoid exposing raw model CRUD where workflow rules exist.
9. Avoid alphabetical model registry navigation.
10. Avoid bypassing state machines.
11. Use the shared templates and styling rules from H.8.

#### H.7.7 Domain admin registry

Each domain app SHOULD expose admin navigation metadata from a local module.

Example:

```python
# apps/crm/quotes/admin_nav.py

QUOTE_ADMIN_SECTION = {
    "section": "CRM",
    "label": "Quotes",
    "items": [
        {
            "label": "Quotes",
            "url_name": "tenant_admin:quotes:list",
            "capability": "quotes.view",
        },
        {
            "label": "Pricing Approvals",
            "url_name": "tenant_admin:pricing_approvals:list",
            "capability": "pricing.approval.request",
        },
    ],
}
```

The custom admin shell imports or discovers these definitions explicitly. It MUST NOT depend on Django admin’s alphabetical model registry.

#### H.7.8 Model ownership

Each domain owns its own models, forms, services, tenant-facing views, admin views, URLs, templates, and tests.

Example:

```text
apps/crm/quotes/
  models.py
  services/
  forms.py
  views/
  urls.py
  admin_views/
  admin_nav.py
  tests/
```

Cross-domain admin screens may exist, but they must compose domain services rather than moving model ownership into a generic admin app.

#### H.7.9 Production restrictions

In staging, demo, and production:

- The base Django admin MUST be disabled, or
- It MUST be mounted only at `/django-admin/`, staff-superuser restricted, IP-restricted where possible, and excluded from tenant workflows.

No tenant workflow may depend on base Django admin.

#### H.7.10 Decisions Embedded in This Section

- Custom admin sites are product surfaces.
- Base Django admin is a development inspection tool only.
- Phase 1 custom admin sites are used to test the framework and domain workflows while tenant-facing templates are built.
- Tenant-facing views remain required so engineers can experience the app as a tenant user.

### H.8 Design Assets and Phase 2 Style Parity

**Status: NORMATIVE.**

#### H.8.1 Source assets

The initial visual system is defined by the attached Phase 1 assets:

| Asset | Target path | Purpose |
| --- | --- | --- |
| `base.html` | `backend/templates/base.html` | Shared base template with static CSS includes, impersonation banner include, messages, and content blocks |
| `homepage.html` | `backend/templates/landing/homepage.html` | Root-domain public landing page |
| `login.html` | `backend/templates/auth_portal/login.html` | Root-domain login page |
| `homepage.css` | `backend/static/landing/css/homepage.css` | Public landing, auth-page, shared tokens, and topbar styles |
| `dashboard.css` | `backend/static/landing/css/dashboard.css` | Temporary tenant dashboard and lightweight app-page styles |

These files define the initial MyPipelineHero brand language. They are not throwaway mockups.

#### H.8.2 Base template requirements

The base template MUST provide:

1. `{% load static %}`.
2. A configurable `{% block title %}`.
3. A configurable `{% block body_class %}`.
4. Static CSS includes for the shared landing/dashboard styles.
5. `{% block extra_css %}` and `{% block extra_js %}` extension points.
6. Server-rendered impersonation banner include.
7. Server-rendered Django messages.
8. `{% block content %}` for page content.

Production SHOULD NOT depend on browser-CDN Tailwind. The current attached base template may use the Tailwind browser CDN during early scaffolding, but M0/M1 should move toward compiled static assets through the project frontend pipeline.

#### H.8.3 Design tokens

The CSS custom properties under `:root` are the source of truth for the initial brand palette, shell colors, surface colors, border colors, radius scale, focus ring, and typography stack.

Phase 1 templates and Phase 2 React components MUST preserve these token names or provide a documented compatibility mapping.

Important token groups:

```text
--mph-primary
--mph-primary-dark
--mph-primary-soft
--mph-shell
--mph-surface
--mph-border
--mph-text
--mph-muted
--mph-landing-bg
--mph-landing-panel
--mph-landing-copy
--mph-radius-xl
--mph-radius-2xl
--mph-radius-3xl
--mph-focus-ring
--mph-font-sans
```

#### H.8.4 Class naming convention

Shared CSS classes use the `mph-` prefix. Domain templates SHOULD use `mph-` classes for shared layout and component primitives and domain-specific suffixes where needed.

Examples:

```text
mph-page
mph-header
mph-brand
mph-button
mph-auth-page
mph-auth-card
mph-dashboard-shell
mph-topbar
```

Phase 2 React components MUST either reuse these classes or map React component styles to equivalent tokens and visual behavior.

#### H.8.5 Landing and login pages

The landing page and login page are root-domain pages. They MUST remain server-rendered. They MUST use the shared public-body styling posture:

```text
body class: mph-public-body
login body class: mph-public-body mph-auth-body
```

The landing page sign-in links MUST target `/login/`.

#### H.8.6 Tenant dashboard placeholder

The dashboard CSS is the baseline for early tenant-portal pages and lightweight app pages. It MAY be replaced by richer domain-specific templates, but replacements MUST preserve the shared token language and accessibility posture.

#### H.8.7 Phase 2 React style parity

Phase 2 React MUST not introduce an unrelated visual language. React pages must preserve:

1. brand colors,
2. typography posture,
3. radius scale,
4. focus states,
5. button hierarchy,
6. public/auth-page visual language,
7. app-shell/topbar visual language,
8. impersonation banner prominence.

A Phase 2 domain cannot retire its Phase 1 template until both functional parity and visual/design parity are accepted.

#### H.8.8 Decisions Embedded in This Section

- Attached CSS/templates are the initial design baseline.
- Phase 2 React inherits the same visual language.
- Root-domain landing and auth pages stay Django-rendered.
- Domain templates are a parity reference, not disposable scaffolding.

---

## Part I — Quality, Operations, Delivery

### I.1 Testing Strategy

**Status: NORMATIVE.**

#### I.1.1 Test layers

| Layer | Scope | Speed | Tooling |
| --- | --- | --- | --- |
| Unit | Pure functions, dataclasses, helpers | <1ms each | pytest |
| Service | Service-layer functions with DB; rolled back per test | 10–100ms | pytest + transactional fixtures |
| Integration | Multi-service flows (accept_quote → fulfillment dispatch) | 100–500ms | pytest + transactional fixtures |
| Admin | Custom platform/tenant admin views and actions | 50–200ms | pytest + Client fixture |
| API | DRF viewsets, serializers, contract validation | 50–200ms | pytest + DRF APIClient |
| E2E smoke | Full HTTP flow on a running app, Phase 1 critical paths | 1–10s | pytest + Playwright |
| Property-based | Invariants over generated inputs | 100ms–10s per test | hypothesis |
| Mutation | Pricing engine correctness | minutes | mutmut |
| Load (manual) | RPO/RTO and pipeline throughput validation | n/a | k6 |

CI runs unit + service + integration + admin + API + property-based on every PR. E2E smoke runs on `main` post-merge. Mutation runs nightly. Load tests are manual.

#### I.1.2 Pytest configuration

```toml
[tool.pytest.ini_options]
DJANGO_SETTINGS_MODULE = "settings.test"
python_files = ["test_*.py"]
testpaths = ["apps", "tests"]
markers = [
    "slow: tests that take >1s",
    "property: hypothesis property-based tests",
    "e2e: end-to-end smoke tests",
    "load: load tests",
]
addopts = ["--strict-markers", "--reuse-db", "-ra"]
filterwarnings = [
    "error",
    "ignore::DeprecationWarning:.*third_party.*",
]
```

#### I.1.3 Factories (factory_boy + faker)

```python
class UserFactory(DjangoModelFactory):
    class Meta:
        model = User
        django_get_or_create = ("email",)
    email = factory.Sequence(lambda n: f"user{n}@example.test")
    password = factory.PostGenerationMethodCall("set_password", "test-Pa$$word-12345")
    is_active = True
    is_staff = False
    is_superuser = False
    is_system = False


class OrganizationFactory(DjangoModelFactory):
    class Meta:
        model = Organization
    slug = factory.Sequence(lambda n: f"org-{n}")
    name = factory.LazyAttribute(lambda o: o.slug.replace("-", " ").title())
    status = "ACTIVE"
    timezone = "America/Chicago"
    base_currency_code = "USD"


class MembershipFactory(DjangoModelFactory):
    class Meta:
        model = Membership
    user = factory.SubFactory(UserFactory)
    organization = factory.SubFactory(OrganizationFactory)
    status = "ACTIVE"
    first_name = factory.Faker("first_name")
    last_name = factory.Faker("last_name")
```

##### Tenant-aware factory base

```python
class TenantFactory(DjangoModelFactory):
    class Meta:
        abstract = True
    organization = factory.SubFactory(OrganizationFactory)
    created_by = factory.SubFactory(UserFactory)
    updated_by = factory.SelfAttribute("created_by")
```

#### I.1.4 Service-layer test pattern

```python
@pytest.mark.django_db
def test_send_quote_happy_path(membership_with_capabilities):
    membership = membership_with_capabilities("quotes.send", "quotes.view")
    qv = QuoteVersionFactory(
        organization=membership.organization,
        status="DRAFT",
        expiration_date=date.today() + timedelta(days=30),
    )
    QuoteVersionLineFactory(quote_version=qv, organization=membership.organization)

    result = services.send_quote(
        organization_id=membership.organization_id,
        actor_id=membership.user_id,
        quote_version_id=qv.id,
        recipient_emails=["client@example.com"],
        cover_message=None,
        expected_optimistic_version=qv.optimistic_version,
    )

    qv.refresh_from_db()
    assert qv.status == "SENT"
    assert qv.sent_at is not None
    assert OutboxEntry.objects.filter(
        topic="quote.send_email",
        idempotency_key=f"quote-send:{qv.id}",
    ).exists()
    assert AuditEvent.objects.filter(
        organization_id=membership.organization_id,
        event_type="QUOTE_SENT",
        object_id=str(qv.id),
    ).exists()


@pytest.fixture
def membership_with_capabilities(db):
    def _make(*capability_codes, organization=None):
        membership = MembershipFactory(organization=organization)
        for code in capability_codes:
            CapabilityGrant.objects.create(
                membership=membership,
                capability=Capability.objects.get(code=code),
                grant_type="GRANT",
                reason="test",
            )
        return membership
    return _make
```

#### I.1.5 Property-based tests (Hypothesis)

##### State machine completeness

```python
STATE_MACHINE_REGISTRY = {
    "QuoteVersion": [
        ("DRAFT", "SENT", "send_quote"),
        ("SENT", "ACCEPTED", "accept_quote"),
        # ... full table from C.2.2
    ],
    "WorkOrder": [...],
}


@pytest.mark.property
def test_every_declared_transition_has_a_service_function():
    for entity, transitions in STATE_MACHINE_REGISTRY.items():
        module = SERVICE_MODULES[entity]
        for from_state, to_state, fn_name in transitions:
            fn = getattr(module, fn_name, None)
            assert fn is not None
            sig = inspect.signature(fn)
            assert "organization_id" in sig.parameters
            assert "actor_id" in sig.parameters


@pytest.mark.property
def test_every_terminal_state_has_no_outgoing_transitions():
    for entity, transitions in STATE_MACHINE_REGISTRY.items():
        terminals = TERMINAL_STATES[entity]
        for from_state, _, _ in transitions:
            assert from_state not in terminals
```

##### Pricing engine determinism + replay

```python
@given(context=pricing_context_strategy())
@settings(max_examples=200, deadline=None)
def test_pipeline_is_deterministic(context):
    result_a = execute_pricing_pipeline(context)
    result_b = execute_pricing_pipeline(context)
    assert result_a.final_unit_price == result_b.final_unit_price
    assert result_a.final_line_total == result_b.final_line_total
    assert result_a.tax_amount == result_b.tax_amount
    assert result_a.modifier_log == result_b.modifier_log


@given(context=pricing_context_strategy())
@settings(max_examples=200, deadline=None)
def test_snapshot_replay_matches_within_tolerance(context):
    original = execute_pricing_pipeline(context)
    snapshot = build_snapshot_payload(context, original)
    replayed = replay_from_snapshot_payload(snapshot)
    tolerance = Decimal("0.01")
    assert abs(replayed.final_line_total - original.final_line_total) <= tolerance
```

```python
@st.composite
def pricing_context_strategy(draw, line_type=None):
    line_type = line_type or draw(st.sampled_from(LINE_TYPES))
    quantity = draw(st.decimals(min_value=Decimal("0.01"), max_value=Decimal("10000"), places=4))
    cost_basis = draw(decimal_money)
    return PricingContext(
        organization_id=draw(st.uuids(version=4)),
        # ... full PricingContext build
    )
```

#### I.1.6 Capability-coverage CI test

```python
def test_every_url_has_capability_or_exemption():
    """
    Every URL pattern MUST be:
    - Decorated with @require_capability(), OR
    - Listed in EXEMPT_URL_NAMES with one-line justification.
    """
    resolver = get_resolver()
    missing = []
    for pattern in iterate_url_patterns(resolver):
        if pattern.name in EXEMPT_URL_NAMES:
            continue
        view_func = pattern.callback
        required = getattr(view_func, "_required_capability", None)
        if required is None:
            missing.append(pattern.name or pattern.pattern.regex.pattern)
    assert not missing
```

#### I.1.7 Tenant-isolation CI test

Per B.1.7. Asserts every model with `is_tenant_owned=True` declares organization FK and uses TenantManager.

#### I.1.8 Mutation testing for pricing

```toml
[tool.mutmut]
paths_to_mutate = ["apps/pricing/strategies", "apps/pricing/modifiers", "apps/pricing/engine"]
runner = "pytest -x -q apps/pricing/tests"
tests_dir = "apps/pricing/tests"
```

Run nightly. Target: ≥80% killed mutants on pricing engine modules.

#### I.1.9 Snapshot replay corpus

```text
apps/pricing/tests/corpus/
├── 001_product_cost_plus_simple.json
├── 002_product_target_margin.json
├── ...
├── 042_service_value_based_with_approval.json
├── 050_multi_jurisdiction_tax_summed.json
├── 060_quote_discount_proportional_allocation.json
└── corpus_manifest.json
```

```python
@pytest.mark.parametrize("corpus_file", list_corpus_files())
def test_snapshot_corpus_replay(corpus_file):
    snapshot = load_corpus_snapshot(corpus_file)
    result = replay_pricing_snapshot_from_payload(snapshot)
    expected_total = Decimal(snapshot["outputs"]["final_line_total"])
    tolerance = Decimal("0.01")
    assert abs(result.final_line_total - expected_total) <= tolerance
```

#### I.1.10 Contract tests for the API

```python
@pytest.mark.django_db
def test_committed_schema_matches_runtime():
    client = authenticated_api_client()
    response = client.get("/api/v1/schema/?format=json")
    runtime_schema = response.json()
    committed_path = settings.BASE_DIR / "apps/api/schema/openapi.json"
    with open(committed_path) as f:
        committed_schema = json.load(f)
    assert runtime_schema == committed_schema
```

Schemathesis fuzzing:

```python
@schema.parametrize()
@settings(max_examples=10, deadline=None)
def test_api_conforms_to_schema(case):
    response = case.call()
    case.validate_response(response)
```

#### I.1.11 E2E smoke (Playwright)

E2E covers critical Phase 1 paths:

- Login → 2FA enroll → org pick → tenant landing.
- Lead create → qualify → convert to quote.
- Quote draft → add lines → send → accept (with client resolution).
- Sales order → fulfillment artifacts created.
- Work order assigned → completed.
- Invoice created → sent → paid.
- Logout.

E2E runs on `main` post-merge, not per-PR.

#### I.1.12 Test data discipline

- Tests MUST use factories.
- Tests MUST NOT depend on data created by other tests.
- Tests MUST roll back DB changes.
- Tests MUST NOT write to disk except `tmp_path`.
- Tests MUST NOT make outbound network calls.

#### I.1.13 Decisions Embedded in This Section

- factory_boy + faker over fixture files.
- Hypothesis property tests are CI-required, not nightly.
- Mutation testing nightly, not per-PR.
- E2E on post-merge to `main`, not per-PR.
- Schemathesis fuzzing as a CI gate.
- Snapshot replay corpus checked into source control.

#### I.1.14 Open Questions Deferred to Later Sections

- Performance test suite (k6 scripts, target percentiles): J.10.
- Visual regression testing: K.7.
- Accessibility (a11y) automated testing: K.7.

---

### I.2 Local Development Environment

**Status: NORMATIVE.**

#### I.2.1 Docker Compose topology

```yaml
version: "3.9"

services:
  web:
    build: { context: ., dockerfile: Dockerfile.dev }
    command: python manage.py runserver 0.0.0.0:8000
    volumes:
      - .:/app
      - vite-cache:/app/frontend/node_modules
    ports: ["8000:8000"]
    environment:
      DJANGO_SETTINGS_MODULE: settings.dev
      DATABASE_URL: postgres://mph:mph@postgres:5432/mph
      REDIS_URL: redis://redis:6379/0
      OBJECT_STORE_ENDPOINT: http://minio:9000
      EMAIL_HOST: mailpit
      EMAIL_PORT: "1025"
    depends_on:
      postgres: { condition: service_healthy }
      redis: { condition: service_healthy }
      minio: { condition: service_healthy }
      mailpit: { condition: service_started }

  worker:
    build: { context: ., dockerfile: Dockerfile.dev }
    command: celery -A platform worker -Q critical,default,bulk,reports -l info
    volumes: [".:/app"]
    environment: *web-env
    depends_on: [postgres, redis]

  beat:
    build: { context: ., dockerfile: Dockerfile.dev }
    command: celery -A platform beat -l info --schedule=/tmp/celerybeat-schedule
    volumes: [".:/app"]
    environment: *web-env
    depends_on: [postgres, redis]

  vite:
    image: node:20-alpine
    working_dir: /app/frontend
    command: npm run dev
    volumes:
      - .:/app
      - vite-cache:/app/frontend/node_modules
    ports: ["5173:5173"]

  postgres:
    image: postgres:17
    environment:
      POSTGRES_USER: mph
      POSTGRES_PASSWORD: mph
      POSTGRES_DB: mph
    volumes: ["postgres-data:/var/lib/postgresql/data"]
    ports: ["5432:5432"]
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U mph"]
      interval: 5s
      timeout: 3s
      retries: 5

  redis:
    image: redis:7-alpine
    ports: ["6379:6379"]
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 3s
      retries: 5

  mailpit:
    image: axllent/mailpit:latest
    ports: ["1025:1025", "8025:8025"]
    environment:
      MP_MAX_MESSAGES: "5000"
      MP_SMTP_AUTH_ACCEPT_ANY: "1"
      MP_SMTP_AUTH_ALLOW_INSECURE: "1"

  minio:
    image: minio/minio:latest
    command: server /data --console-address ":9001"
    environment:
      MINIO_ROOT_USER: mph-dev
      MINIO_ROOT_PASSWORD: mph-dev-secret
    volumes: ["minio-data:/data"]
    ports: ["9000:9000", "9001:9001"]
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:9000/minio/health/live"]
      interval: 5s
      timeout: 3s
      retries: 5

  nginx:
    image: nginx:alpine
    volumes: ["./infra/nginx/dev.conf:/etc/nginx/nginx.conf:ro"]
    ports: ["80:80"]
    depends_on: [web]

volumes:
  postgres-data:
  minio-data:
  vite-cache:
```

#### I.2.2 Wildcard subdomain routing

```nginx
events { worker_connections 1024; }
http {
    server {
        listen 80;
        server_name mph.local *.mph.local;
        location / {
            proxy_pass http://web:8000;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }
        location /vite/ {
            proxy_pass http://vite:5173/;
            proxy_set_header Host $host;
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "upgrade";
        }
    }
}
```

#### I.2.3 dnsmasq for wildcard DNS

```bash
# macOS
brew install dnsmasq
sudo brew services start dnsmasq
sudo mkdir -p /etc/resolver
echo "nameserver 127.0.0.1" | sudo tee /etc/resolver/mph.local

# Linux (NetworkManager)
echo "address=/.mph.local/127.0.0.1" | sudo tee /etc/NetworkManager/dnsmasq.d/mph.conf
sudo systemctl reload NetworkManager
```

Fallback: explicit `/etc/hosts` entries per tenant slug used in development.

#### I.2.4 First-time setup

```bash
# scripts/dev-setup.sh
make build
make migrate
make seed-dev
make test
echo "✅ Open http://mph.local/"
echo "✅ Mailpit:  http://localhost:8025/"
echo "✅ MinIO:    http://localhost:9001/"
echo "✅ Vite HMR: http://localhost:5173/"
```

#### I.2.5 Make targets

```makefile
.PHONY: build up down logs shell test lint format migrate seed-dev openapi-regenerate

build:
 docker compose build

up:
 docker compose up -d

down:
 docker compose down

logs:
 docker compose logs -f web worker beat

shell:
 docker compose exec web python manage.py shell

dbshell:
 docker compose exec postgres psql -U mph mph

test:
 docker compose exec web pytest

test-fast:
 docker compose exec web pytest -x -q --no-cov -m "not slow and not e2e"

lint:
 docker compose exec web ruff check apps/ settings/
 docker compose exec web mypy apps/

format:
 docker compose exec web ruff check --fix apps/ settings/
 docker compose exec web ruff format apps/ settings/

migrate:
 docker compose exec web python manage.py migrate

makemigrations:
 docker compose exec web python manage.py makemigrations

seed-dev:
 docker compose exec web python manage.py seed_v1
 docker compose exec web python manage.py seed_dev_tenant

openapi-regenerate:
 docker compose exec web python manage.py spectacular --file apps/api/schema/openapi.json
```

#### I.2.6 Decisions Embedded in This Section

- `mph.local` as the dev wildcard domain.
- dnsmasq path documented; `/etc/hosts` fallback acceptable.
- MinIO over LocalStack S3.
- Mailpit over Mailhog.
- Single `docker-compose.yml` with no overrides.
- Vite as a separate Compose service.

#### I.2.7 Open Questions Deferred to Later Sections

- WSL2 / Windows-specific instructions: K.13.
- Devcontainer support: K.13.

---

### I.3 Environments

**Status: NORMATIVE.**

#### I.3.1 Environment matrix

| Environment | Purpose | Tenants | Data | DNS | Auto-deploy |
| --- | --- | --- | --- | --- | --- |
| **local** | Engineer dev | Sample seeded | Faker-generated | `*.mph.local` | n/a |
| **CI test** | PR + main test runs | Ephemeral per-test | Factory-generated | n/a | per-commit |
| **staging** | Pre-prod validation | Mirrored from prod (anonymized) | Anonymized prod refresh | `*.staging.mypipelinehero.com` | on `main` push |
| **demo** | Sales demos, support training | Curated demo orgs | Curated, idempotent re-seed | `*.demo.mypipelinehero.com` | on demand |
| **prod** | Live tenants | Real | Real | `*.mypipelinehero.com` | manual promotion from staging |

#### I.3.2 Environment configuration

```text
settings/
├── __init__.py
├── base.py
├── dev.py
├── test.py
├── staging.py
├── demo.py
└── prod.py
```

The deployed settings modules are `config.settings.dev`, `config.settings.test`, `config.settings.staging`, `config.settings.demo`, and `config.settings.prod`.

#### I.3.3 Production → staging anonymization pipeline

```python
ANONYMIZATION_RULES = {
    "platform_accounts.User": {
        "email": lambda old, n: f"user-{n}@anon.staging",
        "password": lambda old, n: make_unusable_password(),
        "totp_secret": lambda old, n: None,
        "backup_codes_hash": lambda old, n: None,
    },
    "platform_organizations.Membership": {
        "first_name": lambda old, n: faker.first_name_seeded(n),
        "last_name": lambda old, n: faker.last_name_seeded(n),
        "phone": lambda old, n: faker.phone_seeded(n),
        "invitation_token_hash": lambda old, n: None,
    },
    "crm_clients.Client": {
        "billing_account_name": lambda old, n: f"Anon Client {n}",
        "external_id": lambda old, n: None,
        "tax_exempt_certificate_ref": lambda old, n: None,
    },
    "crm_clients.ClientContact": {
        "first_name": lambda old, n: faker.first_name_seeded(n),
        "last_name": lambda old, n: faker.last_name_seeded(n),
        "email": lambda old, n: f"contact-{n}@anon.staging",
        "phone": lambda old, n: faker.phone_seeded(n),
    },
    "crm_communications.Communication": {
        "body": lambda old, n: f"[Anonymized communication body #{n}]",
        "body_hash": lambda old, n: hashlib.sha256(f"anon-{n}".encode()).hexdigest(),
        "participants": lambda old, n: [],
        "provider_message_id": lambda old, n: None,
    },
    "crm_billing.Payment": {
        "reference": lambda old, n: None,
        "external_id": lambda old, n: None,
    },
}

EXCLUDED_TABLES = {
    "files_attachments.DocumentAttachment",
    "platform_audit.AuditEvent",
    "common_outbox.OutboxEntry",
    "common_outbox.OutboxDeadLetter",
}

DETERMINISTIC_SEED = "{env}-{snapshot_date}".format(env="staging", snapshot_date=date.today().isoformat())
```

Pipeline is deterministic by `(env, snapshot_date)`.

#### I.3.4 Demo environment refresh

Reset on schedule (every Sunday at 06:00 UTC). Demo orgs have `Organization.metadata = {"is_demo": True}`; certain destructive operations are blocked.

#### I.3.5 Promotion gates

```text
local → CI test:    automatic on commit
CI test → staging:  automatic on main push (after CI green)
staging → prod:     manual gate; requires:
                    - Staging soak: ≥24 hours since deploy
                    - Smoke tests: green
                    - On-call acknowledgment
                    - Migration review (if any new migrations)
                    - Changelog updated
```

#### I.3.6 Decisions Embedded in This Section

- Staging is anonymized prod, not synthetic data.
- Anonymization deterministic by date.
- Demo curated and re-seeded weekly.
- Production deploy manually gated.
- One settings module per environment.

#### I.3.7 Open Questions Deferred to Later Sections

- Per-engineer staging branches: K.12.
- Blue-green prod environment: K.12.
- Disaster recovery secondary region: K.12.

---

### I.4 CI/CD and Deployment

**Status: NORMATIVE.**

#### I.4.1 CI pipeline

Every pull request MUST run:

- linting
- type checking
- Django unit tests
- service-layer tests
- integration tests
- authentication/OAuth/OIDC flow tests
- MFA tests
- pricing determinism tests
- snapshot replay corpus tests
- migration safety checks
- tenant-isolation checks
- capability-coverage checks
- dependency vulnerability scan
- Docker image build validation

CI MUST block merge on failure.

#### I.4.2 Image build

The application MUST build into a Docker image suitable for all non-local environments.

Image requirements:

- pinned Python base image
- non-root runtime user
- production dependencies only
- static assets built during image build or release step
- no `.env` files copied into image
- no local SQLite database copied into image
- healthcheck command available
- image tagged with Git SHA and release version

#### I.4.3 Deployment environments

Deployment environments:

| Environment | Deployment method |
| --- | --- |
| `dev` | Docker Compose local |
| `test` | CI containers |
| `staging` | DigitalOcean Docker deployment |
| `demo` | DigitalOcean Docker deployment |
| `prod` | DigitalOcean Docker deployment |

Staging MUST be production-like enough to validate migrations, deploy scripts, worker behavior, beat jobs, object storage, OAuth/OIDC callback behavior, MFA flows, and backup/restore procedures.

#### I.4.4 Production deployment model

v1 deploys without Kubernetes.

Production deployment uses:

- Docker image registry
- DigitalOcean host or hosts
- Docker Compose production file
- reverse proxy container or managed load balancer
- web container
- worker container
- beat container
- managed or self-hosted PostgreSQL
- managed or self-hosted Redis
- optional pgBouncer
- S3-compatible object storage
- environment variables supplied outside Git

#### I.4.5 Production Compose services

The production Compose stack MUST include, directly or through managed services:

```text
reverse-proxy
web
worker
beat
postgres or external DATABASE_URL
redis or external REDIS_URL
pgbouncer, optional
```

The production stack MUST NOT include development-only services such as Mailpit, local Vite dev server, or test-only fixtures.

#### I.4.6 Migration-before-deploy requirement

Database migrations MUST run before new web/worker containers begin serving production traffic.

Deployment sequence:

```text
1. Build and push image.
2. Pull image on target host.
3. Run pre-deploy checks.
4. Run `python manage.py migrate --noinput`.
5. Restart web, worker, and beat containers.
6. Run `python manage.py check --deploy`.
7. Run smoke tests.
8. Verify `/readyz`.
```

Migrations MUST be backward-compatible across at least one deployed application version. Destructive migrations require a documented expand/contract plan.

#### I.4.7 Deployment script shape

```bash
#!/usr/bin/env bash
set -euo pipefail

ENVIRONMENT="$1"
IMAGE_TAG="$2"
HOST="$3"

ssh "$HOST" "
  set -euo pipefail

  cd /opt/mypipelinehero

  export ENVIRONMENT='${ENVIRONMENT}'
  export IMAGE_TAG='${IMAGE_TAG}'

  docker compose -f compose.prod.yml pull

  docker compose -f compose.prod.yml run --rm web \
    python manage.py migrate --noinput

  docker compose -f compose.prod.yml up -d --remove-orphans

  docker compose -f compose.prod.yml exec -T web \
    python manage.py check --deploy

  curl -fsS https://\${PRIMARY_HOSTNAME}/readyz
"
```

The real deploy script MAY differ, but it MUST preserve the same ordering and safety properties.

#### I.4.8 Rollback

Rollback means redeploying a previously known-good Docker image tag.

Rollback MUST NOT automatically run reverse migrations. If a release includes a non-backward-compatible migration, rollback is not allowed unless a release-specific rollback plan exists.

The rollback runbook MUST include:

1. Identify last known-good image tag.
2. Deploy previous image.
3. Restart web/worker/beat.
4. Verify `/readyz`.
5. Verify login.
6. Verify OAuth/OIDC login for enabled providers.
7. Verify quote list.
8. Verify worker consumes a test outbox entry.
9. Record incident notes.

#### I.4.9 Secrets in deployment

Deployment MUST NOT require plaintext secrets in the Git repository.

Allowed v1 patterns:

- `/etc/mypipelinehero/{environment}.env` on host with `0600` permissions.
- DigitalOcean-managed environment variables or secrets.
- Deployment-time injection from a password manager or secret manager.

Production secret rotation MUST be documented in a runbook.

#### I.4.10 Static assets

Static assets MUST be built as part of CI/image build or release build.

Deployment MUST run:

```bash
python manage.py collectstatic --noinput
```

before serving a new release unless static assets are built and packaged earlier in the image.

#### I.4.11 Health endpoints

The application MUST expose:

| Endpoint | Purpose |
| --- | --- |
| `/healthz` | process is alive |
| `/readyz` | process can reach required dependencies |

`/readyz` MUST verify at least:

- PostgreSQL connectivity
- Redis connectivity
- required settings loaded
- migration state not obviously invalid

The reverse proxy, external uptime monitor, and deploy smoke test SHOULD use `/readyz`.

#### I.4.12 pgBouncer

pgBouncer SHOULD be enabled in staging and production once connection count requires pooling.

If enabled:

- Application `DATABASE_URL` points to pgBouncer.
- pgBouncer connects to PostgreSQL.
- transaction pooling is the default.
- Django connection settings must be compatible with pooling.
- Migration commands MAY bypass pgBouncer if required.

#### I.4.13 Out-of-scope for v1 deployment

The following are out of scope for v1:

- Kubernetes manifests
- Helm charts
- Kubernetes Jobs
- Kubernetes Secrets or SealedSecrets
- Kubernetes Ingress
- cert-manager
- HPA
- cluster autoscaling
- service mesh
- blue-green traffic shifting
- canary traffic weighting

These MAY appear in the future scalability appendix.

### I.5 Backup, Restore, Recovery

**Status: NORMATIVE.**

#### I.5.1 Targets

| Target | Value |
| --- | --- |
| RPO | 1 hour |
| RTO | 4 hours |

#### I.5.2 Database backups

| Backup type | Frequency | Retention |
| --- | --- | --- |
| Continuous WAL archiving | Real-time | 7 days |
| Full base backup | Daily at 02:00 UTC | 30 days |
| Weekly archive | Sundays at 03:00 UTC | 1 year |
| Pre-deploy snapshot | Before each prod deploy | 7 days |

Point-in-time recovery (PITR) enabled and validated.

#### I.5.3 Object storage backups

- **Versioning enabled** on production bucket; versions retained 30 days.
- **Cross-region replication** to a secondary bucket.
- **Lifecycle policy:** versioned delete-markers transitioned to Glacier after 30 days.

#### I.5.4 Restore procedures

##### Full database restore

1. Provision new Postgres instance.
2. Restore most recent base backup.
3. Apply WAL files up to target timestamp.
4. Verify integrity: row counts, FK consistency, audit-event continuity.
5. Update application config.
6. Restart affected Docker Compose services.

##### Partial table restore

1. Spin up temporary Postgres from backup.
2. Extract affected rows.
3. Reconcile against current production.
4. Apply forward-only fixes via service-layer (NEVER raw SQL on prod).

##### PITR (logical error)

1. Identify incident timestamp.
2. Restore to temp instance at `incident_ts - 1 minute`.
3. Compare expected vs. actual state.
4. Apply forward-only corrections via service-layer.

#### I.5.5 Restore drill (quarterly)

| # | Step | Owner | Expected duration |
| --- | --- | --- | --- |
| 1 | Schedule drill window; notify on-call | SRE | T-7d |
| 2 | Take "incident" snapshot of staging Postgres | SRE | 5 min |
| 3 | Simulate failure: drop the staging Postgres instance | SRE | 2 min |
| 4 | Provision new instance from latest backup | SRE | 30 min |
| 5 | Apply WAL to PITR target | SRE | 15 min |
| 6 | Verify row counts vs. pre-drill snapshot | SRE | 10 min |
| 7 | Verify FK consistency | SRE | 5 min |
| 8 | Verify audit event continuity | SRE | 5 min |
| 9 | Update staging app config; restart web, worker, and beat containers | SRE | 10 min |
| 10 | Run smoke tests against restored staging | QA | 30 min |
| 11 | Document timing, issues, deviations from runbook | SRE | 30 min |
| 12 | File any runbook update PRs | SRE | T+1d |

Total target: ≤4 hours.

#### I.5.6 Runbook references

| Runbook | Purpose |
| --- | --- |
| `docs/runbooks/database-restore.md` | Full DB restore procedure |
| `docs/runbooks/pitr.md` | Point-in-time recovery |
| `docs/runbooks/incident-response.md` | Top-level incident response |
| `docs/runbooks/outbox-dlq-recovery.md` | Recovering from DLQ accumulation |
| `docs/runbooks/deploy-rollback.md` | Rollback procedure |
| `docs/runbooks/oncall-handoff.md` | On-call shift handoff |

#### I.5.7 Decisions Embedded in This Section

- 1h / 4h RPO/RTO.
- Quarterly restore drill, end-to-end (not tabletop).
- Forward-only corrections via service layer.
- Versioned object storage with cross-region replication.
- Pre-deploy snapshots in addition to scheduled backups.

#### I.5.8 Open Questions Deferred to Later Sections

- DR to secondary region: K.12.
- Per-tenant restore: K.12.

---

### I.6 Migration and Seeding Strategy

**Status: NORMATIVE.**

#### I.6.1 Migration discipline

Django migrations are the only mechanism for schema and data changes. Direct SQL on production is PROHIBITED except in incident response with explicit approval.

#### I.6.2 Seed data hierarchy

| Tier | Scope | Mechanism |
| --- | --- | --- |
| Platform seed | Capabilities, default roles, System User, default tax jurisdictions | Django data migration `seed_v1.py` |
| Per-tenant seed | Tenant-specific defaults at org creation | Service-layer function called from `services.create_organization` |
| Demo seed | Sample tenants and data | Standalone `manage.py seed_dev_tenant` command |

#### I.6.3 Platform seed migration

```python
# apps/platform/rbac/migrations/0002_seed_v1.py
from django.db import migrations
from apps.platform.rbac.seeds.v1_capabilities import V1_CAPABILITIES
from apps.platform.rbac.seeds.v1_default_roles import V1_DEFAULT_ROLES


def seed_v1(apps, schema_editor):
    Capability = apps.get_model("platform_rbac", "Capability")
    Role = apps.get_model("platform_rbac", "Role")
    RoleCapability = apps.get_model("platform_rbac", "RoleCapability")
    User = apps.get_model("platform_accounts", "User")

    # 1. Capabilities (idempotent)
    for cap_def in V1_CAPABILITIES:
        Capability.objects.update_or_create(
            code=cap_def["code"],
            defaults={
                "name": cap_def["name"],
                "description": cap_def["description"],
                "category": cap_def["category"],
            },
        )

    # 2. Default role templates
    for role_def in V1_DEFAULT_ROLES:
        role, _ = Role.objects.update_or_create(
            organization=None,
            code=role_def["code"],
            defaults={
                "name": role_def["name"],
                "description": role_def["description"],
                "is_default": True,
                "is_scoped_role": role_def.get("is_scoped_role", False),
                "is_locked": True,
            },
        )
        existing = set(RoleCapability.objects.filter(role=role).values_list("capability__code", flat=True))
        desired = set(role_def["capabilities"])
        for code in desired - existing:
            cap = Capability.objects.get(code=code)
            RoleCapability.objects.create(role=role, capability=cap)
        for code in existing - desired:
            cap = Capability.objects.get(code=code)
            RoleCapability.objects.filter(role=role, capability=cap).delete()

    # 3. System User
    User.objects.update_or_create(
        email="system@mypipelinehero.internal",
        defaults={
            "is_system": True,
            "is_active": True,
            "is_staff": False,
            "is_superuser": False,
        },
    )


def unseed_v1(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("platform_rbac", "0001_initial"),
        ("platform_accounts", "0001_initial"),
    ]
    operations = [
        migrations.RunPython(seed_v1, unseed_v1),
    ]
```

#### I.6.4 Idempotent seeding

All seed migrations MUST be idempotent. Mechanisms:

- `update_or_create` with stable lookup keys.
- Set-based capability sync.
- No reliance on auto-incrementing IDs.

#### I.6.5 Successor seed migrations

```python
# apps/platform/rbac/migrations/0017_seed_v1_3_pricing_capabilities.py
def add_v1_3_capabilities(apps, schema_editor):
    Capability = apps.get_model("platform_rbac", "Capability")
    Role = apps.get_model("platform_rbac", "Role")
    RoleCapability = apps.get_model("platform_rbac", "RoleCapability")

    NEW_CAPS = [
        {"code": "pricing.bundles.archive", "name": "Archive bundles", ...},
    ]
    for cap_def in NEW_CAPS:
        cap, _ = Capability.objects.update_or_create(
            code=cap_def["code"],
            defaults={...},
        )
        # Auto-extend Owner template only
        owner_template = Role.objects.get(organization=None, code="owner")
        RoleCapability.objects.update_or_create(
            role=owner_template,
            capability=cap,
        )
        # Also extend per-tenant Owner roles
        for org_owner in Role.objects.filter(organization__isnull=False, code="owner"):
            RoleCapability.objects.update_or_create(
                role=org_owner,
                capability=cap,
            )
```

Successor migrations:

- Append capabilities; never silently remove.
- Auto-extend Owner role only.
- Other defaults only if release notes call for it explicitly.
- Custom (tenant-defined) roles never modified.

#### I.6.6 Per-tenant seed

```python
def create_organization(*, slug, name, primary_contact_email, ...) -> Organization:
    with transaction.atomic():
        org = Organization.objects.create(
            slug=slug, name=name, status="ACTIVE",
            primary_contact_email=primary_contact_email,
            timezone="America/Chicago", base_currency_code="USD",
        )

        # 1. Copy default role templates to org-scoped roles
        for template in Role.objects.filter(organization=None, is_default=True, is_locked=True):
            org_role = Role.objects.create(
                organization=org,
                code=template.code,
                name=template.name,
                description=template.description,
                is_default=True,
                is_scoped_role=template.is_scoped_role,
                is_locked=True,
            )
            for rc in RoleCapability.objects.filter(role=template):
                RoleCapability.objects.create(role=org_role, capability=rc.capability)

        # 2. Default segment
        CustomerSegment.objects.create(
            organization=org, code="STANDARD", name="Standard",
            default_multiplier=Decimal("1.00"), is_default=True,
        )

        # 3. Default invoicing policy
        InvoicingPolicy.objects.create(organization=org)

        # 4. Default tax jurisdiction (org's country baseline)
        # 5. Default labor rate card (empty draft)
        # 6. Numbering config defaults
        org.numbering_config = DEFAULT_NUMBERING_CONFIG
        org.save()

        # 7. Audit
        audit_emit("ORG_SETTINGS_UPDATED", actor_id=None, organization_id=org.id, ...)

    return org
```

#### I.6.7 Custom user model baseline

The `platform_accounts.User` model MUST be defined and migrated in `apps/platform/accounts/migrations/0001_initial.py`. Retrofitting `AUTH_USER_MODEL` after deployment is PROHIBITED.

```python
# scripts/check_user_model_baseline.py
"""
Asserts that:
- apps/platform/accounts/migrations/0001_initial.py exists
- It defines the User model
- AUTH_USER_MODEL = "platform_accounts.User" in config/settings/base.py
"""
```

#### I.6.8 Migration ordering

```text
apps/platform/accounts/migrations/0001_initial.py          # User
apps/platform/organizations/migrations/0001_initial.py     # Organization, Membership
apps/platform/rbac/migrations/0001_initial.py              # Capability, Role, grants
apps/platform/rbac/migrations/0002_seed_v1.py              # depends on platform_accounts.0001 + platform_organizations.0001 + platform_rbac.0001
apps/operations/locations/migrations/0001_initial.py       # Region/Market/Location
apps/catalog/pricing/migrations/0001_initial.py
apps/crm/quotes/migrations/0001_initial.py
... etc.
```

Every nested Django app MUST use a stable explicit `AppConfig.label` so migration dependencies remain readable and durable.

#### I.6.9 Migration verification

```yaml
- run: python manage.py migrate
- run: python manage.py check
- run: python manage.py makemigrations --check --dry-run

# On PRs touching seed_v1.py:
- run: python manage.py migrate
- run: python manage.py migrate platform_rbac 0002 --fake
- run: python manage.py migrate platform_rbac   # re-runs seed; must be idempotent
- run: pytest apps/platform/rbac/tests/seeds/
```

#### I.6.10 Decisions Embedded in This Section

- Three-tier seed hierarchy (platform / per-tenant / demo).
- Successor migrations append-only.
- New capabilities auto-extend Owner role only.
- Per-tenant seed runs from `services.create_organization`, not a migration.
- Custom user model in 0001_initial. Non-negotiable.
- Idempotent seeders verified by CI re-run check.

#### I.6.11 Open Questions Deferred to Later Sections

- Tenant data import / CSV import: K.13.
- Migration of historical accepted quotes from legacy systems: K.13.

---

---

## Part J — Development Phases and Milestones

### J.1 Milestone Framework

**Status: NORMATIVE.**

#### J.1.1 Purpose

Part J is the binding roadmap for the v1 build. It is the contract between engineering and the business about what ships, in what order, with what guarantees. Every milestone has explicit, testable exit criteria; "done" is not a judgment call.

The milestone structure is sequential with deliberate parallelism windows. Skipping a milestone is prohibited; deferring scope within a milestone is permitted under the rules in J.12.

#### J.1.2 Definition of Done

A milestone is DONE when ALL of the following are true:

1. **Code complete.** Every NORMATIVE deliverable in the milestone's Scope section has shipped to `main`.
2. **Tests green.** The CI pipeline (I.1) is green on the commit at which the milestone is declared done. No skipped tests for milestone-relevant code without a tracked deferral.
3. **Exit criteria pass.** Every line in the milestone's Exit Criteria section has been verified — either via an automated check (linked test) or via a recorded manual verification (linked runbook step or screenshot).
4. **Documentation in sync.** Any guide section whose NORMATIVE rules changed during the milestone has a corresponding guide PR merged.
5. **Decisions reviewed.** Any new decisions added during the milestone are reviewed and either accepted or refuted in the milestone retrospective.
6. **Audit checked.** The capability-coverage CI test (I.1.6), tenant-isolation CI test (B.1.7), and snapshot replay corpus (I.1.9) all pass on the milestone commit.
7. **Retrospective filed.** A short retrospective document is filed in `docs/retrospectives/M{n}.md` listing what shipped, what slipped, what was learned, and what was deferred (with K.1 entries created for each deferral).

A milestone is NOT done because "we built the thing." It is done because the seven items above are all verifiable.

#### J.1.3 Exit-criteria discipline

Exit criteria MUST be:

- **Testable.** Either runs in CI or has a documented manual verification step.
- **Specific.** "Performance is good" is not exit criteria; "p95 quote-list page latency under 800ms in staging on the synthetic 10k-quote dataset" is.
- **Traceable.** Each criterion references a test file path, a runbook step, a CI workflow job, or a manual verification record.
- **Bounded.** Each criterion has a clear pass/fail threshold; no "should be" or "ideally."

A criterion that cannot be tested is rewritten until it can be.

#### J.1.4 Dependency graph

```text
                     ┌──────────────┐
                     │ M0 Foundation│
                     └──────┬───────┘
                            │
                     ┌──────▼───────┐
                     │ M1 Tenancy / │
                     │ Identity /   │
                     │ Auth         │
                     └──────┬───────┘
                            │
                     ┌──────▼───────┐
                     │ M2 RBAC +    │
                     │    Audit     │
                     └──┬────────┬──┘
                        │        │
              ┌─────────▼──┐  ┌──▼─────────────┐
              │ M3 Catalog │  │ M4 CRM         │
              │  + Pricing │  │   Pipeline     │
              │  + Snapshots│  │   (parallel)   │
              └─────────┬──┘  └──┬─────────────┘
                        │        │
                     ┌──▼────────▼──┐
                     │ M5           │
                     │ Fulfillment  │
                     └──────┬───────┘
                            │
                     ┌──────▼───────┐
                     │ M6 Billing + │
                     │   Reporting  │
                     └──────┬───────┘
                            │
                     ┌──────▼───────┐
                     │ M7 Custom    │
                     │ Tenant Admin │
                     │   Data       │
                     │   Lifecycle  │
                     └──────┬───────┘
                            │
                     ┌──────▼───────┐
                     │ M8 Production│
                     │   Readiness  │
                     └──────┬───────┘
                            │
                       [v1 Launch]
                            │
                     ┌──────▼───────┐
                     │ M9 Phase 2   │
                     │   React      │
                     │   Portal     │
                     │   (post-v1)  │
                     └──────────────┘
```

M3 and M4 may run in parallel after M2 completes. Other milestones MUST run sequentially.

#### J.1.5 Team-size assumption

Duration estimates assume **3–4 senior backend engineers + 1 senior frontend engineer + 1 SRE/platform engineer + 1 product/PM**, with an engineering manager dual-hatting on architecture review.

Smaller teams MUST scale durations and SHOULD reduce parallelism. Larger teams SHOULD NOT compress durations below the floor.

#### J.1.6 Decisions Embedded in This Section

- Definition of Done is seven-pointed and non-negotiable.
- Exit criteria MUST be testable.
- Sequential milestones with one parallelism window (M3 + M4).
- Milestone retrospectives produce K.1 entries for every deferral.
- Team-size floor for durations.

#### J.1.7 Open Questions Deferred to Later Sections

- None. This is the binding roadmap.

---

### J.2 M0 — Foundation

**Status: NORMATIVE.**

#### J.2.1 Goals

Establish the project skeleton: repository, Docker Compose dev environment, Django project layout, root-domain landing page, custom user model in migration #1, baseline CI pipeline, the platform-seed migration, custom platform admin shell, dev-only Django admin inspection path, and the first-tenant-creation path. By the end of M0, an engineer can clone the repo, run `make seed-dev`, view the landing page at `/`, sign in to the custom platform admin shell, inspect seeded models in dev-only `/django-admin/`, and see one seeded tenant.

#### J.2.2 Scope

| Reference | Deliverable |
| --- | --- |
| A.5 | Base project structure with root-level `frontend/` and `backend/apps/...` domain organization |
| A.3 | Docker Compose with web, postgres, redis, mailpit, minio, vite, nginx (per I.2.1) |
| A.3 | nginx wildcard subdomain routing for `*.mph.local` (per I.2.2) |
| B.3.1 | Custom `platform_accounts.User` model in `apps/platform/accounts/migrations/0001_initial.py` |
| B.3.10 | System User created by seed migration |
| I.6.3 | `seed_v1` data migration (capabilities scaffold, default role templates scaffold, System User) |
| I.4.1 | CI pipeline scaffold (lint + test jobs only) |
| H.1/H.8 | Frontend tooling scaffold, shared CSS/design assets, Tailwind/django-vite/HTMX baseline |
| H.3 | Root-domain custom landing page at `/` and login page at `/login/` |
| H.7 | Custom platform admin shell at `/platform/` |
| H.7 | Dev-only Django admin inspection path at `/django-admin/` |
| FM | This guide checked into the repo at `docs/guide.md` |
| I.6.7 | `scripts/check_user_model_baseline.py` enforcement |
| A.4.5 | Static AST check scaffold for service-layer discipline (warns initially; blocks from M2) |

#### J.2.3 Out-of-scope

- Tenant subdomain routing logic (M1).
- Full authentication flows beyond root landing/login scaffolding and custom platform admin shell (M1).
- Base Django admin as a product surface. Dev-only raw model inspection at `/django-admin/` is allowed.
- Pricing engine code (M3).
- Any commercial domain code (M4).
- Production CI/CD (M8).
- Sentry, OpenTelemetry full wiring (M8).

#### J.2.4 Exit criteria

| # | Criterion | Verification |
| --- | --- | --- |
| 1 | `make build && make up && make seed-dev` succeeds on a fresh checkout | manual; recorded in `docs/retrospectives/M0.md` |
| 2 | `make test` runs and passes (zero tests is acceptable here; framework must work) | CI job `test` green |
| 3 | `make lint` runs ruff + mypy and passes on baseline code | CI job `lint` green |
| 4 | `platform_accounts.User` is the configured `AUTH_USER_MODEL` | `scripts/check_user_model_baseline.py` passes |
| 5 | `python manage.py migrate` succeeds on a fresh DB | CI test job |
| 6 | One `is_system=True` user exists after `seed_v1` runs | `pytest apps/platform/rbac/tests/seeds/test_system_user.py` |
| 7 | Root-domain landing page is reachable in dev at `/` | manual; recorded |
| 8 | Custom platform admin shell is reachable in dev at `/platform/` | manual; recorded |
| 9 | Dev-only Django admin inspection path is reachable at `/django-admin/` for a dev superuser | manual; recorded |
| 10 | Base Django admin is not required for any v1 product workflow | review |
| 11 | Attached landing/login/base templates and CSS assets are committed to the paths in A.5/H.8 | review |
| 12 | `mailpit` web UI reachable at `http://localhost:8025/` | manual |
| 13 | `minio` console reachable at `http://localhost:9001/` | manual |
| 14 | Vite HMR works: changing a TS or CSS file updates the browser without full reload | manual |

#### J.2.5 Dependencies

**Entry:** none. M0 is the entry point.
**Blocks:** every other milestone.

#### J.2.6 Suggested duration

**2–3 calendar weeks.**

#### J.2.7 Risk register

1. **Custom user model retrofitting.** If `AUTH_USER_MODEL` is not in migration #1, retrofitting is severe pain. Mitigation: I.6.7 CI check from day one.
2. **Compose flakiness on macOS.** Docker Desktop volume performance can be terrible; pre-emptively use named volumes for `node_modules`.
3. **dnsmasq friction.** Engineers without admin rights will struggle with wildcard DNS. Mitigation: `/etc/hosts` fallback documented in I.2.3 and the dev-setup script must work for both paths.
4. **Custom admin shell expands into domain CRUD too early.** Mitigation: M0 shell only proves routing/authenticated staff landing; domain admin workflows land in M7.
5. **Dev-only Django admin becomes a product dependency.** Mitigation: `/django-admin/` is documented as raw model inspection only, and exit criteria require no v1 workflow depends on it.
6. **Landing-page styles drift from tenant/React styles.** Mitigation: H.8 makes the attached CSS/design tokens the shared visual baseline.

#### J.2.8 Decisions Embedded in This Section

- M0 ships zero commercial domain code by design.
- Frontend tooling scaffolded in M0 even though no tenant portal exists yet.
- Static AST check warns in M0, blocks from M2.
- The custom platform admin shell exists from M0; base Django admin is not a product milestone dependency.
- Dev-only `/django-admin/` is allowed for raw model inspection.
- The root-domain landing page exists from M0.
- Shared CSS/design assets are part of the foundation, not later polish.

#### J.2.9 Open Questions Deferred to Later Sections

- None.

---

### J.3 M1 — Tenancy + Identity + Auth

**Status: NORMATIVE.**

#### J.3.1 Goals

M1 establishes tenant identity, user authentication, OAuth/OIDC login, MFA, membership resolution, organization routing, tenant handoff, support access, and the foundational RBAC data model.

M1 delivers the security and identity foundation required before any tenant-owned business domain can be safely built.

#### J.3.2 Scope

| Reference | Deliverable |
| --- | --- |
| B.1 | Organization model, slug rules, status semantics |
| B.1 | TenantOwnedModel abstract base |
| B.1 | TenantManager and TenantQuerySet |
| B.1 | Tenant-isolation CI guardrail |
| B.2 | Region, Market, Location models |
| B.2 | MembershipScopeAssignment model |
| B.2 | Operating-scope resolution helpers |
| B.3 | Custom User model |
| B.3 | Membership model |
| B.3 | OAuth/OIDC external identity integration |
| B.3 | OAuthProviderConfig model |
| H.3 | Root-domain landing page entrypoint |
| B.4 | Root-domain login page |
| B.4 | Local email/password login |
| B.4 | django-allauth account/socialaccount integration |
| B.4 | OIDC provider login flow |
| B.4 | Local MFA enrollment and challenge |
| B.4 | Trusted external MFA policy |
| B.4 | Organization picker |
| B.4 | Signed handoff token issuance and consumption |
| B.4 | Tenant-local session creation |
| B.4 | Multi-tab warning interstitial |
| B.4 | Logout semantics |
| B.5 | Password policy |
| B.5 | OAuth/OIDC account takeover protections |
| B.5 | Rate limiting |
| B.6 | Capability, Role, RoleCapability, MembershipRole, MembershipCapabilityGrant |
| B.6 | Seed default roles |
| B.6 | Basic capability evaluation helper |
| B.7/H.7 | Platform console landing page |
| H.4/H.7 | Initial tenant-view page after handoff for tenant-user perspective testing |
| B.7 | Support impersonation start/end |
| B.7 | ImpersonationAuditLog |
| B.7 | Server-rendered impersonation banner |

#### J.3.3 Required OAuth/OIDC implementation

M1 MUST implement:

```text
django-allauth account login
django-allauth socialaccount
OpenID Connect provider support
root-domain OAuth/OIDC callback
canonical User resolution
ExternalIdentity or SocialAccount linkage
provider configuration loaded from environment/secrets
local MFA via TOTP/recovery codes
trusted-provider MFA policy
tenant membership resolution after authentication
cross-subdomain handoff
```

OAuth/OIDC login MUST NOT create tenant memberships, roles, capabilities, or operating scopes.

#### J.3.4 Required MFA implementation

M1 MUST implement local MFA using:

```text
totp
recovery_codes
```

M1 MUST support this policy:

| Login path | MFA behavior |
| --- | --- |
| Local password | local MFA required |
| OAuth/OIDC with trusted provider MFA | provider MFA may satisfy login MFA |
| OAuth/OIDC without trusted provider MFA | local step-up MFA required |
| Support user through any login path | MFA required |
| Sensitive action | recent re-auth required |

#### J.3.5 Authentication flow tests

M1 MUST include tests for:

1. local password login with MFA,
2. local password login without enrolled MFA forcing enrollment,
3. OAuth/OIDC login with linked external identity,
4. OAuth/OIDC login with verified email linking to existing invited user,
5. OAuth/OIDC login rejected for unverified email when verification is required,
6. OAuth/OIDC login with trusted provider MFA,
7. OAuth/OIDC login without trusted provider MFA requiring local step-up,
8. user with zero memberships sees no active access page,
9. staff user with zero memberships lands on platform console,
10. user with one membership receives handoff token,
11. user with multiple memberships sees organization picker,
12. handoff token cannot be replayed,
13. handoff token cannot be consumed on wrong tenant host,
14. tenant-local session includes user, organization, membership, auth method, and MFA timestamp,
15. support impersonation requires reason and re-auth,
16. impersonation banner appears in tenant portal.

#### J.3.6 Account linking tests

M1 MUST include tests for:

1. provider subject ID maps to existing external identity,
2. verified email can link only through approved flow,
3. unverified email cannot link to existing user,
4. conflicting external identity blocks login,
5. user cannot unlink last login method,
6. unlinking external identity requires re-auth,
7. provider tokens and authorization codes are never logged.

#### J.3.7 RBAC foundation tests

M1 MUST include tests for:

1. default capabilities seeded,
2. default roles seeded,
3. Owner role receives all capabilities,
4. DENY grant overrides GRANT,
5. scoped role with no scope assignment sees no scoped records,
6. support user does not automatically receive tenant capabilities during impersonation,
7. tenant-owned models use TenantManager.

#### J.3.8 Out-of-scope

- Tenant-managed custom identity providers.
- SAML.
- Provider group-to-role mapping.
- SCIM provisioning.
- Passwordless magic links.
- Passkeys-only login.
- Public API authentication.
- Full URL capability-coverage CI test; this lands in M2.
- Complete audit partitioning; this lands in M2.
- Production OAuth provider launch verification; this lands in M8.

#### J.3.9 Exit criteria

| # | Criterion | Verification |
| --- | --- | --- |
| 1 | Custom User model exists from migration #1 | migration review |
| 2 | Organization slug routing works locally | integration test |
| 3 | Local password login works on root domain | integration test |
| 4 | Local MFA enrollment and challenge work | integration test |
| 5 | Recovery codes work and are single-use | integration test |
| 6 | OAuth/OIDC login works through configured test provider | integration test |
| 7 | Provider client secret is loaded from env/secret source | settings test |
| 8 | OAuth/OIDC callback validates provider response | integration test |
| 9 | External identity links to canonical User | integration test |
| 10 | OAuth/OIDC login does not create Membership | service test |
| 11 | Trusted external MFA policy is enforced | integration test |
| 12 | Untrusted provider requires local step-up MFA | integration test |
| 13 | Organization picker appears for multi-membership users | integration test |
| 14 | Single-membership users receive valid handoff token | integration test |
| 15 | Handoff token is single-use and 60-second limited | integration test |
| 16 | Tenant-local session is independent from root-domain session | integration test |
| 17 | Support user lands on platform console | integration test |
| 18 | Support impersonation creates audit log and banner | integration test |
| 19 | Tenant-isolation model guardrail passes | CI |
| 20 | No tokens, secrets, TOTP secrets, or recovery codes appear in logs | security test |

#### J.3.10 Dependencies

**Entry:** M0 complete.  
**Blocks:** M2 RBAC enforcement, audit, and all tenant-owned domain work.

#### J.3.11 Suggested duration

**4–6 calendar weeks.**

#### J.3.12 Risk register

1. **OAuth/OIDC accidentally grants tenant access.** Mitigation: membership resolution remains separate and required.
2. **Account takeover through email-based linking.** Mitigation: require verified email and approved linking flow.
3. **Trusted external MFA is assumed without proof.** Mitigation: provider-level security review and explicit `trust_external_mfa` flag.
4. **Tenant sessions become shared across subdomains.** Mitigation: tenant-local session cookie per subdomain.
5. **Provider tokens leak into logs.** Mitigation: audit/log masking tests.
6. **Support impersonation bypasses tenant RBAC.** Mitigation: impersonated membership drives capability checks.

#### J.3.13 Decisions Embedded in This Section

- Django custom User remains canonical.
- django-allauth is the v1 authentication integration library.
- OIDC is preferred for external login.
- OAuth/OIDC login proves identity only.
- Membership/RBAC/RML determine tenant authorization.
- Local MFA is required unless provider MFA is explicitly trusted.
- Tenant access continues through root-domain login and signed tenant handoff.

### J.4 M2 — RBAC + Audit

**Status: NORMATIVE.**

#### J.4.1 Goals

Implement the three-layer authorization enforcement, the full v1 capability registry and default roles, MembershipCapabilityGrant override semantics, the AuditEvent table with monthly partitioning, the typed exception taxonomy, the outbox pattern with dispatcher and beat, and structured logging.

#### J.4.2 Scope

| Reference | Deliverable |
| --- | --- |
| B.6.3 | Full v1 capability registry seeded |
| B.6.4 | 11 default role templates seeded |
| B.6.7 | RoleCapability, MembershipRole, MembershipCapabilityGrant models |
| B.6.2 | Permission evaluation algorithm with DENY-beats-GRANT |
| B.6.8 | `@require_capability` view decorator + DRF mixins |
| B.6.9 | Capability-coverage CI test |
| B.2.5 | Queryset intersection with operating scope |
| B.2.6 | Object-level operating-scope check |
| C.1.14 | AuditEvent model with monthly range partitioning |
| C.5.3 | Partition pre-create beat job |
| G.5.3 | `audit_emit` API + transaction-bound enforcement |
| G.5.5 | Masking and redaction rules |
| G.5.6 | Retention rules (no actual prune yet; ships with M8) |
| G.2 | Full domain exception taxonomy with HTTP/UI mapping |
| G.2.5 | Phase 1 Django middleware for domain-error handling |
| C.1.14 | OutboxEntry + OutboxDeadLetter models |
| G.3.2 | `outbox.publish` API |
| G.3.3 | Outbox dispatcher beat job (5-second tick) |
| G.3.6 | `@outbox_handler` decorator + worker pattern |
| G.4.1 | structlog configuration with required keys |
| G.4.2 | Correlation ID propagation through middleware + outbox |
| G.4.8 | Health endpoints (`/healthz`, `/readyz`, `/healthz/deep`) |
| A.4.5 | Static AST check upgraded from warn to block |
| I.4.4 | Celery beat singleton scaffolding (redbeat configured) |

#### J.4.3 Out-of-scope

- Pricing engine (M3).
- Domain models beyond identity/RBAC (M3, M4).
- Sentry integration (M8).
- Audit retention pruning (M8).
- Tenant export/deletion (M7).

#### J.4.4 Exit criteria

| # | Criterion | Verification |
| --- | --- | --- |
| 1 | Capability-coverage CI test passes | CI |
| 2 | All 11 default role templates exist in DB after `seed_v1` | `pytest apps/platform/rbac/tests/seeds/test_v1_default_roles.py` |
| 3 | Per-tenant default roles materialize from templates on `services.create_organization` | service test |
| 4 | DENY MembershipCapabilityGrant overrides GRANT | service test |
| 5 | Tenant-isolation CI test still passes after RBAC code lands | CI |
| 6 | Operating-scope intersection blocks queries to records outside permitted RML closure | service test |
| 7 | Object-level scope check raises `OperatingScopeViolationError` | service test |
| 8 | AuditEvent monthly partitions exist for current month + 6 months ahead | manual + `pytest apps/audit/tests/test_partitions.py` |
| 9 | `audit_emit` raises if called outside `transaction.atomic()` | service test |
| 10 | All domain exceptions in G.2 exist with stable `error_code` strings | unit test enumerating taxonomy |
| 11 | DRF exception handler returns the documented JSON envelope | API test |
| 12 | Phase 1 middleware redirects `CapabilityRequiredError` with messages framework toast | manual + view test |
| 13 | Outbox dispatcher tick runs every 5 seconds and picks up PENDING entries | integration test |
| 14 | Outbox idempotency key uniqueness enforced; duplicate non-terminal publish raises `IdempotencyConflictError` | service test |
| 15 | Outbox CONSUMED entries pruned after 30 days (job exists; first run not required yet) | service test |
| 16 | Correlation ID propagates from web request → service log → outbox payload → worker log | integration test |
| 17 | Health endpoints return 200 unauthenticated; `/readyz` returns 503 if Postgres or Redis is down | integration test |
| 18 | Static AST check now blocks PRs (no longer warn-only) | CI |

#### J.4.5 Dependencies

**Entry:** M1 complete.
**Blocks:** M3, M4, every later milestone.

#### J.4.6 Suggested duration

**4–5 calendar weeks.**

#### J.4.7 Risk register

1. **Outbox dispatcher race conditions.** `select_for_update(skip_locked=True)` semantics differ subtly across versions. Mitigation: integration test running two dispatcher instances asserting no double-pickup.
2. **AuditEvent partition overflow.** If pre-create job fails silently, inserts fail at month rollover. Mitigation: alert on pre-create failure (G.4.9).
3. **Capability registry creep during M3+.** Each new domain wants new capabilities. Mitigation: any new capability requires a guide PR amending B.6.3.

#### J.4.8 Decisions Embedded in This Section

- Outbox dispatcher ships in M2, not deferred.
- AuditEvent partitioning ships from migration #1 of the audit app.
- Capability-coverage CI test blocks PRs from M2 onward.

#### J.4.9 Open Questions Deferred to Later Sections

- Sentry integration: M8.
- Metrics/traces export: M8.
- Audit search UI and custom tenant admin site: M7.

---

### J.5 M3 — Catalog + Pricing Engine + Snapshots

**Status: NORMATIVE.**

#### J.5.1 Goals

Implement the catalog and simplified pricing engine foundation.

M3 delivers:

```text
Service/Product/RawMaterial/Supplier catalog
+ BOM versioning
+ pricing configuration models
+ PricingContextBuilder
+ cost/input resolvers
+ 7 base pricing strategies
+ reusable modifier pipeline
+ approval policy evaluation
+ PricingSnapshot persistence
+ snapshot replay
```

M3 MUST NOT implement one pricing strategy class per named business scenario.

#### J.5.2 Scope

| Reference | Deliverable |
| --- | --- |
| E.1 | Service, Product, RawMaterial, Supplier, SupplierProduct models + service surface |
| E.1.3 | UnitOfMeasure enum |
| E.2 | BOM, BOMVersion, BOMLine models + activation/supersession service |
| E.2.4 | BuildBOMSnapshot model |
| E.3 | PricingRule, PriceList, PriceListItem, ClientContractPricing, LaborRateCard, LaborRateCardLine models |
| E.4 | CustomerSegment, PromotionCampaign, PromotionUsage, BundleDefinition, BundleComponent models |
| E.5 | Pricing architecture using strategies, resolvers, modifiers, approval policies, and snapshots |
| E.5 | PricingContext frozen dataclass |
| E.5 | PricingContextBuilder |
| E.5 | Cost/InputResolver Protocol + resolver registry |
| E.5 | PricingStrategy Protocol + 7-strategy registry |
| E.5 | PricingModifier Protocol + modifier registry |
| E.5 | ApprovalPolicy service |
| E.6 | Base strategy implementations |
| E.7 | Modifier implementations |
| E.8 | Pricing rule resolution algorithm |
| E.9 | PricingApproval model + workflow services + expiry beat job |
| E.10 | PricingSnapshot model + replay procedure |
| E.10 | Engine version policy v1.0 |
| F.4 | TaxJurisdiction, TaxRate models + resolution algorithm |
| I.1.5 | Hypothesis property tests for pricing-engine determinism + replay |
| I.1.9 | Snapshot replay corpus |
| I.1.8 | Mutation testing config for pricing modules |
| C.5.3 | Monthly partitioning on PricingSnapshot |

#### J.5.3 Base strategies required

The strategy registry MUST include exactly these v1 base strategy codes unless the guide is amended:

```text
strategy.fixed_price
strategy.cost_plus
strategy.target_margin
strategy.rate_card
strategy.tiered
strategy.component_sum
strategy.recurring_plan
```

#### J.5.4 Cost/input resolvers required

The resolver registry MUST include:

```text
cost_source.manual
cost_source.catalog_standard_cost
cost_source.selected_supplier
cost_source.bom_version
cost_source.manufactured_build_up
cost_source.labor_rate_card
```

The following MAY be added later without changing the base strategy model:

```text
cost_source.preferred_supplier
cost_source.lowest_available_supplier
cost_source.landed_cost
cost_source.contract_cost
```

#### J.5.5 Modifiers required

The modifier registry MUST include:

```text
modifier.customer_contract
modifier.customer_segment
modifier.location
modifier.service_zone
modifier.complexity
modifier.rush
modifier.after_hours
modifier.promotion
modifier.line_discount
modifier.quote_discount
modifier.minimum_charge
modifier.trip_fee
modifier.manual_override
modifier.floor_margin
modifier.tax
modifier.rounding
```

`modifier.currency` and `modifier.approval_policy` MAY exist as internal future-compatible hooks, but they MUST NOT obscure the separation between price adjustment and approval evaluation.

#### J.5.6 Strategy classes explicitly prohibited in v1

The following MUST NOT be implemented as standalone base strategy classes in v1:

```text
PreferredSupplierPricingStrategy
LowestCostSupplierPricingStrategy
RushServicePricingStrategy
AfterHoursServicePricingStrategy
LocationAdjustedProductPricingStrategy
ComplexityAdjustedServicePricingStrategy
PromotionalPricingStrategy
MinimumChargePricingStrategy
FloorPricePricingStrategy
MilestonePricingStrategy
```

These behaviors MUST be implemented as resolvers, modifiers, approval policies, or billing schedules.

#### J.5.7 Out-of-scope

- Quote, QuoteVersion, QuoteVersionLine models.
- SalesOrder, Invoice, and Payment domains.
- BOM clone-to-new-version UX.
- Bundle-of-bundles.
- Multiple stacking promotions.
- Multi-currency.
- Concrete accounting adapters.
- Kubernetes deployment.
- `strategy.value_outcome`, unless explicitly added by guide amendment.
- Advanced recurring billing automation beyond quote-time pricing support.
- Automated lowest-cost supplier selection unless required by the first production tenant.

#### J.5.8 Exit criteria

| # | Criterion | Verification |
| --- | --- | --- |
| 1 | All 7 base strategies registered in `STRATEGY_REGISTRY` | registry completeness test |
| 2 | Required cost/input resolvers registered in `COST_RESOLVER_REGISTRY` | registry completeness test |
| 3 | Required modifiers registered in `MODIFIER_REGISTRY` | registry completeness test |
| 4 | Strategy implementations perform no database queries | unit test / monkeypatch guard |
| 5 | Resolver implementations perform all required DB-backed input selection | service tests |
| 6 | PricingContextBuilder resolves catalog, supplier, BOM, labor rate, contract, segment, location, tax, and rounding inputs | integration tests |
| 7 | `strategy.cost_plus` supports selected supplier and manufactured build-up through resolver inputs | deterministic pricing tests |
| 8 | `strategy.target_margin` correctly distinguishes margin from markup | deterministic pricing tests |
| 9 | `strategy.rate_card` supports role/hour/rate pricing | deterministic pricing tests |
| 10 | `strategy.tiered` supports flat tier and graduated tier modes | deterministic pricing tests |
| 11 | `strategy.component_sum` supports bundle/service-product package pricing | deterministic pricing tests |
| 12 | `strategy.recurring_plan` supports v1 quote-time recurring plan pricing | deterministic pricing tests |
| 13 | Manual override creates approval requirement and audit event | service/integration test |
| 14 | Discount threshold, below-floor, and below-margin approvals trigger correctly | service tests |
| 15 | PricingSnapshot persists engine version, strategy code, cost source, base inputs, modifiers, approval state, tax, rounding, final totals, gross profit, and margin | snapshot schema test |
| 16 | Snapshot replay reconstructs historical result without querying current catalog/rule data | replay corpus test |
| 17 | Pricing admin preview shows resolver inputs, base calculation, modifier deltas, approval reasons, tax, rounding, and final result | admin/view test |
| 18 | Legacy 41-strategy registry test is removed or replaced | CI |

#### J.5.9 Dependencies

**Entry:** M2 complete.  
**Blocks:** M4 quote builder, M5 fulfillment cost rollups, M6 billing/reporting.

#### J.5.10 Suggested duration

**5–7 calendar weeks.**

#### J.5.11 Risk register

1. **Pricing scope creep reintroduces strategy sprawl.** Mitigation: registry completeness test allows only approved base strategies.
2. **Resolver/strategy boundary gets blurred.** Mitigation: strategies are tested to ensure no DB access.
3. **Snapshots omit critical context.** Mitigation: replay corpus must include service, resale product, manufactured product, bundle, recurring plan, discount, override, and approval cases.
4. **Approval logic hidden inside strategies.** Mitigation: approval policies live in separate service and return explicit approval reasons.
5. **Mixed service/product quote packages become opaque.** Mitigation: component detail preserved internally in snapshot payloads.

#### J.5.12 Decisions Embedded in This Section

- v1 pricing uses 7 reusable base strategies.
- Supplier, BOM, labor rate, and manufactured cost selection are resolver responsibilities.
- Rush, location, complexity, discount, minimum charge, and floor/margin behavior are modifier or approval-policy responsibilities.
- Milestone billing is a billing schedule, not a base pricing strategy.
- PricingSnapshot replay must not depend on current catalog/rule state.

### J.6 M4 — CRM Pipeline

**Status: NORMATIVE.**

#### J.6.1 Goals

Implement the lead-to-acceptance pipeline: Lead, Quote (with versioning), QuoteVersion, QuoteVersionLine, Client, the quote builder service surface, quote retraction with line inheritance and re-pricing, the acceptance flow with client resolution, Tasks, Communications, and DocumentAttachment.

#### J.6.2 Scope

| Reference | Deliverable |
| --- | --- |
| C.1.2 | Lead, LeadContact, LeadLocation models + state machine |
| D.1 | Lead service surface + state transitions |
| D.1.3 | Lead → Quote conversion |
| C.1.3 | Quote, QuoteVersion, QuoteVersionLine, QuoteVersionDiscount models |
| D.2 | Quote builder service surface |
| D.2.2 | Quote send service |
| D.2.3 | Quote retraction with line inheritance and re-pricing |
| C.1.4 | Client, ClientContact, ClientLocation models |
| D.3 | Quote acceptance flow with `ClientResolution` tagged union |
| D.3.3 | Lead → Client field-mapping at acceptance |
| C.1.5 | SalesOrder, SalesOrderLine models |
| D.4.2 | Bundle decomposition at acceptance |
| C.1.6 | Task, TaskLink, Communication, CommunicationLink models |
| D.7 | Task and Communication service surfaces |
| C.1.7 | DocumentAttachment, DocumentAttachmentLink models |
| D.8 | Document attachment service + storage abstraction |
| C.1.15 | EntityNumberSequence + `allocate_number` |
| H.4 | Phase 1 portal screens for Leads, Quotes, Clients, Tasks, Communications |
| C.5.4 | Optimistic concurrency on QuoteVersion (DRAFT only) |
| I.1.4 | Service-layer test coverage for every service in this batch |

#### J.6.3 Out-of-scope

- Fulfillment dispatch worker creating WorkOrder/BuildOrder/PurchaseOrder (M5).
- Invoice and Payment domains (M6).
- Inbound email synchronization (K.10).
- Phase 1 dashboard with KPI rollups (K.8).

#### J.6.4 Exit criteria

| # | Criterion | Verification |
| --- | --- | --- |
| 1 | Lead lifecycle state machine implemented per C.2.1 with property test asserting completeness | property test |
| 2 | Lead → Quote conversion creates Quote container + DRAFT QuoteVersion; no quote lines pre-populated | service test |
| 3 | Quote builder service emits PricingSnapshot for every line via engine from M3 | service test |
| 4 | Quote send rejects if any QuoteVersionLine has a pending PricingApproval | service test |
| 5 | Quote send transitions DRAFT → SENT and enqueues `quote.send_email` outbox | service test |
| 6 | Quote retraction creates successor DRAFT version, deep-copies lines, RE-PRICES each line | service test + property test |
| 7 | Quote-level discount IS copied to successor draft on retraction | service test |
| 8 | Quote acceptance idempotent on (organization_id, idempotency_key) | service test |
| 9 | Acceptance with `mode="create_new"` creates Client + ClientContact (primary) per D.3.3 mapping | service test |
| 10 | Acceptance with `mode="use_existing"` rejects if client_id is not in same org | service test |
| 11 | SalesOrderLine created from each QuoteVersionLine; bundle decomposition produces parent + child SOLs | service test |
| 12 | Acceptance enqueues `sales_order.dispatch_fulfillment` outbox per resulting SOL | service test |
| 13 | Optimistic concurrency: DRAFT QuoteVersion edits with stale `expected_optimistic_version` raise `ConcurrencyConflictError` | service test |
| 14 | Manual price override is sensitive (re-auth required); always triggers PricingApproval | E2E test |
| 15 | Task `block_task` requires `blocked_reason`; CHECK enforced | service test |
| 16 | Communication body is hashed; updates to body fail (immutability) | service test |
| 17 | DocumentAttachment upload validates MIME allowlist + size cap (50MB) | service test |
| 18 | DocumentAttachment download URL re-evaluates capability + tenancy on every call | service test |
| 19 | Number allocation is row-locked; concurrent calls produce sequential numbers | integration test |
| 20 | Phase 1 templates render with capability-aware UI | E2E test |
| 21 | Capability-coverage CI test still passes after M4 routes added | CI |

#### J.6.5 Dependencies

**Entry:** M2 complete (RBAC, audit, outbox). M3 complete (pricing engine).
**Blocks:** M5.

#### J.6.6 Suggested duration

**6–8 calendar weeks** if M4 runs in parallel with M3; otherwise 4–6 weeks if M3 is already complete.

#### J.6.7 Risk register

1. **Quote builder + pricing engine integration glitches.** Mitigation: integration tests; property tests over the builder's input shaping.
2. **Acceptance idempotency under double-click.** Mitigation: service-layer idempotency check on (org, key) BEFORE state mutation; key derived from session+timestamp+version hash.
3. **Bundle decomposition at acceptance creating orphans.** Mitigation: invariant test that every child SOL with `parent_sales_order_line_id` set has its parent in the same SO and same line_type=BUNDLE.

#### J.6.8 Decisions Embedded in This Section

- Quote retraction RE-PRICES inherited lines, never copies snapshots.
- Bundle decomposition at acceptance, not at quote time.
- Acceptance flow uses explicit `ClientResolution` tagged union.

#### J.6.9 Open Questions Deferred to Later Sections

- Quote PDF rendering tooling: M6 (WeasyPrint vs. ReportLab vs. headless-Chromium pinned in M6).
- Inbound email sync: K.10.

---

### J.7 M5 — Fulfillment

**Status: NORMATIVE.**

#### J.7.1 Goals

Implement WorkOrder, PurchaseOrder + PurchaseAllocation + receipt, BuildOrder + BuildBOMSnapshot + BuildLaborEntry + BuildLaborAdjustment + variance reporting, and the fulfillment dispatch worker.

#### J.7.2 Scope

| Reference | Deliverable |
| --- | --- |
| D.4 | Fulfillment dispatch outbox handler `sales_order.dispatch_fulfillment` |
| D.4.4 | SalesOrder status rollup service |
| C.1.12 | WorkOrder model with state machine |
| E.13 | Work Order service surface |
| C.1.12 | PurchaseOrder, PurchaseOrderLine, PurchaseAllocation models |
| E.11 | PO service surface |
| E.11.2 | Allocation invariant enforcement |
| C.1.12 | BuildOrder, BuildBOMSnapshot, BuildLaborEntry, BuildLaborAdjustment models |
| E.12 | BuildOrder service surface |
| E.12.3 | Labor entry append-only with adjustment-row corrections |
| E.12.4 | Build variance computed read-side |
| E.13.3 | WorkOrder completion with `outcome_notes` ≥ 10 chars |
| H.4 | Phase 1 portal screens for WorkOrders, PurchaseOrders, BuildOrders |
| F.2 | Invoice eligibility computation |

#### J.7.3 Out-of-scope

- Invoice and Payment (M6).
- Inventory deduction (K.6).
- Supplier portal/EDI (K.6).
- Recurring service templates (K.6).
- Route optimization, dispatch automation (K.6).

#### J.7.4 Exit criteria

| # | Criterion | Verification |
| --- | --- | --- |
| 1 | `sales_order.dispatch_fulfillment` worker creates WO for SERVICE SOL, BO for MANUFACTURED, PENDING for RESALE, decomposes BUNDLE | service test |
| 2 | Worker is idempotent on (sales_order_line_id) | service test |
| 3 | WO state machine matches C.2.4; property test passes | property test |
| 4 | WO complete with `outcome_notes` shorter than 10 chars raises `CompletionValidationError` | service test |
| 5 | WO complete sets SOL.fulfillment_status=FULFILLED and triggers `recompute_sales_order_status` outbox | service test |
| 6 | PO state machine matches C.2.5; property test passes | property test |
| 7 | PO cancellation prohibited at PART_RECEIVED | service test |
| 8 | Allocation sum invariant enforced at service layer | service test |
| 9 | Receipt update of resale SOL's allocations transitions SOL.fulfillment_status to FULFILLED when total received ≥ SOL.quantity | service test |
| 10 | BO state machine matches C.2.6; property test passes | property test |
| 11 | `start_build` creates immutable BuildBOMSnapshot from active BOM version; estimated costs sourced from PricingSnapshot at acceptance | service test |
| 12 | BuildLaborEntry resolves rate from rate-card active on `occurred_on` | service test |
| 13 | BuildLaborAdjustment uses original entry's applied rate for `internal_cost_delta` | service test |
| 14 | Build variance read-side returns material/labor/total deltas | unit test |
| 15 | SalesOrder status rollup transitions OPEN → IN_FULFILLMENT → FULFILLED | service test |
| 16 | Invoice eligibility transitions per InvoicingPolicy | service test |
| 17 | Bundle eligibility = ALL_COMPONENTS_ELIGIBLE | service test |
| 18 | Capability-coverage CI test passes for new fulfillment routes | CI |

#### J.7.5 Dependencies

**Entry:** M3 + M4 complete.
**Blocks:** M6.

#### J.7.6 Suggested duration

**5–7 calendar weeks.**

#### J.7.7 Risk register

1. **Fulfillment dispatch idempotency.** Outbox retries that re-enter the dispatch handler must not double-create artifacts. Mitigation: explicit "existing artifact?" check at the start of each `create_*_from_sales_order_line`.
2. **Build labor concurrency.** Two technicians recording labor on the same BO concurrently could race on `actual_labor_cost`. Mitigation: `select_for_update` on BuildOrder when recording labor.
3. **Invoice eligibility timing.** A WO completion event firing before SO transitioning out of OPEN can confuse the rollup. Mitigation: `recompute_sales_order_status` always uses outbox; rollup recomputes from authoritative state.

#### J.7.8 Decisions Embedded in This Section

- Fulfillment dispatch always through outbox, never inline.
- Build labor entries are append-only with adjustment rows.
- Variance computed read-side, never stored.

#### J.7.9 Open Questions Deferred to Later Sections

- Inventory tracking: K.6.
- Recurring service templates: K.6.

---

### J.8 M6 — Billing + Reporting

**Status: NORMATIVE.**

#### J.8.1 Goals

Implement Invoice + InvoiceLine + Payment + PaymentAllocation + PaymentAdjustment + tax calculation + accounting adapter pattern (Noop only) + 10 fixed reports + ReportExportJob async export.

#### J.8.2 Scope

| Reference | Deliverable |
| --- | --- |
| C.1.13 | InvoicingPolicy, Invoice, InvoiceLine, Payment, PaymentAllocation, PaymentAdjustment models |
| F.1 | Invoice creation, send, void services |
| F.1.2 | Snapshot-driven invoice math |
| F.1.3 | Bundle invoicing (parent only) |
| F.1.6 | `invoice.overdue_check` daily beat job |
| F.2 | Invoice eligibility services |
| F.3 | Payment recording, allocation, reversal, adjustment services |
| F.3.5 | Overpayment as `unapplied_amount`; no credit-balance entity |
| F.4 | Tax modifier integrated; F.4 surface (jurisdictions, rates, exemption display) |
| F.5 | Accounting adapter Protocol + NoopAccountingAdapter + outbox-driven sync |
| F.6 | 10 fixed reports + `run_report` service + ReportExportJob async path |
| F.6.4 | Export retention (14-day) — `retention_until` field set; prune job in M8 |
| H.4 | Phase 1 portal screens for Invoices, Payments, Reports |
| H.4 | Quote PDF + Invoice PDF rendering (WeasyPrint) |
| C.1.13 | Invoice and Payment numbering via `EntityNumberSequence` |

#### J.8.3 Out-of-scope

- Concrete accounting adapters (QuickBooks, Xero, NetSuite) — K.6.
- Bidirectional accounting sync — K.6.
- Refunds, credit notes, write-offs — K.3.
- Custom report builders — K.8.
- Scheduled report delivery — K.8.
- BI/data-warehouse export — K.8.
- Dashboard KPIs — K.8.
- Multi-currency invoicing — K.5.
- VATIN/EU VAT — K.5.

#### J.8.4 Exit criteria

| # | Criterion | Verification |
| --- | --- | --- |
| 1 | Invoice creation requires every referenced SOL to have `invoice_eligibility=ELIGIBLE` | service test |
| 2 | Partial invoicing scales snapshot pricing proportionally; rounding once on final InvoiceLine | service test |
| 3 | Bundle invoicing presents parent line only on the invoice | service test |
| 4 | Invoice send sets status=SENT and enqueues `invoice.generate_pdf` then `invoice.send_email` | service test |
| 5 | Invoice void rejected if any non-reversed PaymentAllocation exists | service test |
| 6 | `invoice.overdue_check` beat job transitions SENT past due_date to OVERDUE | service test against simulated clock |
| 7 | Payment record idempotent on (org, idempotency_key) | service test |
| 8 | Payment allocation reversal preserves original row with `reversed_at` | service test |
| 9 | Payment.amount NEVER mutated; corrections only via PaymentAdjustment | service test |
| 10 | Overpayment leaves `unapplied_amount > 0`; visible on client account view | E2E test |
| 11 | Tax resolution walks jurisdiction hierarchy bounded to depth 5 | service test |
| 12 | `Client.tax_exempt=True` zeros tax regardless of line.taxable | unit test |
| 13 | Tax-exempt certificate ref appears on quote PDF and invoice PDF | E2E test |
| 14 | Accounting sync outbox entries enqueued after Client/Invoice/Payment commit | service test |
| 15 | NoopAccountingAdapter returns success without external call | unit test |
| 16 | All 10 fixed reports return correct row counts on synthetic multi-tenant fixture | report tests, one per report |
| 17 | Reports < 5000 rows return inline; ≥ 5000 rows queue ReportExportJob | service test |
| 18 | ReportExportJob produces a CSV attachment with `document_kind=EXPORT_ARCHIVE`, `retention_until = created_at + 14 days` | integration test |
| 19 | Quote PDF and Invoice PDF render with WeasyPrint | E2E test |
| 20 | Capability-coverage CI test passes for new billing/reporting routes | CI |

#### J.8.5 Dependencies

**Entry:** M5 complete.
**Blocks:** M7.

#### J.8.6 Suggested duration

**5–6 calendar weeks.**

#### J.8.7 Risk register

1. **PDF rendering parity.** WeasyPrint renders CSS differently than browsers. Mitigation: dedicated print stylesheet from day one; visual diff against reference PDFs in CI.
2. **Tax hierarchy correctness on edge cases.** Mitigation: depth-bounded ancestor walk + property test.
3. **Report query performance on real data shapes.** Mitigation: every report benchmarked on synthetic 10k-quote tenant in CI.

#### J.8.8 Decisions Embedded in This Section

- WeasyPrint locked as PDF rendering engine in v1.
- Invoice math reads directly from SOL's snapshot, never recomputes.
- Reports as Python functions, not stored procs.

#### J.8.9 Open Questions Deferred to Later Sections

- Refund domain: K.3.
- Custom report builders: K.8.
- Concrete accounting adapters: K.6.

---

### J.9 M7 — Custom Tenant Admin, Domain Admin Workflows + Data Lifecycle

**Status: NORMATIVE.**

#### J.9.1 Goals

Implement the custom tenant admin site for organization administrators, including member invites, role/scope assignments, capability grants, numbering config, invoicing policy, tax config, audit search, tenant data export, and tenant deletion flow with 30-day grace period.

M7 completes the domain-organized custom tenant admin model: admin screens are grouped by business domain, owned by their domain apps, and implemented as custom Django views. M7 also ensures that each domain has enough tenant-facing templates to test the user experience before Phase 2 React. The base Django admin MUST NOT be required for tenant administration.

#### J.9.2 Scope

| Reference | Deliverable |
| --- | --- |
| H.7 | Custom tenant admin site shell and domain-grouped navigation |
| H.7 | Custom admin workflow coverage for each v1 domain |
| H.8 | Shared styling applied to custom admin and tenant-facing templates |
| H.7 | Domain-owned admin views/forms/navigation metadata |
| H.4 | Phase 1 tenant admin portal screens |
| B.6 | Member invite workflow + invite token (signed; 7-day expiry; single-use) |
| B.6 | Role assignment + scope assignment + capability-grant overrides UIs |
| G.5.8 | Audit search service + Phase 1 audit search UI |
| G.7.2 | TenantExportRequest model + service + `tenant.export.assemble` worker |
| G.7.2 | Export archive layout (gzipped tar with JSONL + CSV mirrors + attachments) |
| G.7.3 | TenantDeletionRequest model + service + 30-day grace + beat-driven `tenant.deletion.execute` worker |
| G.7.3 | Pre-deletion read-only state during grace period |
| C.4.2 | Cascade rules for tenant deletion |
| F.5.4 | Org-settings page exposes accounting_adapter_code + accounting_adapter_config (encrypted) |

#### J.9.3 Out-of-scope

- Base Django admin as a tenant administration surface.
- Cross-region audit shipping (K.9).
- Per-user data subject requests (K.9).
- Cross-tenant legal-hold export (K.9).
- Audit retention pruning (M8).
- Self-service org signup (K.4).
- Parent/child client account hierarchy (K.4).

#### J.9.4 Exit criteria

| # | Criterion | Verification |
| --- | --- | --- |
| 1 | Custom tenant admin home at `/admin/` on tenant subdomain renders domain-grouped navigation | E2E test |
| 2 | Tenant admin navigation is grouped by Organization, CRM, Catalog, Operations, Billing, Reporting, Security/Audit | manual + view test |
| 3 | Domain apps own their own admin views/forms/services/navigation metadata | architecture review |
| 4 | No tenant admin workflow relies on base Django admin | review |
| 5 | Member invite creates Membership with status=INVITED and `invitation_token_hash` set; outbox enqueues invite email | service test |
| 6 | Invite acceptance creates User (or links existing) and transitions Membership to ACTIVE; MFA enrollment gate enforced | E2E test |
| 7 | Role assignment, scope assignment, and capability grant UIs require sensitive-action re-auth | E2E test |
| 8 | DENY-beats-GRANT semantics visible in custom tenant admin UI when a grant is created | manual + service test |
| 9 | Catalog/pricing admin screens are under Catalog/Pricing navigation | view test |
| 10 | Organization/member/role admin screens are under Organization navigation | view test |
| 11 | Audit search service requires `admin.audit.view` capability; search emits its own DATA_ACCESS audit row | service test |
| 12 | Audit search supports filters: event_type, actor_id, object_kind, object_id, date range; results paginated | E2E test |
| 13 | TenantExportRequest with `requested_scope=FULL` produces archive containing all org-scoped tables in JSONL + CSV mirrors + attachments | integration test against synthetic tenant |
| 14 | Export archive `output_attachment` has `retention_until = now() + 14 days`; status transitions QUEUED → ASSEMBLING → READY → EXPIRED | service test |
| 15 | Export download requires sensitive re-auth; emits TENANT_EXPORT_DOWNLOADED audit per download | E2E test |
| 16 | TenantDeletionRequest requires confirmation phrase = org slug; mismatched phrase rejects | service test |
| 17 | TenantDeletionRequest sets Organization.status=OFFBOARDING and enters 30-day GRACE_PERIOD | service test |
| 18 | During GRACE_PERIOD, mutations on tenant data are blocked (read-only mode); exports still allowed | E2E test |
| 19 | Cancellation during grace period restores Organization.status=ACTIVE | service test |
| 20 | `tenant.deletion.execute_due` beat job picks up GRACE_PERIOD requests where `grace_period_ends_at < now` | service test |
| 21 | Execution worker hard-deletes tenant-owned rows in dependency order; preserves Organization tombstone, AuditEvent, ImpersonationAuditLog | integration test |
| 22 | Object-store binaries for deleted tenant's DocumentAttachments removed | integration test |
| 23 | Reminder emails sent on day 1, 7, 25, 28, 29 of grace period | service test against simulated clock |
| 24 | Capability-coverage CI test passes for custom tenant admin routes | CI |

#### J.9.5 Dependencies

**Entry:** M6 complete.
**Blocks:** M8.

#### J.9.6 Suggested duration

**4–5 calendar weeks.**

#### J.9.7 Risk register

1. **Admin navigation becomes a second model registry.** Mitigation: domain-owned navigation metadata and business-domain grouping, not alphabetical Django app/model discovery.
2. **Export archive memory blow-up.** A tenant with 10GB of attachments and 1M audit events cannot be assembled in-memory. Mitigation: streaming JSONL writers, attachment streaming directly from object store to tar.
3. **Deletion cascade ordering bugs.** Mitigation: dependency order is data; test that runs deletion against a fully-populated synthetic tenant and asserts zero orphans + zero remaining rows except preserved tombstones.
4. **Grace-period read-only enforcement gaps.** Mitigation: middleware-level gate that blocks all mutating views when `request.tenant_organization.status == "OFFBOARDING"`, with explicit allowlist for export/cancel actions.
5. **Base Django admin leaks into workflows.** Mitigation: capability coverage and architecture review verify tenant admin workflows use custom views and service-layer functions.

#### J.9.8 Decisions Embedded in This Section

- M7 ships the custom tenant admin site and domain admin workflows, not base Django admin customization.
- M7 verifies tenant-facing domain templates exist for user-perspective testing.
- M7 preserves the Phase 1 templates as the React parity source for M9.
- Admin navigation is grouped by business domain.
- Domain apps own their models, services, forms, admin views, and navigation metadata.
- Export archive is gzipped tar with JSONL + CSV mirrors.
- Tenant deletion is beat-driven, not button-driven.
- Reminder emails on curated cadence.

#### J.9.9 Open Questions Deferred to Later Sections

- Cross-tenant legal-hold export: K.9.
- Per-user data subject requests: K.9.

---

### J.10 M8 — Production Readiness

**Status: NORMATIVE.**

#### J.10.1 Goals

M8 makes the v1 build production-ready using the non-Kubernetes DigitalOcean/Docker deployment model.

M8 validates:

- deployability,
- rollback,
- backups,
- restore drill,
- observability,
- security controls,
- OAuth/OIDC production readiness,
- MFA production readiness,
- worker/beat reliability,
- pricing snapshot replay,
- anonymized staging refresh,
- runbook completeness,
- load-test readiness.

#### J.10.2 Scope

| Reference | Deliverable |
| --- | --- |
| G.4.5 | Sentry SDK integration with structured-log context propagation |
| G.4.6 | OpenTelemetry SDK installed; logs exporter wired; metrics/traces SDK present with no-op exporter |
| G.4.9 | Initial alert thresholds configured |
| G.5.6 | `audit.retention_prune` daily beat job |
| F.6.4 | `attachment.retention_prune` daily beat job |
| G.3.5 | Beat-only scheduled jobs wired and verified |
| G.3.5 | Exactly one beat container per environment |
| I.4 | Docker-based production deployment on DigitalOcean |
| I.4 | Production Docker image build and registry push |
| I.4 | `compose.prod.yml` for web, worker, beat, reverse proxy, Redis, optional pgBouncer |
| I.4 | Migration-before-deploy workflow |
| I.4 | Rollback workflow using previous image tag |
| I.4 | Production secret injection outside Git |
| I.4 | `/healthz` and `/readyz` endpoints used by deploy smoke tests |
| B.4 | Production OAuth/OIDC callback URLs configured |
| B.4 | Production OAuth/OIDC provider validation verified |
| B.4 | Trusted external MFA decision reviewed |
| B.5 | OAuth/OIDC account takeover protections verified |
| B.5 | Local MFA recovery process verified |
| I.5.2 | Automated daily backups + WAL/PITR-equivalent recovery + weekly archives |
| I.5.5 | First restore drill executed against staging |
| I.3.3 | Production → staging anonymization pipeline scheduled and running weekly |
| I.3.4 | Demo environment refresh job scheduled weekly |
| G.6 | Security review: TLS, CSP, rate limits, file upload validation, dependency scan, host hardening |
| docs/runbooks | Deploy, rollback, restore, secret rotation, incident response, worker failure, beat failure runbooks |
| Load test | k6 suite covering auth, OAuth/OIDC callback, MFA, quote send, pricing preview, payment record, report run |

#### J.10.3 OAuth/OIDC production readiness

Before launch, each production OAuth/OIDC provider MUST pass a security checklist:

| Check | Requirement |
| --- | --- |
| Provider enabled intentionally | `OAuthProviderConfig.is_active=true` only after review |
| Callback URL | Exact root-domain production callback configured |
| Client ID | Loaded from approved config |
| Client secret | Loaded from secret source; absent from Git |
| HTTPS | Required for login and callback |
| State validation | Verified |
| Nonce validation | Verified for OIDC |
| ID token signature | Verified for OIDC |
| Issuer/audience | Verified |
| Email verification | Enforced unless explicitly waived |
| Domain restriction | Enforced if configured |
| Account linking | Verified against takeover cases |
| Provider MFA trust | Explicitly approved or local MFA required |
| Logging | No authorization codes, tokens, secrets, TOTP secrets, or recovery codes in logs |

#### J.10.4 MFA production readiness

Before launch:

1. Local MFA enrollment works.
2. TOTP challenge works.
3. Recovery codes work.
4. Recovery codes are single-use.
5. Recovery-code regeneration invalidates old codes.
6. Support users cannot bypass MFA.
7. OAuth/OIDC users without trusted provider MFA receive local step-up MFA.
8. Sensitive-action re-auth works for password and OAuth/OIDC users.
9. MFA reset/recovery support runbook exists.
10. MFA-related audit events are emitted.

#### J.10.5 Out-of-scope

- Kubernetes deployment.
- Helm charts.
- Kubernetes migration Jobs.
- Kubernetes Secrets or SealedSecrets.
- Kubernetes ingress.
- cert-manager.
- HPA.
- Cluster autoscaling.
- Blue-green deployment through traffic splitting.
- Canary deployment through traffic weighting.
- Multi-region production deployment.
- Read replica routing unless needed before launch.
- Tenant-managed custom identity providers.
- SAML.
- SCIM.
- Provider group-to-role mapping.
- Passkeys-only login.

These belong in the future scalability appendix.

#### J.10.6 Exit criteria

| # | Criterion | Verification |
| --- | --- | --- |
| 1 | Sentry receives a test event with full structured-log context | manual |
| 2 | OpenTelemetry SDK initialized; structured logs flow to log sink | manual |
| 3 | Initial alerts from G.4.9 configured and tested | runbook record |
| 4 | `audit.retention_prune` runs daily and respects retention categories | integration test |
| 5 | `attachment.retention_prune` deletes expired object-store binaries | integration test |
| 6 | Production Docker image builds from CI and is tagged with Git SHA | CI |
| 7 | Production host pulls and runs image through `compose.prod.yml` | runbook record |
| 8 | Deployment runs migrations before restarting services | deploy log |
| 9 | `/readyz` passes after deploy | smoke test |
| 10 | Rollback to prior image tag succeeds without reverse migrations | rollback drill |
| 11 | Exactly one beat container runs in each environment | deploy verification |
| 12 | Beat-triggered jobs are idempotent or lock-protected | integration tests |
| 13 | Worker consumes a test outbox entry after deploy | smoke test |
| 14 | pgBouncer is configured or explicitly deferred with connection-count justification | architecture review |
| 15 | No plaintext production secrets exist in Git | grep audit + manual review |
| 16 | Production secrets load from approved external source | deploy verification |
| 17 | OAuth/OIDC client secrets absent from image and Git | secret scan |
| 18 | Production OAuth/OIDC callback URL works over HTTPS | manual + integration test |
| 19 | OAuth/OIDC login validates state, nonce, issuer, audience, signature, and expiry | integration test |
| 20 | Unverified provider email cannot link to an existing user | security test |
| 21 | Trusted external MFA provider decision documented | security review |
| 22 | Untrusted provider requires local step-up MFA | integration test |
| 23 | Support user MFA works through all enabled login paths | integration test |
| 24 | Handoff signing key rotation runbook exists and has been tested | runbook record |
| 25 | Project-level encryption key rotation runbook exists | runbook record |
| 26 | TLS 1.2+ only; TLS 1.3 supported where available | SSL test |
| 27 | CSP enforced in production | browser/security test |
| 28 | Rate limits verified for password, MFA, OAuth/OIDC, and handoff endpoints | test report |
| 29 | Dependency vulnerability scan fails CI on HIGH/CRITICAL CVEs unless waived | CI |
| 30 | Container image runs as non-root or exception approved | image inspection |
| 31 | Host firewall allows only required ports | ops checklist |
| 32 | Quarterly restore drill executed; RTO ≤ 4h and RPO ≤ 1h verified | runbook record |
| 33 | Anonymization pipeline produces usable staging data from recent production backup | integration test |
| 34 | Pricing snapshot replay corpus passes against deployed staging build | CI/staging |
| 35 | Load test targets met for auth, OAuth/OIDC login, MFA, quote send, pricing preview, invoice list, and report export | k6 run |
| 36 | All runbooks reviewed and executed by an engineer other than the author | runbook records |
| 37 | First production deploy executed through documented manual approval workflow | runbook record |

#### J.10.7 Dependencies

**Entry:** M7 complete.  
**Blocks:** v1 launch.

#### J.10.8 Suggested duration

**3–5 calendar weeks.**

#### J.10.9 Risk register

1. **OAuth/OIDC callback misconfiguration blocks login.** Mitigation: staging and production callback verification before launch.
2. **Account takeover through unsafe email linking.** Mitigation: verified email requirement, linking tests, security review.
3. **Provider MFA is trusted without enforcement.** Mitigation: explicit provider review and `trust_external_mfa` flag.
4. **Local MFA recovery flow locks out legitimate users.** Mitigation: recovery-code flow, support runbook, audited reset process.
5. **Secrets leak through image or deploy files.** Mitigation: secret scan, env-based config, restricted host permissions.
6. **Docker host becomes a single point of failure.** Mitigation: managed Postgres/Redis where feasible, backups, restore drill, rebuild procedure.
7. **Migrations fail during production deploy.** Mitigation: migration safety lint, staging rehearsal, backward-compatible migrations.
8. **Beat accidentally runs twice.** Mitigation: one beat service in Compose, deploy verification, idempotent scheduled jobs.
9. **Load test reveals connection exhaustion.** Mitigation: enable pgBouncer and tune Gunicorn/Celery concurrency.

#### J.10.10 Decisions Embedded in This Section

- v1 production deployment is Docker-based on DigitalOcean.
- Kubernetes is deferred.
- OAuth/OIDC production readiness is part of launch readiness.
- django-allauth remains the v1 authentication integration layer.
- Root-domain OAuth/OIDC login flows into existing tenant handoff.
- Provider MFA may satisfy MFA only when explicitly trusted.
- Local step-up MFA is required when provider MFA is not trusted.
- Membership/RBAC/RML remain authoritative for tenant authorization.
- Production secrets remain outside source control.

### J.11 M9 — Phase 2 React Portal (post-v1)

**Status: NORMATIVE for the contract; INFORMATIVE for sprint-level scoping.**

#### J.11.1 Goals

After v1 is stable in production, build the DRF-based internal API and the custom React tenant portal. Replace Phase 1 server-rendered tenant-portal screens domain-by-domain. Retain Phase 1 for login, account, platform console, support tooling, and email templates.

#### J.11.2 Scope

| Reference | Deliverable |
| --- | --- |
| H.6 | Full DRF internal API surface per H.6.11 |
| H.6.9 | drf-spectacular OpenAPI schema generation; committed schema CI-validated |
| H.6.3 | SessionAuthentication-only |
| H.6.4 | TenantScopedQuerysetMixin + CapabilityRequiredMixin |
| H.6.6 | Cursor pagination by default; offset for known-small endpoints |
| H.6.10 | API rate limiting (60/user/min mutations, 600/user/min reads) |
| H.5 | React portal (framework selected at design sprint) |
| H.5.5 | Per-domain cutover with feature flags `react_portal.{domain}` |
| docs | Phase 1 retirement criteria + retirement playbook |
| docs | TypeScript SDK generation from OpenAPI |
| CI | Schema diff / breaking-change CI gate |
| docs | Component documentation surface |

#### J.11.3 Out-of-scope

- Public/external API (K.11).
- Webhook emitters (K.11).
- Native mobile applications (K.13).

#### J.11.4 Exit criteria

| # | Criterion | Verification |
| --- | --- | --- |
| 1 | DRF API exposes every endpoint in H.6.11 with documented capability requirements | OpenAPI schema review |
| 2 | OpenAPI schema committed to source control; CI fails on drift | CI test |
| 3 | Schemathesis fuzzing passes against the API in CI | CI |
| 4 | Cookie-bound auth: API rejects requests without tenant-local session cookie | API test |
| 5 | API throttling returns 429 with `Retry-After` at the documented limits | API test |
| 6 | React app loads on `{slug}.mypipelinehero.com/` for feature-flagged domains | manual |
| 7 | Capability-aware UI loads capabilities once via `GET /api/v1/me/capabilities` and caches for the session | manual |
| 8 | Impersonation banner renders in React when `X-Impersonating: true` | manual |
| 9 | First domain (Quotes) cut over to React with feature parity vs. Phase 1 | parity test suite |
| 10 | Each subsequent domain cut over only after parity test suite passes | per-domain |
| 11 | Phase 1 templates retired only after 30 days of React-domain stability | retrospective |

#### J.11.5 Dependencies

**Entry:** M8 complete; v1 in production for at least 60 days with stable error rates.
**Blocks:** Public API (K.11) and any React-dependent integrations.

#### J.11.6 Suggested duration

**Ongoing post-v1.** Initial DRF API + first domain cutover: 8–12 weeks. Subsequent domains: 2–4 weeks each. Phase 1 retirement when feature parity complete: 6–12 months elapsed.

#### J.11.7 Risk register

1. **Phase 1 / Phase 2 coexistence drift.** Mitigation: every state-changing operation goes through the service layer; the layer is shared.
2. **OpenAPI schema drift.** Mitigation: codegen from committed OpenAPI; CI gate on schema drift.
3. **Capability-cache staleness.** Mitigation: capability changes invalidate the session.

#### J.11.8 Decisions Embedded in This Section

- Per-domain cutover, not big-bang.
- Phase 1 retirement gated by 30-day stability per domain.
- TypeScript SDK generated from OpenAPI, not hand-written.

#### J.11.9 Open Questions Deferred to Later Sections

- React framework selection: pre-M9 design sprint.
- TypeScript SDK distribution mechanism: design sprint.

---

### J.12 Cross-Milestone Considerations

**Status: NORMATIVE.**

#### J.12.1 Parallelism

The dependency graph (J.1.4) explicitly permits M3 + M4 to run in parallel. Other milestones MUST run sequentially. Implicit parallelism is PROHIBITED.

#### J.12.2 Code review at milestone boundaries

At every milestone boundary:

1. **Architecture review.** A senior engineer outside the milestone's primary contributors reviews NORMATIVE changes for architectural drift.
2. **Security review.** Security reviewer checks for new attack surfaces (especially M1, M2, M7, M8).
3. **Performance review.** A performance-conscious engineer checks for new N+1 query risks, missing indexes, unbounded queryset patterns.
4. **Documentation review.** Product/PM reviews user-facing impact and runbook updates.

Architecture review is blocking. Security review is blocking for M1/M2/M7/M8. Performance review is blocking for M3/M5/M6/M8. Documentation review is non-blocking but creates follow-up tickets.

#### J.12.3 Milestone-skipping rules

A milestone MAY NOT be skipped. A milestone MAY have its scope reduced under J.12.5.

- M0 cannot be skipped (no project).
- M1 cannot be skipped (no tenants, no users).
- M2 cannot be skipped (no enforcement scaffolding, no audit).
- M3 cannot be skipped (no pricing engine, no quote math).
- M4 cannot be skipped (no commercial pipeline).
- M5 cannot be skipped (no fulfillment, no invoicing trigger).
- M6 cannot be skipped (no billing, no revenue).
- M7 cannot be skipped (no custom tenant self-administration).
- M8 cannot be skipped (no production launch).
- M9 may be deferred indefinitely (Phase 2 is post-v1).

#### J.12.4 Scope-cutting playbook

If a milestone is at risk of slipping, scope is cut in this priority order:

1. **Cut frontend polish first.** Reduce visual fidelity; ship functional but unpolished screens.
2. **Cut nice-to-have reports.** The 10-report catalog is the v1 bar; specific reports may slip to a post-v1 patch.
3. **Cut secondary state-machine paths.**
4. **Cut secondary admin UI.**
5. **NEVER cut tenant isolation.** No exceptions.
6. **NEVER cut audit logging.** No exceptions.
7. **NEVER cut RBAC enforcement.** No exceptions.
8. **NEVER cut the snapshot replay corpus or the corpus CI gate.** No exceptions.
9. **NEVER cut the tenant-isolation CI test.** No exceptions.
10. **NEVER cut the capability-coverage CI test.** No exceptions.

The "NEVER cut" list is the irreducible safety floor of v1.

#### J.12.5 Cuts produce K.1 entries

Every milestone-scope cut produces a K.1 entry. Without this, cuts disappear into the backlog and are never picked up. The retrospective is the forcing function.

#### J.12.6 Decisions Embedded in This Section

- M3 + M4 parallelism is the only sanctioned parallelism in v1.
- Architecture review is blocking at every milestone boundary.
- The "NEVER cut" list is irreducible.
- Every cut produces a K.1 entry.

#### J.12.7 Open Questions Deferred to Later Sections

- None. This is the binding roadmap.

---

---

## Part K — Deferred / Out-of-v1 Catalog

### K.1 Format Conventions

**Status: NORMATIVE.**

#### K.1.1 Purpose

Part K is the registry of every "we'll do that later" promise made in batches 1–5. It is the contract about what is explicitly NOT in v1, why it isn't, what v1 already does to accommodate the future implementation, and what target version it lands in.

A deferred item without a K.1 entry is an implicit decision (prohibited per A.2.10). When a new deferral is identified, a guide PR adds a K.1 entry in the same change.

#### K.1.2 Entry format

| Field | Meaning |
| --- | --- |
| **Name** | Short, distinctive name of the feature |
| **Description** | One paragraph: what the feature does |
| **Motivation** | One paragraph: who wants this and why |
| **v1 accommodation** | What v1 already does to make a future implementation cheap |
| **Prerequisites** | Other K.1 items or v1 work that MUST land first |
| **Affected sections** | Guide sections that will be amended when the item is built |
| **Effort tier** | S (≤2 weeks) / M (2–6 weeks) / L (6–12 weeks) / XL (12+ weeks) |
| **Target version** | "v1.5" / "v2" / "v3+" |

Effort tiers are calibrated against the team-size assumption in J.1.5.

#### K.1.3 Re-entry to the guide

When a deferred item is built:

1. The K.1 entry is REMOVED from this section in the guide PR that ships the feature.
2. The affected NORMATIVE sections are AMENDED.
3. The entry's removal and the amendment are noted in the changelog with the version bump.

#### K.1.4 Decisions Embedded in This Section

- Every deferred decision MUST appear in K.1.
- Removed K.1 entries are tracked via git history; resurrected deferrals re-enter as new entries.

---

### K.2 Pricing Extensions

#### K.2.1 Standalone PriceList strategy

| Field | Value |
| --- | --- |
| Description | A pricing strategy that selects a unit price directly from a PriceList without requiring an active ClientContractPricing — i.e., "use this price list for this product line type for this tenant" without binding to a specific client. |
| Motivation | Some tenants want public-facing price lists (catalog pricing) that apply to all clients, not contract-specific lists. v1 forces all PriceList use through ClientContractPricing. |
| v1 accommodation | The PriceList model and PriceListItem model already exist. Standalone public price lists can be implemented through `strategy.fixed_price` plus price-list resolver semantics rather than a new base strategy. |
| Prerequisites | None. |
| Affected sections | E.3.3, E.6 |
| Effort tier | S |
| Target version | v1.5 |

#### K.2.2 Bundle-of-bundles

| Field | Value |
| --- | --- |
| Description | BundleDefinition components that reference other BundleDefinitions, allowing nested bundles. |
| Motivation | Tenants with hierarchical service offerings ("Platinum Package contains Gold Package + extras") need composition without flattening. |
| v1 accommodation | BundleComponent has FK to Service or Product but not to BundleDefinition. Adding the FK is a migration; the decomposition logic at acceptance (D.4.2) needs to recurse. |
| Prerequisites | None. |
| Affected sections | C.1.10, E.4.3, D.4.2 |
| Effort tier | M |
| Target version | v2 |

#### K.2.3 Multiple stacking promotions

| Field | Value |
| --- | --- |
| Description | Allow more than one eligible PromotionCampaign to apply to the same line, with explicit stacking rules (additive percent, multiplicative, etc.). |
| Motivation | Tenants with running promotions plus loyalty campaigns hit lines eligible for both; v1 picks only the highest-priority. |
| v1 accommodation | The promotion modifier (E.7.7) is the only place this logic lives. PromotionUsage tracks eligibility caps. |
| Prerequisites | None. |
| Affected sections | E.7.7, E.4.2 |
| Effort tier | M |
| Target version | v2 |

#### K.2.4 Success-fee invoicing for outcome-based services

| Field | Value |
| --- | --- |
| Description | When a future `strategy.value_outcome` or equivalent value/outcome pricing mode is added, the success-fee component becomes invoiceable when the outcome metric is met, post-delivery. |
| Motivation | Outcome-based pricing requires a deferred invoice for the success fee; v1 only invoices the base fee. |
| v1 accommodation | PricingSnapshot can retain outcome-related fields inside `base_inputs` if manually captured, but no value/outcome base strategy is registered in v1. |
| Prerequisites | Refund-or-credit-balance work (K.3.2) helps but is not strictly required. |
| Affected sections | E.6, E.10, F.1, F.2 |
| Effort tier | L |
| Target version | v2 |

#### K.2.5 Tenant-managed UoM

| Field | Value |
| --- | --- |
| Description | Tenants can define their own units of measure beyond the 21 v1 enum values; potentially with conversion factors. |
| Motivation | Specialized industries have unit conventions outside the v1 set. |
| v1 accommodation | The UoM field on catalog items and quote lines is a TEXT column, not a hard enum at the DB layer. The enum lives at the form/API boundary. |
| Prerequisites | UoM conversion logic decision. |
| Affected sections | E.1.3, C.1.8 |
| Effort tier | M |
| Target version | v2 |

#### K.2.6 Service variants / options

| Field | Value |
| --- | --- |
| Description | Services can have variants (small/medium/large; in-shop vs. on-site) without modeling each as a separate Service. |
| Motivation | Tenants currently duplicate Service rows for each variant; quote builder UX suffers. |
| v1 accommodation | None directly. The CONFIGURABLE bundle pattern is similar but heavier. |
| Prerequisites | None. |
| Affected sections | E.1, C.1.8, E.6 |
| Effort tier | L |
| Target version | v2 |

#### K.2.7 BOM clone-to-new-version UX

| Field | Value |
| --- | --- |
| Description | A one-click action to clone an ACTIVE BOMVersion into a new DRAFT, copying all lines for editing. |
| Motivation | Operators currently must create a draft and re-add every line; clunky for products with 50+ BOM lines. |
| v1 accommodation | The data model supports it; this is purely a UX/service layer addition. |
| Prerequisites | None. |
| Affected sections | E.2, H.4 |
| Effort tier | S |
| Target version | v1.5 |

---

### K.3 Billing Extensions

#### K.3.1 Refund domain

| Field | Value |
| --- | --- |
| Description | First-class refund records that return funds to the client and reduce reported revenue. |
| Motivation | Real-world tenant operations require refunds; v1's "out of scope" stance forces operators to issue refunds outside the system. |
| v1 accommodation | PaymentAdjustment (REVERSAL/CORRECTION) handles correction cases; PaymentAllocation reversal handles unwinding allocations. |
| Prerequisites | Credit-balance entity (K.3.2). |
| Affected sections | F.3, C.1.13, G.5 |
| Effort tier | L |
| Target version | v2 |

#### K.3.2 Credit-balance entity

| Field | Value |
| --- | --- |
| Description | A first-class CreditBalance entity that tracks unapplied client credit, replacing v1's `Payment.unapplied_amount` accumulation. |
| Motivation | Tracking credit across multiple Payments via `unapplied_amount` is workable for v1 but doesn't scale. |
| v1 accommodation | `Payment.unapplied_amount` is accessible via client account view. Migration path: a CreditBalance can be created with `source_payment_id` references for backwards compatibility. |
| Prerequisites | None. |
| Affected sections | C.1.13, F.3 |
| Effort tier | M |
| Target version | v2 |

#### K.3.3 Partial bundle invoicing

| Field | Value |
| --- | --- |
| Description | Allow per-component partial invoicing within a bundle (currently only parent-level partial invoicing). |
| Motivation | Tenants with bundles where components fulfill on different timelines want to invoice as components complete. |
| v1 accommodation | None — v1 explicitly limits bundle invoicing to the parent line. |
| Prerequisites | UI design for per-component invoice presentation. |
| Affected sections | F.1.3, H.4 |
| Effort tier | M |
| Target version | v2 |

#### K.3.4 Per-line eligibility overrides

| Field | Value |
| --- | --- |
| Description | Allow a specific SOL to override the InvoicingPolicy's eligibility rule. |
| Motivation | Edge cases where the org-wide policy doesn't fit a specific deal. |
| v1 accommodation | `manual_release_for_invoicing` (F.2.3) covers most cases. |
| Prerequisites | None. |
| Affected sections | C.1.5, F.2 |
| Effort tier | S |
| Target version | v1.5 |

#### K.3.5 Partial-cancel of PART_RECEIVED POs

| Field | Value |
| --- | --- |
| Description | Allow cancellation of remaining quantity on a PO line that has had partial receipts. |
| Motivation | Operators currently have to reconcile manually if a supplier partial-ships then cancels the rest. |
| v1 accommodation | The PO state machine prohibits this; manual reconciliation outside the system. |
| Prerequisites | None. |
| Affected sections | E.11.5, C.2.5 |
| Effort tier | M |
| Target version | v2 |

---

### K.4 Identity Extensions

#### K.4.1 WebAuthn / passkeys

| Field | Value |
| --- | --- |
| Description | Phishing-resistant authentication via WebAuthn (passkeys, hardware keys). |
| Motivation | TOTP is phishable; passkeys are not. Higher-trust deployments want strong auth. |
| v1 accommodation | The User model has TOTP fields; adding WebAuthn credential records is purely additive. |
| Prerequisites | None. |
| Affected sections | B.3.2, B.4.2, H.3.4, H.3.5 |
| Effort tier | M |
| Target version | v2 |

#### K.4.2 "Remember this device"

| Field | Value |
| --- | --- |
| Description | Skip 2FA challenge for trusted devices for N days, with an explicit "trust this device" checkbox at challenge time. |
| Motivation | UX: users on their daily-driver laptop are tired of TOTP at every login. |
| v1 accommodation | None — v1 challenges 2FA on every login. |
| Prerequisites | None. |
| Affected sections | B.4.1, B.4.2, B.5 |
| Effort tier | M |
| Target version | v1.5 |

#### K.4.3 Self-service org signup

| Field | Value |
| --- | --- |
| Description | A signup flow that lets a new prospect create an Organization without an invite. |
| Motivation | Removes manual onboarding friction for self-service-first sales motion. |
| v1 accommodation | `services.create_organization` is the service-layer entry point; v1 only exposes it via platform admin. |
| Prerequisites | Self-service billing if monetized. |
| Affected sections | B.1, H.3 |
| Effort tier | L |
| Target version | v2 |

#### K.4.4 Parent/child client account hierarchy

| Field | Value |
| --- | --- |
| Description | A Client may have a `parent_client_id`, modeling enterprise customers with multiple subsidiaries. |
| Motivation | Tenants with national/international clients want consolidated views and shared contracts. |
| v1 accommodation | None. Each Client is currently flat. |
| Prerequisites | Reporting changes for hierarchical roll-ups. |
| Affected sections | C.1.4, D.6, F.6, E.3.4 |
| Effort tier | L |
| Target version | v2 |

---

### K.5 Currency / FX / Tax Extensions

#### K.5.1 Multi-currency invoicing within a single org

| Field | Value |
| --- | --- |
| Description | An organization can issue invoices in multiple currencies (e.g., USD for US clients, CAD for Canadian clients), with FX-rate sourcing. |
| Motivation | Cross-border tenants need this. |
| v1 accommodation | `Organization.base_currency_code` is single; PricingSnapshot, Invoice, and SalesOrder carry `currency_code`; the currency modifier slot exists at pipeline step 22 but raises if `target_currency_code` set. |
| Prerequisites | FX rate sourcing decision. |
| Affected sections | B.1.2, C.1.10, E.7.15, F.1, F.4 |
| Effort tier | XL |
| Target version | v2 |

#### K.5.2 FX rate sourcing

| Field | Value |
| --- | --- |
| Description | Integration with an FX rate provider to source rates for currency conversion. Rates are snapshotted onto PricingSnapshot for replay determinism. |
| Motivation | Required by K.5.1. |
| v1 accommodation | The PricingContext has `fx_rate` and `target_currency_code` fields reserved but unused. |
| Prerequisites | None directly; pairs with K.5.1. |
| Affected sections | E.5.2, C.1.10 |
| Effort tier | M |
| Target version | v2 |

#### K.5.3 VATIN / EU VAT

| Field | Value |
| --- | --- |
| Description | EU VAT compliance: VATIN validation, reverse-charge handling, VAT-MOSS reporting. |
| Motivation | EU tenants and tenants selling into the EU. |
| v1 accommodation | TaxJurisdiction supports hierarchical jurisdictions; TaxRate supports per-line-type filtering; Client has `tax_exempt` flag. |
| Prerequisites | None directly. |
| Affected sections | C.1.11, F.4, F.6 |
| Effort tier | L |
| Target version | v2 |

#### K.5.4 Tax-exempt certificate document upload integration

| Field | Value |
| --- | --- |
| Description | Operators upload a tax-exemption certificate document; the certificate ref on Client links to a DocumentAttachment. |
| Motivation | Audit-friendly handling of exemption certificates. |
| v1 accommodation | `Client.tax_exempt_certificate_ref` is a TEXT field; DocumentAttachment domain exists. |
| Prerequisites | None. |
| Affected sections | C.1.4, D.8, F.4.5 |
| Effort tier | S |
| Target version | v1.5 |

---

### K.6 Operations Extensions

#### K.6.1 Concrete accounting adapters (QuickBooks, Xero, NetSuite)

| Field | Value |
| --- | --- |
| Description | Implementations of `AccountingAdapter` for popular accounting systems, syncing Client / Invoice / Payment one-way from MPH to the external system. |
| Motivation | Customers using these tools want their financial records mirrored. |
| v1 accommodation | The adapter Protocol, registry, NoopAccountingAdapter, and outbox-driven sync pattern all exist. |
| Prerequisites | Per-tenant adapter configuration UI. |
| Affected sections | F.5 |
| Effort tier | L per adapter |
| Target version | v1.5 (QuickBooks first); v2 (Xero, NetSuite) |

#### K.6.2 Bidirectional accounting sync

| Field | Value |
| --- | --- |
| Description | Changes in the external accounting system reflect back to MPH. |
| Motivation | Reduces dual-entry surface for operators. |
| v1 accommodation | None — v1 sync is one-way. |
| Prerequisites | K.6.1. |
| Affected sections | F.5 |
| Effort tier | XL |
| Target version | v3+ |

#### K.6.3 Supplier portal / EDI

| Field | Value |
| --- | --- |
| Description | Suppliers receive POs and submit shipment notices via an electronic interchange (EDI) or a web portal. |
| Motivation | Reduces manual PO transmission and acknowledgment overhead. |
| v1 accommodation | None. POs are emailed in v1. |
| Prerequisites | Public-facing portal infrastructure decisions. |
| Affected sections | E.11, H.4 |
| Effort tier | XL |
| Target version | v3+ |

#### K.6.4 Inventory deduction

| Field | Value |
| --- | --- |
| Description | RawMaterials and Products track on-hand quantity; PO receipts increment, BOM consumption decrements, manual adjustments allowed. |
| Motivation | Tenants currently track inventory in a separate system; the disconnect is operationally painful. |
| v1 accommodation | None — v1 explicitly excludes inventory. |
| Prerequisites | Per-location inventory decision. |
| Affected sections | E.1, E.11, E.12 |
| Effort tier | XL |
| Target version | v3+ |

#### K.6.5 Recurring service templates

| Field | Value |
| --- | --- |
| Description | Define a service template that auto-generates Quotes/SalesOrders/WorkOrders on a schedule. |
| Motivation | Tenants with recurring service contracts (e.g., monthly maintenance) currently re-create the same records manually. |
| v1 accommodation | `WorkOrder.recurrence_template_id` is reserved (null in v1). |
| Prerequisites | None. |
| Affected sections | C.1.12, D.4, E.13 |
| Effort tier | L |
| Target version | v2 |

#### K.6.6 Route optimization, dispatch automation

| Field | Value |
| --- | --- |
| Description | Auto-assign WOs to technicians based on location, schedule, skills; optimize daily routes. |
| Motivation | Field-service tenants with many techs in a region. |
| v1 accommodation | WorkOrder has `assigned_to_membership_id`, `scheduled_date`, `client_location_id`. Manual assignment in v1. |
| Prerequisites | Skills modeling per Membership. |
| Affected sections | E.13 |
| Effort tier | XL |
| Target version | v3+ |

---

### K.7 Frontend Extensions

#### K.7.1 Per-tenant theming / white-labeling

| Field | Value |
| --- | --- |
| Description | Tenants can customize the brand color palette and logo for their tenant portal (and exported PDFs). |
| Motivation | Tenants reselling to their own customers want a branded experience. |
| v1 accommodation | None — v1 ships a fixed palette. |
| Prerequisites | Logo upload + favicon (K.7.2). |
| Affected sections | H.1, H.2, F.6, C.1 |
| Effort tier | M |
| Target version | v2 |

#### K.7.2 Per-tenant logo upload + favicon

| Field | Value |
| --- | --- |
| Description | Tenants upload their own logo and favicon for the tenant portal. |
| Motivation | Branding parity with tenant theming. |
| v1 accommodation | DocumentAttachment domain handles file uploads. |
| Prerequisites | None. |
| Affected sections | B.1.2, H.2, H.4 |
| Effort tier | S |
| Target version | v1.5 |

#### K.7.3 Saved views / list filters per user

| Field | Value |
| --- | --- |
| Description | Users save filter configurations on list pages and recall them. |
| Motivation | Power users currently re-apply the same filters daily. |
| v1 accommodation | None. |
| Prerequisites | None. |
| Affected sections | H.4.4 |
| Effort tier | M |
| Target version | v2 |

#### K.7.4 Dashboard customization per role

| Field | Value |
| --- | --- |
| Description | Role-specific dashboard tile sets with KPIs (AR aging, today's WOs, quote pipeline). |
| Motivation | The minimal v1 dashboard is functional but not differentiating. |
| v1 accommodation | The current dashboard is a single template; replacing it with a tile registry is straightforward. |
| Prerequisites | None. |
| Affected sections | H.4.3 |
| Effort tier | L |
| Target version | v2 |

#### K.7.5 Inline help / tour mode

| Field | Value |
| --- | --- |
| Description | Onboarding tour for new users; contextual help bubbles. |
| Motivation | Reduces "I don't know what this does" support load. |
| v1 accommodation | None. |
| Prerequisites | None. |
| Affected sections | H.4 |
| Effort tier | M |
| Target version | v2 |

#### K.7.6 Visual regression testing

| Field | Value |
| --- | --- |
| Description | Per-component visual diff testing in CI. |
| Motivation | Catches accidental visual drift. |
| v1 accommodation | None. |
| Prerequisites | Component documentation surface. |
| Affected sections | I.1 |
| Effort tier | M |
| Target version | v2 |

#### K.7.7 Accessibility (a11y) automated testing

| Field | Value |
| --- | --- |
| Description | axe-core or similar in CI to catch a11y regressions. |
| Motivation | a11y is a baseline expectation; v1 ships with manual review only. |
| v1 accommodation | Form rendering through partials and progressive enhancement reduce the worst a11y risks. |
| Prerequisites | None. |
| Affected sections | I.1 |
| Effort tier | M |
| Target version | v1.5 |

#### K.7.8 Component documentation surface

| Field | Value |
| --- | --- |
| Description | A Storybook-equivalent for the Phase 1 component partials. |
| Motivation | New engineers struggle to discover existing partials and end up creating duplicates. |
| v1 accommodation | None. |
| Prerequisites | None. |
| Affected sections | H.2 |
| Effort tier | M |
| Target version | v1.5 |

#### K.7.9 Print-optimized stylesheets

| Field | Value |
| --- | --- |
| Description | A dedicated print stylesheet for in-browser "Print" actions on quotes/invoices/work orders. |
| Motivation | Operators occasionally print directly from the screen. |
| v1 accommodation | PDFs are the canonical printable artifact. |
| Prerequisites | None. |
| Affected sections | H.4 |
| Effort tier | S |
| Target version | v1.5 |

---

### K.8 Reporting Extensions

#### K.8.1 Custom report builders

| Field | Value |
| --- | --- |
| Description | Tenant admins compose custom reports from a constrained query language; saved, shared with org members, exported. |
| Motivation | Tenants with reporting needs outside the v1 fixed catalog of 10. |
| v1 accommodation | The 10 fixed reports cover the ~80% case. |
| Prerequisites | Schema explorer / column metadata exposure. |
| Affected sections | F.6 |
| Effort tier | XL |
| Target version | v3+ |

#### K.8.2 Scheduled report delivery

| Field | Value |
| --- | --- |
| Description | A tenant admin schedules a report to email a specific list every week/month. |
| Motivation | Stakeholders want weekly AR aging reports without logging in. |
| v1 accommodation | Reports run on demand only. |
| Prerequisites | None. |
| Affected sections | F.6, G.3 |
| Effort tier | M |
| Target version | v2 |

#### K.8.3 BI / data-warehouse export

| Field | Value |
| --- | --- |
| Description | Per-tenant data warehouse export (Snowflake, BigQuery, Redshift) on a schedule. |
| Motivation | Larger tenants want their data in their existing BI stack. |
| v1 accommodation | The `tenant.export.assemble` pipeline produces JSONL+CSV; that's a starting point. |
| Prerequisites | Per-warehouse adapter design. |
| Affected sections | G.7.2 |
| Effort tier | XL |
| Target version | v3+ |

#### K.8.4 Dashboard KPIs

| Field | Value |
| --- | --- |
| Description | Real-time KPI tiles on the dashboard with charts (revenue trend, quote conversion rate, WO completion velocity). |
| Motivation | The minimal v1 dashboard doesn't help executives. |
| v1 accommodation | The 10 fixed reports cover the data; the dashboard can pull from them. |
| Prerequisites | Dashboard customization (K.7.4). |
| Affected sections | H.4.3 |
| Effort tier | L |
| Target version | v2 |

---

### K.9 Compliance Extensions

#### K.9.1 Cross-region audit shipping

| Field | Value |
| --- | --- |
| Description | AuditEvent rows replicated to a second region for compliance / tamper-evidence. |
| Motivation | Compliance frameworks (HIPAA, SOC 2) sometimes require cross-region audit retention. |
| v1 accommodation | AuditEvent retention via partition detach-then-drop; partitions could be archived to object storage in another region. |
| Prerequisites | DR secondary region infrastructure (K.12.2). |
| Affected sections | G.5 |
| Effort tier | L |
| Target version | v3+ |

#### K.9.2 Per-user data subject requests

| Field | Value |
| --- | --- |
| Description | A specific user (not whole-org) requests their personal data extracted from a tenant. |
| Motivation | GDPR / CCPA per-user rights. |
| v1 accommodation | Whole-tenant export covers the org-wide case but not per-user requests within an active tenant. |
| Prerequisites | None. |
| Affected sections | G.7 |
| Effort tier | M |
| Target version | v2 |

#### K.9.3 Cross-tenant legal-hold export

| Field | Value |
| --- | --- |
| Description | A platform-administered ability to export selected records across tenants under legal hold. |
| Motivation | Legal discovery requests. |
| v1 accommodation | None — v1's tenant isolation makes this deliberately hard. |
| Prerequisites | Strict legal review of cross-tenant query allowances. |
| Affected sections | G.5, G.7 |
| Effort tier | L |
| Target version | v3+ |

#### K.9.4 Bug bounty program

| Field | Value |
| --- | --- |
| Description | A scoped program that rewards security researchers for responsibly-disclosed findings. |
| Motivation | External pressure-tests the security posture. |
| v1 accommodation | The CSP report-uri, audit logging, and rate limits all help with disclosure forensics. |
| Prerequisites | Internal security review maturity (M8 baseline + 6 months of operations). |
| Affected sections | G.6 |
| Effort tier | M (program setup; ongoing operational cost) |
| Target version | v2 |

#### K.9.5 WAF (Web Application Firewall)

| Field | Value |
| --- | --- |
| Description | A layer 7 firewall (Cloudflare, AWS WAF, Cloud Armor) in front of the ingress. |
| Motivation | Defense-in-depth against common attack patterns. |
| v1 accommodation | Application-tier security controls (CSP, rate limits, CSRF) are defense-in-depth without WAF. |
| Prerequisites | None. |
| Affected sections | G.6, I.4 |
| Effort tier | M |
| Target version | v1.5 |

#### K.9.6 Penetration-testing schedule

| Field | Value |
| --- | --- |
| Description | Annual external pen test by a reputable firm. |
| Motivation | Compliance + insurance requirement for many enterprise customers. |
| v1 accommodation | None. |
| Prerequisites | Stable v1 in production. |
| Affected sections | G.6 |
| Effort tier | M (per cycle) |
| Target version | v1.5 (first cycle) |

---

### K.10 Communications Extensions

#### K.10.1 Inbound email channels

| Field | Value |
| --- | --- |
| Description | Inbound email parsing: a unique per-org address routes inbound mail to a Lead or Communication record. |
| Motivation | Tenants want to capture inbound prospect emails without manual logging. |
| v1 accommodation | The Communication model has direction=INBOUND and channel=EMAIL fields reserved; no inbound parser exists. |
| Prerequisites | Per-tenant inbound address allocation, email-parsing infrastructure. |
| Affected sections | C.1.6, D.7 |
| Effort tier | L |
| Target version | v2 |

#### K.10.2 Mailbox threading

| Field | Value |
| --- | --- |
| Description | Outbound and inbound emails on the same thread are grouped via Message-ID / In-Reply-To headers. |
| Motivation | Communication history is currently a flat log. |
| v1 accommodation | Communication has `provider_message_id` field; threading metadata could be added. |
| Prerequisites | K.10.1. |
| Affected sections | C.1.6 |
| Effort tier | M |
| Target version | v2 |

#### K.10.3 In-app notifications

| Field | Value |
| --- | --- |
| Description | A notification feed within the tenant portal (assigned task, pricing approval requested). |
| Motivation | Currently, all notifications are email-only; in-app reduces email noise. |
| v1 accommodation | The outbox pattern emits notification events; in-app notifications would consume the same events via a different handler. |
| Prerequisites | None. |
| Affected sections | G.3, H.4 |
| Effort tier | M |
| Target version | v2 |

---

### K.11 Phase 2 Extensions

#### K.11.1 React framework selection

| Field | Value |
| --- | --- |
| Description | Pre-M9 design sprint to select build tool, routing library, data-fetching library, and component patterns. |
| Motivation | Required by M9. |
| v1 accommodation | The forward-looking constraints in H.5.3 are framework-agnostic. |
| Prerequisites | v1 in production for 60+ days. |
| Affected sections | H.5 |
| Effort tier | S |
| Target version | pre-M9 |

#### K.11.2 TypeScript SDK from OpenAPI

| Field | Value |
| --- | --- |
| Description | Auto-generated TypeScript types and client SDK from the committed OpenAPI schema. |
| Motivation | Phase 2 React client needs type-safe API access. |
| v1 accommodation | drf-spectacular generates the OpenAPI schema; CI validates it. |
| Prerequisites | None. |
| Affected sections | H.6 |
| Effort tier | S |
| Target version | pre-M9 |

#### K.11.3 Schema diff / breaking-change CI gate

| Field | Value |
| --- | --- |
| Description | CI compares the new OpenAPI schema against the previous main-branch schema and flags breaking changes. |
| Motivation | Prevents accidental API breakage that breaks the React client. |
| v1 accommodation | OpenAPI schema is committed; diffing is straightforward. |
| Prerequisites | K.11.2. |
| Affected sections | H.6, I.1 |
| Effort tier | S |
| Target version | M9 |

#### K.11.4 Public / external API

| Field | Value |
| --- | --- |
| Description | A versioned, externally-documented API for tenant integrations and third-party developers. |
| Motivation | Tenants want programmatic access for custom integrations. |
| v1 accommodation | The internal API exists; making it public requires hardening (auth options, rate limits, SLAs, versioning policy, public docs). |
| Prerequisites | M9 stable. |
| Affected sections | H.6 |
| Effort tier | XL |
| Target version | v3+ |

#### K.11.5 Webhook emitters

| Field | Value |
| --- | --- |
| Description | Tenants register webhooks (URL + secret) for events; MPH POSTs to the URL with retry semantics. |
| Motivation | Tenant integrations with external systems. |
| v1 accommodation | The outbox pattern is the natural emission mechanism. |
| Prerequisites | K.11.4. |
| Affected sections | G.3 |
| Effort tier | L |
| Target version | v3+ |

---

### K.12 Operations and DR Extensions

#### K.12.1 Canary deployment strategy

| Field | Value |
| --- | --- |
| Description | A small percentage of traffic routed to a new release before full rollout. |
| Motivation | Reduces blast radius of bad deploys. |
| v1 accommodation | RollingUpdate strategy with `maxUnavailable: 0` provides zero-downtime, but no traffic-split canary. |
| Prerequisites | Service mesh or ingress capable of weighted routing. |
| Affected sections | I.4 |
| Effort tier | L |
| Target version | v2 |

#### K.12.2 Multi-region active-passive DR

| Field | Value |
| --- | --- |
| Description | A second region with read-replica Postgres and replicated object storage; failover is manual but rehearsed. |
| Motivation | Region-level disaster recovery. |
| v1 accommodation | Cross-region object-store replication is in v1 (I.5.3). Postgres replication to a remote region is the missing piece. |
| Prerequisites | Operational maturity at v1 launch + 6 months. |
| Affected sections | I.4, I.5 |
| Effort tier | XL |
| Target version | v3+ |

#### K.12.3 Database failover automation

| Field | Value |
| --- | --- |
| Description | Automatic failover to a standby Postgres on primary failure. |
| Motivation | Reduces RTO for primary-DB failures. |
| v1 accommodation | Manual failover via runbook. |
| Prerequisites | Production stability at v1 + 6 months. |
| Affected sections | I.4, I.5 |
| Effort tier | L |
| Target version | v2 |

#### K.12.4 Per-tenant point-in-time restore

| Field | Value |
| --- | --- |
| Description | A tenant admin requests their data restored to a point in time without affecting other tenants. |
| Motivation | "I deleted something I shouldn't have" — currently requires manual support intervention. |
| v1 accommodation | Whole-DB PITR exists; per-tenant restore requires logical-restore tooling. |
| Prerequisites | None. |
| Affected sections | I.5, G.7 |
| Effort tier | L |
| Target version | v3+ |

#### K.12.5 Blue-green prod environment

| Field | Value |
| --- | --- |
| Description | Two production environments (blue and green); deploy to inactive, swap traffic at the ingress. |
| Motivation | Instant rollback at the traffic level. |
| v1 accommodation | Forward-only rollback via redeploying the prior SHA covers the common case. |
| Prerequisites | Database migration discipline. |
| Affected sections | I.4 |
| Effort tier | L |
| Target version | v3+ |

#### K.12.6 Per-engineer staging branches

| Field | Value |
| --- | --- |
| Description | Each PR or feature branch gets a disposable staging environment with seeded data. |
| Motivation | Reduces "I can't reproduce that locally" investigation time. |
| v1 accommodation | Single staging environment. |
| Prerequisites | Cluster autoscaling + namespace-per-branch tooling. |
| Affected sections | I.3 |
| Effort tier | L |
| Target version | v2 |

---

### K.13 Localization, Mobile, and Schema-per-Tenant

#### K.13.1 i18n / l10n of error messages

| Field | Value |
| --- | --- |
| Description | Error messages and UI strings translated for non-English-speaking users. |
| Motivation | International tenant base. |
| v1 accommodation | All error messages have stable `error_code` strings; the codes are the source of truth. |
| Prerequisites | None. |
| Affected sections | G.2, H.2, H.4 |
| Effort tier | L |
| Target version | v2 |

#### K.13.2 Native iOS / Android applications

| Field | Value |
| --- | --- |
| Description | First-party mobile clients consuming the Phase 2 API. |
| Motivation | Field-service technicians want offline-capable mobile access. |
| v1 accommodation | None. |
| Prerequisites | Phase 2 API stable (M9). |
| Affected sections | H.5 |
| Effort tier | XL |
| Target version | v3+ |

#### K.13.3 Schema-per-tenant deployment

| Field | Value |
| --- | --- |
| Description | Each tenant gets a dedicated Postgres schema; query routing per tenant. |
| Motivation | Some compliance frameworks require physical/logical isolation. Some tenants have outsized data volumes. |
| v1 accommodation | Row-based tenancy with `organization_id` is fully implemented; schema-per-tenant would be a re-architecture. |
| Prerequisites | Re-evaluation of the entire query layer. |
| Affected sections | A.3, B.1, all data-model sections |
| Effort tier | XL |
| Target version | v3+ if ever |

#### K.13.4 Tenant data import / CSV import for clients/leads

| Field | Value |
| --- | --- |
| Description | Tenant admins upload CSVs to bulk-create Clients, Contacts, or Leads from external systems. |
| Motivation | New tenants migrating from another CRM need a fast onboarding path. |
| v1 accommodation | None. New tenants enter records manually or via API. |
| Prerequisites | None. |
| Affected sections | D.1, D.6, H.4 |
| Effort tier | M |
| Target version | v1.5 |

#### K.13.5 Migration of historical accepted quotes from legacy systems

| Field | Value |
| --- | --- |
| Description | A tooling path for importing accepted quotes from legacy systems with their pricing snapshots, tax records, and invoice history. |
| Motivation | Tenants migrating from another CRM want their historical revenue data. |
| v1 accommodation | None. The PricingSnapshot replay corpus is checked-in test data, not migration tooling. |
| Prerequisites | Tenant data import (K.13.4). |
| Affected sections | E.10, F.1 |
| Effort tier | XL |
| Target version | v3+ |

#### K.13.6 Decisions Embedded in This Section

- Schema-per-tenant target version is "v3+ if ever." Row-based tenancy with disciplined enforcement is sufficient unless compliance forces otherwise.
