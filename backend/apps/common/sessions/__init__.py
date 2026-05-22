"""Per-tenant session middleware (M1 D6 Phase 3).

Implements B.4.14: cookies are scoped per host so root-domain and
tenant-subdomain sessions are independent. ``PerTenantSessionMiddleware``
replaces Django's standard ``SessionMiddleware`` in ``MIDDLEWARE``.
"""

from __future__ import annotations

from apps.common.sessions.host_resolution import (
    HostScope,
    SessionScope,
    resolve_session_scope,
)

__all__ = ["HostScope", "SessionScope", "resolve_session_scope"]
