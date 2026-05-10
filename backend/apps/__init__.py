"""Top-level package for MyPipelineHero application code.

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
"""
