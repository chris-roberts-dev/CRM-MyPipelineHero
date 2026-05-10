"""Celery application for MyPipelineHero.

Importable as ``apps.common.celery:app`` (and re-exported from the project
root as ``celery_app`` in ``config/__init__.py``).

Run worker:

    celery -A apps.common.celery worker -Q critical,default,bulk,reports -l info

Run beat:

    celery -A apps.common.celery beat -l info --schedule=/tmp/celerybeat-schedule
"""

from __future__ import annotations

import os

from celery import Celery

# Default to dev settings if none provided. Production deployments override.
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")

app: Celery = Celery("mph")

# Read Celery config from Django settings under the CELERY_ namespace.
app.config_from_object("django.conf:settings", namespace="CELERY")

# Auto-discover tasks declared in any installed Django app.
app.autodiscover_tasks()


@app.task(bind=True, ignore_result=True)
def debug_task(self) -> None:  # type: ignore[no-untyped-def]
    """Smoke-test task. Useful for verifying broker connectivity in M0."""
    print(f"Celery debug_task fired. Request: {self.request!r}")
