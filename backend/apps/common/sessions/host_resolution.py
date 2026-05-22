"""Host → session-scope resolution (M1 D6 Phase 3).

Pure functions that compute the session cookie name and cookie domain
from the request host. No Django dependencies beyond ``settings`` —
keeps the logic unit-testable without spinning up a request cycle.

Three scopes:

* ``HostScope.ROOT`` — request to the root domain (``mph.local`` in
  dev). Cookie name: ``settings.SESSION_COOKIE_NAME`` (default
  ``"mph_root_session"`` per M1 D6 base.py).
* ``HostScope.TENANT`` — request to a tenant subdomain
  (``{slug}.mph.local``). Cookie name: ``tenant_session_{slug}``.
  Cookie domain: the exact tenant host.
* ``HostScope.OTHER`` — request to a host we don't classify
  (``localhost``, ``testserver``, IP literals). Falls back to
  ``settings.SESSION_COOKIE_NAME`` with no Domain attribute (browser
  default = exact host).

The template-string parsing happens once per process at import time;
subsequent calls are pure dict lookups.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum

from django.conf import settings


class HostScope(str, Enum):
    ROOT = "ROOT"
    TENANT = "TENANT"
    OTHER = "OTHER"


@dataclass(frozen=True)
class SessionScope:
    """The cookie name and domain a request's session should use."""

    host_scope: HostScope
    cookie_name: str
    cookie_domain: str | None
    tenant_slug: str | None  # populated only when host_scope == TENANT


# Slug regex from B.1.2 — used to validate the parsed slug, not to
# match the host. The host parser strips prefix/suffix; if what
# remains doesn't look like a valid slug, we treat the host as OTHER
# rather than TENANT (defense in depth — a malformed host shouldn't
# get a writable tenant session).
_SLUG_REGEX = re.compile(r"^[a-z][a-z0-9-]{1,61}[a-z0-9]$")


def _parse_tenant_template() -> tuple[str, str]:
    """Split MPH_TENANT_DOMAIN_TEMPLATE into (prefix, suffix) at {slug}.

    Example: ``"{slug}.mph.local"`` → (``""``, ``".mph.local"``).
    ``"mph-{slug}.example.com"`` → (``"mph-"``, ``".example.com"``).
    """
    template = settings.MPH_TENANT_DOMAIN_TEMPLATE
    if "{slug}" not in template:
        raise ValueError(
            f"MPH_TENANT_DOMAIN_TEMPLATE={template!r} does not contain '{{slug}}'"
        )
    prefix, suffix = template.split("{slug}", 1)
    return prefix, suffix


def _root_domain() -> str:
    return settings.MPH_ROOT_DOMAIN


def resolve_session_scope(host: str) -> SessionScope:
    """Classify the host and return cookie name+domain accordingly.

    Args:
        host: The request host (``request.get_host()``), with port
            already stripped by the caller.

    Returns:
        A SessionScope describing what cookie name and domain to use
        for sessions on this host.
    """
    root = _root_domain()
    prefix, suffix = _parse_tenant_template()

    # Strip any port (paranoia — caller should already have done this).
    host = host.split(":", 1)[0].lower()

    # ROOT scope: exact match on the root domain.
    if host == root.lower():
        return SessionScope(
            host_scope=HostScope.ROOT,
            cookie_name=settings.SESSION_COOKIE_NAME,
            # None → browser scopes the cookie to exact host only.
            # B.4.14 prohibits parent-domain sharing.
            cookie_domain=None,
            tenant_slug=None,
        )

    # TENANT scope: matches the prefix/suffix template AND extracted
    # slug matches the B.1.2 slug regex.
    if host.startswith(prefix) and host.endswith(suffix):
        # Strip prefix and suffix; what remains is the candidate slug.
        candidate = host[len(prefix) :]
        candidate = candidate[: len(candidate) - len(suffix)] if suffix else candidate
        if candidate and _SLUG_REGEX.match(candidate):
            return SessionScope(
                host_scope=HostScope.TENANT,
                cookie_name=f"tenant_session_{candidate}",
                cookie_domain=host,
                tenant_slug=candidate,
            )

    # OTHER scope: testserver, localhost, IPs, anything else. Use the
    # global default cookie name with no Domain attribute (browser
    # default = exact host).
    return SessionScope(
        host_scope=HostScope.OTHER,
        cookie_name=settings.SESSION_COOKIE_NAME,
        cookie_domain=None,
        tenant_slug=None,
    )
