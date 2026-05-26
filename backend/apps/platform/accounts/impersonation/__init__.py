"""Support-impersonation subsystem (M1 D7 Phase 4 + Phase 5).

Phase 4 (this phase) — backend primitives only:
* :class:`apps.platform.accounts.impersonation.models.ImpersonationSession`
* :func:`apps.platform.accounts.impersonation.services.start_impersonation`
* :func:`apps.platform.accounts.impersonation.services.end_impersonation`
* Audit codes ``IMPERSONATION_STARTED``, ``IMPERSONATION_ENDED``,
  ``IMPERSONATION_DENIED``.

Phase 5 will add:
* UI surfaces in the platform console (start / list / end views).
* Integration with the handoff flow (impersonation tokens carry
  the admin's identity through to the tenant session).
* Tenant-side recognition (banner, audit context).

Per the project posture, this is a subpackage that owns its own
models. The ``models.py`` here is imported explicitly from
``apps.platform.accounts.apps.AccountsConfig.ready()`` so Django's
app registry picks it up — without that import, ``makemigrations``
would generate spurious ``DeleteModel`` migrations. Same pattern
as ``oauth/`` and ``handoff/``.
"""

from __future__ import annotations
