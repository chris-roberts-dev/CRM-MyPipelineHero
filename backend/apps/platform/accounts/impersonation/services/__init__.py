"""Impersonation services (M1 D7 Phase 4).

Two services:
* :func:`start_impersonation` — create a session, audit STARTED.
* :func:`end_impersonation` — close a session, audit ENDED.

Both follow the project service-layer rules (A.4.4):
* Keyword-only primitive arguments.
* Own ``transaction.atomic()`` boundary.
* Audit emission inside the boundary.
* Validation failures audit ``IMPERSONATION_DENIED`` with a reason
  code before re-raising the typed exception.
"""

from __future__ import annotations

from apps.platform.accounts.impersonation.services._end import end_impersonation
from apps.platform.accounts.impersonation.services._start import (
    start_impersonation,
)
from apps.platform.accounts.impersonation.services.exceptions import (
    ImpersonationActorNotStaffError,
    ImpersonationAlreadyActiveError,
    ImpersonationError,
    ImpersonationMembershipInvalidError,
    ImpersonationReasonRequiredError,
    ImpersonationSelfTargetError,
    ImpersonationSessionAlreadyEndedError,
    ImpersonationSessionNotFoundError,
    ImpersonationTargetInvalidError,
)

__all__ = [
    "start_impersonation",
    "end_impersonation",
    # Exception hierarchy
    "ImpersonationError",
    "ImpersonationActorNotStaffError",
    "ImpersonationAlreadyActiveError",
    "ImpersonationMembershipInvalidError",
    "ImpersonationReasonRequiredError",
    "ImpersonationSelfTargetError",
    "ImpersonationSessionAlreadyEndedError",
    "ImpersonationSessionNotFoundError",
    "ImpersonationTargetInvalidError",
]
