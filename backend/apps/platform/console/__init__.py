"""Platform console app (M1 D7).

The custom administrative surface mounted at ``/platform/`` per
H.7. This is a CONCRETE consumer of the
:mod:`apps.common.admin` primitives (base views, navigation
registry, shell layout), not part of `apps.common.*` itself —
the console reasons about domain entities (Organization, User,
HandoffSigningKey, ImpersonationSession) and is therefore domain
code.

**What lives here:**

* M1 D7 Phase 1 — URL skeleton + ``PlatformConsoleAccessMixin`` +
  navigation chrome + placeholder views.
* M1 D7 Phase 2 — Read-only org / user surfaces.
* M1 D7 Phase 3 — Handoff signing key management UI.
* M1 D7 Phase 4-5 — Impersonation start / list / end UI.

**What does NOT live here:**

* Base Django admin registrations (those stay in app-local
  ``admin.py`` and remain mounted at ``/django-admin/`` in DEBUG
  only).
* Any state-changing business logic. Console views call into the
  same service functions any other surface would call.
* Tenant-portal views (those live in :mod:`apps.web.tenant_portal`).
"""

from __future__ import annotations
