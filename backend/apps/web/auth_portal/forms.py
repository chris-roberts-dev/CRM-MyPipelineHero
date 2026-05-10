"""Auth-portal forms.

M0 ships a styled ``LoginForm`` shell so the login template renders
exactly as designed in the Phase 1 visual baseline (H.8.5). It does not
authenticate yet — wiring up against django-allauth lands in M1
(B.4.3 login flow).
"""

from __future__ import annotations

from typing import Any

from django import forms


class LoginForm(forms.Form):
    """Visual login form used by ``LoginPageView`` (M0 scaffold)."""

    email = forms.EmailField(
        label="Email",
        widget=forms.EmailInput(
            attrs={
                "autocomplete": "username",
                "inputmode": "email",
                "autocapitalize": "none",
                "autocorrect": "off",
                "spellcheck": "false",
                "placeholder": "you@example.com",
            }
        ),
    )
    password = forms.CharField(
        label="Password",
        widget=forms.PasswordInput(
            attrs={
                "autocomplete": "current-password",
                "placeholder": "••••••••",
            }
        ),
    )
    next = forms.CharField(
        required=False,
        widget=forms.HiddenInput(),
    )

    def clean(self) -> dict[str, Any]:
        # Authentication itself lands in M1 against allauth. We deliberately
        # do not raise validation errors here in M0; the form is render-only.
        return super().clean() or {}
