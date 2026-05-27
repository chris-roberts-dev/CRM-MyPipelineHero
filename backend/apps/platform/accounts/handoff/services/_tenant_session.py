"""establish_tenant_session service (M1 D6 Phase 4B, B.4.14, M1 D7 Phase 5).

Writes the B.4.14-shaped tenant-local session dict and authenticates
the user into the tenant context. Called from the handoff-consume
view after a successful ``consume_handoff_token`` returns a
``HandoffResult``.

**M1 D7 Phase 5 — Impersonation context in the session.**

When the HandoffResult carries ``impersonator_admin_id``, the session
gets ``mph_session_impersonator_admin_id`` set to the admin's id (as
a string). Downstream code that needs to know "is this an
impersonation session?" reads this key. The
``EnforceImpersonationLiveness`` middleware uses it to gate tenant
requests against the ImpersonationSession row's ``ended_at``.

For non-impersonation sessions, the key is set to None so every
tenant session has the same shape.
"""

from __future__ import annotations

import logging

from django.contrib.auth import get_user_model, login
from django.db import transaction
from django.http import HttpRequest

from apps.platform.accounts.handoff.results import HandoffResult
from apps.platform.audit.services import audit_emit

logger = logging.getLogger(__name__)


# Session keys per B.4.14 — read by downstream tenant-scoped views,
# RBAC checks, and the reauthentication / step-up flows.
SESSION_KEY_ORGANIZATION_ID = "mph_session_organization_id"
SESSION_KEY_MEMBERSHIP_ID = "mph_session_membership_id"
SESSION_KEY_AUTH_METHOD = "mph_session_auth_method"
SESSION_KEY_AUTH_PROVIDER = "mph_session_auth_provider"
SESSION_KEY_MFA_SATISFIED_AT = "mph_session_mfa_satisfied_at"
# M1 D7 Phase 5 — impersonation context.
SESSION_KEY_IMPERSONATOR_ADMIN_ID = "mph_session_impersonator_admin_id"


def establish_tenant_session(
    *,
    request: HttpRequest,
    handoff_result: HandoffResult,
) -> None:
    """Authenticate the user and populate B.4.14 session keys.

    Side effects:
        * ``request.session`` is mutated: Django auth keys (via
          ``login()``) + the five B.4.14 session keys + the
          M1 D7 Phase 5 impersonator session key.
        * Audit event ``TENANT_SESSION_ESTABLISHED`` is emitted
          within an atomic block. For impersonation sessions, the
          audit metadata includes ``impersonator_admin_id``.

    Raises:
        UserModel.DoesNotExist: if ``handoff_result.user_id`` no
            longer references a valid user.
    """
    UserModel = get_user_model()
    user = UserModel.objects.get(id=handoff_result.user_id)

    with transaction.atomic():
        user.backend = "django.contrib.auth.backends.ModelBackend"
        login(request, user)

        # B.4.14 session keys.
        request.session[SESSION_KEY_ORGANIZATION_ID] = str(
            handoff_result.organization_id
        )
        request.session[SESSION_KEY_MEMBERSHIP_ID] = str(handoff_result.membership_id)
        request.session[SESSION_KEY_AUTH_METHOD] = handoff_result.auth_method
        request.session[SESSION_KEY_AUTH_PROVIDER] = handoff_result.auth_provider
        request.session[SESSION_KEY_MFA_SATISFIED_AT] = (
            handoff_result.mfa_satisfied_at.isoformat()
        )
        # M1 D7 Phase 5 — write impersonator id (None for non-impersonation,
        # so every tenant session has the same shape).
        request.session[SESSION_KEY_IMPERSONATOR_ADMIN_ID] = (
            str(handoff_result.impersonator_admin_id)
            if handoff_result.impersonator_admin_id is not None
            else None
        )
        request.session.modified = True

        audit_metadata: dict[str, object | None] = {
            "auth_method": handoff_result.auth_method,
            "auth_provider": handoff_result.auth_provider,
            "mfa_satisfied_at": handoff_result.mfa_satisfied_at.isoformat(),
        }
        if handoff_result.impersonator_admin_id is not None:
            audit_metadata["impersonator_admin_id"] = str(
                handoff_result.impersonator_admin_id
            )

        audit_emit(
            "TENANT_SESSION_ESTABLISHED",
            actor_id=handoff_result.user_id,
            organization_id=handoff_result.organization_id,
            object_kind="platform_organizations.Membership",
            object_id=str(handoff_result.membership_id),
            metadata=audit_metadata,
        )
