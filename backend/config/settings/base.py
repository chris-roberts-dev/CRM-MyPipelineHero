"""Shared Django settings for MyPipelineHero.

Authoritative reference: `docs/guide.md` parts A, B, G, H, I.

This module sets defaults and shape. Per-environment modules
(``dev``, ``test``, ``staging``, ``demo``, ``prod``) extend it and
override what they need.

Secrets and environment-specific values come from environment variables.
We never commit a real ``.env`` and never log secrets.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from kombu import Queue

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

# BASE_DIR points at backend/ — the directory containing manage.py.
BASE_DIR: Path = Path(__file__).resolve().parent.parent.parent

# REPO_ROOT points at the repository root (one above backend/).
# Used for django-vite frontend manifest discovery.
REPO_ROOT: Path = BASE_DIR.parent

# Vite-produced asset directory (manifest + bundles). Populated by
# `npm run build` inside the frontend container. Absent during fresh
# local-dev runs; STATICFILES_DIRS conditionally includes it below.
FRONTEND_DIST: Path = REPO_ROOT / "frontend" / "dist"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def env(name: str, default: str | None = None) -> str:
    """Read an environment variable, falling back to ``default`` if unset."""
    value = os.environ.get(name)
    if value is None or value == "":
        if default is None:
            return ""
        return default
    return value


def env_bool(name: str, default: bool = False) -> bool:
    """Parse a boolean env var. Accepts: 1/0, true/false, yes/no, on/off."""
    raw = os.environ.get(name)
    if raw is None or raw == "":
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def env_list(name: str, default: list[str] | None = None, sep: str = ",") -> list[str]:
    """Parse a separator-delimited env var into a list of stripped strings."""
    raw = os.environ.get(name)
    if raw is None or raw == "":
        return list(default or [])
    return [item.strip() for item in raw.split(sep) if item.strip()]


# ---------------------------------------------------------------------------
# Core
# ---------------------------------------------------------------------------

SECRET_KEY: str = env(
    "DJANGO_SECRET_KEY",
    "django-insecure-replace-me-in-every-non-dev-environment",
)
DEBUG: bool = env_bool("DJANGO_DEBUG", default=False)
ALLOWED_HOSTS: list[str] = env_list(
    "DJANGO_ALLOWED_HOSTS",
    default=["localhost", "127.0.0.1"],
)

# Domain configuration (referenced from M1 onward for tenant subdomain routing)
MPH_ROOT_DOMAIN: str = env("MPH_ROOT_DOMAIN", "mph.local")
MPH_TENANT_DOMAIN_TEMPLATE: str = env("MPH_TENANT_DOMAIN_TEMPLATE", "{slug}.mph.local")


# ---------------------------------------------------------------------------
# Applications
# ---------------------------------------------------------------------------

DJANGO_APPS: list[str] = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.sites",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.admin",  # dev-only mount; see config/urls.py
]

# django-allauth is the authentication boundary (B.3.2). It is installed
# from M0 so M1 can wire login/MFA/OAuth/OIDC without a separate plumbing pass.
# django-vite is installed from M0 D3 for compiled frontend assets (H.1.2).
THIRD_PARTY_APPS: list[str] = [
    "allauth",
    "allauth.account",
    "allauth.socialaccount",
    "allauth.socialaccount.providers.openid_connect",
    "allauth.mfa",
    "django_vite",
]

# Order matters: platform.accounts MUST be first because it owns the
# custom User model referenced by AUTH_USER_MODEL (B.3.1, I.6.7).
PLATFORM_APPS: list[str] = [
    "apps.platform.accounts",
    "apps.platform.organizations",
    "apps.platform.rbac",
    "apps.platform.audit",
    "apps.platform.support",
]

WEB_APPS: list[str] = [
    "apps.web.landing",
    "apps.web.auth_portal",
    "apps.web.tenant_portal",
]

COMMON_APPS: list[str] = [
    "apps.common.tenancy",
    "apps.common.outbox",
]

INSTALLED_APPS: list[str] = (
    DJANGO_APPS + THIRD_PARTY_APPS + PLATFORM_APPS + WEB_APPS + COMMON_APPS
)


# ---------------------------------------------------------------------------
# Middleware
# ---------------------------------------------------------------------------

MIDDLEWARE: list[str] = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "allauth.account.middleware.AccountMiddleware",
]


# ---------------------------------------------------------------------------
# URL / WSGI / ASGI
# ---------------------------------------------------------------------------

ROOT_URLCONF: str = "config.urls"
WSGI_APPLICATION: str = "config.wsgi.application"
ASGI_APPLICATION: str = "config.asgi.application"


# ---------------------------------------------------------------------------
# Templates
# ---------------------------------------------------------------------------

TEMPLATES: list[dict[str, Any]] = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]


# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------


def _database_from_url(url: str) -> dict[str, Any]:
    """Parse a ``postgres://user:pass@host:port/db`` URL into Django config."""
    from urllib.parse import unquote, urlparse

    parsed = urlparse(url)
    if parsed.scheme not in {"postgres", "postgresql"}:
        raise ValueError(
            f"Only postgres/postgresql DATABASE_URL schemes are supported, got: {parsed.scheme!r}"
        )
    return {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": (parsed.path or "/").lstrip("/"),
        "USER": unquote(parsed.username) if parsed.username else "",
        "PASSWORD": unquote(parsed.password) if parsed.password else "",
        "HOST": parsed.hostname or "",
        "PORT": str(parsed.port or ""),
        "CONN_MAX_AGE": 60,
        "ATOMIC_REQUESTS": False,
    }


