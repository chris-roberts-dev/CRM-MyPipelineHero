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
