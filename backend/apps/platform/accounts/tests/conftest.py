"""Accounts-app conftest (M1 D4).

Intentionally near-empty. Auth fixtures (``user_factory``,
``user_with_totp``, etc.) and the audit-buffer reset autouse were
promoted to ``backend/conftest.py`` so tests in any directory can
reference them. Pure helpers live in
``apps/platform/accounts/tests/_helpers.py``.

This module is retained as an explicit marker so a future engineer
looking for "where are the accounts test fixtures defined?" sees
this docstring rather than searching upward.
"""

from __future__ import annotations
