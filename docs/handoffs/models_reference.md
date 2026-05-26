# Django Models Reference

This file combines all `models.py` files in the project.

## backend / apps / common / outbox

`backend/apps/common/outbox/models.py`

```python
"""Placeholder for outbox models.

Concrete ``OutboxEntry`` lands in M1 (G.3.3).
"""

from __future__ import annotations
```

## backend / apps / common / tenancy

`backend/apps/common/tenancy/models.py`

```python
"""TenantOwnedModel abstract base (B.1.3).

Every tenant-owned model in the codebase inherits from this class.
The shape is dictated by B.1.3.

Subclasses MUST NOT override:
    - ``organization`` (the FK type and on_delete are mandatory)
    - ``is_tenant_owned`` (it is the discriminant for the B.1.7
      guardrail)
    - ``objects`` (the manager must remain ``TenantManager``-derived)

Subclasses MAY override:
    - ``created_at`` / ``updated_at`` semantics if a domain has a
      different audit-time concept (rare)
    - ``Meta.abstract = False`` is implicit; concrete subclasses define
      their own ``Meta`` (verbose names, indexes, constraints)
    - The QuerySet class (via ``TenantManager.from_queryset(...)``) to
      add per-model query helpers, including overriding
      ``intersect_with_operating_scope`` for models that carry
      ``location_id``.

See ``apps.common.tenancy.__init__`` for the developer primer on when
to subclass this vs use ``models.Manager``.
"""

from __future__ import annotations

from typing import ClassVar

from django.conf import settings
from django.db import models

from apps.common.tenancy.managers import TenantManager


class TenantOwnedModel(models.Model):
    """Abstract base for every tenant-owned model (B.1.3)."""

    organization = models.ForeignKey(
        "platform_organizations.Organization",
        on_delete=models.PROTECT,
        related_name="+",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="+",
        null=True,
        blank=True,
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="+",
        null=True,
        blank=True,
    )

    # Discriminant attribute checked by the B.1.7 guardrail. Subclasses
    # inherit this automatically; do not re-declare or override it.
    is_tenant_owned: ClassVar[bool] = True

    # Tenant-aware manager. Subclasses may swap in a manager built from
    # a per-model QuerySet subclass, but the manager MUST remain a
    # subclass of TenantManager so use_in_migrations=False and the
    # for_org/for_membership surface are preserved.
    objects: ClassVar[TenantManager] = TenantManager()

    class Meta:
        abstract = True
```

## backend / apps / operations / locations

`backend/apps/operations/locations/models.py`