DATABASES: dict[str, Any] = {
    "default": _database_from_url(
        env("DATABASE_URL", "postgres://mph:mph@postgres:5432/mph")
    ),
}

DEFAULT_AUTO_FIELD: str = "django.db.models.BigAutoField"


# ---------------------------------------------------------------------------
# Authentication
# ---------------------------------------------------------------------------

AUTH_USER_MODEL: str = "platform_accounts.User"

AUTHENTICATION_BACKENDS: list[str] = [
    "django.contrib.auth.backends.ModelBackend",
    "allauth.account.auth_backends.AuthenticationBackend",
]

SITE_ID: int = 1
ACCOUNT_LOGIN_METHODS: set[str] = {"email"}
ACCOUNT_SIGNUP_FIELDS: list[str] = ["email*", "password1*", "password2*"]
ACCOUNT_EMAIL_VERIFICATION: str = "mandatory"
ACCOUNT_UNIQUE_EMAIL: bool = True

LOGIN_URL: str = "/login/"
LOGIN_REDIRECT_URL: str = "/select-org/"
LOGOUT_REDIRECT_URL: str = "/"


# ---------------------------------------------------------------------------
# Password validation
# ---------------------------------------------------------------------------

AUTH_PASSWORD_VALIDATORS: list[dict[str, Any]] = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {"min_length": 12},
    },
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]


# ---------------------------------------------------------------------------
# Internationalization
# ---------------------------------------------------------------------------

LANGUAGE_CODE: str = env("LANGUAGE_CODE", "en-us")
TIME_ZONE: str = env("TIME_ZONE", "America/Chicago")
USE_I18N: bool = True
USE_TZ: bool = True


# ---------------------------------------------------------------------------
# Static files + django-vite (H.1.2)
# ---------------------------------------------------------------------------

STATIC_URL: str = "/static/"
STATIC_ROOT: Path = BASE_DIR / "staticfiles"

# The frontend/dist directory exists only after `npm run build` produces
# a manifest. In dev mode django-vite serves assets through the Vite
# dev server (see DJANGO_VITE below) so the manifest is not required to
# load pages. We add `frontend/dist` to STATICFILES_DIRS only when it
# exists to avoid Django's "static directory does not exist" warning.
STATICFILES_DIRS: list[Path] = [BASE_DIR / "static"]
if FRONTEND_DIST.is_dir():
    STATICFILES_DIRS.append(FRONTEND_DIST)

MEDIA_URL: str = "/media/"
MEDIA_ROOT: Path = BASE_DIR / "media"

# django-vite: route bundle requests to the Vite dev server when DEBUG
# is on, and read from the built manifest in production.
#
# In dev, the browser fetches /vite/<asset> through Nginx, which proxies
# to the Vite container at vite:5173. The dev server host/port point at
# Nginx so the browser stays on one origin.
DJANGO_VITE: dict[str, dict[str, Any]] = {
    "default": {
        "dev_mode": DEBUG,
        "dev_server_protocol": "http",
        "dev_server_host": "mph.local",
        "dev_server_port": 80,
        "static_url_prefix": "vite",
        "manifest_path": FRONTEND_DIST / ".vite" / "manifest.json",
    }
}


