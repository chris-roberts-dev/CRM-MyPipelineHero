# MyPipelineHero — Project Handoff

**Last updated:** end of M1 Deliverable 5 (OAuth/OIDC provider
integration: data model, claims, loader, resolution service,
socialaccount adapter, trusted-MFA middleware policy, templates,
adapter-boundary tests).

**Audience:** the next engineer or AI session to pick up this project.
Read this top-to-bottom before touching code. The Fresh Session Startup
Prompt at the bottom is meant for copy/paste into a new AI session.

---

## 1. Project Overview

**MyPipelineHero** is a Django-based multi-tenant CRM SaaS platform for
organizations that sell services, resale products, and manufactured
products. The project is being built incrementally, milestone by
milestone, starting from a blank repository.

### Authoritative source

`docs/guide.md` (the **MyPipelineHero technical development guide
v0.7**) is the source of truth.

### Current development phase

**M1 — Tenancy + Identity + Auth (in progress).**

M0 complete. M1 progress:

- **D1 ✅** Tenancy primitives + B.1.7 isolation guardrail.
- **D2 ✅** `services.create_organization` and `services.assign_owner_membership`.
- **D3 ✅** Region / Market / Location + MembershipScopeAssignment + `resolve_location_ids_for_scopes`.
- **D4 ✅** Identity wiring: local password login + MFA enrollment +
  recovery codes via django-allauth + allauth.mfa. Full allauth template
  overrides. Custom `RequireMfaEnrollmentMiddleware` (allauth.mfa has
  no forced-enrollment middleware). Custom `ACCOUNT_USER_DISPLAY`
  (our User model has no `username`). Audit-event catalog extended
  to cover B.4.19 + MFA lifecycle. ~50 new tests.
- **D5 ✅** OAuth/OIDC provider integration: `OAuthProviderConfig`
  model (B.3.7) + `ExternalIdentityClaims` (B.3.8) + settings loader
  reading client secrets from env vars + `resolve_external_user`
  service (B.4.6 / B.4.7) + `MphSocialAccountAdapter` enforcing
  policy at `pre_social_login` + trusted-vs-untrusted-provider MFA
  middleware (B.4.8) + socialaccount template overrides + OAuth help
  page + adapter-boundary integration tests + audit catalog
  expanded to full B.4.19 OAuth events. **Full HTTP integration with
  a mock OIDC issuer was scoped out** — verified at adapter boundary;
  cryptographic validation (state, nonce, signature, issuer, audience)
  is allauth's surface and ships verified in M8 per J.10.3. ~70 new
  tests.
- **D6 — next** Cross-subdomain handoff + tenant-local session + real org picker.
- D7 — pending (support impersonation + platform console).

---

## 2. Current Technical Stack

| Layer | Choice |
| --- | --- |
| Language | Python 3.14 |
| Web framework | Django 5.2 |
| Auth | django-allauth 65.x (account + socialaccount + mfa) |
| DB | PostgreSQL 17 |
| Cache / broker | Redis 7 |
| Background workers | Celery + Celery beat |
| Email (dev) | Mailpit |
| Object store (dev) | MinIO |
| Reverse proxy (dev) | Nginx |
| Reverse proxy (prod) | Nginx or Caddy per guide; deferred |
| Container orchestration | Docker Compose |
| Deployment target | DigitalOcean-oriented Docker |
| Frontend bundler | Vite 5 |
| CSS | Tailwind 4 |
| Frontend lib | HTMX (Phase 1), Alpine.js (narrow scope) |
| Test runner | pytest + pytest-django |
| Lint / type | ruff + mypy |

### Environment differences

(unchanged from previous handoff)

---

## 3. Project Structure

