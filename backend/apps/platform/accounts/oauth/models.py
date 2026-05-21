"""OAuthProviderConfig model (B.3.7).

Platform-managed configuration for an approved OAuth/OIDC provider.

**Secrets are NOT stored in this model.** The model holds the *env-var
key names* (``client_id_env_key``, ``client_secret_env_key``); the
loader reads ``os.environ.get(<key_name>)`` at runtime to obtain the
actual credentials. This keeps secrets out of database backups, the
audit trail, and admin pages — matching B.5.5 ("Client secret loaded
from approved secret source").

**Tenant-managed provider config is deferred** — B.3.7 makes this
explicit. The model is platform-tier; there is no ``organization``
FK.

**Field shape mirrors B.3.7 exactly**, with one M1 D5 extension:

* ``allow_self_registration: BOOL, default(False)`` — per-provider
  policy hook for B.4.6 step 4 ("create a global ``User`` only if
  platform policy allows external self-registration"). Default is
  invitation-only. Flagged in the M1 D5 retro as a deviation from
  B.3.7's exact field list.

**`scopes` and `allowed_email_domains` use Postgres ArrayField.**
The guide specifies TEXT[]; ArrayField is the Django equivalent.
``django.contrib.postgres`` is required in ``INSTALLED_APPS``.
"""

from __future__ import annotations

import uuid
from typing import Any, ClassVar

from django.contrib.postgres.fields import ArrayField
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.db import models
from django.utils.translation import gettext_lazy as _


def _new_provider_config_uuid() -> uuid.UUID:
    """UUID v7 (Python 3.14+) for the provider config primary key."""
    factory = getattr(uuid, "uuid7", uuid.uuid4)
    return factory()


# DNS-safe provider code: lowercase letters, digits, hyphens; 3-63 chars.
# Used in URLs and as the social-account provider id in allauth.
_PROVIDER_CODE_REGEX = r"^[a-z][a-z0-9-]{1,61}[a-z0-9]$"

# Env-var key shape: uppercase letters, digits, underscores.
# Standard POSIX env-var convention. Empty is forbidden; the field
# is required, but a CharField with blank=False enforces that at
# form level — this regex is the value-shape check.
_ENV_KEY_REGEX = r"^[A-Z_][A-Z0-9_]*$"


class ProviderType(models.TextChoices):
    """B.3.7: provider_type ENUM(OIDC, OAUTH2)."""

    OIDC = "OIDC", _("OpenID Connect")
    OAUTH2 = "OAUTH2", _("OAuth 2.0")


