"""Tests for host → session scope resolution (M1 D6 Phase 3)."""

from __future__ import annotations

import pytest
from django.test import override_settings

from apps.common.sessions.host_resolution import (
    HostScope,
    resolve_session_scope,
)


class TestRootDomain:
    @override_settings(
        MPH_ROOT_DOMAIN="mph.local",
        MPH_TENANT_DOMAIN_TEMPLATE="{slug}.mph.local",
        SESSION_COOKIE_NAME="mph_root_session",
    )
    def test_root_domain_returns_root_scope(self) -> None:
        scope = resolve_session_scope("mph.local")
        assert scope.host_scope == HostScope.ROOT
        assert scope.cookie_name == "mph_root_session"
        assert scope.cookie_domain is None  # browser default = exact host
        assert scope.tenant_slug is None

    @override_settings(
        MPH_ROOT_DOMAIN="mph.local",
        MPH_TENANT_DOMAIN_TEMPLATE="{slug}.mph.local",
        SESSION_COOKIE_NAME="mph_root_session",
    )
    def test_root_domain_with_port_stripped(self) -> None:
        # Caller is supposed to strip port, but defense-in-depth: the
        # resolver also strips.
        scope = resolve_session_scope("mph.local:8000")
        assert scope.host_scope == HostScope.ROOT

    @override_settings(
        MPH_ROOT_DOMAIN="mph.local",
        MPH_TENANT_DOMAIN_TEMPLATE="{slug}.mph.local",
        SESSION_COOKIE_NAME="mph_root_session",
    )
    def test_root_domain_case_insensitive(self) -> None:
        scope = resolve_session_scope("MPH.Local")
        assert scope.host_scope == HostScope.ROOT


class TestTenantSubdomain:
    @override_settings(
        MPH_ROOT_DOMAIN="mph.local",
        MPH_TENANT_DOMAIN_TEMPLATE="{slug}.mph.local",
    )
    def test_tenant_subdomain_returns_tenant_scope(self) -> None:
        scope = resolve_session_scope("acme.mph.local")
        assert scope.host_scope == HostScope.TENANT
        assert scope.cookie_name == "tenant_session_acme"
        assert scope.cookie_domain == "acme.mph.local"
        assert scope.tenant_slug == "acme"

    @override_settings(
        MPH_ROOT_DOMAIN="mph.local",
        MPH_TENANT_DOMAIN_TEMPLATE="{slug}.mph.local",
    )
    def test_tenant_subdomain_with_hyphen(self) -> None:
        scope = resolve_session_scope("acme-corp.mph.local")
        assert scope.host_scope == HostScope.TENANT
        assert scope.cookie_name == "tenant_session_acme-corp"
        assert scope.tenant_slug == "acme-corp"

    @override_settings(
        MPH_ROOT_DOMAIN="mph.local",
        MPH_TENANT_DOMAIN_TEMPLATE="{slug}.mph.local",
    )
    def test_tenant_subdomain_case_insensitive_normalized(self) -> None:
        # DNS hostnames are case-insensitive (RFC 4343). The resolver
        # lowercases before classification — UPPER.mph.local is
        # equivalent to upper.mph.local and IS a valid tenant
        # subdomain referencing the 'upper' slug.
        scope = resolve_session_scope("UPPER.mph.local")
        assert scope.host_scope == HostScope.TENANT
        assert scope.tenant_slug == "upper"
        assert scope.cookie_name == "tenant_session_upper"

    @override_settings(
        MPH_ROOT_DOMAIN="mph.local",
        MPH_TENANT_DOMAIN_TEMPLATE="{slug}.mph.local",
    )
    def test_tenant_subdomain_invalid_slug_falls_to_other(self) -> None:
        # Slug regex demands ^[a-z][a-z0-9-]{1,61}[a-z0-9]$ — a leading
        # digit fails. The resolver downgrades these to OTHER.
        scope = resolve_session_scope("1leading.mph.local")
        assert scope.host_scope == HostScope.OTHER


class TestOtherHost:
    @override_settings(
        MPH_ROOT_DOMAIN="mph.local",
        MPH_TENANT_DOMAIN_TEMPLATE="{slug}.mph.local",
        SESSION_COOKIE_NAME="mph_root_session",
    )
    def test_testserver_returns_other(self) -> None:
        scope = resolve_session_scope("testserver")
        assert scope.host_scope == HostScope.OTHER
        # OTHER falls back to the global default cookie name.
        assert scope.cookie_name == "mph_root_session"
        assert scope.cookie_domain is None
        assert scope.tenant_slug is None

    @override_settings(
        MPH_ROOT_DOMAIN="mph.local",
        MPH_TENANT_DOMAIN_TEMPLATE="{slug}.mph.local",
        SESSION_COOKIE_NAME="mph_root_session",
    )
    def test_localhost_returns_other(self) -> None:
        scope = resolve_session_scope("localhost")
        assert scope.host_scope == HostScope.OTHER

    @override_settings(
        MPH_ROOT_DOMAIN="mph.local",
        MPH_TENANT_DOMAIN_TEMPLATE="{slug}.mph.local",
        SESSION_COOKIE_NAME="mph_root_session",
    )
    def test_ip_returns_other(self) -> None:
        scope = resolve_session_scope("127.0.0.1")
        assert scope.host_scope == HostScope.OTHER

    @override_settings(
        MPH_ROOT_DOMAIN="mph.local",
        MPH_TENANT_DOMAIN_TEMPLATE="{slug}.mph.local",
        SESSION_COOKIE_NAME="mph_root_session",
    )
    def test_unrelated_host_returns_other(self) -> None:
        scope = resolve_session_scope("evil.com")
        assert scope.host_scope == HostScope.OTHER


class TestTemplateVariants:
    @override_settings(
        MPH_ROOT_DOMAIN="prod.example.com",
        MPH_TENANT_DOMAIN_TEMPLATE="{slug}.prod.example.com",
    )
    def test_production_template_shape(self) -> None:
        scope = resolve_session_scope("customer-x.prod.example.com")
        assert scope.host_scope == HostScope.TENANT
        assert scope.cookie_name == "tenant_session_customer-x"
        assert scope.cookie_domain == "customer-x.prod.example.com"
        assert scope.tenant_slug == "customer-x"

    @override_settings(
        MPH_ROOT_DOMAIN="example.com",
        MPH_TENANT_DOMAIN_TEMPLATE="mph-{slug}.example.com",
    )
    def test_prefix_template_shape(self) -> None:
        scope = resolve_session_scope("mph-acme.example.com")
        assert scope.host_scope == HostScope.TENANT
        assert scope.tenant_slug == "acme"
        assert scope.cookie_name == "tenant_session_acme"

    @override_settings(MPH_TENANT_DOMAIN_TEMPLATE="no-slug-here.example.com")
    def test_template_missing_slug_raises(self) -> None:
        with pytest.raises(ValueError, match="does not contain"):
            resolve_session_scope("anything.example.com")
