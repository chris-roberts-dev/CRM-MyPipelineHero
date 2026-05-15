# MyPipelineHero — Project Handoff

**Last updated:** end of M1 Deliverable 4 (identity wiring: local
login + MFA + recovery codes via django-allauth + allauth.mfa).

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
- **D5 — next** OAuth/OIDC provider integration.
- D6 — pending (cross-subdomain handoff + tenant-local session + real org picker).
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
│   │   │   │   ├── apps.py            # registers signal handlers
│   │   │   │   ├── middleware.py      # NEW M1 D4: RequireMfaEnrollmentMiddleware
│   │   │   │   ├── signals.py         # NEW M1 D4: allauth signal handlers
│   │   │   │   ├── user_display.py    # NEW M1 D4: ACCOUNT_USER_DISPLAY callable
│   │   │   │   ├── services/          # NEW M1 D4 layout
│   │   │   │   │   ├── __init__.py
│   │   │   │   │   ├── _audit.py      # record_auth_event
│   │   │   │   │   ├── _register.py   # register_local_user
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
│   │       │   ├── views_select_org.py  # NEW M1 D4: /select-org/ placeholder
│   │       │   ├── urls.py
│   │       │   └── tests/
│   │       └── tenant_portal/
│   └── templates/
│       ├── base.html
│       ├── account/                   # NEW M1 D4: allauth overrides
│       │   ├── _public_base.html
│       │   ├── _settings_base.html
│       │   ├── login.html
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
│       ├── mfa/                       # NEW M1 D4: allauth.mfa overrides
│       │   ├── authenticate.html
│       │   ├── index.html
│       │   ├── totp/
│       │   │   ├── activate_form.html
│       │   │   └── deactivate_form.html
│       │   └── recovery_codes/
│       │       ├── index.html
│       │       └── generate.html
│       └── auth_portal/
│           └── select_org_placeholder.html
└── ...
```

### Non-obvious folder conventions

(unchanged from previous handoff, plus:)

- **`apps/platform/accounts/middleware.py`** holds
  `RequireMfaEnrollmentMiddleware`. Position in `MIDDLEWARE` is AFTER
  `allauth.account.middleware.AccountMiddleware`. The middleware
  enforces B.4.9 because allauth.mfa ships only a challenge
  middleware, not a forced-enrollment one.
- **`apps/platform/accounts/user_display.py`** holds the
  `ACCOUNT_USER_DISPLAY` callable. Required because our User model
  is email-only (no `username` field), and allauth's
  `default_user_display` reads `user.username`.
- **`apps/web/auth_portal/tests/test_allauth_template_smoke.py`** is
  THE SPINE of M1 D4 test coverage. Parametrized over every
  allauth-rendered template; asserts 200 + `mph-auth-card` /
  `mph-settings-card`. Any new template override added in future
  milestones MUST be added to this table.

---

## 4. Major Decisions Already Made

(All previous decisions preserved; M1 D4 adds:)

### Identity / Auth

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
  who logs in without TOTP is redirected to `/accounts/2fa/totp/`.
- **`ACCOUNT_USER_DISPLAY`** points at our email-returning callable.
- **`seed_dev_tenant`** creates a verified primary `EmailAddress`
  for the demo admin so dev login isn't blocked by the verification
  gate.

### Audit catalog

The `_KNOWN_EVENT_TYPES` set in `apps/platform/audit/services.py` now
includes the full B.4.19 catalog plus MFA lifecycle codes. Pending
G.5.2 amendment in M2.

---

## 5-12. Models, Services, Tests, Risks, Commands, Handoff notes

(Unchanged sections preserved; M1 D4 updates:)

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

### Files to review before changing code (M1 D4 additions)

| Change area | Files to read first |
| --- | --- |
| Anything in `/accounts/*` flow | `config/settings/base.py` ACCOUNT_*, MFA_* settings; allauth template overrides |
| New auth audit event | `_KNOWN_EVENT_TYPES`, `signals.py`, B.4.19 |
| MFA policy change | `RequireMfaEnrollmentMiddleware`, B.4.9 |
| Adding an allauth template override | `apps/web/auth_portal/tests/test_allauth_template_smoke.py` — add a TemplateCase row |

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
- django-allauth 65.x is wired with allauth.mfa for TOTP + recovery
  codes. Forced enrollment via custom RequireMfaEnrollmentMiddleware
  (allauth.mfa ships only a challenge middleware).
- Allauth template overrides at templates/account/* and templates/mfa/*.
  ANY new override MUST be added to the smoke suite at
  apps/web/auth_portal/tests/test_allauth_template_smoke.py.
- M0 (Foundation) complete; M1 D1-D4 complete; M1 D5 (OAuth/OIDC) is next.

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

My next step is M1 Deliverable 5: OAuth/OIDC provider integration
per J.3.3 and J.3.6 of the guide.

Confirm you understand the project posture, then proceed.
```