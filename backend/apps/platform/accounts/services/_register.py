"""Local-user registration service (M1 D4).

This service creates a canonical :class:`apps.platform.accounts.User`
row for a user who will authenticate with a local password. It is the
authoritative service-layer entrypoint for:

1. The seed_dev_tenant management command (currently uses
   ``User.objects.create_user`` directly; tracked in the M1 retro as a
   follow-up to migrate to this service).
2. The future invite-acceptance flow (M1 D5+).

OAuth/OIDC-only users follow a different path: they are created by
``resolve_external_user`` (B.4.6) during the OAuth callback, with
``external_login_only=True`` and an unusable password. That service
lands in M1 D5; this one is local-password only.

**Service contract** (A.4.4):

* Keyword-only primitive arguments.
* Single ``transaction.atomic()`` boundary.
* ``audit_emit("USER_REGISTERED", ...)`` inside the boundary.
* Typed exceptions for the two distinguishable failure modes.
* Does NOT create a Membership. Tenant membership is bootstrapped
  separately by ``assign_owner_membership`` or the invite flow.

**Security notes:**

* Email is normalized to lowercase (B.3.3 CHECK constraint).
* Password validation runs Django's configured validators (B.5.2).
* ``password_changed_at`` is stamped so the rotation policy (B.5.3)
  has an anchor.
* The cleartext password is NEVER logged. The audit payload contains
  only the user id, normalized email, and a boolean
  ``password_was_set``; the password itself never enters the audit
  trail.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.platform.accounts.services.exceptions import (
    UserAlreadyExistsError,
    UserNotFoundError,
)
from apps.platform.audit.services import audit_emit

if TYPE_CHECKING:
    from apps.platform.accounts.models import User


def _validate_email_shape(value: str) -> None:
    """Lightweight email shape check; full normalization happens at write."""
    if not isinstance(value, str) or "@" not in value or len(value) > 254:
        raise ValidationError({"email": "Must be a valid email address."})


def register_local_user(
    *,
    email: str,
    password: str,
    actor_id: UUID,
    is_active: bool = True,
) -> User:
    """Create a canonical User for local-password authentication (B.3.3).

    Steps performed inside a single ``transaction.atomic()``:

    1. Validate the email shape.
    2. Confirm the actor exists.
    3. Validate the password against Django's configured validators
       (B.5.2: 12-char minimum, common-password check, etc.).
    4. Reject if the email is already taken (case-insensitively).
    5. Create the User row with a hashed password and stamp
       ``password_changed_at`` (anchor for B.5.3 rotation policy).
    6. Emit ``USER_REGISTERED`` audit event. The audit payload does
       NOT contain the cleartext password — only the user id and
       normalized email.

    Args:
        email: User-supplied email. Normalized to lowercase before
            persistence.
        password: Cleartext password. Validated; never logged.
        actor_id: UUID of the User performing the registration. For
            self-signup flows the user has just registered themselves;
            the calling view passes the newly-created allauth user id
            *after* allauth has run its own create. For the future
            invite-acceptance flow this is the invitee's id once
            email verification completes. For system bootstrap
            (seed_dev_tenant) it is the System User id.
        is_active: Whether the user is immediately able to log in.
            Defaults True. Pass False for invite-pending accounts that
            need a verification step first.

    Returns:
        The newly created User.

    Raises:
        ValidationError: input fails validation (email shape, password
            policy). No DB writes occur in this case.
        UserAlreadyExistsError: email is already taken.
        UserNotFoundError: actor_id does not exist.
    """
    if actor_id is None:
        raise ValueError("actor_id is required.")

    _validate_email_shape(email)

    UserModel = get_user_model()
    normalized_email = UserModel.objects.normalize_email(email).lower()

    if not UserModel.objects.filter(pk=actor_id).exists():
        raise UserNotFoundError(actor_id)

    # Run Django's password validators BEFORE the transaction so we
    # don't hold a row lock through validator I/O (e.g. common-password
    # check). We have a dummy unsaved User so validators that look at
    # email/etc. work.
    validate_password(password, user=UserModel(email=normalized_email))

    if UserModel.objects.filter(email=normalized_email).exists():
        raise UserAlreadyExistsError(normalized_email)

    try:
        with transaction.atomic():
            user = UserModel.objects.create_user(
                email=normalized_email,
                password=password,
                is_active=is_active,
                is_staff=False,
                is_superuser=False,
                is_system=False,
            )
            # The manager's _create_user stamps password_changed_at,
            # but only when a password is provided. We're explicit
            # here to be safe.
            if user.password_changed_at is None:
                user.password_changed_at = timezone.now()
                user.save(update_fields=["password_changed_at"])

            audit_emit(
                "USER_REGISTERED",
                actor_id=actor_id,
                organization_id=None,
                object_kind="platform_accounts.User",
                object_id=str(user.id),
                payload_after={
                    "email": user.email,
                    "is_active": user.is_active,
                    "password_was_set": True,
                    # Never include the password itself, hashed or not.
                },
            )
    except IntegrityError as exc:
        # The User.email unique constraint is the only realistic
        # IntegrityError source on this path. Re-raise as a typed
        # exception so callers branch cleanly.
        if "email" in str(exc).lower():
            raise UserAlreadyExistsError(normalized_email) from exc
        raise

    return user
