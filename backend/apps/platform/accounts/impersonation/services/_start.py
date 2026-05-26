"""start_impersonation service (M1 D7 Phase 4, B.7).

Creates an ImpersonationSession row, emits IMPERSONATION_STARTED.
On validation failure, emits IMPERSONATION_DENIED with a reason
code and re-raises the typed exception.

Per project service-layer rules (A.4.4):
* Keyword-only primitive arguments.
* Single ``transaction.atomic()`` for the state change + audit.
* Validation failures also audit (within their own atomic block)
  so security-relevant denials are recorded even though no
  session row is created. Matches the M1 D6 HANDOFF_REPLAY_DETECTED
  / HANDOFF_HOST_MISMATCH precedent.
"""

from __future__ import annotations

import logging
from uuid import UUID

from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction

from apps.platform.accounts.impersonation.models import ImpersonationSession
from apps.platform.accounts.impersonation.services.exceptions import (
    ImpersonationActorNotStaffError,
    ImpersonationAlreadyActiveError,
    ImpersonationMembershipInvalidError,
    ImpersonationReasonRequiredError,
    ImpersonationSelfTargetError,
    ImpersonationTargetInvalidError,
)
from apps.platform.audit.services import audit_emit
from apps.platform.organizations.models import Membership, MembershipStatus

logger = logging.getLogger(__name__)


_MIN_REASON_LENGTH = 10


