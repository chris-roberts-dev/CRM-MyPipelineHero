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

BASE_DIR: Path = Path(__file__).resolve().parent.parent.parent
REPO_ROOT: Path = BASE_DIR.parent
FRONTEND_DIST: Path = REPO_ROOT / "frontend" / "dist"


def env(name: str, default: str | None = None) -> str:
    value = os.environ.get(name)
    if value is None or value == "":
        if default is None:
            return ""
        return default
    return value


def env_bool(name: str, default: bool = False) -> bool:
    raw = os.environ.get(name)
    if raw is None or raw == "":
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def env_list(name: str, default: list[str] | None = None, sep: str = ",") -> list[str]:
    raw = os.environ.get(name)
    if raw is None or raw == "":
        return list(default or [])
    return [item.strip() for item in raw.split(sep) if item.strip()]


SECRET_KEY: str = env(
    "DJANGO_SECRET_KEY",
    "django-insecure-replace-me-in-every-non-dev-environment",
)
DEBUG: bool = env_bool("DJANGO_DEBUG", default=False)
ALLOWED_HOSTS: list[str] = env_list(
    "DJANGO_ALLOWED_HOSTS",
    default=["localhost", "127.0.0.1"],
)

MPH_ROOT_DOMAIN: str = env("MPH_ROOT_DOMAIN", "mph.local")
MPH_TENANT_DOMAIN_TEMPLATE: str = env("MPH_TENANT_DOMAIN_TEMPLATE", "{slug}.mph.local")

# Audit recording (G.5.3 M1 stub).
# When True, the audit_emit stub appends events to an in-memory buffer
# so tests can assert emission. Default False (production-safe);
# dev/test settings opt in.
MPH_AUDIT_RECORDING: bool = env_bool("MPH_AUDIT_RECORDING", default=False)


DJANGO_APPS: list[str] = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.sites",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.admin",
]

THIRD_PARTY_APPS: list[str] = [
    "allauth",
    "allauth.account",
    "allauth.socialaccount",
    "allauth.socialaccount.providers.openid_connect",
    "allauth.mfa",
    "django_vite",
]

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

OPERATIONS_APPS: list[str] = [
    "apps.operations.locations",
]

INSTALLED_APPS: list[str] = (
    DJANGO_APPS
    + THIRD_PARTY_APPS
    + PLATFORM_APPS
    + OPERATIONS_APPS
    + WEB_APPS
    + COMMON_APPS
)


MIDDLEWARE: list[str] = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "allauth.account.middleware.AccountMiddleware",
    "apps.platform.accounts.middleware.RequireMfaEnrollmentMiddleware",
]


ROOT_URLCONF: str = "config.urls"
WSGI_APPLICATION: str = "config.wsgi.application"
ASGI_APPLICATION: str = "config.asgi.application"


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


def _database_from_url(url: str) -> dict[str, Any]:
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
# Authentication — django-allauth (B.3.2, B.4, B.5) + allauth.mfa (B.4.8/9, B.5.7-9)
# ---------------------------------------------------------------------------

AUTH_USER_MODEL: str = "platform_accounts.User"

AUTHENTICATION_BACKENDS: list[str] = [
    "django.contrib.auth.backends.ModelBackend",
    "allauth.account.auth_backends.AuthenticationBackend",
]

SITE_ID: int = 1

# B.5.2 password policy — Argon2 first, then Django defaults.
PASSWORD_HASHERS: list[str] = [
    "django.contrib.auth.hashers.Argon2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher",
    "django.contrib.auth.hashers.BCryptSHA256PasswordHasher",
    "django.contrib.auth.hashers.ScryptPasswordHasher",
]

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

# ----- allauth account-app settings -----
# B.4: email is the username; verification is mandatory; sessions get fixation
# protection.
ACCOUNT_LOGIN_METHODS: set[str] = {"email"}
ACCOUNT_SIGNUP_FIELDS: list[str] = ["email*", "password1*", "password2*"]
ACCOUNT_EMAIL_VERIFICATION: str = "mandatory"
ACCOUNT_UNIQUE_EMAIL: bool = True
# Custom user-display callable. Our User model has no `username` field
# (B.3.3 — email-only identity). Allauth's default
# `default_user_display` reads `user.username` and crashes; this hook
# routes the lookup to `user.email` instead. Used by every
# `{% user_display %}` template tag and by allauth's internal
# formatting code paths.
ACCOUNT_USER_DISPLAY: str = "apps.platform.accounts.user_display.user_display"

ACCOUNT_LOGOUT_ON_PASSWORD_CHANGE: bool = True
ACCOUNT_PRESERVE_USERNAME_CASING: bool = False
ACCOUNT_SESSION_REMEMBER: bool = False
ACCOUNT_EMAIL_CONFIRMATION_EXPIRE_DAYS: int = 3
# B.4 requires explicit logout — disable allauth's GET-logout shortcut so
# logout is POST-only and CSRF-protected.
ACCOUNT_LOGOUT_ON_GET: bool = False
# Show distinct user-facing copy for a known-but-unverified email vs. a
# successful login; per H.3.4 the *invalid credentials* message stays
# generic, but verification status drives MFA-enrollment routing.
ACCOUNT_LOGIN_BY_CODE_ENABLED: bool = False
# B.5.10 rate limits — allauth vocabulary maps to (action, limit, window).
# Reproduces the table where possible; full per-IP+per-email split needs
# django-ratelimit later.
ACCOUNT_RATE_LIMITS: dict[str, Any] = {
    "login": "5/m,20/h",  # POST /accounts/login/
    "login_failed": "5/m",
    "signup": "20/h",
    "send_email": "5/m",
    "change_email": "5/h",
    "manage_email": "10/m",
    "reset_password": "3/h",
    "reset_password_email": "3/h",
    "reset_password_from_key": "5/m",
    "confirm_email": "10/m",
}

