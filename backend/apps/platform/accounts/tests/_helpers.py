"""Test helpers for the accounts app (M1 D4).

Pure functions and constants used by the test suite. Lives outside
``conftest.py`` because conftest is not a regular importable Python
module — pytest loads it specially and ``from .conftest import X``
does not work reliably across discovery boundaries.

What lives here:

* ``TEST_TOTP_SECRET`` — the canonical fixture secret.
* ``totp_code_for(secret)`` — compute the current TOTP code via
  RFC 6238 using the period/digit count from Django settings. Used
  by the end-to-end MFA test (J.3.9 #4). We hand-roll TOTP rather
  than depending on ``pyotp`` because allauth's ``[mfa]`` extra
  does not pull pyotp in transitively.
* ``_install_totp_authenticator(user, secret)`` — write an
  Authenticator row directly. Bypasses allauth's adapter encryption,
  which is fine for tests (the secret never leaves the test process).
* ``_install_recovery_codes(user)`` — same, for recovery codes.
  Smoke-rendering only; the single-use end-to-end test uses
  allauth's real generate flow.

Why direct Authenticator rows instead of allauth's high-level API:
the allauth ``activate`` function path has shifted between versions.
Writing the Authenticator row directly is stable across versions
because the model itself is the public contract surface.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import secrets as _secrets
import struct
import time
from typing import Any

from allauth.mfa.models import Authenticator
from django.conf import settings

# Stable base32-encoded test TOTP secret. 16 chars — the standard TOTP
# key length. Tests that need to satisfy a challenge use
# `totp_code_for(TEST_TOTP_SECRET)` to compute a valid 6-digit code.
TEST_TOTP_SECRET = "JBSWY3DPEHPK3PXP"


def _compute_totp_code(secret: str, when: float | None = None) -> str:
    """Compute a TOTP code for a base32 secret.

    RFC 6238 with the period and digit count from Django's
    ``MFA_TOTP_PERIOD`` / ``MFA_TOTP_DIGITS`` settings. SHA-1 is
    RFC-mandated.

    Args:
        secret: base32-encoded shared secret.
        when: unix timestamp; defaults to the current time.

    Returns:
        Zero-padded decimal code as a string.
    """
    period = getattr(settings, "MFA_TOTP_PERIOD", 30)
    digits = getattr(settings, "MFA_TOTP_DIGITS", 6)
    if when is None:
        when = time.time()
    counter = int(when // period)
    key = base64.b32decode(secret)
    counter_bytes = struct.pack(">Q", counter)
    h = hmac.new(key, counter_bytes, hashlib.sha1).digest()
    offset = h[-1] & 0x0F
    truncated = struct.unpack(">I", h[offset : offset + 4])[0] & 0x7FFFFFFF
    return str(truncated % (10**digits)).zfill(digits)


def totp_code_for(secret: str) -> str:
    """Public helper exposed to tests. See ``_compute_totp_code``."""
    return _compute_totp_code(secret)


def _install_totp_authenticator(user: Any, secret: str) -> Authenticator:
    """Install a TOTP Authenticator row for a user, raw.

    Data shape ``{"secret": "..."}`` matches what allauth's TOTP
    wrapper expects on read. The secret is stored plaintext (no
    adapter encryption), which is fine for tests because the secret
    never leaves the test DB.
    """
    return Authenticator.objects.create(
        user=user,
        type=Authenticator.Type.TOTP,
        data={"secret": secret},
    )


def _install_recovery_codes(user: Any) -> Authenticator:
    """Install a recovery-codes Authenticator row for a user, raw.

    The data shape mirrors what allauth's recovery-codes wrapper
    stores: ``{"migrated_codes": [], "seed": <random hex>}``. The
    actual codes are derived from the seed; tests that need to
    assert the single-use rule should use allauth's real generate
    view instead of this helper because the wrapper's derivation
    algorithm may shift between versions.
    """
    return Authenticator.objects.create(
        user=user,
        type=Authenticator.Type.RECOVERY_CODES,
        data={"migrated_codes": [], "seed": _secrets.token_hex(20)},
    )
