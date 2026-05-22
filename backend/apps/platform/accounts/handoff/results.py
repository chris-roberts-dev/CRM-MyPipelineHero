"""HandoffResult dataclass (B.4.12, M1 D6 Phase 2).

Returned by :func:`consume_handoff_token`. Carries everything
:func:`establish_tenant_session` (Phase 4) needs to construct the
B.4.14-shaped tenant-local session.
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
        auth_provider: Provider_code for OAuth/OIDC, else None.
        mfa_satisfied_at: Wall-clock timestamp of when MFA was satisfied
            on the root-domain session. Tenant-side B.4.10 re-auth windows
            compare against this.
    """

    user_id: UUID
    organization_id: UUID
    membership_id: UUID
    auth_method: str
    auth_provider: str | None
    mfa_satisfied_at: datetime
