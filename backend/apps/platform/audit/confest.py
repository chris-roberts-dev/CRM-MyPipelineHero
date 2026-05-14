"""pytest fixtures for audit recording.

Auto-clears the in-memory audit buffer between tests so assertions
about "events emitted by THIS test" stay accurate.
"""

from __future__ import annotations

import pytest

from apps.platform.audit.services import reset_captured_audit_events


@pytest.fixture(autouse=True)
def _reset_audit_buffer() -> None:
    """Clear the per-thread audit event buffer before each test."""
    reset_captured_audit_events()
    yield
    reset_captured_audit_events()