```python
"""Region / Market / Location models (B.2.2).

All three inherit from :class:`apps.common.tenancy.models.TenantOwnedModel`,
which gives them:

* an ``organization`` FK with ``on_delete=PROTECT``,
* ``created_at`` / ``updated_at`` / ``created_by`` / ``updated_by`` audit columns,
* ``is_tenant_owned = True`` (so the B.1.7 guardrail picks them up),
* a default manager that is a :class:`TenantManager` subclass.

Hierarchy invariants (B.2.1):

* A Market belongs to exactly one Region.
* A Location belongs to exactly one Market.
* Cross-organization references are prohibited. This is enforced at
  the service layer via :func:`apps.common.tenancy.utils.ensure_same_org`.
  No cross-row DB CHECK constraint is used (B.1.6 forbids that pattern
  in v1).
"""

from __future__ import annotations

import uuid

from django.db import models

from apps.common.tenancy.managers import TenantManager, TenantQuerySet
from apps.common.tenancy.models import TenantOwnedModel

# ---------------------------------------------------------------------------
# Region
# ---------------------------------------------------------------------------


class Region(TenantOwnedModel):
    """Top-level operating-scope grouping within an Organization (B.2.2)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(max_length=64)
    name = models.CharField(max_length=128)
    is_active = models.BooleanField(default=True)

    class Meta:
        app_label = "operations_locations"
        verbose_name = "Region"
        verbose_name_plural = "Regions"
        unique_together = [("organization", "code")]
        ordering = ["organization_id", "code"]

    def __str__(self) -> str:
        return f"{self.code} — {self.name}"


# ---------------------------------------------------------------------------
# Market
# ---------------------------------------------------------------------------


class Market(TenantOwnedModel):
    """Mid-level operating-scope grouping, child of a Region (B.2.2)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    region = models.ForeignKey(
        Region,
        on_delete=models.PROTECT,
        related_name="markets",
    )
    code = models.CharField(max_length=64)
    name = models.CharField(max_length=128)
    is_active = models.BooleanField(default=True)

    class Meta:
        app_label = "operations_locations"
        verbose_name = "Market"
        verbose_name_plural = "Markets"
        unique_together = [("organization", "code")]
        ordering = ["organization_id", "code"]

    def __str__(self) -> str:
        return f"{self.code} — {self.name}"


# ---------------------------------------------------------------------------
# Location — with per-model QuerySet (B.2.5 pattern)
# ---------------------------------------------------------------------------


class LocationQuerySet(TenantQuerySet):
    """Per-model QuerySet for Location.

    Location is the *leaf* of the operating-scope hierarchy: every
    permitted Location id IS itself the row this queryset returns. So
    rather than filtering ``location_id__in=...`` (the pattern in
    B.2.5's SalesOrder example), we filter ``id__in=...``.

    The membership-no-scope-assignments rules from B.2.5 still apply:

    * No assignments + non-scoped role  → org-wide access (return self).
    * No assignments + scoped role      → zero access (return self.none()).
    * Has assignments                   → filter to the permitted set.
    """

    def intersect_with_operating_scope(self, membership) -> LocationQuerySet:  # type: ignore[override]
        # Avoid the import cycle: resolve_location_ids_for_scopes lives
        # in apps.common.tenancy.utils which itself depends on this
        # package indirectly via models registry walks. Import locally.
        from apps.common.tenancy.utils import resolve_location_ids_for_scopes

        scopes = list(membership.scope_assignments.all())
        if not scopes:
            if membership.role_assignments.filter(role__is_scoped_role=True).exists():
                return self.none()
            return self
        permitted = resolve_location_ids_for_scopes(scopes)
        return self.filter(id__in=permitted)


class LocationManager(TenantManager.from_queryset(LocationQuerySet)):  # type: ignore[misc]
    """Default manager for Location.

    Reuses TenantManager's invariants (use_in_migrations=False) and
    layers on the LocationQuerySet method surface.
    """

    use_in_migrations: bool = False


class Location(TenantOwnedModel):
    """Leaf node in the operating-scope hierarchy (B.2.2).

    The address fields are denormalized for fast display and for
    pricing/tax inputs (B.2.7). The ``region_admin`` field holds the
    administrative region (state/province) — note this is unrelated to
    the operating-scope ``region`` FK on Market.

    ``tax_jurisdiction_id`` is a plain UUID column awaiting the
    TaxJurisdiction model that lands in M3 (J.5). It will be converted
    to a real FK at that time. Same pattern as
    ``Organization.default_tax_jurisdiction_id`` from M0 D2.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    market = models.ForeignKey(
        Market,
        on_delete=models.PROTECT,
        related_name="locations",
    )
    code = models.CharField(max_length=64)
    name = models.CharField(max_length=128)

    # Address fields (B.2.2)
    address_line1 = models.CharField(max_length=256, blank=True, default="")
    address_line2 = models.CharField(max_length=256, blank=True, default="")
    city = models.CharField(max_length=128, blank=True, default="")
    region_admin = models.CharField(
        max_length=128,
        blank=True,
        default="",
        help_text=(
            "Administrative region (state/province). Unrelated to the "
            "operating-scope Region attached via market.region."
        ),
    )
    postal_code = models.CharField(max_length=32, blank=True, default="")
    country = models.CharField(max_length=64, blank=True, default="")

    tax_jurisdiction_id = models.UUIDField(
        null=True,
        blank=True,
        help_text=(
            "Plain UUID column awaiting M3 TaxJurisdiction model. "
            "Converted to a real FK at that milestone."
        ),
    )

    is_active = models.BooleanField(default=True)

    objects = LocationManager()  # type: ignore[assignment]

    class Meta:
        app_label = "operations_locations"
        verbose_name = "Location"
        verbose_name_plural = "Locations"
        unique_together = [("organization", "code")]
        ordering = ["organization_id", "code"]

    def __str__(self) -> str:
        return f"{self.code} — {self.name}"
```

## backend / apps / platform / accounts / handoff

`backend/apps/platform/accounts/handoff/models.py`

