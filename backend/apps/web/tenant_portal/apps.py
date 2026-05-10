from __future__ import annotations

from django.apps import AppConfig


class TenantPortalConfig(AppConfig):
    name = "apps.web.tenant_portal"
    label = "web_tenant_portal"
    verbose_name = "Web · Tenant portal"
