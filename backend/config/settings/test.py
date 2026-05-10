"""Test settings — used by pytest and CI.

Designed to be fast, deterministic, and offline. No network services
beyond the local DB are required to run the suite.
"""

from __future__ import annotations

from .base import *  # noqa: F401,F403
from .base import env

DEBUG: bool = False

SECRET_KEY: str = "test-secret-key-not-used-in-any-deployed-environment"  # noqa: S105

ALLOWED_HOSTS: list[str] = ["*"]

# Faster password hashing in the test suite. SHA1 is acceptable here
# because the test DB is throwaway and isolated.
PASSWORD_HASHERS: list[str] = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]

# In-memory email backend so tests don't depend on Mailpit.
EMAIL_BACKEND: str = "django.core.mail.backends.locmem.EmailBackend"

# Local-memory cache so tests don't depend on Redis when run outside Compose.
CACHES: dict = {
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
