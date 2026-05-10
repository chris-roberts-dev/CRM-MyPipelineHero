from __future__ import annotations

from django.apps import AppConfig


class OutboxConfig(AppConfig):
    name = "apps.common.outbox"
    label = "common_outbox"
    verbose_name = "Common · Outbox"
