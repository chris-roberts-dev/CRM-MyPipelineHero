"""Fernet encryption helpers for HandoffSigningKey.secret (M1 D6 Phase 1).

B.4.13.1 specifies that the per-rotation HMAC secret is encrypted at
rest. We implement that as service-layer Fernet encryption with a
master key from environment (``HANDOFF_KEY_ENCRYPTION_KEY``) rather
than a custom EncryptedField type. The security property is
identical and avoids inventing a field type that doesn't exist yet
in the codebase. See M1 D6 retro deviation log.

Failure semantics:

* Missing master key at import time → ImproperlyConfigured raised
  by ``_get_fernet`` on first use. The settings module also asserts
  presence so deployments fail loudly.
* Decryption failure (wrong key, tampered ciphertext) → raises
  ``HandoffSecretDecryptionError`` which the caller MUST treat as
  "this key is unusable; do not use it for verification."

The master key has no in-application rotation mechanism in M1 D6.
Rotating the master key would render every existing
HandoffSigningKey.secret undecryptable. Out of scope; tracked as
operational concern.
"""

from __future__ import annotations

from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured


class HandoffSecretDecryptionError(Exception):
    """Raised when a HandoffSigningKey.secret cannot be decrypted.

    Likely causes: master key rotation without re-encryption,
    corruption of the stored ciphertext, or tampering. The caller
    MUST NOT use the key for verification when this is raised; do
    NOT log the raw ciphertext or master-key fingerprint in the
    error message.
    """


def _get_fernet() -> Fernet:
    """Construct a Fernet instance from settings.

    Raises:
        ImproperlyConfigured: if ``HANDOFF_KEY_ENCRYPTION_KEY`` is
        absent or malformed.
    """
    key = getattr(settings, "HANDOFF_KEY_ENCRYPTION_KEY", None)
    if not key:
        raise ImproperlyConfigured(
            "HANDOFF_KEY_ENCRYPTION_KEY is not configured. Generate one "
            "with `python -c 'from cryptography.fernet import Fernet; "
            "print(Fernet.generate_key().decode())'` and set it in the "
            "environment."
        )
    # Accept either bytes or str; Fernet expects bytes.
    if isinstance(key, str):
        key = key.encode("ascii")
    try:
        return Fernet(key)
    except (ValueError, TypeError) as exc:
        raise ImproperlyConfigured(
            "HANDOFF_KEY_ENCRYPTION_KEY is malformed. Must be a 32-byte "
            "url-safe base64-encoded value (Fernet.generate_key() output)."
        ) from exc


def encrypt_handoff_secret(plaintext: bytes) -> str:
    """Encrypt the raw per-rotation HMAC secret.

    Returns a Fernet token (base64 ASCII string) suitable for storage
    in a TextField column.
    """
    if not isinstance(plaintext, (bytes, bytearray)):
        raise TypeError(f"plaintext must be bytes, got {type(plaintext).__name__}")
    return _get_fernet().encrypt(bytes(plaintext)).decode("ascii")


def decrypt_handoff_secret(ciphertext: str) -> bytes:
    """Decrypt a Fernet-encrypted per-rotation HMAC secret.

    Raises:
        HandoffSecretDecryptionError: if the ciphertext can't be
        decrypted with the current master key.
    """
    if not isinstance(ciphertext, str):
        raise TypeError(f"ciphertext must be str, got {type(ciphertext).__name__}")
    try:
        return _get_fernet().decrypt(ciphertext.encode("ascii"))
    except InvalidToken as exc:
        # Do NOT echo the ciphertext or master-key fingerprint into
        # the error message.
        raise HandoffSecretDecryptionError(
            "HandoffSigningKey.secret could not be decrypted with the "
            "current HANDOFF_KEY_ENCRYPTION_KEY."
        ) from exc