# ----- allauth.mfa settings (B.4.8, B.5.7-9) -----
# v1 supported methods: TOTP + recovery codes. WebAuthn/passkeys/SMS deferred.
MFA_SUPPORTED_TYPES: list[str] = ["totp", "recovery_codes"]
MFA_TOTP_ISSUER: str = env("MFA_TOTP_ISSUER", "MyPipelineHero")
MFA_TOTP_PERIOD: int = 30
MFA_TOTP_DIGITS: int = 6
MFA_TOTP_TOLERANCE: int = 1  # accept current + 1 prior 30-sec window
MFA_RECOVERY_CODE_COUNT: int = 10  # B.5.9
MFA_RECOVERY_CODE_DIGITS: int = 8
MFA_FORMS: dict[str, str] = {
    # Allauth defaults are fine; listing them here makes overrides cheap later.
    "authenticate": "allauth.mfa.base.forms.AuthenticateForm",
    "reauthenticate": "allauth.mfa.base.forms.AuthenticateForm",
    "activate_totp": "allauth.mfa.totp.forms.ActivateTOTPForm",
    "deactivate_totp": "allauth.mfa.totp.forms.DeactivateTOTPForm",
    "generate_recovery_codes": "allauth.mfa.recovery_codes.forms.GenerateRecoveryCodesForm",
}

# B.4.9: enrollment is required for local-password users. Make MFA setup
# the post-login destination when missing.
MFA_PASSKEY_LOGIN_ENABLED: bool = False
# B.4.10: TOTP-only sensitive-action re-auth (H.4.6); never re-prompts password.
ACCOUNT_REAUTHENTICATION_REQUIRED: bool = True
ACCOUNT_REAUTHENTICATION_TIMEOUT: int = 5 * 60  # 5 minutes — the strict B.4.10 window

# Login/logout URL shape. The auth_portal `/login/` route remains a 302
# to allauth's canonical URL so historical links keep working.
LOGIN_URL: str = "/accounts/login/"
LOGIN_REDIRECT_URL: str = "/select-org/"
LOGOUT_REDIRECT_URL: str = "/"

LANGUAGE_CODE: str = env("LANGUAGE_CODE", "en-us")
TIME_ZONE: str = env("TIME_ZONE", "America/Chicago")
USE_I18N: bool = True
USE_TZ: bool = True


STATIC_URL: str = "/static/"
STATIC_ROOT: Path = BASE_DIR / "staticfiles"

STATICFILES_DIRS: list[Path] = [BASE_DIR / "static"]
if FRONTEND_DIST.is_dir():
    STATICFILES_DIRS.append(FRONTEND_DIST)

MEDIA_URL: str = "/media/"
MEDIA_ROOT: Path = BASE_DIR / "media"

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


EMAIL_BACKEND: str = env("EMAIL_BACKEND", "django.core.mail.backends.smtp.EmailBackend")
EMAIL_HOST: str = env("EMAIL_HOST", "mailpit")
EMAIL_PORT: int = int(env("EMAIL_PORT", "1025"))
EMAIL_HOST_USER: str = env("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD: str = env("EMAIL_HOST_PASSWORD", "")
EMAIL_USE_TLS: bool = env_bool("EMAIL_USE_TLS", default=False)
DEFAULT_FROM_EMAIL: str = env("DEFAULT_FROM_EMAIL", "noreply@mph.local")
SERVER_EMAIL: str = DEFAULT_FROM_EMAIL


CELERY_BROKER_URL: str = env("CELERY_BROKER_URL", "redis://redis:6379/1")
CELERY_RESULT_BACKEND: str = env("CELERY_RESULT_BACKEND", "redis://redis:6379/2")
CELERY_TIMEZONE: str = TIME_ZONE
CELERY_ENABLE_UTC: bool = True
CELERY_TASK_DEFAULT_QUEUE: str = "default"

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


CACHES: dict[str, dict[str, Any]] = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": env("REDIS_URL", "redis://redis:6379/0"),
    }
}


SESSION_ENGINE: str = "django.contrib.sessions.backends.db"
SESSION_COOKIE_NAME: str = "mph_sessionid"
SESSION_COOKIE_HTTPONLY: bool = True
SESSION_COOKIE_SAMESITE: str = "Lax"
SESSION_COOKIE_SECURE: bool = False

CSRF_COOKIE_NAME: str = "mph_csrftoken"
CSRF_COOKIE_HTTPONLY: bool = False
CSRF_COOKIE_SAMESITE: str = "Lax"
CSRF_COOKIE_SECURE: bool = False
CSRF_TRUSTED_ORIGINS: list[str] = []

SECURE_BROWSER_XSS_FILTER: bool = True
SECURE_CONTENT_TYPE_NOSNIFF: bool = True
X_FRAME_OPTIONS: str = "DENY"


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
