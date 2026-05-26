"""end_impersonation service (M1 D7 Phase 4, B.7).

Closes an active ImpersonationSession by setting ``ended_at``,
``ended_by_user``, and ``end_reason``. Emits IMPERSONATION_ENDED.

Per project service-layer rules (A.4.4):
* Keyword-only primitive arguments.
* Single ``transaction.atomic()`` for the state change + audit.
* SELECT FOR UPDATE locks the session row to prevent concurrent
  end-calls from both succeeding.
"""

from __future__ import annotations

import logging
from uuid import UUID

from django.db import transaction
from django.utils import timezone

from apps.platform.accounts.impersonation.models import (
    ImpersonationEndReason,
    ImpersonationSession,
)
from apps.platform.accounts.impersonation.services.exceptions import (
    ImpersonationSessionAlreadyEndedError,
    ImpersonationSessionNotFoundError,
)
from apps.platform.audit.services import audit_emit

logger = logging.getLogger(__name__)


def end_impersonation(
    *,
    session_id: UUID,
    ended_by_user_id: UUID,
    end_reason: str = ImpersonationEndReason.ADMIN_ENDED,
) -> ImpersonationSession:
    """End an impersonation session (B.7).

    Args:
        session_id: ImpersonationSession.id.
        ended_by_user_id: User ending the session. Can be the
            original admin OR a different staff user (e.g. senior
            admin ending someone else's runaway session). The
            audit event records who.
        end_reason: One of ImpersonationEndReason.choices. Default
            is ADMIN_ENDED. Phase 5 logout-driven end will pass
            ImpersonationEndReason.LOGOUT.

    Returns:
        The updated (now-ended) ImpersonationSession.

    Raises:
        ImpersonationSessionNotFoundError
        ImpersonationSessionAlreadyEndedError
    """
    with transaction.atomic():
        # SELECT FOR UPDATE — concurrent end-calls serialize and
        # the second one finds the session already ended.
        try:
            session = ImpersonationSession.objects.select_for_update().get(
                id=session_id
            )
        except ImpersonationSession.DoesNotExist as exc:
            raise ImpersonationSessionNotFoundError(
                f"No ImpersonationSession with id={session_id!r}"
            ) from exc

        if session.ended_at is not None:
            raise ImpersonationSessionAlreadyEndedError(
                f"ImpersonationSession id={session_id!r} was already "
                f"ended at {session.ended_at!r} by user "
                f"{session.ended_by_user_id!r}."
            )

        # Validate end_reason against the choices.
        valid_reasons = {value for value, _ in ImpersonationEndReason.choices}
        if end_reason not in valid_reasons:
            raise ValueError(
                f"end_reason={end_reason!r} is not one of " f"{sorted(valid_reasons)!r}"
            )

        now = timezone.now()
        session.ended_at = now
        session.ended_by_user_id = ended_by_user_id
        session.end_reason = end_reason
        session.save(update_fields=["ended_at", "ended_by_user", "end_reason"])

        audit_emit(
            "IMPERSONATION_ENDED",
            actor_id=ended_by_user_id,
            organization_id=session.organization_id,
            object_kind="platform_accounts.ImpersonationSession",
            object_id=str(session.id),
            on_behalf_of_id=session.target_user_id,
            metadata={
                "admin_user_id": str(session.admin_user_id),
                "target_user_id": str(session.target_user_id),
                "end_reason": end_reason,
                "duration_seconds": int((now - session.started_at).total_seconds()),
            },
        )

        return session