```text
mph/
├── backend/
│   ├── conftest.py
│   ├── manage.py
│   ├── compose.yaml
│   ├── docker/
│   ├── config/
│   │   ├── settings/{base,dev,test,staging,demo,prod}.py
│   │   ├── urls.py
│   │   ├── wsgi.py
│   │   └── asgi.py
│   ├── apps/
│   │   ├── common/
│   │   ├── platform/
│   │   │   ├── accounts/
│   │   │   │   ├── models.py
│   │   │   │   ├── apps.py             # M1 D4 + M1 D5: post_migrate-triggered OAuth loader
│   │   │   │   ├── middleware.py       # M1 D4 + M1 D5 Phase 4: trusted-provider MFA policy
│   │   │   │   ├── signals.py          # M1 D4: allauth signal handlers
│   │   │   │   ├── user_display.py     # M1 D4: ACCOUNT_USER_DISPLAY callable
│   │   │   │   ├── oauth/              # NEW M1 D5
│   │   │   │   │   ├── __init__.py
│   │   │   │   │   ├── adapter.py      # MphSocialAccountAdapter
│   │   │   │   │   ├── claims.py       # ExternalIdentityClaims + normalize
│   │   │   │   │   ├── loader.py       # OAuthProviderConfig → SOCIALACCOUNT_PROVIDERS
│   │   │   │   │   ├── models.py       # OAuthProviderConfig (B.3.7)
│   │   │   │   │   └── signals.py      # social_account_* handlers
│   │   │   │   ├── templatetags/       # NEW M1 D5
│   │   │   │   │   ├── __init__.py
│   │   │   │   │   └── oauth_providers.py
│   │   │   │   ├── services/           # M1 D4 layout
│   │   │   │   │   ├── __init__.py
│   │   │   │   │   ├── _audit.py       # record_auth_event
│   │   │   │   │   ├── _register.py    # register_local_user
│   │   │   │   │   ├── _resolve_external.py  # NEW M1 D5 Phase 2
│   │   │   │   │   └── exceptions.py
│   │   │   │   └── tests/
│   │   │   ├── organizations/
│   │   │   ├── rbac/
│   │   │   ├── audit/
│   │   │   └── support/
│   │   ├── operations/
│   │   │   └── locations/
│   │   └── web/
│   │       ├── landing/
│   │       ├── auth_portal/
│   │       │   ├── views.py             # M1 D4: /login/ is now a 302 redirect
│   │       │   ├── views_select_org.py  # M1 D4: /select-org/ placeholder
│   │       │   ├── views_oauth_help.py  # NEW M1 D5 Phase 3: OAuth-failure help page
│   │       │   ├── urls.py              # adds /oauth-help/<slug:reason>/
│   │       │   └── tests/
│   │       └── tenant_portal/
│   └── templates/
│       ├── base.html
│       ├── account/                   # M1 D4 allauth overrides
│       │   ├── _public_base.html
│       │   ├── _settings_base.html
│       │   ├── login.html               # M1 D5: now renders provider buttons via templatetag
│       │   ├── logout.html
│       │   ├── signup.html
│       │   ├── email.html
│       │   ├── email_confirm.html
│       │   ├── password_change.html
│       │   ├── password_reset.html
│       │   ├── password_reset_done.html
│       │   ├── password_reset_from_key.html
│       │   ├── password_reset_from_key_done.html
│       │   ├── reauthenticate.html
│       │   ├── verified_email_required.html
│       │   ├── email/
│       │   │   ├── email_confirmation_subject.txt
│       │   │   ├── email_confirmation_message.txt
│       │   │   ├── password_reset_key_subject.txt
│       │   │   └── password_reset_key_message.txt
│       │   └── messages/
│       │       ├── email_confirmed.txt
│       │       ├── email_confirmation_sent.txt
│       │       ├── logged_in.txt
│       │       ├── logged_out.txt
│       │       ├── password_changed.txt
│       │       └── unverified_primary_email.txt
│       ├── mfa/                       # M1 D4 allauth.mfa overrides
│       │   ├── authenticate.html
│       │   ├── index.html
│       │   ├── totp/
│       │   │   ├── activate_form.html
│       │   │   └── deactivate_form.html
│       │   └── recovery_codes/
│       │       ├── index.html
│       │       └── generate.html
│       ├── socialaccount/             # NEW M1 D5 Phase 5
│       │   ├── login.html               # provider-redirect interstitial
│       │   ├── connections.html         # user's linked-providers UI
│       │   ├── authentication_error.html
│       │   └── login_cancelled.html
│       └── auth_portal/
│           ├── select_org_placeholder.html
│           └── oauth_help.html         # NEW M1 D5 Phase 3
└── ...
```

