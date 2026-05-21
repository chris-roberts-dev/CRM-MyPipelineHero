"""Add OAuthProviderConfig model (M1 D5, B.3.7).

Platform-managed OAuth/OIDC provider configuration. Secrets are NOT
stored in this table — only the env-var key NAMES that the loader
reads at runtime.
"""

from __future__ import annotations

import django.contrib.postgres.fields
import django.core.validators
from django.db import migrations, models

import apps.platform.accounts.oauth.models


class Migration(migrations.Migration):

    dependencies = [
        ("platform_accounts", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="OAuthProviderConfig",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=apps.platform.accounts.oauth.models._new_provider_config_uuid,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                (
                    "provider_code",
                    models.CharField(
                        help_text=(
                            "Stable identifier used in URLs and as the "
                            "allauth provider id. Example: 'google-workspace'."
                        ),
                        max_length=63,
                        unique=True,
                        validators=[
                            django.core.validators.RegexValidator(
                                message=(
                                    "provider_code must match "
                                    "^[a-z][a-z0-9-]{1,61}[a-z0-9]$ "
                                    "(DNS-safe, lowercase, 3-63 chars)."
                                ),
                                regex="^[a-z][a-z0-9-]{1,61}[a-z0-9]$",
                            ),
                        ],
                    ),
                ),
                (
                    "display_name",
                    models.CharField(
                        help_text=(
                            "Human-readable label shown on the login page button."
                        ),
                        max_length=255,
                    ),
                ),
                (
                    "provider_type",
                    models.CharField(
                        choices=[
                            ("OIDC", "OpenID Connect"),
                            ("OAUTH2", "OAuth 2.0"),
                        ],
                        default="OIDC",
                        help_text=(
                            "OIDC is preferred (J.3.13). OAUTH2 is "
                            "supported but rarer."
                        ),
                        max_length=8,
                    ),
                ),
                (
                    "issuer_url",
                    models.URLField(
                        blank=True,
                        help_text=(
                            "OIDC issuer URL. The well-known config at "
                            "<issuer>/.well-known/openid-configuration "
                            "drives the rest of the discovery flow. "
                            "Required when provider_type=OIDC."
                        ),
                        max_length=512,
                        null=True,
                    ),
                ),
                (
                    "authorization_url",
                    models.URLField(blank=True, max_length=512, null=True),
                ),
                (
                    "token_url",
                    models.URLField(blank=True, max_length=512, null=True),
                ),
                (
                    "userinfo_url",
                    models.URLField(blank=True, max_length=512, null=True),
                ),
                (
                    "jwks_url",
                    models.URLField(
                        blank=True,
                        help_text=(
                            "JWKS URL for ID token signature " "verification (OIDC)."
                        ),
                        max_length=512,
                        null=True,
                    ),
                ),
                (
                    "client_id_env_key",
                    models.CharField(
                        help_text=(
                            "Name of the env var holding the OAuth "
                            "client ID. Example: "
                            "'OAUTH_GOOGLE_WORKSPACE_CLIENT_ID'. The "
                            "value is read at startup; this column "
                            "never stores the secret."
                        ),
                        max_length=255,
                        validators=[
                            django.core.validators.RegexValidator(
                                message=(
                                    "client_id_env_key must be a POSIX "
                                    "env-var name (uppercase letters, "
                                    "digits, underscores)."
                                ),
                                regex="^[A-Z_][A-Z0-9_]*$",
                            ),
                        ],
                    ),
                ),
                (
                    "client_secret_env_key",
                    models.CharField(
                        help_text=(
                            "Name of the env var holding the OAuth "
                            "client secret. B.5.5: secret MUST NOT live "
                            "in source control or in the database. This "
                            "field is audit-masked per G.5.5."
                        ),
                        max_length=255,
                        validators=[
                            django.core.validators.RegexValidator(
                                message=(
                                    "client_secret_env_key must be a "
                                    "POSIX env-var name."
                                ),
                                regex="^[A-Z_][A-Z0-9_]*$",
                            ),
                        ],
                    ),
                ),
                (
                    "scopes",
                    django.contrib.postgres.fields.ArrayField(
                        base_field=models.CharField(max_length=128),
                        blank=True,
                        default=list,
                        help_text=(
                            "Requested OAuth scopes. ['openid', "
                            "'email', 'profile'] is a safe default "
                            "for OIDC."
                        ),
                        size=None,
                    ),
                ),
                (
                    "is_active",
                    models.BooleanField(
                        default=False,
                        help_text=(
                            "If False, the provider is invisible to the "
                            "login page and to the loader. Platform "
                            "admins flip this to True only after "
                            "security review."
                        ),
                    ),
                ),
                (
                    "require_verified_email",
                    models.BooleanField(
                        default=True,
                        help_text=(
                            "If True (the default), the provider must "
                            "report email_verified=true. Required by "
                            "B.5.6 to prevent account-takeover via "
                            "unverified-email linking."
                        ),
                    ),
                ),
                (
                    "trust_external_mfa",
                    models.BooleanField(
                        default=False,
                        help_text=(
                            "If True, the provider's MFA is treated as "
                            "satisfying login MFA (B.4.8). Requires "
                            "explicit security review (B.5.5) before "
                            "being enabled in production. Default is "
                            "False — users will be forced through local "
                            "TOTP enrollment."
                        ),
                    ),
                ),
                (
                    "allowed_email_domains",
                    django.contrib.postgres.fields.ArrayField(
                        base_field=models.CharField(max_length=253),
                        blank=True,
                        help_text=(
                            "Optional list of email-domain suffixes "
                            "(without the @). If set, only users whose "
                            "verified email matches one of these "
                            "domains may authenticate through this "
                            "provider."
                        ),
                        null=True,
                        size=None,
                    ),
                ),
                (
                    "allow_self_registration",
                    models.BooleanField(
                        default=False,
                        help_text=(
                            "Per-provider policy for B.4.6 step 4. If "
                            "True, new users from this provider may be "
                            "created on first login. If False (the "
                            "default), an existing User row is required "
                            "(e.g. via invitation). Tracked as a "
                            "deviation from B.3.7 in the M1 D5 retro."
                        ),
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "verbose_name": "OAuth/OIDC provider config",
                "verbose_name_plural": "OAuth/OIDC provider configs",
                "ordering": ["display_name", "provider_code"],
            },
        ),
    ]
