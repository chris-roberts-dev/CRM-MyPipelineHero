"""Dev-only Django admin registrations for platform_organizations.

Registrations live in ``apps.platform.accounts.admin`` so the order of
imports matches the order of model registration. This file exists only
to be discovered by Django's admin autoloader; it intentionally
contains no registrations of its own.
"""

from __future__ import annotations
