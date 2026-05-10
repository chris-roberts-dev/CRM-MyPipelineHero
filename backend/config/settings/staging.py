"""Staging settings — production-like validation environment.

See ``dev.py`` for a note on why per-environment overrides use bare
assignment instead of fresh type annotations.
"""

from __future__ import annotations

from .base import *  # star-import: F403/F405 suppressed in pyproject.toml

DEBUG = False

# SECRET_KEY MUST be supplied via environment variable.
SECRET_KEY = env("DJANGO_SECRET_KEY")
if not SECRET_KEY:
    raise RuntimeError("DJANGO_SECRET_KEY must be set in staging")

ALLOWED_HOSTS = env_list("DJANGO_ALLOWED_HOSTS")
CSRF_TRUSTED_ORIGINS = env_list("DJANGO_CSRF_TRUSTED_ORIGINS")

# HTTPS-everything posture.
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_PROXY_SSL_HEADER: tuple[str, str] = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT: bool = True
SECURE_HSTS_SECONDS: int = 60 * 60 * 24 * 30  # 30 days
SECURE_HSTS_INCLUDE_SUBDOMAINS: bool = True
SECURE_HSTS_PRELOAD: bool = False

# JSON logs always in non-local environments.
import os as _os  # noqa: E402

_os.environ.setdefault("LOG_FORMAT", "json")
