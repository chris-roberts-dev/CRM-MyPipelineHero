"""Public landing page (H.3.3).

This view MUST:

1. Render at ``/``.
2. Use the shared ``base.html`` and landing CSS (H.8).
3. Provide a clear sign-in path to ``/login/``.
4. Avoid tenant-specific data.
5. Avoid requiring authentication.
6. Avoid requiring React or tenant-portal JS.
7. Remain server-rendered in Phase 2.

The page content (plans, features, workflow) is public marketing copy
and MUST NOT be treated as a source of truth for pricing/billing logic
(H.3.3 final paragraph).
"""

from __future__ import annotations

from django.views.generic import TemplateView


class LandingPageView(TemplateView):
    template_name = "landing/homepage.html"
