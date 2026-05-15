"""Project-wide pytest configuration.

Located at ``backend/conftest.py`` so pytest-django discovers it before
any app-level test files.

Houses:

1. ``django_db_setup`` override (existing) — re-applies the platform
   seed (96 capabilities, 11 default role templates, the System User)
   once per session so tests see consistent seed state even after
   transactional truncation.

2. Auth fixtures (M1 D4) — promoted from
   ``apps/platform/accounts/tests/conftest.py`` so tests in any
   directory can reference them. The fixtures cover the User-with-no-
   MFA, User-with-TOTP, and User-with-TOTP-plus-recovery-codes states
   used by the allauth template smoke suite and the signal/middleware
   tests.

3. ``_reset_audit_buffer`` autouse fixture (M1 D4) — promoted from
   ``apps/platform/audit/conftest.py``. Clears the in-memory audit
   buffer before AND after each test so audit-emission assertions
   don't accumulate events across tests. The original
   ``apps/platform/audit/conftest.py`` is intentionally retained so
   the buffer-reset wiring stays visible in the audit app, even
   though it now runs redundantly (the double-clear is free).

Pure helper functions used by tests (``totp_code_for``,
``_install_totp_authenticator``, ``_install_recovery_codes``) live in
``apps/platform/accounts/tests/_helpers.py`` so test code can import
them. Conftest is not a regular Python module and cannot host
importable helpers.
"""

from __future__ import annotations

from typing import Any

import pytest
from apps.platform.accounts.tests._helpers import (
    TEST_TOTP_SECRET,
    _install_recovery_codes,
    _install_totp_authenticator,
)

# ---------------------------------------------------------------------------
# Session-scoped: re-apply platform seed (existing).
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def django_db_setup(django_db_setup, django_db_blocker):
    """Ensure platform seed data is present after Django sets up the test DB.

    pytest-django's default ``django_db_setup`` runs Django migrations,
    which DOES run the ``seed_v1`` data migration. However, tests marked
    with ``transaction=True`` truncate the database between runs (NOT
    rollback), wiping the seed rows. On the next session, Django
    fast-paths through the migration setup if the schema is already in
    place — so the seed data does not get re-applied.

    This override re-runs the idempotent seed function explicitly so
    the seed state is guaranteed at the start of every session,
    regardless of what previous transactional tests did to the DB.
    """
    from apps.platform.rbac.migrations._seed_runner import run_seed_v1_now

    with django_db_blocker.unblock():
        run_seed_v1_now()


# ---------------------------------------------------------------------------
# Autouse: reset the audit buffer (M1 D4 promotion).
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _reset_audit_buffer() -> Any:
    """Clear the in-memory audit buffer before AND after every test.

    The M1 audit stub stashes emitted events in a thread-local list so
    tests can assert emission. Without this autouse, events leak
    across tests and assertions like ``len(events) == 1`` see stale
    rows from earlier tests.

    Originally defined as an autouse in ``apps/platform/audit/conftest.py``
    where it only fired for tests under that app. Promoted to the
    project-wide conftest in M1 D4 so the new accounts/auth_portal
    test suites also benefit.
    """
    from apps.platform.audit.services import reset_captured_audit_events

    reset_captured_audit_events()
    yield
    reset_captured_audit_events()


# ---------------------------------------------------------------------------
# Auth fixtures (M1 D4 promotion from apps/platform/accounts/tests/conftest.py).
# ---------------------------------------------------------------------------


@pytest.fixture
def user_factory(db: Any) -> Any:
    """Factory for canonical Users with a configurable EmailAddress row.

    Returns a callable ``make_user(*, email, password=None,
    verified=True, is_staff=False)`` that creates a User and the
    associated allauth EmailAddress (verified by default).

    Depends on ``db`` so tests using this fixture automatically get
    pytest-django's per-test transaction isolation. The session-scoped
    seed is untouched.
    """
    from allauth.account.models import EmailAddress
    from django.contrib.auth import get_user_model

    User = get_user_model()

    def _make(
        *,
        email: str,
        password: str | None = "test-password-1234!",
        verified: bool = True,
        is_staff: bool = False,
    ) -> Any:
        user = User.objects.create_user(
            email=email,
            password=password,
            is_active=True,
            is_staff=is_staff,
        )
        EmailAddress.objects.create(
            user=user,
            email=email,
            verified=verified,
            primary=True,
        )
        return user

    return _make


@pytest.fixture
def user_unverified(user_factory: Any) -> Any:
    """A user whose primary EmailAddress is NOT verified."""
    return user_factory(email="unverified@example.test", verified=False)


@pytest.fixture
def user_verified_no_mfa(user_factory: Any) -> Any:
    """A verified user with no TOTP enrolled.

    This is the state that triggers ``RequireMfaEnrollmentMiddleware``
    to redirect to ``/accounts/2fa/totp/activate/``.
    """
    return user_factory(email="verified-nomfa@example.test", verified=True)


@pytest.fixture
def totp_secret() -> str:
    """The shared TOTP secret used by fixture-built authenticators."""
    return TEST_TOTP_SECRET


@pytest.fixture
def user_with_totp(user_factory: Any, totp_secret: str) -> Any:
    """A verified user with a TOTP Authenticator row already installed.

    Bypasses allauth's enrollment view; appropriate for tests asserting
    post-enrollment behavior (template rendering, middleware
    pass-through). The end-to-end MFA test uses the real enrollment
    flow to exercise allauth's view itself.
    """
    user = user_factory(email="with-totp@example.test", verified=True)
    _install_totp_authenticator(user, totp_secret)
    return user


@pytest.fixture
def user_with_totp_and_recovery(user_with_totp: Any) -> Any:
    """A verified user with TOTP + a recovery-codes Authenticator row.

    Recovery codes here are seeded raw for template-rendering smoke
    purposes. Tests that need allauth-wrapper-readable codes
    (single-use enforcement) use the real generate view.
    """
    _install_recovery_codes(user_with_totp)
    return user_with_totp
