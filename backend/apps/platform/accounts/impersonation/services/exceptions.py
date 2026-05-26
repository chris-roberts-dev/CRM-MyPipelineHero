"""Typed exceptions for the impersonation service layer (M1 D7 Phase 4).

Fine-grained types per the project's service-layer pattern. Each
validation failure has its own subclass so callers (and tests) can
discriminate without string-matching error messages.
"""

from __future__ import annotations


class ImpersonationError(Exception):
    """Base for all impersonation service-layer errors."""


# ---- Start failures. ----------------------------------------------


class ImpersonationActorNotStaffError(ImpersonationError):
    """The acting admin is not is_staff or is_active.

    Only staff users may initiate impersonation (B.7).
    """


class ImpersonationTargetInvalidError(ImpersonationError):
    """The target user is not a valid impersonation target.

    Covers: user does not exist, is_system, is_staff, or
    is_active is False. B.7's strict interpretation: targets must
    be regular non-staff users.
    """


class ImpersonationMembershipInvalidError(ImpersonationError):
    """The membership does not anchor target+org+ACTIVE status.

    The service requires an ACTIVE Membership matching
    (target_user_id, organization_id, membership_id). Mismatch
    of any of these three values raises this.
    """


class ImpersonationSelfTargetError(ImpersonationError):
    """admin_user_id == target_user_id.

    DB-level check_constraint backs this up; the service raises
    the explicit exception before reaching the DB so the error
    message is human-readable.
    """


class ImpersonationReasonRequiredError(ImpersonationError):
    """The reason field is empty or below the minimum length.

    B.7 requires a recorded business reason. v1 enforces a
    minimum length (10 characters after strip) to discourage
    "test" / "x" / "asdf" placeholders.
    """


class ImpersonationAlreadyActiveError(ImpersonationError):
    """This admin already has an active impersonation session.

    DB-level partial unique index backs this up; the service
    raises the explicit exception early for a nicer error
    message. End the existing session before starting a new one.
    """


# ---- End failures. ------------------------------------------------


class ImpersonationSessionNotFoundError(ImpersonationError):
    """No ImpersonationSession matches the given session_id."""


class ImpersonationSessionAlreadyEndedError(ImpersonationError):
    """The session was already ended (``ended_at IS NOT NULL``)."""
