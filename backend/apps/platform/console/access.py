"""Access control for the platform console (M1 D7 Phase 1).

Every platform-console view enforces three things:

1. The user is authenticated (Django's standard requirement).
2. The user has ``is_staff = True`` (B.3.4 — "User may access the
   platform console").
3. The user has completed MFA, satisfied via the normal
   ``RequireMfaEnrollmentMiddleware`` chain. We don't add a
   second MFA check here; the global middleware is the one
   source of truth.

Anonymous users get redirected to login. Authenticated but
non-staff users get a 403. We deliberately do NOT silently
redirect non-staff to ``/select-org/`` — a 403 makes it
obvious when a non-staff user discovers (or guesses) a
``/platform/...`` URL.

**Why a mixin, not a decorator.** All platform views are
class-based for consistency with the Phase 2+ surfaces (org
list/detail and user search/detail will both use generic
ListView / DetailView). Mixins compose cleanly with those
generic views.
"""

from __future__ import annotations

from typing import Any

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import HttpRequest, HttpResponse
from django.utils.decorators import method_decorator


@method_decorator(login_required, name="dispatch")
class PlatformConsoleAccessMixin:
    """Enforce ``is_staff`` on every platform-console view.

    Subclasses get login_required for free (via the decorator).
    The dispatch hook adds the is_staff check on top.

    Returns 403 (Forbidden) for authenticated non-staff users
    rather than redirecting. The behavior is intentional: a
    redirect would obscure the access denial in browser history,
    and non-staff users shouldn't be probing platform URLs.
    """

    def dispatch(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        if not request.user.is_staff:
            raise PermissionDenied("Platform console access requires is_staff=True.")
        return super().dispatch(request, *args, **kwargs)  # type: ignore[misc]
