"""Test settings — used by pytest and CI.

Designed to be fast, deterministic, and offline. No network services
beyond the local DB are required to run the suite.

See ``dev.py`` for a note on why per-environment overrides use bare
assignment instead of fresh type annotations.
"""

from __future__ import annotations

from config.settings.base import *  # star-import: F403/F405 suppressed in pyproject.toml

DEBUG = False

SECRET_KEY = "test-secret-key-not-used-in-any-deployed-environment"

ALLOWED_HOSTS = ["*"]

MPH_AUDIT_RECORDING = True

DJANGO_VITE = {
    **DJANGO_VITE,
    "default": {
        **DJANGO_VITE["default"],
        "dev_mode": True,
    },
}

# Faster password hashing in the test suite. MD5 is acceptable here
# because the test DB is throwaway and isolated.
PASSWORD_HASHERS: list[str] = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]

# In-memory email backend so tests don't depend on Mailpit.
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"

# Local-memory cache so tests don't depend on Redis when run outside Compose.
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "mph-test",
    }
}

# Run Celery tasks synchronously in tests (no broker required).
CELERY_TASK_ALWAYS_EAGER: bool = True
CELERY_TASK_EAGER_PROPAGATES: bool = True

# DATABASE_URL is honored; CI sets it to point at the CI Postgres service.
# Locally, ``make test`` runs against the dev Postgres which is fine.

# Reduce log noise during pytest runs.
import logging as _logging  # noqa: E402

_logging.disable(_logging.CRITICAL)
