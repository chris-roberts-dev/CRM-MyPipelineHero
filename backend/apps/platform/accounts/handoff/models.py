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