### Non-obvious folder conventions

(unchanged from previous handoff, plus:)

- **`apps/platform/accounts/middleware.py`** holds
  `RequireMfaEnrollmentMiddleware`. Position in `MIDDLEWARE` is AFTER
  `allauth.account.middleware.AccountMiddleware`. The middleware
  enforces B.4.9 because allauth.mfa ships only a challenge
  middleware, not a forced-enrollment one. **M1 D5 Phase 4 extended
  the middleware to honor `OAuthProviderConfig.trust_external_mfa`:**
  trusted-provider OAuth users bypass enrollment; untrusted-provider
  users are forced to enroll.
- **`apps/platform/accounts/user_display.py`** holds the
  `ACCOUNT_USER_DISPLAY` callable. Required because our User model
  is email-only (no `username` field), and allauth's
  `default_user_display` reads `user.username`.
- **`apps/web/auth_portal/tests/test_allauth_template_smoke.py`** is
  THE SPINE of M1 D4/D5 test coverage. Parametrized over every
  allauth-rendered template; asserts `expected_status` (default 200,
  some non-200 like 401 for socialaccount auth-error) + at least one
  acceptable `mph-*` chrome class. **Any new template override added
  in future milestones MUST be added to this table.**
- **`apps/platform/accounts/oauth/`** is the dedicated subpackage for
  all OAuth/OIDC code (M1 D5). The model, claims, loader, adapter,
  and signals all live here. The resolution service lives in
  `services/_resolve_external.py` because services have their own
  layout convention.
- **`apps/platform/accounts/templatetags/oauth_providers.py`**
  exposes `{% active_oauth_providers %}` and
  `{% user_linked_providers %}` for the login and connections
  templates. Templates that need the OAuth provider list must
  `{% load oauth_providers %}` explicitly — no context processor
  registers this globally.

---

## 4. Major Decisions Already Made

(All previous decisions preserved.)

### Identity / Auth (M1 D4)

- **django-allauth 65.x** owns the login form, password reset,
  signup, MFA, email management, and reauthentication views. Mounted
  at `/accounts/`.
- **`/login/`** is a permanent redirect to `/accounts/login/`. The
  M0 auth_portal scaffold view is gone.
- **`/select-org/`** is a placeholder view for M1 D4. Real org
  picker lands in M1 D6.
- **TOTP + recovery codes** are the v1 MFA. WebAuthn/passkeys are
  out of scope for v1.
- **Mandatory email verification** (`ACCOUNT_EMAIL_VERIFICATION = "mandatory"`).
- **Forced MFA enrollment** (`RequireMfaEnrollmentMiddleware`). User
  who logs in without TOTP is redirected to
  `/accounts/2fa/totp/activate/`.
- **`ACCOUNT_USER_DISPLAY`** points at our email-returning callable.
- **`ACCOUNT_USER_MODEL_USERNAME_FIELD = None`** because the User
  model has no `username` field.
- **`seed_dev_tenant`** creates a verified primary `EmailAddress`
  for the demo admin so dev login isn't blocked by the verification
  gate.

### OAuth / OIDC (M1 D5)

- **`OAuthProviderConfig` is platform-managed** per B.3.7. **Stores
  env-var KEY NAMES only**, never the secret values. The loader
  reads `os.environ.get(config.client_secret_env_key)` at runtime.
- **`ExternalIdentityClaims`** is the normalized B.3.8 shape. **Raw
  provider claims MUST NOT reach business logic** — only the
  normalized claims object. The translator
  (`normalize_socialaccount_claims`) strips token-shaped keys
  defensively before constructing the claims dataclass.
