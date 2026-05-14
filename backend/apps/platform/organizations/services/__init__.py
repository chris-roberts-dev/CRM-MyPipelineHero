"""Tenant-organization service layer (M1 D2).

This package will host:

* ``create_organization`` — provision a new tenant, clone the 11
  default role templates to per-tenant Role rows, create the bootstrap
  Owner Membership, and emit the appropriate AuditEvent(s).
* ``suspend_organization`` / ``activate_organization`` — status
  transitions for platform-side org lifecycle management.

Service-layer rules (A.4.4):

* Functions accept primitive arguments (UUIDs, strings, decimals).
  They do not accept request objects.
* Functions are the only sanctioned call site for state-changing ORM
  writes. Direct ``Model.objects.create(...)`` from views/forms/
  signals/admin/management commands is prohibited (with the explicit
  exemptions for admin/migrations/tests/management-commands per A.4.5).
* Functions own their transaction boundaries via
  ``transaction.atomic(...)``.

This file is intentionally empty in M1 D1. The first concrete service
function (``create_organization``) ships in M1 D2 — see the M1
retrospective for the deliverable schedule.
"""
