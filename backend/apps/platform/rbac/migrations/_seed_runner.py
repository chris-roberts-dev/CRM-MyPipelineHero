"""Re-runnable seed helper used by idempotency tests.

This module exposes the seed body in a form that can be invoked outside
the migration framework so tests can assert idempotency without
unmigrating the database.

Migration module names start with digits (``0002_seed_v1``) which is
illegal as a Python identifier, so we import via ``importlib`` and pull
the seed function off the module object directly.

Production code MUST NOT call ``run_seed_v1_now()``. The function is
test-scoped infrastructure.
"""

from __future__ import annotations

import importlib

from django.apps import apps as django_apps


def run_seed_v1_now() -> None:
    """Re-execute the seed_v1 body against the current DB state."""
    module = importlib.import_module("apps.platform.rbac.migrations.0002_seed_v1")
    module.seed_v1(django_apps, None)