- **`resolve_external_user(...)` is the single chokepoint** for
  external→canonical user resolution (B.4.6). Strict B.4.7 rules
  1-4 enforced: verified email when required, no conflicting
  external identity, provider active. **Rule #5** (invite-flow
  confirmation) is **not** enforced here — it lives one level up in
  the adapter or invite-acceptance view. The `LinkingNotAllowedError`
  exception is reserved for forward compatibility but never raised
  in M1 D5.
- **`allow_self_registration` is per-provider**, extension to B.3.7.
  Default False (invitation-only). Tracked in retro as a deviation.
- **`MphSocialAccountAdapter`** subclasses allauth's
  `DefaultSocialAccountAdapter` and overrides `pre_social_login` to
  call `resolve_external_user`. Each typed exception maps to a
  specific `/oauth-help/<reason>/` redirect via `ImmediateHttpResponse`.
- **Trusted-provider MFA bypass** is in
  `RequireMfaEnrollmentMiddleware`. The middleware reads
  `request.session["mph_login_provider_code"]` (written by Phase 3
  signal handlers at login time) and queries
  `OAuthProviderConfig.trust_external_mfa`. The TOTP **enrollment**
  is bypassed for trusted providers; the TOTP **challenge** (allauth's
  own middleware) still fires for users who already have TOTP —
  conservatively safe, tracked for future polish.
- **`SOCIALACCOUNT_PROVIDERS` is populated via `post_migrate` signal**,
  not `AppConfig.ready()`. Django warns against DB queries during
  app init; `post_migrate` fires after migrations including the
  test-DB setup, so providers are loaded for every environment.
  **Tradeoff:** runtime-added provider configs require a server
  restart that triggers migrate to take effect. Acceptable since
  provider config is platform-admin-managed.
- **`SOCIALACCOUNT_AUTO_SIGNUP = False`** — our adapter does the
  resolution; allauth's auto-signup would bypass our policy.
- **`SOCIALACCOUNT_LOGIN_ON_GET = False`** — provider login URLs
  are POST-only to prevent CSRF via hidden-image-tag attacks. Our
  login and connections templates render forms with CSRF tokens.

### Audit catalog

The `_KNOWN_EVENT_TYPES` set in `apps/platform/audit/services.py` now
includes the full B.4.19 catalog plus MFA lifecycle codes. Pending
G.5.2 amendment in M2.

**OAuth events emitted (M1 D5):**

- `OAUTH_LOGIN_STARTED` — adapter on every `pre_social_login`.
- `OAUTH_LOGIN_SUCCEEDED` — `social_account_added` (first link) and
  `social_account_updated` (repeat login) signal handlers.
- `OAUTH_LOGIN_FAILED` — adapter on typed exception, with structured
  `failure_reason` metadata: `provider_not_active`, `domain_not_allowed`,
  `email_not_verified`, `conflicting_identity`, `user_inactive`,
  `no_existing_user`, `authentication_error`.
- `OAUTH_ACCOUNT_LINKED` — `resolve_external_user` service.
- `OAUTH_ACCOUNT_UNLINKED` — `social_account_removed` signal handler.
- `OAUTH_PROVIDER_MFA_TRUSTED` — middleware, once per session for
  trusted-provider users.
- `OAUTH_PROVIDER_MFA_NOT_TRUSTED` — middleware, once per session
  for untrusted-provider users.

---

## 5-12. Models, Services, Tests, Risks, Commands, Handoff notes

(Unchanged sections preserved; M1 D4 and M1 D5 updates appended.)

### New services (M1 D4)

#### `apps.platform.accounts.services.register_local_user(...)`

Keyword-only primitive arguments: `email`, `password`, `actor_id`,
`is_active`. Single `transaction.atomic()`. Emits `USER_REGISTERED`.
Typed exceptions: `UserAlreadyExistsError`, `UserNotFoundError`.

#### `apps.platform.accounts.services.record_auth_event(...)`

The single service-layer entry point for allauth signal handlers.
Owns its own atomic boundary. Re-raises programming errors
(`UnknownAuditEventError`, `AuditOutsideTransactionError`); swallows
others so auth flow isn't broken by audit hiccups.

### New services (M1 D5)

#### `apps.platform.accounts.services.resolve_external_user(...)`

