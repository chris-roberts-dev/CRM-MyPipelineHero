"""Tests for MFA satisfaction signal handlers (M1 D6 Phase 4A).

Uses a real Django SessionStore — NOT a plain dict — so the
``modified`` flag behaves the way it does in production. Plain
dicts don't have a ``.modified`` attribute settable in the way
Django's session machinery uses; the prior version's
``request.session = {}`` approach was wrong.
"""

from __future__ import annotations

from datetime import datetime

import pytest
from allauth.mfa.signals import authenticator_added, authenticator_used
from django.contrib.sessions.backends.db import SessionStore
from django.http import HttpRequest
from django.test import RequestFactory

from apps.platform.accounts.signals_mfa import SESSION_KEY_MFA_SATISFIED_AT


def _request_with_session() -> HttpRequest:
    """Build a request with a real Django SessionStore attached.

    Uses the DB session backend so the ``modified`` attribute
    behaves exactly like in production. The session row is never
    saved to DB during these tests — the handler just writes to
    the in-memory ``_session`` cache.
    """
    factory = RequestFactory()
    request = factory.get("/")
    request.session = SessionStore()  # type: ignore[assignment]
    return request


@pytest.mark.django_db
class TestAuthenticatorUsedSignal:
    """authenticator_used → mph_mfa_satisfied_at written."""

    def test_signal_writes_session_key(self) -> None:
        request = _request_with_session()
        authenticator_used.send(
            sender=None,
            request=request,
            user=None,
            authenticator=None,
        )
        assert SESSION_KEY_MFA_SATISFIED_AT in request.session
        value = request.session[SESSION_KEY_MFA_SATISFIED_AT]
        parsed = datetime.fromisoformat(value)
        assert parsed.tzinfo is not None

    def test_signal_sets_session_modified(self) -> None:
        request = _request_with_session()
        # Real SessionStore starts un-modified.
        assert request.session.modified is False
        authenticator_used.send(
            sender=None,
            request=request,
            user=None,
            authenticator=None,
        )
        assert request.session.modified is True


@pytest.mark.django_db
class TestAuthenticatorAddedSignal:
    """authenticator_added → mph_mfa_satisfied_at written."""

    def test_signal_writes_session_key(self) -> None:
        request = _request_with_session()
        authenticator_added.send(
            sender=None,
            request=request,
            user=None,
            authenticator=None,
        )
        assert SESSION_KEY_MFA_SATISFIED_AT in request.session


@pytest.mark.django_db
class TestSignalDefensiveBehavior:
    """Signal handlers don't crash when request is None or has no session."""

    def test_no_request_does_not_crash(self) -> None:
        # Should silently no-op.
        authenticator_used.send(
            sender=None,
            request=None,
            user=None,
            authenticator=None,
        )

    def test_request_without_session_does_not_crash(self) -> None:
        factory = RequestFactory()
        request = factory.get("/")
        # request.session attribute is missing on a raw RequestFactory
        # request — the SessionMiddleware would normally set it but
        # we're calling the signal directly without going through middleware.
        # Signal handler should detect the missing session and no-op.
        authenticator_used.send(
            sender=None,
            request=request,
            user=None,
            authenticator=None,
        )
