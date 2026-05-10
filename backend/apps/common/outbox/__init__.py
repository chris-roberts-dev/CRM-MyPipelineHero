"""Outbox pattern primitives (A.3.5, G.3).

Phase 1: app skeleton only — concrete OutboxEntry, dispatcher, and
task bridge land in M1.
"""

default_app_config = "apps.common.outbox.apps.OutboxConfig"