```python
"""HandoffSigningKey model (B.4.13.1, M1 D6 Phase 1).

The model carries no business logic in save(); see the
``handoff/services/`` package for the lifecycle services.

The ``secret`` column holds the Fernet-encrypted per-rotation HMAC
secret as a TextField (Fernet tokens are base64 ASCII). See
``encryption.py`` for the encrypt/decrypt helpers and the deviation
note in the M1 D6 retro.
"""

from __future__ import annotations

import uuid
from typing import Any, ClassVar

from django.db import models
from django.db.models import CheckConstraint, Q
from django.utils.translation import gettext_lazy as _


def _new_uuid() -> uuid.UUID:
    """UUID v7 factory (Python 3.14+). Falls back to uuid4 for older runtimes."""
    factory = getattr(uuid, "uuid7", uuid.uuid4)
    return factory()


class HandoffSigningKey(models.Model):
    """Per-rotation HMAC signing key for handoff tokens (B.4.13.1).

    Lifecycle:

    1. Created — ``created_at`` set, ``promoted_at`` NULL,
       ``retired_at`` NULL. Cannot verify tokens yet.
    2. Promoted — ``promoted_at`` set. Becomes the primary
       (newest non-retired) for token issuance. Previous primary
       remains active for verification during overlap window.
    3. Retired — ``retired_at`` set. No longer used for
       verification. Row preserved for audit reconstruction.

    Active key set rules (enforced at service layer):

    * Exactly one primary key at a time (the newest non-retired).
    * At most two non-retired keys at any moment (rotation overlap).
    * Retired keys stay in the table indefinitely.

    The ``CHECK retired_at IS NULL OR retired_at > created_at``
    constraint catches operator error at the DB layer.
    """

    id = models.UUIDField(primary_key=True, default=_new_uuid, editable=False)

    # Short stable identifier embedded in JWT ``kid`` header. Format
    # is validated at service-layer; not enforced by DB regex.
    # Example: "hsk_2026q2", "hsk_emergency_20260522".
    key_id = models.CharField(
        max_length=64,
        unique=True,
        editable=False,
    )

    # Fernet-encrypted HMAC secret. TextField because Fernet tokens
    # are base64 ASCII. Never exposed in admin / __str__ / __repr__.
    secret = models.TextField(editable=False)

    # Algorithm pinned to HS256 per B.4.12 / B.4.13.1. Stored so a
    # future migration to RS256 (or a stronger HS) can coexist with
    # older rows.
    algorithm = models.CharField(
        max_length=16,
        default="HS256",
        editable=False,
    )

    created_at = models.DateTimeField(auto_now_add=True)
    promoted_at = models.DateTimeField(null=True, blank=True, editable=False)
    retired_at = models.DateTimeField(null=True, blank=True, editable=False)

    class Meta:
        verbose_name = _("handoff signing key")
        verbose_name_plural = _("handoff signing keys")
        constraints: ClassVar[list[Any]] = [
            CheckConstraint(
                condition=Q(retired_at__isnull=True)
                | Q(retired_at__gt=models.F("created_at")),
                name="handoff_signing_key_retired_after_created",
            ),
        ]
        indexes: ClassVar[list[Any]] = [
            # Primary-key lookup pattern: active (retired_at IS NULL),
            # ordered by created_at DESC.
            models.Index(
                fields=["-created_at"],
                condition=Q(retired_at__isnull=True),
                name="handoff_signing_key_active_idx",
            ),
        ]

    def __str__(self) -> str:
        status = (
            "retired"
            if self.retired_at
            else ("primary" if self.promoted_at else "pending")
        )
        return f"HandoffSigningKey({self.key_id}, {status})"

    def __repr__(self) -> str:
        # Explicitly excludes the encrypted secret to avoid accidental
        # disclosure in tracebacks or shell prints.
        return (
            f"HandoffSigningKey(id={self.id}, key_id={self.key_id!r}, "
            f"created_at={self.created_at!r}, "
            f"promoted_at={self.promoted_at!r}, "
            f"retired_at={self.retired_at!r})"
        )
```

## backend / apps / platform / accounts / impersonation

`backend/apps/platform/accounts/impersonation/models.py`