class OAuthProviderConfig(models.Model):
    """Platform-managed OAuth/OIDC provider configuration (B.3.7).

    Approval lifecycle (M1 D5 — informally enforced):

    1. Platform admin creates the row with ``is_active=False``.
    2. Security review confirms callback URL, provider MFA posture,
       allowed domains.
    3. Platform admin flips ``is_active=True``.

    The loader at startup only includes rows where ``is_active=True``
    in allauth's ``SOCIALACCOUNT_PROVIDERS`` config. An inactive row
    is invisible to login flows.
    """

    id = models.UUIDField(
        primary_key=True,
        default=_new_provider_config_uuid,
        editable=False,
    )

    # Stable provider identifier. Used in URLs (e.g.
    # ``/accounts/oidc/<provider_code>/login/``) and as the allauth
    # provider id. MUST be DNS-safe.
    provider_code = models.CharField(
        max_length=63,
        unique=True,
        validators=[
            RegexValidator(
                regex=_PROVIDER_CODE_REGEX,
                message=(
                    "provider_code must match "
                    f"{_PROVIDER_CODE_REGEX} "
                    "(DNS-safe, lowercase, 3-63 chars)."
                ),
            ),
        ],
        help_text=_(
            "Stable identifier used in URLs and as the allauth "
            "provider id. Example: 'google-workspace'."
        ),
    )

    display_name = models.CharField(
        max_length=255,
        help_text=_("Human-readable label shown on the login page button."),
    )

    provider_type = models.CharField(
        max_length=8,
        choices=ProviderType.choices,
        default=ProviderType.OIDC,
        help_text=_("OIDC is preferred (J.3.13). OAUTH2 is supported but rarer."),
    )

    # ---- OIDC discovery endpoints (per B.3.7) ----

    issuer_url = models.URLField(
        max_length=512,
        null=True,
        blank=True,
        help_text=_(
            "OIDC issuer URL. The well-known config at "
            "<issuer>/.well-known/openid-configuration drives the "
            "rest of the discovery flow. Required when "
            "provider_type=OIDC."
        ),
    )
    authorization_url = models.URLField(
        max_length=512,
        null=True,
        blank=True,
    )
    token_url = models.URLField(
        max_length=512,
        null=True,
        blank=True,
    )
    userinfo_url = models.URLField(
        max_length=512,
        null=True,
        blank=True,
    )
    jwks_url = models.URLField(
        max_length=512,
        null=True,
        blank=True,
        help_text=_("JWKS URL for ID token signature verification (OIDC)."),
    )

    # ---- Credentials (loaded from env at runtime) ----

    client_id_env_key = models.CharField(
        max_length=255,
        validators=[
            RegexValidator(
                regex=_ENV_KEY_REGEX,
                message=(
                    "client_id_env_key must be a POSIX env-var name "
                    "(uppercase letters, digits, underscores)."
                ),
            ),
        ],
        help_text=_(
            "Name of the env var holding the OAuth client ID. "
            "Example: 'OAUTH_GOOGLE_WORKSPACE_CLIENT_ID'. The value "
            "is read at startup; this column never stores the secret."
        ),
    )
    client_secret_env_key = models.CharField(
        max_length=255,
        validators=[
            RegexValidator(
                regex=_ENV_KEY_REGEX,
                message=("client_secret_env_key must be a POSIX env-var name."),
            ),
        ],
        help_text=_(
            "Name of the env var holding the OAuth client secret. "
            "B.5.5: secret MUST NOT live in source control or in the "
            "database. This field is audit-masked per G.5.5."
        ),
    )

    # ---- Behaviour flags (B.3.7 + M1 D5 extension) ----

    scopes = ArrayField(
        base_field=models.CharField(max_length=128),
        default=list,
        blank=True,
        help_text=_(
            "Requested OAuth scopes. ['openid', 'email', 'profile'] is "
            "a safe default for OIDC."
        ),
    )

    is_active = models.BooleanField(
        default=False,
        help_text=_(
            "If False, the provider is invisible to the login page and "
            "to the loader. Platform admins flip this to True only "
            "after security review."
        ),
    )

    require_verified_email = models.BooleanField(
        default=True,
        help_text=_(
            "If True (the default), the provider must report "
            "email_verified=true. Required by B.5.6 to prevent "
            "account-takeover via unverified-email linking."
        ),
    )

    trust_external_mfa = models.BooleanField(
        default=False,
        help_text=_(
            "If True, the provider's MFA is treated as satisfying "
            "login MFA (B.4.8). Requires explicit security review "
            "(B.5.5) before being enabled in production. Default is "
            "False — users will be forced through local TOTP enrollment."
        ),
    )

    allowed_email_domains = ArrayField(
        base_field=models.CharField(max_length=253),
        null=True,
        blank=True,
        help_text=_(
            "Optional list of email-domain suffixes (without the @). "
            "If set, only users whose verified email matches one of "
            "these domains may authenticate through this provider."
        ),
    )

    # M1 D5 extension to B.3.7:
    allow_self_registration = models.BooleanField(
        default=False,
        help_text=_(
            "Per-provider policy for B.4.6 step 4. If True, new users "
            "from this provider may be created on first login. If False "
            "(the default), an existing User row is required (e.g. via "
            "invitation). Tracked as a deviation from B.3.7 in the M1 "
            "D5 retro."
        ),
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("OAuth/OIDC provider config")
        verbose_name_plural = _("OAuth/OIDC provider configs")
        ordering: ClassVar[list[str]] = ["display_name", "provider_code"]

    def __str__(self) -> str:
        return f"{self.display_name} ({self.provider_code})"

    def clean(self) -> None:
        """Cross-field validation.

        Runs only via ModelForm / explicit ``full_clean()``. We do
        NOT enforce these as DB CHECK constraints because the rules
        are easier to reason about as Python — and B.3.7 doesn't
        require them at the DB level.
        """
        super().clean()
        errors: dict[str, Any] = {}

        # OIDC providers need at least the issuer URL.
        if self.provider_type == ProviderType.OIDC and not self.issuer_url:
            errors["issuer_url"] = _("issuer_url is required when provider_type=OIDC.")

        # OAUTH2 providers need explicit authorization/token URLs (no
        # discovery document).
        if self.provider_type == ProviderType.OAUTH2:
            if not self.authorization_url:
                errors["authorization_url"] = _(
                    "authorization_url is required when provider_type=OAUTH2."
                )
            if not self.token_url:
                errors["token_url"] = _(
                    "token_url is required when provider_type=OAUTH2."
                )

        # Trusted external MFA only makes sense when the provider's
        # claims include AMR/ACR. We don't have a way to validate that
        # here at config time, but require_verified_email being False
        # AND trust_external_mfa being True is almost certainly a
        # misconfiguration — the provider is asserting "we did MFA" but
        # the application is willing to accept "we didn't even verify
        # the email". Reject this combo.
        if self.trust_external_mfa and not self.require_verified_email:
            errors["trust_external_mfa"] = _(
                "trust_external_mfa requires require_verified_email=True. "
                "A provider that doesn't verify email is not trustworthy "
                "for MFA assertions."
            )

        if errors:
            raise ValidationError(errors)
