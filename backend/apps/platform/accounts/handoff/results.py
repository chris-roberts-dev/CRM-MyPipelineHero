"""HandoffResult dataclass (B.4.12, M1 D6 Phase 2 + M1 D7 Phase 5).

Returned by :func:`consume_handoff_token`. Carries everything
:func:`establish_tenant_session` needs to construct the B.4.14-shaped
tenant-local session.

**M1 D7 Phase 5 — impersonation context.**

Adds the optional ``impersonator_admin_id`` field. When non-None,
the tenant session is an impersonation session and the platform
admin's id is recorded both in the tenant session (so the banner
and middleware can read it) and in the audit metadata. When None,
the handoff is a regular user-initiated tenant entry.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True)
class HandoffResult:
    """Successful handoff token consumption result.

    Field names match the JWT payload claims and the B.4.14 session
    keys. Constructors / fields are intentionally minimal: the
    consume service produces this; the tenant-session establishment
    service writes it into the session dict directly.

    Fields:
        user_id: The User the handoff is for.
        organization_id: The target tenant.
        membership_id: The Membership that authorized the handoff.
        auth_method: One of "password", "oidc", "oauth2", "impersonation"
            per B.4.14.
        auth_provider: provider_code for OAuth/OIDC, else None.
        mfa_satisfied_at: Wall-clock timestamp of when MFA was satisfied
            on the root-domain session. Tenant-side B.4.10 re-auth windows
            compare against this.
        impersonator_admin_id: Platform admin's User id when this is an
            impersonation handoff; None otherwise. M1 D7 Phase 5.
            When set, ``auth_method`` MUST be ``"impersonation"`` (the
            issue service enforces this cross-field invariant). The
            tenant-session establishment service writes this into the
            session as ``mph_session_impersonator_admin_id``.
    """

    user_id: UUID
    organization_id: UUID
    membership_id: UUID
    auth_method: str
    auth_provider: str | None
    mfa_satisfied_at: datetime
    impersonator_admin_id: UUID | None = None
