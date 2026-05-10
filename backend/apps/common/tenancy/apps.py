"""Row-level tenancy primitives.

Phase 1: app skeleton only — concrete TenantOwnedModel, TenantManager,
and tenant context land in M1 (B.1.3, B.1.4).
"""

default_app_config = "apps.common.tenancy.apps.TenancyConfig"
