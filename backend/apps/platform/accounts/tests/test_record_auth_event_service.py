"""Tests for record_auth_event (M1 D4).

This is the thin service wrapper around audit_emit that allauth signal
handlers call. It must:
- Open its own atomic boundary.
- Re-raise programming errors (UnknownAuditEventError,
  AuditOutsideTransactionError).
- Swallow other exceptions so an audit hiccup never breaks auth.
"""

from __future__ import annotations

from typing import Any
from unittest import mock
from uuid import uuid4

import pytest

from apps.platform.accounts.services import record_auth_event
from apps.platform.audit.services import (
    AuditOutsideTransactionError,
    UnknownAuditEventError,
    captured_audit_events,
)


@pytest.mark.django_db
class TestRecordAuthEvent:
    def test_opens_own_transaction_and_emits(self) -> None:
        actor_id = uuid4()
        record_auth_event(
            event_type="LOGIN_SUCCEEDED",
            actor_id=actor_id,
            metadata={"method": "test"},
        )
        events = captured_audit_events(event_type="LOGIN_SUCCEEDED")
        assert len(events) == 1
        assert events[0].actor_id == actor_id

    def test_unknown_event_type_re_raises(self) -> None:
        with pytest.raises(UnknownAuditEventError):
            record_auth_event(
                event_type="DEFINITELY_NOT_A_REAL_EVENT",
                actor_id=uuid4(),
            )

    def test_audit_outside_transaction_re_raises(self) -> None:
        """If our own atomic boundary fails to open, surface that as a bug."""
        with mock.patch(
            "apps.platform.accounts.services._audit.transaction.atomic",
            side_effect=AuditOutsideTransactionError("simulated"),
        ):
            with pytest.raises(AuditOutsideTransactionError):
                record_auth_event(
                    event_type="LOGIN_SUCCEEDED",
                    actor_id=uuid4(),
                )

    def test_generic_exception_is_swallowed(self, caplog: Any) -> None:
        """An unexpected exception in the audit path must NOT break auth."""
        with mock.patch(
            "apps.platform.accounts.services._audit.audit_emit",
            side_effect=RuntimeError("unexpected"),
        ):
            # Must not raise.
            record_auth_event(
                event_type="LOGIN_SUCCEEDED",
                actor_id=uuid4(),
            )

        # And we should have logged the swallow at WARNING.
        warnings = [r for r in caplog.records if r.levelname == "WARNING"]
        assert any("record_auth_event failed" in r.message for r in warnings)
