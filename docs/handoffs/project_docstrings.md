# Project Docstrings

This file was generated from Python module, class, function, and method docstrings.

## `backend/apps/__init__.py`

### Module docstring

Top-level package for MyPipelineHero application code.

Apps are organized by ownership domain (per `docs/guide.md` § A.5):

    apps.platform.*    Identity, organizations, RBAC, audit, support
    apps.web.*         Server-rendered surfaces (landing, auth portal, tenant portal)
    apps.crm.*         Lead, quote, client, task, communication, order, billing
    apps.catalog.*     Services, products, materials, suppliers, pricing, manufacturing
    apps.operations.*  Locations, purchasing, build, work orders
    apps.files.*       Document attachments
    apps.reporting.*   Reports and exports
    apps.api.*         DRF Phase 2 internal API
    apps.common.*      Shared infrastructure (tenancy, db, services, outbox, utils)

Every nested app uses an explicit ``AppConfig.label`` (A.5.7).

## `backend/apps/common/__init__.py`

### Module docstring

Shared infrastructure used across every domain.

Domain apps may freely import from ``apps.common.*``. ``apps.common.*``
must not import from any domain app.

## `backend/apps/common/admin/__init__.py`

### Module docstring

Custom-admin framework primitives (H.7).

Concrete base views, navigation registry, and shell layout land in M1
alongside the platform-console expansion.

## `backend/apps/common/celery.py`

### Module docstring

Celery application for MyPipelineHero.

Importable as ``apps.common.celery:app`` (and re-exported from the project
root as ``celery_app`` in ``config/__init__.py``).

Run worker:

    celery -A apps.common.celery worker -Q critical,default,bulk,reports -l info

Run beat:

    celery -A apps.common.celery beat -l info --schedule=/tmp/celerybeat-schedule

### Function `debug_task`

Smoke-test task. Useful for verifying broker connectivity in M0.

## `backend/apps/common/choices/__init__.py`

### Module docstring

Shared enum/choice constants used by multiple domains.

## `backend/apps/common/db/__init__.py`

### Module docstring

Shared DB helpers — constraints, partition helpers, etc. (M5+).

## `backend/apps/common/outbox/__init__.py`

### Module docstring

Outbox pattern primitives (A.3.5, G.3).

Phase 1: app skeleton only — concrete OutboxEntry, dispatcher, and
task bridge land in M1.

## `backend/apps/common/outbox/models.py`

### Module docstring

Placeholder for outbox models.

Concrete ``OutboxEntry`` lands in M1 (G.3.3).

## `backend/apps/common/services/__init__.py`

### Module docstring

Shared service-layer primitives.

Concrete frozen ``*Result`` dataclasses, decorator helpers, and shared
exception types land alongside the first domain service in M2.

## `backend/apps/common/sessions/__init__.py`

### Module docstring

Per-tenant session middleware (M1 D6 Phase 3).

Implements B.4.14: cookies are scoped per host so root-domain and
tenant-subdomain sessions are independent. ``PerTenantSessionMiddleware``
replaces Django's standard ``SessionMiddleware`` in ``MIDDLEWARE``.

## `backend/apps/common/sessions/host_resolution.py`

### Module docstring

Host → session-scope resolution (M1 D6 Phase 3).

Pure functions that compute the session cookie name and cookie domain
from the request host. No Django dependencies beyond ``settings`` —
keeps the logic unit-testable without spinning up a request cycle.

Three scopes:

* ``HostScope.ROOT`` — request to the root domain (``mph.local`` in
  dev). Cookie name: ``settings.SESSION_COOKIE_NAME`` (default
  ``"mph_root_session"`` per M1 D6 base.py).
* ``HostScope.TENANT`` — request to a tenant subdomain
  (``{slug}.mph.local``). Cookie name: ``tenant_session_{slug}``.
  Cookie domain: the exact tenant host.
* ``HostScope.OTHER`` — request to a host we don't classify
  (``localhost``, ``testserver``, IP literals). Falls back to
  ``settings.SESSION_COOKIE_NAME`` with no Domain attribute (browser
  default = exact host).

The template-string parsing happens once per process at import time;
subsequent calls are pure dict lookups.

### Class `SessionScope`

The cookie name and domain a request's session should use.

### Function `_parse_tenant_template`

Split MPH_TENANT_DOMAIN_TEMPLATE into (prefix, suffix) at {slug}.

Example: ``"{slug}.mph.local"`` → (``""``, ``".mph.local"``).
``"mph-{slug}.example.com"`` → (``"mph-"``, ``".example.com"``).

### Function `resolve_session_scope`

Classify the host and return cookie name+domain accordingly.

Args:
    host: The request host (``request.get_host()``), with port
        already stripped by the caller.

Returns:
    A SessionScope describing what cookie name and domain to use
    for sessions on this host.

## `backend/apps/common/sessions/middleware.py`

### Module docstring

Per-tenant session middleware + per-host URLconf middleware
(M1 D6 Phases 3 + 4A, B.4.14 + B.4.15).

``PerTenantSessionMiddleware`` (Phase 3) replaces Django's
standard ``SessionMiddleware`` to scope session cookies per host.

``HostUrlconfMiddleware`` (Phase 4A) sets ``request.urlconf``
based on the host scope so root-domain and tenant-subdomain URL
spaces are mutually exclusive.

**Test opt-out.** Setting ``MPH_HOST_URLCONF_ROUTING_ENABLED = False``
disables the host-routing override. Tests that need to swap in a
test-only URLconf via ``override_settings(ROOT_URLCONF=...)`` set
this flag at the class or module level. Production keeps the
default ``True`` and the middleware enforces per-host routing
normally.

**OTHER scope falls through.** When the host doesn't match root
or tenant patterns (testserver, localhost, IPs),
``HostUrlconfMiddleware`` does NOT set ``request.urlconf``.
Django then uses ``settings.ROOT_URLCONF``.

Both middlewares read the same ``request._mph_session_scope``
attribute set by ``PerTenantSessionMiddleware.process_request``.
MIDDLEWARE order MUST be: ``PerTenantSessionMiddleware`` first,
``HostUrlconfMiddleware`` second.

**Django version coupling.** ``PerTenantSessionMiddleware``
mirrors Django 5.2's ``SessionMiddleware.process_response``
closely. ``HostUrlconfMiddleware`` uses the documented
``request.urlconf`` attribute.

### Class `PerTenantSessionMiddleware`

Session middleware that picks the cookie name per host.

### Class `HostUrlconfMiddleware`

Set ``request.urlconf`` based on host scope (B.4.15).

Root domain → ``config.urls_root``.
Tenant subdomain → ``config.urls_tenant``.
OTHER (testserver, localhost) → fall through to
``settings.ROOT_URLCONF``.

**Test opt-out.** When
``settings.MPH_HOST_URLCONF_ROUTING_ENABLED = False``, the
middleware skips the override entirely and lets
``settings.ROOT_URLCONF`` win. Tests that need to swap in a
test-only URLconf (e.g. the per-host session cookie tests)
use this flag.

Reads ``request._mph_session_scope`` set by
``PerTenantSessionMiddleware.process_request``. MUST be ordered
AFTER ``PerTenantSessionMiddleware`` in ``MIDDLEWARE``.

## `backend/apps/common/sessions/tests/test_host_resolution.py`

### Module docstring

Tests for host → session scope resolution (M1 D6 Phase 3).

## `backend/apps/common/sessions/tests/test_host_urlconf_middleware.py`

### Module docstring

Tests for HostUrlconfMiddleware (M1 D6 Phase 4A).

### Function `_enable_host_routing`

Enable HostUrlconfMiddleware for every test in this module.

### Class `TestHostUrlconfRouting`

Each host scope resolves to the correct URLconf.

### Class `TestHostUrlconfDefensiveFallback`

When _mph_session_scope is missing, middleware falls through cleanly.

### Function `test_root_host_resolves_root_urlconf`

Root-domain request can reach allauth login (root-only route).

### Function `test_tenant_host_cannot_reach_root_routes`

Tenant subdomain returns 404 for root-only routes like allauth.

### Function `test_testserver_falls_through_to_root_urlconf`

Tests using default testserver host fall through to ROOT_URLCONF.

### Function `test_landing_page_root_and_tenant_both_resolve`

Landing routing differs by host.

Root domain serves the marketing landing page (200).
Tenant subdomain serves the tenant landing — which, for an
unauthenticated visitor with no tenant session, redirects to
the root-domain picker (302 to mph.local/select-org/).

### Function `test_falls_through_when_scope_attribute_missing`

Direct middleware invocation without session-scope attribute.

## `backend/apps/common/sessions/tests/test_middleware.py`

### Module docstring

Tests for PerTenantSessionMiddleware (M1 D6 Phase 3, B.4.14).

These tests intentionally use a test-only URL that explicitly writes to
``request.session``.

Previously these tests used ``/accounts/login/`` because allauth's login
GET was assumed to touch the session. In the current app behavior, that
request only sets the CSRF cookie and does not write a session cookie, so
it is not a reliable way to test session-cookie middleware.

The goal here is to test the middleware behavior once Django actually has
a modified session to persist.

### Function `touch_session_view`

Force Django to create/write a session cookie.

### Function `use_test_urlconf`

Point these tests at the test-only URLConf in this module.

### Class `TestCookieNamePerHost`

The Set-Cookie header carries the right name for the request host.

### Class `TestCookieDomainScoping`

A cookie's Domain attribute must NOT span the parent domain.

### Class `TestSessionIsolationBetweenHosts`

Sessions established on root vs. tenant must not bleed into each other.

## `backend/apps/common/sessions/tests/test_middleware_provider_mfa_satisfaction.py`

### Module docstring

Tests for trusted-provider mph_mfa_satisfied_at session write (M1 D6 Phase 4A).

When ``RequireMfaEnrollmentMiddleware`` bypasses enrollment for a
trusted-provider OAuth user, it also writes
``mph_mfa_satisfied_at`` to session. This test guards that.

## `backend/apps/common/tenancy/__init__.py`

### Module docstring

MyPipelineHero tenancy primitives (B.1.3-B.1.7).

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

### Function `__getattr__`

Resolve a public-API name on first access.

Defers submodule imports until after Django's app registry has
finished populating. Without this, ``from apps.common.tenancy
import TenantOwnedModel`` at the top of any module imported during
Django startup would raise ``AppRegistryNotReady``.

### Function `__dir__`

Make ``dir(apps.common.tenancy)`` show the public API names.

## `backend/apps/common/tenancy/apps.py`

### Module docstring

App config for apps.common.tenancy.

## `backend/apps/common/tenancy/exceptions.py`

### Module docstring

Tenancy-related exceptions (B.1.6, B.2.6).

These exceptions signal violations of the tenant-isolation invariants.
They are not user-facing error messages — services that catch them
should treat them as 500-level bugs (the calling code should never
have constructed the cross-tenant query in the first place).

Services raise these by calling :func:`ensure_same_org` or by
invoking the RBAC object-check helpers (lands in M2).

### Class `TenantViolationError`

Raised when a service-layer call mixes records from different orgs.

Per B.1.6, when a tenant-owned record references another
tenant-owned record, both MUST belong to the same Organization.
This exception fires when :func:`ensure_same_org` detects a
cross-tenant mix.

Attributes:
    record_summaries: list of ``"<ModelName>(id=<id>, org=<org_id>)"``
        strings, one per record that participated in the violation.
        Useful for logs; never expose to end users.

### Class `OperatingScopeViolationError`

Raised when a membership's operating scope does not cover a target record.

Per B.2.6, when a membership has scope assignments (Region/Market/
Location) and the target record carries a ``location_id``, the
location MUST fall within the membership's permitted location set.
This exception fires when it does not.

Attributes:
    membership_id: the membership whose scope was insufficient.
    target_location_id: the location the membership cannot reach.

## `backend/apps/common/tenancy/managers.py`

### Module docstring

TenantManager and TenantQuerySet (B.1.4).

Tenant-aware ORM surface for :class:`TenantOwnedModel` subclasses.

``TenantManager`` does NOT auto-filter querysets. This is deliberate:

* B.1.5 permits two cross-tenant exception paths (Support User
  platform console + migrations). Auto-filtering would force every
  exception-path call to think about how to escape the filter, which
  inverts the safety posture.
* Service-layer code is the authoritative call site for tenant-scoped
  reads, and it uses the explicit ``for_org(...)`` / ``for_membership(...)``
  methods. The explicitness is a feature.

Models that need operating-scope intersection (B.2.5) — e.g.
SalesOrder, which carries ``location_id`` — override
``intersect_with_operating_scope`` on a per-model QuerySet subclass.
The base method returns ``self`` unchanged.

### Class `TenantQuerySet`

Tenant-aware queryset surface (B.1.4).

### Class `TenantManager`

Manager for :class:`TenantOwnedModel` subclasses.

Two important properties:

* ``use_in_migrations = False``: the Django migration framework
  uses ``models.Manager()`` semantics on tenant-owned models inside
  data migrations. Migrations that need tenant scoping MUST filter
  explicitly. This prevents accidental ``RelatedManager``-style
  auto-filtering inside historical model proxies.
* No auto-filtering: the manager does not inject any
  ``organization_id`` filter on its own. Service-layer reads MUST
  call ``for_org`` or ``for_membership`` explicitly.

### Function `for_org`

Filter to records belonging to a specific Organization.

Args:
    organization_id: UUID of the target Organization.

Returns:
    New queryset filtered on ``organization_id``.

### Function `for_membership`

Apply org scope AND operating-scope intersection.

Equivalent to::

    qs.for_org(membership.organization_id) \
      .intersect_with_operating_scope(membership)

Use this in service layer reads where the acting member's
operating scope (Region/Market/Location) should restrict
visibility (B.2.5).

### Function `intersect_with_operating_scope`

Restrict to records covered by the membership's operating scope.

The base implementation is a no-op (returns ``self``). Per-model
QuerySet subclasses override this for models that carry a
``location_id`` field — see B.2.5 for the SalesOrder example.

For models without a ``location_id`` field, the no-op base is
the correct behavior: there is nothing to intersect against.

## `backend/apps/common/tenancy/models.py`

### Module docstring

TenantOwnedModel abstract base (B.1.3).

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

### Class `TenantOwnedModel`

Abstract base for every tenant-owned model (B.1.3).

## `backend/apps/common/tenancy/tests/test_isolation_guardrail.py`

### Module docstring

B.1.7 tenant-isolation CI guardrail.

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

### Function `_has_organization_fk`

True iff the model has a field named ``organization`` that is a FK.

### Function `_organization_fk_target`

Return the model label that the ``organization`` FK targets.

### Function `_organization_fk_on_delete`

Return the on_delete callable for the ``organization`` FK.

### Function `test_every_tenant_owned_model_organization_fk_targets_canonical_org`

Tenant-owned models MUST reference the canonical Organization.

B.1.3 explicitly names ``platform_organizations.Organization`` as
the target. Catching the wrong target here prevents accidental
references to a future "OrgLite" or shadow model.

### Function `test_every_tenant_owned_model_organization_fk_is_protect`

B.1.3 mandates ``on_delete=PROTECT`` for tenant-owned ``organization`` FKs.

Tenant deletion is a multi-stage workflow (G.7.3); a CASCADE on the
organization FK would let a stray ``Organization.delete()`` silently
take out tenant data without going through that workflow.

### Function `test_organization_is_not_tenant_owned`

The Organization model IS the tenant; it MUST NOT carry the flag.

### Function `test_user_is_not_tenant_owned`

User is platform-tier identity, not tenant-owned (B.3.1).

### Function `test_membership_is_not_tenant_owned`

Membership is the JOIN row; it is org-scoped but not TenantOwnedModel.

Tenant authorization flows through Membership; the platform console
queries it across tenants. See the developer primer in
apps.common.tenancy.__init__ for the rationale.

### Function `test_capability_and_role_are_not_tenant_owned`

RBAC tables are platform-tier; they are NOT TenantOwnedModel.

### Function `test_tenant_manager_does_not_run_in_migrations`

TenantManager.use_in_migrations is False per B.1.4.

### Function `test_tenant_owned_model_is_abstract`

The base class itself must remain abstract.

### Function `test_tenant_owned_model_has_organization_fk_declaration`

Sanity-check the abstract base's own FK declaration.

## `backend/apps/common/tenancy/tests/test_manager_surface.py`

### Module docstring

Tests for TenantManager / TenantQuerySet surface (B.1.4).

These tests don't require any concrete tenant-owned model to exist. They
verify the manager class properties and the queryset's method
signatures.

We deliberately don't try to exercise ``for_org`` end-to-end with a
synthetic queryset: ``.filter(organization_id=...)`` requires a bound
model to resolve the field name, and constructing a fake model just to
test the signature is more cost than the test is worth. The real
``for_org`` behavior gets covered the moment any tenant-owned model
appears in a domain test (M1 D3 onward).

### Function `test_tenant_queryset_intersect_default_is_identity`

Base intersect_with_operating_scope returns self unchanged.

### Function `test_tenant_queryset_exposes_for_org`

``for_org`` is callable on TenantQuerySet.

### Function `test_for_org_accepts_a_single_positional_argument`

``for_org(organization_id)`` accepts exactly one positional arg.

### Function `test_tenant_queryset_exposes_for_membership`

``for_membership`` is callable on TenantQuerySet.

### Function `test_for_membership_accepts_a_single_positional_argument`

``for_membership(membership)`` accepts exactly one positional arg.

### Function `test_tenant_manager_inherits_queryset_methods`

``TenantManager`` exposes ``for_org`` and ``for_membership`` as proxies.

``Manager.from_queryset(TenantQuerySet)`` generates manager methods
that delegate to the queryset's methods of the same name. We don't
invoke them here (that requires a bound model); we just confirm the
attributes exist on the manager class.

## `backend/apps/common/tenancy/tests/test_utils.py`

### Module docstring

Tests for apps.common.tenancy.utils.

### Function `test_ensure_same_org_accepts_organization_instance`

An Organization passed in returns its own id as the common org id.

### Function `test_resolve_with_empty_iterable_returns_empty_list`

The function accepts an empty iterable without touching the DB.

### Function `test_resolve_with_iterator_input_also_works`

Passing a generator instead of a list works.

## `backend/apps/common/tenancy/utils.py`

### Module docstring

Tenancy helpers (B.1.6, B.2.6).

These utilities are called from service-layer code to enforce the
tenant-isolation and operating-scope invariants. They are NOT called
from views, models, or migrations.

### Function `_record_org_id`

Extract the org id from a record.

Handles three shapes:
  - ``TenantOwnedModel`` subclasses: ``record.organization_id``
  - ``Organization`` instances: ``record.id`` (the org IS the tenant)
  - Anything else: returns None (caller decides whether to raise)

### Function `_record_summary`

Produce a short, log-safe summary of a record for error context.

### Function `ensure_same_org`

