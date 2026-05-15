"""Tests for the ACCOUNT_USER_DISPLAY callable (M1 D4).

This is the fix for the `'User' object has no attribute 'username'`
AttributeError that surfaced during the demo login. The callable MUST:
- Return user.email for our User model.
- Not raise on any input shape.
- Fall back gracefully when the input lacks an email attribute.
"""

from __future__ import annotations

from typing import Any
from unittest import mock

import pytest

from apps.platform.accounts.user_display import user_display


@pytest.mark.django_db
class TestUserDisplay:
    def test_returns_email_for_real_user(self, user_verified_no_mfa: Any) -> None:
        assert user_display(user_verified_no_mfa) == user_verified_no_mfa.email

    def test_handles_none(self) -> None:
        assert user_display(None) == ""

    def test_handles_object_without_email(self) -> None:
        obj = mock.MagicMock(spec=[])  # no email attribute
        # __str__ returns the MagicMock repr; either way it must not raise.
        result = user_display(obj)
        assert isinstance(result, str)

    def test_handles_object_with_empty_email(self) -> None:
        obj = mock.MagicMock()
        obj.email = ""
        obj.__str__ = lambda self: "fallback-str"
        result = user_display(obj)
        # Falls through to str(obj) because email is falsy.
        assert isinstance(result, str)

    def test_setting_points_at_this_callable(self) -> None:
        """Sanity check that base.py wires ACCOUNT_USER_DISPLAY correctly."""
        from django.conf import settings

        assert (
            settings.ACCOUNT_USER_DISPLAY
            == "apps.platform.accounts.user_display.user_display"
        )
