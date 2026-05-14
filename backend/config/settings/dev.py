"""Local development settings.

Loads ``.env`` via plain os.environ — Docker Compose injects them.

Note: S104 (binding to all interfaces) is suppressed for this file in
``pyproject.toml`` because the local Django web container intentionally
binds to ``0.0.0.0:8000`` so the host can reach it. Production settings
never get this exemption.

Note on annotations: per-environment overrides use bare assignment (no
``: bool``, ``: list[str]`` etc.) so that mypy treats them as rebinds of
the symbols already imported from ``.base`` rather than redefinitions.
This is the idiomatic Django pattern for layered settings under strict
type checking.
"""

from __future__ import annotations

from config.settings.base import *  # star-import: F403/F405 suppressed in pyproject.toml

MPH_AUDIT_RECORDING: bool = True

DEBUG = env_bool("DJANGO_DEBUG", default=True)

# Trust the local Nginx hostnames as well as the bare web container.
ALLOWED_HOSTS = [
    "mph.local",
    ".mph.local",  # leading dot allows wildcard tenant subdomains in M1
    "localhost",
    "127.0.0.1",
    "web",
    "0.0.0.0",
]

CSRF_TRUSTED_ORIGINS = [
    "http://mph.local",
    "http://*.mph.local",
    "http://localhost",
    "http://localhost:8000",
]

INTERNAL_IPS: list[str] = ["127.0.0.1"]

# Plain-text logs are nicer in a dev terminal.
import os as _os  # noqa: E402

_os.environ.setdefault("LOG_FORMAT", "plain")