Keyword-only primitive arguments: `claims` (ExternalIdentityClaims),
`provider_config` (OAuthProviderConfig), `actor_id`. The single
chokepoint for OAuth/OIDC user resolution per B.4.6 / B.4.7.
Single `transaction.atomic()`. Emits `OAUTH_ACCOUNT_LINKED` on link;
also emits `USER_REGISTERED` on self-registration creation.

Typed exceptions (all in `services/exceptions.py`):

- `UserInactiveError` — matched user is inactive.
- `ProviderNotActiveError` — `OAuthProviderConfig.is_active=False`.
- `EmailNotVerifiedError` — provider didn't assert verification.
- `EmailDomainNotAllowedError` — domain not in allowlist.
- `ConflictingExternalIdentityError` — different SocialAccount
  exists for same provider.
- `NoExistingUserAndSelfRegistrationDisabledError` — no match and
  self-registration disabled.
- `LinkingNotAllowedError` — reserved for B.4.7 #5 (invite-flow
  confirmation); not raised in M1 D5.

### What NOT to assume (M1 D4 additions)

- **Allauth's template context keys are NOT all documented.** When
  adding a new allauth template override, GET the page in a test
  before assuming a context variable exists. The smoke suite at
  `apps/web/auth_portal/tests/test_allauth_template_smoke.py` is the
  enforcement mechanism; add new overrides to its table.
- **Allauth.mfa does NOT force enrollment.** It only challenges
  already-enrolled users. Forced enrollment lives in our middleware.
- **The User model has NO `username` field.** Any code that reads
  `user.username` will crash. Use `user.email` or
  `apps.platform.accounts.user_display.user_display(user)`.

### What NOT to assume (M1 D5 additions)

- **`OAuthProviderConfig` does NOT store secrets.** There is no
  `client_secret` column. The loader reads
  `os.environ.get(config.client_secret_env_key)` at runtime.
  Inspecting the model in admin/shell will only show env-var key
  names, never the actual credentials.
- **`resolve_external_user` does NOT create Memberships, Roles, or
  Capabilities.** OAuth login proves identity only (B.3.9). Anyone
  who reads OAuth code and thinks "the user logged in, surely they
  have access to something" is wrong — tenant access is established
  through invitations + Memberships + RBAC in a separate code path.
