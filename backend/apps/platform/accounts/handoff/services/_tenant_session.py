"""establish_tenant_session service (M1 D6 Phase 4B, B.4.14).

Writes the B.4.14-shaped tenant-local session dict and authenticates
the user into the tenant context. Called from the handoff-consume
view after a successful ``consume_handoff_token`` returns a
``HandoffResult``.

Per project posture:
* Owns its own ``transaction.atomic()`` for the audit emit.
* Keyword-only arguments.
* The session itself isn't a DB row in the traditional sense
  (Django's DB-backed session backend persists at request end via
  ``PerTenantSessionMiddleware``), so the "state change" here is
  the in-memory ``request.session`` mutation plus the Django auth
  login. Treating this as a service keeps audit emission consistent
  with other state-change boundaries and makes the consume view thin.

**Session shape per B.4.14:**

The session is populated with:
* ``_auth_user_id``, ``_auth_user_backend``, ``_auth_user_hash`` —
  written by ``django.contrib.auth.login``. Marks the session as
  authenticated for subsequent requests.
* ``mph_session_organization_id`` — the tenant the user is operating
  within. Used by row-level tenancy checks downstream.
* ``mph_session_membership_id`` — the Membership that authorized
  this session. Distinct from organization_id because RBAC scopes
  attach to memberships.
* ``mph_session_auth_method`` — "password", "oidc", "oauth2",
  "impersonation". Read by reauthentication / step-up flows.
* ``mph_session_auth_provider`` — provider_code if OAuth, else None.
* ``mph_session_mfa_satisfied_at`` — ISO 8601 timestamp from the
  handoff token. B.4.10 freshness checks compare against this.

**Why not just login(request, user)?** Django's login alone marks
the session authenticated but doesn't store organization or
membership context. The handoff carried those through; we record
them here so subsequent requests on the tenant subdomain don't
need to re-derive them.
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


def establish_tenant_session(
    *,
    request: HttpRequest,
    handoff_result: HandoffResult,
) -> None:
    """Authenticate the user and populate B.4.14 session keys.

    Args:
        request: The HTTP request landing on the tenant subdomain
            (the one that consumed the handoff token).
        handoff_result: The verified handoff payload from
            ``consume_handoff_token``. Carries user_id,
            organization_id, membership_id, auth_method,
            auth_provider, mfa_satisfied_at.

    Side effects:
        * ``request.session`` is mutated: Django auth keys (via
          ``login()``) + the five B.4.14 session keys above.
        * Audit event ``TENANT_SESSION_ESTABLISHED`` is emitted
          within an atomic block.

    Raises:
        UserModel.DoesNotExist: if ``handoff_result.user_id`` no
            longer references a valid user. The caller should
            treat this as a 4xx (the user was deleted between
            handoff issue and consume — extremely rare).
    """
    UserModel = get_user_model()
    user = UserModel.objects.get(id=handoff_result.user_id)

    with transaction.atomic():
        # Set the auth backend explicitly so Django's login() doesn't
        # have to guess. ModelBackend is the canonical local-auth
        # backend; the user IS authenticated (the handoff token
        # proved it), this just marks the session with the standard
        # Django auth keys so AccountMiddleware and downstream
        # request.user access work.
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
        request.session.modified = True

        audit_emit(
            "TENANT_SESSION_ESTABLISHED",
            actor_id=handoff_result.user_id,
            organization_id=handoff_result.organization_id,
            object_kind="platform_organizations.Membership",
            object_id=str(handoff_result.membership_id),
            metadata={
                "auth_method": handoff_result.auth_method,
                "auth_provider": handoff_result.auth_provider,
                "mfa_satisfied_at": handoff_result.mfa_satisfied_at.isoformat(),
            },
        )
