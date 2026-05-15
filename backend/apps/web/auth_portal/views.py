"""Auth-portal views (M1 D4).

The M0 scaffold's ``LoginPageView`` was a placeholder rendering of the
styled login form. M1 D4 replaces it with a permanent redirect to
allauth's canonical ``/accounts/login/``. This keeps any inbound
``/login/`` links working (landing-page CTA, marketing materials,
bookmarks) while making allauth the sole owner of the actual login
flow.

The redirect preserves ``?next=`` so post-login navigation continues
to work as expected.
"""

from __future__ import annotations

from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect
from django.urls import reverse
from django.views import View


class LoginPageView(View):
    """Permanent redirect from ``/login/`` to ``/accounts/login/``.

    Allauth owns the login form and POST handler. This view exists so
    the historical ``/login/`` URL keeps resolving.
    """

    def get(
        self, request: HttpRequest, *args: object, **kwargs: object
    ) -> HttpResponse:
        target = reverse("account_login")
        next_url = request.GET.get("next")
        if next_url:
            # urlencoding is handled by Django's HttpResponseRedirect via
            # the underlying QueryDict serialization; keep it explicit.
            from urllib.parse import urlencode

            target = f"{target}?{urlencode({'next': next_url})}"
        return redirect(target, permanent=True)

    # POST redirects to allauth's POST handler with the same status. We
    # don't carry the form body across the redirect (browsers won't
    # re-POST on a 308 unless the user re-confirms); the GET branch is
    # the one that matters for inbound links.
    def post(
        self, request: HttpRequest, *args: object, **kwargs: object
    ) -> HttpResponse:
        return self.get(request, *args, **kwargs)
