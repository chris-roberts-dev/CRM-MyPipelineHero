## M1 D6 — Cross-subdomain auth handoff ✅ COMPLETE

All six phases shipped. Test count: ~410 passing.

**Phase 1 — Handoff signing keys.** `HandoffSigningKey` model with
Fernet-encrypted secret. Service layer: `create`, `promote`, `retire`,
`emergency_rotate`. `active_handoff_signing_keys_ordered_by_created_desc`
helper. Audit codes wired.

**Phase 2 — Token issue + consume.** `issue_handoff_token` mints a
JWT signed with the primary key, writes a Redis nonce, and (Phase 5)
adds the token id to a per-user secondary index. `consume_handoff_token`
verifies the JWT (kid-first, trial fallback to active keys), atomically
single-use-consumes via GETDEL, removes from the secondary index, and
checks host binding + active membership.

**Phase 3 — Per-tenant sessions.** `PerTenantSessionMiddleware` writes
host-derived cookie names (`mph_root_session` on root,
`tenant_session_{slug}` on tenants). Cookie domain is `None` (host-
scoped, no parent-domain sharing). `SessionScope` and
`resolve_session_scope` host-classification helpers.

**Phase 4A — Host URL routing + MFA satisfaction.** `HostUrlconfMiddleware`
sets `request.urlconf` per host scope. `signals_mfa.py` writes
`mph_mfa_satisfied_at` to session on `authenticator_used` /
`authenticator_added`. Trusted-provider OAuth middleware also writes
the key when bypass fires.

**Phase 4B — Org picker + handoff issue + tenant consume + landing.**
`SelectOrgView` implements B.4.15 branch table (no membership → no-
access page; one membership → auto-advance; many/staff → picker).
`HandoffIssueView` mints tokens via POST. `HandoffConsumeView` on
tenant subdomain runs the consume + `establish_tenant_session` service

+ redirect. `TenantLandingView` shows the post-handoff state.

**Phase 5 — Logout + token revocation.** `TenantLogoutView` destroys
the tenant session and emits `TENANT_SESSION_LOGOUT`.
`signals_logout._on_user_logged_out` classifies the logout host: tenant
→ skip; root/unknown → revoke handoff tokens via
`revoke_all_handoff_tokens_for_user` and emit `ROOT_SESSION_LOGOUT`.
Secondary Redis index `user_handoffs:{uid}` enables the revocation.
Defensive request-host extraction in the signal handler.

**Phase 6 — Integration tests + retro.** J.3.9 #13-#16 multi-host
integration tests cover single-membership auto-advance, multi-
membership picker flow, host-mismatch rejection, and bidirectional
logout. Retro entry at `docs/retros/m1-d6-retro.md` covers all six
phases including deviations and known limitations.

### Audit codes added in D6

`HANDOFF_SIGNING_KEY_CREATED`, `HANDOFF_SIGNING_KEY_PROMOTED`,
`HANDOFF_SIGNING_KEY_RETIRED`, `HANDOFF_SIGNING_KEY_EMERGENCY_ROTATED`,
`HANDOFF_VERIFIED_WITH_RETIRED_KEY`, `TENANT_SESSION_ESTABLISHED`,
`MEMBERSHIP_SELECTED`, `ROOT_SESSION_LOGOUT`, `TENANT_SESSION_LOGOUT`,
`HANDOFF_TOKENS_REVOKED_BY_LOGOUT`. All registered in
`apps/platform/audit/services.py:_KNOWN_EVENT_TYPES`. To be folded
into G.5.2 in M2 audit work.

### Known limitations

+ Race window: token issue concurrent with logout — bounded by 60s
  TTL.
+ `signals_logout._fallback_host` checks for setting names that
  don't match our `MPH_ROOT_DOMAIN`; falls through to `testserver`.
+ Multi-tab interstitial (B.4.16) deferred — spec is incomplete
  on cross-subdomain mechanism.
+ Trusted-provider TOTP bypass (M1 D5 carry-over).

## M1 D7 — Platform console + impersonation ✅ COMPLETE

All six phases shipped. Test count: 559 passing. Retro at
`docs/retros/m1-d7-retro.md`.

**Phase 1 — Foundation.** New app `apps.platform.console` at
`/platform/`. `PlatformConsoleAccessMixin` enforces `is_staff`
(403 not redirect). Shared utility
`apps/platform/accounts/utils/email_verification.py` powers both
seed_dev_tenant and a `createsuperuser` extension that
auto-verifies the admin's email.

**Phase 2 — Read-only surfaces.** Org list/detail with name/slug
search and pagination. User search (search-driven, no query → no
results to avoid full-table scans). User detail shows MFA status
as boolean only — never the secret, never the recovery hash,
never password hashes.

**Phase 3 — Handoff signing key management UI.** List with
computed lifecycle state (pending/primary/active overlap/retired).
Create / Promote / Retire / Emergency rotate, each with two-page
confirmation. Emergency rotate URL has no key_id parameter — the
service determines the primary itself; operator types the new
key_id on the form. Service exceptions render inline as 400s.

**Phase 4 — Impersonation backend.** `ImpersonationSession` model
(UUID v7, all FKs PROTECT) with CHECK constraints
(admin != target, ended_at >= started_at, ended pair set together)
and a partial unique index (one active session per admin).
`start_impersonation` and `end_impersonation` services. Strict v1:
no staff-on-staff, no system-user, reason min length 10 chars.
Validation failures audit `IMPERSONATION_DENIED` with reason_code
metadata before raising. Race-window handling: `IntegrityError`
from partial unique index translates to
`ImpersonationAlreadyActiveError` with a follow-up denied audit
emitted in a fresh atomic block.

**Phase 5 — UI + handoff/tenant integration.**

Backend integration:

