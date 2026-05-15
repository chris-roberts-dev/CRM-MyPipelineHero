"""M0 login-scaffold test (REPLACED in M1 D4).

The M0 scaffold view rendered a styled form that did not authenticate.
M1 D4 replaced that view with a permanent redirect to allauth's
canonical `/accounts/login/`. The scaffold test is therefore replaced
by `test_url_routing.py::TestAuthPortalRouting::test_login_redirect_to_allauth`.

This file remains as a tombstone documenting the migration so a
future engineer doesn't try to revive the scaffold.
"""

from __future__ import annotations

import pytest
from django.test import Client


@pytest.mark.django_db
class TestLoginScaffoldRemoved:
    def test_login_path_is_now_a_redirect(self, client: Client) -> None:
        response = client.get("/login/")
        assert response.status_code in (301, 302)
        assert response["Location"].startswith("/accounts/login/")
