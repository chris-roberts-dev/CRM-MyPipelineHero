"""Custom root-domain landing page (H.3.3).

Permanently server-rendered (A.4.3, H.8.5). Owns the templates under
``templates/landing/`` and the public CSS under ``static/landing/css/``.
"""

default_app_config = "apps.web.landing.apps.LandingConfig"
