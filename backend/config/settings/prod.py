"""Production settings.

See ``dev.py`` for a note on why per-environment overrides use bare
assignment instead of fresh type annotations.
"""

from __future__ import annotations

from .base import *  # star-import: F403/F405 suppressed in pyproject.toml

DEBUG = False

SECRET_KEY = env("DJANGO_SECRET_KEY")
if not SECRET_KEY:
    raise RuntimeError("DJANGO_SECRET_KEY must be set in production")

ALLOWED_HOSTS = env_list("DJANGO_ALLOWED_HOSTS")
if not ALLOWED_HOSTS:
    raise RuntimeError("DJANGO_ALLOWED_HOSTS must be set in production")

CSRF_TRUSTED_ORIGINS = env_list("DJANGO_CSRF_TRUSTED_ORIGINS")

# HTTPS-everything posture.
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_PROXY_SSL_HEADER: tuple[str, str] = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT: bool = True
SECURE_HSTS_SECONDS: int = 60 * 60 * 24 * 365  # 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS: bool = True
SECURE_HSTS_PRELOAD: bool = True

import os as _os  # noqa: E402

_os.environ.setdefault("LOG_FORMAT", "json")
