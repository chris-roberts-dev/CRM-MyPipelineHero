"""Custom User model (B.3.3).

This is the canonical platform identity. OAuth/OIDC login identities link
to this model; they do not replace it.

Notes on field shape:

* ``id`` is a UUID. UUID v7 (B.3.3 / C.1.1) requires Python 3.14+ where
  ``uuid.uuid7`` is available natively. We use it directly so we don't
  carry a third-party dependency.
* ``email`` is the ``USERNAME_FIELD``. It is normalized to lower case
  in ``UserManager._normalize_email_lower``.
* The TOTP fields, lockout fields, and external-login flag are present
  from migration #1 even though their behavior is wired up in M1. The
  guide is explicit that these belong on the user model from day one
  (B.3.3, J.2.7 #1) so we are not retrofitting columns post-deployment.

Service-layer note: state-changing flows on this model (lockout, TOTP
enrollment, password rotation) all live in service functions added in M1.
This model itself never carries business logic in ``save()``.
"""

from __future__ import annotations

import uuid
from typing import Any

from django.contrib.auth.hashers import make_password
from django.contrib.auth.models import (
    AbstractBaseUser,
    BaseUserManager,
    PermissionsMixin,
)
from django.db import models
from django.db.models import CheckConstraint, Q
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


def _new_user_uuid() -> uuid.UUID:
    """Return a UUID v7 (Python 3.14+) for the User primary key."""
    # ``uuid.uuid7`` was added in CPython 3.14. Fall back to uuid4 if missing
    # so the code is still importable on older interpreters during tooling.
    factory = getattr(uuid, "uuid7", uuid.uuid4)
    return factory()


class PreferredAuthMethod(models.TextChoices):
    """Hint for which login method this user prefers (B.3.3)."""

    PASSWORD = "PASSWORD", _("Password")
    OIDC = "OIDC", _("OAuth/OIDC")
    EITHER = "EITHER", _("Either")


class UserManager(BaseUserManager["User"]):
    """Custom manager for email-as-username users (B.3.3)."""

    use_in_migrations = True

    def _normalize_email_lower(self, email: str) -> str:
        if not email:
            raise ValueError("The Email field must be set")
        # BaseUserManager.normalize_email lowercases only the domain. The guide
        # requires the full address to be lower-case (B.3.3 CHECK constraint).
        return self.normalize_email(email).lower()

    def _create_user(
        self,
        email: str,
        password: str | None,
        **extra_fields: Any,
    ) -> User:
        email = self._normalize_email_lower(email)
        user = self.model(email=email, **extra_fields)
        if password:
            user.set_password(password)
            user.password_changed_at = timezone.now()
        else:
            # Unusable password — used by external-only and System users.
            user.password = make_password(None)
        user.save(using=self._db)
        return user

    def create_user(
        self,
        email: str,
        password: str | None = None,
        **extra_fields: Any,
    ) -> User:
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        extra_fields.setdefault("is_system", False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(
        self,
        email: str,
        password: str | None = None,
        **extra_fields: Any,
    ) -> User:
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)
        extra_fields.setdefault("is_system", False)
        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")
        return self._create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    """Canonical platform user (B.3.3).

    ``USERNAME_FIELD = "email"``. ``REQUIRED_FIELDS = []``.
    """

    id = models.UUIDField(primary_key=True, default=_new_user_uuid, editable=False)
    email = models.EmailField(_("email address"), unique=True)

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(
        default=False,
        help_text=_("User may access the platform console (B.3.4)."),
    )
    # is_superuser comes from PermissionsMixin
    is_system = models.BooleanField(
        default=False,
        help_text=_("Exactly one System User exists per environment (B.3.10)."),
    )

    # Local MFA (B.3.3). Wired in M1; columns present from migration #1.
    totp_secret = models.TextField(null=True, blank=True)
    totp_enrolled_at = models.DateTimeField(null=True, blank=True)
    backup_codes_hash = models.TextField(null=True, blank=True)

    # Account security (B.5)
    password_changed_at = models.DateTimeField(null=True, blank=True)
    last_password_breach_check_at = models.DateTimeField(null=True, blank=True)
    last_login_at = models.DateTimeField(null=True, blank=True)
    failed_login_count = models.PositiveIntegerField(default=0)
    locked_until = models.DateTimeField(null=True, blank=True)

    # Auth method preference + flags (B.3.3 / B.3.4)
    preferred_auth_method = models.CharField(
        max_length=16,
        choices=PreferredAuthMethod.choices,
        default=PreferredAuthMethod.EITHER,
    )
    external_login_only = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS: list[str] = []

    class Meta:
        verbose_name = _("user")
        verbose_name_plural = _("users")
        constraints = [
            # B.3.3: lower(email) = email
            CheckConstraint(
                condition=Q(email=models.functions.Lower("email")),
                name="platform_accounts_user_email_lowercase",
            ),
            # B.3.3: is_system implies (is_active AND NOT is_staff AND NOT is_superuser)
            CheckConstraint(
                condition=(
                    Q(is_system=False)
                    | (Q(is_active=True) & Q(is_staff=False) & Q(is_superuser=False))
                ),
                name="platform_accounts_user_system_user_invariant",
            ),
        ]

    def __str__(self) -> str:
        return self.email

    def get_full_name(self) -> str:
        # The user's per-membership name lives on Membership (B.3.5). The
        # platform-level identity exposes only email.
        return self.email

    def get_short_name(self) -> str:
        return self.email