# ---------------------------------------------------------------------------
# Email
# ---------------------------------------------------------------------------

EMAIL_BACKEND: str = env("EMAIL_BACKEND", "django.core.mail.backends.smtp.EmailBackend")
EMAIL_HOST: str = env("EMAIL_HOST", "mailpit")
EMAIL_PORT: int = int(env("EMAIL_PORT", "1025"))
EMAIL_HOST_USER: str = env("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD: str = env("EMAIL_HOST_PASSWORD", "")
EMAIL_USE_TLS: bool = env_bool("EMAIL_USE_TLS", default=False)
DEFAULT_FROM_EMAIL: str = env("DEFAULT_FROM_EMAIL", "noreply@mph.local")
SERVER_EMAIL: str = DEFAULT_FROM_EMAIL


# ---------------------------------------------------------------------------
# Celery
# ---------------------------------------------------------------------------

CELERY_BROKER_URL: str = env("CELERY_BROKER_URL", "redis://redis:6379/1")
CELERY_RESULT_BACKEND: str = env("CELERY_RESULT_BACKEND", "redis://redis:6379/2")
CELERY_TIMEZONE: str = TIME_ZONE
CELERY_ENABLE_UTC: bool = True
CELERY_TASK_DEFAULT_QUEUE: str = "default"

# Logical queue separation per A.3.2.
#
# Celery expects ``task_queues`` to be a sequence of ``kombu.Queue`` instances,
# not strings. We declare each queue with its name and routing key explicitly.
# Workers select which queues to consume via the ``-Q`` flag on the command
# line (see backend/compose.yaml worker service).
CELERY_TASK_QUEUES: tuple[Queue, ...] = (
    Queue("critical", routing_key="critical"),
    Queue("default", routing_key="default"),
    Queue("bulk", routing_key="bulk"),
    Queue("reports", routing_key="reports"),
)

CELERY_TASK_ACKS_LATE: bool = True
CELERY_TASK_REJECT_ON_WORKER_LOST: bool = True
CELERY_WORKER_PREFETCH_MULTIPLIER: int = 1
CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP: bool = True


# ---------------------------------------------------------------------------
# Caching
# ---------------------------------------------------------------------------

CACHES: dict[str, dict[str, Any]] = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": env("REDIS_URL", "redis://redis:6379/0"),
    }
}


# ---------------------------------------------------------------------------
# Sessions / CSRF / Security
# ---------------------------------------------------------------------------

SESSION_ENGINE: str = "django.contrib.sessions.backends.db"
SESSION_COOKIE_NAME: str = "mph_sessionid"
SESSION_COOKIE_HTTPONLY: bool = True
SESSION_COOKIE_SAMESITE: str = "Lax"
SESSION_COOKIE_SECURE: bool = False

CSRF_COOKIE_NAME: str = "mph_csrftoken"
CSRF_COOKIE_HTTPONLY: bool = False  # HTMX reads the value via JS (H.1.6)
CSRF_COOKIE_SAMESITE: str = "Lax"
CSRF_COOKIE_SECURE: bool = False
CSRF_TRUSTED_ORIGINS: list[str] = []

SECURE_BROWSER_XSS_FILTER: bool = True
SECURE_CONTENT_TYPE_NOSNIFF: bool = True
X_FRAME_OPTIONS: str = "DENY"


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

LOG_LEVEL: str = env("LOG_LEVEL", "INFO")

LOGGING: dict[str, Any] = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "json": {
            "format": (
                '{"ts":"%(asctime)s","level":"%(levelname)s",'
                '"logger":"%(name)s","msg":"%(message)s"}'
            ),
        },
        "plain": {
            "format": "%(asctime)s %(levelname)s %(name)s %(message)s",
        },
    },
    "handlers": {
        "stdout": {
            "class": "logging.StreamHandler",
            "formatter": "json" if env("LOG_FORMAT", "json") == "json" else "plain",
        },
    },
    "root": {"handlers": ["stdout"], "level": LOG_LEVEL},
    "loggers": {
        "django": {"handlers": ["stdout"], "level": LOG_LEVEL, "propagate": False},
        "django.request": {
            "handlers": ["stdout"],
            "level": "WARNING",
            "propagate": False,
        },
        "celery": {"handlers": ["stdout"], "level": LOG_LEVEL, "propagate": False},
    },
}