Verify every record belongs to the same Organization (B.1.6 #1).

Service-layer code passes the records it is about to write or
join. If any pair of records carries a different ``organization_id``,
this function raises :exc:`TenantViolationError`.

Args:
    *records: Two or more records to check. Each MUST be either a
        ``TenantOwnedModel`` subclass instance or an
        ``Organization`` instance. ``None`` values are skipped.

Returns:
    The common ``organization_id`` shared by all non-None records.

Raises:
    TenantViolationError: if records belong to different orgs, or
        if any record lacks a resolvable org id.
    ValueError: if called with fewer than one non-None record.

### Function `resolve_location_ids_for_scopes`

Resolve a membership's scope assignments to a flat list of Location ids.

A MembershipScopeAssignment can be at Region, Market, or Location
granularity (B.2.4). This helper expands each assignment to the
leaf Location set it covers:

    - REGION assignment   → all Locations under all Markets under that Region
    - MARKET assignment   → all Locations under that Market
    - LOCATION assignment → that Location only

The result is deduplicated.

Implementation strategy: bucket the input by scope_type, then issue
one query per scope_type (REGION → Location.objects.filter(
market__region_id__in=...), MARKET → Location.objects.filter(
market_id__in=...), LOCATION → the literal IDs). This is at most
three queries regardless of how many scope rows the membership has,
so there is no N+1 over the scope list.

Args:
    scopes: an iterable of MembershipScopeAssignment rows. May be
        an empty iterable, in which case the result is ``[]``.

Returns:
    A list of Location UUIDs covered by the scopes, deduplicated.
    Order is unspecified.

## `backend/apps/common/tests/__init__.py`

### Module docstring

Shared test helpers / fixtures used across domains.

## `backend/apps/common/tests/test_health.py`

### Module docstring

Smoke tests for /healthz and /readyz (G.4.8).

### Function `test_readyz_returns_ok_when_dependencies_up`

In the test environment, DB and cache (locmem) are always reachable.

## `backend/apps/common/utils/__init__.py`

### Module docstring

Shared utilities. Only environment-agnostic helpers belong here.

## `backend/apps/common/utils/health.py`

### Module docstring

Health check views (G.4.8).

These endpoints are intentionally unauthenticated and intentionally cheap.

* ``/healthz``     — process is alive. Returns 200 with ``{"status": "ok"}``.
* ``/readyz``      — process can serve traffic (DB + Redis reachable).
* ``/healthz/deep``— exhaustive (DB write, Redis SET, object store HEAD).

The deep check is deferred to a later milestone; this module ships ``healthz``
and ``readyz`` for M0.

### Function `healthz`

Liveness probe. Always returns 200 if the process is up.

### Function `readyz`

Readiness probe. 200 iff DB and cache are reachable; 503 otherwise.

## `backend/apps/common/utils/health_urls.py`

### Module docstring

URL bindings for health endpoints (G.4.8).

Mounted at the project root so the paths are exactly ``/healthz`` and
``/readyz``.

## `backend/apps/operations/locations/__init__.py`

### Module docstring

Region / Market / Location (RML) — operating-scope hierarchy (B.2).

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

## `backend/apps/operations/locations/admin.py`

### Module docstring

Dev-only Django admin registrations for RML models.

Mounted at ``/django-admin/`` and only visible when DEBUG=True. The
production platform console (custom admin at ``/platform/``) gets the
proper RML editing surface in a later milestone.

## `backend/apps/operations/locations/apps.py`

### Module docstring

App config for apps.operations.locations.

## `backend/apps/operations/locations/models.py`

### Module docstring

Region / Market / Location models (B.2.2).

All three inherit from :class:`apps.common.tenancy.models.TenantOwnedModel`,
which gives them:

* an ``organization`` FK with ``on_delete=PROTECT``,
* ``created_at`` / ``updated_at`` / ``created_by`` / ``updated_by`` audit columns,
* ``is_tenant_owned = True`` (so the B.1.7 guardrail picks them up),
* a default manager that is a :class:`TenantManager` subclass.

Hierarchy invariants (B.2.1):

* A Market belongs to exactly one Region.
* A Location belongs to exactly one Market.
* Cross-organization references are prohibited. This is enforced at
  the service layer via :func:`apps.common.tenancy.utils.ensure_same_org`.
  No cross-row DB CHECK constraint is used (B.1.6 forbids that pattern
  in v1).

### Class `Region`

Top-level operating-scope grouping within an Organization (B.2.2).

### Class `Market`

Mid-level operating-scope grouping, child of a Region (B.2.2).

### Class `LocationQuerySet`

Per-model QuerySet for Location.

Location is the *leaf* of the operating-scope hierarchy: every
permitted Location id IS itself the row this queryset returns. So
rather than filtering ``location_id__in=...`` (the pattern in
B.2.5's SalesOrder example), we filter ``id__in=...``.

The membership-no-scope-assignments rules from B.2.5 still apply:

* No assignments + non-scoped role  → org-wide access (return self).
* No assignments + scoped role      → zero access (return self.none()).
* Has assignments                   → filter to the permitted set.

### Class `LocationManager`

Default manager for Location.

Reuses TenantManager's invariants (use_in_migrations=False) and
layers on the LocationQuerySet method surface.

### Class `Location`

Leaf node in the operating-scope hierarchy (B.2.2).

The address fields are denormalized for fast display and for
pricing/tax inputs (B.2.7). The ``region_admin`` field holds the
administrative region (state/province) — note this is unrelated to
the operating-scope ``region`` FK on Market.

``tax_jurisdiction_id`` is a plain UUID column awaiting the
TaxJurisdiction model that lands in M3 (J.5). It will be converted
to a real FK at that time. Same pattern as
``Organization.default_tax_jurisdiction_id`` from M0 D2.

## `backend/apps/operations/locations/tests/test_models.py`

### Module docstring

Tests for RML models (B.2.2) and the operating-scope intersection (B.2.5).

### Function `rml_tree`

Build a small RML tree on org_a:

Region NORTH
  Market NORTH-A
    Location N-A-1
    Location N-A-2
  Market NORTH-B
    Location N-B-1
Region SOUTH
  Market SOUTH-A
    Location S-A-1

### Function `test_region_code_can_repeat_across_orgs`

Same code is fine across different orgs.

### Function `test_cross_org_market_to_region_chain_caught_by_ensure_same_org`

B.1.6 invariant: cross-org references are prohibited.

There is no cross-row DB CHECK enforcing this (the guide rules
those out for v1). Instead, service-layer code calls
``ensure_same_org`` before constructing the chain. This test
verifies that helper catches the violation when it would happen.

Note: at the ORM level, creating a Market in org_b with a Region
from org_a would technically succeed. The protection is at the
service-layer doorway. When the Market-creation service lands
(M2+), it will call ``ensure_same_org(organization=org_b,
region=region_a)`` and the helper will raise. We exercise that
contract here.

### Function `test_cross_org_location_to_market_chain_caught_by_ensure_same_org`

Same protection one level deeper in the chain.

### Function `test_resolve_mixed_scopes_returns_union_dedupe`

REGION + MARKET + LOCATION at once: union, deduplicated.

Setup:
  REGION SOUTH (covers s_a_1)
  MARKET NORTH-A (covers n_a_1, n_a_2)
  LOCATION n_a_1 (already covered by NORTH-A; should dedupe)

Expected: {n_a_1, n_a_2, s_a_1}

### Function `test_location_queryset_intersect_with_no_scopes_and_no_scoped_role`

No scope assignments + Owner (non-scoped) role = org-wide access.

## `backend/apps/platform/__init__.py`

### Module docstring

Platform-level apps: identity, organizations, RBAC, audit, support.

## `backend/apps/platform/accounts/__init__.py`

### Module docstring

Platform identity — the canonical User model (B.3).

The ``User`` model in this app is the value of ``AUTH_USER_MODEL``
(``platform_accounts.User``) and is migrated in this app's
``0001_initial`` migration. Retrofitting AUTH_USER_MODEL after
deployment is prohibited (I.6.7).

## `backend/apps/platform/accounts/admin.py`

### Module docstring

Dev-only Django admin registrations.

This module is loaded ONLY when ``/django-admin/`` is mounted (DEBUG=True
per config/urls.py). It is for raw model inspection during development
(H.7.2). The production admin surface is the custom platform admin
(H.7.1).

Each registration uses ``ModelAdmin`` with conservative settings —
readonly timestamps, search by stable fields, list display tuned for
quick eyeballing. No bulk-edit, no save-as-new, no inline form magic.
None of these surfaces are product workflows.

### Class `UserAdmin`

Minimal raw-inspection admin. Not a product surface.

## `backend/apps/platform/accounts/apps.py`

### Module docstring

AppConfig for the accounts app.

Wires signal handlers and (M1 D5) loads OAuthProviderConfig rows
into ``SOCIALACCOUNT_PROVIDERS`` via the post_migrate signal.

### Function `_reload_oauth_providers_after_migrate`

Handler for post_migrate: reload OAuth provider settings.

### Function `ready`

Wire signal handlers and the post_migrate OAuth loader.

Signal handlers (M1 D4):
    * allauth account-app signals → record_auth_event.
    * allauth.mfa lifecycle signals → record_auth_event.

Signal handlers (M1 D5 Phase 3):
    * allauth.socialaccount signals → OAUTH_LOGIN_SUCCEEDED,
      OAUTH_ACCOUNT_UNLINKED.

Signal handlers (M1 D6 Phase 4A):
    * allauth.mfa.signals.authenticator_used and
      authenticator_added → write
      ``mph_mfa_satisfied_at`` to session for downstream
      consumption by the org picker / handoff token issue.

Signal handlers (M1 D6 Phase 5):
    * allauth.account.signals.user_logged_out → on root
      logout, revoke outstanding handoff tokens via the
      user_handoffs:{uid} Redis index and emit
      ``ROOT_SESSION_LOGOUT``. Tenant logouts are no-ops
      here (tenant view emits its own audit).

Model discovery (M1 D5 / M1 D6 / M1 D7):
    * Subpackage models (oauth/, handoff/, impersonation/)
      are NOT auto-discovered by Django because they don't
      live in the app's top-level models.py. The imports
      below force the subpackages' __init__.py to run
      during app-ready, which in turn imports models.py
      from each subpackage and registers the models with
      Django's app registry. Without these imports,
      ``makemigrations`` would generate spurious
      DeleteModel migrations and the test DB schema would
      diverge from the production one.

Settings loader (M1 D5 Phase 3):
    * Read active OAuthProviderConfig rows and write the
      resulting ``SOCIALACCOUNT_PROVIDERS`` dict to
      django.conf.settings. Triggered by ``post_migrate``
      rather than from ``ready()`` itself — Django warns
      against DB access during app init.

## `backend/apps/platform/accounts/handoff/__init__.py`

### Module docstring

Handoff subsystem (M1 D6).

Cross-subdomain handoff per B.4.11-B.4.17. Phase 1 owns the signing-
key lifecycle; Phase 2 owns token issue/consume; Phases 3-5 wire HTTP
endpoints and per-tenant sessions.

## `backend/apps/platform/accounts/handoff/encryption.py`

### Module docstring

Fernet encryption helpers for HandoffSigningKey.secret (M1 D6 Phase 1).

B.4.13.1 specifies that the per-rotation HMAC secret is encrypted at
rest. We implement that as service-layer Fernet encryption with a
master key from environment (``HANDOFF_KEY_ENCRYPTION_KEY``) rather
than a custom EncryptedField type. The security property is
identical and avoids inventing a field type that doesn't exist yet
in the codebase. See M1 D6 retro deviation log.

Failure semantics:

* Missing master key at import time → ImproperlyConfigured raised
  by ``_get_fernet`` on first use. The settings module also asserts
  presence so deployments fail loudly.
* Decryption failure (wrong key, tampered ciphertext) → raises
  ``HandoffSecretDecryptionError`` which the caller MUST treat as
  "this key is unusable; do not use it for verification."

The master key has no in-application rotation mechanism in M1 D6.
Rotating the master key would render every existing
HandoffSigningKey.secret undecryptable. Out of scope; tracked as
operational concern.

### Class `HandoffSecretDecryptionError`

Raised when a HandoffSigningKey.secret cannot be decrypted.

Likely causes: master key rotation without re-encryption,
corruption of the stored ciphertext, or tampering. The caller
MUST NOT use the key for verification when this is raised; do
NOT log the raw ciphertext or master-key fingerprint in the
error message.

### Function `_get_fernet`

Construct a Fernet instance from settings.

Raises:
    ImproperlyConfigured: if ``HANDOFF_KEY_ENCRYPTION_KEY`` is
    absent or malformed.

### Function `encrypt_handoff_secret`

Encrypt the raw per-rotation HMAC secret.

Returns a Fernet token (base64 ASCII string) suitable for storage
in a TextField column.

### Function `decrypt_handoff_secret`

Decrypt a Fernet-encrypted per-rotation HMAC secret.

Raises:
    HandoffSecretDecryptionError: if the ciphertext can't be
    decrypted with the current master key.

## `backend/apps/platform/accounts/handoff/models.py`

### Module docstring

HandoffSigningKey model (B.4.13.1, M1 D6 Phase 1).

The model carries no business logic in save(); see the
``handoff/services/`` package for the lifecycle services.

The ``secret`` column holds the Fernet-encrypted per-rotation HMAC
secret as a TextField (Fernet tokens are base64 ASCII). See
``encryption.py`` for the encrypt/decrypt helpers and the deviation
note in the M1 D6 retro.

### Function `_new_uuid`

UUID v7 factory (Python 3.14+). Falls back to uuid4 for older runtimes.

### Class `HandoffSigningKey`

Per-rotation HMAC signing key for handoff tokens (B.4.13.1).

Lifecycle:

1. Created — ``created_at`` set, ``promoted_at`` NULL,
   ``retired_at`` NULL. Cannot verify tokens yet.
2. Promoted — ``promoted_at`` set. Becomes the primary
   (newest non-retired) for token issuance. Previous primary
   remains active for verification during overlap window.
3. Retired — ``retired_at`` set. No longer used for
   verification. Row preserved for audit reconstruction.

Active key set rules (enforced at service layer):

* Exactly one primary key at a time (the newest non-retired).
* At most two non-retired keys at any moment (rotation overlap).
* Retired keys stay in the table indefinitely.

The ``CHECK retired_at IS NULL OR retired_at > created_at``
constraint catches operator error at the DB layer.

## `backend/apps/platform/accounts/handoff/results.py`

### Module docstring

HandoffResult dataclass (B.4.12, M1 D6 Phase 2).

Returned by :func:`consume_handoff_token`. Carries everything
:func:`establish_tenant_session` (Phase 4) needs to construct the
B.4.14-shaped tenant-local session.

### Class `HandoffResult`

Successful handoff token consumption result.

Field names match the JWT payload claims and the B.4.14 session
keys. Constructors / fields are intentionally minimal: the
consume service produces this; the tenant-session establishment
service writes it into the session dict directly.

Fields:
    user_id: The User the handoff is for.
    organization_id: The target tenant.
    membership_id: The Membership that authorized the handoff.
    auth_method: One of "password", "oidc", "oauth2", "impersonation"
        per B.4.14.
    auth_provider: Provider_code for OAuth/OIDC, else None.
    mfa_satisfied_at: Wall-clock timestamp of when MFA was satisfied
        on the root-domain session. Tenant-side B.4.10 re-auth windows
        compare against this.

## `backend/apps/platform/accounts/handoff/services/__init__.py`

### Module docstring

Handoff services package (M1 D6).

Phase 1 — Signing-key lifecycle.
Phase 2 — Token issue/consume.
Phase 4B — Tenant session establishment.
Phase 5 — Token revocation on logout.

## `backend/apps/platform/accounts/handoff/services/_consume.py`

### Module docstring

consume_handoff_token service (B.4.12, M1 D6 Phase 2 + Phase 5).

Verifies a JWT, atomically consumes the Redis nonce, removes the
token id from the per-user secondary index, checks host binding and
membership status, and returns a HandoffResult.

The consume function uses GETDEL (Redis 6.2+) for atomic single-use
enforcement. This deviates from the guide's pipeline pattern
(GET + DELETE inside a MULTI/EXEC pipeline) for a stronger reason:
the pipeline pattern doesn't actually prevent concurrent consumes
from both seeing the same GET result before either DELETE lands.
GETDEL is a single command that returns the value AND deletes
atomically; concurrent calls either get the value (one wins) or
None (everyone else).

**Phase 5 — Secondary index cleanup.**

After GETDEL succeeds (meaning this consume "won" the race), the
token id is removed from the ``user_handoffs:{user_id}`` set via
SREM. This is a best-effort cleanup: failures don't abort the
consume (the set has its own TTL and will self-clean within 60s).

### Function `consume_handoff_token`

Verify, consume, and return a handoff result (B.4.12).

The verification sequence:

1. JWT signature verification, with kid-first lookup falling back
   to a trial loop over active signing keys.
2. Atomic single-use enforcement via Redis GETDEL.
3. Best-effort SREM from the per-user secondary index.
4. Host check: request.get_host() matches the organization's
   tenant subdomain per MPH_TENANT_DOMAIN_TEMPLATE.
5. Membership check: an ACTIVE Membership row matches the
   (user, organization) pair from the JWT.

Any failure emits a structured audit event with a reason code and
raises HandoffInvalidError. The caller MUST treat HandoffInvalidError
as "do not establish a tenant session; render a generic error."

Args:
    token: The JWT received from the issuing side.
    request: The HTTP request landing on the tenant subdomain.
        Used for ``request.get_host()`` for the host check.

Returns:
    HandoffResult containing the verified user, org, membership,
    auth method/provider, and MFA satisfaction timestamp.

Raises:
    HandoffInvalidError: verification failed. ``exc.reason`` is one
        of "expired", "invalid", "invalid_signature",
        "not_found_or_replayed", "host_mismatch",
        "membership_inactive", "organization_missing".

### Function `_verify_jwt`

Verify the JWT signature against active signing keys.

Strategy:
1. Read unverified ``kid`` header.
2. If kid present and matches an active key, try that key first.
3. Otherwise, trial-loop over active keys (newest first).
4. Catch expired-token before invalid-signature so the audit
   reason is correct (expired → "expired", bad sig → "invalid_signature").

Returns:
    (payload, used_key_id) tuple on success.

Raises:
    HandoffInvalidError: with reason "expired", "invalid", or
    "invalid_signature".

### Function `_parse_iso_datetime`

Parse an ISO 8601 datetime string.

Python 3.14 datetime.fromisoformat handles full ISO 8601 including
timezone info — no need for python-dateutil here.

## `backend/apps/platform/accounts/handoff/services/_issue.py`

### Module docstring

issue_handoff_token service (B.4.12, M1 D6 Phase 2 + Phase 5).

Mints a JWT signed with the current primary HandoffSigningKey,
writes a Redis nonce keyed by the token id, AND writes the token id
to a per-user secondary index for revocation-on-logout (B.4.17, M1
D6 Phase 5).

Per project posture:
* Keyword-only primitive arguments.
* Single ``transaction.atomic()`` for audit emission. Redis writes
  happen INSIDE the atomic block but are not themselves transactional
  (Redis state isn't undone if the audit emit fails). This is a
  deliberate consistency tradeoff: if audit fails, the Redis nonce
  and index entry expire naturally in 60s, and the token is never
  returned to the caller because the function re-raises. Net effect:
  token is unusable even though the nonce briefly exists.
* Audit emitted inside the atomic boundary.

**Phase 5 — Secondary index ``user_handoffs:{user_id}``.**

Each issue adds the token id to a Redis Set named
``user_handoffs:{user_id}`` so root-domain logout can enumerate
outstanding tokens for revocation. The set is given the same TTL as
the token (refreshed on every SADD) so it self-cleans if no logout
runs. Consume also removes from the set so it stays minimal during
normal flow.

**Known race window:** if a consume completes between SMEMBERS and
DEL during logout, the just-consumed token id is in the revocation
list but its primary key is already gone. The revocation flow
handles this by tolerating DEL of a missing key (Redis returns 0,
not an error). Similarly, if an issue runs concurrently with logout,
its token may not appear in SMEMBERS and thus survive logout. Both
windows are bounded by the 60-second TTL. See M1 D6 retro for the
full analysis.

### Function `issue_handoff_token`

Mint a cross-subdomain handoff token (B.4.12).

The returned string is a signed JWT (HS256). The caller embeds
it in a POST form action targeting the tenant subdomain's
handoff-consume endpoint.

Args:
    user_id: The User the handoff is for.
    organization_id: The target tenant.
    membership_id: The Membership authorizing the handoff. Must
        reference an ACTIVE membership for this user+org.
    auth_method: How the user authenticated on root domain. Must
        be one of "password", "oidc", "oauth2", "impersonation".
    auth_provider: provider_code if OAuth/OIDC, else None.
    mfa_satisfied_at: Wall-clock timestamp of MFA satisfaction.

Returns:
    The signed JWT as an ASCII string.

Raises:
    HandoffInvalidIssueParamError: any parameter failed validation.
    NoActiveHandoffSigningKeyError: no non-retired signing key
        available; operator must rotate a key in.

### Function `_validate_issue_params`

Validate issue parameters; raise HandoffInvalidIssueParamError on failure.

## `backend/apps/platform/accounts/handoff/services/_keys.py`

### Module docstring

HandoffSigningKey lifecycle services (B.4.13.1, M1 D6 Phase 1).

All four mutating services share these properties per project posture:

* Keyword-only primitive arguments.
* Single ``transaction.atomic()`` per call.
* Audit event emitted inside the atomic boundary.
* Actor must be staff or the system user.
* Typed exceptions on failure.

Per B.4.13.1 the active key set is read via the query helper
``active_handoff_signing_keys_ordered_by_created_desc`` rather than
embedded queries — keeping the ordering rule in exactly one place.

### Function `_validate_actor`

Actor must be staff or the system user.

M1 D7 platform-admin UI will supply real staff users; for now,
the System User is accepted so migrations / shell can rotate.

### Function `active_handoff_signing_keys_ordered_by_created_desc`

Return non-retired signing keys, newest first.

The newest non-retired key (index 0) is the primary used for
token issuance. Older non-retired keys (index 1+) are valid for
verification during the rotation overlap.

Returns an empty list if no keys are active — token issuance
will raise; token verification cannot succeed.

### Function `create_handoff_signing_key`

Create a new signing key (lifecycle step 1).

The new key is NOT yet promoted — it cannot verify tokens until
``promote_handoff_signing_key`` is called. This matches B.4.13.1
step 1: "generated but not yet primary."

Args:
    actor_id: User performing the rotation. Must be staff or
        system.
    key_id: Short stable identifier (e.g. "hsk_2026q3"). Must
        match ``_KEY_ID_PATTERN``.

Raises:
    HandoffSigningKeyInvalidIdError: key_id format invalid.
    HandoffSigningKeyAlreadyExistsError: key_id already in use.
    TooManyActiveHandoffSigningKeysError: refusing to create a
        third non-retired key.
    InvalidHandoffActorError: actor is not staff or system.

### Function `promote_handoff_signing_key`

Promote a created key to primary (lifecycle step 2).

After promotion, the key becomes the primary used for issuance.
The previous primary remains active for verification until
``retire_handoff_signing_key`` is called.

Raises:
    HandoffSigningKeyNotFoundError: no such key_id.
    HandoffSigningKeyAlreadyPromotedError: key already promoted.
    HandoffSigningKeyAlreadyRetiredError: key has been retired.
    InvalidHandoffActorError: actor is not staff or system.

### Function `retire_handoff_signing_key`

Retire a promoted key (lifecycle step 4).

A retired key is preserved for audit reconstruction but no
longer used for verification.

Raises:
    HandoffSigningKeyNotFoundError: no such key_id.
    HandoffSigningKeyNotPromotedError: key was never promoted.
    HandoffSigningKeyAlreadyRetiredError: key already retired.
    InvalidHandoffActorError: actor is not staff or system.

### Function `emergency_rotate_handoff_signing_key`

Emergency rotation: create + promote + retire previous primary.

Per B.4.13.1 step 5: "perform steps 1-2 immediately, set the
overlap window to 60 seconds (the maximum token lifetime), then
retire."

In M1 D6 Phase 1, we don't sleep the 60s in-process — that would
block the calling process. The previous primary is retired
immediately; in-flight tokens issued by it will simply fail
verification rather than continue working. **This is a stricter
interpretation of emergency rotation than B.4.13.1 — it cuts
the overlap window to zero rather than 60 seconds.** The
tradeoff is acceptable for emergency response (where the suspected
compromise outweighs in-flight UX) but deviates from the spec.
Tracked in retro.

The emergency-rotation audit event is emitted with the original
key_id (the one being compromised) in metadata.

Raises: any of the exceptions create_/promote_/retire_ raise.

## `backend/apps/platform/accounts/handoff/services/_redis_client.py`

### Module docstring

Redis client factory for handoff nonce storage (M1 D6 Phase 2).

Centralizes the choice of Redis backend so tests can swap in
fakeredis. The choice is made via the ``MPH_HANDOFF_USE_FAKEREDIS``
setting (True in test.py, False everywhere else); the URL is
``MPH_HANDOFF_REDIS_URL`` for the real-Redis case.

We deliberately open a fresh client per call rather than caching a
module-level singleton. Reasons:

* Test isolation: each test gets its own fakeredis instance.
* Connection pooling is already handled by redis-py's per-URL
  default pool.
* Avoids "module-level singleton holds stale connection after Redis
  restart" failure mode in production.

Future optimization (M2+): cache per-process clients keyed by URL
with a connection-health check on retrieval.

### Function `get_handoff_redis_client`

Return a redis-compatible client for handoff nonce storage.

Returns a real ``redis.Redis`` instance in production / dev /
staging, and a ``fakeredis.FakeRedis`` instance when
``MPH_HANDOFF_USE_FAKEREDIS`` is True (test settings).

The returned client supports all commands the handoff services
use: ``set``, ``setex``, ``get``, ``delete``, ``getdel``,
``pipeline``, ``exists``.

### Function `_shared_fakeredis_client`

Return the process-wide fakeredis instance, creating it if needed.

### Function `reset_handoff_fakeredis`

Test helper: flush + recreate the fakeredis singleton.

Called from an autouse pytest fixture to give each test a fresh
in-memory Redis. Never call from production code.

## `backend/apps/platform/accounts/handoff/services/_revoke.py`

### Module docstring

revoke_all_handoff_tokens_for_user service (M1 D6 Phase 5, B.4.17).

Reads the ``user_handoffs:{user_id}`` Redis set, deletes each
``handoff:{tid}`` key, deletes the index set, and emits
``HANDOFF_TOKENS_REVOKED_BY_LOGOUT`` if any tokens were actually
revoked.

Called from the ``user_logged_out`` signal handler on root-domain
logout. Tenant-portal logout does NOT call this — tenant logout
destroys only that tenant's session, not the cross-tenant access
the root session provides.

**Failure mode.** Redis is operationally critical for the handoff
flow. If Redis is unreachable during logout, this function logs at
ERROR and returns 0 (no tokens revoked). The logout itself still
proceeds (the user's session is gone). Outstanding tokens then live
out their 60-second TTL. Net effect: a small window of "user
logged out but old handoff tokens still consumable" — bounded by
the TTL, never worse than the natural expiry.

**Known race window.** A token issued concurrently with revocation
may not appear in SMEMBERS (the SADD landed after the read). That
token survives logout until its own TTL expires. Tracked as a
known limitation for v1; Lua-script atomicity would close it but
adds operational complexity disproportionate to the risk.

### Function `revoke_all_handoff_tokens_for_user`

Revoke all outstanding handoff tokens for a user.

Args:
    user_id: The user whose outstanding tokens should be invalidated.

Returns:
    Number of tokens revoked (0 if none outstanding or Redis is
    unreachable). The return value is informational; the
    ``HANDOFF_TOKENS_REVOKED_BY_LOGOUT`` audit event records the
    same count.

## `backend/apps/platform/accounts/handoff/services/_tenant_session.py`

### Module docstring

establish_tenant_session service (M1 D6 Phase 4B, B.4.14).

Writes the B.4.14-shaped tenant-local session dict and authenticates
the user into the tenant context. Called from the handoff-consume
view after a successful ``consume_handoff_token`` returns a
``HandoffResult``.

Per project posture:
* Owns its own ``transaction.atomic()`` for the audit emit.
* Keyword-only arguments.
* The session itself isn't a DB row in the traditional sense
  (Django's DB-backed session backend persists at request end via
  ``PerTenantSessionMiddleware``), so the "state change" here is
  the in-memory ``request.session`` mutation plus the Django auth
  login. Treating this as a service keeps audit emission consistent
  with other state-change boundaries and makes the consume view thin.

**Session shape per B.4.14:**

The session is populated with:
* ``_auth_user_id``, ``_auth_user_backend``, ``_auth_user_hash`` —
  written by ``django.contrib.auth.login``. Marks the session as
  authenticated for subsequent requests.
* ``mph_session_organization_id`` — the tenant the user is operating
  within. Used by row-level tenancy checks downstream.
* ``mph_session_membership_id`` — the Membership that authorized
  this session. Distinct from organization_id because RBAC scopes
  attach to memberships.
* ``mph_session_auth_method`` — "password", "oidc", "oauth2",
  "impersonation". Read by reauthentication / step-up flows.
* ``mph_session_auth_provider`` — provider_code if OAuth, else None.
* ``mph_session_mfa_satisfied_at`` — ISO 8601 timestamp from the
  handoff token. B.4.10 freshness checks compare against this.

**Why not just login(request, user)?** Django's login alone marks
the session authenticated but doesn't store organization or
membership context. The handoff carried those through; we record
them here so subsequent requests on the tenant subdomain don't
need to re-derive them.

### Function `establish_tenant_session`

Authenticate the user and populate B.4.14 session keys.

Args:
    request: The HTTP request landing on the tenant subdomain
        (the one that consumed the handoff token).
    handoff_result: The verified handoff payload from
        ``consume_handoff_token``. Carries user_id,
        organization_id, membership_id, auth_method,
        auth_provider, mfa_satisfied_at.

Side effects:
    * ``request.session`` is mutated: Django auth keys (via
      ``login()``) + the five B.4.14 session keys above.
    * Audit event ``TENANT_SESSION_ESTABLISHED`` is emitted
      within an atomic block.

Raises:
    UserModel.DoesNotExist: if ``handoff_result.user_id`` no
        longer references a valid user. The caller should
        treat this as a 4xx (the user was deleted between
        handoff issue and consume — extremely rare).

## `backend/apps/platform/accounts/handoff/services/exceptions.py`

### Module docstring

Typed exceptions for the handoff services (M1 D6).

### Class `HandoffSigningKeyError`

Base for signing-key service exceptions.

### Class `HandoffSigningKeyInvalidIdError`

The supplied key_id doesn't match the required format.

The format is enforced because key_id is used as the JWT ``kid``
header and ends up in audit logs; arbitrary user input would
create operational and log-hygiene problems.

### Class `HandoffSigningKeyAlreadyExistsError`

A HandoffSigningKey with this key_id already exists.

### Class `HandoffSigningKeyNotFoundError`

No HandoffSigningKey row with the supplied key_id.

### Class `HandoffSigningKeyAlreadyPromotedError`

promote_handoff_signing_key called on a key already promoted.

### Class `HandoffSigningKeyNotPromotedError`

retire_handoff_signing_key called on a never-promoted key.

Retiring a never-promoted key would orphan it without a clear
audit trail. If the operator really wants to discard a key that
was created in error, they can manually delete the row.

### Class `HandoffSigningKeyAlreadyRetiredError`

retire_handoff_signing_key called on an already-retired key.

### Class `TooManyActiveHandoffSigningKeysError`

Refusing to create a third non-retired key.

B.4.13.1: holding more than two non-retired keys is prohibited.

### Class `InvalidHandoffActorError`

The supplied actor is neither staff nor the system user.

Key rotation is an operational action and requires a privileged
actor. M1 D7's platform-admin UI will supply real staff users;
until then, system-user actors are accepted for migrations and
bootstrapping.

### Class `HandoffTokenError`

Base for token issue/consume exceptions.

### Class `NoActiveHandoffSigningKeyError`

Refusing to issue: no non-retired HandoffSigningKey exists.

The platform admin must rotate in a new key before handoff tokens
can be issued. Without an active signing key, no token can be
cryptographically issued or verified.

### Class `HandoffInvalidIssueParamError`

An issue parameter failed validation.

Causes:
- ``auth_method`` is not in the B.4.14 allowed set.
- ``mfa_satisfied_at`` is in the future.
- ``mfa_satisfied_at`` is absurdly stale (> 1 hour ago).
- ``user_id`` / ``organization_id`` / ``membership_id`` do not
  reference an active membership.

### Class `HandoffInvalidError`

Token consume failed validation.

The ``reason`` attribute carries a stable code suitable for
audit metadata and user-facing error pages. Values:

* ``"expired"`` — JWT exp claim is in the past.
* ``"invalid"`` — JWT structurally malformed or claim set incomplete.
* ``"invalid_signature"`` — no active signing key verified the JWT.
* ``"not_found_or_replayed"`` — Redis nonce missing.
* ``"host_mismatch"`` — request host doesn't match the token's
  organization slug.
* ``"membership_inactive"`` — Membership row no longer ACTIVE.
* ``"organization_missing"`` — Organization referenced by token
  does not exist.

## `backend/apps/platform/accounts/impersonation/__init__.py`

### Module docstring

Support-impersonation subsystem (M1 D7 Phase 4 + Phase 5).

Phase 4 (this phase) — backend primitives only:
* :class:`apps.platform.accounts.impersonation.models.ImpersonationSession`
* :func:`apps.platform.accounts.impersonation.services.start_impersonation`
* :func:`apps.platform.accounts.impersonation.services.end_impersonation`
* Audit codes ``IMPERSONATION_STARTED``, ``IMPERSONATION_ENDED``,
  ``IMPERSONATION_DENIED``.

Phase 5 will add:
* UI surfaces in the platform console (start / list / end views).
* Integration with the handoff flow (impersonation tokens carry
  the admin's identity through to the tenant session).
* Tenant-side recognition (banner, audit context).

Per the project posture, this is a subpackage that owns its own
models. The ``models.py`` here is imported explicitly from
``apps.platform.accounts.apps.AccountsConfig.ready()`` so Django's
app registry picks it up — without that import, ``makemigrations``
would generate spurious ``DeleteModel`` migrations. Same pattern
as ``oauth/`` and ``handoff/``.

## `backend/apps/platform/accounts/impersonation/models.py`

### Module docstring

ImpersonationSession model (M1 D7 Phase 4, B.7).

Records every platform-admin impersonation: who, who, when started,
when ended, why. The lifecycle is created at start, mutated only by
end (writes ``ended_at`` + ``ended_by_user`` + ``end_reason``).

Per project posture:
* UUID v7 primary key.
* No business logic in ``save()`` — services do the state changes.
* All FKs use ``on_delete=PROTECT`` — impersonation history must
  not silently disappear when a user is deleted.
* Constraints enforce the cross-field invariants at the database
  level (admin != target, ended_at >= started_at, the
  "ended-together" pair is set or both null, one active per admin).

The model is in the accounts app's ``impersonation`` subpackage to
match the ``oauth/`` and ``handoff/`` precedent. Discovery from the
app config requires an explicit import in ``apps.py:ready()`` —
without it, ``makemigrations`` generates spurious ``DeleteModel``
migrations because Django's auto-discovery doesn't follow into
sub-package ``models.py``.

### Function `_new_session_uuid`

UUID v7 (Python 3.14+) primary keys for ImpersonationSession.

### Class `ImpersonationEndReason`

How an impersonation session ended (B.7).

### Class `ImpersonationSessionManager`

Manager exposing the active-session lookup.

### Class `ImpersonationSession`

Authoritative record of a single platform-admin impersonation (B.7).

A row is created at impersonation start and mutated only at end.
The session is "active" while ``ended_at IS NULL``; otherwise
closed. Audit events ``IMPERSONATION_STARTED`` and
``IMPERSONATION_ENDED`` correspond to the create + close
transitions.

The session anchors to a specific (target_user, organization,
membership) triple. The membership FK is the strict source of
truth for "what scope was the admin acting in"; the redundant
``organization`` FK is denormalized for fast tenant-scoped
queries (Phase 5 will display "active impersonations in this
org").

All FKs are ``PROTECT``. Impersonation history is audit-grade
data — a user deletion that would orphan an impersonation row
must be blocked. The ``platform_audit.AuditEvent`` rows (M2)
will reference these by ID.

### Function `active_for_admin`

Return the admin's currently-active session, or None.

At most one active session per admin is permitted by the
partial unique index in ``Meta.constraints``. This helper
is the canonical read site for "is this admin currently
impersonating?"

### Function `is_active`

True while ``ended_at`` is null.

## `backend/apps/platform/accounts/impersonation/services/__init__.py`

### Module docstring

Impersonation services (M1 D7 Phase 4).

Two services:
* :func:`start_impersonation` — create a session, audit STARTED.
* :func:`end_impersonation` — close a session, audit ENDED.

Both follow the project service-layer rules (A.4.4):
* Keyword-only primitive arguments.
* Own ``transaction.atomic()`` boundary.
* Audit emission inside the boundary.
* Validation failures audit ``IMPERSONATION_DENIED`` with a reason
  code before re-raising the typed exception.

## `backend/apps/platform/accounts/impersonation/services/_end.py`

### Module docstring

end_impersonation service (M1 D7 Phase 4, B.7).

Closes an active ImpersonationSession by setting ``ended_at``,
``ended_by_user``, and ``end_reason``. Emits IMPERSONATION_ENDED.

Per project service-layer rules (A.4.4):
* Keyword-only primitive arguments.
* Single ``transaction.atomic()`` for the state change + audit.
* SELECT FOR UPDATE locks the session row to prevent concurrent
  end-calls from both succeeding.

### Function `end_impersonation`

End an impersonation session (B.7).

Args:
    session_id: ImpersonationSession.id.
    ended_by_user_id: User ending the session. Can be the
        original admin OR a different staff user (e.g. senior
        admin ending someone else's runaway session). The
        audit event records who.
    end_reason: One of ImpersonationEndReason.choices. Default
        is ADMIN_ENDED. Phase 5 logout-driven end will pass
        ImpersonationEndReason.LOGOUT.

Returns:
    The updated (now-ended) ImpersonationSession.

Raises:
    ImpersonationSessionNotFoundError
    ImpersonationSessionAlreadyEndedError

## `backend/apps/platform/accounts/impersonation/services/_start.py`

### Module docstring

start_impersonation service (M1 D7 Phase 4, B.7).

Creates an ImpersonationSession row, emits IMPERSONATION_STARTED.
On validation failure, emits IMPERSONATION_DENIED with a reason
code and re-raises the typed exception.

Per project service-layer rules (A.4.4):
* Keyword-only primitive arguments.
* Single ``transaction.atomic()`` for the state change + audit.
* Validation failures also audit (within their own atomic block)
  so security-relevant denials are recorded even though no
  session row is created. Matches the M1 D6 HANDOFF_REPLAY_DETECTED
  / HANDOFF_HOST_MISMATCH precedent.

### Function `start_impersonation`

Start an impersonation session (B.7).

### Function `_audit_denied`

Emit IMPERSONATION_DENIED inside its own atomic block.

## `backend/apps/platform/accounts/impersonation/services/exceptions.py`

### Module docstring

Typed exceptions for the impersonation service layer (M1 D7 Phase 4).

Fine-grained types per the project's service-layer pattern. Each
validation failure has its own subclass so callers (and tests) can
discriminate without string-matching error messages.

### Class `ImpersonationError`

Base for all impersonation service-layer errors.

### Class `ImpersonationActorNotStaffError`

The acting admin is not is_staff or is_active.

Only staff users may initiate impersonation (B.7).

### Class `ImpersonationTargetInvalidError`

The target user is not a valid impersonation target.

Covers: user does not exist, is_system, is_staff, or
is_active is False. B.7's strict interpretation: targets must
be regular non-staff users.

### Class `ImpersonationMembershipInvalidError`

The membership does not anchor target+org+ACTIVE status.

The service requires an ACTIVE Membership matching
(target_user_id, organization_id, membership_id). Mismatch
of any of these three values raises this.

### Class `ImpersonationSelfTargetError`

admin_user_id == target_user_id.

DB-level check_constraint backs this up; the service raises
the explicit exception before reaching the DB so the error
message is human-readable.

### Class `ImpersonationReasonRequiredError`

The reason field is empty or below the minimum length.

B.7 requires a recorded business reason. v1 enforces a
minimum length (10 characters after strip) to discourage
"test" / "x" / "asdf" placeholders.

### Class `ImpersonationAlreadyActiveError`

This admin already has an active impersonation session.

DB-level partial unique index backs this up; the service
raises the explicit exception early for a nicer error
message. End the existing session before starting a new one.

### Class `ImpersonationSessionNotFoundError`

No ImpersonationSession matches the given session_id.

### Class `ImpersonationSessionAlreadyEndedError`

The session was already ended (``ended_at IS NOT NULL``).

## `backend/apps/platform/accounts/middleware.py`

### Module docstring

Require-MFA-enrollment middleware (M1 D4 + M1 D5 Phase 4 + M1 D6 Phase 4A).

Enforces B.4.9 enrollment requirements:

* **Local-password user without TOTP** → redirect to enrollment.
* **OAuth/OIDC user via TRUSTED provider** → bypass; provider MFA
  satisfies login MFA per B.4.8.
* **OAuth/OIDC user via UNTRUSTED provider** → redirect to enrollment;
  local step-up MFA is required.
* **Support user** → enrollment required unless the provider is
  explicitly trusted (B.3.11 + B.4.8).

**M1 D6 Phase 4A addition:** when the trusted-provider bypass
applies, also write ``mph_mfa_satisfied_at`` to session. Trusted-
provider OAuth users don't trigger allauth.mfa's ``authenticator_used``
signal (no local challenge), so without this write the picker would
have no satisfaction timestamp for OAuth-only users.

The session write is once-per-session (alongside the existing
audit-emission throttle) so the timestamp doesn't refresh on every
request and defeat the staleness check.

**Audit events emitted by this middleware:**

* ``LOCAL_MFA_CHALLENGE_REQUIRED`` — once per session.
* ``OAUTH_PROVIDER_MFA_TRUSTED`` — once per session.
* ``OAUTH_PROVIDER_MFA_NOT_TRUSTED`` — once per session.

**Why emissions go through ``record_auth_event``.** Middleware
runs outside any request-level transaction (``ATOMIC_REQUESTS=False``).
Calling ``audit_emit`` directly raises ``AuditOutsideTransactionError``.
``record_auth_event`` opens its own ``transaction.atomic()`` and
catches non-programming errors — same pattern allauth signal
handlers use.

### Class `RequireMfaEnrollmentMiddleware`

Force authenticated users to enroll MFA before reaching the app.

### Function `_record_provider_mfa_satisfaction_once`

Write ``mph_mfa_satisfied_at`` for trusted-provider users.

Once-per-session to avoid refreshing the timestamp on every
request (which would defeat downstream staleness checks).
Only writes if the key is absent.

## `backend/apps/platform/accounts/models.py`

### Module docstring

Custom User model (B.3.3).

This is the canonical platform identity. OAuth/OIDC login identities link
to this model; they do not replace it.

Notes on field shape:

* ``id`` is a UUID. UUID v7 (B.3.3 / C.1.1) requires Python 3.14+ where
  ``uuid.uuid7`` is available natively. We use it directly so we don't
  carry a third-party dependency.
* ``email`` is the ``USERNAME_FIELD``. It is normalized to lower case
  in ``UserManager._normalize_email_lower``.
* The TOTP fields, lockout fields, and external-login flag are present
  from migration #1 even though their behavior is wired up in M1. The
  guide is explicit that these belong on the user model from day one
  (B.3.3, J.2.7 #1) so we are not retrofitting columns post-deployment.

Service-layer note: state-changing flows on this model (lockout, TOTP
enrollment, password rotation) all live in service functions added in M1.
This model itself never carries business logic in ``save()``.

### Function `_new_user_uuid`

Return a UUID v7 (Python 3.14+) for the User primary key.

### Class `PreferredAuthMethod`

Hint for which login method this user prefers (B.3.3).

### Class `UserManager`

Custom manager for email-as-username users (B.3.3).

### Class `User`

Canonical platform user (B.3.3).

``USERNAME_FIELD = "email"``. ``REQUIRED_FIELDS = []``.

### Function `create_superuser`

Create a superuser AND auto-install a verified EmailAddress.

M1 D7 Phase 1 — Ergonomics fix. Settings include
``ACCOUNT_EMAIL_VERIFICATION = "mandatory"`` per the production
posture, which means every login by a user without a verified
``allauth.account.models.EmailAddress`` row is bounced to the
email-confirmation flow. For the bootstrap superuser, this is a
chicken-and-egg blocker (no Mailpit, no SMTP, can't sign in
to configure either).

Calling :func:`ensure_verified_email_address` here makes the
bootstrap superuser able to sign in immediately after
``createsuperuser`` completes. The function is idempotent, so
re-running the management command doesn't double-create.

This catches both the CLI ``createsuperuser`` path AND any
programmatic superuser creation (dev scripts, tests) — the
hook is at the manager method rather than at the management
command, so all paths to superuser get the verified
EmailAddress.

## `backend/apps/platform/accounts/oauth/__init__.py`

### Module docstring

OAuth/OIDC integration for the accounts app (M1 D5).

Houses:

* :class:`OAuthProviderConfig` — platform-managed configuration row
  for each approved OAuth/OIDC provider (B.3.7).
* :class:`ExternalIdentityClaims` — normalized, immutable shape that
  the rest of the auth code consumes (B.3.8). Raw provider claims
  MUST NOT be passed to business logic.
* :func:`normalize_socialaccount_claims` — translates allauth's
  ``SocialLogin`` into our normalized shape.
* :func:`load_socialaccount_providers` — at startup, reads active
  ``OAuthProviderConfig`` rows and produces the
  ``SOCIALACCOUNT_PROVIDERS`` dict allauth expects.

The :func:`resolve_external_user` service (B.4.6) lives in the
``services`` package alongside ``register_local_user`` and
``record_auth_event``; it lands in Phase 2.

## `backend/apps/platform/accounts/oauth/adapter.py`

### Module docstring

MPH social-account adapter for django-allauth (M1 D5 Phase 3).

This adapter is the HTTP boundary between allauth's OAuth/OIDC flow
and our :func:`resolve_external_user` service. Allauth invokes
``pre_social_login`` once a provider callback has validated cryptographically
(state, nonce, ID token signature, issuer, audience, expiry per B.4.5) and
before allauth proceeds to associate the social account with a User row.

Our override does the following inside ``pre_social_login``:

1. Build :class:`ExternalIdentityClaims` from the inbound
   ``SocialLogin`` via :func:`normalize_socialaccount_claims`.
2. Load the matching :class:`OAuthProviderConfig` row.
3. Call :func:`resolve_external_user` to enforce B.4.6 / B.4.7
   linking policy and return the canonical User.
4. On success: mutate ``sociallogin.user`` to point at the resolved
   User so allauth proceeds with that user.
5. On a typed exception: emit ``OAUTH_LOGIN_FAILED`` with a
   ``failure_reason`` metadata, then raise
   :class:`ImmediateHttpResponse` redirecting to the help page.

**Why ImmediateHttpResponse and not return None.** Returning None
tells allauth "no objection, proceed." Raising ImmediateHttpResponse
is the documented way to halt the flow and force a redirect from
inside the adapter callback.

**Cached System User actor id.** The service requires an actor_id.
At pre_social_login time no user is authenticated (that's the entire
point of this hook firing before authentication). We use the System
User per B.3.10. The id is cached on the adapter class after first
lookup to avoid a DB hit per OAuth callback.

### Class `MphSocialAccountAdapter`

Allauth socialaccount adapter implementing MPH policy.

Configured via the ``SOCIALACCOUNT_ADAPTER`` setting in base.py.

### Function `_get_system_actor_id`

Return the System User id, caching after first lookup.

Raises:
    User.DoesNotExist: if no System User exists. This indicates
    the seed migration didn't run; the OAuth callback cannot
    proceed safely without a system actor.

### Function `_reset_system_actor_id_cache`

Test helper: clear the cached System User id.

Tests that re-seed the DB or test the cache-miss path can
invoke this to force a fresh lookup. Never called in
production code.

### Function `pre_social_login`

Enforce B.4.6 / B.4.7 linking policy via resolve_external_user.

Args:
    request: The HTTP request mid-callback.
    sociallogin: Allauth's SocialLogin instance. Has ``.account``
        (SocialAccount with provider/uid/extra_data) and
        ``.user`` (in-flight User, possibly unsaved).

Side effects:
    * Emits ``OAUTH_LOGIN_STARTED`` (every call).
    * Emits ``OAUTH_LOGIN_FAILED`` on typed exception.
    * On success, swaps ``sociallogin.user`` to the resolved
      canonical User. Allauth then proceeds with login on
      that user.

Raises:
    ImmediateHttpResponse: on any typed exception, to halt
        allauth and redirect to the help page.

### Function `_emit_failure`

Emit OAUTH_LOGIN_FAILED with the structured failure reason.

The reason value is from the closed set in
``_EXCEPTION_TO_FAILURE_REASON``, so the audit catalog stays
consistent and queryable.

### Function `_render_help_redirect`

Redirect to the OAuth help page for a given failure reason.

The help-page view (apps.web.auth_portal.views_oauth_help)
validates the slug against an allowlist before rendering.

## `backend/apps/platform/accounts/oauth/claims.py`

### Module docstring

Normalized external-identity claims (B.3.8).

Provider claims arrive from allauth in a variety of provider-specific
shapes. The application MUST normalize them into a small internal
shape before account resolution (B.3.8). This module owns that shape
and the translator.

**Why normalize.** B.3.8 is explicit: "Raw provider claims MUST NOT be
used directly in authorization decisions." If business logic reads
``sociallogin.account.extra_data["email"]`` directly, it's coupled to
the provider's claim layout. Normalization moves that coupling into
one place (this module) where it can be tested, audited, and changed
without rippling.

**What's safe to put in raw_claims.** The raw_claims dict is retained
so service code can introspect provider-specific fields when
necessary (e.g. for support debugging). However, raw_claims MUST NOT
contain tokens, authorization codes, refresh tokens, ID tokens, or
client secrets. Allauth's ``SocialLogin.account.extra_data`` already
excludes tokens by default, so we copy it as-is.

**What's NOT in this dataclass.** No access tokens, no refresh
tokens, no ID tokens. Per B.5.6 #6: "Provider tokens MUST NOT be
stored unless explicitly required." We don't store them. Allauth's
``SocialToken`` may persist them in some configurations, but our
normalized claims object never carries them.

### Class `ExternalIdentityClaims`

B.3.8 normalized claims shape.

All fields are read-only after construction. The raw_claims dict
is shallow-copied at construction time so callers can't mutate it
via reference.

NOTE: B.3.8 specifies `raw_claims: Mapping[str, Any]`. We use
`dict[str, Any]` so the copy-on-construct semantics are explicit;
the read-only contract is preserved by the dataclass freeze.

### Function `_coerce_amr`

Normalize provider AMR to a tuple of strings.

### Function `_coerce_email_verified`

Extract email_verified across provider variations.

OIDC standard: ``email_verified`` boolean.
Google: ``email_verified`` boolean (compliant).
Microsoft (Azure AD): no ``email_verified``; trust ``email`` from
``upn``/``preferred_username`` if present.
GitHub: ``email`` is verified iff returned by the verified-emails
endpoint, but allauth's GitHub adapter doesn't always surface it.

Default policy: ``email_verified`` claim is the source of truth.
If absent, treat as False. Providers we explicitly trust to skip
this check declare so via ``OAuthProviderConfig.require_verified_email``
— but the *claim* itself stays False here; the policy decision
happens in :func:`resolve_external_user` (Phase 2).

### Function `normalize_socialaccount_claims`

Translate an allauth ``SocialLogin`` into our normalized shape.

Called by the social-account adapter's ``pre_social_login`` hook
(Phase 3). Returns an immutable, business-logic-safe view.

Args:
    sociallogin: allauth's ``SocialLogin`` instance. Has
        ``.account`` (the ``SocialAccount``) and ``.user`` (the
        in-flight ``User``, possibly unsaved). We read claims
        from ``account.extra_data`` and the account's ``provider``
        and ``uid``.

Returns:
    :class:`ExternalIdentityClaims` with provider_code, provider_uid,
    normalized email, email_verified, optional display_name, acr/amr
    if present, and a sanitized raw_claims copy.

## `backend/apps/platform/accounts/oauth/loader.py`

### Function `_read_env_secret`

Read an env var; return None if missing/empty.

Centralized so future changes (e.g. reading from a secret manager
instead of os.environ) happen in one place.

### Function `_build_openid_connect_app`

Build the per-provider 'APPS' entry for an OIDC provider.

Returns None if the env-backed credentials aren't available; the
caller skips the provider.

### Function `load_socialaccount_providers`

Build the SOCIALACCOUNT_PROVIDERS dict from active configs.

Called at app-ready time from
``apps.platform.accounts.apps.AccountsConfig.ready()`` (Phase 3
wires this).

Returns:
    A dict in allauth's ``SOCIALACCOUNT_PROVIDERS`` shape. May be
    empty if no providers are active or all active providers are
    missing env credentials.

### Function `apply_socialaccount_providers_to_settings`

Mutate ``django.conf.settings.SOCIALACCOUNT_PROVIDERS`` in place.

Called from ``AccountsConfig.ready()``. Safe to call multiple times
(idempotent); each call rebuilds the dict from scratch.

Note on settings mutation: Django settings are read-only by
contract, but ``SOCIALACCOUNT_PROVIDERS`` is consumed by allauth
at runtime (not at import time), so mutating it after Django has
finished loading works. The alternative (database-backed allauth
apps via ``SocialApp``) requires Django Sites + admin management
we don't want at this stage.

## `backend/apps/platform/accounts/oauth/models.py`

### Module docstring

OAuthProviderConfig model (B.3.7).

Platform-managed configuration for an approved OAuth/OIDC provider.

**Secrets are NOT stored in this model.** The model holds the *env-var
key names* (``client_id_env_key``, ``client_secret_env_key``); the
loader reads ``os.environ.get(<key_name>)`` at runtime to obtain the
actual credentials. This keeps secrets out of database backups, the
audit trail, and admin pages — matching B.5.5 ("Client secret loaded
from approved secret source").

**Tenant-managed provider config is deferred** — B.3.7 makes this
explicit. The model is platform-tier; there is no ``organization``
FK.

**Field shape mirrors B.3.7 exactly**, with one M1 D5 extension:

* ``allow_self_registration: BOOL, default(False)`` — per-provider
  policy hook for B.4.6 step 4 ("create a global ``User`` only if
  platform policy allows external self-registration"). Default is
  invitation-only. Flagged in the M1 D5 retro as a deviation from
  B.3.7's exact field list.

**`scopes` and `allowed_email_domains` use Postgres ArrayField.**
The guide specifies TEXT[]; ArrayField is the Django equivalent.
``django.contrib.postgres`` is required in ``INSTALLED_APPS``.

### Function `_new_provider_config_uuid`

UUID v7 (Python 3.14+) for the provider config primary key.

### Class `ProviderType`

B.3.7: provider_type ENUM(OIDC, OAUTH2).

### Class `OAuthProviderConfig`

Platform-managed OAuth/OIDC provider configuration (B.3.7).

Approval lifecycle (M1 D5 — informally enforced):

1. Platform admin creates the row with ``is_active=False``.
2. Security review confirms callback URL, provider MFA posture,
   allowed domains.
3. Platform admin flips ``is_active=True``.

The loader at startup only includes rows where ``is_active=True``
in allauth's ``SOCIALACCOUNT_PROVIDERS`` config. An inactive row
is invisible to login flows.

### Function `clean`

Cross-field validation.

Runs only via ModelForm / explicit ``full_clean()``. We do
NOT enforce these as DB CHECK constraints because the rules
are easier to reason about as Python — and B.3.7 doesn't
require them at the DB level.

## `backend/apps/platform/accounts/oauth/signals.py`

### Module docstring

Allauth socialaccount signal handlers (M1 D5 Phases 3, 4, 5).

Maps allauth's socialaccount signals to B.4.19 audit events and
writes the post-login session key the middleware reads.

Successful-login paths (Phase 3, Phase 4):
* ``social_account_added`` → OAUTH_LOGIN_SUCCEEDED (first-time link);
  also writes the provider-code session key for the MFA enrollment
  middleware (Phase 4).
* ``social_account_updated`` → OAUTH_LOGIN_SUCCEEDED (repeat login);
  same session-key write.

Unlink path (Phase 3):
* ``social_account_removed`` → OAUTH_ACCOUNT_UNLINKED.

Pre-adapter failure paths (Phase 5):
* ``social_account_login_failed`` (provider returned an error /
  cryptographic validation failed) → OAUTH_LOGIN_FAILED with
  failure_reason='authentication_error'.
* (Login cancellation is handled by the user-facing template only —
  allauth doesn't fire a dedicated signal for cancellation that
  carries enough context for an audit event. Tracked in retro.)

Note: ``pre_social_login`` is intentionally not wired here. The
adapter (Phase 3) emits ``OAUTH_LOGIN_STARTED`` directly with full
claims context the signal payload doesn't carry.

### Function `_write_login_provider_code_to_session`

Store the login provider code on the session.

Read by :class:`RequireMfaEnrollmentMiddleware` to determine
whether to bypass or force local TOTP enrollment.

If the request has no ``session`` attribute (unusual for a real
HTTP request, but possible for synthetic signals from tests),
silently skip — the middleware will treat the absence as a
local-password login and force enrollment, which is the safe
default.

### Function `_on_social_account_added`

First-time SocialAccount creation for a User.

Emits OAUTH_LOGIN_SUCCEEDED. The OAUTH_ACCOUNT_LINKED event is
already emitted by :func:`resolve_external_user` from inside the
service's atomic boundary; this signal-side emission is the
*login outcome* counterpart.

Also writes the login provider code to the session so the MFA
enrollment middleware can apply the trusted-provider policy.

### Function `_on_social_account_removed`

SocialAccount unlinking — B.4.18.

Emits OAUTH_ACCOUNT_UNLINKED. The actor is the user themselves
(only the account owner can unlink); pre-emption-by-admin
unlinking happens through a separate platform-tier flow which
will emit the same event with a different actor in M1 D7.

### Function `_on_social_account_updated`

Repeat-login on an existing SocialAccount.

Emits OAUTH_LOGIN_SUCCEEDED. This is the success marker for
every OAuth login AFTER the first. allauth fires this signal
on each successful repeat OAuth login, BEFORE user_logged_in.

Also writes the login provider code to the session so the MFA
enrollment middleware can apply the trusted-provider policy.

### Function `_on_social_account_login_failed`

Provider returned an error to the callback.

Causes include:
  - state/nonce mismatch (CSRF defense, B.4.5),
  - ID token signature failure (B.4.5),
  - provider-side error response,
  - network failure mid-callback.

Emits OAUTH_LOGIN_FAILED with failure_reason='authentication_error'.
The exception type is captured in metadata for support
debugging, but the exception MESSAGE is not — exception
messages can contain tokens or other sensitive data from
provider responses (B.4.19 / G.5.5).

## `backend/apps/platform/accounts/services/__init__.py`

### Module docstring

Account service layer (M1 D4 + M1 D5).

Public API:

* :func:`register_local_user` (M1 D4) — create a canonical User row
  for local-password authentication.
* :func:`record_auth_event` (M1 D4) — single service entry for
  allauth signal handlers to emit auth audit events.
* :func:`resolve_external_user` (M1 D5) — resolve or link an
  OAuth/OIDC identity to a canonical User per B.4.6 / B.4.7.

Service-layer rules (A.4.4):

* Functions accept primitive arguments (UUIDs, strings, decimals).
* Functions own their transaction boundaries via ``transaction.atomic(...)``.
* Audit events are emitted via :func:`apps.platform.audit.services.audit_emit`
  inside the same atomic boundary as the state change they describe.

Exceptions (defined in :mod:`apps.platform.accounts.services.exceptions`):

M1 D4:
* :exc:`UserAlreadyExistsError` — email collision on registration.
* :exc:`UserNotFoundError` — caller referenced a nonexistent user.

M1 D5:
* :exc:`UserInactiveError` — matched user has is_active=False.
* :exc:`ProviderNotActiveError` — provider config is_active=False.
* :exc:`EmailNotVerifiedError` — provider didn't assert verified email.
* :exc:`EmailDomainNotAllowedError` — domain not in allowlist.
* :exc:`ConflictingExternalIdentityError` — existing different external
  identity for same provider.
* :exc:`NoExistingUserAndSelfRegistrationDisabledError` — no match and
  self-registration disabled.
* :exc:`LinkingNotAllowedError` — reserved for B.4.7 #5 (invite flow);
  not raised in M1 D5.

## `backend/apps/platform/accounts/services/_audit.py`

### Module docstring

Authentication-event audit service (M1 D4).

This is the single service-layer entry point used by allauth signal
handlers (in :mod:`apps.platform.accounts.signals`) to emit
authentication audit events. The signal handlers themselves contain
zero business logic; they translate allauth's signal payload into a
call to :func:`record_auth_event`, which owns the transaction
boundary and the actual ``audit_emit`` call.

**Why this layer exists**

The project rule (A.4.4) is that ``apps/*/services/`` is the sole
state-change boundary. ``audit_emit`` is a state change in the
audit-trail sense, and it requires an open ``transaction.atomic()``.
Allauth signals fire outside any service's atomic block, so each
signal handler needs *some* boundary. Rather than have every handler
open its own ``transaction.atomic()`` and call ``audit_emit`` inline
(which would scatter audit-emission logic across many files), we
funnel all of them through this one service.

**Signal handlers are exempt-equivalent.** They live in ``signals.py``,
not in ``services/``, so the service-discipline AST check
(``scripts/check_service_layer_discipline.py``) treats them like
views — they MUST NOT make ORM writes. The only call they make
into the platform is :func:`record_auth_event`, which IS in
``services/`` and owns the transaction.

**Failure isolation.** A failure inside ``record_auth_event`` MUST
NOT abort the originating auth flow. Allauth's signal dispatch is
synchronous; a raise propagates up. The function therefore swallows
``Exception`` after logging it, with the documented exception of
``AuditOutsideTransactionError`` and ``UnknownAuditEventError`` which
are programming errors and re-raise (these surface in tests, not in
production where the recording stub is off).

### Function `record_auth_event`

Emit an authentication-related audit event from a signal handler.

Owns its own ``transaction.atomic()`` boundary so allauth signal
handlers can call it without holding a transaction. This is the
only service in the codebase that is permitted to be invoked from
a signal handler (A.4.4 documents the carve-out for audit
fan-out).

Args:
    event_type: Must be present in ``_KNOWN_EVENT_TYPES``. See
        B.4.19 for the catalog of authentication codes.
    actor_id: UUID of the User the event is *about*. For
        ``LOGIN_FAILED`` and ``ACCOUNT_LOCKED`` this may be None
        (e.g. credentials with no matching user) — pass None and
        put the attempted email in ``metadata``.
    organization_id: Always None for platform-tier auth events.
        Reserved for future per-tenant auth events (e.g. if a
        login is scoped to an org context).
    object_kind: Optional dotted model label.
    object_id: Optional stringified id of the affected object.
    metadata: Free-form metadata. Must NEVER contain:
        cleartext passwords, OAuth tokens, ID tokens, refresh
        tokens, authorization codes, TOTP secrets, recovery codes,
        CSRF tokens, session keys. Per B.4.19 + G.5.5.

Raises:
    UnknownAuditEventError: registered as a programming error and
        re-raised. Indicates a typo in the signal handler.
    AuditOutsideTransactionError: re-raised. Indicates this
        function failed to open its own transaction — would
        be a Django/library bug.

Behavior on any other exception: logged at WARNING and swallowed,
so an audit-stub hiccup never breaks login.

## `backend/apps/platform/accounts/services/_register.py`

### Module docstring

Local-user registration service (M1 D4).

This service creates a canonical :class:`apps.platform.accounts.User`
row for a user who will authenticate with a local password. It is the
authoritative service-layer entrypoint for:

1. The seed_dev_tenant management command (currently uses
   ``User.objects.create_user`` directly; tracked in the M1 retro as a
   follow-up to migrate to this service).
2. The future invite-acceptance flow (M1 D5+).

OAuth/OIDC-only users follow a different path: they are created by
``resolve_external_user`` (B.4.6) during the OAuth callback, with
``external_login_only=True`` and an unusable password. That service
lands in M1 D5; this one is local-password only.

**Service contract** (A.4.4):

* Keyword-only primitive arguments.
* Single ``transaction.atomic()`` boundary.
* ``audit_emit("USER_REGISTERED", ...)`` inside the boundary.
* Typed exceptions for the two distinguishable failure modes.
* Does NOT create a Membership. Tenant membership is bootstrapped
  separately by ``assign_owner_membership`` or the invite flow.

**Security notes:**

* Email is normalized to lowercase (B.3.3 CHECK constraint).
* Password validation runs Django's configured validators (B.5.2).
* ``password_changed_at`` is stamped so the rotation policy (B.5.3)
  has an anchor.
* The cleartext password is NEVER logged. The audit payload contains
  only the user id, normalized email, and a boolean
  ``password_was_set``; the password itself never enters the audit
  trail.

### Function `_validate_email_shape`

Lightweight email shape check; full normalization happens at write.

### Function `register_local_user`

Create a canonical User for local-password authentication (B.3.3).

Steps performed inside a single ``transaction.atomic()``:

1. Validate the email shape.
2. Confirm the actor exists.
3. Validate the password against Django's configured validators
   (B.5.2: 12-char minimum, common-password check, etc.).
4. Reject if the email is already taken (case-insensitively).
5. Create the User row with a hashed password and stamp
   ``password_changed_at`` (anchor for B.5.3 rotation policy).
6. Emit ``USER_REGISTERED`` audit event. The audit payload does
   NOT contain the cleartext password — only the user id and
   normalized email.

Args:
    email: User-supplied email. Normalized to lowercase before
        persistence.
    password: Cleartext password. Validated; never logged.
    actor_id: UUID of the User performing the registration. For
        self-signup flows the user has just registered themselves;
        the calling view passes the newly-created allauth user id
        *after* allauth has run its own create. For the future
        invite-acceptance flow this is the invitee's id once
        email verification completes. For system bootstrap
        (seed_dev_tenant) it is the System User id.
    is_active: Whether the user is immediately able to log in.
        Defaults True. Pass False for invite-pending accounts that
        need a verification step first.

Returns:
    The newly created User.

Raises:
    ValidationError: input fails validation (email shape, password
        policy). No DB writes occur in this case.
    UserAlreadyExistsError: email is already taken.
    UserNotFoundError: actor_id does not exist.

## `backend/apps/platform/accounts/services/_resolve_external.py`

### Module docstring

resolve_external_user — OAuth/OIDC user resolution service (B.4.6, B.4.7).

This is the *single* chokepoint where an external (OAuth/OIDC) identity
becomes a canonical platform User. Every callback flow MUST go through
this function. No other code may create a SocialAccount or link an
external identity to a User.

**Resolution order (B.4.6):**

1. Validate provider is active.
2. Validate email-domain allowlist.
3. Validate email-verification policy.
4. Subject-ID lookup. If the (provider_code, provider_uid) pair
   already maps to a SocialAccount → return the linked User.
5. Email-based linking. If verified email matches an existing User
   and there's no conflicting external identity for the same provider
   → link and return.
6. Self-registration. If the provider config allows self-registration
   → create a new external-only User and link.
7. Otherwise → raise NoExistingUserAndSelfRegistrationDisabledError.
   This is the "no active access / invitation required" exit point.

**B.4.7 silent-linking rules — what this service enforces:**

Per the guide, silent account linking based only on email is prohibited
unless ALL of:

1. provider email is verified → enforced at step 3.
2. provider is active and approved → enforced at step 1.
3. provider config allows email-based linking → enforced by the
   combination of step 3 (verified email) AND step 5 (only proceeds
   when the email is verified).
4. no conflicting existing external identity exists → enforced at step 5.
5. user is completing an invite flow or passes a local confirmation
   challenge → NOT enforced here. This is a UI-level rule that lives
   in the adapter/invite-flow layer. The service is strict on the
   first four; the fifth is a soft control above the service. Tracked
   in the M1 D5 retro deviation log.

**Side effects:**

* MAY create a SocialAccount.
* MAY create a User (only when self-registration is allowed).
* MUST emit OAUTH_ACCOUNT_LINKED when a SocialAccount is created.
* MUST emit USER_REGISTERED when a User is created.
* MUST NOT create, modify, or delete Membership / Role / Capability rows
  (B.3.9).
* MUST NOT store tokens.
* MUST NOT modify is_staff / is_superuser based on provider claims.

### Function `_strip_sensitive`

Return a copy of extra_data with sensitive keys removed.

### Function `_email_domain`

Extract domain from a normalized lowercase email.

### Function `_domain_allowed`

True iff allowed_domains is None/empty OR email's domain is listed.

Matching is case-insensitive (domains in the provider config are
expected lowercase; we lowercase the email's domain anyway for
defense in depth).

### Function `_has_conflicting_external_identity`

Does this user have a DIFFERENT SocialAccount for the same provider?

B.4.7 #4: "no conflicting existing external identity exists."
Same provider, different uid = conflict. Two different providers
(e.g. google + microsoft) = NOT a conflict; users can have both.

### Function `resolve_external_user`

Resolve or link an OAuth/OIDC identity to a canonical User (B.4.6).

See module docstring for the full algorithm and B.4.7 rule mapping.

Args:
    claims: Normalized provider claims (B.3.8). Built by
        ``normalize_socialaccount_claims`` (Phase 1).
    provider_config: The OAuthProviderConfig row whose
        ``provider_code`` matches ``claims.provider_code``. Caller
        (the adapter) is responsible for loading the right config
        for the inbound claim.
    actor_id: System User id during the callback flow. The
        *resolution* is a system action (the application decides
        who the user is); the subsequent *login* event has
        ``actor_id=user.id`` and lives in the Phase 4 signal
        handler.

Returns:
    The canonical User. Caller (the adapter) is responsible for
    calling allauth's login mechanics on this user.

Raises:
    ProviderNotActiveError: provider_config.is_active=False.
    EmailDomainNotAllowedError: email's domain isn't in the
        provider's allowed_email_domains.
    EmailNotVerifiedError: provider requires verified email and
        the provider didn't assert verification.
    ConflictingExternalIdentityError: a different SocialAccount
        for the same provider already links to the candidate user.
    UserInactiveError: matched user has is_active=False.
    NoExistingUserAndSelfRegistrationDisabledError: no existing
        user and the provider doesn't allow self-registration.
    ValueError: actor_id is missing or provider_code mismatch
        between claims and config (a programming error).

### Function `_update_socialaccount_extra_data`

Touch the SocialAccount with the latest provider claims.

Strips sensitive keys defensively. Wraps in atomic() so the write
is committed before the caller's allauth login flow proceeds.

### Function `_link_socialaccount_to_user`

Create a SocialAccount row linking claims to the given user.

Emits OAUTH_ACCOUNT_LINKED inside the atomic boundary.

Raises:
    ConflictingExternalIdentityError if a race created a SocialAccount
    between the existence check and the create. Re-raised as the
    same typed exception so callers branch identically.

### Function `_create_external_user_and_link`

Create a new external-only User and link the SocialAccount.

Only called when ``provider_config.allow_self_registration=True``
AND no existing user matches by email OR subject ID.

The new User:
  - has the verified email from claims as ``email``,
  - has ``external_login_only=True`` (B.3.4),
  - has an unusable Django password,
  - is is_active=True,
  - is NOT is_staff or is_superuser.

Emits both USER_REGISTERED and OAUTH_ACCOUNT_LINKED inside the
atomic boundary.

## `backend/apps/platform/accounts/services/exceptions.py`

### Module docstring

Typed exceptions for the accounts service layer.

Pattern mirrors :mod:`apps.platform.organizations.services.exceptions`:

* ``LookupError`` subclasses for missing records.
* ``ValueError`` subclasses for business-rule violations.

These are part of the public service contract — caller code branches
on them.

### Class `UserNotFoundError`

Raised when a service references a User id that does not exist.

### Class `UserAlreadyExistsError`

Raised when registering a local user with an email that already exists.

The collision is detected before any DB write; the caller can branch
cleanly between "send password reset" vs. "first-time registration".

### Class `UserInactiveError`

Raised when the resolved User has ``is_active=False``.

The login MUST stop and the user MUST NOT be authenticated. The
adapter (Phase 3) maps this to the same "no active access" exit
as the no-existing-user case.

### Class `ProviderNotActiveError`

Raised when the OAuthProviderConfig has ``is_active=False``.

This indicates the provider was deactivated after a callback URL
was already issued. The login MUST stop; the user-facing message
is the standard "credentials invalid" exit.

### Class `EmailNotVerifiedError`

Raised when the provider didn't assert email_verified=true and the
provider config requires it (B.5.6 #1).

The login MUST stop. The user-facing message is "please verify your
email at the provider, then try again."

### Class `EmailDomainNotAllowedError`

Raised when the user's email domain isn't in the provider's
allowed_email_domains list (B.4.5).

The login MUST stop. The user-facing message is generic
("this account isn't permitted via that provider") to avoid
leaking the allowlist.

### Class `ConflictingExternalIdentityError`

Raised when an existing User has a different external identity
for the same provider (B.4.7 #4).

Example: the user has a SocialAccount linking
``(google-workspace, old-subject-id)`` to their account, but the
callback now arrives with ``(google-workspace, new-subject-id)``
for an email that matches the same user. This could be a legitimate
provider-side migration OR an account-takeover attempt. Resolution
requires manual support intervention (per B.4.7).

The adapter (Phase 3) maps this to the account-linking help flow.

### Class `NoExistingUserAndSelfRegistrationDisabledError`

Raised when there's no matching User by subject ID OR email, and
the provider config has ``allow_self_registration=False``.

The adapter (Phase 3) maps this to the "no active access /
invitation required" exit page — the same page rendered when a
user has zero memberships (B.4.4 branch 12a).

### Class `LinkingNotAllowedError`

Reserved for B.4.7 #5 — "user is completing an invite flow or
passes a local confirmation challenge."

Not raised in M1 D5 because B.4.7 #5 is enforced one level up
(in the adapter / invite-flow). Defined here so the typed-exception
surface is stable when M2 wires the invite flow.

## `backend/apps/platform/accounts/signals.py`

### Module docstring

Allauth signal handlers for authentication audit events (M1 D4).

These handlers are thin adapters. They:

1. Receive an allauth signal.
2. Extract the user id and event-relevant metadata.
3. Call :func:`apps.platform.accounts.services.record_auth_event`.

They MUST NOT contain business logic, MUST NOT make ORM writes
directly, and MUST NOT log sensitive data (B.4.19, G.5.5).

The set of handled signals maps to B.4.19's authentication audit
event catalog:

* ``user_logged_in``         → ``LOCAL_PASSWORD_LOGIN_SUCCEEDED`` + ``LOGIN_SUCCEEDED``
* ``user_login_failed``      → ``LOCAL_PASSWORD_LOGIN_FAILED`` + ``LOGIN_FAILED``
* ``user_logged_out``        → ``LOGOUT``
* ``user_signed_up``         → ``USER_REGISTERED`` (when self-signup is allowed)
* ``email_confirmed``        → ``EMAIL_VERIFIED``
* ``email_confirmation_sent``→ ``EMAIL_VERIFICATION_SENT``
* ``password_changed``       → ``PASSWORD_CHANGED``
* ``password_reset``         → ``PASSWORD_RESET_COMPLETED``
* ``password_set``           → ``PASSWORD_CHANGED`` (first-time set after invite)
* ``authenticator_added``    → ``MFA_ENROLLED``
* ``authenticator_removed``  → ``MFA_DISABLED``

Signals are connected by ``AccountsConfig.ready()``.

**OAUTH_* and HANDOFF_* events are intentionally NOT wired here.**
They land in M1 D5 (OAuth provider integration) and M1 D6 (handoff
token issuance) respectively.

**ACCOUNT_LOCKED is also NOT wired here.** Allauth doesn't emit a
distinct lockout signal — the lockout decision is made internally
during login_failed. The full B.5.4 dual-tier policy needs a custom
rate limiter; an interim ACCOUNT_LOCKED emission lands as part of
that work. Tracked in M1 retro as a follow-up.

### Function `_user_id`

Safely extract a user's UUID; return None if missing.

### Function `_safe_metadata`

Build a metadata dict that includes only NON-SENSITIVE values.

Per B.4.19 / G.5.5, we MUST NOT include passwords, tokens,
authorization codes, TOTP secrets, recovery codes, CSRF tokens,
session keys, or full request headers.

What IS safe to include: client IP, user agent, route path,
method, and the allauth event-specific extras passed in.

### Function `on_user_logged_in`

Fires after a successful login (any method).

Allauth fires this once. We emit BOTH the generic LOGIN_SUCCEEDED
and the method-specific LOCAL_PASSWORD_LOGIN_SUCCEEDED because
B.4.19 catalogs both. The distinction matters: an OAuth login
will emit LOGIN_SUCCEEDED + OAUTH_LOGIN_SUCCEEDED instead (M1 D5).

For M1 D4 (local-only), every successful login is a local
password login.

### Function `on_user_login_failed`

Fires when authentication credentials fail.

The ``credentials`` dict from allauth contains the *attempted*
identifier (usually email). We include only the email field; the
password field is NEVER touched.

### Function `on_user_logged_out`

Fires when a user logs out.

### Function `on_user_signed_up`

Fires after allauth-driven self-signup.

This is a *secondary* code path. Production registration goes
through ``register_local_user`` (the service) and emits the
USER_REGISTERED event itself, inside the service's atomic block.
But allauth's built-in signup view bypasses our service (it does
its own ``User.objects.create_user`` under the hood), and emits
``user_signed_up`` after. We catch that here so the audit event
fires regardless of which signup path was used.

De-duplication: if both signal-driven AND service-driven emissions
fire for the same user, that's two USER_REGISTERED events.
Acceptable in M1 because allauth signup is gated behind email
verification (B.4) and our service is the only path used by
seed_dev_tenant / invite-acceptance.

### Function `on_email_confirmation_sent`

Fires when allauth sends a verification email.

### Function `on_email_confirmed`

Fires when a user confirms an email address.

### Function `on_password_changed`

Fires when an authenticated user changes their password.

### Function `on_password_set`

Fires when a user sets a password for the first time
(e.g. after invite acceptance, or after linking an external identity).

### Function `on_password_reset`

Fires when a user completes the password-reset flow.

### Function `register_signal_handlers`

No-op marker called from AccountsConfig.ready().

The @receiver decorators above register the handlers at module
import time. This function exists so AccountsConfig.ready() has
an explicit hook to import this module, which is what actually
triggers the receivers to bind. Without that import, the signals
never connect.

### Function `on_authenticator_added`

Fires when a user enrolls a new MFA authenticator (TOTP, recovery codes).

### Function `on_authenticator_removed`

Fires when a user disables an MFA authenticator.

## `backend/apps/platform/accounts/signals_logout.py`

### Module docstring

Logout signal handler — root-domain revocation (M1 D6 Phase 5, B.4.17).

Hooks the logout signal. When logout happens on the root domain, all
outstanding handoff tokens for the user are revoked and ROOT_SESSION_LOGOUT
is emitted.

When logout happens on a tenant subdomain, the tenant logout view owns
TENANT_SESSION_LOGOUT audit emission and this handler returns early.
Tenant logouts MUST NOT revoke cross-tenant handoff tokens.

This handler is intentionally defensive because Django's logout signal may
fire in test-client flows, mocked signal tests, or other code paths where the
request object is incomplete or does not have normal host metadata.

### Function `_fallback_host`

Return a safe fallback host for tests or incomplete requests.

Prefer an explicit root-domain-style setting if the project defines one.
Otherwise use ``testserver``, which is Django's conventional test host.

### Function `_safe_request_host`

Safely extract a normalized host from a possibly incomplete request.

``request.get_host()`` can fail in tests when the request lacks
``HTTP_HOST`` and ``SERVER_NAME``. Mocked requests may also return a
MagicMock instead of a string. This helper normalizes those cases so the
logout signal receiver never crashes while handling audit/revocation.

### Function `_is_tenant_logout_host`

Return True when host clearly resolves to a tenant subdomain.

If host classification fails, default to root-style behavior. That means
we revoke outstanding handoff tokens rather than leaving them active.
Tenant logout requests should have a real tenant host, so they will still
be classified correctly in normal request flows.

### Function `_on_user_logged_out`

Revoke outstanding handoff tokens when logout is on the root domain.

Args:
    sender: Signal sender.
    request: The HTTP request. Used for host classification.
    user: The user who just logged out. May be None for edge-case flows.

## `backend/apps/platform/accounts/signals_mfa.py`

### Module docstring

MFA satisfaction signal handlers (M1 D6 Phase 4A).

Writes ``mph_mfa_satisfied_at`` to the request session when the
user completes an MFA event — TOTP challenge passed, recovery code
consumed, or fresh TOTP enrollment.

The session key is consumed by the org picker view (Phase 4B) to
populate ``HandoffResult.mfa_satisfied_at`` at handoff-token issue
time. The token then carries the timestamp across to the tenant
subdomain, where B.4.10 freshness checks can be enforced from the
tenant session.

**Two allauth.mfa signals handled:**

* ``authenticator_used`` — fires when a user verifies an
  authenticator (TOTP code passed, recovery code consumed,
  passkey verified). The canonical "MFA was just satisfied"
  signal.
* ``authenticator_added`` — fires when a user enrolls a new
  authenticator. Allauth's enrollment flow requires the user to
  enter a valid TOTP code as part of activation, so we treat
  enrollment success as equivalent to "MFA was just satisfied."
  Without this, a freshly-enrolled user would have no
  ``mph_mfa_satisfied_at`` on session and would fail B.4.10
  freshness checks immediately after enrolling.

Trusted-provider OAuth bypass — where MFA is "satisfied" by the
identity provider rather than a local challenge — is handled
separately in
:mod:`apps.platform.accounts.middleware` (the
``RequireMfaEnrollmentMiddleware._emit_provider_mfa_trusted_once``
codepath, which now also sets the session key).

**Why this lives in signals, not middleware.** Allauth's MFA
challenge / enrollment views complete the MFA event and then
redirect to ``LOGIN_REDIRECT_URL``. By the time the redirect target
runs, allauth's signal has already fired. Hooking the signal
captures the satisfaction moment precisely; hooking the redirect-
target view would race with the picker and produce stale
timestamps.

**No audit emission from these handlers.** This is purely session
state. Audit events for MFA enrollment / use are emitted elsewhere
(``MFA_ENROLLED``, ``LOCAL_MFA_CHALLENGE_PASSED``) by signal
handlers wired in M1 D4. The signals here are session-only side
effects and don't need to go through ``record_auth_event``.

### Function `_on_authenticator_used`

Write ``mph_mfa_satisfied_at`` when a user passes an MFA check.

Fires for TOTP challenge passes, recovery-code consumption, and
passkey verification. The session is the request's session
(root-domain when the user is logging in to mph.local).

### Function `_on_authenticator_added`

Write ``mph_mfa_satisfied_at`` when a user enrolls a new authenticator.

Allauth's enrollment flow validates a TOTP code as part of
activation, so enrollment success is functionally equivalent
to passing an MFA challenge. Without this handler, a user who
enrolls and then immediately hits the picker would have no
satisfaction timestamp on session.

### Function `_record_mfa_satisfaction`

Write the timestamp to session, with defensive guards.

## `backend/apps/platform/accounts/templatetags/oauth_providers.py`

### Module docstring

Template tags exposing OAuth provider configuration to templates.

Used by:

* ``account/login.html`` — to render a provider button per active
  ``OAuthProviderConfig``.
* ``socialaccount/connections.html`` — to render "link this provider"
  options for providers the user hasn't linked yet.

Scoped to templates that explicitly load the tag library, rather than
a context processor that runs on every request. The login page renders
infrequently (rate-limited to ~20/hour per IP); a DB query per render
is acceptable for M1 D5 without caching.

### Function `active_oauth_providers`

Return all OAuthProviderConfig rows with ``is_active=True``.

Ordered by display_name (stable button order in templates).
Returns an empty list if no providers are active — the login
template should handle that case by simply not rendering the
OAuth section.

### Function `user_linked_providers`

Return the set of provider_codes the user has SocialAccounts for.

Used by ``socialaccount/connections.html`` to determine which
providers should appear as "link this provider" buttons (i.e. the
active providers MINUS what's already linked).

Returns an empty set for anonymous users.

## `backend/apps/platform/accounts/tests/_helpers.py`

### Module docstring

Test helpers for the accounts app (M1 D4).

Pure functions and constants used by the test suite. Lives outside
``conftest.py`` because conftest is not a regular importable Python
module — pytest loads it specially and ``from .conftest import X``
does not work reliably across discovery boundaries.

What lives here:

* ``TEST_TOTP_SECRET`` — the canonical fixture secret.
* ``totp_code_for(secret)`` — compute the current TOTP code via
  RFC 6238 using the period/digit count from Django settings. Used
  by the end-to-end MFA test (J.3.9 #4). We hand-roll TOTP rather
  than depending on ``pyotp`` because allauth's ``[mfa]`` extra
  does not pull pyotp in transitively.
* ``_install_totp_authenticator(user, secret)`` — write an
  Authenticator row directly. Bypasses allauth's adapter encryption,
  which is fine for tests (the secret never leaves the test process).
* ``_install_recovery_codes(user)`` — same, for recovery codes.
  Smoke-rendering only; the single-use end-to-end test uses
  allauth's real generate flow.

Why direct Authenticator rows instead of allauth's high-level API:
the allauth ``activate`` function path has shifted between versions.
Writing the Authenticator row directly is stable across versions
because the model itself is the public contract surface.

### Function `_compute_totp_code`

Compute a TOTP code for a base32 secret.

RFC 6238 with the period and digit count from Django's
``MFA_TOTP_PERIOD`` / ``MFA_TOTP_DIGITS`` settings. SHA-1 is
RFC-mandated.

Args:
    secret: base32-encoded shared secret.
    when: unix timestamp; defaults to the current time.

Returns:
    Zero-padded decimal code as a string.

### Function `totp_code_for`

Public helper exposed to tests. See ``_compute_totp_code``.

### Function `_install_totp_authenticator`

Install a TOTP Authenticator row for a user, raw.

Data shape ``{"secret": "..."}`` matches what allauth's TOTP
wrapper expects on read. The secret is stored plaintext (no
adapter encryption), which is fine for tests because the secret
never leaves the test DB.

### Function `_install_recovery_codes`

Install a recovery-codes Authenticator row for a user, raw.

The data shape mirrors what allauth's recovery-codes wrapper
stores: ``{"migrated_codes": [], "seed": <random hex>}``. The
actual codes are derived from the seed; tests that need to
assert the single-use rule should use allauth's real generate
view instead of this helper because the wrapper's derivation
algorithm may shift between versions.

## `backend/apps/platform/accounts/tests/conftest.py`

### Module docstring

Accounts-app conftest (M1 D4).

Intentionally near-empty. Auth fixtures (``user_factory``,
``user_with_totp``, etc.) and the audit-buffer reset autouse were
promoted to ``backend/conftest.py`` so tests in any directory can
reference them. Pure helpers live in
``apps/platform/accounts/tests/_helpers.py``.

This module is retained as an explicit marker so a future engineer
looking for "where are the accounts test fixtures defined?" sees
this docstring rather than searching upward.

## `backend/apps/platform/accounts/tests/test_create_superuser_email_verification.py`

### Module docstring

Tests for the M1 D7 Phase 1 createsuperuser ergonomics fix.

Verifies that ``UserManager.create_superuser`` auto-creates a
verified primary allauth ``EmailAddress`` row. Without this, the
first ``createsuperuser`` on a fresh deployment can't sign in
because settings include
``ACCOUNT_EMAIL_VERIFICATION = "mandatory"``.

### Function `test_create_superuser_is_idempotent_for_email_address`

If ``create_superuser`` is somehow re-run (or another path
creates the EmailAddress first), the helper should not
duplicate-create.

### Function `test_create_regular_user_does_not_create_email_address`

``create_user`` (non-superuser) does NOT auto-verify.

Regular users must go through the normal allauth email
verification flow. The ergonomics fix is ONLY for the
bootstrap-superuser case.

## `backend/apps/platform/accounts/tests/test_end_impersonation.py`

### Module docstring

Tests for end_impersonation service (M1 D7 Phase 4).

### Function `test_end_by_different_staff_succeeds`

A different staff user can end someone else's session.

### Function `test_admin_can_start_new_session_after_ending`

After ending, the admin can start a new impersonation.

## `backend/apps/platform/accounts/tests/test_handoff_signing_key_services.py`

### Module docstring

Tests for HandoffSigningKey lifecycle services (M1 D6 Phase 1).

Coverage:
* Fernet encryption round-trip (model layer)
* create_handoff_signing_key validation + audit emission
* promote_handoff_signing_key state transitions + audit
* retire_handoff_signing_key state transitions + audit
* emergency_rotate_handoff_signing_key full flow
* active_handoff_signing_keys_ordered_by_created_desc ordering
* "two non-retired max" invariant
* actor validation (staff / system / neither)
* __repr__ does not leak the encrypted secret

### Function `test_with_two_active_retires_oldest_first`

Edge case: emergency rotation lands mid-normal-rotation.

## `backend/apps/platform/accounts/tests/test_handoff_token_services.py`

### Module docstring

Tests for issue/consume handoff-token services (M1 D6 Phase 2).

### Function `primary_key`

Active, promoted primary HandoffSigningKey.

### Function `org_and_membership`

A user with an ACTIVE membership in an organization.

### Function `tenant_request_for_acme`

An HttpRequest with host matching the 'acme' tenant slug.

### Function `test_verifies_with_old_key_and_emits_retired_key_audit`

Token issued with key A; rotation adds key B as primary;
token still verifies with A but emits the audit event.

## `backend/apps/platform/accounts/tests/test_impersonation_model.py`

### Module docstring

Tests for ImpersonationSession model constraints (M1 D7 Phase 4).

### Function `test_admin_cannot_equal_target`

DB CHECK: admin_user != target_user.

### Function `test_ended_at_before_started_rejected`

DB CHECK: ended_at >= started_at when set.

### Function `test_ended_pair_must_be_set_together_both_null`

DB CHECK: both ended_at + ended_by_user null, or both set.

Test: setting only ended_at without ended_by_user fails.

### Function `test_at_most_one_active_session_per_admin`

Partial unique index: one active impersonation per admin.

### Function `test_admin_can_start_new_session_after_ending_first`

End the first session, then a new one can start.

## `backend/apps/platform/accounts/tests/test_log_scrubbing.py`

### Module docstring

Log-scrubbing test (J.3.9 #20).

Asserts that secrets — passwords, TOTP secrets, recovery codes — do not
appear in any log record during a full local-auth flow.

This is a probe, not a proof. The audit pipeline's masking (G.5.5)
lives in the M2 partitioned-storage implementation; until then, we
verify that the M1 stub + signal handlers don't leak secrets into
captured logs.

## `backend/apps/platform/accounts/tests/test_mfa_end_to_end.py`

### Module docstring

End-to-end MFA tests (J.3.9 #4, #5).

These tests exercise allauth's real MFA flow — POSTing to enrollment,
satisfying the challenge with a real computed TOTP code, and consuming
a recovery code. The smoke suite uses fixture-built authenticators
for speed; these tests trade speed for fidelity to verify that the
flow itself works.

Coverage:
- J.3.9 #4: Local MFA enrollment + challenge work.
- J.3.9 #5: Recovery codes are single-use.
- J.3.5 #1: Local password login with MFA.
- J.3.5 #2: Local password login without enrolled MFA forces enrollment.

TOTP code computation uses the in-repo ``totp_code_for`` helper (RFC
6238 against MFA_TOTP_* settings), avoiding a pyotp dependency.

### Function `_extract_totp_secret`

Extract the TOTP setup secret from the activation page.

Tries two strategies in order:

1. Read it from the session, where allauth.mfa stashes the
   in-progress secret during the activation flow. Tried under
   both 65.x key names.
2. Scrape the rendered HTML. Our template renders the secret
   inside a ``<code class="mph-mfa-secret-code">`` element, but
   attribute order and additional class tokens vary by template
   state, so use a permissive regex.

Returns the secret as a base32 string, or None if both strategies
fail (caller should assert and dump body for debugging).

### Class `TestLocalLoginWithoutMfaForcesEnrollment`

J.3.5 #2: a verified user with no TOTP is forced to enroll.

### Class `TestMfaEnrollmentAndChallenge`

J.3.9 #4: enrollment + challenge work end-to-end.

### Class `TestRecoveryCodesSingleUse`

J.3.9 #5: recovery codes are single-use.

Uses allauth's real generate-recovery-codes view to obtain a valid
code (rather than the fixture-built raw seed), so the wrapper's
consumption logic actually fires.

## `backend/apps/platform/accounts/tests/test_middleware.py`

### Module docstring

Tests for RequireMfaEnrollmentMiddleware (M1 D4 + M1 D5 Phase 4).

M1 D4 — B.4.9 local password enforcement:
- authenticated local-password users without TOTP are redirected
  to /accounts/2fa/totp/activate/.
- allowlisted paths pass through regardless of MFA state.
- LOCAL_MFA_CHALLENGE_REQUIRED emitted once per session.
- system user is exempt.

M1 D5 Phase 4 — B.4.8 trusted-provider MFA policy:
- OAuth user via TRUSTED provider with no TOTP bypasses enrollment.
- OAuth user via UNTRUSTED provider with no TOTP is forced to enroll.
- OAUTH_PROVIDER_MFA_TRUSTED / _NOT_TRUSTED emitted once per session.
- missing OAuthProviderConfig falls back to forcing enrollment
  (safe-default failure mode).
- existing TOTP enrollment bypasses the middleware regardless of
  login method.

### Function `trusted_provider`

A provider configured as trusted for external MFA.

### Function `untrusted_provider`

A provider configured as NOT trusted for external MFA.

### Function `_login_via_provider`

Test helper: simulate an OAuth login by setting the session key
that the OAuth signal handler would have written at login time.

Used instead of running allauth's full OAuth flow because:
- the full flow needs the mock OIDC issuer (Phase 6).
- the middleware behavior under test is independent of how the
  session key got there.

### Class `TestTrustedProviderBypassesEnrollment`

B.4.8: trusted-provider OAuth user with no TOTP can proceed.

### Class `TestUntrustedProviderForcesEnrollment`

B.4.8: untrusted-provider OAuth user must enroll local TOTP.

### Class `TestExistingTOTPBypassesMiddleware`

If the user already has TOTP, no enrollment policy applies.

Belt-and-suspenders: even for an OAuth user via untrusted provider,
if they happen to ALREADY have TOTP enrolled, the middleware
doesn't fire OAUTH_PROVIDER_MFA_* events. The decision point is
'is enrollment needed', not 'what login method'.

### Class `TestUnknownProviderCodeForcesEnrollment`

Defense in depth: if the provider config can't be loaded, the
middleware MUST fall back to forcing enrollment.

This shouldn't happen in practice (signal handler writes the code,
and providers aren't deleted mid-session), but if it does — e.g.
operator deactivates a provider while users are mid-session — the
safe default is to force local MFA.

### Class `TestThrottleIsPerSession`

A fresh login session gets a fresh throttle slate.

Logging out and back in should yield a new emission because the
session is replaced.

## `backend/apps/platform/accounts/tests/test_middleware_outside_transaction.py`

### Module docstring

Production-realism guard for RequireMfaEnrollmentMiddleware.

The standard middleware tests use the pytest-django @pytest.mark.django_db
decorator without ``transaction=True``, which wraps each test in a
transaction. That wrapping inadvertently satisfies the audit service's
"must be in a transaction" check — masking the bug where middleware
calls audit_emit directly without opening its own transaction.

This file's tests use ``transaction=True`` so pytest-django commits
each statement (no enclosing transaction). The middleware then runs in
the same state as production. If a future change makes the middleware
call audit_emit directly again, these tests fail with
AuditOutsideTransactionError — surfacing the bug before deploy rather
than after.

### Class `TestMiddlewareEmissionsOutsideTransaction`

Regression guard: emit paths must not crash outside a transaction.

Each test below would have caught the bug at:
AuditOutsideTransactionError at /select-org/

where the middleware called audit_emit directly while no
request-level transaction was open.

## `backend/apps/platform/accounts/tests/test_oauth_adapter.py`

### Module docstring

Tests for the MphSocialAccountAdapter (M1 D5 Phase 3).

Covers:
- pre_social_login dispatches to resolve_external_user
- success path: sociallogin.user is set to the resolved user
- each typed exception maps to the right failure_reason audit
- each typed exception maps to the right help-page redirect
- OAUTH_LOGIN_STARTED is emitted on every call
- OAUTH_LOGIN_FAILED is emitted with structured failure_reason
- unknown provider_code is handled as provider_not_active
- the System User id is cached after first lookup

The adapter is tested with stub SocialLogin instances rather than
running allauth's full flow. The full-flow tests live in Phase 6
with the mock OIDC issuer.

### Class `TestPreSocialLoginFailures`

Each typed exception maps to a redirect + structured audit event.

### Class `TestOAuthHelpView`

Sanity tests on the help-page view itself.

## `backend/apps/platform/accounts/tests/test_oauth_adapter_resolution.py`

### Module docstring

Adapter-boundary integration tests for J.3.9 #6, #8, #9, #10 (M1 D5 Phase 6).

These tests exercise the full chain from
``MphSocialAccountAdapter.pre_social_login`` through
``resolve_external_user`` to the database side effects. The HTTP
flow (allauth's authorization redirect, token exchange, JWKS
verification) is allauth's surface — we use synthetic
``SocialLogin`` fixtures rather than a mock OIDC issuer.

This matches the M1 D5 retro decision: service+adapter coverage
provides regression protection over our policy decisions, and M8
production-readiness (J.10.3) does the real-provider verification.

Coverage matrix (J.3.9 numbering):

* #6 — OAuth login works through configured provider → verified at
  adapter boundary (this file). HTTP integration deferred to M8.
* #8 — OAuth callback validates provider response → verified for
  the validations our adapter enforces (provider active, email
  verified, allowed domain, conflicting identity). Cryptographic
  validations (state, nonce, signature) are allauth's responsibility
  and verified in M8.
* #9 — External identity links to canonical User → verified
  end-to-end via the adapter (this file) AND at the service level
  (test_resolve_external_user_service.py).
* #10 — OAuth login does not create Membership → verified at the
  service level. Re-verified at adapter level here.

### Function `provider_default`

An active OIDC provider with the typical M1 D5 posture:
require verified email, no self-registration, untrusted MFA.

### Function `provider_self_reg`

An active OIDC provider that allows self-registration.

### Class `TestOAuthLoginAdapterBoundary`

J.3.9 #6 — OAuth login works through configured provider.
J.3.9 #9 — External identity links to canonical User.

### Class `TestProviderResponseValidationAtAdapter`

J.3.9 #8 — OAuth callback validates provider response.

Cryptographic validations (state, nonce, ID token signature,
issuer, audience) are enforced by allauth BEFORE our adapter runs.
Verified in M8 with real providers (J.10.3).

Our adapter enforces the configuration-level validations:
provider is active, verified email if required, allowed domain,
no conflicting identity. Those are exercised here.

### Class `TestOAuthLoginCreatesNoMembership`

J.3.9 #10 — OAuth login does not create Membership.

The service-level test already covers this with full enforcement.
The adapter-level test re-verifies in the *adapter* context:
even a successful login through allauth's pipeline does not
create a Membership row.

### Class `TestAuditEventOrdering`

OAUTH_LOGIN_STARTED MUST precede other events from the same call.

## `backend/apps/platform/accounts/tests/test_oauth_claims.py`

### Module docstring

Tests for ExternalIdentityClaims and normalize_socialaccount_claims (B.3.8).

### Class `_FakeSocialAccount`

Stub mimicking allauth.socialaccount.models.SocialAccount.

### Class `_FakeSocialLogin`

Stub mimicking allauth.socialaccount.models.SocialLogin.

### Function `test_token_fields_stripped_from_raw_claims`

Defense in depth: token-like keys never enter the claims object.

### Function `test_display_name_falls_back_to_display_name_claim`

Some providers use `display_name` instead of `name`.

## `backend/apps/platform/accounts/tests/test_oauth_loader.py`

### Module docstring

Tests for the SOCIALACCOUNT_PROVIDERS loader (M1 D5 Phase 1).

Covers:
- only is_active=True providers are loaded
- inactive providers are invisible to the loader
- missing env vars cause the provider to be skipped (warning logged)
- credentials are read from env vars (not from the model)
- the dict shape matches what allauth expects
- the apply_to_settings hook mutates settings.SOCIALACCOUNT_PROVIDERS

## `backend/apps/platform/accounts/tests/test_oauth_log_scrubbing.py`

### Module docstring

J.3.9 #20 — OAuth-specific log scrubbing (M1 D5 Phase 6).

Verifies that the OAuth flow does not write tokens, authorization
codes, client secrets, ID tokens, or TOTP secrets into log records.

M1 D4 already covered the local-auth flow (test_log_scrubbing.py).
This file covers the OAuth-specific paths: claims normalization,
adapter resolution, signal-driven audit emission.

Probe-not-proof: G.5.5 masking lives in M2's audit storage. Until
then, this test confirms the M1 D5 code paths don't leak.

### Function `_assert_no_leaks`

Walk all records, fail if any leak string appears anywhere.

### Class `TestNormalizationDoesNotLogTokens`

normalize_socialaccount_claims strips tokens (Phase 1). Verify
the stripping path itself doesn't log the values it's stripping.

### Class `TestAdapterDoesNotLogTokens`

Adapter's success and failure paths both must scrub.

### Function `test_adapter_failure_path_no_token_in_log`

Failure path emits OAUTH_LOGIN_FAILED + logs an info line.
Neither emission carries the tokens.

## `backend/apps/platform/accounts/tests/test_oauth_provider_config_model.py`

### Module docstring

Tests for the OAuthProviderConfig model (M1 D5 Phase 1).

Covers:
- field shape per B.3.7
- provider_code validator (DNS-safe)
- env-key validators (POSIX shape)
- OIDC-requires-issuer-url validation
- OAUTH2-requires-auth-and-token-url validation
- trust_external_mfa + require_verified_email=False is rejected
- secrets are NOT stored in the model (only env-var key names)

### Function `test_secret_never_stored_in_model_fields`

The model has no `client_secret` field — only the key NAME.

## `backend/apps/platform/accounts/tests/test_oauth_settings.py`

### Module docstring

J.3.9 #7 — provider client secret is loaded from env/secret source.

The OAuthProviderConfig model stores ONLY the env-var key NAMES
(client_id_env_key, client_secret_env_key). The actual credentials
are read from ``os.environ`` at startup by the loader. This file
verifies that:

1. The loaded SOCIALACCOUNT_PROVIDERS dict carries values from
   ``os.environ``, not from the DB row.
2. Changing the env var (without changing the DB row) changes the
   loaded value on next reload.
3. A missing env var causes the provider to be skipped (Phase 1
   behavior re-confirmed at the settings layer).
4. The OAuthProviderConfig model has no field that could hold a
   plaintext secret.

### Class `TestClientSecretLoadedFromEnv`

J.3.9 #7: secret comes from env, not from DB.

### Class `TestModelDoesNotStoreSecrets`

Belt and suspenders: model surface has no plaintext-secret field.

### Function `test_model_str_does_not_expose_env_key_value`

A platform admin viewing __str__ should see the provider
identity, not the env-var key name (the env-var key name is
less sensitive than the secret itself, but exposing it
widely-via-admin is still poor hygiene).

## `backend/apps/platform/accounts/tests/test_oauth_unlinking.py`

### Module docstring

B.4.18 unlinking tests (M1 D5 Phase 6).

J.3.6 #5 — user cannot unlink last login method.
J.3.6 #6 — unlinking external identity requires re-auth.
J.3.6 #7 — provider tokens and authorization codes are never logged.

The enforcement points being tested:

* Last-login-method protection (B.4.18) lives in allauth's
  ``DisconnectForm.clean()`` in 65.x — the form refuses to validate
  if the disconnect would leave the user with no usable login method.
  We exercise the form directly rather than the adapter method
  (which is now a hook that does nothing by default).

* Re-auth requirement (B.4.10) is enforced by allauth's
  ``ACCOUNT_REAUTHENTICATION_REQUIRED = True`` plus the 5-minute
  freshness window. A force_login'd session has no fresh auth
  timestamp, so the connections page bounces through
  /accounts/reauthenticate/.

* Token scrubbing (B.4.19 / G.5.5) — the unlink signal handler
  receives a SocialAccount with extra_data that may contain tokens.
  The handler must not log tokens, and the OAUTH_ACCOUNT_UNLINKED
  audit event must not echo extra_data.

### Function `_build_disconnect_form`

Construct a DisconnectForm as the connections view would.

Allauth's ``DisconnectForm.__init__`` (65.x) takes ``request``
and ``data`` only. The form derives ``self.accounts`` itself
via ``SocialAccount.objects.filter(user=request.user)``. So we
must attach the test user to the request before constructing.

### Class `TestCannotUnlinkLastLoginMethod`

B.4.18: A user MUST NOT remove their only usable login method.

Enforcement lives in allauth's DisconnectForm.clean() in 65.x.
The form refuses to validate if disconnect would leave the user
with no usable login method (no usable password AND no remaining
SocialAccount).

### Class `TestUnlinkingRequiresReauth`

B.4.18 / B.4.10: unlinking is a sensitive action.

Allauth honors ``ACCOUNT_REAUTHENTICATION_REQUIRED = True`` and
redirects stale sessions through /accounts/reauthenticate/ before
allowing connection management.

Note on URL: allauth 65.x mounts the connections view at
/accounts/3rdparty/. The older /accounts/social/connections/
path is a 301-redirect alias kept for backward compatibility.
We hit the canonical URL directly to avoid noise in assertions.

### Class `TestTokensNeverLoggedDuringUnlink`

B.4.19 / G.5.5: tokens, auth codes, secrets MUST NOT enter logs.

The unlink signal handler receives a SocialAccount with
``extra_data`` that may contain tokens (defense in depth — Phase 2
strips them on persistence, but tests reproduce the worst case
here). The handler must not log the token.

### Function `test_user_with_password_can_unlink_only_socialaccount`

User has a usable local password — unlinking their one
SocialAccount is fine because the password remains as a
login method.

### Function `test_external_only_user_with_multiple_socialaccounts_can_unlink_one`

External-only user with two providers — can unlink one,
the other remains as a usable method.

### Function `test_unlink_audit_event_does_not_contain_extra_data`

OAUTH_ACCOUNT_UNLINKED's metadata must not echo extra_data.

## `backend/apps/platform/accounts/tests/test_record_auth_event_service.py`

### Module docstring

Tests for record_auth_event (M1 D4).

This is the thin service wrapper around audit_emit that allauth signal
handlers call. It must:
- Open its own atomic boundary.
- Re-raise programming errors (UnknownAuditEventError,
  AuditOutsideTransactionError).
- Swallow other exceptions so an audit hiccup never breaks auth.

### Function `test_audit_outside_transaction_re_raises`

If our own atomic boundary fails to open, surface that as a bug.

### Function `test_generic_exception_is_swallowed`

An unexpected exception in the audit path must NOT break auth.

``caplog.at_level(...)`` is required because ``config/settings/test.py``
calls ``logging.disable(logging.CRITICAL)`` to suppress noisy
test output. That global disable suppresses our WARNING line
even though caplog's default level is 0. The ``at_level``
context manager temporarily re-enables logging at the requested
level for the duration of the block, then restores the previous
disable threshold.

## `backend/apps/platform/accounts/tests/test_resolve_external_user_service.py`

### Module docstring

Tests for resolve_external_user (M1 D5 Phase 2, B.4.6 / B.4.7).

Covers J.3.6 #1, #3, #4 and J.3.5 #3, #4, #5 at the service level.
The end-to-end HTTP flow lands in Phase 6.

J.3.5 #3 — OAuth/OIDC login with linked external identity:
  → test_subject_id_lookup_returns_linked_user

J.3.5 #4 — OAuth/OIDC login with verified email linking to existing
            invited user:
  → test_verified_email_links_to_existing_user

J.3.5 #5 — OAuth/OIDC login rejected for unverified email when
            verification is required:
  → test_unverified_email_rejected_when_required

J.3.6 #1 — provider subject ID maps to existing external identity:
  → test_subject_id_lookup_returns_linked_user

J.3.6 #3 — unverified email cannot link to existing user:
  → test_unverified_email_does_not_link_to_existing_user

J.3.6 #4 — conflicting external identity blocks login:
  → test_conflicting_external_identity_blocks_link

### Function `system_actor_id`

The System User id — the canonical actor for OAuth resolution.

### Function `oidc_provider`

A standard, active OIDC provider with strict verification.

### Function `oidc_provider_with_self_registration`

Like ``oidc_provider`` but with self-registration enabled.

### Function `_claims`

Construct a claims fixture inline (small enough not to need a factory).

### Class `TestEmailVerificationRequirement`

J.3.5 #5 + J.3.6 #3: unverified email rejected when required.

### Class `TestSubjectIdLookup`

J.3.6 #1 + J.3.5 #3: subject ID maps to linked external identity.

### Class `TestEmailBasedLinking`

J.3.5 #4: verified email links to existing invited user.

### Class `TestConflictingExternalIdentity`

J.3.6 #4: conflicting external identity blocks login.

### Class `TestResolutionDoesNotCreateMembership`

B.3.9: OAuth/OIDC login proves identity only.

The resolution service MUST NOT create Membership / Role /
Capability / OperatingScope rows. This is verified by counting
Membership rows before and after.

### Function `test_unverified_email_does_not_link_to_existing_user`

J.3.6 #3: even if email matches an existing user, unverified
email MUST NOT silently link.

### Function `test_subject_id_lookup_no_audit_event_emitted_on_return`

No new linking happened — no OAUTH_ACCOUNT_LINKED audit event.

### Function `test_subject_id_lookup_updates_extra_data`

Repeated logins refresh the SocialAccount extra_data with
the latest provider claims (minus tokens).

### Function `test_conflicting_external_identity_blocks_link`

A user already has a different subject ID for the same provider.

The login MUST stop. The user-facing message (rendered by the
Phase 3 adapter) is the account-linking help flow.

### Function `test_different_provider_is_NOT_a_conflict`

A user with a Google identity can also have a Microsoft identity.

### Function `test_no_existing_user_and_self_reg_disabled_rejected`

B.4.6 step 4 default: no User, self-registration off → reject.

## `backend/apps/platform/accounts/tests/test_revoke_handoff_tokens.py`

### Module docstring

Tests for revoke_all_handoff_tokens_for_user (M1 D6 Phase 5).

### Function `test_revoked_token_cannot_be_consumed`

End-to-end: issue, revoke, attempted consume returns
not_found_or_replayed.

### Function `test_consume_removes_token_from_index`

After successful consume, the token id is removed from
the user_handoffs index (Phase 5 best-effort cleanup).

## `backend/apps/platform/accounts/tests/test_signals.py`

### Module docstring

Tests for allauth signal handlers (M1 D4).

Verifies that each handled allauth signal triggers the right audit
event with the right shape. Signal-handler logic is intentionally
thin (translate signal payload → service call), so the tests are
mostly contract assertions.

### Class `TestMfaSignals`

Direct invocation of allauth.mfa signals.

These test our handler shape; the end-to-end MFA test suite
exercises the real allauth flow that emits these signals.

## `backend/apps/platform/accounts/tests/test_signals_logout.py`

### Module docstring

Tests for the user_logged_out signal handler (M1 D6 Phase 5).

## `backend/apps/platform/accounts/tests/test_signals_mfa.py`

### Module docstring

Tests for MFA satisfaction signal handlers (M1 D6 Phase 4A).

Uses a real Django SessionStore — NOT a plain dict — so the
``modified`` flag behaves the way it does in production. Plain
dicts don't have a ``.modified`` attribute settable in the way
Django's session machinery uses; the prior version's
``request.session = {}`` approach was wrong.

### Function `_request_with_session`

Build a request with a real Django SessionStore attached.

Uses the DB session backend so the ``modified`` attribute
behaves exactly like in production. The session row is never
saved to DB during these tests — the handler just writes to
the in-memory ``_session`` cache.

### Class `TestAuthenticatorUsedSignal`

authenticator_used → mph_mfa_satisfied_at written.

### Class `TestAuthenticatorAddedSignal`

authenticator_added → mph_mfa_satisfied_at written.

### Class `TestSignalDefensiveBehavior`

Signal handlers don't crash when request is None or has no session.

## `backend/apps/platform/accounts/tests/test_start_impersonation.py`

### Module docstring

Tests for start_impersonation service (M1 D7 Phase 4).

## `backend/apps/platform/accounts/tests/test_user_display.py`

### Module docstring

Tests for the ACCOUNT_USER_DISPLAY callable (M1 D4).

This is the fix for the `'User' object has no attribute 'username'`
AttributeError that surfaced during the demo login. The callable MUST:
- Return user.email for our User model.
- Not raise on any input shape.
- Fall back gracefully when the input lacks an email attribute.

### Function `test_setting_points_at_this_callable`

Sanity check that base.py wires ACCOUNT_USER_DISPLAY correctly.

## `backend/apps/platform/accounts/tests/test_user_model.py`

### Module docstring

Smoke tests for the custom User model (B.3.3, I.6.7).

Note: tests freely use ``User = get_user_model()`` (Django idiom). The
PascalCase rebinding is intentional; ``N806`` is suppressed for tests in
``pyproject.toml``.

### Function `test_auth_user_model_setting`

The custom user model must be wired in from migration #1 (I.6.7).

## `backend/apps/platform/accounts/tests/tests_register_local_user_service.py`

### Module docstring

Tests for the register_local_user service (M1 D4).

Covers:
- happy path with verified user creation
- email-collision rejection (typed exception)
- password-policy rejection (Django validators)
- missing actor rejection
- USER_REGISTERED audit event emission and content
- atomicity: failure leaves no partial state
- password never appears in any captured audit payload

### Function `system_actor_id`

The seed_v1 System User id — the canonical bootstrap actor.

### Function `test_atomicity_rolls_back_on_audit_failure`

If audit_emit raises mid-transaction, the User row is rolled back.

## `backend/apps/platform/accounts/user_display.py`

### Module docstring

Allauth ``ACCOUNT_USER_DISPLAY`` callable.

Allauth's default user-display function (``default_user_display`` in
``allauth.account.internal.userkit``) reads ``user.username`` to print
a friendly identifier in templates and emails. Our custom ``User``
model (B.3.3) is email-only — ``USERNAME_FIELD = "email"`` with no
``username`` field — so that default crashes with ``AttributeError``.

Allauth lets the application override this lookup via the
``ACCOUNT_USER_DISPLAY`` setting, which it resolves at runtime as a
dotted import path to a callable taking a single user argument and
returning a string. This module provides that callable.

Used by:

* ``{% user_display user %}`` template tag (the trigger that surfaced
  the bug — used in ``account/email/email_confirmation_message.txt``,
  ``account/email_confirm.html``, ``account/email/password_reset_key_message.txt``,
  and ``account/messages/logged_in.txt``).
* Internal allauth code paths that format the user for log lines,
  error pages, and similar.

The function MUST be safe to call with any object that has at least
the shape of our ``User`` model. It MUST NOT raise. If the user
object is unexpectedly shaped (e.g. a unit-test stub), the function
falls back to ``str(user)``, which on our ``User`` returns the email
via ``__str__``.

The function MUST NOT log or return secrets. ``email`` is the safe,
human-friendly identifier we intentionally show in product UI; it is
explicitly not redacted by G.5.5.

### Function `user_display`

Return a human-readable label for a User.

Resolution order:

1. ``user.email`` — the canonical identifier on our User model
   (B.3.3). USERNAME_FIELD = "email", so this is always populated
   for real users.
2. ``str(user)`` — falls back via the model's ``__str__``, which
   on our User also returns the email. Catches the case where the
   caller hands us a not-quite-User object (test stubs, etc.).
3. ``""`` — last-ditch empty string so allauth template rendering
   never crashes on a malformed user object.

## `backend/apps/platform/accounts/utils/__init__.py`

### Module docstring

Account utilities shared by services, management commands, and tests.

Helpers in this package are intentionally side-effect-light and
exempt from the service-layer transaction rule (A.4.4). They run
inside a caller's transaction when state-changing, and are called
from both service code AND management-command / test code.

The first member is :func:`ensure_verified_email_address`, which
idempotently installs a verified primary allauth ``EmailAddress``
row for a user. Used by:

* ``UserManager.create_superuser`` — so the first-time admin
  isn't blocked by allauth's mandatory email verification
  middleware.
* ``seed_dev_tenant`` management command — so the demo admin
  can sign in without a Mailpit roundtrip.

The helper writes through the allauth ORM directly. This is
acceptable in a utility module because:

* allauth's ``EmailAddress`` is not a tenant-owned model; the
  A.4.4 service-layer rule covers state changes to OUR domain
  models, not third-party auth-system rows.
* ``update_or_create`` provides natural idempotency.
* The two callers (manager method + seed command) are both
  legitimately outside the service layer.

## `backend/apps/platform/accounts/utils/email_verification.py`

### Module docstring

Idempotent verified-EmailAddress installation (M1 D7 Phase 1).

Extracted from the M1 D4 ``seed_dev_tenant._ensure_verified_email_address``
helper so the same logic can be reused by ``UserManager.create_superuser``
without duplicating the allauth-EmailAddress write.

**Why this exists.** Settings include
``ACCOUNT_EMAIL_VERIFICATION = "mandatory"`` per the production
posture. Every login by a user without a verified
``EmailAddress`` row gets bounced to allauth's email-confirmation
flow. For:

* The bootstrap superuser (first ``createsuperuser`` run on a
  fresh deployment) — they have no Mailpit access, no SMTP
  configured, and a chicken-and-egg blocker.
* The dev demo tenant — the engineer wants to sign in to
  ``admin@mph.local`` immediately without a Mailpit roundtrip.

Installing a pre-verified ``EmailAddress`` resolves both. The
function is idempotent so re-running ``createsuperuser`` (or
re-running the seed command after a ``--reset``) doesn't
double-create or get into half-verified states.

### Function `ensure_verified_email_address`

Idempotently install a verified primary EmailAddress for ``user``.

Args:
    user: Any user object exposing an ``email`` attribute. In our
        codebase this is always ``apps.platform.accounts.models.User``.

Returns:
    ``True`` if the row was newly created; ``False`` if it already
    existed (and we force-flipped it to verified/primary in case a
    prior allauth flow had left it unverified).

Side effects:
    Writes / updates a single ``allauth.account.models.EmailAddress``
    row. Does not open its own transaction — the caller is
    responsible for transactional context if they need one. In
    practice both callers (``create_superuser`` and
    ``seed_dev_tenant``) run this in a context where atomicity
    doesn't matter: either the row commits or the entire user
    creation rolls back.

## `backend/apps/platform/audit/__init__.py`

### Module docstring

Platform-tier audit event subsystem (G.5).

The full ``AuditEvent`` partitioned model lands in M2 (J.4 — RBAC + Audit).
In M1, this app exposes the ``audit_emit`` interface as a stub so that
service-layer code can adopt the audit contract without waiting for the
storage layer.

Public API:

* :func:`audit_emit` — emit an audit event. In M1 this is a stub that
  validates a transaction is open and records the event in-memory when
  recording is enabled (for tests). The real implementation inserts a
  partitioned ``AuditEvent`` row.

The contract is documented in G.5.3. Services that wire through this
interface today will continue to work unchanged when the M2 storage
backend lands.

## `backend/apps/platform/audit/apps.py`

### Module docstring

App config for apps.platform.audit.

## `backend/apps/platform/audit/confest.py`

### Module docstring

pytest fixtures for audit recording.

Auto-clears the in-memory audit buffer between tests so assertions
about "events emitted by THIS test" stay accurate.

### Function `_reset_audit_buffer`

Clear the per-thread audit event buffer before each test.

## `backend/apps/platform/audit/models.py`

### Module docstring

Placeholder for AuditEvent (C.1.14, G.5).

## `backend/apps/platform/audit/services.py`

### Module docstring

Audit emission interface (G.5.3) — M1 stub.

The full implementation, with partitioned ``platform_audit.AuditEvent``
rows + masking + retention, lands in M2 (J.4). M1's contract surface
matches the documented :func:`audit_emit` signature exactly so service
code written against it today won't need to change in M2.

**Behavior in M1:**

* Validates that a database transaction is open (per G.5.3 "raises if
  not within a transaction"). This enforces the discipline that audit
  events are emitted alongside the state change they describe, in the
  same atomic boundary, so the audit row commits if and only if the
  state change commits.
* If audit recording is enabled (``MPH_AUDIT_RECORDING=True`` in
  settings, default ``True`` in dev/test, default ``False`` in prod),
  appends an :class:`AuditEvent` named-tuple to a thread-local buffer.
  Tests use :func:`captured_audit_events` to assert emission.
* Otherwise, the event is dropped silently. The M2 implementation will
  replace this with a database insert.

**Event registry deviations from G.5.2:**

M1 D2 adds `ORG_CREATED` / `MEMBERSHIP_CREATED`. M1 D4 adds
`USER_REGISTERED` and MFA lifecycle codes. M1 D6 Phase 1 adds the
handoff-signing-key lifecycle codes. M1 D6 Phase 4B adds the
session-establishment codes (`TENANT_SESSION_ESTABLISHED`,
`MEMBERSHIP_SELECTED`). M1 D6 Phase 5 adds the logout-and-revocation
codes (`ROOT_SESSION_LOGOUT`, `TENANT_SESSION_LOGOUT`,
`HANDOFF_TOKENS_REVOKED_BY_LOGOUT`). M1 D7 Phase 4 adds the
impersonation codes (`IMPERSONATION_STARTED`, `IMPERSONATION_ENDED`,
`IMPERSONATION_DENIED`). All these additions will be folded into
G.5.2 during M2 audit work.

### Class `AuditEvent`

In-memory representation of an audit event.

## `backend/apps/platform/console/__init__.py`

### Module docstring

Platform console app (M1 D7).

The custom administrative surface mounted at ``/platform/`` per
H.7. This is a CONCRETE consumer of the
:mod:`apps.common.admin` primitives (base views, navigation
registry, shell layout), not part of `apps.common.*` itself —
the console reasons about domain entities (Organization, User,
HandoffSigningKey, ImpersonationSession) and is therefore domain
code.

**What lives here:**

* M1 D7 Phase 1 — URL skeleton + ``PlatformConsoleAccessMixin`` +
  navigation chrome + placeholder views.
* M1 D7 Phase 2 — Read-only org / user surfaces.
* M1 D7 Phase 3 — Handoff signing key management UI.
* M1 D7 Phase 4-5 — Impersonation start / list / end UI.

**What does NOT live here:**

* Base Django admin registrations (those stay in app-local
  ``admin.py`` and remain mounted at ``/django-admin/`` in DEBUG
  only).
* Any state-changing business logic. Console views call into the
  same service functions any other surface would call.
* Tenant-portal views (those live in :mod:`apps.web.tenant_portal`).

## `backend/apps/platform/console/access.py`

### Module docstring

Access control for the platform console (M1 D7 Phase 1).

Every platform-console view enforces three things:

1. The user is authenticated (Django's standard requirement).
2. The user has ``is_staff = True`` (B.3.4 — "User may access the
   platform console").
3. The user has completed MFA, satisfied via the normal
   ``RequireMfaEnrollmentMiddleware`` chain. We don't add a
   second MFA check here; the global middleware is the one
   source of truth.

Anonymous users get redirected to login. Authenticated but
non-staff users get a 403. We deliberately do NOT silently
redirect non-staff to ``/select-org/`` — a 403 makes it
obvious when a non-staff user discovers (or guesses) a
``/platform/...`` URL.

**Why a mixin, not a decorator.** All platform views are
class-based for consistency with the Phase 2+ surfaces (org
list/detail and user search/detail will both use generic
ListView / DetailView). Mixins compose cleanly with those
generic views.

### Class `PlatformConsoleAccessMixin`

Enforce ``is_staff`` on every platform-console view.

Subclasses get login_required for free (via the decorator).
The dispatch hook adds the is_staff check on top.

Returns 403 (Forbidden) for authenticated non-staff users
rather than redirecting. The behavior is intentional: a
redirect would obscure the access denial in browser history,
and non-staff users shouldn't be probing platform URLs.

## `backend/apps/platform/console/apps.py`

### Module docstring

AppConfig for the platform console app.

## `backend/apps/platform/console/tests/test_access.py`

### Module docstring

Tests for PlatformConsoleAccessMixin and platform-URL access.

Three scenarios per view:
* Anonymous → redirect to login.
* Authenticated non-staff → 403.
* Authenticated staff → 200 (for list URLs) or 404 (for detail URLs
  with non-existent identifiers — the auth check still passed).

We test against every Phase 1/2 platform URL to confirm the mixin
is wired uniformly. If a Phase 3+ view forgets to inherit the
mixin, the corresponding 403 test will catch it.

### Function `test_staff_user_detail_urls_pass_auth_then_404`

For URLs with non-existent identifiers, staff sees 404 (not 403)
— auth check passed; the resolver couldn't find the row.

## `backend/apps/platform/console/tests/test_orgs.py`

### Module docstring

Tests for org list and detail views (M1 D7 Phase 2).

## `backend/apps/platform/console/tests/test_signing_keys.py`

### Module docstring

Tests for handoff signing key management views (M1 D7 Phase 3).

### Function `test_post_duplicate_new_key_id_returns_error`

Using the current primary's key_id as new_key_id is
rejected — service raises HandoffSigningKeyAlreadyExistsError.

## `backend/apps/platform/console/tests/test_users.py`

### Module docstring

Tests for user search and detail views (M1 D7 Phase 2).

## `backend/apps/platform/console/urls.py`

### Module docstring

Platform console URLs (M1 D7 Phase 1 + Phase 2 + Phase 3).

Phase 3 emergency-rotate URL has NO ``<key_id>`` parameter.
The service determines the current primary itself; the operator
provides ``new_key_id`` via the confirmation form.

## `backend/apps/platform/console/views.py`

### Module docstring

Platform console views (M1 D7 Phase 1 + Phase 2 + Phase 3).

Phase 1 — Skeleton.
* :class:`PlatformHomeView` — root ``/platform/`` redirect.
* :class:`ImpersonationLogView` — placeholder (Phase 5).

Phase 2 — Read-only org/user surfaces.
* :class:`OrgListView` — paginated list with name/slug search.
* :class:`OrgDetailView` — single org with member count + metadata.
* :class:`UserSearchView` — search-driven list (no query → no results).
* :class:`UserDetailView` — single user with memberships, MFA, security.

Phase 3 — Handoff signing key management UI.
* :class:`SigningKeysListView` — list all keys with lifecycle state.
* :class:`SigningKeyCreateView` — form + POST → create.
* :class:`SigningKeyPromoteView` — confirmation + POST → promote.
* :class:`SigningKeyRetireView` — confirmation + POST → retire.
* :class:`SigningKeyEmergencyRotateView` — confirmation + POST → rotate.

All state-changing views are POST-only on the action; GET shows a
confirmation/form page. CSRF is standard Django (root domain). The
actor for audit emission is ``request.user`` — the human platform
admin doing the work.

**Emergency rotate URL design (Phase 3 finalization).** The
``emergency_rotate_handoff_signing_key`` service takes
``new_key_id`` (the operator-chosen identifier for the freshly-
created replacement key) and determines the previous primary
itself via the standard ``active_handoff_signing_keys_ordered_by_created_desc``
helper. The URL therefore does NOT take a ``<key_id>`` parameter —
the operator picks the new id on the confirmation form.

### Class `PlatformHomeView`

``/platform/`` — redirect to the org list.

### Class `_PlatformPlaceholderView`

Base class for placeholder views.

### Class `OrgListView`

Paginated list of all tenant organizations.

### Class `OrgDetailView`

Read-only org detail.

### Class `UserSearchView`

Search-driven user list.

### Class `UserDetailView`

Read-only user detail.

### Function `_annotate_signing_key_state`

Compute lifecycle state + display label for a key.

Returns a dict with:
* ``state``: one of "primary", "active", "pending", "retired".
* ``state_display``: human-readable label.
* ``css_class``: Tailwind classes for the state badge.

Primary key determination matches the M1 D6 Phase 1 retro note:
primary = most recent non-retired key by ``created_at`` DESC.

### Class `SigningKeysListView`

List all handoff signing keys with lifecycle state.

### Class `SigningKeyCreateView`

GET shows form, POST creates a new key.

### Class `_SigningKeyKeyedActionView`

Base for promote / retire (URL-keyed by the target key_id).

Emergency rotate does NOT inherit from this — its URL has no
``<key_id>`` parameter because the service determines the
target itself.

### Class `SigningKeyPromoteView`

Promote a pending key to primary.

### Class `SigningKeyRetireView`

Retire a key (mark unusable for future verification).

### Class `SigningKeyEmergencyRotateView`

Emergency rotate the current primary.

The service determines which key is the current primary via
``active_handoff_signing_keys_ordered_by_created_desc()``; the
operator provides ``new_key_id`` for the freshly-minted
replacement.

URL design rationale: no ``<key_id>`` URL parameter. The
operator clicks "Emergency rotate" from the list (which shows
next to the current primary), lands on a confirmation page
that displays the current primary, and submits a new key_id.

Per the M1 D6 retro: this is a zero-overlap rotation — all
outstanding tokens become invalid. Use ONLY when compromise is
suspected.

## `backend/apps/platform/organizations/__init__.py`

### Module docstring

Public API for the platform_organizations app.

Lazy re-exports (PEP 562) to avoid AppRegistryNotReady during Django
startup. Production code should normally import from
``apps.platform.organizations.models`` or
``apps.platform.organizations.scope_models`` directly; the names
re-exported here are a convenience layer.

## `backend/apps/platform/organizations/admin.py`

### Module docstring

Dev-only Django admin registrations for platform_organizations.

Registrations live in ``apps.platform.accounts.admin`` so the order of
imports matches the order of model registration. This file exists only
to be discovered by Django's admin autoloader; it intentionally
contains no registrations of its own.

## `backend/apps/platform/organizations/apps.py`

### Module docstring

App config for apps.platform.organizations.

## `backend/apps/platform/organizations/models.py`

### Module docstring

Organization, Membership, and tenant-lifecycle entities (B.1.2, B.3.5, C.1.16).

This module owns the multi-tenant root entity. Every other tenant-owned
model in the codebase references ``Organization`` via a PROTECTed FK
(B.1.3).

Service-layer note: state-changing flows (create_organization,
invite_user, suspend_membership, request_tenant_deletion, etc.) live in
service functions added in M1+. The models in this file carry no
business logic in ``save()`` — they only declare structure.

Index naming: every ``models.Index`` carries an explicit ``name=``
argument. Auto-generated index names are fragile across Django versions
(the 6-char hash suffix Django computes can drift) and cause spurious
``RenameIndex`` migrations on every ``makemigrations`` run. Always name
indexes explicitly going forward.

### Function `_new_uuid`

UUID v7 factory (Python 3.14+). Falls back to uuid4 for older runtimes.

### Class `OrganizationStatus`

Organization lifecycle states (B.1.2).

### Class `MembershipStatus`

Membership lifecycle states (B.3.5, C.2.9).

### Class `TenantExportScope`

Scope of a tenant data export request (C.1.16, G.7.2).

### Class `TenantExportStatus`

Lifecycle of a tenant export request (C.1.16, G.7.2).

### Class `TenantDeletionStatus`

Lifecycle of a tenant deletion request (C.1.16, G.7.3).

### Class `Organization`

Tenant root (B.1.2).

Field notes:
* ``slug`` matches ``^[a-z][a-z0-9-]{1,61}[a-z0-9]$`` and is the subdomain
  key for tenant routing. Slug is immutable post-creation in v1.
* ``default_tax_jurisdiction_id`` and ``invoicing_policy_id`` reference
  models that land in later milestones (M3 catalog/pricing, M5 billing).
  They are declared as plain UUID columns for now and converted to real
  ``ForeignKey`` columns when those target models exist. The on-delete
  semantics will be ``SET_NULL`` to match the nullable shape.
* ``accounting_adapter_config`` is required to be encrypted at rest in
  production (F.5.4). We store it as plain JSONB here; an
  ``EncryptedJSONField`` is introduced in M5 alongside the first concrete
  accounting adapter. Local-dev impact: none.

### Class `Membership`

Authoritative tenant-access record (B.3.5).

Membership is the authoritative tenant-access record. OAuth/OIDC login
proves identity only — it does not grant tenant access by itself
(B.3.9).

The partial unique index on ``is_default_for_user`` enforces that a
user has at most one default membership (B.3.5).

### Class `TenantExportRequest`

Tenant data export request (C.1.16, G.7.2).

Schema only — service logic lands with the export pipeline in a later
milestone. ``output_attachment_id`` will become a FK to
``DocumentAttachment`` when the files app's models land; declared as a
plain UUID column for now.

### Class `TenantDeletionRequest`

Tenant deletion request (C.1.16, G.7.3).

Multi-stage workflow with a 30-day grace period. Schema only —
``request_tenant_deletion`` / ``cancel_tenant_deletion`` /
``execute_tenant_deletion`` services land in M1+.

## `backend/apps/platform/organizations/scope_models.py`

### Module docstring

MembershipScopeAssignment (B.2.4).

Lives in ``apps.platform.organizations`` because it joins Membership
(an organizations-app model) with RML rows. The cross-app dependency
direction is: ``platform_organizations`` → ``operations_locations``.

CHECK constraint enforces "exactly one of (region_id, market_id,
location_id) is non-null" per the B.2.4 spec.

NOT a TenantOwnedModel subclass:

* MembershipScopeAssignment isn't a tenant-owned record in the
  same sense as a domain entity. It's a JOIN row owned by a
  Membership. The platform console may legitimately query these
  across tenants.
* The organization is reachable transitively via
  ``self.membership.organization_id``. Adding a redundant org column
  would invite drift.

### Class `MembershipScopeAssignment`

Per-Membership scope grant at REGION, MARKET, or LOCATION granularity.

## `backend/apps/platform/organizations/services/__init__.py`

### Module docstring

Organization service layer (M1 D2).

Public API:

* :func:`create_organization` — provision a new tenant with cloned
  per-tenant role rows.
* :func:`assign_owner_membership` — bootstrap the first ACTIVE
  Membership for a tenant and assign the per-tenant Owner role.

Service-layer rules (A.4.4):

* Functions accept primitive arguments (UUIDs, strings, decimals).
  They do not accept request objects.
* Functions own their transaction boundaries via
  ``transaction.atomic(...)``.
* Audit events are emitted via :func:`apps.platform.audit.services.audit_emit`
  inside the same atomic boundary as the state change they describe.

Exceptions (defined in :mod:`apps.platform.organizations.services.exceptions`):

* :exc:`OrganizationSlugInUseError` — slug collision on create.
* :exc:`OrganizationNotFoundError` — caller referenced a nonexistent org.
* :exc:`UserNotFoundError` — caller referenced a nonexistent user.
* :exc:`MembershipAlreadyExistsError` — user already has a Membership
  in the target organization.

## `backend/apps/platform/organizations/services/_create.py`

### Module docstring

Organization-creation and owner-membership-assignment services (M1 D2).

These are the first concrete service-layer functions in the codebase.
They exemplify the discipline every future service follows:

* Primitive arguments only (no request, no model instances passed
  through views).
* Single ``transaction.atomic()`` boundary per public function.
* Audit emission inside the same boundary.
* Typed exceptions for distinguishable failure modes.
* No state-change ORM writes outside ``services/``.

### Function `_validate_slug`

Raise ValidationError if slug doesn't match the B.1.2 shape.

### Function `_validate_email`

Lightweight email shape check; full normalization happens at write time.

### Function `create_organization`

Provision a new tenant Organization with cloned per-tenant Role rows.

Steps performed inside a single ``transaction.atomic()``:

1. Create the Organization row.
2. Clone all 11 default Role templates (organization=NULL, is_default=True)
   to per-tenant Role rows scoped to this Organization. For each clone,
   replicate the template's RoleCapability rows so the per-tenant Role
   holds the same capability set as its template.
3. Emit an ``ORG_CREATED`` audit event.

Args:
    slug: DNS-safe subdomain key per B.1.2. Validated against
        ``^[a-z][a-z0-9-]{1,61}[a-z0-9]$``.
    name: Human-readable organization name.
    primary_contact_email: Primary contact email (required by Org model).
    primary_contact_name: Optional contact display name.
    primary_contact_phone: Optional contact phone.
    timezone: IANA timezone name; defaults to America/Chicago.
    base_currency_code: ISO 4217 currency code; defaults to USD.
    actor_id: UUID of the User performing the creation. For
        system-bootstrap flows (e.g. seed_dev_tenant), pass the
        System User's id.

Returns:
    The newly created Organization.

Raises:
    ValidationError: any input fails validation. No DB writes
        occur in this case.
    OrganizationSlugInUseError: the slug is already taken. No
        partial state is left behind because the transaction rolls
        back.
    ValueError: actor_id is missing.

### Function `_clone_default_role_templates`

Clone the 11 default Role templates to per-tenant Role rows.

Called inside ``create_organization``'s atomic block. Pre-conditions:

* The 11 templates exist (seed_v1 ran).
* No per-tenant Role rows for this organization exist yet (the
  Organization was just created in the same transaction).

Each clone:

* has organization=organization (tenant-scoped),
* has is_default=False, is_locked=False (tenant copies can be
  modified from M1 onward by Org Admin),
* preserves the template's is_scoped_role flag,
* has matching RoleCapability rows pointing at the same Capability
  objects.

### Function `assign_owner_membership`

Create the bootstrap Owner Membership for a tenant.

Steps performed inside a single ``transaction.atomic()``:

1. Confirm the Organization and User both exist.
2. Confirm no Membership already exists for the pair.
3. Create a Membership with status=ACTIVE.
   ``is_default_for_user`` is set True if and only if the user
   does not already have a default Membership in another org.
4. Look up the per-tenant Owner Role (cloned by
   :func:`create_organization`).
5. Create a MembershipRole row linking the membership to that role.
6. Emit ``MEMBERSHIP_CREATED`` and ``ROLE_ASSIGNED`` audit events.

Args:
    organization_id: The Organization the new member joins.
    user_id: The User being made the Owner.
    actor_id: The User performing the action. For system-bootstrap
        flows this is the System User.
    first_name: Optional given name on the Membership.
    last_name: Optional family name on the Membership.

Returns:
    The newly created Membership.

Raises:
    OrganizationNotFoundError: the org doesn't exist.
    UserNotFoundError: the target user doesn't exist.
    MembershipAlreadyExistsError: the (user, org) pair is already
        a Membership.
    RuntimeError: the per-tenant Owner Role is missing (would
        indicate create_organization was bypassed).

## `backend/apps/platform/organizations/services/exceptions.py`

### Module docstring

Exceptions raised by the organization services.

These are typed for the service-layer caller. Callers should NEVER
``except IntegrityError`` to detect a slug collision — that's an
implementation detail. They catch :exc:`OrganizationSlugInUseError`.

### Class `OrganizationSlugInUseError`

Raised when create_organization sees an existing slug.

The slug uniqueness constraint is the only realistic source of
IntegrityError on the Organization insert, so the service catches
that case explicitly and re-raises with a typed exception so
callers can branch cleanly without parsing exception strings.

Attributes:
    slug: the slug that already exists.

### Class `OrganizationNotFoundError`

Raised when a service lookup by organization_id returns nothing.

### Class `UserNotFoundError`

Raised when a service lookup by user_id returns nothing.

### Class `MembershipAlreadyExistsError`

Raised when assign_owner_membership is called for a (user, org) pair
that already has a Membership row.

This is a service-layer protection: the M0 D2 partial unique index
enforces "at most one Membership per (user, organization)" at the
DB level. Catching the existence check in Python first lets callers
branch on a typed exception instead of an IntegrityError.

Attributes:
    user_id: the user that already has a membership.
    organization_id: the organization the user is already a member of.

## `backend/apps/platform/organizations/tests/services/test_assign_owner_membership.py`

### Module docstring

Tests for apps.platform.organizations.services.assign_owner_membership.

### Function `test_role_assignment_failure_rolls_back_membership`

If the MembershipRole insert blows up, the Membership rolls back.

## `backend/apps/platform/organizations/tests/services/test_create_organization.py`

### Module docstring

Tests for apps.platform.organizations.services.create_organization.

### Function `test_collision_does_not_emit_audit_event`

The audit event is inside the atomic block, so a slug collision
rolls back the audit event along with the (failed) Organization
insert.

### Function `test_create_is_not_idempotent_on_existing_slug`

Idempotent slug handling is the seed_dev_tenant convenience
pattern, NOT the production service pattern. The service raises a
typed exception so callers explicitly choose how to handle
collisions.

### Function `test_role_clone_runs_in_same_transaction_as_org_create`

If role cloning blows up, the Organization insert rolls back too.

## `backend/apps/platform/rbac/__init__.py`

### Module docstring

RBAC: capabilities, roles, grants, enforcement (B.6).

Phase 1: app skeleton only — concrete Capability, Role, RoleCapability,
MembershipRoleAssignment, MembershipCapabilityGrant land in M1, and
``seed_v1`` (I.6.3) lands as ``0002_seed_v1`` in this app.

## `backend/apps/platform/rbac/admin.py`

### Module docstring

Dev-only Django admin registrations for platform_rbac.

Registrations live in ``apps.platform.accounts.admin``. This file exists
only to be discovered by Django's admin autoloader.

## `backend/apps/platform/rbac/models.py`

### Module docstring

RBAC models: Capability, Role, RoleCapability, MembershipRole,
MembershipCapabilityGrant (B.6.7).

The capability registry is populated by the ``seed_v1`` data migration
(I.6.3). Role templates with ``organization=None, is_locked=True,
is_default=True`` are also seeded; per-tenant Owner/Admin/etc. roles
are created by ``services.create_organization`` (I.6.6).

Permission evaluation algorithm: B.6.2.

Index naming: every ``models.Index`` carries an explicit ``name=``
argument. Auto-generated index names are fragile across Django versions
(the 6-char hash suffix Django computes can drift) and cause spurious
``RenameIndex`` migrations on every ``makemigrations`` run. Always name
indexes explicitly going forward.

### Function `_new_uuid`

UUID v7 factory (Python 3.14+).

### Class `CapabilityGrantType`

Per-membership capability overrides (B.6.7).

### Class `Capability`

Atomic permission unit (B.6.3, B.6.7).

Capabilities are platform-scoped (no organization FK). Their codes
are stable contract strings — renaming is a breaking change
(G.2.3 analog).

### Class `Role`

A bundle of capabilities (B.6.7).

Template roles have ``organization=NULL, is_default=True,
is_locked=True``. Per-tenant roles have a concrete organization FK
and are cloned from templates by ``services.create_organization``
(I.6.6).

Uniqueness is ``(organization, code)``. Because ``organization`` is
nullable and Postgres treats ``NULL`` as distinct by default in unique
indexes, the constraint uses ``nulls_distinct=False`` so a single
template per ``code`` is enforced.

### Class `RoleCapability`

Role → Capability assignment (B.6.7).

### Class `MembershipRole`

Membership → Role assignment (B.6.7).

Note: the guide names the entity ``MembershipRole`` (B.6.7 line 2073).
The M2M is between membership and role; one membership can hold
multiple roles.

### Class `MembershipCapabilityGrant`

Per-membership capability override (GRANT or DENY) — B.6.2 step 5.

DENY beats GRANT (B.6.2). Applied on top of role-derived capabilities
during permission evaluation.

## `backend/apps/platform/rbac/seeds/__init__.py`

### Module docstring

V1 capability and default-role seed sources.

These modules are pure Python data — no Django model imports. They are
read by the ``seed_v1`` data migration (I.6.3) which itself uses
``apps.get_model(...)`` to obtain the historical model classes.

Editing capability codes here is a breaking change. Adding new
capabilities is additive and should be done in a successor seed
migration (I.6.5), NOT by editing this file.

## `backend/apps/platform/rbac/seeds/v1_capabilities.py`

### Module docstring

V1 capability registry (B.6.3).

Each entry is a dict with the shape:

    {
        "code": "leads.view",
        "name": "View leads",
        "description": "Read access to lead records.",
        "category": "Lead Management",
    }

Codes are stable contract strings. Renames are breaking changes
(propagation policy: B.6.5/B.6.6).

## `backend/apps/platform/rbac/seeds/v1_default_roles.py`

### Module docstring

V1 default role templates (B.6.4).

Each entry describes a template role that the ``seed_v1`` migration
installs with ``organization=NULL, is_default=True, is_locked=True``.

When ``services.create_organization`` runs (I.6.6), these templates are
cloned to org-scoped Role rows so per-tenant role assignment can begin.

The ``ALL_CAPABILITIES`` sentinel below means "every non-deprecated
capability in V1_CAPABILITIES at seed time." The seed migration
expands it. New capabilities added in later seed migrations (I.6.5)
auto-extend the Owner template only; they DO NOT auto-extend templates
that materialized this sentinel at seed time.

## `backend/apps/platform/rbac/tests/seeds/test_seed_v1.py`

### Module docstring

Seed-v1 verification tests.

Covers J.2.4 exit criterion #6 plus the M0/M1 RBAC-bootstrap assertions:

* exactly one is_system=True user exists after seed runs
* all V1 capabilities exist after seed runs
* all 11 default role templates exist with their expected capability sets
* re-running the seed is a no-op (idempotency)

These tests rely on ``backend/conftest.py`` re-applying the idempotent
seed function at session start so the seeded state is reliably present
before each test, regardless of what previous transactional tests did
to the database.

### Function `test_no_per_tenant_roles_created_by_seed_function`

Per-tenant Owner/Org Admin/etc. roles are created by
services.create_organization (I.6.6) and seed_dev_tenant, NOT by the
seed function itself.

This test re-runs the seed function in isolation and asserts that it
produced no organization-scoped Role rows of its own. We don't make a
statement about pre-existing org-scoped rows in the database (a
sibling test in this session may have created some via
seed_dev_tenant); we only assert that this specific invocation of
the seed function did not create any.

### Function `test_reapplying_seed_is_idempotent`

Re-execute the seed function and verify row counts are unchanged.

Runs inside a single transactional test (no ``transaction=True``)
so the test database keeps its seeded state after the test exits.
The earlier shape of this test used ``transaction=True`` which
truncates the DB between tests and broke subsequent runs.

### Function `test_sales_staff_has_client_contacts_and_locations_management`

D2 follow-up: Sales Staff template includes contacts/locations management.

## `backend/apps/platform/support/__init__.py`

### Module docstring

Platform console + support impersonation (B.7, H.7).

The ``/platform/`` URL mount lives here. M0 ships a minimal
authenticated landing page; impersonation, tenant search, and audit
review land in M1.

## `backend/apps/platform/support/management/commands/seed_dev_tenant.py`

### Module docstring

Dev-only standalone management command: seed_dev_tenant (I.6.2).

Creates a fully-functional sample tenant so an engineer can sign in and
walk through ``/platform/`` with real organization data.

This command MUST NOT run in non-dev environments. It refuses to execute
unless ``DJANGO_DEBUG`` is true OR the active settings module is
``config.settings.dev`` / ``config.settings.test``.

After M1 D2: the creation path delegates to
:func:`apps.platform.organizations.services.create_organization` and
:func:`apps.platform.organizations.services.assign_owner_membership`.
The ``--reset`` path retains direct ORM writes because it is a
destructive dev-only tool with no service-layer analogue.

After M1 D4: the creation path also seeds a verified primary allauth
``EmailAddress`` row for the demo admin user. Without it, the
production-grade ``ACCOUNT_EMAIL_VERIFICATION = "mandatory"`` policy
would gate every dev login behind clicking a Mailpit link. The seeded
``EmailAddress`` is idempotent via ``update_or_create``; the
``--reset`` path doesn't need to clean it up because allauth's
``EmailAddress.user`` FK CASCADEs from User deletes.

Exempt from the service-layer discipline AST check (A.4.5) because
management commands are explicitly listed in the exemption set, same as
admin/migrations/tests.

### Class `Command`

Seed a demo tenant for local development.

### Function `_reset_tenant`

Delete the demo tenant and its associated rows.

Order matters because of FK protection:
  MembershipRole → Membership → Role (per-tenant) → Organization.
Capability rows are platform-level and are never touched here.

EmailAddress cleanup: not explicit here. ``EmailAddress.user``
is a CASCADE FK in allauth's model, so when this method
decides to drop the admin user (the "no remaining memberships"
branch below), allauth's EmailAddress rows for that user are
removed automatically. When we KEEP the admin user (they
still have memberships in other orgs), keeping their verified
EmailAddress is the right call — they need it to sign in to
those other orgs.

### Function `_ensure_verified_email_address`

Idempotently install a verified primary EmailAddress for the user.

M1 D7 Phase 1 — the underlying logic moved to
:mod:`apps.platform.accounts.utils.email_verification` so the
same idempotent installation powers ``UserManager.create_superuser``.
This method is kept as a thin wrapper because the seed command's
summary output depends on the ``created`` boolean for reporting.

Returns a ``(EmailAddress, created)`` tuple to preserve the
pre-refactor signature. The shared utility returns only the
``created`` bool; we re-fetch the row here for the tuple's first
element. The extra query is a once-per-seed-run cost in dev only.

## `backend/apps/platform/support/tests/test_seed_dev_tenant.py`

### Module docstring

Tests for the seed_dev_tenant management command (M1 D4 update).

Verifies:
- Existing behavior: org + user + membership + owner role created.
- M1 D4 addition: verified primary EmailAddress row created for the
  admin user.
- Idempotency: re-running the command does not duplicate the
  EmailAddress.
- --reset: when the admin user is dropped, the EmailAddress row is
  CASCADE-deleted (no explicit cleanup needed).

## `backend/apps/platform/support/urls.py`

### Module docstring

Platform console URLs.

Mounted at ``/platform/`` (H.7.2). M0 exposes a single landing page that
proves staff-only routing works. Cross-tenant tooling (impersonation,
tenant search, audit review) lands in M1.

## `backend/apps/platform/support/views.py`

### Module docstring

Platform console views.

In M0 this is a thin authenticated landing page that proves the
``/platform/`` mount renders for ``is_staff`` users (H.7.1, H.7.4).

The real platform admin (tenant search, impersonation, audit review,
dead letters, OAuth/OIDC providers) lands in M1+ as separate views,
each calling the service layer for state changes (H.7.6).

### Class `PlatformConsoleHomeView`

Authenticated platform-console landing page.

Authorization in M0 is a simple ``is_staff`` check — capability-based
enforcement (B.6.8) wires up in M1 once the capability registry exists.

## `backend/apps/web/__init__.py`

### Module docstring

Server-rendered web surfaces.

Three sub-apps:

* ``apps.web.landing``       Custom root-domain landing page (H.3.3, H.8).
* ``apps.web.auth_portal``   Login, MFA, invite, password-reset, org picker.
* ``apps.web.tenant_portal`` Tenant-facing Django-template UI for Phase 1.

## `backend/apps/web/auth_portal/__init__.py`

### Module docstring

Root-domain authentication portal (H.3).

In M0 this app exposes a minimal scaffold for ``/login/`` so that the
landing page's sign-in CTA renders the correct page. The full login,
MFA, OAuth/OIDC, password-reset, invite-acceptance, and org-picker
flows wire up in M1 against django-allauth (B.3.2, B.4).

## `backend/apps/web/auth_portal/tests/test_allauth_template_smoke.py`

### Module docstring

Allauth template-rendering smoke suite (M1 D4 + M1 D5 Phases 3, 5).

THE SPINE OF M1 D4 / D5 TEST COVERAGE.

For each allauth-rendered template, this suite:
1. Sets up the right user state (anonymous / verified / TOTP / etc.).
2. Issues a request that lands the user on that template.
3. Asserts the response is the expected status (default 200).
4. Asserts a representative ``mph-*`` class appears in the body
   (proves our override was picked up, not allauth's bundled default).

Any new template override added in future milestones MUST be added
to this table.

**Allauth-may-redirect-through-reauth note.** Allauth 65.x gates MFA
management actions behind a fresh-authentication check. Tests that
use ``client.force_login(...)`` don't satisfy this freshness check,
so a GET to e.g. ``/accounts/2fa/totp/activate/`` follows allauth's
redirect to ``/accounts/reauthenticate/`` first. The smoke assertion
therefore accepts EITHER the originally-targeted chrome class OR
the reauthenticate-page's chrome class. The end-to-end MFA test
exercises the real reauth-then-activate flow separately.

**socialaccount/login.html is NOT in this suite.** That template
renders only mid-OAuth-flow (when POSTing to
/accounts/oidc/<provider>/login/), which requires a configured
provider AND the mock OIDC issuer (Phase 6). Smoke-testing it
here would either need stubbed allauth view machinery or the mock
issuer — both belong to Phase 6.

**Non-200 expected_status note.** Some allauth views deliberately
return non-200 statuses on success-of-rendering (e.g. the
``socialaccount_login_error`` view returns 401 because it represents
an auth failure that nevertheless renders a page). The
``expected_status`` field on each ``TemplateCase`` declares the
status the test should accept. A 200 default covers most cases.

### Class `TemplateCase`

A single allauth template to smoke-test.

### Class `TestAllauthTemplateSmoke`

One parametrized test covering every allauth-rendered template.

### Class `TestAllauthTemplateSmokeStateful`

Smoke tests for templates that need stateful setup beyond
fixture login (email confirmations, password reset keys).

### Class `TestLoginPageProviderButtons`

The login page renders a button per active OAuthProviderConfig.

### Class `TestConnectionsPageProviderListing`

The connections page lists unlinked active providers.

### Function `test_no_providers_no_button_section`

When no providers are active, the SSO section is absent.

## `backend/apps/web/auth_portal/tests/test_handoff_issue_view.py`

### Module docstring

Tests for HandoffIssueView (M1 D6 Phase 4B).

## `backend/apps/web/auth_portal/tests/test_login_scaffold.py`

### Module docstring

M0 login-scaffold test (REPLACED in M1 D4).

The M0 scaffold view rendered a styled form that did not authenticate.
M1 D4 replaced that view with a permanent redirect to allauth's
canonical `/accounts/login/`. The scaffold test is therefore replaced
by `test_url_routing.py::TestAuthPortalRouting::test_login_redirect_to_allauth`.

This file remains as a tombstone documenting the migration so a
future engineer doesn't try to revive the scaffold.

## `backend/apps/web/auth_portal/tests/test_select_org_view.py`

### Module docstring

Tests for SelectOrgView (M1 D6 Phase 4B, B.4.15).

## `backend/apps/web/auth_portal/tests/test_url_routing.py`

### Module docstring

Tests for auth_portal URL routing (M1 D4).

Verifies:
- /login/ permanent-redirects to /accounts/login/ (preserving ?next=).
- /select-org/ requires authentication.
- /accounts/login/ resolves to allauth's LoginView (override is picked up).

### Function `test_accounts_login_resolves_to_allauth`

allauth.urls is mounted at /accounts/ — verify it owns login.

## `backend/apps/web/auth_portal/urls.py`

### Module docstring

URL configuration for the auth_portal app.

The bulk of the auth surface is mounted under /accounts/ by allauth
(see config/urls.py). This module exposes the auxiliary auth_portal
routes:

* /login/ — permanent redirect to /accounts/login/ (M1 D4).
* /select-org/ — real org picker (M1 D6 Phase 4B).
* /oauth-help/<reason>/ — OAuth-failure help page (M1 D5 Phase 3).
  Mounted outside the /accounts/ namespace to avoid resolver
  ambiguity with allauth's URLconf.
* /handoff/issue/ — POST endpoint that mints handoff tokens
  (M1 D6 Phase 4B).

The ``app_name`` namespace is ``auth_portal``; templates and the
OAuth adapter refer to routes as e.g. ``auth_portal:oauth_help``.

## `backend/apps/web/auth_portal/views.py`

### Module docstring

Auth-portal views (M1 D4).

The M0 scaffold's ``LoginPageView`` was a placeholder rendering of the
styled login form. M1 D4 replaces it with a permanent redirect to
allauth's canonical ``/accounts/login/``. This keeps any inbound
``/login/`` links working (landing-page CTA, marketing materials,
bookmarks) while making allauth the sole owner of the actual login
flow.

The redirect preserves ``?next=`` so post-login navigation continues
to work as expected.

### Class `LoginPageView`

Permanent redirect from ``/login/`` to ``/accounts/login/``.

Allauth owns the login form and POST handler. This view exists so
the historical ``/login/`` URL keeps resolving.

## `backend/apps/web/auth_portal/views_handoff_issue.py`

### Module docstring

Handoff issue HTTP endpoint (M1 D6 Phase 4B, B.4.12 issue side).

POST /handoff/issue/

Form data: ``membership_id`` (UUID).

The endpoint is the user-explicit-selection counterpart to the
single-membership auto-advance code path in
:mod:`apps.web.auth_portal.views_select_org`. It validates that
the membership belongs to the requesting user and is active, mints
the handoff token, emits ``MEMBERSHIP_SELECTED`` with
``auto_selected=False``, and renders the auto-POST form.

**Security boundary.** The endpoint trusts the POST'd
``membership_id`` to identify which org the user wants. It does
NOT trust it to identify the USER — that comes from
``request.user`` (Django auth). The membership lookup is
constrained to the current user; a forged membership_id pointing
to another user's row returns 404.

CSRF protection: standard Django CSRF (this is a same-origin POST
from the picker page on root domain to the issue endpoint on root
domain).

### Class `HandoffIssueView`

POST-only handoff issue endpoint.

## `backend/apps/web/auth_portal/views_oauth_help.py`

### Module docstring

OAuth-failure help page (M1 D5 Phase 3).

Renders contextual copy when an OAuth/OIDC login is rejected by the
:class:`MphSocialAccountAdapter`. Each ``reason`` slug maps 1:1 to a
typed exception raised by :func:`resolve_external_user`:

* ``provider_not_active`` → :class:`ProviderNotActiveError`
* ``domain_not_allowed`` → :class:`EmailDomainNotAllowedError`
* ``email_not_verified`` → :class:`EmailNotVerifiedError`
* ``conflicting_identity`` → :class:`ConflictingExternalIdentityError`
* ``user_inactive`` → :class:`UserInactiveError`
* ``no_existing_user`` → :class:`NoExistingUserAndSelfRegistrationDisabledError`

The view validates the inbound slug against a closed allowlist; unknown
slugs render the generic ``provider_not_active`` copy (the safest
default — generic "credentials invalid" without policy leakage).

### Function `oauth_help`

Render the OAuth help page for a given failure reason.

Closed allowlist: unknown ``reason`` slugs render the generic
``provider_not_active`` copy (safe default).

## `backend/apps/web/auth_portal/views_select_org.py`

### Module docstring

Org-picker view (M1 D6 Phase 4B, B.4.15).

Replaces the M1 D4 placeholder. Implements the B.4.15 branch table:

* **No active memberships, not staff** → render
  ``no_active_access.html`` (HTTP 200, message + logout link).
* **Exactly one active membership** → auto-issue handoff token,
  render ``handoff_form.html`` with JavaScript auto-submit.
* **Multiple active memberships** → render ``select_org.html``
  with one card per membership.
* **Staff user (regardless of memberships)** → render
  ``select_org.html`` with staff-specific copy including a link
  to the platform console (M1 D7 destination).

The picker view doesn't itself issue tokens for the multi-
membership case — it renders a list of POST forms targeting
``/handoff/issue/``. The user clicks one, the issue view mints
the token, that view renders the auto-POST form.

**Why two views (picker + issue) instead of one?** Separation of
concerns: the picker is read-only (lists memberships); the issue
endpoint is the only place that calls ``issue_handoff_token`` and
the only place that audits ``MEMBERSHIP_SELECTED`` (for the user-
explicit case). The auto-advance single-membership branch also
calls the issue logic, but in-line rather than via redirect to
keep the UX as a single page load.

### Class `SelectOrgView`

GET-only org picker / auto-advance / no-access page.

### Function `_issue_token_for_membership`

Mint a handoff token + emit MEMBERSHIP_SELECTED audit.

Returns the JWT on success, None if no active signing key
exists (an operational failure that the caller should surface
to the user).

Args:
    request: For session reads (auth_method, mfa_satisfied_at).
    membership: The chosen Membership.
    auto_selected: True for the single-membership auto-advance
        path; False for explicit user selection. Recorded in
        audit metadata.

### Function `_derive_auth_method`

Determine ``(auth_method, auth_provider)`` from session state.

Looks for ``mph_login_provider_code`` (written by the OAuth
signal handler in M1 D5). Presence → OAuth/OIDC login; the
provider code tells us which.

For local-password logins, the provider code is absent and we
return ``("password", None)``.

The distinction between "oauth2" and "oidc" requires looking
up the provider config. For M1 D6 we use "oidc" as the
canonical value when a provider is set; this matches our
primary OAuth integration shape (B.3.7 supports both but the
catalog treats them interchangeably for the
``auth_method`` claim).

### Function `_read_mfa_satisfied_at`

Read mfa_satisfied_at from session.

Written by ``apps.platform.accounts.signals_mfa`` on
``authenticator_used`` / ``authenticator_added``, or by the
trusted-provider OAuth middleware bypass. Falls back to
``timezone.now()`` if absent — a defensive default that the
issue-side staleness check (1 hour max) will still accept.

**Known limitation:** the fallback masks the case where MFA was
never satisfied at all. For local-password users, the middleware
forces enrollment before they can reach the picker, so this is
practically unreachable. For OAuth users with un-trusted
providers, the middleware also forces enrollment. For trusted-
provider OAuth users, the middleware writes the key. Falling
back to now() is therefore a belt-and-suspenders default that
only fires if the session was cleared mid-flow (extreme edge).

### Function `_auto_advance`

Single-membership auto-issue path.

Mints the token, emits ``MEMBERSHIP_SELECTED`` with
``auto_selected=True``, renders the auto-POST form.

### Function `_render_handoff_form`

Render the auto-POST form pointing at the tenant subdomain.

### Function `_render_no_signing_key_available`

Render error when no active HandoffSigningKey exists.

Operationally fatal — platform admin must create + promote
a key. The picker shows a user-friendly error rather than a
500.

## `backend/apps/web/landing/__init__.py`

### Module docstring

Custom root-domain landing page (H.3.3).

Permanently server-rendered (A.4.3, H.8.5). Owns the templates under
``templates/landing/`` and the public CSS under ``static/landing/css/``.

## `backend/apps/web/landing/tests/test_landing.py`

### Module docstring

Smoke tests for the public landing page (H.3.3, J.2.4 #7).

### Function `test_landing_page_uses_public_body_class`

H.8.5 requires the ``mph-public-body`` class on the landing page.

## `backend/apps/web/landing/urls.py`

### Module docstring

Public root-domain URLs.

## `backend/apps/web/landing/views.py`

### Module docstring

Public landing page (H.3.3).

This view MUST:

1. Render at ``/``.
2. Use the shared ``base.html`` and landing CSS (H.8).
3. Provide a clear sign-in path to ``/login/``.
4. Avoid tenant-specific data.
5. Avoid requiring authentication.
6. Avoid requiring React or tenant-portal JS.
7. Remain server-rendered in Phase 2.

The page content (plans, features, workflow) is public marketing copy
and MUST NOT be treated as a source of truth for pricing/billing logic
(H.3.3 final paragraph).

## `backend/apps/web/tenant_portal/__init__.py`

### Module docstring

Tenant-facing Django-template UI for Phase 1 (H.4).

M0 ships a thin dashboard placeholder using the committed dashboard.css.
Real tenant-portal screens land progressively from M2 onward.

## `backend/apps/web/tenant_portal/tests/test_handoff_consume_view.py`

### Module docstring

Tests for HandoffConsumeView + TenantLandingView (M1 D6 Phase 4B).

### Function `_enable_host_routing`

These tests exercise tenant-subdomain routing.

### Function `_load_session_for_host`

Read the session for a specific host's cookie.

Django's ``client.session`` is host-blind — it always reads the
cookie named ``settings.SESSION_COOKIE_NAME``. Our
``PerTenantSessionMiddleware`` writes the cookie under a host-
derived name (``tenant_session_{slug}`` on tenant subdomains).
This helper resolves the right cookie name and loads the
session row from the DB backend.

## `backend/apps/web/tenant_portal/tests/test_multi_host_integration.py`

### Module docstring

End-to-end multi-host integration tests (M1 D6 Phase 6, J.3.9 #13-#16).

These tests simulate the full root→tenant→logout flow as a browser
would experience it:

1. POST credentials to allauth login on root domain.
2. Complete MFA (TOTP authenticator pre-installed in fixtures).
3. Hit /select-org/ on root domain.
4. Auto-advance (one membership) or pick (multi-membership).
5. POST the issued JWT to the tenant subdomain's /handoff/.
6. Land on the tenant home with the B.4.14 session keys populated.
7. Tenant or root logout, depending on the test scenario.

Cookie semantics matter at every hop: the client carries one cookie
per host. Phase 3's PerTenantSessionMiddleware writes
``mph_root_session`` on root domain and ``tenant_session_{slug}`` on
tenant subdomains. ``client.session`` is host-blind (reads
``settings.SESSION_COOKIE_NAME``); we read host-scoped sessions via
the ``_load_session_for_host`` helper.

The MFA flow is bypassed for ergonomics: we pre-install a TOTP
authenticator on the user fixture and write the
``mph_mfa_satisfied_at`` session key directly. This decouples the
integration tests from allauth's MFA enrollment UI, which is exercised
in ``test_mfa_end_to_end.py``.

### Function `_enable_host_routing`

All integration tests exercise per-host URL routing.

### Function `_load_session_for_host`

Read the session for a specific host's cookie name.

### Function `_login_user_with_mfa`

Establish a logged-in root session with MFA satisfaction marker.

Skips the password POST + TOTP challenge UI (those flows are covered
in test_mfa_end_to_end.py). We force_login + write the MFA marker
directly, replicating the state the user would be in immediately
after completing both steps via the UI.

### Function `_follow_handoff_form`

Parse the auto-POST form from the issue response and submit it.

### Class `TestSingleMembershipEndToEnd`

User with one membership goes from picker straight to tenant.

### Class `TestMultiMembershipEndToEnd`

User with multiple memberships sees picker, chooses one, lands on tenant.

### Class `TestHostMismatchRejection`

Token issued for Acme is rejected if posted to Globex's subdomain.

### Class `TestLogoutFlowEndToEnd`

Logout from one host doesn't unintentionally kill the other.

### Function `test_audit_trail_complete`

The full flow emits MEMBERSHIP_SELECTED, HANDOFF_TOKEN_ISSUED,
HANDOFF_TOKEN_CONSUMED, TENANT_SESSION_ESTABLISHED in order.

### Function `test_token_for_acme_posted_to_globex_rejected`

A handoff token bound to Acme MUST fail when consumed on
Globex's subdomain, even if the user has a valid Globex
membership. B.4.12 host-binding check.

### Function `test_tenant_logout_preserves_root_session`

After tenant logout, the user can return to root /select-org/
and pick another org without re-authenticating.

### Function `test_root_logout_kills_handoff_tokens`

Root logout revokes all outstanding handoff tokens.

### Function `test_root_logout_emits_root_session_logout`

Root logout always emits ROOT_SESSION_LOGOUT.

## `backend/apps/web/tenant_portal/tests/test_tenant_logout_view.py`

### Module docstring

Tests for TenantLogoutView (M1 D6 Phase 5, B.4.17).

### Function `_enable_host_routing`

Tenant logout tests exercise tenant-subdomain routing.

### Function `_load_session_for_host`

Read the session for a specific host's cookie.

### Function `test_logout_does_not_revoke_handoff_tokens`

Tenant logout MUST NOT revoke outstanding handoff tokens.

Other tenant sessions established from the same root session
should remain accessible.

### Function `test_logout_when_not_authenticated_redirects`

Anonymous tenant logout request just redirects to root picker.

## `backend/apps/web/tenant_portal/urls.py`

### Module docstring

Tenant-subdomain URL routing (M1 D6 Phase 4B + Phase 5).

Phase 4B populated the handoff consume endpoint and tenant landing
page. Phase 5 adds the tenant logout endpoint.

Lives on tenant subdomains only. The host-routing middleware in
``apps.common.sessions.middleware.HostUrlconfMiddleware`` ensures
tenant requests resolve against this URLconf, never against the
root-domain ``config.urls_root``.

## `backend/apps/web/tenant_portal/views.py`

### Module docstring

Tenant-portal views (M1 D6 Phase 4B + Phase 5).

### Class `HandoffConsumeView`

POST receiver for cross-domain handoff.

### Class `TenantLandingView`

GET-only tenant landing page after handoff.

Not ``@login_required``; the redirect target for unauthenticated
tenant requests is on the ROOT domain (``mph.local/select-org/``).

### Class `TenantLogoutView`

Tenant-local logout (M1 D6 Phase 5, B.4.17).

Destroys ONLY this tenant's session. The root-domain session
remains intact; other tenant sessions remain intact. Outstanding
handoff tokens for this user are NOT revoked — root-domain
logout owns that.

POST-only (CSRF-protected by Django's normal CSRF middleware,
which DOES protect tenant subdomain requests — only the cross-
domain handoff consume endpoint needs ``@csrf_exempt``).

Emits ``TENANT_SESSION_LOGOUT`` BEFORE calling
``django.contrib.auth.logout()`` so we still have access to
``request.user.id`` and the B.4.14 session keys for the audit
payload. The ``user_logged_out`` signal handler in
``apps.platform.accounts.signals_logout`` detects this is a
tenant host and skips the root-logout revocation path.

## `backend/config/__init__.py`

### Module docstring

Top-level Django project package for MyPipelineHero.

Exposes the Celery app at module load so workers can pick it up via
``celery -A apps.common.celery worker`` and so ``shared_task`` decorators
register correctly.

## `backend/config/asgi.py`

### Module docstring

ASGI config for MyPipelineHero.

## `backend/config/settings/__init__.py`

### Module docstring

Settings package.

Concrete settings modules:

    config.settings.base        # shared base
    config.settings.dev         # local development
    config.settings.test        # automated tests
    config.settings.staging     # production-like validation
    config.settings.demo        # demo / sandbox
    config.settings.prod        # production

Selected via the DJANGO_SETTINGS_MODULE environment variable.

## `backend/config/settings/base.py`

### Module docstring

Shared Django settings for MyPipelineHero.

Authoritative reference: `docs/guide.md` parts A, B, G, H, I.

This module sets defaults and shape. Per-environment modules
(``dev``, ``test``, ``staging``, ``demo``, ``prod``) extend it and
override what they need.

Secrets and environment-specific values come from environment variables.
We never commit a real ``.env`` and never log secrets.

## `backend/config/settings/demo.py`

### Module docstring

Demo / sandbox settings.

Production-equivalent posture. The data-anonymization / refresh pipeline
(I.3.4) lives outside this settings file.

## `backend/config/settings/dev.py`

### Module docstring

Local development settings.

Loads ``.env`` via plain os.environ — Docker Compose injects them.

Note: S104 (binding to all interfaces) is suppressed for this file in
``pyproject.toml`` because the local Django web container intentionally
binds to ``0.0.0.0:8000`` so the host can reach it. Production settings
never get this exemption.

Note on annotations: per-environment overrides use bare assignment (no
``: bool``, ``: list[str]`` etc.) so that mypy treats them as rebinds of
the symbols already imported from ``.base`` rather than redefinitions.
This is the idiomatic Django pattern for layered settings under strict
type checking.

## `backend/config/settings/prod.py`

### Module docstring

Production settings.

See ``dev.py`` for a note on why per-environment overrides use bare
assignment instead of fresh type annotations.

## `backend/config/settings/staging.py`

### Module docstring

Staging settings — production-like validation environment.

See ``dev.py`` for a note on why per-environment overrides use bare
assignment instead of fresh type annotations.

## `backend/config/settings/test.py`

### Module docstring

Test settings — used by pytest and CI.

Designed to be fast, deterministic, and offline. No network services
beyond the local DB are required to run the suite.

See ``dev.py`` for a note on why per-environment overrides use bare
assignment instead of fresh type annotations.

## `backend/config/urls.py`

### Module docstring

Default URLconf — used when HostUrlconfMiddleware doesn't pick
a per-host URLconf for the current request.

This module re-exports the root URLconf's urlpatterns so any
codepath that doesn't go through the per-host middleware (error
handlers, ``manage.py shell``, ``reverse()`` outside a request,
test cases not exercising host-aware behavior) still resolves the
landing / auth_portal / allauth routes.

Per-host routing is in :mod:`config.urls_root` and
:mod:`config.urls_tenant`; the middleware in
``apps.common.sessions.middleware.HostUrlconfMiddleware`` switches
between them based on request host.

## `backend/config/urls_root.py`

### Module docstring

Root-domain URL routing (M1 D6 Phase 4A).

Mounted by ``HostUrlconfMiddleware`` when the request host is the
root domain (``mph.local`` in dev). Hosts the landing page, the
allauth auth surface (login / MFA / OAuth / email management), the
auth_portal (org picker, OAuth help), the health endpoints
(/healthz, /readyz), and — future — the platform admin console at
``/platform/``.

The tenant-subdomain routes (tenant portal, ``/handoff/`` consume)
live in :mod:`config.urls_tenant` and are NOT reachable from root.

OTHER-scope hosts (testserver, localhost, IPs) resolve against
``settings.ROOT_URLCONF`` which re-exports this module's
``urlpatterns``. ``HostUrlconfMiddleware`` deliberately does NOT
override ``request.urlconf`` for OTHER scope so tests that use
``override_settings(ROOT_URLCONF=...)`` continue working.

**Health URLs MUST stay at root paths** (``/healthz``, ``/readyz``).
Existing middleware allowlists and external probes depend on these
exact paths.

## `backend/config/urls_tenant.py`

### Module docstring

Tenant-subdomain URL routing (M1 D6 Phase 4A).

Mounted by ``HostUrlconfMiddleware`` when the request host matches
the tenant-subdomain template (``{slug}.mph.local``). Hosts the
tenant portal, the ``/handoff/`` consume endpoint, and tenant-
scoped resources.

Phase 4A leaves this URLconf minimal (a fallback include of
``tenant_portal.urls`` which itself is empty for now). Phase 4B
populates the real handoff consume endpoint + tenant landing.

The root-domain routes (allauth, picker) are NOT reachable from
tenant subdomains — the URL resolver only knows about routes in
this module when the host is TENANT scope.

## `backend/config/wsgi.py`

### Module docstring

WSGI config for MyPipelineHero (Gunicorn entrypoint).

## `backend/conftest.py`

### Module docstring

Project-wide pytest configuration.

Located at ``backend/conftest.py`` so pytest-django discovers it before
any app-level test files.

Houses:

1. ``django_db_setup`` override (existing) — re-applies the platform
   seed (96 capabilities, 11 default role templates, the System User)
   once per session so tests see consistent seed state even after
   transactional truncation.

2. Auth fixtures (M1 D4) — promoted from
   ``apps/platform/accounts/tests/conftest.py`` so tests in any
   directory can reference them. The fixtures cover the User-with-no-
   MFA, User-with-TOTP, and User-with-TOTP-plus-recovery-codes states
   used by the allauth template smoke suite and the signal/middleware
   tests.

3. ``_reset_audit_buffer`` autouse fixture (M1 D4) — promoted from
   ``apps/platform/audit/conftest.py``. Clears the in-memory audit
   buffer before AND after each test so audit-emission assertions
   don't accumulate events across tests. The original
   ``apps/platform/audit/conftest.py`` is intentionally retained so
   the buffer-reset wiring stays visible in the audit app, even
   though it now runs redundantly (the double-clear is free).

Pure helper functions used by tests (``totp_code_for``,
``_install_totp_authenticator``, ``_install_recovery_codes``) live in
``apps/platform/accounts/tests/_helpers.py`` so test code can import
them. Conftest is not a regular Python module and cannot host
importable helpers.

### Function `user_verified_with_totp`

User with verified email AND TOTP enrolled.

### Function `_reset_handoff_fakeredis_between_tests`

Each test starts with a fresh in-memory fakeredis.

Without this, a token issued in test A is still in the fakeredis
store when test B runs, causing cross-test pollution.

### Function `django_db_setup`

Ensure platform seed data is present after Django sets up the test DB.

pytest-django's default ``django_db_setup`` runs Django migrations,
which DOES run the ``seed_v1`` data migration. However, tests marked
with ``transaction=True`` truncate the database between runs (NOT
rollback), wiping the seed rows. On the next session, Django
fast-paths through the migration setup if the schema is already in
place — so the seed data does not get re-applied.

This override re-runs the idempotent seed function explicitly so
the seed state is guaranteed at the start of every session,
regardless of what previous transactional tests did to the DB.

### Function `_reset_audit_buffer`

Clear the in-memory audit buffer before AND after every test.

The M1 audit stub stashes emitted events in a thread-local list so
tests can assert emission. Without this autouse, events leak
across tests and assertions like ``len(events) == 1`` see stale
rows from earlier tests.

Originally defined as an autouse in ``apps/platform/audit/conftest.py``
where it only fired for tests under that app. Promoted to the
project-wide conftest in M1 D4 so the new accounts/auth_portal
test suites also benefit.

### Function `user_factory`

Factory for canonical Users with a configurable EmailAddress row.

Returns a callable ``make_user(*, email, password=None,
verified=True, is_staff=False)`` that creates a User and the
associated allauth EmailAddress (verified by default).

Depends on ``db`` so tests using this fixture automatically get
pytest-django's per-test transaction isolation. The session-scoped
seed is untouched.

### Function `user_unverified`

A user whose primary EmailAddress is NOT verified.

### Function `user_verified_no_mfa`

A verified user with no TOTP enrolled.

This is the state that triggers ``RequireMfaEnrollmentMiddleware``
to redirect to ``/accounts/2fa/totp/activate/``.

### Function `totp_secret`

The shared TOTP secret used by fixture-built authenticators.

### Function `user_with_totp`

A verified user with a TOTP Authenticator row already installed.

Bypasses allauth's enrollment view; appropriate for tests asserting
post-enrollment behavior (template rendering, middleware
pass-through). The end-to-end MFA test uses the real enrollment
flow to exercise allauth's view itself.

### Function `user_with_totp_and_recovery`

A verified user with TOTP + a recovery-codes Authenticator row.

Recovery codes here are seeded raw for template-rendering smoke
purposes. Tests that need allauth-wrapper-readable codes
(single-use enforcement) use the real generate view.

## `scripts/check_service_layer_discipline.py`

### Module docstring

A.4.5 — Service-layer discipline AST static check.

Walks ``backend/apps/**/*.py`` and warns on patterns the guide
prohibits outside the service layer:

* ``Model.objects.create(...)`` outside ``apps/*/services/``,
  ``apps/**/admin*.py``, ``apps/**/migrations/``, ``apps/**/tests/``,
  and ``apps/**/management/commands/`` (CLI seed/admin tools).
* ``.save()`` and ``.delete()`` outside ``apps/*/services/``.
* ``Manager.update(...)`` on a queryset outside ``apps/*/services/``.
* ``transaction.atomic()`` opened outside ``apps/*/services/`` (warning).
* ``request.user`` referenced inside ``apps/*/services/``.
* ``GenericForeignKey`` declared anywhere.
* ``forms.ModelChoiceField`` not nested under ``TenantModelChoiceField``
  (narrow heuristic — flag any direct ``forms.ModelChoiceField(...)``
  call in ``apps/**/forms.py``).

The script is ADVISORY in M0 — it reports findings and exits 0. Per
A.4.5 the check becomes blocking from M2.

Output format: ``<path>:<line>: WARN[<rule>] <message>``

Exit codes:
    0  Always (M0). The script is non-blocking.

### Function `is_service_path`

True if the file lives under any ``apps/*/services/`` tree.

### Function `is_admin_path`

True if the file is an admin module or under an admin subtree.

### Function `is_management_command_path`

True if the file lives under any ``management/commands/`` directory.

Django management commands are dev-/admin-tier CLI tools and are
explicitly exempt from the service-layer write rules along with
admin/migrations/tests.

### Class `_ServiceDisciplineVisitor`

Walk a module's AST and collect rule violations.

### Function `_attr_chain`

Flatten an attribute access into a list of names.

``Quote.objects.create`` → ``["Quote", "objects", "create"]``

## `scripts/check_user_model_baseline.py`

### Module docstring

A.4.5 — Service-layer discipline AST static check.

Walks ``backend/apps/**/*.py`` and warns on patterns the guide
prohibits outside the service layer:

* ``Model.objects.create(...)`` outside ``apps/*/services/``,
  ``apps/**/admin*.py``, ``apps/**/migrations/``, and ``apps/**/tests/``.
* ``.save()`` and ``.delete()`` outside ``apps/*/services/``.
* ``Manager.update(...)`` on a queryset outside ``apps/*/services/``.
* ``transaction.atomic()`` opened outside ``apps/*/services/`` (warning).
* ``request.user`` referenced inside ``apps/*/services/``.
* ``GenericForeignKey`` declared anywhere.
* ``forms.ModelChoiceField`` not nested under ``TenantModelChoiceField``
  (narrow heuristic — flag any direct ``forms.ModelChoiceField(...)``
  call in ``apps/**/forms.py``).

The script is ADVISORY in M0 — it reports findings and exits 0. Per
A.4.5 the check becomes blocking from M2.

Output format: ``<path>:<line>: WARN[<rule>] <message>``

### Function `is_service_path`

True if the file lives under any ``apps/*/services/`` tree.

### Function `is_admin_path`

True if the file is an admin module or under an admin subtree.

### Class `_ServiceDisciplineVisitor`

Walk a module's AST and collect rule violations.

### Function `_attr_chain`

Flatten an attribute access into a list of names.

``Quote.objects.create`` → ``["Quote", "objects", "create"]``

## `scripts/dev-create_github_roadmap.py`

### Module docstring

Create/update GitHub milestones and exit-criteria tracking issues from docs/guide.md.

Usage from repo root:

    python scripts/create_github_roadmap.py --guide docs/guide.md --dry-run

Apply changes:

    python scripts/create_github_roadmap.py --guide docs/guide.md --apply

Optionally also create story issues from each milestone's Scope table:

    python scripts/create_github_roadmap.py --guide docs/guide.md --apply --stories

Requirements:
    - GitHub CLI installed: https://cli.github.com/
    - Authenticated: gh auth login
    - Run from inside the GitHub repository, or pass --repo OWNER/REPO

## `scripts/export_models_reference.py`

### Function `heading_for_models_file`

Example:
backend/apps/platform/accounts/models.py

Becomes:
## apps / platform / accounts
