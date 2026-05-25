"""Tests for HostUrlconfMiddleware (M1 D6 Phase 4A)."""

from __future__ import annotations

from typing import Any

import pytest
from django.http import HttpRequest, HttpResponse
from django.test import Client


@pytest.fixture(autouse=True)
def _enable_host_routing(settings: Any) -> None:
    """Enable HostUrlconfMiddleware for every test in this module."""
    settings.MPH_HOST_URLCONF_ROUTING_ENABLED = True


@pytest.mark.django_db
class TestHostUrlconfRouting:
    """Each host scope resolves to the correct URLconf."""

    def test_root_host_resolves_root_urlconf(self) -> None:
        """Root-domain request can reach allauth login (root-only route)."""
        client = Client(HTTP_HOST="mph.local")
        response = client.get("/accounts/login/")
        assert response.status_code == 200

    def test_tenant_host_cannot_reach_root_routes(self) -> None:
        """Tenant subdomain returns 404 for root-only routes like allauth."""
        client = Client(HTTP_HOST="acme.mph.local")
        response = client.get("/accounts/login/")
        # 404 because urls_tenant doesn't include allauth.
        assert response.status_code == 404

    def test_testserver_falls_through_to_root_urlconf(self) -> None:
        """Tests using default testserver host fall through to ROOT_URLCONF."""
        client = Client()
        response = client.get("/accounts/login/")
        assert response.status_code == 200

    def test_landing_page_root_and_tenant_both_resolve(self) -> None:
        """Landing routing differs by host.

        Root domain serves the marketing landing page (200).
        Tenant subdomain serves the tenant landing — which, for an
        unauthenticated visitor with no tenant session, redirects to
        the root-domain picker (302 to mph.local/select-org/).
        """
        root_client = Client(HTTP_HOST="mph.local")
        tenant_client = Client(HTTP_HOST="acme.mph.local")

        root_response = root_client.get("/")
        tenant_response = tenant_client.get("/")

        # Root: 200 (landing).
        assert root_response.status_code == 200
        # Tenant: 302 redirect to root picker (no tenant session).
        assert tenant_response.status_code == 302
        assert "/select-org/" in tenant_response["Location"]


@pytest.mark.django_db
class TestHostUrlconfDefensiveFallback:
    """When _mph_session_scope is missing, middleware falls through cleanly."""

    def test_falls_through_when_scope_attribute_missing(self) -> None:
        """Direct middleware invocation without session-scope attribute."""
        from apps.common.sessions.middleware import HostUrlconfMiddleware

        def get_response(request: HttpRequest) -> HttpResponse:
            urlconf = getattr(request, "urlconf", None)
            return HttpResponse(f"urlconf={urlconf}")

        middleware = HostUrlconfMiddleware(get_response)
        request = HttpRequest()
        response = middleware(request)
        assert response.content == b"urlconf=None"