def start_impersonation(
    *,
    admin_user_id: UUID,
    target_user_id: UUID,
    organization_id: UUID,
    membership_id: UUID,
    reason: str,
) -> ImpersonationSession:
    """Start an impersonation session (B.7)."""
    UserModel = get_user_model()
    reason_clean = (reason or "").strip()

    # Self-target + reason-length checks (cheap, no DB).
    if admin_user_id == target_user_id:
        _audit_denied(
            admin_user_id=admin_user_id,
            target_user_id=target_user_id,
            organization_id=organization_id,
            reason_code="self_target",
        )
        raise ImpersonationSelfTargetError("An admin cannot impersonate themselves.")

    if len(reason_clean) < _MIN_REASON_LENGTH:
        _audit_denied(
            admin_user_id=admin_user_id,
            target_user_id=target_user_id,
            organization_id=organization_id,
            reason_code="reason_required",
        )
        raise ImpersonationReasonRequiredError(
            f"Reason must be at least {_MIN_REASON_LENGTH} characters "
            f"after trimming whitespace; got {len(reason_clean)}."
        )

    # Actor validation.
    try:
        admin = UserModel.objects.get(id=admin_user_id)
    except UserModel.DoesNotExist as exc:
        _audit_denied(
            admin_user_id=admin_user_id,
            target_user_id=target_user_id,
            organization_id=organization_id,
            reason_code="actor_not_found",
        )
        raise ImpersonationActorNotStaffError(
            f"admin_user_id={admin_user_id!r} does not exist"
        ) from exc

    if not (admin.is_staff and admin.is_active):
        _audit_denied(
            admin_user_id=admin_user_id,
            target_user_id=target_user_id,
            organization_id=organization_id,
            reason_code="actor_not_staff_or_inactive",
        )
        raise ImpersonationActorNotStaffError(
            f"admin_user_id={admin_user_id!r} is not an active staff user; "
            "impersonation requires is_staff=True and is_active=True."
        )

    # Target validation.
    try:
        target = UserModel.objects.get(id=target_user_id)
    except UserModel.DoesNotExist as exc:
        _audit_denied(
            admin_user_id=admin_user_id,
            target_user_id=target_user_id,
            organization_id=organization_id,
            reason_code="target_not_found",
        )
        raise ImpersonationTargetInvalidError(
            f"target_user_id={target_user_id!r} does not exist"
        ) from exc

    if not target.is_active:
        _audit_denied(
            admin_user_id=admin_user_id,
            target_user_id=target_user_id,
            organization_id=organization_id,
            reason_code="target_inactive",
        )
        raise ImpersonationTargetInvalidError(
            f"target_user_id={target_user_id!r} is not active; cannot "
            "impersonate an inactive user."
        )

    if getattr(target, "is_system", False):
        _audit_denied(
            admin_user_id=admin_user_id,
            target_user_id=target_user_id,
            organization_id=organization_id,
            reason_code="target_is_system",
        )
        raise ImpersonationTargetInvalidError(
            f"target_user_id={target_user_id!r} is the system user; "
            "cannot impersonate the system user."
        )

    if target.is_staff:
        _audit_denied(
            admin_user_id=admin_user_id,
            target_user_id=target_user_id,
            organization_id=organization_id,
            reason_code="target_is_staff",
        )
        raise ImpersonationTargetInvalidError(
            f"target_user_id={target_user_id!r} is a staff user; v1 "
            "impersonation does not permit staff-on-staff impersonation. "
            "If a senior admin needs to investigate another admin's "
            "session, use audit log review instead."
        )

    # Membership validation.
    try:
        membership = Membership.objects.get(
            id=membership_id,
            user_id=target_user_id,
            organization_id=organization_id,
        )
    except Membership.DoesNotExist as exc:
        _audit_denied(
            admin_user_id=admin_user_id,
            target_user_id=target_user_id,
            organization_id=organization_id,
            reason_code="membership_not_found_or_mismatched",
        )
        raise ImpersonationMembershipInvalidError(
            f"membership_id={membership_id!r} does not match "
            f"(target_user_id={target_user_id!r}, "
            f"organization_id={organization_id!r}), or doesn't exist."
        ) from exc

    if membership.status != MembershipStatus.ACTIVE:
        _audit_denied(
            admin_user_id=admin_user_id,
            target_user_id=target_user_id,
            organization_id=organization_id,
            reason_code="membership_not_active",
        )
        raise ImpersonationMembershipInvalidError(
            f"membership_id={membership_id!r} is not ACTIVE "
            f"(status={membership.status!r}); cannot impersonate via "
            "a non-active membership."
        )

    # Active-session pre-check (DB partial unique index is the
    # authoritative enforcement; this gives a nicer error).
    existing_active = ImpersonationSession.objects.active_for_admin(admin_user_id)
    if existing_active is not None:
        _audit_denied(
            admin_user_id=admin_user_id,
            target_user_id=target_user_id,
            organization_id=organization_id,
            reason_code="admin_already_impersonating",
        )
        raise ImpersonationAlreadyActiveError(
            f"admin_user_id={admin_user_id!r} already has an active "
            f"impersonation session (id={existing_active.id!r}); end "
            "it before starting a new one."
        )

    # Create the session row + emit audit. Catch IntegrityError
    # from the race window between active-session check and insert.
    try:
        with transaction.atomic():
            session = ImpersonationSession.objects.create(
                admin_user_id=admin_user_id,
                target_user_id=target_user_id,
                organization_id=organization_id,
                membership_id=membership_id,
                reason=reason_clean,
            )

            audit_emit(
                "IMPERSONATION_STARTED",
                actor_id=admin_user_id,
                organization_id=organization_id,
                object_kind="platform_accounts.ImpersonationSession",
                object_id=str(session.id),
                on_behalf_of_id=target_user_id,
                metadata={
                    "target_user_id": str(target_user_id),
                    "membership_id": str(membership_id),
                    "reason_length": len(reason_clean),
                    # Reason text NOT in metadata — canonical
                    # source is the session row.
                },
            )

            return session
    except IntegrityError as exc:
        # Race: another transaction created an active session for
        # this admin between our pre-check and our insert. Partial
        # unique index rejected our insert.
        _audit_denied(
            admin_user_id=admin_user_id,
            target_user_id=target_user_id,
            organization_id=organization_id,
            reason_code="admin_already_impersonating_race",
        )
        raise ImpersonationAlreadyActiveError(
            f"admin_user_id={admin_user_id!r} concurrently started "
            "another impersonation session."
        ) from exc


def _audit_denied(
    *,
    admin_user_id: UUID,
    target_user_id: UUID,
    organization_id: UUID,
    reason_code: str,
) -> None:
    """Emit IMPERSONATION_DENIED inside its own atomic block."""
    with transaction.atomic():
        audit_emit(
            "IMPERSONATION_DENIED",
            actor_id=admin_user_id,
            organization_id=organization_id,
            object_kind="platform_accounts.User",
            object_id=str(target_user_id),
            metadata={
                "reason_code": reason_code,
                "target_user_id": str(target_user_id),
            },
        )
