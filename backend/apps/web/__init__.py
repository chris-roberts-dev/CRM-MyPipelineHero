"""Server-rendered web surfaces.

Three sub-apps:

* ``apps.web.landing``       Custom root-domain landing page (H.3.3, H.8).
* ``apps.web.auth_portal``   Login, MFA, invite, password-reset, org picker.
* ``apps.web.tenant_portal`` Tenant-facing Django-template UI for Phase 1.
"""
