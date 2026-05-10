"""Smoke tests for the public landing page (H.3.3, J.2.4 #7)."""

from __future__ import annotations

import pytest
from django.test import Client


@pytest.mark.django_db
def test_landing_page_renders_at_root() -> None:
    client = Client()
    response = client.get("/")
    assert response.status_code == 200


@pytest.mark.django_db
def test_landing_page_links_to_login() -> None:
    client = Client()
    response = client.get("/")
    assert response.status_code == 200
    assert b'href="/login/"' in response.content


@pytest.mark.django_db
def test_landing_page_uses_public_body_class() -> None:
    """H.8.5 requires the ``mph-public-body`` class on the landing page."""
    client = Client()
    response = client.get("/")
    assert response.status_code == 200
    assert b"mph-public-body" in response.content
