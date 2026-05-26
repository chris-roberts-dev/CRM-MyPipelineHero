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

## Next: M1 D7 — Support impersonation + platform console

Per the original M1 plan:

+ **B.7 Support impersonation flow.** Platform-admin user impersonates
  a tenant user with full audit trail. `ImpersonationSession` model,
  `impersonate_user` service, `end_impersonation` service. Audit codes:
  `IMPERSONATION_STARTED`, `IMPERSONATION_ENDED`, `IMPERSONATION_DENIED`.
+ **Platform console at `/platform/`.** Replaces M1 D6 placeholder
  link from the staff branch of the org picker. Custom Django views
  (NOT base Django admin per project posture). Includes:
  + Organization list / detail.
  + User search / detail.
  + Handoff signing key management UI (calls Phase 1 services).
  + Impersonation flow UI.
+ **Plan-management scaffolding** wired to M2A backend when M2A ships.
+ **`createsuperuser` ergonomics fix** — auto-create verified
  `EmailAddress` so the first-time admin isn't blocked by allauth's
  email-verification middleware.

M2A (plan entitlements) remains inserted between M2 and M3 as decided
during D6.

## Carrying into M1 D7

+ The patterns established during D6 — service-layer state changes,
  middleware audit via `record_auth_event`, signal handlers as a real
  architectural layer — apply equally to impersonation.
+ The `/platform/` URLs live on root domain. Add to `config/urls_root.py`.
+ Platform-admin views need their own MFA enforcement and a separate
  authentication carve-out (the platform console must NOT pass the
  org-picker; it's a parallel auth flow). Worth thinking through up-
  front.
