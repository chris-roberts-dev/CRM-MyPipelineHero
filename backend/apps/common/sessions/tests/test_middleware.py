"""Tests for PerTenantSessionMiddleware (M1 D6 Phase 3, B.4.14).

These tests intentionally use a test-only URL that explicitly writes to
``request.session``.

Previously these tests used ``/accounts/login/`` because allauth's login
GET was assumed to touch the session. In the current app behavior, that
request only sets the CSRF cookie and does not write a session cookie, so
it is not a reliable way to test session-cookie middleware.

The goal here is to test the middleware behavior once Django actually has
a modified session to persist.
"""

from __future__ import annotations

import pytest
from django.http import HttpRequest, HttpResponse
from django.test import Client
from django.urls import clear_url_caches, path

pytestmark = pytest.mark.django_db


# ---------------------------------------------------------------------------
# Test-only URLConf
# ---------------------------------------------------------------------------


def touch_session_view(request: HttpRequest) -> HttpResponse:
    """Force Django to create/write a session cookie."""
    request.session["touched"] = True
    return HttpResponse("ok")


urlpatterns = [
    path("__test__/touch-session/", touch_session_view),
]

_SESSION_TOUCHING_PATH = "/__test__/touch-session/"


@pytest.fixture(autouse=True)
def use_test_urlconf(settings):
    """Point these tests at the test-only URLConf in this module."""
    settings.ROOT_URLCONF = __name__
    clear_url_caches()
    yield
    clear_url_caches()


# ---------------------------------------------------------------------------
# Cookie name correctness — the core B.4.14 property.
# ---------------------------------------------------------------------------


class TestCookieNamePerHost:
    """The Set-Cookie header carries the right name for the request host."""

    def test_root_domain_request_writes_mph_root_session(self) -> None:
        client = Client(HTTP_HOST="mph.local")
        response = client.get(_SESSION_TOUCHING_PATH)

        assert response.status_code == 200

        cookie_names = list(client.cookies)
        assert (
            "mph_root_session" in cookie_names
        ), f"Expected mph_root_session cookie, got {cookie_names!r}"

        tenant_cookies = [c for c in cookie_names if c.startswith("tenant_session_")]
        assert tenant_cookies == [], (
            f"Root domain request must not write tenant_session_* cookie, "
            f"got {tenant_cookies!r}"
        )

    def test_tenant_subdomain_request_writes_tenant_session_acme(self) -> None:
        client = Client(HTTP_HOST="acme.mph.local")
        response = client.get(_SESSION_TOUCHING_PATH)

        assert response.status_code == 200

        cookie_names = list(client.cookies)
        assert (
            "tenant_session_acme" in cookie_names
        ), f"Expected tenant_session_acme cookie, got {cookie_names!r}"

    def test_testserver_request_writes_default_cookie(self) -> None:
        # No HTTP_HOST → default "testserver". Falls to OTHER/root scope.
        client = Client()
        response = client.get(_SESSION_TOUCHING_PATH)

        assert response.status_code == 200
        assert "mph_root_session" in client.cookies


# ---------------------------------------------------------------------------
# Cookie isolation — the B.4.14 "PROHIBITED shared parent-domain" property.
# ---------------------------------------------------------------------------


class TestCookieDomainScoping:
    """A cookie's Domain attribute must NOT span the parent domain."""

    def test_root_cookie_has_no_domain_attribute(self) -> None:
        client = Client(HTTP_HOST="mph.local")
        response = client.get(_SESSION_TOUCHING_PATH)

        assert response.status_code == 200

        morsel = client.cookies.get("mph_root_session")
        assert morsel is not None

        # No domain attribute → browser scopes to exact host.
        assert morsel["domain"] in ("", None), (
            f"Root session cookie must have no Domain attribute; got "
            f"domain={morsel['domain']!r}"
        )

    def test_tenant_cookie_domain_is_exact_tenant_host(self) -> None:
        client = Client(HTTP_HOST="acme.mph.local")
        response = client.get(_SESSION_TOUCHING_PATH)

        assert response.status_code == 200

        morsel = client.cookies.get("tenant_session_acme")
        assert morsel is not None

        # Exact-host Domain attribute, per B.4.14.
        assert morsel["domain"] == "acme.mph.local", (
            f"Tenant session cookie must scope to exact host; got "
            f"domain={morsel['domain']!r}"
        )


# ---------------------------------------------------------------------------
# Session isolation — same browser, different hosts, different session keys.
# ---------------------------------------------------------------------------


class TestSessionIsolationBetweenHosts:
    """Sessions established on root vs. tenant must not bleed into each other."""

    def test_two_clients_two_different_session_keys(self) -> None:
        root_client = Client(HTTP_HOST="mph.local")
        tenant_client = Client(HTTP_HOST="acme.mph.local")

        root_response = root_client.get(_SESSION_TOUCHING_PATH)
        tenant_response = tenant_client.get(_SESSION_TOUCHING_PATH)

        assert root_response.status_code == 200
        assert tenant_response.status_code == 200

        root_morsel = root_client.cookies.get("mph_root_session")
        tenant_morsel = tenant_client.cookies.get("tenant_session_acme")

        assert root_morsel is not None
        assert tenant_morsel is not None
        assert root_morsel.value != tenant_morsel.value, (
            "Distinct hosts must produce distinct session keys — they share "
            "a backend table but the cookies, and therefore the session rows, "
            "are independent."
        )
