"""Smoke tests for the M0 login-page scaffold (H.3.4, J.2.3)."""

from __future__ import annotations

import pytest
from django.test import Client


@pytest.mark.django_db
def test_login_page_renders() -> None:
    client = Client()
    response = client.get("/login/")
    assert response.status_code == 200


@pytest.mark.django_db
def test_login_page_uses_auth_body_classes() -> None:
    """H.8.5 requires the auth body classes on /login/."""
    client = Client()
    response = client.get("/login/")
    assert response.status_code == 200
    assert b"mph-public-body" in response.content
    assert b"mph-auth-body" in response.content


@pytest.mark.django_db
def test_login_post_does_not_authenticate_in_m0() -> None:
    """M0 deliberately does not authenticate. M1 replaces this view."""
    client = Client()
    response = client.post(
        "/login/",
        data={"email": "anyone@example.com", "password": "irrelevant"},
    )
    # Form re-renders with a non-field error explaining M0 state.
    assert response.status_code == 200
    assert b"M1" in response.content or b"not yet wired up" in response.content