- **B.4.7 rule #5 is NOT enforced inside `resolve_external_user`.**
  The rule ("user is completing an invite flow or passes a local
  confirmation challenge") is a UI-state-machine concern that the
  service can't see. It lives in the adapter/invite-acceptance view
  in a later milestone. M1 D5 enforces rules 1-4 strictly.
- **Trusted-provider TOTP challenge bypass is NOT implemented.**
  The middleware bypasses *enrollment* for trusted-provider users
  but not the *challenge* (allauth.mfa's own middleware). A
  trusted-provider user who has previously enrolled TOTP still sees
  the challenge on each login. Conservatively safe; tracked as an
  open polish item.
- **`SOCIALACCOUNT_PROVIDERS` is built dynamically.** It is NOT
  defined statically in `base.py`. The dict is populated at
  `post_migrate` time by `apply_socialaccount_providers_to_settings()`.
  Adding a row to `OAuthProviderConfig` at runtime does NOT
  automatically make the provider available; a server restart with
  migrations triggers the load.
- **`socialaccount/authentication_error.html` returns HTTP 401, not
  200.** Allauth's view signals failure via status code AND template.
  The smoke suite's `expected_status` field handles this.
- **`SOCIALACCOUNT_AUTO_SIGNUP` is intentionally False.** Don't
  flip it to True without understanding that this would bypass our
  resolution policy (`resolve_external_user`). Allauth would do its
  own user-creation logic which doesn't respect our B.4.7 rules.

### Files to review before changing code

| Change area | Files to read first |
| --- | --- |
| Anything in `/accounts/*` flow | `config/settings/base.py` ACCOUNT_*, MFA_* settings; allauth template overrides |
| New auth audit event | `_KNOWN_EVENT_TYPES`, `signals.py`, `oauth/signals.py`, B.4.19 |
| MFA policy change | `RequireMfaEnrollmentMiddleware`, B.4.8, B.4.9 |
| Adding an allauth template override | `apps/web/auth_portal/tests/test_allauth_template_smoke.py` — add a TemplateCase row |
| OAuth provider config schema | `apps/platform/accounts/oauth/models.py`, B.3.7, M1 retro D5 deviation #1 |
| External-identity resolution policy | `apps/platform/accounts/services/_resolve_external.py`, B.4.6, B.4.7 |
| Trusted-vs-untrusted provider MFA | `apps/platform/accounts/middleware.py`, `oauth/signals.py`, B.4.8 |
| OAuth templates | `templates/socialaccount/*`, `templates/auth_portal/oauth_help.html`, smoke suite |
| OAuth signal wiring | `apps/platform/accounts/oauth/signals.py`, `apps.py` (post_migrate hook) |

---

## Fresh Session Startup Prompt

```
I'm continuing work on MyPipelineHero, a Django-based multi-tenant
CRM SaaS platform. I'm attaching:

1. handoff.md — current project state and conventions.
2. docs/guide.md (v0.7) — authoritative architecture source.

Treat the guide as the source of truth. When the guide conflicts with
general best practices, follow the guide unless there is a clear
safety, security, correctness, or production-readiness concern. Flag
any deviation explicitly.

Act as my senior software engineer, technical architect, and
implementation reviewer.

Project posture summary:

- Row-level multi-tenancy. Organization is the tenant root.
- Custom User model from migration #1. Email-only identity; no
  username field. Use ACCOUNT_USER_DISPLAY callable, not user.username.
- Service-layer-first business logic. apps/*/services/ is the sole
  authoritative state-change boundary.
- Audit emission is contractually mandatory for state changes;
  audit_emit raises if not inside a transaction.
- django-allauth 65.x is wired with allauth.account, allauth.mfa,
  and allauth.socialaccount for local password + TOTP/recovery codes
  + OAuth/OIDC.
- Forced MFA enrollment via custom RequireMfaEnrollmentMiddleware
  (allauth.mfa ships only a challenge middleware). The middleware
  also honors OAuthProviderConfig.trust_external_mfa for OAuth users.
- OAuth/OIDC integration: OAuthProviderConfig stores env-var key
  NAMES only (B.3.7); ExternalIdentityClaims normalizes provider
  claims (B.3.8); resolve_external_user is the single resolution
  chokepoint (B.4.6/B.4.7); MphSocialAccountAdapter enforces policy
  at pre_social_login.
- Allauth template overrides at templates/account/*, templates/mfa/*,
  templates/socialaccount/*. ANY new override MUST be added to the
  smoke suite at apps/web/auth_portal/tests/test_allauth_template_smoke.py.
- M0 (Foundation) complete; M1 D1-D5 complete; M1 D6 (cross-subdomain
  handoff + tenant-local session + real org picker per B.4.11-B.4.17)
  is next.

When I ask you to implement a task:

1. Briefly restate the scope you are about to implement.
2. Identify any assumptions.
3. Proceed without asking follow-up questions unless genuinely
   blocked.
4. Flag anything that looks wrong, inconsistent, risky, or
   under-specified.
5. Keep the implementation aligned with the guide.

When providing code, provide full files (not patches), one fenced
code block per file, with the file path stated.

Do not:
- Suggest switching away from Django.
- Use schema-per-tenant.
- Use the base Django admin as the production admin UI.
- Skip tenant isolation.
- Bypass the service layer for state-changing workflows.
- Put business logic in model save(), signals, forms, views, DRF
  serializers, Celery tasks, or admin actions.
- Log secrets, OAuth tokens, authorization codes, TOTP secrets, or
  recovery codes.
- Guess if you're unsure if a file or code exists — ask for the file.

My next step is M1 Deliverable 6: cross-subdomain handoff +
tenant-local session + real org picker per B.4.11 through B.4.17
of the guide.

Confirm you understand the project posture, then proceed.
```
