"""Platform-tier audit event subsystem (G.5).

The full ``AuditEvent`` partitioned model lands in M2 (J.4 — RBAC + Audit).
In M1, this app exposes the ``audit_emit`` interface as a stub so that
service-layer code can adopt the audit contract without waiting for the
storage layer.

Public API:

* :func:`audit_emit` — emit an audit event. In M1 this is a stub that
  validates a transaction is open and records the event in-memory when
  recording is enabled (for tests). The real implementation inserts a
  partitioned ``AuditEvent`` row.

The contract is documented in G.5.3. Services that wire through this
interface today will continue to work unchanged when the M2 storage
backend lands.
"""

from __future__ import annotations

from apps.platform.audit.services import (
    AuditEvent,
    audit_emit,
    captured_audit_events,
    is_audit_recording_enabled,
)

__all__ = [
    "AuditEvent",
    "audit_emit",
    "captured_audit_events",
    "is_audit_recording_enabled",
]
