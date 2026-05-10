"""Platform console + support impersonation (B.7, H.7).

The ``/platform/`` URL mount lives here. M0 ships a minimal
authenticated landing page; impersonation, tenant search, and audit
review land in M1.
"""

default_app_config = "apps.platform.support.apps.SupportConfig"
