"""Local development settings.

Loads ``.env`` via plain os.environ — Docker Compose injects them.
"""

from __future__ import annotations

from .base import *  # noqa: F401,F403
from .base import BASE_DIR, MIDDLEWARE, env, env_bool

DEBUG: bool = env_bool("DJANGO_DEBUG", default=True)

# Trust the local Nginx hostnames as well as the bare web container.
ALLOWED_HOSTS: list[str] = [
    "mph.local",
    ".mph.local",  # leading dot allows wildcard tenant subdomains in M1
    "localhost",
    "127.0.0.1",
    "web",
    "0.0.0.0",  # noqa: S104 — local dev only
]

CSRF_TRUSTED_ORIGINS: list[str] = [
    "http://mph.local",
    "http://*.mph.local",
    "http://localhost",
    "http://localhost:8000",
]

INTERNAL_IPS: list[str] = ["127.0.0.1"]

# Use the database session backend so dev sessions survive container restarts.
# (Switch to signed_cookies if you want fully stateless dev sessions.)

# Console email is sometimes more convenient than Mailpit; flip via env.
if env("EMAIL_BACKEND", ""):
    EMAIL_BACKEND = env("EMAIL_BACKEND")
else:
    # Default in dev: use Mailpit via the SMTP backend already set in base.py
    pass

# Plain-text logs are nicer in a dev terminal.
import os as _os  # noqa: E402

_os.environ.setdefault("LOG_FORMAT", "plain")