```python
"""ImpersonationSession model (M1 D7 Phase 4, B.7).

Records every platform-admin impersonation: who, who, when started,
when ended, why. The lifecycle is created at start, mutated only by
end (writes ``ended_at`` + ``ended_by_user`` + ``end_reason``).

Per project posture:
* UUID v7 primary key.
* No business logic in ``save()`` — services do the state changes.
* All FKs use ``on_delete=PROTECT`` — impersonation history must
  not silently disappear when a user is deleted.
* Constraints enforce the cross-field invariants at the database
  level (admin != target, ended_at >= started_at, the
  "ended-together" pair is set or both null, one active per admin).

The model is in the accounts app's ``impersonation`` subpackage to
match the ``oauth/`` and ``handoff/`` precedent. Discovery from the
app config requires an explicit import in ``apps.py:ready()`` —
without it, ``makemigrations`` generates spurious ``DeleteModel``
migrations because Django's auto-discovery doesn't follow into
sub-package ``models.py``.
"""

from __future__ import annotations

from typing import Any, ClassVar
from uuid import UUID, uuid7

from django.conf import settings
from django.db import models
from django.db.models import CheckConstraint, F, Q, UniqueConstraint
from django.utils.translation import gettext_lazy as _


def _new_session_uuid() -> UUID:
    """UUID v7 (Python 3.14+) primary keys for ImpersonationSession."""
    return uuid7()


class ImpersonationEndReason(models.TextChoices):
    """How an impersonation session ended (B.7)."""

    ADMIN_ENDED = "ADMIN_ENDED", _("Admin ended")
    LOGOUT = "LOGOUT", _("Logout")
    EXPIRED = "EXPIRED", _("Expired")


class ImpersonationSessionManager(models.Manager["ImpersonationSession"]):
    """Manager exposing the active-session lookup."""

    def active_for_admin(self, admin_user_id: UUID) -> ImpersonationSession | None:
        """Return the admin's currently-active session, or None.

        At most one active session per admin is permitted by the
        partial unique index in ``Meta.constraints``. This helper
        is the canonical read site for "is this admin currently
        impersonating?"
        """
        return self.filter(admin_user_id=admin_user_id, ended_at__isnull=True).first()


class ImpersonationSession(models.Model):
    """Authoritative record of a single platform-admin impersonation (B.7).

    A row is created at impersonation start and mutated only at end.
    The session is "active" while ``ended_at IS NULL``; otherwise
    closed. Audit events ``IMPERSONATION_STARTED`` and
    ``IMPERSONATION_ENDED`` correspond to the create + close
    transitions.

    The session anchors to a specific (target_user, organization,
    membership) triple. The membership FK is the strict source of
    truth for "what scope was the admin acting in"; the redundant
    ``organization`` FK is denormalized for fast tenant-scoped
    queries (Phase 5 will display "active impersonations in this
    org").

    All FKs are ``PROTECT``. Impersonation history is audit-grade
    data — a user deletion that would orphan an impersonation row
    must be blocked. The ``platform_audit.AuditEvent`` rows (M2)
    will reference these by ID.
    """

    id = models.UUIDField(primary_key=True, default=_new_session_uuid, editable=False)

    # Who.
    admin_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="impersonation_sessions_initiated",
        help_text=_("Platform admin performing the impersonation (B.7)."),
    )
    target_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="impersonation_sessions_received",
        help_text=_("User being impersonated."),
    )

    # Where.
    organization = models.ForeignKey(
        "platform_organizations.Organization",
        on_delete=models.PROTECT,
        related_name="impersonation_sessions",
    )
    membership = models.ForeignKey(
        "platform_organizations.Membership",
        on_delete=models.PROTECT,
        related_name="impersonation_sessions",
        help_text=_(
            "The specific membership being assumed. Anchors the "
            "session to a (user, org) pair that was ACTIVE at "
            "start time."
        ),
    )

    # Why.
    reason = models.TextField(help_text=_("Business reason for impersonation (B.7)."))

    # When — domain timestamps.
    started_at = models.DateTimeField(auto_now_add=True)
    ended_at = models.DateTimeField(null=True, blank=True)

    # How it ended.
    ended_by_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="impersonation_sessions_ended",
        help_text=_("User who ended the session. NULL while session is active."),
    )
    end_reason = models.CharField(
        max_length=16,
        choices=ImpersonationEndReason.choices,
        blank=True,
        default="",
        help_text=_(
            "Why the session ended. Empty string while active; "
            "set when ended_at is set."
        ),
    )

    # Audit columns.
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = ImpersonationSessionManager()

    class Meta:
        verbose_name = _("impersonation session")
        verbose_name_plural = _("impersonation sessions")
        indexes: ClassVar[list[Any]] = [
            models.Index(
                fields=["admin_user", "started_at"],
                name="impers_admin_started_idx",
            ),
            models.Index(
                fields=["target_user", "started_at"],
                name="impers_target_started_idx",
            ),
            models.Index(
                fields=["organization", "started_at"],
                name="impers_org_started_idx",
            ),
        ]
        constraints: ClassVar[list[Any]] = [
            # B.7: can't impersonate yourself.
            CheckConstraint(
                condition=~Q(admin_user=F("target_user")),
                name="impers_admin_not_target",
            ),
            # ended_at must be >= started_at when set.
            CheckConstraint(
                condition=Q(ended_at__isnull=True) | Q(ended_at__gte=F("started_at")),
                name="impers_ended_after_started",
            ),
            # ended_at and ended_by_user are set together (both
            # null or both non-null).
            CheckConstraint(
                condition=(
                    (Q(ended_at__isnull=True) & Q(ended_by_user__isnull=True))
                    | (Q(ended_at__isnull=False) & Q(ended_by_user__isnull=False))
                ),
                name="impers_ended_pair_together",
            ),
            # At most one active impersonation per admin.
            UniqueConstraint(
                fields=["admin_user"],
                condition=Q(ended_at__isnull=True),
                name="impers_one_active_per_admin",
            ),
        ]

    def __str__(self) -> str:
        state = "active" if self.ended_at is None else "ended"
        return (
            f"ImpersonationSession({self.admin_user_id} → "
            f"{self.target_user_id}, {state})"
        )

    @property
    def is_active(self) -> bool:
        """True while ``ended_at`` is null."""
        return self.ended_at is None
```

## backend / apps / platform / accounts

`backend/apps/platform/accounts/models.py`

```python
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
from typing import Any, ClassVar

from django.contrib.auth.hashers import make_password
from django.contrib.auth.models import (
    AbstractBaseUser,
    BaseUserManager,
    PermissionsMixin,
)
from django.db import models
from django.db.models import CheckConstraint, Q
from django.db.models.functions import Lower
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
        """Create a superuser AND auto-install a verified EmailAddress.

        M1 D7 Phase 1 — Ergonomics fix. Settings include
        ``ACCOUNT_EMAIL_VERIFICATION = "mandatory"`` per the production
        posture, which means every login by a user without a verified
        ``allauth.account.models.EmailAddress`` row is bounced to the
        email-confirmation flow. For the bootstrap superuser, this is a
        chicken-and-egg blocker (no Mailpit, no SMTP, can't sign in
        to configure either).

        Calling :func:`ensure_verified_email_address` here makes the
        bootstrap superuser able to sign in immediately after
        ``createsuperuser`` completes. The function is idempotent, so
        re-running the management command doesn't double-create.

        This catches both the CLI ``createsuperuser`` path AND any
        programmatic superuser creation (dev scripts, tests) — the
        hook is at the manager method rather than at the management
        command, so all paths to superuser get the verified
        EmailAddress.
        """
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)
        extra_fields.setdefault("is_system", False)
        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")
        user = self._create_user(email, password, **extra_fields)

        # Import inline to avoid circular import at module load
        # (utils package imports from allauth, which we want to avoid
        # forcing into the User-model import path).
        from apps.platform.accounts.utils import ensure_verified_email_address

        ensure_verified_email_address(user)

        return user


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

    # Django-auth class-level configuration. Annotated with ClassVar so static
    # analyzers (ruff RUF012) recognize them as intentionally class-shared
    # configuration rather than mutable instance defaults.
    USERNAME_FIELD: ClassVar[str] = "email"
    REQUIRED_FIELDS: ClassVar[list[str]] = []

    class Meta:
        verbose_name = _("user")
        verbose_name_plural = _("users")
        # ClassVar tells ruff this is intentional class-level metadata, not
        # a mutable instance default.
        constraints: ClassVar[list[Any]] = [
            # B.3.3: lower(email) = email
            CheckConstraint(
                condition=Q(email=Lower("email")),
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
```

