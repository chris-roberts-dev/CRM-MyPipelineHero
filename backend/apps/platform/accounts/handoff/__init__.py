"""Handoff subsystem (M1 D6).

Cross-subdomain handoff per B.4.11-B.4.17. Phase 1 owns the signing-
key lifecycle; Phase 2 owns token issue/consume; Phases 3-5 wire HTTP
endpoints and per-tenant sessions.
"""

from __future__ import annotations

from apps.platform.accounts.handoff.models import HandoffSigningKey

__all__ = ["HandoffSigningKey"]
