"""Smoke tests for /healthz and /readyz (G.4.8)."""

from __future__ import annotations

import pytest
from django.test import Client


@pytest.mark.django_db
def test_healthz_returns_ok() -> None:
    client = Client()
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.django_db
def test_readyz_returns_ok_when_dependencies_up() -> None:
    """In the test environment, DB and cache (locmem) are always reachable."""
    client = Client()
    response = client.get("/readyz")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["checks"]["database"] == "ok"
    assert body["checks"]["cache"] == "ok"