+ `HandoffResult.impersonator_admin_id: UUID | None` field.
+ `issue_handoff_token` gains optional `impersonator_admin_id`
  with cross-field invariant against `auth_method`.
+ JWT carries optional `iai` claim.
+ `consume_handoff_token` parses `iai` into HandoffResult.
+ `establish_tenant_session` writes
  `mph_session_impersonator_admin_id` session key (None for
  non-impersonation, so every session has the same shape).
+ `TENANT_SESSION_ESTABLISHED` audit metadata includes the
  impersonator id when present.

UI surfaces:

+ `UserImpersonateView` confirmation form + auto-POST handoff
  redirect.
+ `ImpersonationLogView` lists active + recent sessions.
+ `EndImpersonationFromConsoleView` ends sessions from the
  console.
+ `EnforceImpersonationLiveness` tenant middleware force-logs-out
  when the underlying session row has been ended out-of-band.
+ Tenant landing banner (yellow/orange chrome) with admin email
  and end button.
+ `EndImpersonationFromTenantView` at tenant `/end-impersonation/`
  ends with reason=ADMIN_ENDED.
+ `TenantLogoutView` now ends impersonation with reason=LOGOUT
  before flushing the session.

**Phase 6 — Retro.** This handoff entry + `docs/retros/m1-d7-retro.md`.

### Audit codes added in D7

`IMPERSONATION_STARTED`, `IMPERSONATION_ENDED`,
`IMPERSONATION_DENIED`. Registered in
`apps/platform/audit/services.py:_KNOWN_EVENT_TYPES`. To be folded
into G.5.2 in M2.

### Known limitations

+ Impersonating a no-TOTP target lands them on the MFA enrollment
  page (`RequireMfaEnrollmentMiddleware` fires on every tenant
  request including impersonation). Mitigation candidate (a) in
  the retro: middleware bypasses enrollment when session has
  `impersonator_admin_id` set. Track for M2.
+ MFA middleware redirect URL is root-relative on tenant
  subdomains. The tenant urlconf doesn't have
  `/accounts/2fa/totp/activate/`, so a real browser would 404.
  Track for M2.
+ `EnforceImpersonationLiveness` doesn't emit
  `TENANT_SESSION_LOGOUT` for its force-logout. The companion
  `IMPERSONATION_ENDED` event captures the cause; the missing
  logout event is mechanical cleanup. Could be revisited.
+ Strict v1: no staff-on-staff impersonation. Senior admins must
  use audit log review instead.
+ Strict v1: no auto-expiry of long-running sessions. Reserved
  `EXPIRED` end_reason exists but no Celery task closes idle
  sessions.

## M1 — COMPLETE (D1–D7)

All seven M1 days have shipped. The platform now has:

+ Custom User model with UUID v7 keys, email-only identity,
  TOTP + recovery codes MFA, lockout, OAuth/OIDC linkage.
+ Organization + Membership + Role + Capability data layer
  (RBAC implementation deferred to M2).
+ Row-level multi-tenancy guardrail (CI-level model-shape
  check).
+ Cross-subdomain auth handoff with signing-key rotation,
  per-tenant sessions, per-host URL routing.
+ Platform-admin console at `/platform/` with read-only
  org/user surfaces, signing-key management, and full
  impersonation flow.
+ Audit emission stub with 35+ registered event types
  (storage layer deferred to M2).
+ Test count: 559 across 50+ test files.

## Next: M2 — RBAC + Audit storage

The original M2 scope:

+ **G.5 Audit-event storage.** Replace the M1 stub with the
  partitioned `platform_audit.AuditEvent` model. Per-event
  retention policy. Masking for sensitive fields. The
  `_KNOWN_EVENT_TYPES` registry currently in
  `apps.platform.audit.services` moves to G.5.2 proper.
+ **RBAC implementation.** The seed_v1 data migration already
  installed the 11 default role templates and the capability
  grant matrix in M1 D2. M2 wires this up to actual
  permission checks: `has_capability(user, capability,
  organization)` service, decorator/mixin for views,
  middleware integration if appropriate.
+ **Membership lifecycle services.** Invite, accept, suspend,
  reinstate, deactivate. Audit codes for each.
+ **Role assignment + unassignment services.**

Followed by **M2A — Plan entitlements and add-on foundation**
(inserted between M2 and M3 per the design decision adopted
mid-D6). Spec at `docs/entitlements.md`. Models:
`Subscription`, `PlanEntitlement`, `PlanAddOnEntitlement`,
`OrganizationAddOnSubscription`, `OrganizationEntitlementOverride`.
Services: `has_feature`, `require_feature` with N+1-safe
request-scope caching.

**Then M3** — Catalog + pricing.

## Carrying into M2

+ The patterns established during D6/D7 — service-layer state
  changes, middleware-driven enforcement, signal handlers as a
  real architectural layer, validation-failure audit pattern —
  apply directly to the M2 audit-storage and RBAC work.
+ The `_KNOWN_EVENT_TYPES` set is the authoritative list of
  events the system emits. Use it as the migration starting
  point for `platform_audit.AuditEvent`.
+ The platform console URL space is currently flat. As M2 RBAC
  views land, consider a grouping pass (e.g. `/platform/users/`,
  `/platform/orgs/`, `/platform/audit/`, `/platform/security/`).
+ Two real product gaps from M1 D7 to address in M2 if scope
  permits: the no-TOTP impersonation footgun, and the
  root-relative MFA enrollment redirect on tenant subdomains.
  See `docs/retros/m1-d7-retro.md` for details.
+ The fixture naming bug — `user_verified_with_totp` doesn't
  actually install TOTP per the failure email
  `verified-nomfa@example.test` — should get a cleanup pass.
  Either rename the fixture or update its definition to match
  its name.
