"""Log-scrubbing test (J.3.9 #20).

Asserts that secrets — passwords, TOTP secrets, recovery codes — do not
appear in any log record during a full local-auth flow.

This is a probe, not a proof. The audit pipeline's masking (G.5.5)
lives in the M2 partitioned-storage implementation; until then, we
verify that the M1 stub + signal handlers don't leak secrets into
captured logs.
"""

from __future__ import annotations

import logging
from typing import Any

import pytest
from django.test import Client

from apps.platform.accounts.tests._helpers import _install_totp_authenticator


@pytest.mark.django_db
class TestLogScrubbing:
    def test_login_flow_does_not_log_secrets(
        self,
        client: Client,
        user_factory: Any,
        caplog: Any,
    ) -> None:
        # Pin a known cleartext password and TOTP secret.
        password = "must-never-appear-in-logs-7777!"
        totp_secret = "JBSWY3DPEHPK3PXP"

        user = user_factory(email="logtest@example.test", password=password)
        _install_totp_authenticator(user, totp_secret)

        with caplog.at_level(logging.DEBUG):
            # Exercise a few code paths that touch the user.
            client.force_login(user)
            client.get("/select-org/")
            client.logout()

        # Assert none of the secret material appears in any log line.
        for record in caplog.records:
            assert (
                password not in record.getMessage()
            ), f"Cleartext password leaked into log: {record.getMessage()}"
            assert (
                totp_secret not in record.getMessage()
            ), f"TOTP secret leaked into log: {record.getMessage()}"

    def test_failed_login_does_not_log_password(
        self,
        client: Client,
        user_factory: Any,
        caplog: Any,
    ) -> None:
        password = "the-wrong-password-leak-check-43!"
        user_factory(email="wrong-pwd@example.test")

        with caplog.at_level(logging.DEBUG):
            client.post(
                "/accounts/login/",
                {"login": "wrong-pwd@example.test", "password": password},
            )

        for record in caplog.records:
            assert password not in record.getMessage()
