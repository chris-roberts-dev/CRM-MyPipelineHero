"""Top-level Django project package for MyPipelineHero.

Exposes the Celery app at module load so workers can pick it up via
``celery -A apps.common.celery worker`` and so ``shared_task`` decorators
register correctly.
"""

from __future__ import annotations

from apps.common.celery import app as celery_app

__all__ = ("celery_app",)