## backend / apps / platform / accounts / oauth

`backend/apps/platform/accounts/oauth/models.py`

```python
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
```

## backend / apps / platform / audit

`backend/apps/platform/audit/models.py`

```python
"""Placeholder for AuditEvent (C.1.14, G.5)."""

from __future__ import annotations
```

## backend / apps / platform / organizations

`backend/apps/platform/organizations/models.py`

```python
"""Organization, Membership, and tenant-lifecycle entities (B.1.2, B.3.5, C.1.16).

This module owns the multi-tenant root entity. Every other tenant-owned
model in the codebase references ``Organization`` via a PROTECTed FK
(B.1.3).

Service-layer note: state-changing flows (create_organization,
invite_user, suspend_membership, request_tenant_deletion, etc.) live in
service functions added in M1+. The models in this file carry no
business logic in ``save()`` — they only declare structure.

Index naming: every ``models.Index`` carries an explicit ``name=``
argument. Auto-generated index names are fragile across Django versions
(the 6-char hash suffix Django computes can drift) and cause spurious
``RenameIndex`` migrations on every ``makemigrations`` run. Always name
indexes explicitly going forward.
"""

from __future__ import annotations

import uuid
from typing import Any, ClassVar

from django.conf import settings
from django.db import models
from django.db.models import Q, UniqueConstraint
from django.utils.translation import gettext_lazy as _


def _new_uuid() -> uuid.UUID:
    """UUID v7 factory (Python 3.14+). Falls back to uuid4 for older runtimes."""
    factory = getattr(uuid, "uuid7", uuid.uuid4)
    return factory()


# ---------------------------------------------------------------------------
# Choices
# ---------------------------------------------------------------------------


class OrganizationStatus(models.TextChoices):
    """Organization lifecycle states (B.1.2)."""

    ACTIVE = "ACTIVE", _("Active")
    SUSPENDED = "SUSPENDED", _("Suspended")
    OFFBOARDING = "OFFBOARDING", _("Offboarding")
    DELETED = "DELETED", _("Deleted")


class MembershipStatus(models.TextChoices):
    """Membership lifecycle states (B.3.5, C.2.9)."""

    INVITED = "INVITED", _("Invited")
    ACTIVE = "ACTIVE", _("Active")
    SUSPENDED = "SUSPENDED", _("Suspended")
    INACTIVE = "INACTIVE", _("Inactive")
    EXPIRED = "EXPIRED", _("Expired")


class TenantExportScope(models.TextChoices):
    """Scope of a tenant data export request (C.1.16, G.7.2)."""

    FULL = "FULL", _("Full")
    COMMERCIAL_ONLY = "COMMERCIAL_ONLY", _("Commercial only")
    AUDIT_ONLY = "AUDIT_ONLY", _("Audit only")


class TenantExportStatus(models.TextChoices):
    """Lifecycle of a tenant export request (C.1.16, G.7.2)."""

    QUEUED = "QUEUED", _("Queued")
    ASSEMBLING = "ASSEMBLING", _("Assembling")
    READY = "READY", _("Ready")
    DOWNLOADED = "DOWNLOADED", _("Downloaded")
    EXPIRED = "EXPIRED", _("Expired")
    FAILED = "FAILED", _("Failed")
    CANCELLED = "CANCELLED", _("Cancelled")


class TenantDeletionStatus(models.TextChoices):
    """Lifecycle of a tenant deletion request (C.1.16, G.7.3)."""

    GRACE_PERIOD = "GRACE_PERIOD", _("Grace period")
    EXECUTING = "EXECUTING", _("Executing")
    EXECUTED = "EXECUTED", _("Executed")
    CANCELLED = "CANCELLED", _("Cancelled")


# ---------------------------------------------------------------------------
# Organization
# ---------------------------------------------------------------------------


class Organization(models.Model):
    """Tenant root (B.1.2).

    Field notes:
    * ``slug`` matches ``^[a-z][a-z0-9-]{1,61}[a-z0-9]$`` and is the subdomain
      key for tenant routing. Slug is immutable post-creation in v1.
    * ``default_tax_jurisdiction_id`` and ``invoicing_policy_id`` reference
      models that land in later milestones (M3 catalog/pricing, M5 billing).
      They are declared as plain UUID columns for now and converted to real
      ``ForeignKey`` columns when those target models exist. The on-delete
      semantics will be ``SET_NULL`` to match the nullable shape.
    * ``accounting_adapter_config`` is required to be encrypted at rest in
      production (F.5.4). We store it as plain JSONB here; an
      ``EncryptedJSONField`` is introduced in M5 alongside the first concrete
      accounting adapter. Local-dev impact: none.
    """

    id = models.UUIDField(primary_key=True, default=_new_uuid, editable=False)
    slug = models.CharField(max_length=63, unique=True)
    name = models.CharField(max_length=200)
    status = models.CharField(
        max_length=16,
        choices=OrganizationStatus.choices,
        default=OrganizationStatus.ACTIVE,
    )

    # Primary contact
    primary_contact_name = models.CharField(max_length=200, blank=True, default="")
    primary_contact_email = models.EmailField()
    primary_contact_phone = models.CharField(max_length=64, blank=True, default="")

    # Locale and finance
    timezone = models.CharField(max_length=64, default="America/Chicago")
    base_currency_code = models.CharField(max_length=3, default="USD")

    # Forward references to later-milestone models (M3/M5).
    # TODO(M3): convert default_tax_jurisdiction_id to FK(TaxJurisdiction, SET_NULL)
    # TODO(M5): convert invoicing_policy_id to FK(InvoicingPolicy, SET_NULL)
    default_tax_jurisdiction_id = models.UUIDField(null=True, blank=True)
    invoicing_policy_id = models.UUIDField(null=True, blank=True)

    # Numbering configuration — per-entity prefix overrides (C.3).
    numbering_config = models.JSONField(default=dict, blank=True)

    # Accounting adapter (F.5.4).
    accounting_adapter_code = models.CharField(max_length=64, default="noop")
    # TODO(M5): replace with EncryptedJSONField when the adapter ships.
    accounting_adapter_config = models.JSONField(default=dict, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("organization")
        verbose_name_plural = _("organizations")
        indexes: ClassVar[list[Any]] = [
            models.Index(fields=["status"], name="platform_or_status_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.slug})"


# ---------------------------------------------------------------------------
# Membership
# ---------------------------------------------------------------------------


class Membership(models.Model):
    """Authoritative tenant-access record (B.3.5).

    Membership is the authoritative tenant-access record. OAuth/OIDC login
    proves identity only — it does not grant tenant access by itself
    (B.3.9).

    The partial unique index on ``is_default_for_user`` enforces that a
    user has at most one default membership (B.3.5).
    """

    id = models.UUIDField(primary_key=True, default=_new_uuid, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="memberships",
    )
    organization = models.ForeignKey(
        Organization,
        on_delete=models.PROTECT,
        related_name="memberships",
    )
    status = models.CharField(
        max_length=16,
        choices=MembershipStatus.choices,
        default=MembershipStatus.INVITED,
    )

    # Invitation fields (B.4 / M1)
    invited_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="+",
    )
    invited_at = models.DateTimeField(null=True, blank=True)
    invitation_expires_at = models.DateTimeField(null=True, blank=True)
    # Audit-masked in service-layer logging.
    invitation_token_hash = models.CharField(max_length=128, null=True, blank=True)
    accepted_at = models.DateTimeField(null=True, blank=True)

    # Per-membership personal name (independent of platform-level User identity)
    first_name = models.CharField(max_length=80, blank=True, default="")
    last_name = models.CharField(max_length=80, blank=True, default="")
    phone = models.CharField(max_length=64, null=True, blank=True)

    is_default_for_user = models.BooleanField(default=False)
    suspended_reason = models.TextField(blank=True, default="")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("membership")
        verbose_name_plural = _("memberships")
        constraints: ClassVar[list[Any]] = [
            UniqueConstraint(
                fields=["user", "organization"],
                name="platform_organizations_membership_user_org_unique",
            ),
            # Partial unique index — at most one default membership per user.
            UniqueConstraint(
                fields=["user"],
                condition=Q(is_default_for_user=True),
                name="platform_organizations_membership_one_default_per_user",
            ),
        ]
        indexes: ClassVar[list[Any]] = [
            models.Index(
                fields=["user", "organization"], name="platform_or_user_id_org_idx"
            ),
            models.Index(
                fields=["organization", "status"], name="platform_or_org_id_status_idx"
            ),
        ]

    def __str__(self) -> str:
        display_name = " ".join(
            part for part in [self.first_name, self.last_name] if part
        ).strip()

        if not display_name:
            get_full_name = getattr(self.user, "get_full_name", None)
            if callable(get_full_name):
                display_name = get_full_name().strip()

        if not display_name:
            display_name = getattr(self.user, "email", str(self.user))

        return (
            f"{display_name} - {self.organization.name} ({self.get_status_display()})"
        )


# ---------------------------------------------------------------------------
# Tenant lifecycle requests
# ---------------------------------------------------------------------------


class TenantExportRequest(models.Model):
    """Tenant data export request (C.1.16, G.7.2).

    Schema only — service logic lands with the export pipeline in a later
    milestone. ``output_attachment_id`` will become a FK to
    ``DocumentAttachment`` when the files app's models land; declared as a
    plain UUID column for now.
    """

    id = models.UUIDField(primary_key=True, default=_new_uuid, editable=False)
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="export_requests",
    )
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="+",
    )
    requested_at = models.DateTimeField(auto_now_add=True)
    requested_scope = models.CharField(
        max_length=24,
        choices=TenantExportScope.choices,
        default=TenantExportScope.FULL,
    )
    status = models.CharField(
        max_length=16,
        choices=TenantExportStatus.choices,
        default=TenantExportStatus.QUEUED,
    )

    # TODO(M2+): convert to FK(DocumentAttachment) once files app lands.
    output_attachment_id = models.UUIDField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    failure_reason = models.TextField(blank=True, default="")
    bytes_size = models.BigIntegerField(null=True, blank=True)
    row_count = models.BigIntegerField(null=True, blank=True)

    cancelled_at = models.DateTimeField(null=True, blank=True)
    cancelled_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="+",
    )

    class Meta:
        verbose_name = _("tenant export request")
        verbose_name_plural = _("tenant export requests")
        indexes: ClassVar[list[Any]] = [
            models.Index(
                fields=["organization", "status"],
                name="platform_or_export_org_st_idx",
            ),
            models.Index(
                fields=["status", "expires_at"], name="platform_or_status_expires_idx"
            ),
        ]

    def __str__(self) -> str:
        return (
            f"Export request {str(self.id)[:8]} "
            f"for {self.organization} "
            f"({self.get_requested_scope_display()}, {self.get_status_display()})"
        )


class TenantDeletionRequest(models.Model):
    """Tenant deletion request (C.1.16, G.7.3).

    Multi-stage workflow with a 30-day grace period. Schema only —
    ``request_tenant_deletion`` / ``cancel_tenant_deletion`` /
    ``execute_tenant_deletion`` services land in M1+.
    """

    id = models.UUIDField(primary_key=True, default=_new_uuid, editable=False)
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="deletion_requests",
    )
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="+",
    )
    requested_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(
        max_length=16,
        choices=TenantDeletionStatus.choices,
        default=TenantDeletionStatus.GRACE_PERIOD,
    )
    grace_period_ends_at = models.DateTimeField()
    # Required: confirmation phrase MUST equal the org slug (G.7.3).
    confirmation_phrase_provided = models.CharField(max_length=63)

    cancelled_at = models.DateTimeField(null=True, blank=True)
    cancelled_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="+",
    )
    cancelled_reason = models.TextField(blank=True, default="")

    executed_at = models.DateTimeField(null=True, blank=True)
    executed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="+",
    )
    rows_deleted_per_table = models.JSONField(null=True, blank=True)

    class Meta:
        verbose_name = _("tenant deletion request")
        verbose_name_plural = _("tenant deletion requests")
        indexes: ClassVar[list[Any]] = [
            models.Index(
                fields=["organization", "status"], name="platform_or_org_status_del_idx"
            ),
            models.Index(
                fields=["status", "grace_period_ends_at"],
                name="platform_or_status_grace_idx",
            ),
        ]

    def __str__(self) -> str:
        return (
            f"Deletion request {str(self.id)[:8]} "
            f"for {self.organization} "
            f"({self.get_status_display()}, grace ends {self.grace_period_ends_at:%Y-%m-%d})"
        )
```

