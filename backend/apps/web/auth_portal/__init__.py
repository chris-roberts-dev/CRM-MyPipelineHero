"""Root-domain authentication portal (H.3).

In M0 this app exposes a minimal scaffold for ``/login/`` so that the
landing page's sign-in CTA renders the correct page. The full login,
MFA, OAuth/OIDC, password-reset, invite-acceptance, and org-picker
flows wire up in M1 against django-allauth (B.3.2, B.4).
"""

default_app_config = "apps.web.auth_portal.apps.AuthPortalConfig"
