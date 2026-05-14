"""Project-wide pytest configuration.

Located at ``backend/conftest.py`` so pytest-django discovers it before
any app-level test files.

The fixture below makes the platform-tier seed data (96 capabilities,
11 default role templates, the System User) reliably present at the
start of every test. Without it, tests that use
``@pytest.mark.django_db(transaction=True)`` truncate the test database
between runs and wipe out the data the seed migration originally
installed, causing subsequent test sessions to fail with empty seed
state.

The fixture overrides pytest-django's ``django_db_setup`` so the seed
re-application happens once per session, after Django has finished its
migration setup, and writes outside per-test transaction isolation via
``django_db_blocker.unblock()``.

The seed function itself (``apps.platform.rbac.migrations._seed_runner.
run_seed_v1_now``) is idempotent, so re-applying it across sessions or
re-using a warm DB is safe.
"""

from __future__ import annotations

import pytest


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