## backend / apps / platform / rbac

`backend/apps/platform/rbac/models.py`

```python
"""RBAC models: Capability, Role, RoleCapability, MembershipRole,
MembershipCapabilityGrant (B.6.7).

The capability registry is populated by the ``seed_v1`` data migration
(I.6.3). Role templates with ``organization=None, is_locked=True,
is_default=True`` are also seeded; per-tenant Owner/Admin/etc. roles
are created by ``services.create_organization`` (I.6.6).

Permission evaluation algorithm: B.6.2.

Index naming: every ``models.Index`` carries an explicit ``name=``
argument. Auto-generated index names are fragile across Django versions
(the 6-char hash suffix Django computes can drift) and cause spurious
``RenameIndex`` migrations on every ``makemigrations`` run. Always name
indexes explicitly going forward.
"""

from __future__ import annotations

import uuid
from typing import Any, ClassVar

from django.conf import settings
from django.db import models
from django.db.models import Q, UniqueConstraint
from django.utils.translation import gettext_lazy as _


def _new_uuid() -> uuid.UUID:
    """UUID v7 factory (Python 3.14+)."""
    factory = getattr(uuid, "uuid7", uuid.uuid4)
    return factory()


# ---------------------------------------------------------------------------
# Choices
# ---------------------------------------------------------------------------


class CapabilityGrantType(models.TextChoices):
    """Per-membership capability overrides (B.6.7)."""

    GRANT = "GRANT", _("Grant")
    DENY = "DENY", _("Deny")


# ---------------------------------------------------------------------------
# Capability
# ---------------------------------------------------------------------------


class Capability(models.Model):
    """Atomic permission unit (B.6.3, B.6.7).

    Capabilities are platform-scoped (no organization FK). Their codes
    are stable contract strings — renaming is a breaking change
    (G.2.3 analog).
    """

    id = models.UUIDField(primary_key=True, default=_new_uuid, editable=False)
    code = models.CharField(max_length=64, unique=True)
    name = models.CharField(max_length=120)
    description = models.TextField(blank=True, default="")
    category = models.CharField(max_length=64)

    is_deprecated = models.BooleanField(default=False)
    deprecated_in_version = models.CharField(max_length=32, null=True, blank=True)
    deprecated_replacement_code = models.CharField(max_length=64, null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("capability")
        verbose_name_plural = _("capabilities")
        indexes: ClassVar[list[Any]] = [
            models.Index(fields=["category"], name="platform_rb_categ_idx"),
            models.Index(fields=["is_deprecated"], name="platform_rb_dep_idx"),
        ]

    def __str__(self) -> str:
        return self.code


# ---------------------------------------------------------------------------
# Role
# ---------------------------------------------------------------------------


class Role(models.Model):
    """A bundle of capabilities (B.6.7).

    Template roles have ``organization=NULL, is_default=True,
    is_locked=True``. Per-tenant roles have a concrete organization FK
    and are cloned from templates by ``services.create_organization``
    (I.6.6).

    Uniqueness is ``(organization, code)``. Because ``organization`` is
    nullable and Postgres treats ``NULL`` as distinct by default in unique
    indexes, the constraint uses ``nulls_distinct=False`` so a single
    template per ``code`` is enforced.
    """

    id = models.UUIDField(primary_key=True, default=_new_uuid, editable=False)
    organization = models.ForeignKey(
        "platform_organizations.Organization",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="roles",
        help_text=_(
            "NULL for default templates; concrete org for tenant-scoped roles."
        ),
    )
    code = models.CharField(max_length=64)
    name = models.CharField(max_length=120)
    description = models.TextField(blank=True, default="")

    is_default = models.BooleanField(default=False)
    is_scoped_role = models.BooleanField(
        default=False,
        help_text=_("If True, membership scope assignments restrict access (B.2.5)."),
    )
    is_locked = models.BooleanField(
        default=False,
        help_text=_("If True, capabilities cannot be edited via tenant admin."),
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("role")
        verbose_name_plural = _("roles")
        constraints: ClassVar[list[Any]] = [
            # Tenant-scoped uniqueness (organization is non-null).
            UniqueConstraint(
                fields=["organization", "code"],
                condition=Q(organization__isnull=False),
                name="platform_rbac_role_org_code_unique",
            ),
            # Template uniqueness (organization is NULL).
            UniqueConstraint(
                fields=["code"],
                condition=Q(organization__isnull=True),
                name="platform_rbac_role_template_code_unique",
            ),
        ]
        indexes: ClassVar[list[Any]] = [
            models.Index(
                fields=["organization", "is_default"], name="platform_rb_org_def_idx"
            ),
        ]

    def __str__(self) -> str:
        return f"{self.code}"


# ---------------------------------------------------------------------------
# RoleCapability
# ---------------------------------------------------------------------------


class RoleCapability(models.Model):
    """Role → Capability assignment (B.6.7)."""

    id = models.UUIDField(primary_key=True, default=_new_uuid, editable=False)
    role = models.ForeignKey(
        Role,
        on_delete=models.CASCADE,
        related_name="role_capabilities",
    )
    capability = models.ForeignKey(
        Capability,
        on_delete=models.PROTECT,
        related_name="role_capabilities",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("role capability")
        verbose_name_plural = _("role capabilities")
        constraints: ClassVar[list[Any]] = [
            UniqueConstraint(
                fields=["role", "capability"],
                name="platform_rbac_rolecap_unique",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.role} → {self.capability}"


# ---------------------------------------------------------------------------
# MembershipRole
# ---------------------------------------------------------------------------


class MembershipRole(models.Model):
    """Membership → Role assignment (B.6.7).

    Note: the guide names the entity ``MembershipRole`` (B.6.7 line 2073).
    The M2M is between membership and role; one membership can hold
    multiple roles.
    """

    id = models.UUIDField(primary_key=True, default=_new_uuid, editable=False)
    membership = models.ForeignKey(
        "platform_organizations.Membership",
        on_delete=models.CASCADE,
        related_name="role_assignments",
    )
    role = models.ForeignKey(
        Role,
        on_delete=models.PROTECT,
        related_name="member_assignments",
    )
    # null=True so seed-time / bootstrap assignments don't deadlock.
    # Production assignments through services always set this.
    assigned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="+",
    )
    assigned_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("membership role")
        verbose_name_plural = _("membership roles")
        constraints: ClassVar[list[Any]] = [
            UniqueConstraint(
                fields=["membership", "role"],
                name="platform_rbac_membershiprole_unique",
            ),
        ]
        indexes: ClassVar[list[Any]] = [
            models.Index(fields=["membership"], name="platform_rb_memb_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.membership} → {self.role}"


# ---------------------------------------------------------------------------
# MembershipCapabilityGrant
# ---------------------------------------------------------------------------


class MembershipCapabilityGrant(models.Model):
    """Per-membership capability override (GRANT or DENY) — B.6.2 step 5.

    DENY beats GRANT (B.6.2). Applied on top of role-derived capabilities
    during permission evaluation.
    """

    id = models.UUIDField(primary_key=True, default=_new_uuid, editable=False)
    membership = models.ForeignKey(
        "platform_organizations.Membership",
        on_delete=models.CASCADE,
        related_name="capability_grants",
    )
    capability = models.ForeignKey(
        Capability,
        on_delete=models.PROTECT,
        related_name="membership_grants",
    )
    grant_type = models.CharField(
        max_length=8,
        choices=CapabilityGrantType.choices,
    )
    reason = models.TextField()
    granted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="+",
    )
    granted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("membership capability grant")
        verbose_name_plural = _("membership capability grants")
        constraints: ClassVar[list[Any]] = [
            UniqueConstraint(
                fields=["membership", "capability"],
                name="platform_rbac_membershipcapgrant_unique",
            ),
        ]
        indexes: ClassVar[list[Any]] = [
            models.Index(fields=["membership"], name="platform_rb_memb_grant_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.membership} {self.grant_type} {self.capability}"
```
